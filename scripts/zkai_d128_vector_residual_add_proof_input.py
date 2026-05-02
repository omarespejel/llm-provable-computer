#!/usr/bin/env python3
"""Build a d128 parameterized vector residual-add proof input.

This is the first real parameterized vector-block backend artifact. It proves
only the residual-add slice for a d=128 target shape. It does not claim RMSNorm,
projection, activation, down-projection, or full transformer-block coverage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-vector-residual-add-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-vector-residual-add-proof-2026-05.tsv"
TARGET_JSON = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"

SCHEMA = "zkai-vector-block-residual-add-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_VECTOR_BLOCK_RESIDUAL_ADD_AIR_PROOF"
OPERATION = "residual_add"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
SOURCE_PROOF_BACKEND_VERSION = "synthetic-d128-residual-delta-source-v1"
TARGET_COMMITMENT = "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18"
PROOF_NATIVE_PARAMETER_KIND = "d128-residual-add-synthetic-parameters-v1"
Q8_SEMANTIC_ABS_BOUND = 1024
M31_MODULUS = (1 << 31) - 1
MAX_TARGET_JSON_BYTES = 2 * 1024 * 1024

INPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d128-input-activation:v1"
RESIDUAL_DELTA_DOMAIN = "ptvm:zkai:d128-residual-delta:v1"
OUTPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d128-output-activation:v1"
RESIDUAL_ADD_ROW_DOMAIN = "ptvm:zkai:d128-residual-add-rows:v1"

NEXT_BACKEND_STEP = (
    "parameterize RMSNorm, projection, activation, and down-projection slices before claiming a full d128 transformer-block proof"
)

NON_CLAIMS = [
    "not a full transformer-block proof",
    "not RMSNorm, projection, activation, or down-projection proof",
    "not recursive composition",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not onchain deployment evidence",
]

PROOF_VERIFIER_HARDENING = [
    "pinned d128 target width checked before proof verification",
    "canonical d128 vector and row commitment domains checked before proof verification",
    "explicit power-of-two trace domain check before proving",
    "input activation commitment recomputation before proof verification",
    "residual-delta commitment recomputation before proof verification",
    "output activation commitment recomputation before proof verification",
    "residual-add row commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR residual-add relation for every checked output coordinate",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_vector_residual_add_proof_input.py --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv",
    "just gate-fast",
    "python3 -m unittest scripts.tests.test_zkai_d128_vector_residual_add_proof_input",
    "cargo +nightly-2025-07-14 test zkai_vector_block_residual_add_proof --lib --features stwo-backend",
    "just gate",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "operation",
    "width",
    "row_count",
    "input_activation_commitment",
    "residual_delta_commitment",
    "output_activation_commitment",
    "residual_add_row_commitment",
    "residual_delta_relabels_full_output",
    "input_relabels_output",
    "non_claims",
    "next_backend_step",
)


class D128VectorResidualAddInputError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def sequence_commitment(values: list[int], domain: str, width: int = WIDTH) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": [width],
            "values_sha256": sha256_hex(values),
        },
        domain,
    )


def rows_commitment(rows: list[dict[str, int]]) -> str:
    material = [[row["row_index"], row["input_q8"], row["residual_delta_q8"], row["output_q8"]] for row in rows]
    return blake2b_commitment(
        {
            "encoding": "vector_block_residual_add_rows_v1",
            "rows_sha256": sha256_hex(material),
            "shape": [len(rows), 4],
        },
        RESIDUAL_ADD_ROW_DOMAIN,
    )


def proof_native_parameter_commitment(target_commitment: str = TARGET_COMMITMENT) -> str:
    return blake2b_commitment(
        {"target_commitment": target_commitment, "kind": PROOF_NATIVE_PARAMETER_KIND},
        "ptvm:zkai:d128-proof-native-parameter-commitment:v1",
    )


def public_instance_commitment(target_commitment: str = TARGET_COMMITMENT, width: int = WIDTH) -> str:
    return blake2b_commitment(
        {"target_commitment": target_commitment, "operation": OPERATION, "width": width},
        "ptvm:zkai:d128-public-instance:v1",
    )


def require_commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("blake2b-256:"):
        raise D128VectorResidualAddInputError(f"{label} must be a blake2b-256 commitment")
    digest = value.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise D128VectorResidualAddInputError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def require_signed_q8(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128VectorResidualAddInputError(f"{label} must be an integer")
    if not (-Q8_SEMANTIC_ABS_BOUND <= value <= Q8_SEMANTIC_ABS_BOUND):
        raise D128VectorResidualAddInputError(f"{label} outside fixed-point q8 semantic bounds")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise D128VectorResidualAddInputError(f"{label} outside signed M31 bounds")


def load_target(path: pathlib.Path = TARGET_JSON) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise D128VectorResidualAddInputError(f"target evidence is not a regular file: {path}")
        raw = path.read_bytes()
        if len(raw) > MAX_TARGET_JSON_BYTES:
            raise D128VectorResidualAddInputError("target evidence exceeds max size")
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128VectorResidualAddInputError(f"failed to load target evidence: {err}") from err
    if not isinstance(payload, dict):
        raise D128VectorResidualAddInputError("target evidence must be an object")
    validate_target(payload)
    return payload


def validate_target(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D128VectorResidualAddInputError("target evidence must be an object")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise D128VectorResidualAddInputError("target summary missing")
    expected = {
        "target_width": WIDTH,
        "target_ff_dim": 512,
        "target_result": "GO_D128_LAYERWISE_COMPARATOR_TARGET_SPEC",
        "local_proof_result": "NO_GO_LOCAL_D128_PROOF_ARTIFACT_MISSING",
        "target_commitment": TARGET_COMMITMENT,
    }
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            raise D128VectorResidualAddInputError(f"target summary mismatch: {field}")


def build_vectors() -> tuple[list[int], list[int], list[int]]:
    input_q8 = [((index * 13 + 7) % 193) - 96 for index in range(WIDTH)]
    residual_delta_q8 = [((index * 17 + 11) % 97) - 48 for index in range(WIDTH)]
    output_q8 = [base + delta for base, delta in zip(input_q8, residual_delta_q8, strict=True)]
    for label, values in (
        ("input", input_q8),
        ("residual delta", residual_delta_q8),
        ("output", output_q8),
    ):
        for index, value in enumerate(values):
            require_signed_q8(value, f"{label} {index}")
    return input_q8, residual_delta_q8, output_q8


def build_rows(input_q8: list[int], residual_delta_q8: list[int]) -> list[dict[str, int]]:
    if len(input_q8) != WIDTH or len(residual_delta_q8) != WIDTH:
        raise D128VectorResidualAddInputError("vector length mismatch")
    rows = []
    for row_index, (base, delta) in enumerate(zip(input_q8, residual_delta_q8, strict=True)):
        output = base + delta
        require_signed_q8(output, f"output {row_index}")
        rows.append({"row_index": row_index, "input_q8": base, "residual_delta_q8": delta, "output_q8": output})
    return rows


def build_payload(target: dict[str, Any] | None = None) -> dict[str, Any]:
    target = load_target() if target is None else target
    validate_target(target)
    target_commitment = target["summary"]["target_commitment"]
    input_q8, residual_delta_q8, output_q8 = build_vectors()
    rows = build_rows(input_q8, residual_delta_q8)
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
        "residual_delta_domain": RESIDUAL_DELTA_DOMAIN,
        "output_activation_domain": OUTPUT_ACTIVATION_DOMAIN,
        "residual_add_row_domain": RESIDUAL_ADD_ROW_DOMAIN,
        "input_activation_commitment": sequence_commitment(input_q8, INPUT_ACTIVATION_DOMAIN),
        "residual_delta_commitment": sequence_commitment(residual_delta_q8, RESIDUAL_DELTA_DOMAIN),
        "output_activation_commitment": sequence_commitment(output_q8, OUTPUT_ACTIVATION_DOMAIN),
        "residual_add_row_commitment": rows_commitment(rows),
        "proof_native_parameter_commitment": proof_native_parameter_commitment(target_commitment),
        "public_instance_commitment": public_instance_commitment(target_commitment, WIDTH),
        "statement_commitment": target_commitment,
        "input_q8": input_q8,
        "residual_delta_q8": residual_delta_q8,
        "output_q8": output_q8,
        "rows": rows,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D128VectorResidualAddInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "operation", "target_id", "required_backend_version", "verifier_domain", "width", "row_count",
        "source_proof_backend_version", "input_activation_domain", "residual_delta_domain", "output_activation_domain",
        "residual_add_row_domain", "input_activation_commitment", "residual_delta_commitment", "output_activation_commitment",
        "residual_add_row_commitment", "proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment",
        "input_q8", "residual_delta_q8", "output_q8", "rows", "non_claims", "proof_verifier_hardening", "next_backend_step",
        "validation_commands",
    }
    if set(payload) != expected_fields:
        raise D128VectorResidualAddInputError("payload field set mismatch")
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
        "input_activation_domain": INPUT_ACTIVATION_DOMAIN,
        "residual_delta_domain": RESIDUAL_DELTA_DOMAIN,
        "output_activation_domain": OUTPUT_ACTIVATION_DOMAIN,
        "residual_add_row_domain": RESIDUAL_ADD_ROW_DOMAIN,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise D128VectorResidualAddInputError(f"payload field mismatch: {field}")
    for field in (
        "input_activation_commitment", "residual_delta_commitment", "output_activation_commitment",
        "residual_add_row_commitment", "proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment",
    ):
        require_commitment(payload[field], field)
    if payload["statement_commitment"] != TARGET_COMMITMENT:
        raise D128VectorResidualAddInputError("statement commitment drift")
    if payload["public_instance_commitment"] != public_instance_commitment(TARGET_COMMITMENT, WIDTH):
        raise D128VectorResidualAddInputError("public instance commitment drift")
    if payload["proof_native_parameter_commitment"] != proof_native_parameter_commitment(TARGET_COMMITMENT):
        raise D128VectorResidualAddInputError("proof-native parameter commitment drift")
    if payload["residual_delta_commitment"] == payload["output_activation_commitment"]:
        raise D128VectorResidualAddInputError("residual delta commitment relabeled as full output commitment")
    if payload["input_activation_commitment"] == payload["output_activation_commitment"]:
        raise D128VectorResidualAddInputError("input activation commitment relabeled as output activation commitment")
    input_q8 = payload["input_q8"]
    residual_delta_q8 = payload["residual_delta_q8"]
    output_q8 = payload["output_q8"]
    rows = payload["rows"]
    for label, values in (("input", input_q8), ("residual delta", residual_delta_q8), ("output", output_q8)):
        if not isinstance(values, list) or len(values) != WIDTH:
            raise D128VectorResidualAddInputError(f"{label} vector mismatch")
        for index, value in enumerate(values):
            require_signed_q8(value, f"{label} {index}")
    if sequence_commitment(input_q8, INPUT_ACTIVATION_DOMAIN) != payload["input_activation_commitment"]:
        raise D128VectorResidualAddInputError("input activation commitment drift")
    if sequence_commitment(residual_delta_q8, RESIDUAL_DELTA_DOMAIN) != payload["residual_delta_commitment"]:
        raise D128VectorResidualAddInputError("residual delta commitment drift")
    if sequence_commitment(output_q8, OUTPUT_ACTIVATION_DOMAIN) != payload["output_activation_commitment"]:
        raise D128VectorResidualAddInputError("output activation commitment drift")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D128VectorResidualAddInputError("row vector mismatch")
    recomputed_rows = build_rows(input_q8, residual_delta_q8)
    if rows != recomputed_rows:
        raise D128VectorResidualAddInputError("residual-add row relation drift")
    if [row["output_q8"] for row in rows] != output_q8:
        raise D128VectorResidualAddInputError("output activation row drift")
    if rows_commitment(rows) != payload["residual_add_row_commitment"]:
        raise D128VectorResidualAddInputError("residual-add row commitment drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    return [{
        "target_id": payload["target_id"],
        "decision": payload["decision"],
        "operation": payload["operation"],
        "width": payload["width"],
        "row_count": payload["row_count"],
        "input_activation_commitment": payload["input_activation_commitment"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "output_activation_commitment": payload["output_activation_commitment"],
        "residual_add_row_commitment": payload["residual_add_row_commitment"],
        "residual_delta_relabels_full_output": str(payload["residual_delta_commitment"] == payload["output_activation_commitment"]).lower(),
        "input_relabels_output": str(payload["input_activation_commitment"] == payload["output_activation_commitment"]).lower(),
        "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
        "next_backend_step": payload["next_backend_step"],
    }]


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128VectorResidualAddInputError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128VectorResidualAddInputError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128VectorResidualAddInputError(f"output path must not be a directory: {path}")
    parent = resolved.parent
    if parent.exists() and not parent.is_dir():
        raise D128VectorResidualAddInputError(f"output parent is not a directory: {parent}")
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
        "input_activation_commitment": payload["input_activation_commitment"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "output_activation_commitment": payload["output_activation_commitment"],
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
