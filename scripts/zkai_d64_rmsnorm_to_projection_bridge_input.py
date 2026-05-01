#!/usr/bin/env python3
"""Build the d64 RMSNorm-to-projection bridge proof input.

This is a proof-input generator for the native Stwo bridge slice. It consumes the
checked RMSNorm-local `normed_q8` rows and emits the same values under a separate
projection-input commitment domain. It intentionally does not compute gate/value
projection outputs or the full block output commitment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-native-rmsnorm-public-row-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.tsv"

SCHEMA = "zkai-d64-rmsnorm-to-projection-bridge-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D64_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v2"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v2"
VERIFIER_DOMAIN = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2"
WIDTH = 64
SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION = "stwo-d64-rmsnorm-public-row-air-proof-v2"
RMSNORM_OUTPUT_ROW_COMMITMENT = "blake2b-256:c9ab975e440661ce7796f33b75008d20e7eb26a4c41956d2f723093e4ac373a7"
PROJECTION_INPUT_ROW_COMMITMENT = "blake2b-256:3a84feca5eab58736fdf01369fc64d3afc45c97ecdc629e64f0bb2eb2f8de094"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d"
STATEMENT_COMMITMENT = "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f"
RMSNORM_OUTPUT_ROW_DOMAIN = "ptvm:zkai:d64-rmsnorm-output-row:v1"
PROJECTION_INPUT_ROW_DOMAIN = "ptvm:zkai:d64-projection-input-row:v1"
NEXT_BACKEND_STEP = "encode gate/value projection rows that consume projection_input_row_commitment and produce gate_value_projection_output_commitment"

NON_CLAIMS = [
    "not full d64 block proof",
    "not gate, value, or down projection proof",
    "not activation, SwiGLU, or residual proof",
    "not binding the full d64 output_activation_commitment",
    "bridge proves only the domain-separated handoff from RMSNorm-local rows to projection-input rows",
]

PROOF_VERIFIER_HARDENING = [
    "source RMSNorm output row commitment recomputation before proof verification",
    "projection input row commitment recomputation before proof verification",
    "AIR equality between RMSNorm-local rows and projection-input rows",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_rmsnorm_to_projection_bridge_input.py --write-json docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_rmsnorm_to_projection_bridge_input",
    "cargo +nightly-2025-07-14 test d64_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "row_count",
    "source_rmsnorm_public_row_proof_version",
    "source_rmsnorm_output_row_commitment",
    "projection_input_row_commitment",
    "projection_input_relabels_full_output",
    "non_claims",
    "next_backend_step",
)


class BridgeInputError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def sequence_commitment(values: list[int], domain: str) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": [WIDTH],
            "values_sha256": hashlib.sha256(canonical_json_bytes(values)).hexdigest(),
        },
        domain,
    )


def load_source(path: pathlib.Path = SOURCE_JSON) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise BridgeInputError(f"failed to load source RMSNorm public-row evidence: {err}") from err
    validate_source(payload)
    return payload


def validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise BridgeInputError("source evidence must be an object")
    if source.get("schema") != "zkai-d64-native-rmsnorm-public-row-air-proof-input-v2":
        raise BridgeInputError("source schema mismatch")
    if source.get("target_id") != TARGET_ID:
        raise BridgeInputError("source target mismatch")
    if source.get("width") != WIDTH or source.get("row_count") != WIDTH:
        raise BridgeInputError("source width/row_count mismatch")
    rows = source.get("rows")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise BridgeInputError("source rows mismatch")
    values = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("index") != index:
            raise BridgeInputError("source row index mismatch")
        value = row.get("normed_q8")
        if not isinstance(value, int):
            raise BridgeInputError("source normed_q8 must be integer")
        values.append(value)
    if source.get("rmsnorm_output_row_commitment") != sequence_commitment(values, RMSNORM_OUTPUT_ROW_DOMAIN):
        raise BridgeInputError("source RMSNorm output row commitment drift")
    if source.get("rmsnorm_output_row_commitment") != RMSNORM_OUTPUT_ROW_COMMITMENT:
        raise BridgeInputError("source RMSNorm output row commitment constant drift")


def build_payload(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source() if source is None else source
    validate_source(source)
    rows = [
        {
            "index": row["index"],
            "rmsnorm_normed_q8": row["normed_q8"],
            "projection_input_q8": row["normed_q8"],
        }
        for row in source["rows"]
    ]
    values = [row["projection_input_q8"] for row in rows]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_rmsnorm_public_row_proof_version": SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source_rmsnorm_output_row_commitment": source["rmsnorm_output_row_commitment"],
        "projection_input_row_commitment": sequence_commitment(values, PROJECTION_INPUT_ROW_DOMAIN),
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
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
        raise BridgeInputError("payload must be an object")
    expected_fields = {
        "schema",
        "decision",
        "target_id",
        "required_backend_version",
        "verifier_domain",
        "width",
        "row_count",
        "source_rmsnorm_public_row_proof_version",
        "source_rmsnorm_output_row_commitment",
        "projection_input_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "rows",
        "non_claims",
        "proof_verifier_hardening",
        "next_backend_step",
        "validation_commands",
    }
    if set(payload) != expected_fields:
        raise BridgeInputError("payload field set mismatch")
    if payload.get("projection_input_row_commitment") == OUTPUT_ACTIVATION_COMMITMENT:
        raise BridgeInputError("projection input commitment relabeled as full output commitment")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_rmsnorm_public_row_proof_version": SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source_rmsnorm_output_row_commitment": RMSNORM_OUTPUT_ROW_COMMITMENT,
        "projection_input_row_commitment": PROJECTION_INPUT_ROW_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise BridgeInputError(f"payload field mismatch: {field}")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise BridgeInputError("row vector mismatch")
    rms_values = []
    projection_values = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"index", "rmsnorm_normed_q8", "projection_input_q8"}:
            raise BridgeInputError("row field set mismatch")
        if row["index"] != index:
            raise BridgeInputError("row index drift")
        if not isinstance(row["rmsnorm_normed_q8"], int) or not isinstance(row["projection_input_q8"], int):
            raise BridgeInputError("row values must be integers")
        if row["rmsnorm_normed_q8"] != row["projection_input_q8"]:
            raise BridgeInputError("bridge row equality drift")
        rms_values.append(row["rmsnorm_normed_q8"])
        projection_values.append(row["projection_input_q8"])
    if sequence_commitment(rms_values, RMSNORM_OUTPUT_ROW_DOMAIN) != payload["source_rmsnorm_output_row_commitment"]:
        raise BridgeInputError("source RMSNorm output commitment recomputation drift")
    if sequence_commitment(projection_values, PROJECTION_INPUT_ROW_DOMAIN) != payload["projection_input_row_commitment"]:
        raise BridgeInputError("projection input commitment recomputation drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    return [
        {
            "target_id": payload["target_id"],
            "decision": payload["decision"],
            "width": payload["width"],
            "row_count": payload["row_count"],
            "source_rmsnorm_public_row_proof_version": payload["source_rmsnorm_public_row_proof_version"],
            "source_rmsnorm_output_row_commitment": payload["source_rmsnorm_output_row_commitment"],
            "projection_input_row_commitment": payload["projection_input_row_commitment"],
            "projection_input_relabels_full_output": str(
                payload["projection_input_row_commitment"] == OUTPUT_ACTIVATION_COMMITMENT
            ).lower(),
            "non_claims": len(payload["non_claims"]),
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
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "decision": payload["decision"],
                    "source_rmsnorm_output_row_commitment": payload["source_rmsnorm_output_row_commitment"],
                    "projection_input_row_commitment": payload["projection_input_row_commitment"],
                    "projection_input_relabels_full_output": False,
                    "row_count": payload["row_count"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
