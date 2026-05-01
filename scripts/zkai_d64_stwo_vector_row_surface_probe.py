#!/usr/bin/env python3
"""Stwo vector-row surface probe for the canonical d64 zkAI statement.

This is not a proof benchmark. It asks whether the exact d64 RMSNorm-SwiGLU
statement is blocked by arithmetic size or by statement/commitment consistency
before we implement the native Stwo AIR.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

FIXTURE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-stwo-vector-row-surface-probe-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-stwo-vector-row-surface-probe-2026-05.tsv"

SCHEMA = "zkai-d64-stwo-vector-row-surface-probe-v2"
PUBLIC_INSTANCE_CONTRACT_SCHEMA = "zkai-d64-stwo-proof-public-instance-contract-v1"
DECISION = "GO_PUBLIC_INSTANCE_CONTRACT_NO_GO_EXACT_PROOF_UNTIL_NATIVE_AIR"
SOURCE_DATE_EPOCH_DEFAULT = 0
M31_MODULUS = 2**31 - 1
SIGNED_M31_ABS_LIMIT = 2**30 - 1
EXPECTED_TOTAL_PROJECTION_MUL_ROWS = 49_152
EXPECTED_ACTIVATION_TABLE_ROWS = 2_049
EXPECTED_TRACE_ROWS_EXCLUDING_STATIC_TABLE = 49_920

TSV_COLUMNS = (
    "target_id",
    "width",
    "ff_dim",
    "gate",
    "status",
    "projection_mul_rows",
    "trace_rows_excluding_static_table",
    "activation_table_rows",
    "max_abs_intermediate",
    "fits_signed_m31",
    "public_instance_contract_status",
    "public_instance_mutations_rejected",
    "proof_native_parameter_commitment",
    "public_instance_commitment",
    "statement_commitment",
)


class D64VectorRowSurfaceError(ValueError):
    pass


def _load_fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_statement_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise D64VectorRowSurfaceError(f"failed to load d64 fixture from {FIXTURE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_fixture_module()


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
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise D64VectorRowSurfaceError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise D64VectorRowSurfaceError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _validate_generated_at(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise D64VectorRowSurfaceError("generated_at must be a UTC timestamp string")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as err:
        raise D64VectorRowSurfaceError("generated_at must be a valid UTC timestamp string") from err
    if parsed.tzinfo != dt.timezone.utc:
        raise D64VectorRowSurfaceError("generated_at must be a UTC timestamp string")


def _git_commit() -> str:
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


def _range_summary(values: list[int]) -> dict[str, int]:
    if not values:
        raise D64VectorRowSurfaceError("cannot summarize an empty value list")
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "max_abs": max(abs(item) for item in values),
    }


def _projection_stats(inputs: list[int], matrix: str, rows: int, cols: int, expected: list[int]) -> dict[str, int]:
    if len(inputs) != cols:
        raise D64VectorRowSurfaceError(f"{matrix} input width mismatch")
    if len(expected) != rows:
        raise D64VectorRowSurfaceError(f"{matrix} expected output width mismatch")

    weights: list[int] = []
    products: list[int] = []
    accumulators: list[int] = []
    outputs: list[int] = []
    for row in range(rows):
        acc = 0
        for col in range(cols):
            weight = FIXTURE.weight_value(matrix, row, col)
            product = inputs[col] * weight
            weights.append(weight)
            products.append(product)
            acc += product
        accumulators.append(acc)
        outputs.append(acc // cols)
    if outputs != expected:
        raise D64VectorRowSurfaceError(f"{matrix} projection recomputation mismatch")

    return {
        "rows": rows,
        "cols": cols,
        "mul_rows": rows * cols,
        "max_abs_input": max(abs(item) for item in inputs),
        "max_abs_weight": max(abs(item) for item in weights),
        "max_abs_product": max(abs(item) for item in products),
        "max_abs_accumulator": max(abs(item) for item in accumulators),
        "max_abs_output": max(abs(item) for item in outputs),
    }


def _witness_profile(reference: dict[str, Any]) -> dict[str, Any]:
    width = FIXTURE.WIDTH
    ff_dim = FIXTURE.FF_DIM
    target = FIXTURE.target_spec()
    if target["linear_projection_muls"] != EXPECTED_TOTAL_PROJECTION_MUL_ROWS:
        raise D64VectorRowSurfaceError("fixture projection row count drift")

    sum_squares = sum(item * item for item in reference["input_q8"])
    gate_stats = _projection_stats(
        reference["normed_q8"],
        "gate",
        ff_dim,
        width,
        reference["gate_projection_q8"],
    )
    value_stats = _projection_stats(
        reference["normed_q8"],
        "value",
        ff_dim,
        width,
        reference["value_projection_q8"],
    )
    hidden_products = [
        gate * value
        for gate, value in zip(reference["activated_gate_q8"], reference["value_projection_q8"], strict=True)
    ]
    hidden = [item // FIXTURE.SCALE_Q8 for item in hidden_products]
    if hidden != reference["hidden_q8"]:
        raise D64VectorRowSurfaceError("hidden SwiGLU recomputation mismatch")
    down_stats = _projection_stats(
        reference["hidden_q8"],
        "down",
        width,
        ff_dim,
        reference["residual_delta_q8"],
    )
    output = [
        base + delta for base, delta in zip(reference["input_q8"], reference["residual_delta_q8"], strict=True)
    ]
    if output != reference["output_q8"]:
        raise D64VectorRowSurfaceError("residual output recomputation mismatch")

    row_counts = {
        "input_rows": width,
        "rms_square_rows": width,
        "rms_norm_rows": width,
        "gate_projection_mul_rows": gate_stats["mul_rows"],
        "value_projection_mul_rows": value_stats["mul_rows"],
        "activation_lookup_rows": ff_dim,
        "swiglu_mix_rows": ff_dim,
        "down_projection_mul_rows": down_stats["mul_rows"],
        "residual_rows": width,
        "activation_table_rows": len(FIXTURE.activation_table()),
        "projection_mul_rows": gate_stats["mul_rows"] + value_stats["mul_rows"] + down_stats["mul_rows"],
    }
    row_counts["trace_rows_excluding_static_table"] = (
        row_counts["input_rows"]
        + row_counts["rms_square_rows"]
        + row_counts["rms_norm_rows"]
        + row_counts["gate_projection_mul_rows"]
        + row_counts["value_projection_mul_rows"]
        + row_counts["activation_lookup_rows"]
        + row_counts["swiglu_mix_rows"]
        + row_counts["down_projection_mul_rows"]
        + row_counts["residual_rows"]
    )

    value_ranges = {
        "input_q8": _range_summary(reference["input_q8"]),
        "rms_scale_q8": _range_summary(reference["rms_scale_q8"]),
        "normed_q8": _range_summary(reference["normed_q8"]),
        "gate_projection_q8": _range_summary(reference["gate_projection_q8"]),
        "value_projection_q8": _range_summary(reference["value_projection_q8"]),
        "activated_gate_q8": _range_summary(reference["activated_gate_q8"]),
        "hidden_q8": _range_summary(reference["hidden_q8"]),
        "residual_delta_q8": _range_summary(reference["residual_delta_q8"]),
        "output_q8": _range_summary(reference["output_q8"]),
    }
    intermediate_maxima = {
        "sum_squares": abs(sum_squares),
        "rms_q8": abs(reference["rms_q8"]),
        "gate_product": gate_stats["max_abs_product"],
        "gate_accumulator": gate_stats["max_abs_accumulator"],
        "value_product": value_stats["max_abs_product"],
        "value_accumulator": value_stats["max_abs_accumulator"],
        "swiglu_product": max(abs(item) for item in hidden_products),
        "down_product": down_stats["max_abs_product"],
        "down_accumulator": down_stats["max_abs_accumulator"],
    }
    max_abs_intermediate = max(
        [summary["max_abs"] for summary in value_ranges.values()] + list(intermediate_maxima.values())
    )
    fits_signed_m31 = max_abs_intermediate <= SIGNED_M31_ABS_LIMIT

    return {
        "row_counts": row_counts,
        "value_ranges": value_ranges,
        "projection_stats": {
            "gate": gate_stats,
            "value": value_stats,
            "down": down_stats,
        },
        "intermediate_maxima": intermediate_maxima,
        "m31_range": {
            "modulus": M31_MODULUS,
            "signed_abs_limit": SIGNED_M31_ABS_LIMIT,
            "max_abs_intermediate": max_abs_intermediate,
            "fits_signed_m31": fits_signed_m31,
        },
    }


def decision_matrix() -> list[dict[str, str]]:
    return [
        {
            "gate": "vector_row_arithmetic_surface",
            "status": "GO",
            "reason": "The exact fixture recomputes over a bounded row surface with 49,152 projection multiplication rows.",
            "next_action": "Implement AIR rows for RMS square, RMS norm, projections, activation lookup, mix, down projection, and residual add.",
        },
        {
            "gate": "m31_signed_range_fit",
            "status": "GO",
            "reason": "All checked witness and accumulator values fit below the signed M31 safety limit for this fixture.",
            "next_action": "Keep range checks explicit before scaling beyond d64 or changing quantization.",
        },
        {
            "gate": "proof_native_public_instance_contract",
            "status": "GO",
            "reason": "The proof-facing public-instance contract binds proof_native_parameter_commitment together with model config and input/output commitments.",
            "next_action": "Consume the same public-instance contract inside the native AIR/export path, then verify an honest Stwo proof.",
        },
        {
            "gate": "statement_public_instance_binding",
            "status": "PARTIAL",
            "reason": "The statement commitments can be copied into proof-facing public instance fields, but that alone does not prove witness consistency.",
            "next_action": "Bind model, parameter, table, input, and output commitments inside the verified relation, not only in receipt metadata.",
        },
        {
            "gate": "weight_commitment_consistency",
            "status": "NO_GO_YET",
            "reason": "The fixture now exposes a proof-native parameter commitment, but a native proof must still show witness rows match that commitment.",
            "next_action": "Implement the AIR/export rows that consume proof_native_parameter_commitment rather than only carrying it in the public instance.",
        },
        {
            "gate": "activation_table_commitment_consistency",
            "status": "NO_GO_YET",
            "reason": "The bounded SiLU table is represented in the proof-native parameter commitment, but lookup rows are not yet checked by a native proof.",
            "next_action": "Verify activation lookup membership against the committed table inside the native relation.",
        },
        {
            "gate": "native_stwo_exact_d64_proof",
            "status": "NO_GO_YET",
            "reason": "No Stwo proof is generated in this probe; arithmetic feasibility is positive, exact proof status remains blocked on commitment consistency.",
            "next_action": "Do not claim a proved d64 transformer block until the commitment-consistency gates above are implemented and mutation-tested.",
        },
    ]


def expected_non_claims() -> list[str]:
    return [
        "not a Stwo proof",
        "not a verifier-time benchmark",
        "not proof that the d64 statement is accepted",
        "not relation-level consumption of proof_native_parameter_commitment",
        "not backend independence evidence",
        "not full transformer inference",
        "not a claim that commitment consistency is solved",
    ]


def expected_issue_scope() -> dict[str, Any]:
    return {
        "related_issue": 341,
        "closes_related_issue": False,
        "pr_scope": "surface_probe_prerequisite",
        "missing_for_issue_go": [
            "honest_stwo_proof_for_d64_fixture",
            "native_air_consumes_proof_native_parameter_commitment",
            "statement_commitment_consistency_inside_verified_relation",
            "proof_size",
            "proving_time",
            "verifier_time",
            "statement_envelope_overhead",
        ],
    }


def proof_public_instance_contract(fixture: dict[str, Any]) -> dict[str, Any]:
    statement = fixture["statement"]
    binding = fixture["commitments"]
    public_instance = FIXTURE.public_instance_payload(binding)
    public_instance_commitment = FIXTURE.public_instance_commitment(binding)
    if public_instance_commitment != statement["public_instance_commitment"]:
        raise D64VectorRowSurfaceError("fixture public-instance commitment mismatch")
    if public_instance["proof_native_parameter_commitment"] != statement["proof_native_parameter_commitment"]:
        raise D64VectorRowSurfaceError("fixture proof-native parameter commitment mismatch")
    return {
        "schema": PUBLIC_INSTANCE_CONTRACT_SCHEMA,
        "status": "GO_CONTRACT_BOUND_NOT_NATIVE_PROOF",
        "backend_version_required": fixture["target"]["required_backend_version"],
        "verifier_domain": statement["verifier_domain"],
        "public_instance": public_instance,
        "public_instance_commitment": public_instance_commitment,
        "statement_commitment": statement["statement_commitment"],
        "bound_statement_fields": [
            "target_id",
            "width",
            "ff_dim",
            "model_config_commitment",
            "proof_native_parameter_commitment",
            "input_activation_commitment",
            "output_activation_commitment",
            "public_instance_commitment",
            "statement_commitment",
            "verifier_domain",
            "proof_system_version_required",
        ],
        "proof_native_parameter_commitment": statement["proof_native_parameter_commitment"],
        "non_claim": "This is a proof-public-instance contract, not a native Stwo proof.",
    }


def validate_proof_public_instance_contract(contract: dict[str, Any], fixture: dict[str, Any] | None = None) -> None:
    if not isinstance(contract, dict):
        raise D64VectorRowSurfaceError("proof public-instance contract must be an object")
    expected_fields = {
        "schema",
        "status",
        "backend_version_required",
        "verifier_domain",
        "public_instance",
        "public_instance_commitment",
        "statement_commitment",
        "bound_statement_fields",
        "proof_native_parameter_commitment",
        "non_claim",
    }
    if set(contract) != expected_fields:
        raise D64VectorRowSurfaceError("proof public-instance contract field set mismatch")
    fixture = FIXTURE.build_fixture() if fixture is None else fixture
    expected = proof_public_instance_contract(fixture)
    if contract != expected:
        for field in expected_fields:
            if contract.get(field) != expected[field]:
                raise D64VectorRowSurfaceError(f"proof public-instance contract mismatch: {field}")
        raise D64VectorRowSurfaceError("proof public-instance contract mismatch")


def mutate_contract(contract: dict[str, Any], path: tuple[str, ...], value: Any) -> dict[str, Any]:
    out = json.loads(json.dumps(contract))
    cursor = out
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return out


def proof_public_instance_mutation_cases(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wrong_commitment = "blake2b-256:" + "55" * 32
    return {
        "proof_native_parameter_commitment_public_instance_relabeling": mutate_contract(
            contract, ("public_instance", "proof_native_parameter_commitment"), wrong_commitment
        ),
        "proof_native_parameter_commitment_top_level_relabeling": mutate_contract(
            contract, ("proof_native_parameter_commitment",), wrong_commitment
        ),
        "public_instance_commitment_relabeling": mutate_contract(
            contract, ("public_instance_commitment",), wrong_commitment
        ),
        "statement_commitment_relabeling": mutate_contract(contract, ("statement_commitment",), wrong_commitment),
        "model_config_commitment_relabeling": mutate_contract(
            contract, ("public_instance", "model_config_commitment"), wrong_commitment
        ),
        "input_activation_commitment_relabeling": mutate_contract(
            contract, ("public_instance", "input_activation_commitment"), wrong_commitment
        ),
        "output_activation_commitment_relabeling": mutate_contract(
            contract, ("public_instance", "output_activation_commitment"), wrong_commitment
        ),
        "target_id_relabeling": mutate_contract(contract, ("public_instance", "target_id"), "wrong-d64-target"),
        "width_relabeling": mutate_contract(contract, ("public_instance", "width"), FIXTURE.WIDTH + 1),
        "ff_dim_relabeling": mutate_contract(contract, ("public_instance", "ff_dim"), FIXTURE.FF_DIM + 1),
        "backend_version_relabeling": mutate_contract(
            contract, ("backend_version_required",), "stwo-rmsnorm-swiglu-residual-d64-v999"
        ),
        "verifier_domain_relabeling": mutate_contract(
            contract, ("verifier_domain",), "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v999"
        ),
    }


def run_public_instance_mutation_suite(contract: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    validate_proof_public_instance_contract(contract, fixture)
    cases = []
    for name, mutated in proof_public_instance_mutation_cases(contract).items():
        try:
            validate_proof_public_instance_contract(mutated, fixture)
        except D64VectorRowSurfaceError as err:
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


def build_probe() -> dict[str, Any]:
    fixture = FIXTURE.build_fixture()
    FIXTURE.validate_payload(fixture)
    reference = FIXTURE.evaluate_reference_block()
    profile = _witness_profile(reference)
    decisions = decision_matrix()
    public_instance_contract = proof_public_instance_contract(fixture)
    public_instance_mutations = run_public_instance_mutation_suite(public_instance_contract, fixture)
    return {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": DECISION,
        "source_fixture": {
            "schema": fixture["schema"],
            "target_id": fixture["target"]["target_id"],
            "proof_status": fixture["implementation_status"]["proof_status"],
            "statement_commitment": fixture["statement"]["statement_commitment"],
            "proof_native_parameter_commitment": fixture["statement"]["proof_native_parameter_commitment"],
            "public_instance_commitment": fixture["statement"]["public_instance_commitment"],
        },
        "target": fixture["target"],
        "proof_public_instance_contract": public_instance_contract,
        "proof_public_instance_mutation_suite": public_instance_mutations,
        "witness_profile": profile,
        "witness_profile_commitment": blake2b_commitment(profile, "ptvm:zkai:d64-stwo-vector-row-profile:v1"),
        "decision_matrix": decisions,
        "decision_matrix_commitment": blake2b_commitment(decisions, "ptvm:zkai:d64-stwo-vector-row-decisions:v1"),
        "issue_scope": expected_issue_scope(),
        "non_claims": expected_non_claims(),
    }


def validate_probe(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise D64VectorRowSurfaceError("payload must be an object")
    expected_fields = {
        "schema",
        "generated_at",
        "git_commit",
        "decision",
        "source_fixture",
        "target",
        "proof_public_instance_contract",
        "proof_public_instance_mutation_suite",
        "witness_profile",
        "witness_profile_commitment",
        "decision_matrix",
        "decision_matrix_commitment",
        "issue_scope",
        "non_claims",
    }
    if set(payload) != expected_fields:
        raise D64VectorRowSurfaceError("payload field set mismatch")
    if payload["schema"] != SCHEMA:
        raise D64VectorRowSurfaceError("schema mismatch")
    _validate_generated_at(payload["generated_at"])
    git_commit = payload["git_commit"]
    if not isinstance(git_commit, str) or not git_commit:
        raise D64VectorRowSurfaceError("git_commit must be a non-empty string")
    if git_commit != "unavailable" and (
        len(git_commit) != 40 or any(char not in "0123456789abcdef" for char in git_commit)
    ):
        raise D64VectorRowSurfaceError("git_commit must be a full lowercase hex commit hash")
    if payload["decision"] != DECISION:
        raise D64VectorRowSurfaceError("decision mismatch")

    fixture = FIXTURE.build_fixture()
    expected_source = {
        "schema": fixture["schema"],
        "target_id": fixture["target"]["target_id"],
        "proof_status": fixture["implementation_status"]["proof_status"],
        "statement_commitment": fixture["statement"]["statement_commitment"],
        "proof_native_parameter_commitment": fixture["statement"]["proof_native_parameter_commitment"],
        "public_instance_commitment": fixture["statement"]["public_instance_commitment"],
    }
    if payload["source_fixture"] != expected_source:
        raise D64VectorRowSurfaceError("source fixture drift")
    if payload["target"] != fixture["target"]:
        raise D64VectorRowSurfaceError("target drift")
    validate_proof_public_instance_contract(payload["proof_public_instance_contract"], fixture)
    expected_mutations = run_public_instance_mutation_suite(payload["proof_public_instance_contract"], fixture)
    if payload["proof_public_instance_mutation_suite"] != expected_mutations:
        raise D64VectorRowSurfaceError("proof public-instance mutation suite drift")
    if expected_mutations["decision"] != "GO":
        raise D64VectorRowSurfaceError("proof public-instance mutation suite must reject all cases")

    expected_profile = _witness_profile(FIXTURE.evaluate_reference_block())
    row_counts = expected_profile["row_counts"]
    if row_counts["projection_mul_rows"] != EXPECTED_TOTAL_PROJECTION_MUL_ROWS:
        raise D64VectorRowSurfaceError("projection multiplication row count drift")
    if row_counts["activation_table_rows"] != EXPECTED_ACTIVATION_TABLE_ROWS:
        raise D64VectorRowSurfaceError("activation table row count drift")
    if row_counts["trace_rows_excluding_static_table"] != EXPECTED_TRACE_ROWS_EXCLUDING_STATIC_TABLE:
        raise D64VectorRowSurfaceError("trace row count drift")
    if not expected_profile["m31_range"]["fits_signed_m31"]:
        raise D64VectorRowSurfaceError("witness values exceed signed M31 range")
    if payload["witness_profile"] != expected_profile:
        raise D64VectorRowSurfaceError("witness profile drift")
    if payload["witness_profile_commitment"] != blake2b_commitment(
        expected_profile,
        "ptvm:zkai:d64-stwo-vector-row-profile:v1",
    ):
        raise D64VectorRowSurfaceError("witness profile commitment drift")

    expected_decisions = decision_matrix()
    if payload["decision_matrix"] != expected_decisions:
        raise D64VectorRowSurfaceError("decision matrix drift")
    if payload["decision_matrix_commitment"] != blake2b_commitment(
        expected_decisions,
        "ptvm:zkai:d64-stwo-vector-row-decisions:v1",
    ):
        raise D64VectorRowSurfaceError("decision matrix commitment drift")
    by_gate = {row["gate"]: row["status"] for row in payload["decision_matrix"]}
    if by_gate["vector_row_arithmetic_surface"] != "GO":
        raise D64VectorRowSurfaceError("arithmetic surface must stay GO")
    if by_gate["proof_native_public_instance_contract"] != "GO":
        raise D64VectorRowSurfaceError("proof-native public-instance contract must stay GO")
    if by_gate["weight_commitment_consistency"] != "NO_GO_YET":
        raise D64VectorRowSurfaceError("weight commitment consistency must stay explicit")
    if by_gate["native_stwo_exact_d64_proof"] != "NO_GO_YET":
        raise D64VectorRowSurfaceError("native proof status must not overclaim")
    if payload["issue_scope"] != expected_issue_scope():
        raise D64VectorRowSurfaceError("issue scope drift")
    if payload["non_claims"] != expected_non_claims():
        raise D64VectorRowSurfaceError("non-claims drift")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_probe(payload)
    target = payload["target"]
    profile = payload["witness_profile"]
    row_counts = profile["row_counts"]
    m31_range = profile["m31_range"]
    contract = payload["proof_public_instance_contract"]
    mutation_suite = payload["proof_public_instance_mutation_suite"]
    return [
        {
            "target_id": target["target_id"],
            "width": target["width"],
            "ff_dim": target["ff_dim"],
            "gate": row["gate"],
            "status": row["status"],
            "projection_mul_rows": row_counts["projection_mul_rows"],
            "trace_rows_excluding_static_table": row_counts["trace_rows_excluding_static_table"],
            "activation_table_rows": row_counts["activation_table_rows"],
            "max_abs_intermediate": m31_range["max_abs_intermediate"],
            "fits_signed_m31": str(m31_range["fits_signed_m31"]).lower(),
            "public_instance_contract_status": contract["status"],
            "public_instance_mutations_rejected": mutation_suite["mutations_rejected"],
            "proof_native_parameter_commitment": contract["proof_native_parameter_commitment"],
            "public_instance_commitment": contract["public_instance_commitment"],
            "statement_commitment": payload["source_fixture"]["statement_commitment"],
        }
        for row in payload["decision_matrix"]
    ]


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_probe(payload)
    rows = rows_for_tsv(payload, validated=True)
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
        raise D64VectorRowSurfaceError(f"failed to write vector-row surface probe output: {err}") from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true", help="print the full probe payload")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_probe()
    validate_probe(payload)
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        profile = payload["witness_profile"]
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "decision": payload["decision"],
                    "projection_mul_rows": profile["row_counts"]["projection_mul_rows"],
                    "trace_rows_excluding_static_table": profile["row_counts"]["trace_rows_excluding_static_table"],
                    "max_abs_intermediate": profile["m31_range"]["max_abs_intermediate"],
                    "fits_signed_m31": profile["m31_range"]["fits_signed_m31"],
                    "proof_public_instance_contract": payload["proof_public_instance_contract"]["status"],
                    "proof_public_instance_mutations_rejected": payload["proof_public_instance_mutation_suite"][
                        "mutations_rejected"
                    ],
                    "native_stwo_exact_d64_proof": "NO_GO_YET",
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
