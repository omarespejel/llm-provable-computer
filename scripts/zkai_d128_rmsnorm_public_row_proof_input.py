#!/usr/bin/env python3
"""Build a d128 RMSNorm public-row proof input.

This is a parameterized normalization slice for the d=128 comparator target. It
proves only the public RMSNorm row relations and statement-bound commitments; it
is not a projection, activation, residual, composition, recursion, or full-block
proof.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pathlib
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv"
TARGET_JSON = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"

SCHEMA = "zkai-d128-native-rmsnorm-public-row-air-proof-input-v2"
DECISION = "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF"
OPERATION = "rmsnorm_public_rows"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
SOURCE_PROOF_BACKEND_VERSION = "synthetic-d128-rmsnorm-source-v1"
TARGET_COMMITMENT = "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18"
PROOF_NATIVE_PARAMETER_KIND = "d128-rmsnorm-public-row-synthetic-parameters-v1"
Q8_SCALE = 256
Q8_SEMANTIC_ABS_BOUND = 1_000_000
M31_MODULUS = (1 << 31) - 1
MAX_TARGET_JSON_BYTES = 2 * 1024 * 1024

INPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d128-input-activation:v1"
RMS_SCALE_DOMAIN = "ptvm:zkai:d128-rms-scale:v1"
RMSNORM_OUTPUT_ROW_DOMAIN = "ptvm:zkai:d128-rmsnorm-output-row:v1"
NORMALIZATION_CONFIG_DOMAIN = "ptvm:zkai:d128-rmsnorm-config:v1"
RMS_SCALE_LEAF_DOMAIN = "ptvm:zkai:d128:rms-scale-leaf:v1"
RMS_SCALE_TREE_DOMAIN = "ptvm:zkai:d128:rms-scale-tree:v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:d128-proof-native-parameter-commitment:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:d128-public-instance:v1"

NEXT_BACKEND_STEP = (
    "bridge RMSNorm-local normed rows into the next d128 transformer-block relation surface without relabeling them as the full output commitment"
)

NON_CLAIMS = [
    "not private witness privacy",
    "not full d128 block proof",
    "not projection, activation, SwiGLU, down-projection, or residual proof",
    "rms_q8 scalar sqrt inequality is AIR-native only for this public scalar row surface",
    "not proof that private witness rows open to proof_native_parameter_commitment beyond public rms_scale_tree_root recomputation",
    "not binding the full d128 output_activation_commitment from only RMSNorm local rows",
]

PROOF_VERIFIER_HARDENING = [
    "signed M31 bounds and checked i64 arithmetic for public-row relations",
    "exact integer isqrt recomputation without floating-point sqrt",
    "AIR-native bounded sqrt inequality via 17-bit nonnegative gap decompositions",
    "canonical d128 RMSNorm commitment domains checked before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "normalization config and RMS scale tree recomputed before proof verification",
    "local RMSNorm output row commitment recomputation before proof verification",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_rmsnorm_public_row_proof_input.py --write-json docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv",
    "just gate-fast",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_public_row_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_rmsnorm_public_row_proof --lib --features stwo-backend",
    "just gate",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "operation",
    "width",
    "row_count",
    "rms_q8",
    "sum_squares",
    "average_square_floor",
    "input_activation_commitment",
    "normalization_config_commitment",
    "rms_scale_tree_root",
    "rmsnorm_output_row_commitment",
    "rmsnorm_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class D128RmsnormPublicRowInputError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def blake2b_bytes(bytes_value: bytes, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(bytes_value)
    return digest.hexdigest()


def sequence_commitment(values: list[int], domain: str, width: int = WIDTH) -> str:
    values_json = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": [width],
            "values_sha256": sha256_bytes(values_json),
        },
        domain,
    )


def proof_native_parameter_commitment(target_commitment: str = TARGET_COMMITMENT) -> str:
    return blake2b_commitment(
        {"kind": PROOF_NATIVE_PARAMETER_KIND, "target_commitment": target_commitment},
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def public_instance_commitment(target_commitment: str = TARGET_COMMITMENT, width: int = WIDTH) -> str:
    return blake2b_commitment(
        {"operation": OPERATION, "target_commitment": target_commitment, "width": width},
        PUBLIC_INSTANCE_DOMAIN,
    )


def normalization_config_commitment(rms_q8: int, scale_commitment: str, width: int = WIDTH) -> str:
    return blake2b_commitment(
        {"rms_q8": rms_q8, "rms_square_rows": width, "scale_commitment": scale_commitment},
        NORMALIZATION_CONFIG_DOMAIN,
    )


def rms_scale_tree_root(scale_values: list[int]) -> str:
    if not scale_values:
        raise D128RmsnormPublicRowInputError("cannot commit empty RMS scale tree")
    level: list[str] = []
    for index, value in enumerate(scale_values):
        leaf = {"index": index, "kind": "rms_scale", "value_q8": value}
        level.append(blake2b_bytes(canonical_json_bytes(leaf), RMS_SCALE_LEAF_DOMAIN))
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level = []
        for left, right in zip(level[0::2], level[1::2], strict=True):
            next_level.append(blake2b_bytes(bytes.fromhex(left) + bytes.fromhex(right), RMS_SCALE_TREE_DOMAIN))
        level = next_level
    return f"blake2b-256:{level[0]}"


def require_commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("blake2b-256:"):
        raise D128RmsnormPublicRowInputError(f"{label} must be a blake2b-256 commitment")
    digest = value.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise D128RmsnormPublicRowInputError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def require_domain(payload: dict[str, Any], field: str, expected: str) -> None:
    if payload.get(field) != expected:
        raise D128RmsnormPublicRowInputError(f"domain mismatch: {field}")


def require_signed_q8(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128RmsnormPublicRowInputError(f"{label} must be an integer")
    if not (-Q8_SEMANTIC_ABS_BOUND <= value <= Q8_SEMANTIC_ABS_BOUND):
        raise D128RmsnormPublicRowInputError(f"{label} outside fixed-point q8 semantic bounds")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise D128RmsnormPublicRowInputError(f"{label} outside signed M31 bounds")


def load_target(path: pathlib.Path = TARGET_JSON) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise D128RmsnormPublicRowInputError(f"target evidence is not a regular file: {path}")
        raw = path.read_bytes()
        if len(raw) > MAX_TARGET_JSON_BYTES:
            raise D128RmsnormPublicRowInputError("target evidence exceeds max size")
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128RmsnormPublicRowInputError(f"failed to load target evidence: {err}") from err
    validate_target(payload)
    return payload


def validate_target(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D128RmsnormPublicRowInputError("target evidence must be an object")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise D128RmsnormPublicRowInputError("target summary missing")
    expected = {
        "target_width": WIDTH,
        "target_ff_dim": 512,
        "target_result": "GO_D128_LAYERWISE_COMPARATOR_TARGET_SPEC",
        "target_commitment": TARGET_COMMITMENT,
    }
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            raise D128RmsnormPublicRowInputError(f"target summary mismatch: {field}")


def build_vectors() -> tuple[list[int], list[int]]:
    input_q8 = [((index * 13 + 7) % 193) - 96 for index in range(WIDTH)]
    rms_scale_q8 = [232 + ((index * 19 + 5) % 49) for index in range(WIDTH)]
    for label, values in (("input", input_q8), ("RMS scale", rms_scale_q8)):
        for index, value in enumerate(values):
            require_signed_q8(value, f"{label} {index}")
    return input_q8, rms_scale_q8


def build_rows(input_q8: list[int], rms_scale_q8: list[int]) -> tuple[list[dict[str, int]], int, int, int]:
    if len(input_q8) != WIDTH or len(rms_scale_q8) != WIDTH:
        raise D128RmsnormPublicRowInputError("vector length mismatch")
    sum_squares = sum(value * value for value in input_q8)
    average_square_floor = sum_squares // WIDTH
    rms_q8 = math.isqrt(average_square_floor)
    if rms_q8 <= 0:
        raise D128RmsnormPublicRowInputError("rms_q8 must be positive")
    rows = []
    for index, (input_value, scale_value) in enumerate(zip(input_q8, rms_scale_q8, strict=True)):
        input_square = input_value * input_value
        scaled_product = input_value * scale_value
        scaled_floor, scale_remainder = divmod(scaled_product, Q8_SCALE)
        scaled_floor_product = scaled_floor * Q8_SCALE
        normed_q8, norm_remainder = divmod(scaled_floor_product, rms_q8)
        for label, value in (
            ("input square", input_square),
            ("scaled floor", scaled_floor),
            ("scale remainder", scale_remainder),
            ("normed q8", normed_q8),
            ("norm remainder", norm_remainder),
        ):
            require_signed_q8(value, f"{label} {index}")
        rows.append(
            {
                "index": index,
                "input_q8": input_value,
                "rms_scale_q8": scale_value,
                "input_square": input_square,
                "scaled_floor": scaled_floor,
                "scale_remainder": scale_remainder,
                "normed_q8": normed_q8,
                "norm_remainder": norm_remainder,
                "rms_q8": rms_q8,
            }
        )
    return rows, sum_squares, average_square_floor, rms_q8


def build_payload(target: dict[str, Any] | None = None) -> dict[str, Any]:
    target = load_target() if target is None else target
    validate_target(target)
    target_commitment = target["summary"]["target_commitment"]
    input_q8, rms_scale_q8 = build_vectors()
    rows, sum_squares, average_square_floor, rms_q8 = build_rows(input_q8, rms_scale_q8)
    normed_q8 = [row["normed_q8"] for row in rows]
    scale_commitment = sequence_commitment(rms_scale_q8, RMS_SCALE_DOMAIN)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "operation": OPERATION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_proof_backend_version": SOURCE_PROOF_BACKEND_VERSION,
        "input_activation_domain": INPUT_ACTIVATION_DOMAIN,
        "rms_scale_domain": RMS_SCALE_DOMAIN,
        "rmsnorm_output_row_domain": RMSNORM_OUTPUT_ROW_DOMAIN,
        "normalization_config_domain": NORMALIZATION_CONFIG_DOMAIN,
        "rms_scale_leaf_domain": RMS_SCALE_LEAF_DOMAIN,
        "rms_scale_tree_domain": RMS_SCALE_TREE_DOMAIN,
        "scale_q8": Q8_SCALE,
        "rms_q8": rms_q8,
        "sum_squares": sum_squares,
        "average_square_floor": average_square_floor,
        "proof_native_parameter_commitment": proof_native_parameter_commitment(target_commitment),
        "normalization_config_commitment": normalization_config_commitment(rms_q8, scale_commitment),
        "input_activation_commitment": sequence_commitment(input_q8, INPUT_ACTIVATION_DOMAIN),
        "rmsnorm_output_row_commitment": sequence_commitment(normed_q8, RMSNORM_OUTPUT_ROW_DOMAIN),
        "public_instance_commitment": public_instance_commitment(target_commitment, WIDTH),
        "statement_commitment": target_commitment,
        "rms_scale_tree_root": rms_scale_tree_root(rms_scale_q8),
        "rows": rows,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_payload(payload)
    return payload


def validate_row(row: Any, expected_index: int, rms_q8: int) -> None:
    if not isinstance(row, dict):
        raise D128RmsnormPublicRowInputError("row must be an object")
    expected_fields = {
        "index",
        "input_q8",
        "rms_scale_q8",
        "input_square",
        "scaled_floor",
        "scale_remainder",
        "normed_q8",
        "norm_remainder",
        "rms_q8",
    }
    if set(row) != expected_fields:
        raise D128RmsnormPublicRowInputError("row field set mismatch")
    if row["index"] != expected_index:
        raise D128RmsnormPublicRowInputError("row index mismatch")
    if row["rms_q8"] != rms_q8:
        raise D128RmsnormPublicRowInputError("row rms_q8 mismatch")
    for field in expected_fields - {"index"}:
        require_signed_q8(row[field], f"row {expected_index} {field}")
    if row["input_square"] != row["input_q8"] * row["input_q8"]:
        raise D128RmsnormPublicRowInputError("input square relation drift")
    scaled_product = row["input_q8"] * row["rms_scale_q8"]
    if scaled_product != row["scaled_floor"] * Q8_SCALE + row["scale_remainder"]:
        raise D128RmsnormPublicRowInputError("scaled floor relation drift")
    if not (0 <= row["scale_remainder"] < Q8_SCALE):
        raise D128RmsnormPublicRowInputError("scale remainder out of range")
    if row["scaled_floor"] * Q8_SCALE != row["normed_q8"] * row["rms_q8"] + row["norm_remainder"]:
        raise D128RmsnormPublicRowInputError("normed relation drift")
    if not (0 <= row["norm_remainder"] < row["rms_q8"]):
        raise D128RmsnormPublicRowInputError("norm remainder out of range")


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D128RmsnormPublicRowInputError("payload must be an object")
    expected_fields = {
        "schema",
        "decision",
        "operation",
        "target_id",
        "required_backend_version",
        "verifier_domain",
        "width",
        "row_count",
        "source_proof_backend_version",
        "input_activation_domain",
        "rms_scale_domain",
        "rmsnorm_output_row_domain",
        "normalization_config_domain",
        "rms_scale_leaf_domain",
        "rms_scale_tree_domain",
        "scale_q8",
        "rms_q8",
        "sum_squares",
        "average_square_floor",
        "proof_native_parameter_commitment",
        "normalization_config_commitment",
        "input_activation_commitment",
        "rmsnorm_output_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "rms_scale_tree_root",
        "rows",
        "non_claims",
        "proof_verifier_hardening",
        "next_backend_step",
        "validation_commands",
    }
    if set(payload) != expected_fields:
        raise D128RmsnormPublicRowInputError("payload field set mismatch")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "operation": OPERATION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_proof_backend_version": SOURCE_PROOF_BACKEND_VERSION,
        "scale_q8": Q8_SCALE,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise D128RmsnormPublicRowInputError(f"payload field mismatch: {field}")
    for field, expected in (
        ("input_activation_domain", INPUT_ACTIVATION_DOMAIN),
        ("rms_scale_domain", RMS_SCALE_DOMAIN),
        ("rmsnorm_output_row_domain", RMSNORM_OUTPUT_ROW_DOMAIN),
        ("normalization_config_domain", NORMALIZATION_CONFIG_DOMAIN),
        ("rms_scale_leaf_domain", RMS_SCALE_LEAF_DOMAIN),
        ("rms_scale_tree_domain", RMS_SCALE_TREE_DOMAIN),
    ):
        require_domain(payload, field, expected)
    for field in (
        "proof_native_parameter_commitment",
        "normalization_config_commitment",
        "input_activation_commitment",
        "rmsnorm_output_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "rms_scale_tree_root",
    ):
        require_commitment(payload[field], field)
    if payload["statement_commitment"] != TARGET_COMMITMENT:
        raise D128RmsnormPublicRowInputError("statement commitment drift")
    if payload["public_instance_commitment"] != public_instance_commitment(TARGET_COMMITMENT, WIDTH):
        raise D128RmsnormPublicRowInputError("public instance commitment drift")
    if payload["proof_native_parameter_commitment"] != proof_native_parameter_commitment(TARGET_COMMITMENT):
        raise D128RmsnormPublicRowInputError("proof-native parameter commitment drift")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D128RmsnormPublicRowInputError("row vector mismatch")
    for index, row in enumerate(rows):
        validate_row(row, index, payload["rms_q8"])
    input_values = [row["input_q8"] for row in rows]
    scale_values = [row["rms_scale_q8"] for row in rows]
    normed_values = [row["normed_q8"] for row in rows]
    sum_squares = sum(row["input_square"] for row in rows)
    if payload["sum_squares"] != sum_squares:
        raise D128RmsnormPublicRowInputError("sum squares drift")
    average_square_floor = sum_squares // WIDTH
    if payload["average_square_floor"] != average_square_floor:
        raise D128RmsnormPublicRowInputError("average square floor drift")
    if payload["rms_q8"] != math.isqrt(average_square_floor):
        raise D128RmsnormPublicRowInputError("rms_q8 drift")
    if payload["rms_q8"] <= 0:
        raise D128RmsnormPublicRowInputError("rms_q8 must be positive")
    if sequence_commitment(input_values, INPUT_ACTIVATION_DOMAIN) != payload["input_activation_commitment"]:
        raise D128RmsnormPublicRowInputError("input activation commitment drift")
    if sequence_commitment(normed_values, RMSNORM_OUTPUT_ROW_DOMAIN) != payload["rmsnorm_output_row_commitment"]:
        raise D128RmsnormPublicRowInputError("RMSNorm output row commitment drift")
    scale_commitment = sequence_commitment(scale_values, RMS_SCALE_DOMAIN)
    if normalization_config_commitment(payload["rms_q8"], scale_commitment) != payload["normalization_config_commitment"]:
        raise D128RmsnormPublicRowInputError("normalization config commitment drift")
    if rms_scale_tree_root(scale_values) != payload["rms_scale_tree_root"]:
        raise D128RmsnormPublicRowInputError("RMS scale tree root drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    full_output_placeholder = payload["statement_commitment"]
    return [
        {
            "target_id": payload["target_id"],
            "decision": payload["decision"],
            "operation": payload["operation"],
            "width": payload["width"],
            "row_count": payload["row_count"],
            "rms_q8": payload["rms_q8"],
            "sum_squares": payload["sum_squares"],
            "average_square_floor": payload["average_square_floor"],
            "input_activation_commitment": payload["input_activation_commitment"],
            "normalization_config_commitment": payload["normalization_config_commitment"],
            "rms_scale_tree_root": payload["rms_scale_tree_root"],
            "rmsnorm_output_row_commitment": payload["rmsnorm_output_row_commitment"],
            "rmsnorm_relabels_full_output": str(payload["rmsnorm_output_row_commitment"] == full_output_placeholder).lower(),
            "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            "next_backend_step": payload["next_backend_step"],
        }
    ]


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128RmsnormPublicRowInputError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128RmsnormPublicRowInputError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128RmsnormPublicRowInputError(f"output path must not be a directory: {path}")
    parent = resolved.parent
    if parent.exists() and not parent.is_dir():
        raise D128RmsnormPublicRowInputError(f"output parent is not a directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _fsync_parent_directories(paths: list[pathlib.Path]) -> None:
    seen: set[pathlib.Path] = set()
    for path in paths:
        parent = path.resolve().parent
        if parent in seen:
            continue
        seen.add(parent)
        flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
        try:
            fd = os.open(parent, flags)
        except OSError:
            continue
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _atomic_write_text(path: pathlib.Path, text: str) -> pathlib.Path:
    resolved = _assert_repo_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=resolved.parent, delete=False) as handle:
        tmp = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(tmp, resolved)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return resolved


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    written: list[pathlib.Path] = []
    if json_path is not None:
        written.append(_atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"))
    if tsv_path is not None:
        from io import StringIO

        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_for_tsv(payload, validated=True))
        written.append(_atomic_write_text(tsv_path, buffer.getvalue()))
    _fsync_parent_directories(written)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-json", type=pathlib.Path, default=TARGET_JSON)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_target(args.target_json))
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    summary = {
        "schema": SCHEMA,
        "decision": payload["decision"],
        "target_id": payload["target_id"],
        "operation": payload["operation"],
        "width": payload["width"],
        "row_count": payload["row_count"],
        "rms_q8": payload["rms_q8"],
        "rmsnorm_output_row_commitment": payload["rmsnorm_output_row_commitment"],
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
