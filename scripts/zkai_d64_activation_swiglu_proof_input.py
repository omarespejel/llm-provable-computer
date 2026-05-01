#!/usr/bin/env python3
"""Build the d64 activation/SwiGLU proof input.

This native-proof input consumes the gate/value projection proof output, checks
bounded activation lookup rows plus SwiGLU mixing rows, and emits an intermediate
hidden activation commitment. It intentionally does not prove down projection,
residual addition, or the final block output commitment.
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
GATE_VALUE_SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_gate_value_projection_proof_input.py"
SOURCE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-gate-value-projection-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-activation-swiglu-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-activation-swiglu-proof-2026-05.tsv"

SCHEMA = "zkai-d64-activation-swiglu-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D64_ACTIVATION_SWIGLU_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v2"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v2"
VERIFIER_DOMAIN = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2"
WIDTH = 64
FF_DIM = 256
SCALE_Q8 = 256
ACTIVATION_CLAMP_Q8 = 1024
M31_MODULUS = (1 << 31) - 1
MAX_SOURCE_JSON_BYTES = 1_048_576
SOURCE_GATE_VALUE_SCHEMA = "zkai-d64-gate-value-projection-air-proof-input-v1"
SOURCE_GATE_VALUE_DECISION = "GO_INPUT_FOR_D64_GATE_VALUE_PROJECTION_AIR_PROOF"
SOURCE_GATE_VALUE_PROOF_VERSION = "stwo-d64-gate-value-projection-air-proof-v1"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d"
STATEMENT_COMMITMENT = "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f"
ACTIVATION_LOOKUP_COMMITMENT = "blake2b-256:3487a9ab6cd871b7b46e54c004bf547fe9db9ba8e90b3872ba6ae3cfb990c4b3"
ACTIVATION_OUTPUT_DOMAIN = "ptvm:zkai:d64-activation-output:v1"
HIDDEN_ACTIVATION_DOMAIN = "ptvm:zkai:d64-hidden-activation:v1"
ACTIVATION_SWIGLU_ROW_DOMAIN = "ptvm:zkai:d64-activation-swiglu-rows:v1"
NEXT_BACKEND_STEP = "encode down-projection rows that consume hidden_activation_commitment and produce residual_delta_commitment"

NON_CLAIMS = [
    "not full d64 block proof",
    "not down projection proof",
    "not residual proof",
    "not binding the full d64 output_activation_commitment",
    "not a private activation-lookup opening proof",
    "activation lookup and SwiGLU rows are verifier-recomputed from checked public rows before proof verification",
]

PROOF_VERIFIER_HARDENING = [
    "gate/value projection output commitment recomputation before proof verification",
    "activation table commitment checked before proof verification",
    "activation lookup rows recomputed before proof verification",
    "SwiGLU product, floor quotient, and remainder recomputed before proof verification",
    "hidden activation commitment recomputation before proof verification",
    "AIR relation for every checked activation/SwiGLU row",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_activation_swiglu_proof_input.py --write-json docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_activation_swiglu_proof_input",
    "cargo +nightly-2025-07-14 test d64_native_activation_swiglu_proof --lib --features stwo-backend",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "ff_dim",
    "row_count",
    "activation_lookup_rows",
    "swiglu_mix_rows",
    "source_gate_value_projection_output_commitment",
    "activation_lookup_commitment",
    "activation_output_commitment",
    "hidden_activation_commitment",
    "hidden_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class ActivationSwiGluInputError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ActivationSwiGluInputError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_module(FIXTURE_PATH, "zkai_d64_rmsnorm_swiglu_statement_fixture")
GATE_VALUE = _load_module(GATE_VALUE_SCRIPT_PATH, "zkai_d64_gate_value_projection_proof_input")


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
        raise ActivationSwiGluInputError(f"{label} outside signed M31 bounds")


def load_source(path: pathlib.Path = SOURCE_JSON) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise ActivationSwiGluInputError(f"source gate/value evidence is not a regular file: {path}")
        with path.open("rb") as source_file:
            source_bytes = source_file.read(MAX_SOURCE_JSON_BYTES + 1)
        if len(source_bytes) > MAX_SOURCE_JSON_BYTES:
            raise ActivationSwiGluInputError(
                f"source gate/value evidence exceeds max size: got at least {len(source_bytes)} bytes, limit {MAX_SOURCE_JSON_BYTES} bytes"
            )
        payload = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ActivationSwiGluInputError(f"failed to load gate/value evidence: {err}") from err
    validate_source(payload)
    return payload


def validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise ActivationSwiGluInputError("source gate/value evidence must be an object")
    constants = {
        "schema": SOURCE_GATE_VALUE_SCHEMA,
        "decision": SOURCE_GATE_VALUE_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "source_bridge_proof_version": "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1",
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise ActivationSwiGluInputError(f"source gate/value field mismatch: {field}")
    try:
        GATE_VALUE.validate_payload(source)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors for this script.
        raise ActivationSwiGluInputError(f"source gate/value validation failed: {err}") from err


def source_gate_value_vectors(source: dict[str, Any]) -> tuple[list[int], list[int]]:
    validate_source(source)
    gate = source["gate_projection_q8"]
    value = source["value_projection_q8"]
    if not isinstance(gate, list) or len(gate) != FF_DIM:
        raise ActivationSwiGluInputError("source gate projection vector mismatch")
    if not isinstance(value, list) or len(value) != FF_DIM:
        raise ActivationSwiGluInputError("source value projection vector mismatch")
    for index, item in enumerate([*gate, *value]):
        if not isinstance(item, int):
            raise ActivationSwiGluInputError("source projection values must be integers")
        require_signed_m31(item, f"source projection value {index}")
    if GATE_VALUE.output_commitment(gate, value) != source["gate_value_projection_output_commitment"]:
        raise ActivationSwiGluInputError("source gate/value projection output commitment drift")
    return gate, value


def activation_row(gate_q8: int, value_q8: int, row_index: int) -> dict[str, int]:
    clamped_gate_q8 = max(-ACTIVATION_CLAMP_Q8, min(ACTIVATION_CLAMP_Q8, gate_q8))
    activation_table_index = clamped_gate_q8 + ACTIVATION_CLAMP_Q8
    activation_q8 = FIXTURE.activation_lut_value(gate_q8)
    if activation_q8 != FIXTURE.activation_table()[activation_table_index]:
        raise ActivationSwiGluInputError("activation lookup table mismatch")
    product_q16 = activation_q8 * value_q8
    hidden_q8 = product_q16 // SCALE_Q8
    remainder_q16 = product_q16 - hidden_q8 * SCALE_Q8
    if not (0 <= remainder_q16 < SCALE_Q8):
        raise ActivationSwiGluInputError("SwiGLU remainder outside floor-division range")
    row = {
        "row_index": row_index,
        "gate_q8": gate_q8,
        "clamped_gate_q8": clamped_gate_q8,
        "activation_table_index": activation_table_index,
        "activation_q8": activation_q8,
        "value_q8": value_q8,
        "product_q16": product_q16,
        "hidden_q8": hidden_q8,
        "remainder_q16": remainder_q16,
    }
    for field, item in row.items():
        require_signed_m31(item, field)
    return row


def build_rows(gate: list[int], value: list[int]) -> tuple[list[dict[str, int]], list[int], list[int]]:
    if len(gate) != FF_DIM or len(value) != FF_DIM:
        raise ActivationSwiGluInputError("projection vector length mismatch")
    rows = [activation_row(gate_q8, value_q8, row_index) for row_index, (gate_q8, value_q8) in enumerate(zip(gate, value, strict=True))]
    activated = [row["activation_q8"] for row in rows]
    hidden = [row["hidden_q8"] for row in rows]
    return rows, activated, hidden


def rows_commitment(rows: list[dict[str, int]]) -> str:
    material = [
        [
            row["row_index"],
            row["gate_q8"],
            row["clamped_gate_q8"],
            row["activation_table_index"],
            row["activation_q8"],
            row["value_q8"],
            row["product_q16"],
            row["hidden_q8"],
            row["remainder_q16"],
        ]
        for row in rows
    ]
    return blake2b_commitment(
        {
            "encoding": "d64_activation_swiglu_rows_v1",
            "shape": [len(rows), 9],
            "rows_sha256": sha256_hex(material),
        },
        ACTIVATION_SWIGLU_ROW_DOMAIN,
    )


def build_payload(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source() if source is None else source
    gate, value = source_gate_value_vectors(source)
    rows, activated, hidden = build_rows(gate, value)
    reference = FIXTURE.evaluate_reference_block()
    if gate != reference["gate_projection_q8"]:
        raise ActivationSwiGluInputError("gate projection output does not match canonical reference")
    if value != reference["value_projection_q8"]:
        raise ActivationSwiGluInputError("value projection output does not match canonical reference")
    if activated != reference["activated_gate_q8"]:
        raise ActivationSwiGluInputError("activation output does not match canonical reference")
    if hidden != reference["hidden_q8"]:
        raise ActivationSwiGluInputError("hidden activation output does not match canonical reference")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": len(rows),
        "activation_lookup_rows": FF_DIM,
        "swiglu_mix_rows": FF_DIM,
        "scale_q8": SCALE_Q8,
        "activation_clamp_q8": ACTIVATION_CLAMP_Q8,
        "source_gate_value_projection_proof_version": SOURCE_GATE_VALUE_PROOF_VERSION,
        "source_gate_projection_output_commitment": source["gate_projection_output_commitment"],
        "source_value_projection_output_commitment": source["value_projection_output_commitment"],
        "source_gate_value_projection_output_commitment": source["gate_value_projection_output_commitment"],
        "activation_lookup_commitment": ACTIVATION_LOOKUP_COMMITMENT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "activation_output_commitment": sequence_commitment(activated, ACTIVATION_OUTPUT_DOMAIN, [FF_DIM]),
        "hidden_activation_commitment": sequence_commitment(hidden, HIDDEN_ACTIVATION_DOMAIN, [FF_DIM]),
        "activation_swiglu_row_commitment": rows_commitment(rows),
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "gate_projection_q8": gate,
        "value_projection_q8": value,
        "activated_gate_q8": activated,
        "hidden_q8": hidden,
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ActivationSwiGluInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "ff_dim",
        "row_count", "activation_lookup_rows", "swiglu_mix_rows", "scale_q8", "activation_clamp_q8",
        "source_gate_value_projection_proof_version", "source_gate_projection_output_commitment",
        "source_value_projection_output_commitment", "source_gate_value_projection_output_commitment",
        "activation_lookup_commitment", "proof_native_parameter_commitment", "activation_output_commitment",
        "hidden_activation_commitment", "activation_swiglu_row_commitment", "public_instance_commitment",
        "statement_commitment", "gate_projection_q8", "value_projection_q8", "activated_gate_q8", "hidden_q8",
        "non_claims", "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise ActivationSwiGluInputError("payload field set mismatch")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "row_count": FF_DIM,
        "activation_lookup_rows": FF_DIM,
        "swiglu_mix_rows": FF_DIM,
        "scale_q8": SCALE_Q8,
        "activation_clamp_q8": ACTIVATION_CLAMP_Q8,
        "source_gate_value_projection_proof_version": SOURCE_GATE_VALUE_PROOF_VERSION,
        "activation_lookup_commitment": ACTIVATION_LOOKUP_COMMITMENT,
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
            raise ActivationSwiGluInputError(f"payload field mismatch: {field}")
    if payload["hidden_activation_commitment"] == OUTPUT_ACTIVATION_COMMITMENT:
        raise ActivationSwiGluInputError("hidden activation commitment relabeled as full output commitment")
    gate = payload["gate_projection_q8"]
    value = payload["value_projection_q8"]
    activated = payload["activated_gate_q8"]
    hidden = payload["hidden_q8"]
    if not isinstance(gate, list) or len(gate) != FF_DIM:
        raise ActivationSwiGluInputError("gate projection vector mismatch")
    if not isinstance(value, list) or len(value) != FF_DIM:
        raise ActivationSwiGluInputError("value projection vector mismatch")
    if not isinstance(activated, list) or len(activated) != FF_DIM:
        raise ActivationSwiGluInputError("activation vector mismatch")
    if not isinstance(hidden, list) or len(hidden) != FF_DIM:
        raise ActivationSwiGluInputError("hidden activation vector mismatch")
    for label, values in (
        ("gate projection", gate),
        ("value projection", value),
        ("activation", activated),
        ("hidden activation", hidden),
    ):
        for index, item in enumerate(values):
            if not isinstance(item, int):
                raise ActivationSwiGluInputError(f"{label} values must be integers")
            require_signed_m31(item, f"{label} {index}")
    if sequence_commitment(gate, GATE_VALUE.GATE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]) != payload["source_gate_projection_output_commitment"]:
        raise ActivationSwiGluInputError("source gate projection output commitment drift")
    if sequence_commitment(value, GATE_VALUE.VALUE_PROJECTION_OUTPUT_DOMAIN, [FF_DIM]) != payload["source_value_projection_output_commitment"]:
        raise ActivationSwiGluInputError("source value projection output commitment drift")
    if GATE_VALUE.output_commitment(gate, value) != payload["source_gate_value_projection_output_commitment"]:
        raise ActivationSwiGluInputError("source gate/value projection output commitment drift")
    rows, recomputed_activated, recomputed_hidden = build_rows(gate, value)
    for expected_row_index, row in enumerate(rows):
        expected_keys = {"row_index", "gate_q8", "clamped_gate_q8", "activation_table_index", "activation_q8", "value_q8", "product_q16", "hidden_q8", "remainder_q16"}
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise ActivationSwiGluInputError("row field set mismatch")
        if row["row_index"] != expected_row_index:
            raise ActivationSwiGluInputError("row index drift")
        if not (-ACTIVATION_CLAMP_Q8 <= row["clamped_gate_q8"] <= ACTIVATION_CLAMP_Q8):
            raise ActivationSwiGluInputError("activation clamp range drift")
        if row["activation_table_index"] != row["clamped_gate_q8"] + ACTIVATION_CLAMP_Q8:
            raise ActivationSwiGluInputError("activation table index drift")
        if not (0 <= row["activation_table_index"] <= 2 * ACTIVATION_CLAMP_Q8):
            raise ActivationSwiGluInputError("activation table index range drift")
        if row["activation_q8"] != FIXTURE.activation_table()[row["activation_table_index"]]:
            raise ActivationSwiGluInputError("activation lookup row drift")
        if row["product_q16"] != row["activation_q8"] * row["value_q8"]:
            raise ActivationSwiGluInputError("SwiGLU product relation drift")
        if row["product_q16"] != row["hidden_q8"] * SCALE_Q8 + row["remainder_q16"]:
            raise ActivationSwiGluInputError("SwiGLU floor relation drift")
        if not (0 <= row["remainder_q16"] < SCALE_Q8):
            raise ActivationSwiGluInputError("SwiGLU remainder range drift")
    if recomputed_activated != activated:
        raise ActivationSwiGluInputError("activation output drift")
    if recomputed_hidden != hidden:
        raise ActivationSwiGluInputError("hidden activation output drift")
    if sequence_commitment(activated, ACTIVATION_OUTPUT_DOMAIN, [FF_DIM]) != payload["activation_output_commitment"]:
        raise ActivationSwiGluInputError("activation output commitment drift")
    if sequence_commitment(hidden, HIDDEN_ACTIVATION_DOMAIN, [FF_DIM]) != payload["hidden_activation_commitment"]:
        raise ActivationSwiGluInputError("hidden activation commitment drift")
    if rows_commitment(rows) != payload["activation_swiglu_row_commitment"]:
        raise ActivationSwiGluInputError("activation/SwiGLU row commitment drift")


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
            "activation_lookup_rows": payload["activation_lookup_rows"],
            "swiglu_mix_rows": payload["swiglu_mix_rows"],
            "source_gate_value_projection_output_commitment": payload["source_gate_value_projection_output_commitment"],
            "activation_lookup_commitment": payload["activation_lookup_commitment"],
            "activation_output_commitment": payload["activation_output_commitment"],
            "hidden_activation_commitment": payload["hidden_activation_commitment"],
            "hidden_relabels_full_output": str(payload["hidden_activation_commitment"] == OUTPUT_ACTIVATION_COMMITMENT).lower(),
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
        "source_gate_value_projection_output_commitment": payload["source_gate_value_projection_output_commitment"],
        "hidden_activation_commitment": payload["hidden_activation_commitment"],
        "hidden_relabels_full_output": False,
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
