#!/usr/bin/env python3
"""Build the d64 gate/value projection proof input.

This native-proof input consumes the RMSNorm-to-projection bridge output and
checks the gate/value projection multiplication rows. It intentionally does not
prove activation, SwiGLU mixing, down projection, residual addition, or the final
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
BRIDGE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-gate-value-projection-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-gate-value-projection-proof-2026-05.tsv"

SCHEMA = "zkai-d64-gate-value-projection-air-proof-input-v2"
DECISION = "GO_INPUT_FOR_D64_GATE_VALUE_PROJECTION_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v2"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v2"
VERIFIER_DOMAIN = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2"
WIDTH = 64
FF_DIM = 256
MATRIX_SELECTORS = {"gate": 0, "value": 1}
M31_MODULUS = (1 << 31) - 1
MAX_BRIDGE_JSON_BYTES = 1_048_576
SOURCE_BRIDGE_SCHEMA = "zkai-d64-rmsnorm-to-projection-bridge-air-proof-input-v1"
SOURCE_BRIDGE_DECISION = "GO_INPUT_FOR_D64_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF"
SOURCE_BRIDGE_PROOF_VERSION = "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1"
PROJECTION_INPUT_ROW_COMMITMENT = "blake2b-256:3a84feca5eab58736fdf01369fc64d3afc45c97ecdc629e64f0bb2eb2f8de094"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d"
STATEMENT_COMMITMENT = "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f"
GATE_MATRIX_ROOT = "blake2b-256:c7f5f490cc4140756951d0305a4786a1de9a282687c05a161ea04bd658657cfa"
VALUE_MATRIX_ROOT = "blake2b-256:e63d0d6839c92386e50314370e8b13dee0aa68c624f8ce88c34f6a4c1a2c3174"
PROJECTION_INPUT_ROW_DOMAIN = "ptvm:zkai:d64-projection-input-row:v1"
GATE_PROJECTION_OUTPUT_DOMAIN = "ptvm:zkai:d64-gate-projection-output:v1"
VALUE_PROJECTION_OUTPUT_DOMAIN = "ptvm:zkai:d64-value-projection-output:v1"
GATE_VALUE_PROJECTION_OUTPUT_DOMAIN = "ptvm:zkai:d64-gate-value-projection-output:v1"
GATE_VALUE_PROJECTION_MUL_ROW_DOMAIN = "ptvm:zkai:d64-gate-value-projection-mul-rows:v1"
NEXT_BACKEND_STEP = "encode activation/SwiGLU rows that consume gate_value_projection_output_commitment and produce hidden_activation_commitment"
PROJECTION_SCALE_DIVISOR = WIDTH

NON_CLAIMS = [
    "not full d64 block proof",
    "not activation or SwiGLU proof",
    "not down projection proof",
    "not residual proof",
    "not binding the full d64 output_activation_commitment",
    "output aggregation is verifier-recomputed from checked public multiplication rows, not a private AIR aggregation claim",
    "projection outputs are fixed-point floor quotients; divisor and remainders are bound for auditability",
]

PROOF_VERIFIER_HARDENING = [
    "projection input row commitment recomputation before proof verification",
    "gate/value projection multiplication row commitment recomputation before proof verification",
    "gate/value output commitment recomputation before proof verification",
    "gate/value projection scale divisor and remainder recomputation before proof verification",
    "AIR multiplication relation for every checked gate/value row",
    "gate and value matrix roots recomputed from checked row weights",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_gate_value_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_gate_value_projection_proof_input",
    "cargo +nightly-2025-07-14 test d64_native_gate_value_projection_proof --lib --features stwo-backend",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "ff_dim",
    "row_count",
    "gate_projection_mul_rows",
    "value_projection_mul_rows",
    "source_projection_input_row_commitment",
    "gate_projection_output_commitment",
    "value_projection_output_commitment",
    "gate_value_projection_output_commitment",
    "projection_scale_divisor",
    "gate_projection_remainder_sha256",
    "value_projection_remainder_sha256",
    "projection_output_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class GateValueProjectionInputError(ValueError):
    pass


def _load_fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_statement_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise GateValueProjectionInputError(f"failed to load d64 fixture from {FIXTURE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_fixture_module()


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
        raise GateValueProjectionInputError(f"{label} outside signed M31 bounds")


def load_bridge(path: pathlib.Path = BRIDGE_JSON) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise GateValueProjectionInputError(f"source bridge evidence is not a regular file: {path}")
        with path.open("rb") as source_file:
            source_bytes = source_file.read(MAX_BRIDGE_JSON_BYTES + 1)
        if len(source_bytes) > MAX_BRIDGE_JSON_BYTES:
            raise GateValueProjectionInputError(
                f"source bridge evidence exceeds max size: got at least {len(source_bytes)} bytes, limit {MAX_BRIDGE_JSON_BYTES} bytes"
            )
        payload = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise GateValueProjectionInputError(f"failed to load RMSNorm-to-projection bridge evidence: {err}") from err
    validate_bridge(payload)
    return payload


def validate_bridge(bridge: Any) -> None:
    if not isinstance(bridge, dict):
        raise GateValueProjectionInputError("bridge evidence must be an object")
    constants = {
        "schema": SOURCE_BRIDGE_SCHEMA,
        "decision": SOURCE_BRIDGE_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "projection_input_row_commitment": PROJECTION_INPUT_ROW_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
    }
    for field, expected in constants.items():
        if bridge.get(field) != expected:
            raise GateValueProjectionInputError(f"bridge field mismatch: {field}")
    rows = bridge.get("rows")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise GateValueProjectionInputError("bridge row vector mismatch")
    values = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("index") != index:
            raise GateValueProjectionInputError("bridge row index mismatch")
        value = row.get("projection_input_q8")
        if not isinstance(value, int):
            raise GateValueProjectionInputError("bridge projection input must be integer")
        require_signed_m31(value, "bridge projection input")
        values.append(value)
    if sequence_commitment(values, PROJECTION_INPUT_ROW_DOMAIN, [WIDTH]) != bridge["projection_input_row_commitment"]:
        raise GateValueProjectionInputError("bridge projection input commitment drift")


def projection_input_values(bridge: dict[str, Any]) -> list[int]:
    validate_bridge(bridge)
    return [row["projection_input_q8"] for row in bridge["rows"]]


def matrix_row_values(rows: list[dict[str, Any]], matrix: str, output_index: int) -> list[int]:
    return [
        row["weight_q8"]
        for row in rows
        if row["matrix"] == matrix and row["output_index"] == output_index
    ]


def matrix_root(rows: list[dict[str, Any]], matrix: str) -> str:
    leaf_hashes = []
    for output_index in range(FF_DIM):
        values = matrix_row_values(rows, matrix, output_index)
        if len(values) != WIDTH:
            raise GateValueProjectionInputError(f"{matrix} matrix row width mismatch")
        leaf = {
            "kind": "matrix_row",
            "matrix": matrix,
            "row": output_index,
            "shape": [WIDTH],
            "values_sha256": sha256_hex(values),
        }
        leaf_hashes.append(FIXTURE.merkle_leaf(leaf, "ptvm:zkai:d64:param-matrix-row-leaf:v1"))
    return FIXTURE.merkle_root(leaf_hashes, "ptvm:zkai:d64:param-matrix-row-tree:v1")


def output_commitment(gate: list[int], value: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "d64_gate_value_projection_output_v1",
            "shape": {"gate": [FF_DIM], "value": [FF_DIM]},
            "gate_values_sha256": sha256_hex(gate),
            "value_values_sha256": sha256_hex(value),
        },
        GATE_VALUE_PROJECTION_OUTPUT_DOMAIN,
    )


def divide_accumulators(accumulators: list[int], divisor: int) -> tuple[list[int], list[int]]:
    quotients: list[int] = []
    remainders: list[int] = []
    for value in accumulators:
        quotient, remainder = divmod(value, divisor)
        quotients.append(quotient)
        remainders.append(remainder)
    return quotients, remainders


def rows_commitment(rows: list[dict[str, Any]]) -> str:
    material = [
        [
            row["row_index"],
            row["matrix_selector"],
            row["output_index"],
            row["input_index"],
            row["projection_input_q8"],
            row["weight_q8"],
            row["product_q8"],
        ]
        for row in rows
    ]
    return blake2b_commitment(
        {
            "encoding": "d64_gate_value_projection_mul_rows_v1",
            "shape": [len(rows), 7],
            "rows_sha256": sha256_hex(material),
        },
        GATE_VALUE_PROJECTION_MUL_ROW_DOMAIN,
    )


def build_rows(inputs: list[int]) -> tuple[list[dict[str, Any]], list[int], list[int], list[int], list[int]]:
    rows: list[dict[str, Any]] = []
    accumulators: dict[str, list[int]] = {"gate": [], "value": []}
    row_index = 0
    for matrix in ("gate", "value"):
        for output_index in range(FF_DIM):
            acc = 0
            for input_index in range(WIDTH):
                projection_input_q8 = inputs[input_index]
                weight_q8 = FIXTURE.weight_value(matrix, output_index, input_index)
                product_q8 = projection_input_q8 * weight_q8
                require_signed_m31(product_q8, "projection product")
                rows.append(
                    {
                        "row_index": row_index,
                        "matrix": matrix,
                        "matrix_selector": MATRIX_SELECTORS[matrix],
                        "output_index": output_index,
                        "input_index": input_index,
                        "projection_input_q8": projection_input_q8,
                        "weight_q8": weight_q8,
                        "product_q8": product_q8,
                    }
                )
                acc += product_q8
                row_index += 1
            accumulators[matrix].append(acc)
    gate, gate_remainder = divide_accumulators(accumulators["gate"], PROJECTION_SCALE_DIVISOR)
    value, value_remainder = divide_accumulators(accumulators["value"], PROJECTION_SCALE_DIVISOR)
    return rows, gate, value, gate_remainder, value_remainder


def build_payload(bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    bridge = load_bridge() if bridge is None else bridge
    inputs = projection_input_values(bridge)
    rows, gate, value, gate_remainder, value_remainder = build_rows(inputs)
    reference = FIXTURE.evaluate_reference_block()
    if inputs != reference["normed_q8"]:
        raise GateValueProjectionInputError("projection input does not match canonical RMSNorm normed_q8")
    if gate != reference["gate_projection_q8"]:
        raise GateValueProjectionInputError("gate projection output mismatch")
    if value != reference["value_projection_q8"]:
        raise GateValueProjectionInputError("value projection output mismatch")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": len(rows),
        "gate_projection_mul_rows": FF_DIM * WIDTH,
        "value_projection_mul_rows": FF_DIM * WIDTH,
        "source_bridge_proof_version": SOURCE_BRIDGE_PROOF_VERSION,
        "source_projection_input_row_commitment": PROJECTION_INPUT_ROW_COMMITMENT,
        "gate_matrix_root": matrix_root(rows, "gate"),
        "value_matrix_root": matrix_root(rows, "value"),
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "gate_projection_output_commitment": sequence_commitment(gate, GATE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]),
        "value_projection_output_commitment": sequence_commitment(value, VALUE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]),
        "gate_value_projection_output_commitment": output_commitment(gate, value),
        "projection_scale_divisor": PROJECTION_SCALE_DIVISOR,
        "gate_projection_remainder_sha256": sha256_hex(gate_remainder),
        "value_projection_remainder_sha256": sha256_hex(value_remainder),
        "gate_value_projection_mul_row_commitment": rows_commitment(rows),
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "projection_input_q8": inputs,
        "gate_projection_q8": gate,
        "value_projection_q8": value,
        "gate_projection_remainder_q8": gate_remainder,
        "value_projection_remainder_q8": value_remainder,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise GateValueProjectionInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "ff_dim",
        "row_count", "gate_projection_mul_rows", "value_projection_mul_rows", "source_bridge_proof_version",
        "source_projection_input_row_commitment", "gate_matrix_root", "value_matrix_root",
        "proof_native_parameter_commitment", "gate_projection_output_commitment", "value_projection_output_commitment",
        "gate_value_projection_output_commitment", "projection_scale_divisor", "gate_projection_remainder_sha256",
        "value_projection_remainder_sha256", "gate_value_projection_mul_row_commitment", "public_instance_commitment",
        "statement_commitment", "projection_input_q8", "gate_projection_q8", "value_projection_q8",
        "gate_projection_remainder_q8", "value_projection_remainder_q8", "non_claims",
        "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise GateValueProjectionInputError("payload field set mismatch")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": 2 * FF_DIM * WIDTH,
        "gate_projection_mul_rows": FF_DIM * WIDTH,
        "value_projection_mul_rows": FF_DIM * WIDTH,
        "source_bridge_proof_version": SOURCE_BRIDGE_PROOF_VERSION,
        "source_projection_input_row_commitment": PROJECTION_INPUT_ROW_COMMITMENT,
        "gate_matrix_root": GATE_MATRIX_ROOT,
        "value_matrix_root": VALUE_MATRIX_ROOT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "projection_scale_divisor": PROJECTION_SCALE_DIVISOR,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise GateValueProjectionInputError(f"payload field mismatch: {field}")
    if payload["gate_value_projection_output_commitment"] == OUTPUT_ACTIVATION_COMMITMENT:
        raise GateValueProjectionInputError("gate/value projection output relabeled as full output commitment")
    inputs = payload["projection_input_q8"]
    gate = payload["gate_projection_q8"]
    value = payload["value_projection_q8"]
    gate_remainder = payload["gate_projection_remainder_q8"]
    value_remainder = payload["value_projection_remainder_q8"]
    if not isinstance(inputs, list) or len(inputs) != WIDTH:
        raise GateValueProjectionInputError("projection input vector mismatch")
    if not isinstance(gate, list) or len(gate) != FF_DIM or not isinstance(value, list) or len(value) != FF_DIM:
        raise GateValueProjectionInputError("projection output vector mismatch")
    if not isinstance(gate_remainder, list) or len(gate_remainder) != FF_DIM:
        raise GateValueProjectionInputError("gate projection remainder vector mismatch")
    if not isinstance(value_remainder, list) or len(value_remainder) != FF_DIM:
        raise GateValueProjectionInputError("value projection remainder vector mismatch")
    for value_index, input_value in enumerate(inputs):
        if not isinstance(input_value, int):
            raise GateValueProjectionInputError("projection input must be integer")
        require_signed_m31(input_value, f"projection input {value_index}")
    for label, remainders in (
        ("gate projection remainder", gate_remainder),
        ("value projection remainder", value_remainder),
    ):
        for index, item in enumerate(remainders):
            if not isinstance(item, int):
                raise GateValueProjectionInputError(f"{label} values must be integers")
            if not 0 <= item < PROJECTION_SCALE_DIVISOR:
                raise GateValueProjectionInputError(f"{label} {index} outside divisor range")
    rows, recomputed_gate, recomputed_value, recomputed_gate_remainder, recomputed_value_remainder = build_rows(inputs)
    for expected_row_index, row in enumerate(rows):
        expected_keys = {"row_index", "matrix", "matrix_selector", "output_index", "input_index", "projection_input_q8", "weight_q8", "product_q8"}
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise GateValueProjectionInputError("row field set mismatch")
        if row["row_index"] != expected_row_index:
            raise GateValueProjectionInputError("row index drift")
        matrix = row["matrix"]
        if matrix not in MATRIX_SELECTORS or row["matrix_selector"] != MATRIX_SELECTORS[matrix]:
            raise GateValueProjectionInputError("matrix selector drift")
        if not isinstance(row["output_index"], int) or not (0 <= row["output_index"] < FF_DIM):
            raise GateValueProjectionInputError("output index drift")
        if not isinstance(row["input_index"], int) or not (0 <= row["input_index"] < WIDTH):
            raise GateValueProjectionInputError("input index drift")
        for field in ("projection_input_q8", "weight_q8", "product_q8"):
            if not isinstance(row[field], int):
                raise GateValueProjectionInputError(f"{field} must be integer")
            require_signed_m31(row[field], field)
        if row["product_q8"] != row["projection_input_q8"] * row["weight_q8"]:
            raise GateValueProjectionInputError("projection product relation drift")
        if row["weight_q8"] != FIXTURE.weight_value(matrix, row["output_index"], row["input_index"]):
            raise GateValueProjectionInputError("projection weight drift")
        if inputs[row["input_index"]] != row["projection_input_q8"]:
            raise GateValueProjectionInputError("projection input value drift")
    if sequence_commitment(inputs, PROJECTION_INPUT_ROW_DOMAIN, [WIDTH]) != payload["source_projection_input_row_commitment"]:
        raise GateValueProjectionInputError("projection input commitment recomputation drift")
    if recomputed_gate != gate:
        raise GateValueProjectionInputError("gate projection output drift")
    if recomputed_value != value:
        raise GateValueProjectionInputError("value projection output drift")
    if recomputed_gate_remainder != gate_remainder:
        raise GateValueProjectionInputError("gate projection remainder drift")
    if recomputed_value_remainder != value_remainder:
        raise GateValueProjectionInputError("value projection remainder drift")
    if sha256_hex(gate_remainder) != payload["gate_projection_remainder_sha256"]:
        raise GateValueProjectionInputError("gate projection remainder hash drift")
    if sha256_hex(value_remainder) != payload["value_projection_remainder_sha256"]:
        raise GateValueProjectionInputError("value projection remainder hash drift")
    if matrix_root(rows, "gate") != payload["gate_matrix_root"]:
        raise GateValueProjectionInputError("gate matrix root recomputation drift")
    if matrix_root(rows, "value") != payload["value_matrix_root"]:
        raise GateValueProjectionInputError("value matrix root recomputation drift")
    if sequence_commitment(gate, GATE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]) != payload["gate_projection_output_commitment"]:
        raise GateValueProjectionInputError("gate projection output commitment drift")
    if sequence_commitment(value, VALUE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]) != payload["value_projection_output_commitment"]:
        raise GateValueProjectionInputError("value projection output commitment drift")
    if output_commitment(gate, value) != payload["gate_value_projection_output_commitment"]:
        raise GateValueProjectionInputError("gate/value projection output commitment drift")
    if rows_commitment(rows) != payload["gate_value_projection_mul_row_commitment"]:
        raise GateValueProjectionInputError("gate/value projection row commitment drift")


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
            "gate_projection_mul_rows": payload["gate_projection_mul_rows"],
            "value_projection_mul_rows": payload["value_projection_mul_rows"],
            "source_projection_input_row_commitment": payload["source_projection_input_row_commitment"],
            "gate_projection_output_commitment": payload["gate_projection_output_commitment"],
            "value_projection_output_commitment": payload["value_projection_output_commitment"],
            "gate_value_projection_output_commitment": payload["gate_value_projection_output_commitment"],
            "projection_scale_divisor": payload["projection_scale_divisor"],
            "gate_projection_remainder_sha256": payload["gate_projection_remainder_sha256"],
            "value_projection_remainder_sha256": payload["value_projection_remainder_sha256"],
            "projection_output_relabels_full_output": str(
                payload["gate_value_projection_output_commitment"] == OUTPUT_ACTIVATION_COMMITMENT
            ).lower(),
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
    parser.add_argument("--source-json", type=pathlib.Path, default=BRIDGE_JSON)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_bridge(args.source_json))
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    summary = {
        "schema": SCHEMA,
        "decision": payload["decision"],
        "row_count": payload["row_count"],
        "source_projection_input_row_commitment": payload["source_projection_input_row_commitment"],
        "gate_value_projection_output_commitment": payload["gate_value_projection_output_commitment"],
        "projection_output_relabels_full_output": False,
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
