#!/usr/bin/env python3
"""Canonical d64 RMSNorm-SwiGLU statement fixture.

This is not a proof benchmark.  It fixes the statement surface that a future
Stwo vector-row AIR/export path must prove: deterministic weights, input,
fixed-point config, output, and commitments for a d=64 RMSNorm-SwiGLU-residual
block.  The point is to make the next prover target stable before implementing
the backend.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]

SCHEMA = "zkai-d64-rmsnorm-swiglu-statement-fixture-v1"
RECEIPT_VERSION = "zkai-statement-target-v1"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v1"
MODEL_ID = "urn:zkai:ptvm:rmsnorm-swiglu-residual-d64-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v1"
PROOF_STATUS = "REFERENCE_FIXTURE_NOT_PROVEN"
WIDTH = 64
FF_DIM_MULTIPLIER = 4
FF_DIM = WIDTH * FF_DIM_MULTIPLIER
SCALE_Q8 = 256
ACTIVATION_CLAMP_Q8 = 1024
SEED = "zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05-v1"
DEFAULT_SOURCE_DATE_EPOCH = 0

JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.tsv"

TSV_COLUMNS = (
    "target_id",
    "proof_status",
    "width",
    "ff_dim",
    "linear_projection_muls",
    "projection_weight_scalars",
    "rms_scale_scalars",
    "total_committed_parameter_scalars",
    "statement_fixture_valid",
    "mutations_checked",
    "mutations_rejected",
    "weight_commitment",
    "input_commitment",
    "output_commitment",
    "statement_commitment",
)


class StatementFixtureError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(DEFAULT_SOURCE_DATE_EPOCH))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise StatementFixtureError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise StatementFixtureError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _git_commit() -> str:
    return os.environ.get("ZKAI_GIT_COMMIT") or "unspecified"


def _deterministic_int(label: str, *indices: int, min_value: int, max_value: int) -> int:
    if min_value > max_value:
        raise StatementFixtureError("invalid deterministic integer range")
    payload = ":".join([SEED, label, *(str(index) for index in indices)]).encode("utf-8")
    raw = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return min_value + raw % (max_value - min_value + 1)


def input_vector() -> list[int]:
    return [_deterministic_int("input_q8", i, min_value=-192, max_value=192) for i in range(WIDTH)]


def rms_scale_vector() -> list[int]:
    return [_deterministic_int("rms_scale_q8", i, min_value=224, max_value=288) for i in range(WIDTH)]


def weight_value(matrix: str, row: int, col: int) -> int:
    if matrix not in {"gate", "value", "down"}:
        raise StatementFixtureError(f"unknown matrix: {matrix}")
    return _deterministic_int(f"{matrix}_weight_q8", row, col, min_value=-8, max_value=8)


def _sequence_commitment(values: list[int], domain: str, shape: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": shape,
            "values_sha256": sha256_bytes(canonical_json_bytes(values)),
        },
        domain,
    )


def matrix_commitment(matrix: str, rows: int, cols: int) -> str:
    values = [weight_value(matrix, row, col) for row in range(rows) for col in range(cols)]
    return _sequence_commitment(values, f"ptvm:zkai:d64-{matrix}-matrix:v1", [rows, cols])


def activation_lut_value(x_q8: int) -> int:
    """Integer bounded SiLU-like lookup entry in q8 units.

    The rational sigmoid approximation keeps this fixture deterministic and
    easy to port into an AIR lookup table.  This fixture is therefore a
    quantized SwiGLU target, not a floating-point PyTorch equivalence claim.
    """

    x_q8 = max(-ACTIVATION_CLAMP_Q8, min(ACTIVATION_CLAMP_Q8, x_q8))
    sigmoid_q16 = 32768 + (32768 * x_q8) // (abs(x_q8) + ACTIVATION_CLAMP_Q8)
    sigmoid_q16 = max(0, min(65536, sigmoid_q16))
    return (x_q8 * sigmoid_q16) // 65536


def activation_table() -> list[int]:
    return [activation_lut_value(x) for x in range(-ACTIVATION_CLAMP_Q8, ACTIVATION_CLAMP_Q8 + 1)]


def _project(normed: list[int], matrix: str, rows: int, cols: int) -> list[int]:
    out: list[int] = []
    for row in range(rows):
        acc = 0
        for col in range(cols):
            acc += normed[col] * weight_value(matrix, row, col)
        out.append(acc // cols)
    return out


def evaluate_reference_block() -> dict[str, Any]:
    x = input_vector()
    gamma = rms_scale_vector()
    sum_squares = sum(value * value for value in x)
    rms_q8 = max(1, math.isqrt(max(1, sum_squares // WIDTH)))
    normed = [((value * scale) // SCALE_Q8 * SCALE_Q8) // rms_q8 for value, scale in zip(x, gamma, strict=True)]

    gate = _project(normed, "gate", FF_DIM, WIDTH)
    value = _project(normed, "value", FF_DIM, WIDTH)
    activated_gate = [activation_lut_value(item) for item in gate]
    hidden = [(gate_item * value_item) // SCALE_Q8 for gate_item, value_item in zip(activated_gate, value, strict=True)]

    delta: list[int] = []
    for row in range(WIDTH):
        acc = 0
        for col in range(FF_DIM):
            acc += hidden[col] * weight_value("down", row, col)
        delta.append(acc // FF_DIM)
    output = [base + change for base, change in zip(x, delta, strict=True)]

    return {
        "input_q8": x,
        "rms_scale_q8": gamma,
        "rms_q8": rms_q8,
        "normed_q8": normed,
        "gate_projection_q8": gate,
        "value_projection_q8": value,
        "activated_gate_q8": activated_gate,
        "hidden_q8": hidden,
        "residual_delta_q8": delta,
        "output_q8": output,
    }


def target_spec() -> dict[str, Any]:
    linear_projection_muls = 3 * WIDTH * FF_DIM
    rms_scale_scalars = WIDTH
    return {
        "target_id": TARGET_ID,
        "statement_kind": "transformer-block",
        "model_id": MODEL_ID,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "ff_dim_multiplier": FF_DIM_MULTIPLIER,
        "normalization": "RMSNorm",
        "activation": "bounded_integer_silu_lookup_for_swiglu",
        "residual": True,
        "fixed_point": "q8_signed_integer",
        "linear_projection_muls": linear_projection_muls,
        "swiglu_gate_muls": FF_DIM,
        "rms_square_rows": WIDTH,
        "projection_weight_scalars": linear_projection_muls,
        "rms_scale_scalars": rms_scale_scalars,
        "total_committed_parameter_scalars": linear_projection_muls + rms_scale_scalars,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
    }


def commitments(reference: dict[str, Any]) -> dict[str, str]:
    config = target_spec()
    matrix_commitments = {
        "gate": matrix_commitment("gate", FF_DIM, WIDTH),
        "value": matrix_commitment("value", FF_DIM, WIDTH),
        "down": matrix_commitment("down", WIDTH, FF_DIM),
    }
    return {
        "model_artifact_commitment": blake2b_commitment(
            {
                "model_id": MODEL_ID,
                "weight_generator_seed": SEED,
                "matrix_commitments": matrix_commitments,
                "rms_scale_commitment": _sequence_commitment(
                    reference["rms_scale_q8"], "ptvm:zkai:d64-rms-scale:v1", [WIDTH]
                ),
            },
            "ptvm:zkai:d64-model-artifact:v1",
        ),
        "model_config_commitment": blake2b_commitment(config, "ptvm:zkai:d64-config:v1"),
        "weight_commitment": blake2b_commitment(matrix_commitments, "ptvm:zkai:d64-weights:v1"),
        "input_activation_commitment": _sequence_commitment(
            reference["input_q8"], "ptvm:zkai:d64-input-activation:v1", [WIDTH]
        ),
        "output_activation_commitment": _sequence_commitment(
            reference["output_q8"], "ptvm:zkai:d64-output-activation:v1", [WIDTH]
        ),
        "normalization_config_commitment": blake2b_commitment(
            {
                "rms_q8": reference["rms_q8"],
                "rms_square_rows": WIDTH,
                "scale_commitment": _sequence_commitment(
                    reference["rms_scale_q8"], "ptvm:zkai:d64-rms-scale:v1", [WIDTH]
                ),
            },
            "ptvm:zkai:d64-rmsnorm-config:v1",
        ),
        "activation_lookup_commitment": _sequence_commitment(
            activation_table(),
            "ptvm:zkai:d64-bounded-silu-lut:v1",
            [2 * ACTIVATION_CLAMP_Q8 + 1],
        ),
    }


def statement_payload(reference: dict[str, Any], binding: dict[str, str]) -> dict[str, Any]:
    public_instance = {
        "target_id": TARGET_ID,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "input_activation_commitment": binding["input_activation_commitment"],
        "output_activation_commitment": binding["output_activation_commitment"],
        "model_config_commitment": binding["model_config_commitment"],
    }
    statement = {
        "receipt_version": RECEIPT_VERSION,
        "statement_kind": "transformer-block",
        "model_id": MODEL_ID,
        "verifier_domain": "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v1",
        "proof_system": "stwo-transparent-stark",
        "proof_status": PROOF_STATUS,
        "proof_system_version_required": REQUIRED_BACKEND_VERSION,
        "model_artifact_commitment": binding["model_artifact_commitment"],
        "model_config_commitment": binding["model_config_commitment"],
        "weight_commitment": binding["weight_commitment"],
        "input_activation_commitment": binding["input_activation_commitment"],
        "output_activation_commitment": binding["output_activation_commitment"],
        "normalization_config_commitment": binding["normalization_config_commitment"],
        "activation_lookup_commitment": binding["activation_lookup_commitment"],
        "public_instance_commitment": blake2b_commitment(public_instance, "ptvm:zkai:d64-public-instance:v1"),
        "proof_commitment": None,
        "verifying_key_commitment": None,
        "setup_commitment": None,
        "reference_output_sha256": sha256_bytes(canonical_json_bytes(reference["output_q8"])),
    }
    statement["statement_commitment"] = blake2b_commitment(statement, "ptvm:zkai:d64-statement:v1")
    return statement


def build_fixture() -> dict[str, Any]:
    reference = evaluate_reference_block()
    binding = commitments(reference)
    statement = statement_payload(reference, binding)
    expected_statement = statement_payload(reference, binding)
    mutations = run_mutation_suite(statement, expected_statement)
    return {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": "GO_STATEMENT_TARGET_PINNED_NOT_PROVEN",
        "target": target_spec(),
        "reference_semantics": {
            "seed": SEED,
            "input_sample_q8": reference["input_q8"][:8],
            "output_sample_q8": reference["output_q8"][:8],
            "rms_q8": reference["rms_q8"],
            "activation_lut_domain_q8": [-ACTIVATION_CLAMP_Q8, ACTIVATION_CLAMP_Q8],
            "activation_lut_sample_q8": activation_table()[::512],
            "output_min_q8": min(reference["output_q8"]),
            "output_max_q8": max(reference["output_q8"]),
        },
        "commitments": binding,
        "statement": statement,
        "mutation_suite": mutations,
        "implementation_status": {
            "proof_status": PROOF_STATUS,
            "what_this_is": "canonical committed statement fixture for the next d64 prover target",
            "what_this_is_not": [
                "not a Stwo proof",
                "not a verifier-time benchmark",
                "not a PyTorch equivalence claim",
                "not a full transformer inference claim",
            ],
            "next_backend_work": [
                "encode the RMSNorm rows against the committed scale vector",
                "encode gate/value/down projection rows against committed matrices",
                "encode bounded SiLU lookup and SwiGLU multiplication rows",
                "bind the proof public instance to this statement payload",
            ],
        },
    }


def _expected_statement() -> dict[str, Any]:
    reference = evaluate_reference_block()
    binding = commitments(reference)
    return statement_payload(reference, binding)


def _statement_commitment_from_payload(statement: dict[str, Any]) -> str:
    payload = copy.deepcopy(statement)
    payload.pop("statement_commitment")
    return blake2b_commitment(payload, "ptvm:zkai:d64-statement:v1")


def _validate_statement_against_expected(statement: dict[str, Any], expected: dict[str, Any]) -> None:
    if not isinstance(statement, dict):
        raise StatementFixtureError("statement must be an object")

    expected_keys = set(expected)
    actual_keys = set(statement)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise StatementFixtureError(f"statement field set mismatch: missing={missing}, extra={extra}")

    for field, value in expected.items():
        if field == "statement_commitment":
            continue
        if statement[field] != value:
            raise StatementFixtureError(f"statement field mismatch: {field}")

    if statement["statement_commitment"] != _statement_commitment_from_payload(statement):
        raise StatementFixtureError("statement field mismatch: statement_commitment")

    if statement["statement_commitment"] != expected["statement_commitment"]:
        raise StatementFixtureError("statement field mismatch: statement_commitment")


def validate_statement(statement: dict[str, Any]) -> None:
    _validate_statement_against_expected(statement, _expected_statement())


def mutate_statement(statement: dict[str, Any], field: str, value: Any) -> dict[str, Any]:
    out = copy.deepcopy(statement)
    out[field] = value
    return out


def mutation_cases(statement: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wrong_commitment = "blake2b-256:" + "00" * 32
    wrong_sha256 = "00" * 32
    return {
        "model_id_relabeling": mutate_statement(statement, "model_id", "urn:zkai:ptvm:different-d64-block"),
        "verifier_domain_relabeling": mutate_statement(statement, "verifier_domain", "ptvm:zkai:wrong-domain:v1"),
        "backend_version_relabeling": mutate_statement(
            statement, "proof_system_version_required", "stwo-different-backend"
        ),
        "model_artifact_commitment_relabeling": mutate_statement(
            statement, "model_artifact_commitment", wrong_commitment
        ),
        "model_config_commitment_relabeling": mutate_statement(
            statement, "model_config_commitment", wrong_commitment
        ),
        "weight_commitment_relabeling": mutate_statement(statement, "weight_commitment", wrong_commitment),
        "input_activation_commitment_relabeling": mutate_statement(
            statement, "input_activation_commitment", wrong_commitment
        ),
        "output_activation_commitment_relabeling": mutate_statement(
            statement, "output_activation_commitment", wrong_commitment
        ),
        "normalization_config_commitment_relabeling": mutate_statement(
            statement, "normalization_config_commitment", wrong_commitment
        ),
        "activation_lookup_commitment_relabeling": mutate_statement(
            statement, "activation_lookup_commitment", wrong_commitment
        ),
        "public_instance_commitment_relabeling": mutate_statement(
            statement, "public_instance_commitment", wrong_commitment
        ),
        "statement_commitment_relabeling": mutate_statement(statement, "statement_commitment", wrong_commitment),
        "proof_status_overclaim": mutate_statement(statement, "proof_status", "PROVEN"),
        "reference_output_relabeling": mutate_statement(statement, "reference_output_sha256", wrong_sha256),
    }


def run_mutation_suite(statement: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    _validate_statement_against_expected(statement, expected)
    cases = []
    for name, mutated in mutation_cases(statement).items():
        try:
            _validate_statement_against_expected(mutated, expected)
        except StatementFixtureError as err:
            cases.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "reason": "accepted"})
    rejected = sum(1 for case in cases if case["rejected"])
    return {
        "baseline_valid": True,
        "mutations_checked": len(cases),
        "mutations_rejected": rejected,
        "decision": "GO" if rejected == len(cases) else "NO_GO",
        "cases": cases,
    }


def validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise StatementFixtureError("payload must be an object")
    canonical = build_fixture()
    for field in (
        "schema",
        "generated_at",
        "git_commit",
        "decision",
        "target",
        "reference_semantics",
        "commitments",
        "statement",
        "mutation_suite",
        "implementation_status",
    ):
        if payload.get(field) != canonical[field]:
            raise StatementFixtureError(f"payload {field} does not match canonical fixture")
    statement = payload.get("statement")
    validate_statement(statement)


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_payload(payload)
    target = target_spec()
    statement = payload["statement"]
    mutations = payload["mutation_suite"]
    return [
        {
            "target_id": target["target_id"],
            "proof_status": statement["proof_status"],
            "width": target["width"],
            "ff_dim": target["ff_dim"],
            "linear_projection_muls": target["linear_projection_muls"],
            "projection_weight_scalars": target["projection_weight_scalars"],
            "rms_scale_scalars": target["rms_scale_scalars"],
            "total_committed_parameter_scalars": target["total_committed_parameter_scalars"],
            "statement_fixture_valid": str(mutations["baseline_valid"]).lower(),
            "mutations_checked": mutations["mutations_checked"],
            "mutations_rejected": mutations["mutations_rejected"],
            "weight_commitment": statement["weight_commitment"],
            "input_commitment": statement["input_activation_commitment"],
            "output_commitment": statement["output_activation_commitment"],
            "statement_commitment": statement["statement_commitment"],
        }
    ]


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    rows = rows_for_tsv(payload)
    try:
        if json_path is not None:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if tsv_path is not None:
            tsv_path.parent.mkdir(parents=True, exist_ok=True)
            with tsv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
    except OSError as err:
        raise StatementFixtureError(f"failed to write statement fixture output: {err}") from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_fixture()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "decision": payload["decision"],
                "proof_status": payload["implementation_status"]["proof_status"],
                "mutations_rejected": payload["mutation_suite"]["mutations_rejected"],
                "mutations_checked": payload["mutation_suite"]["mutations_checked"],
                "statement_commitment": payload["statement"]["statement_commitment"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
