#!/usr/bin/env python3
"""Validate the next Stwo-native statement-bound transformer-block gate plan.

The plan is intentionally a design gate, not a proof result. This validator
keeps the next implementation target honest by rejecting plans that omit
transformer-block structure, binding fields, GO/NO-GO criteria, or non-claims.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PLAN_PATH = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "zkai-stwo-statement-bound-transformer-block-plan-2026-04.json"
)

PLAN_SCHEMA = "zkai-stwo-statement-bound-transformer-block-plan-v1"
PLAN_STATUS = "design_gate"
BASELINE_PROOF_SYSTEM_VERSION = "stwo-phase10-linear-block-v4-with-lookup"
TARGET_NAME = "rmsnorm-affine-residual-block-v1"
TARGET_STATEMENT_KIND = "transformer-block"
EXPECTED_STATEMENT_MUTATIONS = 14
EXPECTED_PROOF_ONLY_REJECTIONS = 1
EXPECTED_COMPOSITION_MUTATIONS = 36

REQUIRED_OPERATION_IDS = frozenset(
    {
        "rmsnorm_scale_lookup",
        "quantized_affine_projection",
        "residual_add",
    }
)
REQUIRED_PUBLIC_COMMITMENTS = frozenset(
    {
        "model_artifact_commitment",
        "model_config_commitment",
        "input_commitment",
        "output_commitment",
        "public_instance_commitment",
        "proof_commitment",
        "verifying_key_commitment",
        "setup_commitment",
        "verifier_domain",
        "proof_system_version",
        "evidence_manifest_commitment",
    }
)
REQUIRED_GO_IDS = frozenset(
    {
        "native_stwo_proof_accepts_honest_block",
        "receipt_binds_all_public_commitments",
        "relabeling_suite_rejects_all_statement_mutations",
        "agent_step_composition_accepts_baseline",
        "agent_step_composition_rejects_nested_relabels",
    }
)
REQUIRED_NO_GO_IDS = frozenset(
    {
        "proof_generator_cannot_emit_block_proof",
        "verifier_accepts_statement_relabeling",
        "target_collapses_to_linear_toy",
        "public_instance_not_bound",
    }
)
REQUIRED_NON_CLAIM_FRAGMENTS = (
    "not full transformer inference",
    "not an agent reasoning proof",
    "not a throughput or latency benchmark",
    "not backend independence",
    "not recursive or on-chain verification",
    "does not claim that the existing linear-block primitive already proves transformer-block semantics",
)
REQUIRED_VALIDATION_COMMAND_FRAGMENTS = (
    "scripts.tests.test_zkai_stwo_transformer_block_plan",
    "scripts.tests.test_zkai_stwo_statement_envelope_benchmark",
    "scripts.tests.test_agent_step_zkai_stwo_composition",
    "just gate-fast",
)


class PlanValidationError(ValueError):
    pass


def load_plan(path: pathlib.Path = DEFAULT_PLAN_PATH) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as err:
        raise PlanValidationError(f"failed to load plan {path}: {err}") from err
    if not isinstance(data, dict):
        raise PlanValidationError("plan must be a JSON object")
    return data


def _required_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanValidationError(f"{label} must be an object")
    return value


def _required_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PlanValidationError(f"{label} must be a list")
    return value


def _ids(entries: Iterable[Any], label: str) -> set[str]:
    result: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise PlanValidationError(f"{label}[{index}] must be an object")
        item_id = entry.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise PlanValidationError(f"{label}[{index}].id must be a non-empty string")
        result.add(item_id)
    return result


def _require_superset(actual: set[str], required: set[str], label: str) -> None:
    missing = sorted(required - actual)
    if missing:
        raise PlanValidationError(f"{label} is missing required entries: {', '.join(missing)}")


def _validate_current_baseline(plan: dict[str, Any]) -> None:
    baseline = _required_dict(plan.get("current_baseline"), "current_baseline")
    if baseline.get("statement_receipt_schema") != "zkai-statement-receipt-v1":
        raise PlanValidationError("current_baseline.statement_receipt_schema is not the checked receipt schema")
    if baseline.get("proof_system") != "stwo-transparent-stark":
        raise PlanValidationError("current_baseline.proof_system must stay Stwo-native")
    if baseline.get("proof_system_version") != BASELINE_PROOF_SYSTEM_VERSION:
        raise PlanValidationError(
            f"current_baseline.proof_system_version must be {BASELINE_PROOF_SYSTEM_VERSION!r}"
        )
    if baseline.get("model_id") != "urn:zkai:ptvm:linear-block-v4-with-lookup":
        raise PlanValidationError("current_baseline.model_id does not match the checked Stwo primitive")

    mutation_result = _required_dict(baseline.get("mutation_result"), "current_baseline.mutation_result")
    statement = _required_dict(mutation_result.get("statement_envelope"), "mutation_result.statement_envelope")
    if statement.get("mutations_rejected") != statement.get("mutations_checked"):
        raise PlanValidationError("current statement-envelope baseline must reject all checked mutations")
    if (
        statement.get("mutations_checked") != EXPECTED_STATEMENT_MUTATIONS
        or statement.get("mutations_rejected") != EXPECTED_STATEMENT_MUTATIONS
    ):
        raise PlanValidationError(
            f"current statement-envelope baseline must stay pinned at "
            f"{EXPECTED_STATEMENT_MUTATIONS}/{EXPECTED_STATEMENT_MUTATIONS}"
        )

    proof_only = _required_dict(mutation_result.get("proof_only"), "mutation_result.proof_only")
    if proof_only.get("decision") != "NO_GO_FOR_METADATA_RELABELING_BY_ITSELF":
        raise PlanValidationError("proof-only baseline must remain scoped as NO-GO for metadata relabeling")
    if (
        proof_only.get("mutations_checked") != EXPECTED_STATEMENT_MUTATIONS
        or proof_only.get("mutations_rejected") != EXPECTED_PROOF_ONLY_REJECTIONS
    ):
        raise PlanValidationError(
            f"proof-only baseline must stay pinned at "
            f"{EXPECTED_PROOF_ONLY_REJECTIONS}/{EXPECTED_STATEMENT_MUTATIONS}"
        )

    composition = _required_dict(baseline.get("agent_composition_result"), "current_baseline.agent_composition_result")
    if composition.get("mutations_rejected") != composition.get("mutations_checked"):
        raise PlanValidationError("agent composition baseline must reject all checked mutations")
    if (
        composition.get("mutations_checked") != EXPECTED_COMPOSITION_MUTATIONS
        or composition.get("mutations_rejected") != EXPECTED_COMPOSITION_MUTATIONS
    ):
        raise PlanValidationError(
            f"agent composition baseline must stay pinned at "
            f"{EXPECTED_COMPOSITION_MUTATIONS}/{EXPECTED_COMPOSITION_MUTATIONS}"
        )


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("schema") != PLAN_SCHEMA:
        raise PlanValidationError(f"unexpected schema: {plan.get('schema')!r}")
    if plan.get("status") != PLAN_STATUS:
        raise PlanValidationError(f"plan status must be {PLAN_STATUS!r}")
    if plan.get("decision") != "GO_TO_IMPLEMENTATION_ONLY_AFTER_CRITERIA_ARE_MET":
        raise PlanValidationError("decision must keep this artifact scoped as an implementation gate")

    _validate_current_baseline(plan)

    target = _required_dict(plan.get("target"), "target")
    if target.get("name") != TARGET_NAME:
        raise PlanValidationError(f"target.name must be {TARGET_NAME!r}")
    if target.get("statement_kind") != TARGET_STATEMENT_KIND:
        raise PlanValidationError(f"target.statement_kind must be {TARGET_STATEMENT_KIND!r}")
    if target.get("width") != 4:
        raise PlanValidationError("target.width must remain the bounded width-4 implementation target")

    operations = _required_list(target.get("operations"), "target.operations")
    operation_ids = _ids(operations, "target.operations")
    _require_superset(operation_ids, REQUIRED_OPERATION_IDS, "target.operations")

    public_commitment_items = _required_list(target.get("public_commitments"), "target.public_commitments")
    if not all(isinstance(item, str) and item for item in public_commitment_items):
        raise PlanValidationError("target.public_commitments must contain only non-empty strings")
    public_commitments = set(public_commitment_items)
    _require_superset(public_commitments, REQUIRED_PUBLIC_COMMITMENTS, "target.public_commitments")

    go_ids = _ids(_required_list(plan.get("go_criteria"), "go_criteria"), "go_criteria")
    _require_superset(go_ids, REQUIRED_GO_IDS, "go_criteria")

    no_go_ids = _ids(_required_list(plan.get("no_go_criteria"), "no_go_criteria"), "no_go_criteria")
    _require_superset(no_go_ids, REQUIRED_NO_GO_IDS, "no_go_criteria")

    non_claims = _required_list(plan.get("non_claims"), "non_claims")
    if not all(isinstance(item, str) and item for item in non_claims):
        raise PlanValidationError("non_claims must contain only non-empty strings")
    non_claim_text = "\n".join(item.lower() for item in non_claims)
    for fragment in REQUIRED_NON_CLAIM_FRAGMENTS:
        if fragment.lower() not in non_claim_text:
            raise PlanValidationError(f"non_claims is missing: {fragment}")

    commands = _required_list(plan.get("validation_commands"), "validation_commands")
    if not all(isinstance(command, str) and command for command in commands):
        raise PlanValidationError("validation_commands must contain only non-empty strings")
    command_text = "\n".join(commands)
    missing_command_fragments = [
        fragment for fragment in REQUIRED_VALIDATION_COMMAND_FRAGMENTS if fragment not in command_text
    ]
    if missing_command_fragments:
        raise PlanValidationError(
            "validation_commands is missing required coverage: "
            + ", ".join(missing_command_fragments)
        )
    normalized_commands = {command.strip() for command in commands}
    if not ({"just gate", "just gate-no-nightly"} & normalized_commands):
        raise PlanValidationError(
            "validation_commands must include final repo gate: `just gate` or `just gate-no-nightly`"
        )

    return {
        "schema": PLAN_SCHEMA,
        "status": PLAN_STATUS,
        "target": target["name"],
        "statement_kind": target["statement_kind"],
        "width": target["width"],
        "operation_count": len(operation_ids),
        "public_commitment_count": len(public_commitments),
        "go_criteria_count": len(go_ids),
        "no_go_criteria_count": len(no_go_ids),
        "decision": plan["decision"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=pathlib.Path, default=DEFAULT_PLAN_PATH)
    parser.add_argument("--json", action="store_true", help="emit a JSON validation summary")
    args = parser.parse_args(argv)

    try:
        summary = validate_plan(load_plan(args.plan))
    except PlanValidationError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        print(
            f"{summary['target']}: {summary['statement_kind']} width={summary['width']} "
            f"with {summary['go_criteria_count']} GO criteria and "
            f"{summary['no_go_criteria_count']} NO-GO criteria"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
