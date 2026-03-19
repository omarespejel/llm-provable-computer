#!/usr/bin/env python3
"""Validate exported llm-provable-computer ONNX programs with ONNX Runtime."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

INPUT_DIM = 41
OUTPUT_DIM = 9
FORMAT_VERSION = 1
U16_MODULUS = 1 << 16

EXPECTED_SHIPPED_RESULTS = {
    "addition": {"acc": 8, "halted": True},
    "counter": {"acc": 5, "halted": True},
    "fibonacci": {"acc": 21, "halted": True},
    "multiply": {"acc": 42, "halted": True},
    "subroutine_addition": {"acc": 42, "halted": True},
}


class ValidationError(RuntimeError):
    pass


def rust_round(value: float) -> int:
    if not math.isfinite(value):
        raise ValidationError(f"cannot round non-finite value {value!r}")
    if value >= 0.0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def wrap_i16(value: int) -> int:
    return ((int(value) + (1 << 15)) % U16_MODULUS) - (1 << 15)


def checked_u8(field: str, value: int) -> int:
    if 0 <= value <= 0xFF:
        return value
    raise ValidationError(f"compiled transition produced invalid {field} value {value}")


def validate_stack_pointer(sp: int, memory_size: int) -> None:
    if sp > memory_size:
        raise ValidationError(
            f"stack pointer {sp} is out of bounds for memory size {memory_size}"
        )


def instruction_kind(instruction: Any) -> str:
    if isinstance(instruction, str):
        return instruction
    if isinstance(instruction, dict) and len(instruction) == 1:
        return next(iter(instruction))
    raise ValidationError(f"unsupported instruction encoding in metadata: {instruction!r}")


def validate_stack_precondition(instruction: Any, sp: int, memory_size: int) -> None:
    kind = instruction_kind(instruction)
    if kind in {"Push", "Call"} and sp == 0:
        raise ValidationError(
            f"stack overflow: sp {sp} cannot grow downward within memory size {memory_size}"
        )
    if kind in {"Pop", "Ret"} and sp >= memory_size:
        raise ValidationError(f"stack underflow: sp {sp} is invalid for memory size {memory_size}")


def parse_attention_mode(raw_mode: Any) -> tuple[str, float | None]:
    if raw_mode == "AverageHard":
        return ("average_hard", None)
    if raw_mode == "Softmax":
        return ("softmax", 1.0)
    if isinstance(raw_mode, dict) and "HardSoftmax" in raw_mode:
        payload = raw_mode["HardSoftmax"]
        if not isinstance(payload, dict) or "temperature" not in payload:
            raise ValidationError(f"invalid HardSoftmax payload: {payload!r}")
        temperature = float(payload["temperature"])
        if not math.isfinite(temperature) or temperature <= 0.0:
            raise ValidationError(
                f"soft attention temperature must be finite and > 0, got {temperature}"
            )
        return ("hard_softmax", temperature)
    raise ValidationError(f"unsupported attention mode encoding: {raw_mode!r}")


def metadata_path(path: Path) -> Path:
    if path.is_dir():
        return path / "metadata.json"
    return path


def build_input_vector(state: dict[str, Any], operand: int) -> np.ndarray:
    vector = np.zeros((1, INPUT_DIM), dtype=np.float32)
    vector[0, 0] = 1.0
    vector[0, 1] = float(state["pc"])
    vector[0, 2] = float((state["pc"] + 1) & 0xFF)
    vector[0, 3] = float(state["acc"])
    vector[0, 4] = 1.0 if state["zero_flag"] else 0.0
    vector[0, 5] = 1.0 if state["carry_flag"] else 0.0
    vector[0, 6] = 1.0 if state["halted"] else 0.0
    vector[0, 7] = float(state["sp"])
    vector[0, 8] = float(operand)

    acc_bits = int(state["acc"]) & 0xFFFF
    operand_bits = int(operand) & 0xFFFF
    for bit in range(16):
        vector[0, 9 + bit] = 1.0 if ((acc_bits >> bit) & 1) else 0.0
        vector[0, 25 + bit] = 1.0 if ((operand_bits >> bit) & 1) else 0.0

    return vector


def weighted_memory_value(history: list[tuple[int, int]], temperature: float) -> int:
    scores = np.asarray([step / temperature for step, _ in history], dtype=np.float32)
    max_score = np.max(scores)
    weights = np.exp(scores - max_score).astype(np.float32, copy=False)
    normalized = weights / np.sum(weights, dtype=np.float32)
    values = np.asarray([value for _, value in history], dtype=np.float32)
    blended = float(np.sum(normalized * values, dtype=np.float32))
    return wrap_i16(rust_round(blended))


def resolve_memory_read(
    read_spec: dict[str, Any],
    state: dict[str, Any],
    memory: list[int],
    histories: list[list[tuple[int, int]]],
    attention_mode: tuple[str, float | None],
) -> int:
    kind = read_spec["kind"]
    if kind == "none":
        return 0
    if kind == "direct":
        address = checked_u8("memory address", int(read_spec["address"]))
    elif kind == "stack_top":
        address = checked_u8("stack pointer", int(state["sp"]))
    else:
        raise ValidationError(f"unsupported memory read kind {kind!r}")

    if address >= len(memory):
        raise ValidationError(
            f"memory address {address} is out of bounds for memory size {len(memory)}"
        )

    history = histories[address]
    mode_name, temperature = attention_mode
    if mode_name == "average_hard":
        return history[-1][1]
    if mode_name == "hard_softmax":
        assert temperature is not None
        return weighted_memory_value(history, temperature)
    if mode_name == "softmax":
        return weighted_memory_value(history, 1.0)
    raise ValidationError(f"unsupported attention mode {attention_mode!r}")


def load_compiled_program(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    requested = Path(path)
    meta_path = metadata_path(requested)
    export_dir = meta_path.parent
    with meta_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    if metadata.get("format_version") != FORMAT_VERSION:
        raise ValidationError(
            f"unsupported metadata format version {metadata.get('format_version')}"
        )
    if int(metadata["input_dim"]) != INPUT_DIM:
        raise ValidationError(
            f"metadata input_dim {metadata['input_dim']} does not match expected {INPUT_DIM}"
        )
    if int(metadata["output_dim"]) != OUTPUT_DIM:
        raise ValidationError(
            f"metadata output_dim {metadata['output_dim']} does not match expected {OUTPUT_DIM}"
        )

    instructions = metadata["instructions"]
    program = metadata["program"]
    if len(instructions) != len(program["instructions"]):
        raise ValidationError(
            "metadata instructions length does not match embedded program instruction count"
        )

    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session_options.log_severity_level = 3

    loaded_models: list[dict[str, Any]] = []
    for expected_pc, instruction in enumerate(instructions):
        actual_pc = int(instruction["pc"])
        if actual_pc != expected_pc:
            raise ValidationError(
                f"exported instruction table is misaligned at pc {expected_pc}: found model for pc {actual_pc}"
            )

        model_path = export_dir / instruction["model_file"]
        if not model_path.exists():
            raise ValidationError(f"missing ONNX file {model_path}")

        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )
        loaded_models.append(
            {
                "metadata": instruction,
                "session": session,
                "input_name": session.get_inputs()[0].name,
                "output_name": session.get_outputs()[0].name,
            }
        )

    return metadata, loaded_models


def execute_program(
    metadata: dict[str, Any],
    models: list[dict[str, Any]],
    max_steps: int,
) -> dict[str, Any]:
    program = metadata["program"]
    memory = [wrap_i16(int(value)) for value in program["initial_memory"]]
    state = {
        "pc": 0,
        "acc": 0,
        "sp": len(memory),
        "zero_flag": True,
        "carry_flag": False,
        "halted": False,
        "memory": list(memory),
    }
    trace = [dict(state)]
    histories = [[(0, value)] for value in memory]
    attention_mode = parse_attention_mode(metadata["config"]["attention_mode"])

    step_count = 0
    while step_count < max_steps and not state["halted"]:
        validate_stack_pointer(int(state["sp"]), len(memory))
        pc = int(state["pc"])
        if pc >= len(models):
            raise ValidationError(
                f"program counter {pc} is out of bounds for program length {len(models)}"
            )
        instruction_model = models[pc]
        instruction_meta = instruction_model["metadata"]
        validate_stack_precondition(instruction_meta["instruction"], int(state["sp"]), len(memory))

        operand = resolve_memory_read(
            instruction_meta["memory_read"],
            state,
            memory,
            histories,
            attention_mode,
        )
        input_vector = build_input_vector(state, operand)
        session_output = instruction_model["session"].run(
            [instruction_model["output_name"]],
            {instruction_model["input_name"]: input_vector},
        )[0]
        transition = np.asarray(session_output, dtype=np.float32).reshape(-1)

        if transition.size != OUTPUT_DIM:
            raise ValidationError(
                f"instruction at pc {state['pc']} produced {transition.size} outputs, expected {OUTPUT_DIM}"
            )

        step_count += 1

        if float(transition[3]) >= 0.5:
            write_addr = checked_u8("memory address", rust_round(float(transition[4])))
            if write_addr >= len(memory):
                raise ValidationError(
                    f"memory address {write_addr} is out of bounds for memory size {len(memory)}"
                )
            write_value = wrap_i16(rust_round(float(transition[5])))
            memory[write_addr] = write_value
            histories[write_addr].append((step_count, write_value))

        next_pc = checked_u8("pc", rust_round(float(transition[0])))
        next_sp = checked_u8("sp", rust_round(float(transition[2])))
        validate_stack_pointer(next_sp, len(memory))

        state = {
            "pc": next_pc,
            "acc": wrap_i16(rust_round(float(transition[1]))),
            "sp": next_sp,
            "zero_flag": bool(float(transition[6]) >= 0.5),
            "carry_flag": bool(float(transition[7]) >= 0.5),
            "halted": bool(float(transition[8]) >= 0.5),
            "memory": list(memory),
        }
        trace.append(dict(state))

    return {
        "steps": step_count,
        "halted": bool(state["halted"]),
        "final_state": state,
        "trace": trace,
    }


def infer_program_name(export_path: Path, explicit_name: str | None) -> str | None:
    if explicit_name:
        return explicit_name
    candidate = export_path.name if export_path.is_dir() else export_path.parent.name
    return candidate or None


def build_expectations(args: argparse.Namespace, program_name: str | None) -> dict[str, Any]:
    expectations: dict[str, Any] = {}
    if program_name in EXPECTED_SHIPPED_RESULTS:
        expectations.update(EXPECTED_SHIPPED_RESULTS[program_name])
    if args.expected_acc is not None:
        expectations["acc"] = args.expected_acc
    if args.expected_halted is not None:
        expectations["halted"] = args.expected_halted
    if args.expected_steps is not None:
        expectations["steps"] = args.expected_steps
    return expectations


def validate_expectations(result: dict[str, Any], expectations: dict[str, Any]) -> None:
    final_state = result["final_state"]
    if "acc" in expectations and final_state["acc"] != expectations["acc"]:
        raise ValidationError(
            f"expected ACC={expectations['acc']}, got {final_state['acc']}"
        )
    if "halted" in expectations and result["halted"] != expectations["halted"]:
        raise ValidationError(
            f"expected halted={expectations['halted']}, got {result['halted']}"
        )
    if "steps" in expectations and result["steps"] != expectations["steps"]:
        raise ValidationError(
            f"expected steps={expectations['steps']}, got {result['steps']}"
        )


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value {value!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate llm-provable-computer ONNX exports with onnxruntime."
    )
    parser.add_argument("export_path", help="Export directory or metadata.json path")
    parser.add_argument("--max-steps", type=int, default=4096, help="Maximum execution steps")
    parser.add_argument(
        "--program-name",
        help="Program name used for shipped-program expectations when the export directory name is not stable",
    )
    parser.add_argument("--expected-acc", type=int, help="Expected final ACC value")
    parser.add_argument(
        "--expected-halted",
        type=parse_bool,
        help="Expected final halted flag (true/false)",
    )
    parser.add_argument("--expected-steps", type=int, help="Expected executed step count")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the execution result as JSON",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    export_path = Path(args.export_path)
    metadata, models = load_compiled_program(export_path)
    result = execute_program(metadata, models, args.max_steps)

    program_name = infer_program_name(export_path, args.program_name)
    expectations = build_expectations(args, program_name)
    if expectations:
        validate_expectations(result, expectations)

    payload = {
        "program_name": program_name,
        "steps": result["steps"],
        "halted": result["halted"],
        "final_state": result["final_state"],
        "trace": result["trace"],
        "expectations": expectations,
    }

    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(f"Steps: {payload['steps']}")
        print(f"Halted: {payload['halted']}")
        print(f"ACC: {payload['final_state']['acc']}")
        print(f"PC: {payload['final_state']['pc']}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ValidationError as err:
        print(f"validation error: {err}", file=sys.stderr)
        raise SystemExit(1)
