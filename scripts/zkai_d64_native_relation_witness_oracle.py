#!/usr/bin/env python3
"""Reference relation-witness oracle for the canonical d64 zkAI statement.

This is not a Stwo proof. It is the fail-closed relation oracle we want before
encoding the same checks into AIR: consume the d64 public-instance contract,
recompute the statement witness rows, and reject relabeling of the parameter,
lookup, input, and output surfaces.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import subprocess
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-native-relation-witness-oracle-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-d64-native-relation-witness-oracle-2026-05.tsv"

SCHEMA = "zkai-d64-native-relation-witness-oracle-v1"
DECISION = "GO_RELATION_WITNESS_ORACLE_NOT_STWO_PROOF"
SOURCE_DATE_EPOCH_DEFAULT = 0
EXPECTED_PROJECTION_MUL_ROWS = 49_152
EXPECTED_TRACE_ROWS_EXCLUDING_STATIC_TABLE = 49_920
EXPECTED_ACTIVATION_TABLE_ROWS = 2_049
EXPECTED_MUTATION_NAMES = (
    "proof_native_parameter_commitment_public_instance_relabeling",
    "proof_native_parameter_commitment_manifest_relabeling",
    "gate_parameter_root_relabeling",
    "rms_scale_root_relabeling",
    "activation_table_root_relabeling",
    "input_activation_commitment_relabeling",
    "output_activation_commitment_relabeling",
    "normalization_config_commitment_relabeling",
    "activation_lookup_commitment_relabeling",
    "public_instance_commitment_relabeling",
    "statement_commitment_relabeling",
    "backend_version_relabeling",
    "relation_row_count_relabeling",
    "gate_projection_output_relabeling",
    "activation_lookup_output_relabeling",
    "residual_output_relabeling",
)
PUBLIC_INSTANCE_FIELDS = (
    "target_id",
    "width",
    "ff_dim",
    "input_activation_commitment",
    "output_activation_commitment",
    "model_config_commitment",
    "proof_native_parameter_commitment",
    "normalization_config_commitment",
    "activation_lookup_commitment",
)
TSV_COLUMNS = (
    "target_id",
    "decision",
    "proof_status",
    "projection_mul_rows",
    "trace_rows_excluding_static_table",
    "activation_table_rows",
    "relation_checks",
    "mutations_checked",
    "mutations_rejected",
    "proof_native_parameter_commitment",
    "public_instance_commitment",
    "statement_commitment",
)


class NativeRelationWitnessOracleError(ValueError):
    pass


def _load_fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_d64_rmsnorm_swiglu_statement_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise NativeRelationWitnessOracleError(f"failed to load d64 fixture from {FIXTURE_PATH}")
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
        raise NativeRelationWitnessOracleError("SOURCE_DATE_EPOCH must be an integer timestamp") from err
    try:
        generated_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise NativeRelationWitnessOracleError("SOURCE_DATE_EPOCH must be in the supported timestamp range") from err
    return generated_at.isoformat().replace("+00:00", "Z")


def _validate_generated_at(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise NativeRelationWitnessOracleError("generated_at must be a UTC timestamp string")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as err:
        raise NativeRelationWitnessOracleError("generated_at must be a valid UTC timestamp string") from err
    if parsed.tzinfo != dt.timezone.utc:
        raise NativeRelationWitnessOracleError("generated_at must be a UTC timestamp string")


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
        raise NativeRelationWitnessOracleError("cannot summarize empty relation values")
    return {"count": len(values), "min": min(values), "max": max(values), "max_abs": max(abs(item) for item in values)}


def _projection_outputs(inputs: list[int], matrix: str, rows: int, cols: int) -> tuple[list[int], dict[str, int]]:
    outputs: list[int] = []
    products: list[int] = []
    accumulators: list[int] = []
    for row in range(rows):
        acc = 0
        for col in range(cols):
            product = inputs[col] * FIXTURE.weight_value(matrix, row, col)
            products.append(product)
            acc += product
        accumulators.append(acc)
        outputs.append(acc // cols)
    return outputs, {
        "mul_rows": rows * cols,
        "max_abs_product": max(abs(item) for item in products),
        "max_abs_accumulator": max(abs(item) for item in accumulators),
    }


def _rmsnorm_outputs(inputs: list[int], scales: list[int]) -> tuple[int, list[int]]:
    if len(inputs) != FIXTURE.WIDTH or len(scales) != FIXTURE.WIDTH:
        raise NativeRelationWitnessOracleError("RMSNorm vector width mismatch")
    sum_squares = sum(value * value for value in inputs)
    rms_q8 = max(1, math.isqrt(max(1, sum_squares // FIXTURE.WIDTH)))
    normed = [
        ((value * scale) // FIXTURE.SCALE_Q8 * FIXTURE.SCALE_Q8) // rms_q8
        for value, scale in zip(inputs, scales, strict=True)
    ]
    return rms_q8, normed


def relation_witness(reference: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    statement = fixture["statement"]
    binding = fixture["commitments"]
    computed_binding = FIXTURE.commitments(reference)
    if computed_binding != binding:
        raise NativeRelationWitnessOracleError("commitment surface mismatch")
    computed_statement = FIXTURE.statement_payload(reference, computed_binding)
    if computed_statement != statement:
        raise NativeRelationWitnessOracleError("statement surface mismatch")
    public_instance = FIXTURE.public_instance_payload(binding)
    statement_binding = {
        "backend_version_required": statement["proof_system_version_required"],
        "verifier_domain": statement["verifier_domain"],
        "public_instance_commitment": statement["public_instance_commitment"],
        "statement_commitment": statement["statement_commitment"],
    }
    if statement_binding["backend_version_required"] != fixture["target"]["required_backend_version"]:
        raise NativeRelationWitnessOracleError("backend version mismatch between target and statement")
    parameter_manifest = FIXTURE.proof_native_parameter_manifest(reference)
    if parameter_manifest["proof_native_parameter_commitment"] != public_instance["proof_native_parameter_commitment"]:
        raise NativeRelationWitnessOracleError("proof-native parameter commitment mismatch")

    rms_q8, normed = _rmsnorm_outputs(reference["input_q8"], reference["rms_scale_q8"])
    if rms_q8 != reference["rms_q8"]:
        raise NativeRelationWitnessOracleError("RMSNorm scalar relation mismatch")
    if normed != reference["normed_q8"]:
        raise NativeRelationWitnessOracleError("RMSNorm row relation mismatch")

    gate, gate_stats = _projection_outputs(normed, "gate", FIXTURE.FF_DIM, FIXTURE.WIDTH)
    value, value_stats = _projection_outputs(normed, "value", FIXTURE.FF_DIM, FIXTURE.WIDTH)
    if gate != reference["gate_projection_q8"]:
        raise NativeRelationWitnessOracleError("gate projection relation mismatch")
    if value != reference["value_projection_q8"]:
        raise NativeRelationWitnessOracleError("value projection relation mismatch")

    activated = [FIXTURE.activation_lut_value(item) for item in gate]
    if activated != reference["activated_gate_q8"]:
        raise NativeRelationWitnessOracleError("activation lookup relation mismatch")
    hidden = [(left * right) // FIXTURE.SCALE_Q8 for left, right in zip(activated, value, strict=True)]
    if hidden != reference["hidden_q8"]:
        raise NativeRelationWitnessOracleError("SwiGLU mix relation mismatch")
    down, down_stats = _projection_outputs(hidden, "down", FIXTURE.WIDTH, FIXTURE.FF_DIM)
    if down != reference["residual_delta_q8"]:
        raise NativeRelationWitnessOracleError("down projection relation mismatch")
    output = [base + delta for base, delta in zip(reference["input_q8"], down, strict=True)]
    if output != reference["output_q8"]:
        raise NativeRelationWitnessOracleError("residual output relation mismatch")

    row_counts = {
        "input_rows": FIXTURE.WIDTH,
        "rms_square_rows": FIXTURE.WIDTH,
        "rms_norm_rows": FIXTURE.WIDTH,
        "gate_projection_mul_rows": gate_stats["mul_rows"],
        "value_projection_mul_rows": value_stats["mul_rows"],
        "activation_lookup_rows": FIXTURE.FF_DIM,
        "swiglu_mix_rows": FIXTURE.FF_DIM,
        "down_projection_mul_rows": down_stats["mul_rows"],
        "residual_rows": FIXTURE.WIDTH,
        "activation_table_rows": len(FIXTURE.activation_table()),
    }
    row_counts["projection_mul_rows"] = (
        row_counts["gate_projection_mul_rows"]
        + row_counts["value_projection_mul_rows"]
        + row_counts["down_projection_mul_rows"]
    )
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
    relation_samples = {
        "input_head_q8": reference["input_q8"][:8],
        "gate_projection_head_q8": gate[:8],
        "activation_head_q8": activated[:8],
        "hidden_head_q8": hidden[:8],
        "residual_delta_head_q8": down[:8],
        "output_head_q8": output[:8],
    }
    checks = [
        {"name": "public_instance_field_set", "status": "GO"},
        {"name": "proof_native_parameter_manifest_recomputed", "status": "GO"},
        {"name": "public_statement_commitments_recomputed", "status": "GO"},
        {"name": "rmsnorm_rows_recomputed", "status": "GO"},
        {"name": "gate_value_projection_rows", "status": "GO"},
        {"name": "activation_lookup_rows", "status": "GO"},
        {"name": "swiglu_mix_rows", "status": "GO"},
        {"name": "down_projection_rows", "status": "GO"},
        {"name": "residual_rows", "status": "GO"},
    ]
    return {
        "public_instance": public_instance,
        "statement_binding": statement_binding,
        "parameter_manifest": parameter_manifest,
        "row_counts": row_counts,
        "value_ranges": {
            "input_q8": _range_summary(reference["input_q8"]),
            "normed_q8": _range_summary(reference["normed_q8"]),
            "gate_projection_q8": _range_summary(gate),
            "value_projection_q8": _range_summary(value),
            "activation_q8": _range_summary(activated),
            "hidden_q8": _range_summary(hidden),
            "residual_delta_q8": _range_summary(down),
            "output_q8": _range_summary(output),
        },
        "relation_samples": relation_samples,
        "relation_checks": checks,
        "relation_commitment": blake2b_commitment(
            {
                "public_instance": public_instance,
                "statement_binding": statement_binding,
                "parameter_manifest": parameter_manifest,
                "row_counts": row_counts,
                "relation_samples": relation_samples,
            },
            "ptvm:zkai:d64-native-relation-witness-oracle:v1",
        ),
    }


def _expected_payload() -> dict[str, Any]:
    return build_payload(include_mutations=False)


def validate_relation_witness(witness: dict[str, Any], fixture: dict[str, Any] | None = None) -> None:
    if not isinstance(witness, dict):
        raise NativeRelationWitnessOracleError("relation witness must be an object")
    expected_fields = {
        "public_instance",
        "statement_binding",
        "parameter_manifest",
        "row_counts",
        "value_ranges",
        "relation_samples",
        "relation_checks",
        "relation_commitment",
    }
    if set(witness) != expected_fields:
        raise NativeRelationWitnessOracleError("relation witness field set mismatch")
    fixture = FIXTURE.build_fixture() if fixture is None else fixture
    expected = relation_witness(FIXTURE.evaluate_reference_block(), fixture)
    public_instance = witness["public_instance"]
    if not isinstance(public_instance, dict) or set(public_instance) != set(PUBLIC_INSTANCE_FIELDS):
        raise NativeRelationWitnessOracleError("public instance field set mismatch")
    statement_binding = witness["statement_binding"]
    expected_statement_binding_fields = {
        "backend_version_required",
        "verifier_domain",
        "public_instance_commitment",
        "statement_commitment",
    }
    if not isinstance(statement_binding, dict) or set(statement_binding) != expected_statement_binding_fields:
        raise NativeRelationWitnessOracleError("statement binding field set mismatch")
    if witness != expected:
        for field in expected_fields:
            if witness.get(field) != expected[field]:
                raise NativeRelationWitnessOracleError(f"relation witness mismatch: {field}")
        raise NativeRelationWitnessOracleError("relation witness mismatch")
    rows = witness["row_counts"]
    if rows["projection_mul_rows"] != EXPECTED_PROJECTION_MUL_ROWS:
        raise NativeRelationWitnessOracleError("projection row count drift")
    if rows["trace_rows_excluding_static_table"] != EXPECTED_TRACE_ROWS_EXCLUDING_STATIC_TABLE:
        raise NativeRelationWitnessOracleError("trace row count drift")
    if rows["activation_table_rows"] != EXPECTED_ACTIVATION_TABLE_ROWS:
        raise NativeRelationWitnessOracleError("activation table row count drift")


def mutate_path(value: dict[str, Any], path: tuple[str, ...], replacement: Any) -> dict[str, Any]:
    out = copy.deepcopy(value)
    cursor = out
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    return out


def mutation_cases(witness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wrong_commitment = "blake2b-256:" + "77" * 32
    out = {
        "proof_native_parameter_commitment_public_instance_relabeling": mutate_path(
            witness, ("public_instance", "proof_native_parameter_commitment"), wrong_commitment
        ),
        "proof_native_parameter_commitment_manifest_relabeling": mutate_path(
            witness, ("parameter_manifest", "proof_native_parameter_commitment"), wrong_commitment
        ),
        "gate_parameter_root_relabeling": mutate_path(
            witness, ("parameter_manifest", "matrix_trees", "gate", "root"), wrong_commitment
        ),
        "rms_scale_root_relabeling": mutate_path(
            witness, ("parameter_manifest", "rms_scale_tree", "root"), wrong_commitment
        ),
        "activation_table_root_relabeling": mutate_path(
            witness, ("parameter_manifest", "activation_table_tree", "root"), wrong_commitment
        ),
        "input_activation_commitment_relabeling": mutate_path(
            witness, ("public_instance", "input_activation_commitment"), wrong_commitment
        ),
        "output_activation_commitment_relabeling": mutate_path(
            witness, ("public_instance", "output_activation_commitment"), wrong_commitment
        ),
        "normalization_config_commitment_relabeling": mutate_path(
            witness, ("public_instance", "normalization_config_commitment"), wrong_commitment
        ),
        "activation_lookup_commitment_relabeling": mutate_path(
            witness, ("public_instance", "activation_lookup_commitment"), wrong_commitment
        ),
        "public_instance_commitment_relabeling": mutate_path(
            witness, ("statement_binding", "public_instance_commitment"), wrong_commitment
        ),
        "statement_commitment_relabeling": mutate_path(
            witness, ("statement_binding", "statement_commitment"), wrong_commitment
        ),
        "backend_version_relabeling": mutate_path(
            witness, ("statement_binding", "backend_version_required"), "stwo-rmsnorm-swiglu-residual-d64-v999"
        ),
        "relation_row_count_relabeling": mutate_path(witness, ("row_counts", "projection_mul_rows"), 1),
        "gate_projection_output_relabeling": mutate_path(witness, ("relation_samples", "gate_projection_head_q8"), [0] * 8),
        "activation_lookup_output_relabeling": mutate_path(witness, ("relation_samples", "activation_head_q8"), [0] * 8),
        "residual_output_relabeling": mutate_path(witness, ("relation_samples", "output_head_q8"), [0] * 8),
    }
    if tuple(sorted(out)) != tuple(sorted(EXPECTED_MUTATION_NAMES)):
        raise NativeRelationWitnessOracleError("mutation corpus drift")
    return out


def run_mutation_suite(witness: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    validate_relation_witness(witness, fixture)
    cases = []
    for name, mutated in mutation_cases(witness).items():
        try:
            validate_relation_witness(mutated, fixture)
        except NativeRelationWitnessOracleError as err:
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


def build_payload(*, include_mutations: bool = True) -> dict[str, Any]:
    fixture = FIXTURE.build_fixture()
    FIXTURE.validate_payload(fixture)
    witness = relation_witness(FIXTURE.evaluate_reference_block(), fixture)
    mutation_suite = run_mutation_suite(witness, fixture) if include_mutations else None
    payload = {
        "schema": SCHEMA,
        "generated_at": _generated_at(),
        "git_commit": _git_commit(),
        "decision": DECISION,
        "source_fixture": {
            "schema": fixture["schema"],
            "target_id": fixture["target"]["target_id"],
            "proof_status": fixture["implementation_status"]["proof_status"],
            "proof_native_parameter_commitment": fixture["statement"]["proof_native_parameter_commitment"],
            "public_instance_commitment": fixture["statement"]["public_instance_commitment"],
            "statement_commitment": fixture["statement"]["statement_commitment"],
        },
        "relation_witness": witness,
        "mutation_suite": mutation_suite,
        "non_claims": [
            "not a Stwo proof",
            "not verifier-time evidence",
            "not AIR constraints",
            "not backend independence evidence",
            "not full transformer inference",
        ],
        "next_backend_step": "encode this relation oracle as native Stwo AIR/export rows that consume the same public instance",
    }
    if mutation_suite is None:
        payload.pop("mutation_suite")
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise NativeRelationWitnessOracleError("payload must be an object")
    expected_fields = {
        "schema",
        "generated_at",
        "git_commit",
        "decision",
        "source_fixture",
        "relation_witness",
        "mutation_suite",
        "non_claims",
        "next_backend_step",
    }
    if set(payload) != expected_fields:
        raise NativeRelationWitnessOracleError("payload field set mismatch")
    if payload["schema"] != SCHEMA:
        raise NativeRelationWitnessOracleError("schema mismatch")
    _validate_generated_at(payload["generated_at"])
    git_commit = payload["git_commit"]
    if not isinstance(git_commit, str) or not git_commit:
        raise NativeRelationWitnessOracleError("git_commit must be a non-empty string")
    if git_commit != "unavailable" and (len(git_commit) != 40 or any(char not in "0123456789abcdef" for char in git_commit)):
        raise NativeRelationWitnessOracleError("git_commit must be a full lowercase hex commit hash")
    if payload["decision"] != DECISION:
        raise NativeRelationWitnessOracleError("decision mismatch")
    fixture = FIXTURE.build_fixture()
    expected_payload = _expected_payload()
    if payload["non_claims"] != expected_payload["non_claims"]:
        raise NativeRelationWitnessOracleError("non-claims drift")
    if payload["next_backend_step"] != expected_payload["next_backend_step"]:
        raise NativeRelationWitnessOracleError("next backend step drift")
    expected_source = expected_payload["source_fixture"]
    if payload["source_fixture"] != expected_source:
        raise NativeRelationWitnessOracleError("source fixture drift")
    validate_relation_witness(payload["relation_witness"], fixture)
    expected_mutations = run_mutation_suite(payload["relation_witness"], fixture)
    if payload["mutation_suite"] != expected_mutations:
        raise NativeRelationWitnessOracleError("mutation suite drift")
    if expected_mutations["decision"] != "GO":
        raise NativeRelationWitnessOracleError("mutation suite must reject all cases")


def rows_for_tsv(payload: dict[str, Any], *, validated: bool = False) -> list[dict[str, Any]]:
    if not validated:
        validate_payload(payload)
    witness = payload["relation_witness"]
    rows = witness["row_counts"]
    suite = payload["mutation_suite"]
    return [
        {
            "target_id": payload["source_fixture"]["target_id"],
            "decision": payload["decision"],
            "proof_status": payload["source_fixture"]["proof_status"],
            "projection_mul_rows": rows["projection_mul_rows"],
            "trace_rows_excluding_static_table": rows["trace_rows_excluding_static_table"],
            "activation_table_rows": rows["activation_table_rows"],
            "relation_checks": len(witness["relation_checks"]),
            "mutations_checked": suite["mutations_checked"],
            "mutations_rejected": suite["mutations_rejected"],
            "proof_native_parameter_commitment": payload["source_fixture"]["proof_native_parameter_commitment"],
            "public_instance_commitment": payload["source_fixture"]["public_instance_commitment"],
            "statement_commitment": payload["source_fixture"]["statement_commitment"],
        }
    ]


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
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
        raise NativeRelationWitnessOracleError(f"failed to write relation witness oracle output: {err}") from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true", help="print full payload")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    validate_payload(payload)
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
                    "projection_mul_rows": payload["relation_witness"]["row_counts"]["projection_mul_rows"],
                    "trace_rows_excluding_static_table": payload["relation_witness"]["row_counts"]["trace_rows_excluding_static_table"],
                    "mutations_rejected": payload["mutation_suite"]["mutations_rejected"],
                    "mutations_checked": payload["mutation_suite"]["mutations_checked"],
                    "native_stwo_exact_d64_proof": "NO_GO_YET",
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
