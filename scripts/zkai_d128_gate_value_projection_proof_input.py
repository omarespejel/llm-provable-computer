#!/usr/bin/env python3
"""Build the d128 gate/value projection proof input.

This native-proof input consumes the d128 RMSNorm-to-projection bridge output and
checks the gate/value projection multiplication rows over deterministic,
proof-native synthetic parameters. It intentionally does not prove activation,
SwiGLU mixing, down projection, residual addition, composition, recursion, or the
final block output commitment.
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
BRIDGE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d128-gate-value-projection-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d128-gate-value-projection-proof-2026-05.tsv"

SCHEMA = "zkai-d128-gate-value-projection-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D128_GATE_VALUE_PROJECTION_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
FF_DIM = 512
MATRIX_SELECTORS = {"gate": 0, "value": 1}
M31_MODULUS = (1 << 31) - 1
MAX_BRIDGE_JSON_BYTES = 1_048_576
SOURCE_BRIDGE_SCHEMA = "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1"
SOURCE_BRIDGE_DECISION = "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF"
SOURCE_BRIDGE_PROOF_VERSION = "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1"
SOURCE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ca94d85cb0ed5e9001cd3def00817060745fa015bd8dda5f08732944f7418383"
SOURCE_BRIDGE_STATEMENT_COMMITMENT = "blake2b-256:fe0a9e59560611ed5220fd25b082806977a66a7032f457fce2cd5c3a41856728"
PROJECTION_INPUT_ROW_COMMITMENT = "blake2b-256:84fd5765c9ed8d21ced01ace55c5f95b34f16d159864c1ec20d9a0cd4cd67b17"
DERIVED_BRIDGE_PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:7939a60307f2b0f078e55430faf45cde8598158dd2090c5d65bf4fd72e436f4b"
DERIVED_BRIDGE_STATEMENT_COMMITMENT = "blake2b-256:85a4f027ea7570b388a585fb53cb9c66a7358e2431730e044e39f4bdea859abf"
DERIVED_PROJECTION_INPUT_ROW_COMMITMENT = "blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba"
TARGET_COMMITMENT = "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18"
PROOF_NATIVE_PARAMETER_KIND = "d128-gate-value-projection-synthetic-parameters-v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:d128-proof-native-parameter-commitment:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:d128-public-instance:v1"
WEIGHT_GENERATOR_SEED = "zkai-d128-gate-value-projection-synthetic-parameters-2026-05-v1"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:d1a46c1b0b66363d99ab94953af741710bfadfda2332907274096577efe6bf17"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:be8d4ea70a2fc883381caa077874a4cd5c22707daa527208a606ceee5229728c"
STATEMENT_COMMITMENT = "blake2b-256:3b60f7e1b9fc592dadc4835ed0c85e643de89017c66e7995724911cfbd8297cf"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:7e6ae6d301fc60ac2232d807d155785eabe653cf4e91971adda470a04246a572"
GATE_MATRIX_ROOT = "blake2b-256:101e9f5ad1079bc7ed0e10df96bf30091dcf82d7a3010c5bf7ced764fe15f08e"
VALUE_MATRIX_ROOT = "blake2b-256:ef43adb2d5ab19880576bd0a46692f9c7daf4f0548dc7c6bd2785d9f5b8c0bdd"
GATE_PROJECTION_OUTPUT_COMMITMENT = "blake2b-256:7ba96ea1ea4fb7ec19bede9996273b118c90adcef1f02091225bf613cf618ec7"
VALUE_PROJECTION_OUTPUT_COMMITMENT = "blake2b-256:fd1fcf585627f725ec4e9f8ec7154647f6ed8f44a24f04211e110912fbb82edf"
GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT = "blake2b-256:fb1aa112ab63e26da7d5f0805d2a713fad13dff09ab3a68c0060e85c88aee0f3"
GATE_VALUE_PROJECTION_MUL_ROW_COMMITMENT = "blake2b-256:1dfcd5a2a972dfcf55ecf41a57f82f3225923a2157bd4dc61bb11d4448e74a4a"
PROJECTION_INPUT_ROW_DOMAIN = "ptvm:zkai:d128-projection-input-row:v1"
GATE_PROJECTION_OUTPUT_DOMAIN = "ptvm:zkai:d128-gate-projection-output:v1"
VALUE_PROJECTION_OUTPUT_DOMAIN = "ptvm:zkai:d128-value-projection-output:v1"
GATE_VALUE_PROJECTION_OUTPUT_DOMAIN = "ptvm:zkai:d128-gate-value-projection-output:v1"
GATE_VALUE_PROJECTION_MUL_ROW_DOMAIN = "ptvm:zkai:d128-gate-value-projection-mul-rows:v1"
MATRIX_ROW_LEAF_DOMAIN = "ptvm:zkai:d128:param-matrix-row-leaf:v1"
MATRIX_ROW_TREE_DOMAIN = "ptvm:zkai:d128:param-matrix-row-tree:v1"
NEXT_BACKEND_STEP = "encode d128 activation/SwiGLU rows that consume gate_value_projection_output_commitment and produce hidden_activation_commitment"

NON_CLAIMS = [
    "not full d128 block proof",
    "not activation or SwiGLU proof",
    "not down projection proof",
    "not residual proof",
    "not recursive composition",
    "not private parameter-opening proof",
    "synthetic deterministic gate/value parameters only",
    "not binding the full d128 output_activation_commitment",
    "output aggregation is verifier-recomputed from checked public multiplication rows, not a private AIR aggregation claim",
]

PROOF_VERIFIER_HARDENING = [
    "source d128 RMSNorm-to-projection bridge evidence validation before projection construction",
    "projection input row commitment recomputation before proof verification",
    "gate/value projection multiplication row commitment recomputation before proof verification",
    "gate/value output commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR multiplication relation for every checked gate/value row",
    "gate and value matrix roots recomputed from checked row weights",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_gate_value_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_projection_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_gate_value_projection_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
]
DERIVED_VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_gate_value_projection_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_projection_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_gate_value_projection_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
]

SOURCE_BRIDGE_ANCHORS = (
    {
        "kind": "synthetic",
        "statement_commitment": SOURCE_BRIDGE_STATEMENT_COMMITMENT,
        "public_instance_commitment": SOURCE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
        "projection_input_row_commitment": PROJECTION_INPUT_ROW_COMMITMENT,
        "validation_commands": VALIDATION_COMMANDS,
    },
    {
        "kind": "attention_derived",
        "statement_commitment": DERIVED_BRIDGE_STATEMENT_COMMITMENT,
        "public_instance_commitment": DERIVED_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
        "projection_input_row_commitment": DERIVED_PROJECTION_INPUT_ROW_COMMITMENT,
        "validation_commands": DERIVED_VALIDATION_COMMANDS,
    },
)

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "ff_dim",
    "row_count",
    "gate_projection_mul_rows",
    "value_projection_mul_rows",
    "source_bridge_statement_commitment",
    "source_bridge_public_instance_commitment",
    "source_projection_input_row_commitment",
    "gate_matrix_root",
    "value_matrix_root",
    "gate_projection_output_commitment",
    "value_projection_output_commitment",
    "gate_value_projection_output_commitment",
    "projection_output_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class GateValueProjectionInputError(ValueError):
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


def blake2b_hex(data: bytes, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(data)
    return digest.hexdigest()


def sequence_commitment(values: list[int], domain: str, shape: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": shape,
            "values_sha256": sha256_hex(values),
        },
        domain,
    )


def require_signed_m31(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise GateValueProjectionInputError(f"{label} must be an integer")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise GateValueProjectionInputError(f"{label} outside signed M31 bounds")


def require_commitment(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("blake2b-256:"):
        raise GateValueProjectionInputError(f"{label} must be a blake2b-256 commitment")
    digest = value.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise GateValueProjectionInputError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def source_bridge_anchor(bridge: dict[str, Any]) -> dict[str, Any]:
    statement = require_commitment(bridge.get("statement_commitment"), "bridge statement commitment")
    public_instance = require_commitment(
        bridge.get("public_instance_commitment"),
        "bridge public instance commitment",
    )
    projection = require_commitment(
        bridge.get("projection_input_row_commitment"),
        "bridge projection input row commitment",
    )
    for anchor in SOURCE_BRIDGE_ANCHORS:
        if (
            statement == anchor["statement_commitment"]
            and public_instance == anchor["public_instance_commitment"]
            and projection == anchor["projection_input_row_commitment"]
        ):
            return anchor
    raise GateValueProjectionInputError(
        "bridge source anchor is not approved for d128 gate/value native input"
    )


def parse_blake2b_hex(value: str, label: str) -> bytes:
    if not isinstance(value, str):
        raise GateValueProjectionInputError(f"{label} must be a hex digest")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise GateValueProjectionInputError(f"{label} must be a 32-byte lowercase hex digest")
    return bytes.fromhex(raw)


def deterministic_int(label: str, *indices: int, min_value: int, max_value: int) -> int:
    if min_value > max_value:
        raise GateValueProjectionInputError("invalid deterministic integer range")
    material = ":".join([WEIGHT_GENERATOR_SEED, label, *(str(index) for index in indices)]).encode("utf-8")
    raw = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return min_value + raw % (max_value - min_value + 1)


def weight_value(matrix: str, row: int, col: int) -> int:
    if matrix not in MATRIX_SELECTORS:
        raise GateValueProjectionInputError(f"unknown projection matrix: {matrix}")
    return deterministic_int(f"{matrix}_weight_q8", row, col, min_value=-8, max_value=8)


def merkle_root(leaf_hashes: list[str], domain: str) -> str:
    if not leaf_hashes:
        raise GateValueProjectionInputError("cannot commit an empty matrix tree")
    level = leaf_hashes
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        next_level = []
        for index in range(0, len(level), 2):
            next_level.append(
                blake2b_hex(
                    parse_blake2b_hex(level[index], "left matrix hash")
                    + parse_blake2b_hex(level[index + 1], "right matrix hash"),
                    domain,
                )
            )
        level = next_level
    return f"blake2b-256:{level[0]}"


def proof_native_parameter_commitment(gate_root: str, value_root: str) -> str:
    return blake2b_commitment(
        {
            "ff_dim": FF_DIM,
            "gate_matrix_root": gate_root,
            "kind": PROOF_NATIVE_PARAMETER_KIND,
            "target_commitment": TARGET_COMMITMENT,
            "value_matrix_root": value_root,
            "weight_generator_seed": WEIGHT_GENERATOR_SEED,
            "width": WIDTH,
        },
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def statement_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "ff_dim": payload["ff_dim"],
            "gate_matrix_root": payload["gate_matrix_root"],
            "gate_projection_output_commitment": payload["gate_projection_output_commitment"],
            "gate_value_projection_mul_row_commitment": payload["gate_value_projection_mul_row_commitment"],
            "gate_value_projection_output_commitment": payload["gate_value_projection_output_commitment"],
            "operation": "gate_value_projection",
            "proof_native_parameter_commitment": payload["proof_native_parameter_commitment"],
            "required_backend_version": REQUIRED_BACKEND_VERSION,
            "row_count": payload["row_count"],
            "source_bridge_proof_version": SOURCE_BRIDGE_PROOF_VERSION,
            "source_bridge_statement_commitment": payload["source_bridge_statement_commitment"],
            "source_projection_input_row_commitment": payload["source_projection_input_row_commitment"],
            "target_commitment": TARGET_COMMITMENT,
            "target_id": TARGET_ID,
            "value_matrix_root": payload["value_matrix_root"],
            "value_projection_output_commitment": payload["value_projection_output_commitment"],
            "verifier_domain": VERIFIER_DOMAIN,
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return blake2b_commitment(
        {
            "ff_dim": FF_DIM,
            "operation": "gate_value_projection",
            "target_commitment": statement,
            "width": WIDTH,
        },
        PUBLIC_INSTANCE_DOMAIN,
    )


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
        "operation": "rmsnorm_to_projection_bridge",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
    }
    for field, expected in constants.items():
        if bridge.get(field) != expected:
            raise GateValueProjectionInputError(f"bridge field mismatch: {field}")
    source_bridge_anchor(bridge)
    rows = bridge.get("rows")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise GateValueProjectionInputError("bridge row vector mismatch")
    values = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("index") != index:
            raise GateValueProjectionInputError("bridge row index mismatch")
        value = row.get("projection_input_q8")
        require_signed_m31(value, "bridge projection input")
        values.append(value)
    if sequence_commitment(values, PROJECTION_INPUT_ROW_DOMAIN, [WIDTH]) != bridge["projection_input_row_commitment"]:
        raise GateValueProjectionInputError("bridge projection input commitment drift")


def projection_input_values(bridge: dict[str, Any]) -> list[int]:
    validate_bridge(bridge)
    return [row["projection_input_q8"] for row in bridge["rows"]]


def matrix_row_values(rows: list[dict[str, Any]], matrix: str, output_index: int) -> list[int]:
    return [row["weight_q8"] for row in rows if row["matrix"] == matrix and row["output_index"] == output_index]


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
        leaf_hashes.append(blake2b_hex(canonical_json_bytes(leaf), MATRIX_ROW_LEAF_DOMAIN))
    return merkle_root(leaf_hashes, MATRIX_ROW_TREE_DOMAIN)


def output_commitment(gate: list[int], value: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "d128_gate_value_projection_output_v1",
            "shape": {"gate": [FF_DIM], "value": [FF_DIM]},
            "gate_values_sha256": sha256_hex(gate),
            "value_values_sha256": sha256_hex(value),
        },
        GATE_VALUE_PROJECTION_OUTPUT_DOMAIN,
    )


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
            "encoding": "d128_gate_value_projection_mul_rows_v1",
            "shape": [len(rows), 7],
            "rows_sha256": sha256_hex(material),
        },
        GATE_VALUE_PROJECTION_MUL_ROW_DOMAIN,
    )


def build_rows(inputs: list[int]) -> tuple[list[dict[str, Any]], list[int], list[int]]:
    if len(inputs) != WIDTH:
        raise GateValueProjectionInputError("projection input vector mismatch")
    rows: list[dict[str, Any]] = []
    outputs: dict[str, list[int]] = {"gate": [], "value": []}
    row_index = 0
    for matrix in ("gate", "value"):
        for output_index in range(FF_DIM):
            acc = 0
            for input_index in range(WIDTH):
                projection_input_q8 = inputs[input_index]
                weight_q8 = weight_value(matrix, output_index, input_index)
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
            require_signed_m31(acc, f"{matrix} projection output {output_index}")
            outputs[matrix].append(acc)
    return rows, outputs["gate"], outputs["value"]


def build_payload(bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    bridge = load_bridge() if bridge is None else bridge
    anchor = source_bridge_anchor(bridge)
    inputs = projection_input_values(bridge)
    rows, gate, value = build_rows(inputs)
    gate_root = matrix_root(rows, "gate")
    value_root = matrix_root(rows, "value")
    native_parameter = proof_native_parameter_commitment(gate_root, value_root)
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
        "source_bridge_statement_commitment": anchor["statement_commitment"],
        "source_bridge_public_instance_commitment": anchor["public_instance_commitment"],
        "source_projection_input_row_commitment": anchor["projection_input_row_commitment"],
        "gate_matrix_root": gate_root,
        "value_matrix_root": value_root,
        "proof_native_parameter_commitment": native_parameter,
        "gate_projection_output_commitment": sequence_commitment(gate, GATE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]),
        "value_projection_output_commitment": sequence_commitment(value, VALUE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]),
        "gate_value_projection_output_commitment": output_commitment(gate, value),
        "gate_value_projection_mul_row_commitment": rows_commitment(rows),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "projection_input_q8": inputs,
        "gate_projection_q8": gate,
        "value_projection_q8": value,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(anchor["validation_commands"]),
    }
    statement = statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise GateValueProjectionInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "ff_dim",
        "row_count", "gate_projection_mul_rows", "value_projection_mul_rows", "source_bridge_proof_version",
        "source_bridge_statement_commitment", "source_bridge_public_instance_commitment",
        "source_projection_input_row_commitment", "gate_matrix_root", "value_matrix_root",
        "proof_native_parameter_commitment", "gate_projection_output_commitment", "value_projection_output_commitment",
        "gate_value_projection_output_commitment", "gate_value_projection_mul_row_commitment", "public_instance_commitment",
        "statement_commitment", "projection_input_q8", "gate_projection_q8", "value_projection_q8", "non_claims",
        "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    legacy_synthetic_fields = expected_fields - {
        "source_bridge_statement_commitment",
        "source_bridge_public_instance_commitment",
    }
    if set(payload) == expected_fields:
        source_bridge = {
            "statement_commitment": payload.get("source_bridge_statement_commitment"),
            "public_instance_commitment": payload.get("source_bridge_public_instance_commitment"),
            "projection_input_row_commitment": payload.get("source_projection_input_row_commitment"),
        }
    elif set(payload) == legacy_synthetic_fields:
        source_bridge = {
            "statement_commitment": SOURCE_BRIDGE_STATEMENT_COMMITMENT,
            "public_instance_commitment": SOURCE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
            "projection_input_row_commitment": payload.get("source_projection_input_row_commitment"),
        }
    else:
        raise GateValueProjectionInputError("payload field set mismatch")
    source_anchor = source_bridge_anchor(source_bridge)
    payload["source_bridge_statement_commitment"] = source_anchor["statement_commitment"]
    payload["source_bridge_public_instance_commitment"] = source_anchor["public_instance_commitment"]
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
        "gate_matrix_root": GATE_MATRIX_ROOT,
        "value_matrix_root": VALUE_MATRIX_ROOT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
    }
    for field, expected in constants.items():
        if expected == "TO_BE_FILLED":
            continue
        if payload.get(field) != expected:
            raise GateValueProjectionInputError(f"payload field mismatch: {field}")
    if payload.get("validation_commands") != list(source_anchor["validation_commands"]):
        raise GateValueProjectionInputError("validation commands drift")
    if payload["gate_value_projection_output_commitment"] == OUTPUT_ACTIVATION_COMMITMENT:
        raise GateValueProjectionInputError("gate/value projection output relabeled as full output commitment")
    inputs = payload["projection_input_q8"]
    gate = payload["gate_projection_q8"]
    value = payload["value_projection_q8"]
    if not isinstance(inputs, list) or len(inputs) != WIDTH:
        raise GateValueProjectionInputError("projection input vector mismatch")
    if not isinstance(gate, list) or len(gate) != FF_DIM or not isinstance(value, list) or len(value) != FF_DIM:
        raise GateValueProjectionInputError("projection output vector mismatch")
    for value_index, input_value in enumerate(inputs):
        require_signed_m31(input_value, f"projection input {value_index}")
    rows, recomputed_gate, recomputed_value = build_rows(inputs)
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
            require_signed_m31(row[field], field)
        if row["product_q8"] != row["projection_input_q8"] * row["weight_q8"]:
            raise GateValueProjectionInputError("projection product relation drift")
        if row["weight_q8"] != weight_value(matrix, row["output_index"], row["input_index"]):
            raise GateValueProjectionInputError("projection weight drift")
        if inputs[row["input_index"]] != row["projection_input_q8"]:
            raise GateValueProjectionInputError("projection input value drift")
    if sequence_commitment(inputs, PROJECTION_INPUT_ROW_DOMAIN, [WIDTH]) != payload["source_projection_input_row_commitment"]:
        raise GateValueProjectionInputError("projection input commitment recomputation drift")
    if recomputed_gate != gate:
        raise GateValueProjectionInputError("gate projection output drift")
    if recomputed_value != value:
        raise GateValueProjectionInputError("value projection output drift")
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
    if proof_native_parameter_commitment(payload["gate_matrix_root"], payload["value_matrix_root"]) != payload["proof_native_parameter_commitment"]:
        raise GateValueProjectionInputError("proof-native parameter commitment drift")
    if statement_commitment(payload) != payload["statement_commitment"]:
        raise GateValueProjectionInputError("statement commitment drift")
    if public_instance_commitment(payload["statement_commitment"]) != payload["public_instance_commitment"]:
        raise GateValueProjectionInputError("public instance commitment drift")


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
            "source_bridge_statement_commitment": payload["source_bridge_statement_commitment"],
            "source_bridge_public_instance_commitment": payload["source_bridge_public_instance_commitment"],
            "source_projection_input_row_commitment": payload["source_projection_input_row_commitment"],
            "gate_matrix_root": payload["gate_matrix_root"],
            "value_matrix_root": payload["value_matrix_root"],
            "gate_projection_output_commitment": payload["gate_projection_output_commitment"],
            "value_projection_output_commitment": payload["value_projection_output_commitment"],
            "gate_value_projection_output_commitment": payload["gate_value_projection_output_commitment"],
            "projection_output_relabels_full_output": str(payload["gate_value_projection_output_commitment"] == OUTPUT_ACTIVATION_COMMITMENT).lower(),
            "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
            "next_backend_step": payload["next_backend_step"],
        }
    ]


def _assert_repo_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise GateValueProjectionInputError(f"output path escapes repository: {path}") from err
    if path.is_symlink():
        raise GateValueProjectionInputError(f"output path must not be a symlink: {path}")
    return resolved


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    resolved = _assert_repo_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent)
    tmp_path = pathlib.Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(tmp_path, resolved)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise


def _tsv_text(payload: dict[str, Any]) -> str:
    rows = rows_for_tsv(payload, validated=True)
    import io

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs: list[tuple[pathlib.Path, str]] = []
    if json_path is not None:
        outputs.append((json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"))
    if tsv_path is not None:
        outputs.append((tsv_path, _tsv_text(payload)))
    if not outputs:
        return

    prepared: list[tuple[pathlib.Path, str, str | None]] = []
    seen: set[pathlib.Path] = set()
    for path, text in outputs:
        resolved = _assert_repo_path(path)
        if resolved in seen:
            raise GateValueProjectionInputError(f"duplicate output path: {path}")
        seen.add(resolved)
        previous = resolved.read_text(encoding="utf-8") if resolved.exists() else None
        prepared.append((resolved, text, previous))

    written: list[tuple[pathlib.Path, str | None]] = []
    try:
        for path, text, previous in prepared:
            _atomic_write_text(path, text)
            written.append((path, previous))
    except Exception:
        for path, previous in reversed(written):
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                _atomic_write_text(path, previous)
        raise


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
