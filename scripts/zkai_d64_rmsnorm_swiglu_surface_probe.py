#!/usr/bin/env python3
"""Implementation-surface probe for a d64 RMSNorm-SwiGLU-residual block.

This is not a prover benchmark.  It asks whether the current checked TVM/Stwo
surface can plausibly be extended by "just emitting a larger fixture" for a
matched d=64 transformer block.  The answer matters because a matched public
zkAI comparison needs a real vector-block proof surface, not another wrapper
around the current bounded statement-binding fixture.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ARITHMETIC_PROVER_SOURCE = ROOT / "src" / "stwo_backend" / "arithmetic_subset_prover.rs"
INSTRUCTION_SOURCE = ROOT / "src" / "instruction.rs"
STATE_SOURCE = ROOT / "src" / "state.rs"
LINEAR_BLOCK_V4_PROGRAM = ROOT / "programs" / "linear_block_v4_with_lookup.tvm"

SCHEMA = "zkai-d64-rmsnorm-swiglu-surface-probe-v1"
DECISION_NO_GO = "NO_GO_DIRECT_TVM_LOWERING"
DECISION_GO = "GO_PARAMETERIZED_VECTOR_SURFACE"
TARGET_WIDTH = 64
FF_DIM_MULTIPLIER = 4
DEFAULT_SOURCE_DATE_EPOCH = 0
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v1"

TSV_COLUMNS = (
    "target_width",
    "decision",
    "ff_dim",
    "estimated_linear_muls",
    "estimated_weight_scalars",
    "current_max_addressable_memory_cells",
    "current_pc_horizon",
    "current_fixture_memory_cells",
    "current_fixture_instruction_count",
    "current_fixture_mul_memory_ops",
    "weight_cells_over_memory_limit",
    "mul_ops_over_pc_horizon",
    "blocker_count",
)


class SurfaceProbeError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: pathlib.Path) -> str:
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(DEFAULT_SOURCE_DATE_EPOCH))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise SurfaceProbeError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise SurfaceProbeError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    override = os.environ.get("ZKAI_GIT_COMMIT")
    if override:
        return override
    return "unspecified"


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise SurfaceProbeError(f"failed to read {path}: {err}") from err


def _strip_rust_comments(source: str) -> str:
    output: list[str] = []
    i = 0
    in_string = False
    escaped = False
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if in_string:
            output.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < len(source) and source[i] != "\n":
                i += 1
            if i < len(source):
                output.append("\n")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < len(source) and not (source[i] == "*" and source[i + 1] == "/"):
                output.append("\n" if source[i] == "\n" else " ")
                i += 1
            i = min(i + 2, len(source))
            continue
        output.append(ch)
        if ch == '"':
            in_string = True
        i += 1
    return "".join(output)


def _strip_rust_comments_and_strings(source: str) -> str:
    source = _strip_rust_comments(source)
    output: list[str] = []
    i = 0
    in_string = False
    escaped = False
    while i < len(source):
        ch = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
                output.append('"')
            else:
                output.append(" ")
            i += 1
            continue
        output.append(ch)
        if ch == '"':
            in_string = True
        i += 1
    return "".join(output)


def _ratio_or_inf(numerator: int, denominator: int) -> float:
    return numerator / float(denominator) if denominator > 0 else float("inf")


def d64_target() -> dict[str, Any]:
    ff_dim = TARGET_WIDTH * FF_DIM_MULTIPLIER
    linear_muls = 3 * TARGET_WIDTH * ff_dim
    return {
        "target_id": "rmsnorm-swiglu-residual-d64-v1",
        "statement_kind": "transformer-block",
        "model_id": "urn:zkai:ptvm:rmsnorm-swiglu-residual-d64-v1",
        "required_proof_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "ff_dim": ff_dim,
        "activation": "SwiGLU",
        "normalization": "RMSNorm",
        "residual": True,
        "estimated_linear_muls": linear_muls,
        "estimated_weight_scalars": linear_muls,
        "estimated_activation_rows": ff_dim,
        "estimated_norm_rows": 1,
        "minimum_public_statement_bindings": [
            "model_artifact_commitment",
            "model_config_commitment",
            "weight_commitment",
            "input_activation_commitment",
            "output_activation_commitment",
            "normalization_config_commitment",
            "activation_lookup_commitment",
            "public_instance_commitment",
            "proof_commitment",
            "verifying_key_commitment",
            "setup_commitment",
            "verifier_domain",
            "proof_system_version",
        ],
    }


def _extract_first_match_int(source: str, pattern: str, label: str) -> int:
    match = re.search(pattern, source)
    if not match:
        raise SurfaceProbeError(f"could not extract {label}")
    return int(match.group(1))


def scan_tvm_limits(
    instruction_path: pathlib.Path = INSTRUCTION_SOURCE,
    state_path: pathlib.Path = STATE_SOURCE,
) -> dict[str, Any]:
    instruction_source = _strip_rust_comments_and_strings(_read_text(instruction_path))
    state_source = _strip_rust_comments_and_strings(_read_text(state_path))
    memory_limit_detected = "memory_size > usize::from(u8::MAX)" in instruction_source
    pc_u8_detected = "pub pc: u8" in state_source and "instruction_at(&self, pc: u8)" in instruction_source
    address_u8_detected = "Load(u8)" in instruction_source and "MulMemory(u8)" in instruction_source
    immediate_i16_detected = "LoadImmediate(i16)" in instruction_source
    return {
        "instruction_source_path": _display_path(instruction_path),
        "instruction_source_sha256": sha256_file(instruction_path),
        "state_source_path": _display_path(state_path),
        "state_source_sha256": sha256_file(state_path),
        "memory_limit_detected": memory_limit_detected,
        "pc_u8_detected": pc_u8_detected,
        "address_u8_detected": address_u8_detected,
        "immediate_i16_detected": immediate_i16_detected,
        "max_addressable_memory_cells": 255,
        "pc_horizon": 256,
        "limits_are_current": all(
            [
                memory_limit_detected,
                pc_u8_detected,
                address_u8_detected,
                immediate_i16_detected,
            ]
        ),
    }


def scan_prover_gates(source_path: pathlib.Path = ARITHMETIC_PROVER_SOURCE) -> dict[str, Any]:
    source_without_comments = _strip_rust_comments(_read_text(source_path))
    code_source = _strip_rust_comments_and_strings(source_without_comments)
    markers = {
        "fixture_gate_function": "validate_phase5_proven_fixture" in code_source,
        "linear_block_v4_exact_matcher": "matches_linear_block_v4_with_lookup" in code_source,
        "decoding_step_v2_family_matcher": "matches_decoding_step_v2" in code_source,
        "broader_arithmetic_subset_internal": "broader arithmetic-subset AIR coverage remains internal"
        in source_without_comments,
        "phase12_decoding_only": "experimental Phase12 carry-aware proving supports only the decoding_step_v2 family"
        in source_without_comments,
    }
    backend_versions = sorted(set(re.findall(r"stwo-[a-zA-Z0-9_.\\-]+", source_without_comments)))
    return {
        "source_path": _display_path(source_path),
        "source_sha256": sha256_file(source_path),
        "markers": markers,
        "fixture_gate_detected": all(markers.values()),
        "required_backend_version_present": REQUIRED_BACKEND_VERSION in source_without_comments,
        "known_stwo_backend_versions": backend_versions,
    }


def fixture_profile(program_path: pathlib.Path = LINEAR_BLOCK_V4_PROGRAM) -> dict[str, Any]:
    source = _read_text(program_path)
    memory_cells = _extract_first_match_int(source, r"(?im)^\.memory\s+(\d+)\s*$", ".memory size")
    instruction_lines = []
    for raw_line in source.splitlines():
        stripped = raw_line.split(";", 1)[0].split("#", 1)[0].strip()
        if not stripped or stripped.startswith(".") or stripped.endswith(":"):
            continue
        instruction_lines.append(stripped)
    mul_memory_ops = sum(1 for line in instruction_lines if line.upper().startswith("MULM "))
    return {
        "program_path": _display_path(program_path),
        "program_sha256": sha256_file(program_path),
        "memory_cells": memory_cells,
        "instruction_count": len(instruction_lines),
        "mul_memory_ops": mul_memory_ops,
    }


def classify_surface(
    target: dict[str, Any],
    tvm_limits: dict[str, Any],
    prover_gates: dict[str, Any],
    fixture: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    estimated_weight_scalars = int(target["estimated_weight_scalars"])
    estimated_linear_muls = int(target["estimated_linear_muls"])
    memory_limit = int(tvm_limits["max_addressable_memory_cells"])
    pc_horizon = int(tvm_limits["pc_horizon"])
    limits_are_current = tvm_limits.get("limits_are_current") is True

    if not limits_are_current:
        blockers.append(
            {
                "id": "unsupported_limit_scan",
                "why_it_matters": "the probe could not confirm the current TVM pc/address/immediate limits",
            }
        )
    if limits_are_current and estimated_weight_scalars > memory_limit:
        blockers.append(
            {
                "id": "weight_surface_exceeds_u8_memory_addressing",
                "current_limit_cells": memory_limit,
                "required_weight_scalars": estimated_weight_scalars,
                "why_it_matters": "a naive memory-resident d64 block cannot bind all gate/value/down weights in the current TVM memory surface",
            }
        )
    if limits_are_current and estimated_linear_muls > pc_horizon:
        blockers.append(
            {
                "id": "unrolled_mul_surface_exceeds_u8_pc_horizon",
                "current_pc_horizon": pc_horizon,
                "required_mul_events": estimated_linear_muls,
                "why_it_matters": "a direct one-instruction-per-scalar lowering cannot fit in the current u8 program-counter horizon",
            }
        )
    if fixture["mul_memory_ops"] < estimated_linear_muls:
        blockers.append(
            {
                "id": "current_fixture_is_toy_width",
                "fixture_mul_memory_ops": fixture["mul_memory_ops"],
                "required_mul_events": estimated_linear_muls,
                "why_it_matters": "the checked statement-bound block is useful for binding, not for matched d64 compute coverage",
            }
        )
    fixture_gate_detected = prover_gates.get("fixture_gate_detected") is True
    required_backend_version_present = prover_gates.get("required_backend_version_present") is True
    if not fixture_gate_detected or not required_backend_version_present:
        missing = []
        if not fixture_gate_detected:
            missing.append("confirmed fixture-gate scan")
        if not required_backend_version_present:
            missing.append(target["required_proof_backend_version"])
        blockers.append(
            {
                "id": "missing_parameterized_stwo_backend",
                "required_backend_version": target["required_proof_backend_version"],
                "missing": missing,
                "why_it_matters": "the probe should only report GO when it confirms both the current gate surface and the explicit d64 vector-block backend",
            }
        )
    if prover_gates.get("markers", {}).get("phase12_decoding_only"):
        blockers.append(
            {
                "id": "carry_aware_lane_is_decoding_family_only",
                "why_it_matters": "the scalable carry-aware proving lane cannot currently be reused as a generic RMSNorm/SwiGLU block prover",
            }
        )

    status = DECISION_GO if not blockers else DECISION_NO_GO
    return {
        "target_id": target["target_id"],
        "target_width": target["width"],
        "status": status,
        "reason": (
            "surface exposes a parameterized vector-block backend large enough for d64"
            if status == DECISION_GO
            else "direct TVM fixture growth is not the right implementation path for a matched d64 RMSNorm-SwiGLU block"
        ),
        "blockers": blockers,
        "weight_cells_over_memory_limit": (
            _ratio_or_inf(estimated_weight_scalars, memory_limit) if limits_are_current else float("inf")
        ),
        "mul_ops_over_pc_horizon": (
            _ratio_or_inf(estimated_linear_muls, pc_horizon) if limits_are_current else float("inf")
        ),
    }


def build_payload(
    *,
    instruction_path: pathlib.Path = INSTRUCTION_SOURCE,
    state_path: pathlib.Path = STATE_SOURCE,
    prover_source_path: pathlib.Path = ARITHMETIC_PROVER_SOURCE,
    fixture_path: pathlib.Path = LINEAR_BLOCK_V4_PROGRAM,
) -> dict[str, Any]:
    target = d64_target()
    tvm_limits = scan_tvm_limits(instruction_path=instruction_path, state_path=state_path)
    prover_gates = scan_prover_gates(prover_source_path)
    fixture = fixture_profile(fixture_path)
    classification = classify_surface(target, tvm_limits, prover_gates, fixture)
    return {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "decision": classification["status"],
        "research_issue": "https://github.com/omarespejel/provable-transformer-vm/issues/335",
        "target": target,
        "current_tvm_limits": tvm_limits,
        "current_prover_gates": prover_gates,
        "current_fixture_profile": fixture,
        "classification": classification,
        "summary": {
            "direct_fixture_growth": "NO_GO" if classification["blockers"] else "GO",
            "best_next_path": "parameterized vector-block AIR/export surface with committed weights, not a larger hand-written TVM fixture",
            "positive_result": "the next implementation blocker is now localized to representation/backend surface rather than statement binding",
            "first_target": "d64 before d128",
        },
        "next_required_work": [
            {
                "id": "weight_commitment_surface",
                "description": "Bind gate, value, and down projection weights through a table/vector commitment instead of TVM memory cells.",
            },
            {
                "id": "vector_row_domain",
                "description": "Represent the d64 block over vector/matrix rows rather than one TVM program counter step per scalar multiplication.",
            },
            {
                "id": "parameterized_backend_version",
                "description": f"Add an explicit {REQUIRED_BACKEND_VERSION} or equivalent backend version with verifier-facing statement commitments.",
            },
            {
                "id": "same_statement_comparison",
                "description": "Use the same model/input/output/config/weight receipt fields for Stwo and external proof-stack comparisons.",
            },
        ],
        "non_claims": [
            "This is not a d64 proof.",
            "This is not a performance benchmark.",
            "This does not claim Stwo cannot prove the target.",
            "This does not claim a full transformer-inference result.",
            "This does not weaken the existing width-4 statement-binding result.",
        ],
        "repro": {
            "git_commit": _git_commit(),
            "command": [
                "python3",
                "scripts/zkai_d64_rmsnorm_swiglu_surface_probe.py",
                "--write-json",
                "docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.json",
                "--write-tsv",
                "docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.tsv",
            ],
        },
    }


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    target = payload["target"]
    limits = payload["current_tvm_limits"]
    fixture = payload["current_fixture_profile"]
    classification = payload["classification"]
    return [
        {
            "target_width": target["width"],
            "decision": payload["decision"],
            "ff_dim": target["ff_dim"],
            "estimated_linear_muls": target["estimated_linear_muls"],
            "estimated_weight_scalars": target["estimated_weight_scalars"],
            "current_max_addressable_memory_cells": limits["max_addressable_memory_cells"],
            "current_pc_horizon": limits["pc_horizon"],
            "current_fixture_memory_cells": fixture["memory_cells"],
            "current_fixture_instruction_count": fixture["instruction_count"],
            "current_fixture_mul_memory_ops": fixture["mul_memory_ops"],
            "weight_cells_over_memory_limit": f"{classification['weight_cells_over_memory_limit']:.3f}",
            "mul_ops_over_pc_horizon": f"{classification['mul_ops_over_pc_horizon']:.3f}",
            "blocker_count": len(classification["blockers"]),
        }
    ]


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    try:
        if json_path is not None:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if tsv_path is not None:
            tsv_path.parent.mkdir(parents=True, exist_ok=True)
            with tsv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows_for_tsv(payload))
    except OSError as err:
        raise SurfaceProbeError(f"failed to write probe output: {err}") from err


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the JSON payload to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, help="write the JSON payload")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write the TSV summary")
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
        write_outputs(payload, args.write_json, args.write_tsv)
    except SurfaceProbeError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
