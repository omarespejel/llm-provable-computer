#!/usr/bin/env python3
"""JSTprove/Remainder shape probe for small transformer-adjacent ONNX fixtures.

This is an engineering probe, not a performance benchmark and not a JSTprove
security audit. It asks which tiny operator shapes can be compiled, witnessed,
proved, and verified by a real JSTprove/Remainder binary.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-jstprove-shape-probe-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-jstprove-shape-probe-2026-05.tsv"

SCHEMA = "zkai-jstprove-shape-probe-v1"
DECISION = "GO_OPERATOR_SUPPORT_SPLIT_NOT_TRANSFORMER_PROOF"
SOURCE_DATE_EPOCH_DEFAULT = 0
DEFAULT_WORK_DIR = pathlib.Path(os.environ.get("ZKAI_JSTPROVE_SHAPE_WORK_DIR", "/tmp/zkai-jstprove-shape-probe"))
JSTPROVE_BIN_ENV = "ZKAI_JSTPROVE_REMAINDER_BIN"
GIT_COMMIT_ENV = "ZKAI_JSTPROVE_SHAPE_PROBE_GIT_COMMIT"
JSTPROVE_COMMIT = "7c3cbbee83aaa01adde700673f00e317a4e902f9"
REMAINDER_COMMIT = "06a5f406"
OPSET = 17

EXPECTED_FIXTURE_ORDER = (
    "tiny_gemm",
    "tiny_gemm_add",
    "tiny_gemm_residual_add",
    "tiny_gemm_layernorm",
    "tiny_gemm_batchnorm",
    "tiny_gemm_relu",
    "tiny_gemm_softmax",
    "tiny_matmul_residual_add",
)
EXPECTED_STATUS = {
    "tiny_gemm": "GO",
    "tiny_gemm_add": "GO",
    "tiny_gemm_residual_add": "GO",
    "tiny_gemm_layernorm": "GO",
    "tiny_gemm_batchnorm": "GO",
    "tiny_gemm_relu": "NO_GO",
    "tiny_gemm_softmax": "NO_GO",
    "tiny_matmul_residual_add": "NO_GO",
}
EXPECTED_FAILURE_KIND = {
    "tiny_gemm_relu": "range_check_capacity",
    "tiny_gemm_softmax": "unconstrained_backend_op",
    "tiny_matmul_residual_add": "unsupported_witness_op",
}
EXPECTED_GO_TRANSFORMER_ADJACENT = {
    "tiny_gemm_residual_add",
    "tiny_gemm_layernorm",
    "tiny_gemm_batchnorm",
}
TSV_COLUMNS = (
    "fixture",
    "gate",
    "op_sequence",
    "transformer_relevance",
    "status",
    "failed_step",
    "failure_kind",
    "proof_bytes",
    "model_bytes",
    "onnx_bytes",
    "prove_seconds",
    "verify_seconds",
    "primary_observation",
)


class JstproveShapeProbeError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise JstproveShapeProbeError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise JstproveShapeProbeError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    override = os.environ.get(GIT_COMMIT_ENV)
    if override and override.strip():
        normalized = override.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{7,40}", normalized):
            raise JstproveShapeProbeError(f"{GIT_COMMIT_ENV} must be a 7-40 character hex SHA")
        return normalized
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def fixture_catalog() -> list[dict[str, str]]:
    return [
        {
            "fixture": "tiny_gemm",
            "op_sequence": "Gemm",
            "transformer_relevance": "linear_projection_baseline",
            "primary_observation": "baseline tiny linear projection proves and verifies",
        },
        {
            "fixture": "tiny_gemm_add",
            "op_sequence": "Gemm -> Add",
            "transformer_relevance": "linear_projection_plus_bias_like_add",
            "primary_observation": "extra Add layer proves and verifies",
        },
        {
            "fixture": "tiny_gemm_residual_add",
            "op_sequence": "Gemm(width-preserving) -> Add(input)",
            "transformer_relevance": "linear_projection_plus_residual_add",
            "primary_observation": "residual-style Add proves and verifies",
        },
        {
            "fixture": "tiny_gemm_layernorm",
            "op_sequence": "Gemm(width-preserving) -> LayerNormalization",
            "transformer_relevance": "normalization_after_projection",
            "primary_observation": "LayerNormalization-style tiny shape proves and verifies",
        },
        {
            "fixture": "tiny_gemm_batchnorm",
            "op_sequence": "Gemm -> BatchNormalization",
            "transformer_relevance": "normalization_like_operator_after_projection",
            "primary_observation": "normalization-like tiny shape proves and verifies",
        },
        {
            "fixture": "tiny_gemm_relu",
            "op_sequence": "Gemm -> Relu",
            "transformer_relevance": "activation_or_range_check_pressure",
            "primary_observation": "Relu witness hits Remainder range-check capacity",
        },
        {
            "fixture": "tiny_gemm_softmax",
            "op_sequence": "Gemm(width-preserving) -> Softmax",
            "transformer_relevance": "attention_normalization_pressure",
            "primary_observation": "Softmax witness is generated but proof construction refuses an unconstrained op",
        },
        {
            "fixture": "tiny_matmul_residual_add",
            "op_sequence": "MatMul -> Add(input)",
            "transformer_relevance": "literal_matmul_projection_plus_residual_add",
            "primary_observation": "MatMul compiles but witness generation reports unsupported MatMul",
        },
    ]


def _import_generation_deps():
    try:
        import msgpack  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
        import onnx  # type: ignore[import-not-found]
        from onnx import TensorProto, helper, numpy_helper  # type: ignore[import-not-found]
    except ImportError as err:
        raise JstproveShapeProbeError(
            "shape generation requires onnx, numpy, and msgpack; run with the JSTprove ONNX Python environment"
        ) from err
    return msgpack, np, onnx, TensorProto, helper, numpy_helper


def write_fixture(fixture: str, out_dir: pathlib.Path) -> dict[str, int]:
    msgpack, np, onnx, TensorProto, helper, numpy_helper = _import_generation_deps()
    out_dir.mkdir(parents=True, exist_ok=True)

    input_value = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 2])
    input_data = [1.0, 2.0]

    w1 = numpy_helper.from_array(np.array([[0.5], [1.5]], dtype=np.float32), name="W")
    b1 = numpy_helper.from_array(np.array([0.25], dtype=np.float32), name="B")
    y1 = helper.make_tensor_value_info("Z", TensorProto.FLOAT, [1, 1])

    w2 = numpy_helper.from_array(np.array([[0.5, -0.25], [1.5, 0.75]], dtype=np.float32), name="W2")
    b2 = numpy_helper.from_array(np.array([0.25, -0.5], dtype=np.float32), name="B2")
    y2 = helper.make_tensor_value_info("Z", TensorProto.FLOAT, [1, 2])

    if fixture == "tiny_gemm":
        nodes = [helper.make_node("Gemm", ["input", "W", "B"], ["Z"])]
        outputs = [y1]
        initializers = [w1, b1]
    elif fixture == "tiny_gemm_add":
        c = numpy_helper.from_array(np.array([0.125], dtype=np.float32), name="C")
        nodes = [helper.make_node("Gemm", ["input", "W", "B"], ["Y"]), helper.make_node("Add", ["Y", "C"], ["Z"])]
        outputs = [y1]
        initializers = [w1, b1, c]
    elif fixture == "tiny_gemm_residual_add":
        nodes = [
            helper.make_node("Gemm", ["input", "W2", "B2"], ["Y"]),
            helper.make_node("Add", ["Y", "input"], ["Z"]),
        ]
        outputs = [y2]
        initializers = [w2, b2]
    elif fixture == "tiny_gemm_layernorm":
        gamma = numpy_helper.from_array(np.ones(2, dtype=np.float32), name="gamma")
        beta = numpy_helper.from_array(np.zeros(2, dtype=np.float32), name="beta")
        nodes = [
            helper.make_node("Gemm", ["input", "W2", "B2"], ["Y"]),
            helper.make_node("LayerNormalization", ["Y", "gamma", "beta"], ["Z"], axis=-1, epsilon=1e-5),
        ]
        outputs = [y2]
        initializers = [w2, b2, gamma, beta]
    elif fixture == "tiny_gemm_batchnorm":
        scale = numpy_helper.from_array(np.array([1.0], dtype=np.float32), name="scale")
        bias = numpy_helper.from_array(np.array([0.0], dtype=np.float32), name="bias")
        mean = numpy_helper.from_array(np.array([0.0], dtype=np.float32), name="mean")
        var = numpy_helper.from_array(np.array([1.0], dtype=np.float32), name="var")
        nodes = [
            helper.make_node("Gemm", ["input", "W", "B"], ["Y"]),
            helper.make_node("BatchNormalization", ["Y", "scale", "bias", "mean", "var"], ["Z"], epsilon=1e-5),
        ]
        outputs = [y1]
        initializers = [w1, b1, scale, bias, mean, var]
    elif fixture == "tiny_gemm_relu":
        nodes = [helper.make_node("Gemm", ["input", "W", "B"], ["Y"]), helper.make_node("Relu", ["Y"], ["Z"])]
        outputs = [y1]
        initializers = [w1, b1]
    elif fixture == "tiny_gemm_softmax":
        nodes = [
            helper.make_node("Gemm", ["input", "W2", "B2"], ["Y"]),
            helper.make_node("Softmax", ["Y"], ["Z"], axis=-1),
        ]
        outputs = [y2]
        initializers = [w2, b2]
    elif fixture == "tiny_matmul_residual_add":
        nodes = [
            helper.make_node("MatMul", ["input", "W2"], ["Y"]),
            helper.make_node("Add", ["Y", "input"], ["Z"]),
        ]
        outputs = [y2]
        initializers = [w2]
    else:
        raise JstproveShapeProbeError(f"unknown fixture: {fixture}")

    graph = helper.make_graph(nodes, f"{fixture}_graph", [input_value], outputs, initializer=initializers)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", OPSET)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx_path = out_dir / f"{fixture}.onnx"
    input_path = out_dir / "input.msgpack"
    onnx.save(model, onnx_path)
    input_path.write_bytes(msgpack.packb({"input": input_data}))
    return {"onnx_bytes": onnx_path.stat().st_size, "input_bytes": input_path.stat().st_size}


def _resolve_jstprove_binary(raw: str | None = None) -> pathlib.Path:
    value = raw or os.environ.get(JSTPROVE_BIN_ENV, "jstprove-remainder")
    path = pathlib.Path(value)
    if path.is_absolute():
        if not path.is_file():
            raise JstproveShapeProbeError(f"JSTprove Remainder verifier is missing: {value}")
        if not os.access(path, os.X_OK):
            raise JstproveShapeProbeError(f"JSTprove Remainder verifier is not executable: {value}")
        return path
    resolved = shutil.which(value)
    if resolved is None:
        raise JstproveShapeProbeError(f"JSTprove Remainder verifier is not on PATH: {value}")
    return pathlib.Path(resolved)


def _run_command(command: list[str], *, cwd: pathlib.Path, timeout: int = 240) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        return {
            "returncode": "timeout",
            "seconds": timeout,
            "stdout_excerpt": "",
            "stderr_excerpt": str(err)[:1000],
        }
    except OSError as err:
        raise JstproveShapeProbeError(f"failed to start JSTprove command: {err}") from err
    return {
        "returncode": completed.returncode,
        "seconds": round(time.perf_counter() - started, 6),
        "stdout_excerpt": completed.stdout.strip()[:1000],
        "stderr_excerpt": completed.stderr.strip()[:1000],
    }


def classify_failure(step: str | None, message: str) -> str:
    lowered = message.lower()
    if "range-check capacity" in lowered:
        return "range_check_capacity"
    if "not yet constrained" in lowered or "unconstrained" in lowered:
        return "unconstrained_backend_op"
    if "unsupported op type matmul" in lowered:
        return "unsupported_witness_op"
    if "unsupported" in lowered:
        return "unsupported_backend_op"
    if step is None:
        return ""
    return "external_tool_error"


def _step_seconds(steps: list[dict[str, Any]], step: str) -> str:
    for item in steps:
        if item["step"] == step:
            return f"{float(item['seconds']):.6f}"
    return "NA"


def run_fixture(fixture: str, *, jstprove_bin: pathlib.Path, work_dir: pathlib.Path) -> dict[str, Any]:
    fixture_dir = work_dir / fixture
    if fixture_dir.exists():
        shutil.rmtree(fixture_dir)
    fixture_dir.mkdir(parents=True)
    sizes = write_fixture(fixture, fixture_dir)
    model = fixture_dir / "model.msgpack"
    witness = fixture_dir / "witness.msgpack"
    proof = fixture_dir / "proof.msgpack"
    onnx_path = fixture_dir / f"{fixture}.onnx"
    input_path = fixture_dir / "input.msgpack"

    steps: list[dict[str, Any]] = []
    commands = [
        ("compile", [str(jstprove_bin), "compile", "--model", str(onnx_path), "--output", str(model)]),
        ("witness", [str(jstprove_bin), "witness", "--model", str(model), "--input", str(input_path), "--output", str(witness)]),
        ("prove", [str(jstprove_bin), "prove", "--model", str(model), "--witness", str(witness), "--output", str(proof)]),
        ("verify", [str(jstprove_bin), "--quiet", "verify", "--model", str(model), "--proof", str(proof), "--input", str(input_path)]),
    ]
    failed_step: str | None = None
    failure_message = ""
    for step, command in commands:
        result = _run_command(command, cwd=fixture_dir)
        result["step"] = step
        result["argv"] = [pathlib.Path(part).name if str(jstprove_bin) == part else part for part in command]
        steps.append(result)
        if result["returncode"] != 0:
            failed_step = step
            failure_message = "\n".join(
                item for item in (str(result.get("stderr_excerpt", "")), str(result.get("stdout_excerpt", ""))) if item
            )
            break

    status = "GO" if failed_step is None else "NO_GO"
    failure_kind = "" if status == "GO" else classify_failure(failed_step, failure_message)
    catalog = {item["fixture"]: item for item in fixture_catalog()}[fixture]
    gate = "GO_CHECKED_SMALL_SHAPE" if status == "GO" else f"NO_GO_{failure_kind.upper()}"
    return {
        "fixture": fixture,
        "gate": gate,
        "op_sequence": catalog["op_sequence"],
        "transformer_relevance": catalog["transformer_relevance"],
        "status": status,
        "failed_step": failed_step or "",
        "failure_kind": failure_kind,
        "proof_bytes": proof.stat().st_size if proof.exists() else None,
        "model_bytes": model.stat().st_size if model.exists() else None,
        "onnx_bytes": sizes["onnx_bytes"],
        "input_bytes": sizes["input_bytes"],
        "prove_seconds": _step_seconds(steps, "prove"),
        "verify_seconds": _step_seconds(steps, "verify"),
        "primary_observation": catalog["primary_observation"],
        "steps": steps,
    }


def run_shape_probe(*, jstprove_bin: pathlib.Path | None = None, work_dir: pathlib.Path | None = None) -> dict[str, Any]:
    resolved_bin = jstprove_bin or _resolve_jstprove_binary()
    raw_work_dir = work_dir or DEFAULT_WORK_DIR
    raw_work_dir.mkdir(parents=True, exist_ok=True)
    results = [
        run_fixture(fixture, jstprove_bin=resolved_bin, work_dir=raw_work_dir) for fixture in EXPECTED_FIXTURE_ORDER
    ]
    return build_payload(results, jstprove_bin=resolved_bin, work_dir=raw_work_dir)


def build_payload(results: list[dict[str, Any]], *, jstprove_bin: pathlib.Path, work_dir: pathlib.Path) -> dict[str, Any]:
    go_results = [item for item in results if item["status"] == "GO"]
    no_go_results = [item for item in results if item["status"] == "NO_GO"]
    payload = {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": DECISION,
        "question": "Which tiny transformer-adjacent ONNX shapes does JSTprove/Remainder prove today?",
        "jstprove": {
            "upstream_commit": JSTPROVE_COMMIT,
            "remainder_dependency_commit": REMAINDER_COMMIT,
            "binary": str(jstprove_bin),
        },
        "work_dir": str(work_dir),
        "fixture_catalog": fixture_catalog(),
        "results": results,
        "results_commitment": blake2b_commitment(results, "ptvm:zkai:jstprove-shape-results:v1"),
        "conclusion": {
            "go_count": len(go_results),
            "no_go_count": len(no_go_results),
            "go_transformer_adjacent_fixtures": [
                item["fixture"] for item in go_results if item["fixture"] in EXPECTED_GO_TRANSFORMER_ADJACENT
            ],
            "paper_usage": "engineering_context_only_not_transformer_proof_or_performance_benchmark",
            "interpretation": (
                "JSTprove/Remainder can prove tiny projection, residual-add, and normalization-shaped fixtures, "
                "but the checked Softmax, ReLU, and literal MatMul variants expose separate backend/operator blockers."
            ),
        },
        "non_claims": [
            "not a JSTprove security finding",
            "not a full transformer proof",
            "not a performance benchmark",
            "not evidence that larger shapes remain small",
            "not evidence that unsupported shapes are impossible in future JSTprove versions",
            "not a Tablero result",
        ],
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    expected_fields = {
        "schema",
        "generated_at",
        "git_commit",
        "decision",
        "question",
        "jstprove",
        "work_dir",
        "fixture_catalog",
        "results",
        "results_commitment",
        "conclusion",
        "non_claims",
    }
    expected_conclusion_fields = {
        "go_count",
        "no_go_count",
        "go_transformer_adjacent_fixtures",
        "paper_usage",
        "interpretation",
    }
    if set(payload) != expected_fields:
        raise JstproveShapeProbeError("payload field set mismatch")
    if payload["schema"] != SCHEMA:
        raise JstproveShapeProbeError("schema drift")
    if payload["decision"] != DECISION:
        raise JstproveShapeProbeError("decision drift")
    if payload["results_commitment"] != blake2b_commitment(payload["results"], "ptvm:zkai:jstprove-shape-results:v1"):
        raise JstproveShapeProbeError("results commitment mismatch")
    catalog_names = [item.get("fixture") for item in payload["fixture_catalog"]]
    if catalog_names != list(EXPECTED_FIXTURE_ORDER):
        raise JstproveShapeProbeError("fixture catalog drift")
    result_names = [item.get("fixture") for item in payload["results"]]
    if result_names != list(EXPECTED_FIXTURE_ORDER):
        raise JstproveShapeProbeError("fixture result drift")

    for result in payload["results"]:
        fixture = result["fixture"]
        if result.get("status") != EXPECTED_STATUS[fixture]:
            raise JstproveShapeProbeError(f"{fixture} status drift")
        if result["status"] == "GO":
            if result.get("failed_step") or result.get("failure_kind"):
                raise JstproveShapeProbeError(f"{fixture} GO failure metadata drift")
            if not isinstance(result.get("proof_bytes"), int) or result["proof_bytes"] <= 0:
                raise JstproveShapeProbeError(f"{fixture} proof size missing")
            if result.get("gate") != "GO_CHECKED_SMALL_SHAPE":
                raise JstproveShapeProbeError(f"{fixture} gate drift")
        else:
            if result.get("failure_kind") != EXPECTED_FAILURE_KIND[fixture]:
                raise JstproveShapeProbeError(f"{fixture} failure kind drift")
            if not str(result.get("gate", "")).startswith("NO_GO_"):
                raise JstproveShapeProbeError(f"{fixture} gate drift")
            if not result.get("failed_step"):
                raise JstproveShapeProbeError(f"{fixture} missing failed step")

    conclusion = payload["conclusion"]
    if set(conclusion) != expected_conclusion_fields:
        raise JstproveShapeProbeError("conclusion field set mismatch")
    if conclusion["paper_usage"] != "engineering_context_only_not_transformer_proof_or_performance_benchmark":
        raise JstproveShapeProbeError("paper usage overclaim")
    if conclusion["go_count"] != 5 or conclusion["no_go_count"] != 3:
        raise JstproveShapeProbeError("summary count drift")
    if set(conclusion["go_transformer_adjacent_fixtures"]) != EXPECTED_GO_TRANSFORMER_ADJACENT:
        raise JstproveShapeProbeError("transformer-adjacent GO drift")
    required_non_claims = {
        "not a JSTprove security finding",
        "not a full transformer proof",
        "not a performance benchmark",
        "not a Tablero result",
    }
    if not required_non_claims.issubset(set(payload["non_claims"])):
        raise JstproveShapeProbeError("non-claim drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for result in payload["results"]:
        rows.append({column: result.get(column, "") for column in TSV_COLUMNS})
    return rows


def to_tsv(payload: dict[str, Any]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, dialect="excel-tab", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows_for_tsv(payload))
    return out.getvalue()


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            tmp.write(text)
            tmp_path = pathlib.Path(tmp.name)
        tmp_path.replace(path)
    except OSError as err:
        raise JstproveShapeProbeError(f"failed to write {path}: {err}") from err


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is not None:
        _atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if tsv_path is not None:
        _atomic_write_text(tsv_path, to_tsv(payload))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jstprove-bin", type=pathlib.Path, help=f"path to jstprove-remainder; defaults to ${JSTPROVE_BIN_ENV} or PATH")
    parser.add_argument("--work-dir", type=pathlib.Path, default=DEFAULT_WORK_DIR, help="temporary fixture/proof work directory")
    parser.add_argument("--write-json", type=pathlib.Path, help="write checked JSON evidence")
    parser.add_argument("--write-tsv", type=pathlib.Path, help="write checked TSV evidence")
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    binary = _resolve_jstprove_binary(str(args.jstprove_bin) if args.jstprove_bin else None)
    payload = run_shape_probe(jstprove_bin=binary, work_dir=args.work_dir)
    write_outputs(payload, args.write_json, args.write_tsv)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.write_json is None and args.write_tsv is None:
        print(to_tsv(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
