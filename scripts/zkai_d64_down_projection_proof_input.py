#!/usr/bin/env python3
"""Build the d64 down-projection proof input.

This native-proof input consumes the activation/SwiGLU hidden activation output,
checks the down-projection multiplication rows, and emits a residual-delta
commitment. It intentionally does not prove residual addition or bind the final
block output commitment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
ACTIVATION_SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_activation_swiglu_proof_input.py"
SOURCE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-activation-swiglu-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-down-projection-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-down-projection-proof-2026-05.tsv"

SCHEMA = "zkai-d64-down-projection-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D64_DOWN_PROJECTION_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v2"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v2"
VERIFIER_DOMAIN = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2"
WIDTH = 64
FF_DIM = 256
M31_MODULUS = (1 << 31) - 1
MAX_SOURCE_JSON_BYTES = 1_048_576
Q8_SEMANTIC_ABS_BOUND = 1024
SOURCE_ACTIVATION_SWIGLU_SCHEMA = "zkai-d64-activation-swiglu-air-proof-input-v1"
SOURCE_ACTIVATION_SWIGLU_DECISION = "GO_INPUT_FOR_D64_ACTIVATION_SWIGLU_AIR_PROOF"
SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION = "stwo-d64-activation-swiglu-air-proof-v1"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d"
STATEMENT_COMMITMENT = "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f"
HIDDEN_ACTIVATION_COMMITMENT = "blake2b-256:18482fa6e000d8fb0e0d7b39db46355eeec556622ca69478d1a039438495b047"
DOWN_MATRIX_ROOT = "blake2b-256:19b08584116916a72297047f01e2dc7505fb19e9508b384c7d80dfe3cb82c330"
HIDDEN_ACTIVATION_DOMAIN = "ptvm:zkai:d64-hidden-activation:v1"
RESIDUAL_DELTA_DOMAIN = "ptvm:zkai:d64-residual-delta:v1"
DOWN_PROJECTION_MUL_ROW_DOMAIN = "ptvm:zkai:d64-down-projection-mul-rows:v1"
NEXT_BACKEND_STEP = "encode residual-add rows that consume residual_delta_commitment and produce output_activation_commitment"

NON_CLAIMS = [
    "not full d64 block proof",
    "not residual proof",
    "not binding the full d64 output_activation_commitment",
    "not a private down-weight opening proof",
    "down projection aggregation is verifier-recomputed from checked public multiplication rows, not a private AIR aggregation claim",
]

PROOF_VERIFIER_HARDENING = [
    "activation/SwiGLU hidden activation commitment recomputation before proof verification",
    "down-projection multiplication row commitment recomputation before proof verification",
    "residual-delta commitment recomputation before proof verification",
    "AIR multiplication relation for every checked down-projection row",
    "down matrix root recomputed from checked row weights",
    "explicit fixed-point q8 semantic bounds for hidden activations, down weights, and residual deltas",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_down_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_down_projection_proof_input",
    "cargo +nightly-2025-07-14 test d64_native_down_projection_proof --lib --features stwo-backend",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "ff_dim",
    "row_count",
    "down_projection_mul_rows",
    "residual_delta_rows",
    "source_hidden_activation_commitment",
    "down_matrix_root",
    "residual_delta_commitment",
    "down_projection_mul_row_commitment",
    "residual_delta_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class DownProjectionInputError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise DownProjectionInputError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_module(FIXTURE_PATH, "zkai_d64_rmsnorm_swiglu_statement_fixture")
ACTIVATION_SWIGLU = _load_module(ACTIVATION_SCRIPT_PATH, "zkai_d64_activation_swiglu_proof_input")


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


def sequence_commitment(values: list[int], domain: str, shape: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": shape,
            "values_sha256": sha256_hex(values),
        },
        domain,
    )


def require_signed_m31(value: int, label: str) -> None:
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise DownProjectionInputError(f"{label} outside signed M31 bounds")


def require_signed_q8(value: int, label: str) -> None:
    if not (-Q8_SEMANTIC_ABS_BOUND <= value <= Q8_SEMANTIC_ABS_BOUND):
        raise DownProjectionInputError(f"{label} outside fixed-point q8 semantic bounds")


def load_source(path: pathlib.Path = SOURCE_JSON) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise DownProjectionInputError(f"source activation/SwiGLU evidence is not a regular file: {path}")
        with path.open("rb") as source_file:
            source_bytes = source_file.read(MAX_SOURCE_JSON_BYTES + 1)
        if len(source_bytes) > MAX_SOURCE_JSON_BYTES:
            raise DownProjectionInputError(
                f"source activation/SwiGLU evidence exceeds max size: got at least {len(source_bytes)} bytes, limit {MAX_SOURCE_JSON_BYTES} bytes"
            )
        payload = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise DownProjectionInputError(f"failed to load activation/SwiGLU evidence: {err}") from err
    validate_source(payload)
    return payload


def validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise DownProjectionInputError("source activation/SwiGLU evidence must be an object")
    constants = {
        "schema": SOURCE_ACTIVATION_SWIGLU_SCHEMA,
        "decision": SOURCE_ACTIVATION_SWIGLU_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "source_gate_value_projection_proof_version": "stwo-d64-gate-value-projection-air-proof-v1",
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "hidden_activation_commitment": HIDDEN_ACTIVATION_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise DownProjectionInputError(f"source activation/SwiGLU field mismatch: {field}")
    try:
        ACTIVATION_SWIGLU.validate_payload(source)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors for this script.
        raise DownProjectionInputError(f"source activation/SwiGLU validation failed: {err}") from err


def source_hidden_vector(source: dict[str, Any]) -> list[int]:
    validate_source(source)
    hidden = source["hidden_q8"]
    if not isinstance(hidden, list) or len(hidden) != FF_DIM:
        raise DownProjectionInputError("source hidden activation vector mismatch")
    for index, item in enumerate(hidden):
        if not isinstance(item, int):
            raise DownProjectionInputError("source hidden activation values must be integers")
        require_signed_q8(item, f"source hidden activation {index}")
        require_signed_m31(item, f"source hidden activation {index}")
    if sequence_commitment(hidden, HIDDEN_ACTIVATION_DOMAIN, [FF_DIM]) != source["hidden_activation_commitment"]:
        raise DownProjectionInputError("source hidden activation commitment drift")
    return hidden


def matrix_row_values(rows: list[dict[str, Any]], output_index: int) -> list[int]:
    return [row["weight_q8"] for row in rows if row["output_index"] == output_index]


def matrix_root(rows: list[dict[str, Any]]) -> str:
    leaf_hashes = []
    for output_index in range(WIDTH):
        values = matrix_row_values(rows, output_index)
        if len(values) != FF_DIM:
            raise DownProjectionInputError("down matrix row width mismatch")
        leaf = {
            "kind": "matrix_row",
            "matrix": "down",
            "row": output_index,
            "shape": [FF_DIM],
            "values_sha256": sha256_hex(values),
        }
        leaf_hashes.append(FIXTURE.merkle_leaf(leaf, "ptvm:zkai:d64:param-matrix-row-leaf:v1"))
    return FIXTURE.merkle_root(leaf_hashes, "ptvm:zkai:d64:param-matrix-row-tree:v1")


def rows_commitment(rows: list[dict[str, int]]) -> str:
    material = [
        [
            row["row_index"],
            row["output_index"],
            row["hidden_index"],
            row["hidden_q8"],
            row["weight_q8"],
            row["product_q8"],
        ]
        for row in rows
    ]
    return blake2b_commitment(
        {
            "encoding": "d64_down_projection_mul_rows_v1",
            "shape": [len(rows), 6],
            "rows_sha256": sha256_hex(material),
        },
        DOWN_PROJECTION_MUL_ROW_DOMAIN,
    )


def build_rows(hidden: list[int]) -> tuple[list[dict[str, int]], list[int]]:
    if len(hidden) != FF_DIM:
        raise DownProjectionInputError("hidden activation vector length mismatch")
    rows: list[dict[str, int]] = []
    residual_delta: list[int] = []
    row_index = 0
    for output_index in range(WIDTH):
        acc = 0
        for hidden_index in range(FF_DIM):
            hidden_q8 = hidden[hidden_index]
            weight_q8 = FIXTURE.weight_value("down", output_index, hidden_index)
            require_signed_q8(hidden_q8, "hidden activation")
            require_signed_q8(weight_q8, "down projection weight")
            product_q8 = hidden_q8 * weight_q8
            require_signed_m31(product_q8, "down projection product")
            rows.append(
                {
                    "row_index": row_index,
                    "output_index": output_index,
                    "hidden_index": hidden_index,
                    "hidden_q8": hidden_q8,
                    "weight_q8": weight_q8,
                    "product_q8": product_q8,
                }
            )
            acc += product_q8
            row_index += 1
        residual_delta.append(acc // FF_DIM)
    return rows, residual_delta


def build_payload(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source() if source is None else source
    hidden = source_hidden_vector(source)
    rows, residual_delta = build_rows(hidden)
    reference = FIXTURE.evaluate_reference_block()
    if hidden != reference["hidden_q8"]:
        raise DownProjectionInputError("hidden activation output does not match canonical reference")
    if residual_delta != reference["residual_delta_q8"]:
        raise DownProjectionInputError("residual delta output does not match canonical reference")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": len(rows),
        "down_projection_mul_rows": WIDTH * FF_DIM,
        "residual_delta_rows": WIDTH,
        "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source_hidden_activation_commitment": source["hidden_activation_commitment"],
        "down_matrix_root": matrix_root(rows),
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "residual_delta_commitment": sequence_commitment(residual_delta, RESIDUAL_DELTA_DOMAIN, [WIDTH]),
        "down_projection_mul_row_commitment": rows_commitment(rows),
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "hidden_q8": hidden,
        "residual_delta_q8": residual_delta,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise DownProjectionInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "ff_dim",
        "row_count", "down_projection_mul_rows", "residual_delta_rows", "source_activation_swiglu_proof_version",
        "source_hidden_activation_commitment", "down_matrix_root", "proof_native_parameter_commitment",
        "residual_delta_commitment", "down_projection_mul_row_commitment", "public_instance_commitment",
        "statement_commitment", "hidden_q8", "residual_delta_q8", "non_claims", "proof_verifier_hardening",
        "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise DownProjectionInputError("payload field set mismatch")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": WIDTH * FF_DIM,
        "down_projection_mul_rows": WIDTH * FF_DIM,
        "residual_delta_rows": WIDTH,
        "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source_hidden_activation_commitment": HIDDEN_ACTIVATION_COMMITMENT,
        "down_matrix_root": DOWN_MATRIX_ROOT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise DownProjectionInputError(f"payload field mismatch: {field}")
    if payload["residual_delta_commitment"] == OUTPUT_ACTIVATION_COMMITMENT:
        raise DownProjectionInputError("residual delta commitment relabeled as full output commitment")
    hidden = payload["hidden_q8"]
    residual_delta = payload["residual_delta_q8"]
    if not isinstance(hidden, list) or len(hidden) != FF_DIM:
        raise DownProjectionInputError("hidden activation vector mismatch")
    if not isinstance(residual_delta, list) or len(residual_delta) != WIDTH:
        raise DownProjectionInputError("residual delta vector mismatch")
    for label, values in (("hidden activation", hidden), ("residual delta", residual_delta)):
        for index, item in enumerate(values):
            if not isinstance(item, int):
                raise DownProjectionInputError(f"{label} values must be integers")
            require_signed_q8(item, f"{label} {index}")
            require_signed_m31(item, f"{label} {index}")
    if sequence_commitment(hidden, HIDDEN_ACTIVATION_DOMAIN, [FF_DIM]) != payload["source_hidden_activation_commitment"]:
        raise DownProjectionInputError("source hidden activation commitment drift")
    rows, recomputed_delta = build_rows(hidden)
    for expected_row_index, row in enumerate(rows):
        expected_keys = {"row_index", "output_index", "hidden_index", "hidden_q8", "weight_q8", "product_q8"}
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise DownProjectionInputError("row field set mismatch")
        if row["row_index"] != expected_row_index:
            raise DownProjectionInputError("row index drift")
        if not isinstance(row["output_index"], int) or not (0 <= row["output_index"] < WIDTH):
            raise DownProjectionInputError("output index drift")
        if not isinstance(row["hidden_index"], int) or not (0 <= row["hidden_index"] < FF_DIM):
            raise DownProjectionInputError("hidden index drift")
        for field in ("hidden_q8", "weight_q8", "product_q8"):
            if not isinstance(row[field], int):
                raise DownProjectionInputError(f"{field} must be integer")
            require_signed_m31(row[field], field)
        require_signed_q8(row["hidden_q8"], "hidden_q8")
        require_signed_q8(row["weight_q8"], "weight_q8")
        if row["product_q8"] != row["hidden_q8"] * row["weight_q8"]:
            raise DownProjectionInputError("down projection product relation drift")
        if row["weight_q8"] != FIXTURE.weight_value("down", row["output_index"], row["hidden_index"]):
            raise DownProjectionInputError("down projection weight drift")
        if hidden[row["hidden_index"]] != row["hidden_q8"]:
            raise DownProjectionInputError("hidden activation value drift")
    if recomputed_delta != residual_delta:
        raise DownProjectionInputError("residual delta output drift")
    if matrix_root(rows) != payload["down_matrix_root"]:
        raise DownProjectionInputError("down matrix root recomputation drift")
    if sequence_commitment(residual_delta, RESIDUAL_DELTA_DOMAIN, [WIDTH]) != payload["residual_delta_commitment"]:
        raise DownProjectionInputError("residual delta commitment drift")
    if rows_commitment(rows) != payload["down_projection_mul_row_commitment"]:
        raise DownProjectionInputError("down projection row commitment drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    return [
        {
            "target_id": payload["target_id"],
            "decision": payload["decision"],
            "width": payload["width"],
            "ff_dim": payload["ff_dim"],
            "row_count": payload["row_count"],
            "down_projection_mul_rows": payload["down_projection_mul_rows"],
            "residual_delta_rows": payload["residual_delta_rows"],
            "source_hidden_activation_commitment": payload["source_hidden_activation_commitment"],
            "down_matrix_root": payload["down_matrix_root"],
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "down_projection_mul_row_commitment": payload["down_projection_mul_row_commitment"],
            "residual_delta_relabels_full_output": str(payload["residual_delta_commitment"] == OUTPUT_ACTIVATION_COMMITMENT).lower(),
            "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            "next_backend_step": payload["next_backend_step"],
        }
    ]


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if tsv_path is not None:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        with tsv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows_for_tsv(payload, validated=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-json", type=pathlib.Path, default=SOURCE_JSON)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_source(args.source_json))
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    summary = {
        "schema": SCHEMA,
        "decision": payload["decision"],
        "row_count": payload["row_count"],
        "source_hidden_activation_commitment": payload["source_hidden_activation_commitment"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "residual_delta_relabels_full_output": False,
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
