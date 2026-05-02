#!/usr/bin/env python3
"""Build the d64 residual-add proof input.

This native-proof input consumes the down-projection residual-delta commitment
and the canonical public input-activation commitment, checks the residual-add
rows, and emits the final d64 output-activation commitment. It intentionally
stays a single-slice proof input: it does not claim recursive composition of all
preceding slices or private parameter openings.
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
DOWN_PROJECTION_SCRIPT_PATH = ROOT / "scripts" / "zkai_d64_down_projection_proof_input.py"
SOURCE_JSON = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-down-projection-proof-2026-05.json"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-residual-add-proof-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-residual-add-proof-2026-05.tsv"

SCHEMA = "zkai-d64-residual-add-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_D64_RESIDUAL_ADD_AIR_PROOF"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v2"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v2"
VERIFIER_DOMAIN = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2"
WIDTH = 64
M31_MODULUS = (1 << 31) - 1
MAX_SOURCE_JSON_BYTES = 1_048_576
Q8_SEMANTIC_ABS_BOUND = 1024
SOURCE_DOWN_PROJECTION_SCHEMA = "zkai-d64-down-projection-air-proof-input-v1"
SOURCE_DOWN_PROJECTION_DECISION = "GO_INPUT_FOR_D64_DOWN_PROJECTION_AIR_PROOF"
SOURCE_DOWN_PROJECTION_PROOF_VERSION = "stwo-d64-down-projection-air-proof-v1"
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d"
STATEMENT_COMMITMENT = "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38"
INPUT_ACTIVATION_COMMITMENT = "blake2b-256:4f765c71601320b3ee9341056299e79a004fa94aaa2edcb5c161cb7366b051fc"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f"
RESIDUAL_DELTA_COMMITMENT = "blake2b-256:ff67391fd2636e118af323efb1ed559114421a96e8ea30a7424c114e7074622a"
INPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d64-input-activation:v1"
OUTPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d64-output-activation:v1"
RESIDUAL_DELTA_DOMAIN = "ptvm:zkai:d64-residual-delta:v1"
RESIDUAL_ADD_ROW_DOMAIN = "ptvm:zkai:d64-residual-add-rows:v1"
NEXT_BACKEND_STEP = "compose the d64 proof slices into a single statement-bound block receipt"

NON_CLAIMS = [
    "not recursive composition of all d64 proof slices",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not verifier-time benchmark evidence",
    "not onchain deployment evidence",
]

PROOF_VERIFIER_HARDENING = [
    "source down-projection residual-delta commitment recomputation before proof verification",
    "canonical input activation commitment recomputation before proof verification",
    "residual-add row commitment recomputation before proof verification",
    "final output activation commitment recomputation before proof verification",
    "AIR residual-add relation for every checked d64 output coordinate",
    "explicit fixed-point q8 semantic bounds for input, residual delta, and output activations",
    "intermediate commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_residual_add_proof_input.py --write-json docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_residual_add_proof_input",
    "cargo +nightly-2025-07-14 test d64_native_residual_add_proof --lib --features stwo-backend",
]

TSV_COLUMNS = (
    "target_id",
    "decision",
    "width",
    "row_count",
    "source_down_projection_proof_version",
    "input_activation_commitment",
    "residual_delta_commitment",
    "output_activation_commitment",
    "residual_add_row_commitment",
    "residual_delta_relabels_full_output",
    "input_relabels_output",
    "non_claims",
    "next_backend_step",
)


class ResidualAddInputError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ResidualAddInputError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_module(FIXTURE_PATH, "zkai_d64_rmsnorm_swiglu_statement_fixture")
DOWN_PROJECTION = _load_module(DOWN_PROJECTION_SCRIPT_PATH, "zkai_d64_down_projection_proof_input")


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
        raise ResidualAddInputError(f"{label} outside signed M31 bounds")


def require_signed_q8(value: int, label: str) -> None:
    if not (-Q8_SEMANTIC_ABS_BOUND <= value <= Q8_SEMANTIC_ABS_BOUND):
        raise ResidualAddInputError(f"{label} outside fixed-point q8 semantic bounds")


def load_source(path: pathlib.Path = SOURCE_JSON) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise ResidualAddInputError(f"source down-projection evidence is not a regular file: {path}")
        with path.open("rb") as source_file:
            source_bytes = source_file.read(MAX_SOURCE_JSON_BYTES + 1)
        if len(source_bytes) > MAX_SOURCE_JSON_BYTES:
            raise ResidualAddInputError(
                f"source down-projection evidence exceeds max size: got at least {len(source_bytes)} bytes, limit {MAX_SOURCE_JSON_BYTES} bytes"
            )
        payload = json.loads(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ResidualAddInputError(f"failed to load down-projection evidence: {err}") from err
    validate_source(payload)
    return payload


def validate_source(source: Any) -> None:
    if not isinstance(source, dict):
        raise ResidualAddInputError("source down-projection evidence must be an object")
    constants = {
        "schema": SOURCE_DOWN_PROJECTION_SCHEMA,
        "decision": SOURCE_DOWN_PROJECTION_DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "residual_delta_rows": WIDTH,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "residual_delta_commitment": RESIDUAL_DELTA_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
    }
    for field, expected in constants.items():
        if source.get(field) != expected:
            raise ResidualAddInputError(f"source down-projection field mismatch: {field}")
    try:
        DOWN_PROJECTION.validate_payload(source)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors for this script.
        raise ResidualAddInputError(f"source down-projection validation failed: {err}") from err


def source_residual_delta(source: dict[str, Any]) -> list[int]:
    validate_source(source)
    residual_delta = source["residual_delta_q8"]
    if not isinstance(residual_delta, list) or len(residual_delta) != WIDTH:
        raise ResidualAddInputError("source residual delta vector mismatch")
    for index, item in enumerate(residual_delta):
        if not isinstance(item, int):
            raise ResidualAddInputError("source residual delta values must be integers")
        require_signed_q8(item, f"source residual delta {index}")
        require_signed_m31(item, f"source residual delta {index}")
    if sequence_commitment(residual_delta, RESIDUAL_DELTA_DOMAIN, [WIDTH]) != source["residual_delta_commitment"]:
        raise ResidualAddInputError("source residual delta commitment drift")
    return residual_delta


def rows_commitment(rows: list[dict[str, int]]) -> str:
    material = [
        [
            row["row_index"],
            row["input_q8"],
            row["residual_delta_q8"],
            row["output_q8"],
        ]
        for row in rows
    ]
    return blake2b_commitment(
        {
            "encoding": "d64_residual_add_rows_v1",
            "shape": [len(rows), 4],
            "rows_sha256": sha256_hex(material),
        },
        RESIDUAL_ADD_ROW_DOMAIN,
    )


def build_rows(input_q8: list[int], residual_delta_q8: list[int]) -> list[dict[str, int]]:
    if len(input_q8) != WIDTH:
        raise ResidualAddInputError("input activation vector length mismatch")
    if len(residual_delta_q8) != WIDTH:
        raise ResidualAddInputError("residual delta vector length mismatch")
    rows: list[dict[str, int]] = []
    for row_index, (base, delta) in enumerate(zip(input_q8, residual_delta_q8, strict=True)):
        require_signed_q8(base, f"input activation {row_index}")
        require_signed_q8(delta, f"residual delta {row_index}")
        output = base + delta
        require_signed_q8(output, f"output activation {row_index}")
        require_signed_m31(output, f"output activation {row_index}")
        rows.append(
            {
                "row_index": row_index,
                "input_q8": base,
                "residual_delta_q8": delta,
                "output_q8": output,
            }
        )
    return rows


def build_payload(source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = load_source() if source is None else source
    residual_delta = source_residual_delta(source)
    reference = FIXTURE.evaluate_reference_block()
    input_q8 = reference["input_q8"]
    output_q8 = reference["output_q8"]
    rows = build_rows(input_q8, residual_delta)
    if [row["output_q8"] for row in rows] != output_q8:
        raise ResidualAddInputError("residual-add output does not match canonical reference")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": len(rows),
        "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
        "input_activation_commitment": sequence_commitment(input_q8, INPUT_ACTIVATION_DOMAIN, [WIDTH]),
        "residual_delta_commitment": source["residual_delta_commitment"],
        "output_activation_commitment": sequence_commitment(output_q8, OUTPUT_ACTIVATION_DOMAIN, [WIDTH]),
        "residual_add_row_commitment": rows_commitment(rows),
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "input_q8": input_q8,
        "residual_delta_q8": residual_delta,
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
        raise ResidualAddInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "target_id", "required_backend_version", "verifier_domain", "width", "row_count",
        "source_down_projection_proof_version", "input_activation_commitment", "residual_delta_commitment",
        "output_activation_commitment", "residual_add_row_commitment", "proof_native_parameter_commitment",
        "public_instance_commitment", "statement_commitment", "input_q8", "residual_delta_q8", "output_q8",
        "rows", "non_claims", "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise ResidualAddInputError("payload field set mismatch")
    if payload["residual_delta_commitment"] == payload["output_activation_commitment"]:
        raise ResidualAddInputError("residual delta commitment relabeled as full output commitment")
    if payload["input_activation_commitment"] == payload["output_activation_commitment"]:
        raise ResidualAddInputError("input activation commitment relabeled as output activation commitment")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
        "residual_delta_commitment": RESIDUAL_DELTA_COMMITMENT,
        "output_activation_commitment": OUTPUT_ACTIVATION_COMMITMENT,
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
            raise ResidualAddInputError(f"payload field mismatch: {field}")
    input_q8 = payload["input_q8"]
    residual_delta_q8 = payload["residual_delta_q8"]
    output_q8 = payload["output_q8"]
    rows = payload["rows"]
    for label, values in (("input activation", input_q8), ("residual delta", residual_delta_q8), ("output activation", output_q8)):
        if not isinstance(values, list) or len(values) != WIDTH:
            raise ResidualAddInputError(f"{label} vector mismatch")
        for index, item in enumerate(values):
            if not isinstance(item, int):
                raise ResidualAddInputError(f"{label} values must be integers")
            require_signed_q8(item, f"{label} {index}")
            require_signed_m31(item, f"{label} {index}")
    if sequence_commitment(input_q8, INPUT_ACTIVATION_DOMAIN, [WIDTH]) != payload["input_activation_commitment"]:
        raise ResidualAddInputError("input activation commitment drift")
    if sequence_commitment(residual_delta_q8, RESIDUAL_DELTA_DOMAIN, [WIDTH]) != payload["residual_delta_commitment"]:
        raise ResidualAddInputError("residual delta commitment drift")
    if sequence_commitment(output_q8, OUTPUT_ACTIVATION_DOMAIN, [WIDTH]) != payload["output_activation_commitment"]:
        raise ResidualAddInputError("output activation commitment drift")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise ResidualAddInputError("row vector mismatch")
    recomputed_rows = build_rows(input_q8, residual_delta_q8)
    if rows != recomputed_rows:
        raise ResidualAddInputError("residual-add row relation drift")
    if [row["output_q8"] for row in rows] != output_q8:
        raise ResidualAddInputError("output activation row drift")
    if rows_commitment(rows) != payload["residual_add_row_commitment"]:
        raise ResidualAddInputError("residual-add row commitment drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    return [
        {
            "target_id": payload["target_id"],
            "decision": payload["decision"],
            "width": payload["width"],
            "row_count": payload["row_count"],
            "source_down_projection_proof_version": payload["source_down_projection_proof_version"],
            "input_activation_commitment": payload["input_activation_commitment"],
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "output_activation_commitment": payload["output_activation_commitment"],
            "residual_add_row_commitment": payload["residual_add_row_commitment"],
            "residual_delta_relabels_full_output": str(payload["residual_delta_commitment"] == payload["output_activation_commitment"]).lower(),
            "input_relabels_output": str(payload["input_activation_commitment"] == payload["output_activation_commitment"]).lower(),
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
        "input_activation_commitment": payload["input_activation_commitment"],
        "residual_delta_commitment": payload["residual_delta_commitment"],
        "output_activation_commitment": payload["output_activation_commitment"],
        "residual_add_row_commitment": payload["residual_add_row_commitment"],
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
