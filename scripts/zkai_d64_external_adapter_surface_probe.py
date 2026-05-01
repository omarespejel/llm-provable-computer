#!/usr/bin/env python3
"""External-adapter surface probe for the canonical d64 zkAI statement.

This is not a proof benchmark. It asks whether the exact d64 RMSNorm-SwiGLU
statement fixture can be honestly treated as a vanilla external-adapter target,
and records the minimum semantics an adapter must expose before we compare proof
size, proving time, or verifier time against other stacks.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import shutil
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-external-adapter-surface-probe-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-external-adapter-surface-probe-2026-05.tsv"

SCHEMA = "zkai-d64-external-adapter-surface-probe-v1"
SOURCE_DATE_EPOCH_DEFAULT = 0
DECISION = "NO_GO_EXACT_VANILLA_EXTERNAL_EXPORT_GO_FOR_STATEMENT_RECEIPT_TARGET"
PROOF_STATUS = "REFERENCE_FIXTURE_NOT_PROVEN"

PYTHON_MODULES = ("onnx", "onnxruntime", "numpy", "torch", "ezkl")
CLI_TOOLS = ("ezkl",)
EXPECTED_FLOAT_DRIFT_CHANGED_POSITIONS = 61
EXPECTED_FLOAT_DRIFT_MAX_ABS_DELTA_Q8 = 10
EXPECTED_EXACT_OUTPUT_SHA256 = "d85e1accebec91047bc31f32ca56366a6b794bd83abf0b8eb235f5339c90f956"
EXPECTED_FLOAT_LIKE_OUTPUT_SHA256 = "191b7ce0ffa77dc76584d271c31ec84f24b6b1daa6805ed9577de5c55d482c0f"

TSV_COLUMNS = (
    "candidate_adapter",
    "gate",
    "same_statement_proof_claim",
    "proof_generated",
    "primary_blocker",
    "required_custom_semantics",
    "statement_commitment",
    "width",
    "ff_dim",
    "projection_weight_scalars",
    "total_committed_parameter_scalars",
)


class D64ExternalAdapterProbeError(ValueError):
    pass


def _load_fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_statement_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise D64ExternalAdapterProbeError(f"failed to load d64 fixture from {FIXTURE_PATH}")
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
        raise D64ExternalAdapterProbeError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise D64ExternalAdapterProbeError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _validate_generated_at(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise D64ExternalAdapterProbeError("generated_at must be a UTC timestamp string")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as err:
        raise D64ExternalAdapterProbeError("generated_at must be a valid UTC timestamp string") from err
    if parsed.tzinfo != dt.timezone.utc:
        raise D64ExternalAdapterProbeError("generated_at must be a UTC timestamp string")


def _git_commit() -> str:
    return "unspecified"


def dependency_probe(
    module_overrides: dict[str, bool] | None = None,
    cli_overrides: dict[str, bool] | None = None,
    *,
    include_host_dependencies: bool = False,
) -> dict[str, Any]:
    module_overrides = module_overrides or {}
    cli_overrides = cli_overrides or {}
    if not include_host_dependencies and not module_overrides and not cli_overrides:
        return {
            "mode": "declared_requirements_only",
            "python_modules": {name: "not_recorded" for name in PYTHON_MODULES},
            "cli_tools": {name: "not_recorded" for name in CLI_TOOLS},
            "all_vanilla_external_runtime_present": "not_recorded",
        }

    modules: dict[str, bool | str] = {}
    for name in PYTHON_MODULES:
        if name in module_overrides:
            modules[name] = bool(module_overrides[name])
        elif include_host_dependencies:
            modules[name] = importlib.util.find_spec(name) is not None
        else:
            modules[name] = "not_recorded"
    cli_tools: dict[str, bool | str] = {}
    for name in CLI_TOOLS:
        if name in cli_overrides:
            cli_tools[name] = bool(cli_overrides[name])
        elif include_host_dependencies:
            cli_tools[name] = shutil.which(name) is not None
        else:
            cli_tools[name] = "not_recorded"
    all_runtime_present = (
        modules.get("onnx") is True
        and modules.get("onnxruntime") is True
        and modules.get("numpy") is True
        and modules.get("ezkl") is True
        and cli_tools.get("ezkl") is True
    )
    mode = "host_dependency_probe" if include_host_dependencies else "declared_requirements_with_overrides"
    return {
        "mode": mode,
        "python_modules": modules,
        "cli_tools": cli_tools,
        "all_vanilla_external_runtime_present": all_runtime_present,
    }


def exact_semantic_requirements() -> list[dict[str, str]]:
    return [
        {
            "requirement": "signed_q8_integer_arithmetic",
            "why_it_matters": (
                "The fixture statement is over deterministic signed-q8 integer values, not over "
                "floating-point tensors."
            ),
        },
        {
            "requirement": "floor_division_rounding",
            "why_it_matters": (
                "RMSNorm, projection averages, hidden mixing, and down projection all use Python "
                "integer floor division."
            ),
        },
        {
            "requirement": "integer_square_root",
            "why_it_matters": "The reference RMS value is math.isqrt(sum_squares // width), not sqrt over reals.",
        },
        {
            "requirement": "bounded_integer_silu_lookup",
            "why_it_matters": (
                "The SwiGLU gate uses a 2049-entry clamped integer lookup table, not "
                "floating-point SiLU."
            ),
        },
        {
            "requirement": "committed_parameter_tables",
            "why_it_matters": (
                "The statement binds 49,216 committed parameter scalars across RMS scale and "
                "gate/value/down matrices."
            ),
        },
        {
            "requirement": "statement_receipt_binding",
            "why_it_matters": (
                "The proof must bind model/config/weight/input/output/public-instance "
                "commitments, not only proof bytes."
            ),
        },
    ]


def float_like_reference_output(reference: dict[str, Any]) -> list[int]:
    """A deliberately naive float-style approximation used only as a drift canary."""

    x = reference["input_q8"]
    gamma = reference["rms_scale_q8"]
    sum_squares = sum(value * value for value in x)
    rms = max(1.0, math.sqrt(max(1.0, sum_squares / FIXTURE.WIDTH)))
    normed = [(value * scale) / rms for value, scale in zip(x, gamma, strict=True)]

    gate: list[float] = []
    value_projection: list[float] = []
    for row in range(FIXTURE.FF_DIM):
        gate_acc = 0.0
        value_acc = 0.0
        for col in range(FIXTURE.WIDTH):
            gate_acc += normed[col] * FIXTURE.weight_value("gate", row, col)
            value_acc += normed[col] * FIXTURE.weight_value("value", row, col)
        gate.append(gate_acc / FIXTURE.WIDTH)
        value_projection.append(value_acc / FIXTURE.WIDTH)

    activated_gate = [item / (1.0 + math.exp(-max(-32.0, min(32.0, item / FIXTURE.SCALE_Q8)))) for item in gate]
    hidden = [
        (gate_item * value_item) / FIXTURE.SCALE_Q8
        for gate_item, value_item in zip(activated_gate, value_projection, strict=True)
    ]

    delta: list[int] = []
    for row in range(FIXTURE.WIDTH):
        acc = 0.0
        for col in range(FIXTURE.FF_DIM):
            acc += hidden[col] * FIXTURE.weight_value("down", row, col)
        delta.append(int(round(acc / FIXTURE.FF_DIM)))
    return [base + change for base, change in zip(x, delta, strict=True)]


def float_drift_summary(reference: dict[str, Any]) -> dict[str, Any]:
    exact = reference["output_q8"]
    approx = float_like_reference_output(reference)
    diffs = [abs(a - b) for a, b in zip(exact, approx, strict=True)]
    changed = sum(1 for diff in diffs if diff != 0)
    return {
        "canary": "naive_float_style_export_not_same_statement",
        "changed_output_positions": changed,
        "max_abs_output_delta_q8": max(diffs),
        "exact_output_sha256": sha256_bytes(canonical_json_bytes(exact)),
        "float_like_output_sha256": sha256_bytes(canonical_json_bytes(approx)),
        "interpretation": (
            "A float-style graph is a different statement unless the exact integer rounding, "
            "isqrt, and lookup semantics are encoded."
        ),
    }


def adapter_candidates() -> list[dict[str, Any]]:
    return [
        {
            "candidate_adapter": "vanilla_onnx_ezkl_exact_export",
            "gate": "NO_GO",
            "same_statement_proof_claim": "NO_GO",
            "proof_generated": False,
            "primary_blocker": "exact_d64_semantics_not_encoded_by_a_vanilla_float_export",
            "required_custom_semantics": [
                "floor_division_rounding",
                "integer_square_root",
                "bounded_integer_silu_lookup",
                "committed_parameter_tables",
            ],
            "next_action": (
                "Do not report an EZKL verifier-time row for this statement until a "
                "circuit/export path encodes these semantics exactly."
            ),
        },
        {
            "candidate_adapter": "float_onnx_approximation",
            "gate": "NO_GO_FOR_SAME_STATEMENT",
            "same_statement_proof_claim": "NO_GO",
            "proof_generated": False,
            "primary_blocker": "approximate_float_graph_would_change_the_committed_output_statement",
            "required_custom_semantics": ["new_statement_definition_if_used"],
            "next_action": (
                "Allowed only as a separate approximate-inference statement, not as evidence "
                "for the canonical d64 target."
            ),
        },
        {
            "candidate_adapter": "custom_table_range_external_circuit",
            "gate": "POSSIBLE_NOT_CHECKED",
            "same_statement_proof_claim": "NOT_CHECKED",
            "proof_generated": False,
            "primary_blocker": "requires_custom_table_range_circuit_or_adapter_work",
            "required_custom_semantics": [
                "range_checks",
                "integer_isqrt_or_checked_rms_witness",
                "floor_division_constraints",
                "bounded_silu_lookup_table",
                "statement_receipt_binding",
            ],
            "next_action": (
                "Explore only if it can bind the existing statement commitment without "
                "redefining the target."
            ),
        },
        {
            "candidate_adapter": "stwo_vector_row_air",
            "gate": "REFERRED_TO_BACKEND_TRACK",
            "same_statement_proof_claim": "NOT_CHECKED",
            "proof_generated": False,
            "primary_blocker": "needs_parameterized_vector_block_air_or_export_path",
            "required_custom_semantics": [
                "committed_weight_rows",
                "rmsnorm_rows",
                "projection_rows",
                "bounded_activation_lookup_rows",
                "public_instance_binding",
            ],
            "next_action": "Continue issue #341 as the native proof path for the exact statement.",
        },
        {
            "candidate_adapter": "zkai_statement_receipt_only",
            "gate": "GO_FOR_BINDING_TARGET_NOT_PROOF",
            "same_statement_proof_claim": "NO_GO",
            "proof_generated": False,
            "primary_blocker": "receipt_binds_claims_but_delegated_proof_is_absent",
            "required_custom_semantics": ["delegated_exact_statement_proof"],
            "next_action": "Reuse the receipt fields and mutation suite once an exact external or native proof exists.",
        },
    ]


def build_probe(
    module_overrides: dict[str, bool] | None = None,
    cli_overrides: dict[str, bool] | None = None,
    *,
    include_host_dependencies: bool = False,
) -> dict[str, Any]:
    fixture = FIXTURE.build_fixture()
    FIXTURE.validate_payload(fixture)
    reference = FIXTURE.evaluate_reference_block()
    statement = fixture["statement"]
    dependencies = dependency_probe(
        module_overrides=module_overrides,
        cli_overrides=cli_overrides,
        include_host_dependencies=include_host_dependencies,
    )
    drift = float_drift_summary(reference)
    exact_requirements = exact_semantic_requirements()
    exact_requirements_commitment = blake2b_commitment(
        exact_requirements,
        "ptvm:zkai:d64-external-adapter-requirements:v1",
    )
    candidates = adapter_candidates()
    candidate_matrix_commitment = blake2b_commitment(candidates, "ptvm:zkai:d64-external-adapter-candidates:v1")
    return {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": DECISION,
        "target": fixture["target"],
        "source_fixture": {
            "schema": fixture["schema"],
            "decision": fixture["decision"],
            "proof_status": fixture["implementation_status"]["proof_status"],
            "statement_commitment": statement["statement_commitment"],
            "mutation_suite": {
                "mutations_checked": fixture["mutation_suite"]["mutations_checked"],
                "mutations_rejected": fixture["mutation_suite"]["mutations_rejected"],
                "decision": fixture["mutation_suite"]["decision"],
            },
        },
        "dependency_probe": dependencies,
        "exact_semantic_requirements": exact_requirements,
        "exact_semantic_requirements_commitment": exact_requirements_commitment,
        "float_drift_summary": drift,
        "candidate_adapters": candidates,
        "candidate_matrix_commitment": candidate_matrix_commitment,
        "conclusion": {
            "exact_vanilla_external_export": "NO_GO",
            "statement_receipt_reuse": "GO_FOR_BINDING_TARGET_NOT_PROOF",
            "native_stwo_backend_track": "REFERRED_TO_ISSUE_341",
            "external_custom_circuit_track": "POSSIBLE_NOT_CHECKED",
        },
        "non_claims": [
            "not an EZKL security finding",
            "not a claim that EZKL or ONNX cannot encode custom exact integer circuits",
            "not a proof-generation benchmark",
            "not a verifier-time benchmark",
            "not evidence that the d64 statement is proven",
            "not a full transformer inference claim",
        ],
    }


def _validate_candidate(candidate: dict[str, Any]) -> None:
    required = {
        "candidate_adapter",
        "gate",
        "same_statement_proof_claim",
        "proof_generated",
        "primary_blocker",
        "required_custom_semantics",
        "next_action",
    }
    if set(candidate) != required:
        raise D64ExternalAdapterProbeError("candidate adapter field set mismatch")
    if candidate["proof_generated"] is not False:
        raise D64ExternalAdapterProbeError("candidate adapters must not claim proof generation")
    if not isinstance(candidate["required_custom_semantics"], list):
        raise D64ExternalAdapterProbeError("candidate required_custom_semantics must be a list")


def validate_probe(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise D64ExternalAdapterProbeError("payload must be an object")
    for field in (
        "schema",
        "decision",
        "target",
        "source_fixture",
        "dependency_probe",
        "exact_semantic_requirements",
        "exact_semantic_requirements_commitment",
        "float_drift_summary",
        "candidate_adapters",
        "candidate_matrix_commitment",
        "conclusion",
        "non_claims",
    ):
        if field not in payload:
            raise D64ExternalAdapterProbeError(f"missing payload field: {field}")
    if payload["schema"] != SCHEMA:
        raise D64ExternalAdapterProbeError("schema mismatch")
    if payload["decision"] != DECISION:
        raise D64ExternalAdapterProbeError("decision mismatch")
    _validate_generated_at(payload.get("generated_at"))
    git_commit = payload.get("git_commit")
    if not isinstance(git_commit, str) or not git_commit:
        raise D64ExternalAdapterProbeError("git_commit must be a non-empty string")

    fixture = FIXTURE.build_fixture()
    if payload["target"] != fixture["target"]:
        raise D64ExternalAdapterProbeError("target drift")
    expected_source = {
        "schema": fixture["schema"],
        "decision": fixture["decision"],
        "proof_status": fixture["implementation_status"]["proof_status"],
        "statement_commitment": fixture["statement"]["statement_commitment"],
        "mutation_suite": {
            "mutations_checked": fixture["mutation_suite"]["mutations_checked"],
            "mutations_rejected": fixture["mutation_suite"]["mutations_rejected"],
            "decision": fixture["mutation_suite"]["decision"],
        },
    }
    if payload["source_fixture"] != expected_source:
        raise D64ExternalAdapterProbeError("source fixture drift")

    requirements = payload["exact_semantic_requirements"]
    expected_requirements = exact_semantic_requirements()
    if requirements != expected_requirements:
        raise D64ExternalAdapterProbeError("semantic requirements drift")
    if payload["exact_semantic_requirements_commitment"] != blake2b_commitment(
        expected_requirements,
        "ptvm:zkai:d64-external-adapter-requirements:v1",
    ):
        raise D64ExternalAdapterProbeError("semantic requirements commitment drift")

    expected_drift = float_drift_summary(FIXTURE.evaluate_reference_block())
    if expected_drift["changed_output_positions"] != EXPECTED_FLOAT_DRIFT_CHANGED_POSITIONS:
        raise D64ExternalAdapterProbeError("internal float drift changed-position constant drift")
    if expected_drift["max_abs_output_delta_q8"] != EXPECTED_FLOAT_DRIFT_MAX_ABS_DELTA_Q8:
        raise D64ExternalAdapterProbeError("internal float drift max-delta constant drift")
    if expected_drift["exact_output_sha256"] != EXPECTED_EXACT_OUTPUT_SHA256:
        raise D64ExternalAdapterProbeError("internal exact output hash constant drift")
    if expected_drift["float_like_output_sha256"] != EXPECTED_FLOAT_LIKE_OUTPUT_SHA256:
        raise D64ExternalAdapterProbeError("internal float-like output hash constant drift")
    if payload["float_drift_summary"] != expected_drift:
        raise D64ExternalAdapterProbeError("float drift summary drift")

    candidates = payload["candidate_adapters"]
    expected_candidates = adapter_candidates()
    if candidates != expected_candidates:
        raise D64ExternalAdapterProbeError("candidate adapter matrix drift")
    if not isinstance(candidates, list) or len(candidates) != 5:
        raise D64ExternalAdapterProbeError("candidate adapter matrix must contain five rows")
    for candidate in candidates:
        _validate_candidate(candidate)
    if payload["candidate_matrix_commitment"] != blake2b_commitment(
        expected_candidates,
        "ptvm:zkai:d64-external-adapter-candidates:v1",
    ):
        raise D64ExternalAdapterProbeError("candidate matrix commitment drift")
    by_name = {candidate["candidate_adapter"]: candidate for candidate in candidates}
    if by_name["vanilla_onnx_ezkl_exact_export"]["gate"] != "NO_GO":
        raise D64ExternalAdapterProbeError("vanilla exact export gate must stay NO_GO")
    if by_name["zkai_statement_receipt_only"]["gate"] != "GO_FOR_BINDING_TARGET_NOT_PROOF":
        raise D64ExternalAdapterProbeError("statement receipt row must remain binding-only")
    if payload["conclusion"].get("exact_vanilla_external_export") != "NO_GO":
        raise D64ExternalAdapterProbeError("conclusion exact external export gate drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_probe(payload)
    target = payload["target"]
    statement_commitment = payload["source_fixture"]["statement_commitment"]
    rows: list[dict[str, Any]] = []
    for candidate in payload["candidate_adapters"]:
        rows.append(
            {
                "candidate_adapter": candidate["candidate_adapter"],
                "gate": candidate["gate"],
                "same_statement_proof_claim": candidate["same_statement_proof_claim"],
                "proof_generated": str(candidate["proof_generated"]).lower(),
                "primary_blocker": candidate["primary_blocker"],
                "required_custom_semantics": ",".join(candidate["required_custom_semantics"]),
                "statement_commitment": statement_commitment,
                "width": target["width"],
                "ff_dim": target["ff_dim"],
                "projection_weight_scalars": target["projection_weight_scalars"],
                "total_committed_parameter_scalars": target["total_committed_parameter_scalars"],
            }
        )
    return rows


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
        raise D64ExternalAdapterProbeError(f"failed to write external adapter probe output: {err}") from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true", help="print the full probe payload")
    parser.add_argument(
        "--include-host-deps",
        action="store_true",
        help="include local dependency availability in printed/generated output; off by default for reproducibility",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_probe(include_host_dependencies=args.include_host_deps)
    write_outputs(payload, args.write_json, args.write_tsv)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "decision": payload["decision"],
                    "exact_vanilla_external_export": payload["conclusion"]["exact_vanilla_external_export"],
                    "statement_receipt_reuse": payload["conclusion"]["statement_receipt_reuse"],
                    "statement_commitment": payload["source_fixture"]["statement_commitment"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
