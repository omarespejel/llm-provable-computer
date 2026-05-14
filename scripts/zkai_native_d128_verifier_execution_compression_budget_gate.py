#!/usr/bin/env python3
"""Pin the d128 verifier-execution compression budget.

This gate consumes the checked d128 two-slice verifier-execution target and the
compressed outer statement typed-accounting evidence. It records the exact gap
between the compact statement-binding proof and the object class that would be
comparable to a NANOZK-style d128 block-proof row.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

TARGET_EVIDENCE = EVIDENCE_DIR / "zkai-native-d128-two-slice-verifier-execution-target-2026-05.json"
COMPACT_TYPED_EVIDENCE = (
    EVIDENCE_DIR / "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json"
)

JSON_OUT = EVIDENCE_DIR / "zkai-native-d128-verifier-execution-compression-budget-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-verifier-execution-compression-budget-2026-05.tsv"

SCHEMA = "zkai-native-d128-verifier-execution-compression-budget-gate-v1"
DECISION = "GO_D128_VERIFIER_EXECUTION_COMPRESSION_BUDGET_PINNED"
RESULT = "BUDGET_PINNED_NOT_NANOZK_WIN"
QUESTION = (
    "How much must the real d128 verifier-execution target shrink before it can be "
    "compared honestly with NANOZK's paper-reported d128 block-proof row?"
)
CLAIM_BOUNDARY = (
    "D128_VERIFIER_EXECUTION_COMPRESSION_BUDGET_PINNED_FOR_NEXT_NATIVE_STWO_ATTACK_"
    "NOT_A_COMPACT_STATEMENT_BINDING_NANOZK_WIN"
)
FIRST_BLOCKER = (
    "the compact outer statement proof is small, but the comparable object class is the "
    "selected inner verifier-execution target at 12,688 local typed bytes, and the repo "
    "still lacks a native Stwo AIR or component-native reprove that replaces that target"
)

NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900
EXPECTED_SOURCE_DESCRIPTORS = {
    "verifier_execution_target": {
        "path": "docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json",
        "file_sha256": "a8a79771e10e58ba1b493487c0e64c44abaa2a254dc9a818f67eea99453e3564",
        "payload_sha256": "0230bc05165c94f4f314c39bb39afca80b5fc25e46488347bf244778a04f8aac",
        "schema": "zkai-native-d128-two-slice-verifier-execution-target-gate-v1",
        "decision": "GO_SELECTED_INNER_PROOF_OBJECTS_PINNED_NATIVE_VERIFIER_EXECUTION_TARGET",
        "payload_commitment": "sha256:a46fa76264588965997dbb323cd94d3c4defcb2ad38230b6bd9420be631a2c85",
    },
    "compact_statement_typed_accounting": {
        "path": "docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json",
        "file_sha256": "28345bdaa1e479cd857a614c31cf98a12aaede6a8d00e2e4b46807903ee01bf0",
        "payload_sha256": "54bf65728400d4143425332d2e94a4c5eed826fea2e1def3eae5a9d59d6ac119",
        "schema": "zkai-native-d128-compressed-outer-statement-binary-typed-accounting-gate-v1",
        "decision": "GO_LOCAL_BINARY_TYPED_ACCOUNTING_FOR_COMPRESSED_D128_OUTER_STATEMENT_PROOF",
        "payload_commitment": "blake2b-256:0b313a71788decd2e4c20ce4630d788c8d97c34e30d888d1caefacc68a2b7683",
    },
}

EXPECTED_COMPARISON_OBJECTS = {
    "compact_statement_binding": {
        "object_class": "native_outer_statement_binding_proof_not_verifier_execution",
        "status": "real_compact_binding_object_not_comparable_to_nanozk_block_proof",
        "proof_json_size_bytes": 3_516,
        "local_typed_bytes": 1_792,
        "ratio_vs_nanozk_json": 0.509565,
        "ratio_vs_nanozk_typed": 0.25971,
        "comparable_to_nanozk_block_proof": False,
        "reason_not_comparable": "binds host-verified selected slice statements but does not execute the selected inner Stwo verifier checks",
    },
    "selected_inner_verifier_execution_target": {
        "object_class": "selected_inner_stwo_proof_envelopes_target_for_native_verifier_execution",
        "status": "target_surface_concrete_but_not_executed_by_native_outer_air",
        "proof_json_size_bytes": 34_866,
        "local_typed_bytes": 12_688,
        "ratio_vs_nanozk_json": 5.053043,
        "ratio_vs_nanozk_typed": 1.838841,
        "comparable_to_nanozk_block_proof": "candidate_after_native_execution_or_component_reprove",
        "reason_not_comparable": "the proof envelopes are target inputs, not one native d128 block proof object yet",
    },
}

EXPECTED_COMPRESSION_BUDGET = {
    "nanozk_paper_reported_d128_block_proof_bytes": 6_900,
    "current_verifier_target_typed_bytes": 12_688,
    "current_verifier_target_json_bytes": 34_866,
    "compact_statement_typed_bytes": 1_792,
    "compact_statement_json_bytes": 3_516,
    "typed_bytes_to_remove_to_equal_nanozk": 5_788,
    "json_bytes_to_remove_to_equal_nanozk": 27_966,
    "typed_required_share_of_current_target": 0.543821,
    "typed_required_reduction_ratio": 0.456179,
    "json_required_share_of_current_target": 0.197901,
    "json_required_reduction_ratio": 0.802099,
    "current_target_typed_over_nanozk": 1.838841,
    "current_target_json_over_nanozk": 5.053043,
    "current_target_typed_over_compact_statement": 7.080357,
    "current_target_json_over_compact_statement": 9.916382,
    "compact_statement_typed_share_of_target": 0.141236,
    "compact_statement_json_share_of_target": 0.100843,
}

ATTACK_PATHS = [
    {
        "path_id": "component_native_reprove",
        "classification": "PROMISING_STARK_NATIVE_ROUTE",
        "comparison_status": "potentially_comparable_after_same_statement_binding_and_native_constraints",
        "why": (
            "replace inner-proof verification with native Stwo constraints for the selected "
            "RMSNorm and projection-bridge relations, avoiding the 12,688-byte inner-proof target"
        ),
        "next_gate": "prove or no-go a two-slice component-native reprove with the same source and statement commitments",
    },
    {
        "path_id": "native_stwo_verifier_execution_air",
        "classification": "STRICT_VERIFIER_EXECUTION_ROUTE",
        "comparison_status": "comparable_after_native_outer_air_executes_selected_inner_verifier_checks",
        "why": (
            "consume the pinned proof envelopes and execute their selected verifier checks inside "
            "a native Stwo outer proof object"
        ),
        "next_gate": "build the smallest verifier-execution AIR or record a bounded no-go with row and byte reasons",
    },
    {
        "path_id": "semantic_digest_binding",
        "classification": "NOT_NANOZK_COMPARABLE_BUT_USEFUL_FOR_ARCHITECTURE",
        "comparison_status": "not_comparable_to_block_proof_size",
        "why": (
            "the compact proof binds statement and source commitments, but host verification remains "
            "outside the native proof object"
        ),
        "next_gate": "keep as a binding primitive and never promote its 1,792 typed bytes as a matched NANOZK win",
    },
    {
        "path_id": "external_receipt_controls",
        "classification": "CONTROL_NOT_NATIVE_STARK",
        "comparison_status": "useful_control_not_core_breakthrough_path",
        "why": "SNARK or zkVM receipts can calibrate verifier surfaces but do not prove the STARK-native thesis",
        "next_gate": "only compare as external receipt controls with explicit backend and setup caveats",
    },
]

NON_CLAIMS = [
    "not a NANOZK proof-size win",
    "not a matched NANOZK benchmark",
    "not native verifier execution of the selected inner Stwo proofs",
    "not a native d128 transformer-block proof",
    "not recursion or proof-carrying data",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_native_d128_two_slice_verifier_execution_target_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.tsv",
    "python3 scripts/zkai_native_d128_compressed_outer_statement_binary_accounting_gate.py --write-json docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv",
    "python3 scripts/zkai_native_d128_verifier_execution_compression_budget_gate.py --write-json docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_d128_verifier_execution_compression_budget_gate.py scripts/tests/test_zkai_native_d128_verifier_execution_compression_budget_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_d128_verifier_execution_compression_budget_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "object_id",
    "object_class",
    "status",
    "proof_json_size_bytes",
    "local_typed_bytes",
    "ratio_vs_nanozk_json",
    "ratio_vs_nanozk_typed",
    "comparable_to_nanozk_block_proof",
)

MUTATION_NAMES = (
    "target_source_file_hash_drift",
    "compact_source_payload_hash_drift",
    "target_typed_metric_smuggling",
    "target_json_metric_smuggling",
    "compact_promoted_to_comparable",
    "nanozk_baseline_smuggling",
    "typed_reduction_budget_drift",
    "json_reduction_budget_drift",
    "claim_boundary_overclaim",
    "result_changed_to_win",
    "first_blocker_removed",
    "component_native_route_demoted",
    "semantic_digest_promoted",
    "non_claim_removed",
    "validation_command_drift",
    "source_decision_relabeling",
    "payload_commitment_relabeling",
    "unknown_top_level_field_added",
)


class CompressionBudgetGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise CompressionBudgetGateError(f"invalid JSON value: {err}") from err


def pretty_json(value: dict[str, Any]) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise CompressionBudgetGateError(f"invalid JSON value: {err}") from err


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + sha256_hex(canonical_json_bytes(material))


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_json_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in items:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CompressionBudgetGateError(f"{field} must be object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise CompressionBudgetGateError(f"{field} must be list")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CompressionBudgetGateError(f"{field} must be non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CompressionBudgetGateError(f"{field} must be integer")
    return value


def rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise CompressionBudgetGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise CompressionBudgetGateError(f"source evidence is not a regular file: {path}")
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise CompressionBudgetGateError(f"source evidence escapes repository: {path}") from err
    raw = resolved.read_bytes()
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except Exception as err:
        raise CompressionBudgetGateError(f"failed to parse JSON {path}: {err}") from err
    return require_dict(payload, str(path)), raw


def source_descriptor(source_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    expected = EXPECTED_SOURCE_DESCRIPTORS[source_id]
    descriptor = {
        "source_id": source_id,
        "path": str(path.resolve().relative_to(ROOT.resolve())),
        "file_sha256": sha256_hex(raw),
        "payload_sha256": sha256_hex(canonical_json_bytes(payload)),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "payload_commitment": payload.get("payload_commitment"),
    }
    if descriptor != {"source_id": source_id, **expected}:
        raise CompressionBudgetGateError(f"{source_id} source descriptor drift")
    return descriptor


def load_sources() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    target, target_raw = load_json(TARGET_EVIDENCE)
    compact, compact_raw = load_json(COMPACT_TYPED_EVIDENCE)
    descriptors = [
        source_descriptor("verifier_execution_target", TARGET_EVIDENCE, target, target_raw),
        source_descriptor("compact_statement_typed_accounting", COMPACT_TYPED_EVIDENCE, compact, compact_raw),
    ]
    return target, compact, descriptors


def comparison_objects(target: dict[str, Any], compact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    target_aggregate = require_dict(target.get("aggregate"), "target aggregate")
    compact_aggregate = require_dict(compact.get("aggregate"), "compact aggregate")
    observed = {
        "compact_statement_binding": {
            "object_class": "native_outer_statement_binding_proof_not_verifier_execution",
            "status": "real_compact_binding_object_not_comparable_to_nanozk_block_proof",
            "proof_json_size_bytes": require_int(
                compact_aggregate.get("proof_json_size_bytes"), "compact proof_json_size_bytes"
            ),
            "local_typed_bytes": require_int(compact_aggregate.get("local_typed_bytes"), "compact local_typed_bytes"),
            "ratio_vs_nanozk_json": compact_aggregate.get("json_ratio_vs_nanozk_paper_row"),
            "ratio_vs_nanozk_typed": compact_aggregate.get("typed_ratio_vs_nanozk_paper_row"),
            "comparable_to_nanozk_block_proof": False,
            "reason_not_comparable": "binds host-verified selected slice statements but does not execute the selected inner Stwo verifier checks",
        },
        "selected_inner_verifier_execution_target": {
            "object_class": "selected_inner_stwo_proof_envelopes_target_for_native_verifier_execution",
            "status": "target_surface_concrete_but_not_executed_by_native_outer_air",
            "proof_json_size_bytes": require_int(
                target_aggregate.get("selected_inner_proof_json_bytes"), "target selected_inner_proof_json_bytes"
            ),
            "local_typed_bytes": require_int(
                target_aggregate.get("selected_inner_local_typed_bytes"), "target selected_inner_local_typed_bytes"
            ),
            "ratio_vs_nanozk_json": target_aggregate.get("selected_inner_json_ratio_vs_nanozk_paper_row"),
            "ratio_vs_nanozk_typed": target_aggregate.get("selected_inner_typed_ratio_vs_nanozk_paper_row"),
            "comparable_to_nanozk_block_proof": "candidate_after_native_execution_or_component_reprove",
            "reason_not_comparable": "the proof envelopes are target inputs, not one native d128 block proof object yet",
        },
    }
    if observed != EXPECTED_COMPARISON_OBJECTS:
        raise CompressionBudgetGateError(f"comparison object drift: {observed}")
    return observed


def compression_budget(objects: dict[str, dict[str, Any]]) -> dict[str, Any]:
    target = objects["selected_inner_verifier_execution_target"]
    compact = objects["compact_statement_binding"]
    target_typed = require_int(target["local_typed_bytes"], "target local_typed_bytes")
    target_json = require_int(target["proof_json_size_bytes"], "target proof_json_size_bytes")
    compact_typed = require_int(compact["local_typed_bytes"], "compact local_typed_bytes")
    compact_json = require_int(compact["proof_json_size_bytes"], "compact proof_json_size_bytes")
    computed = {
        "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "current_verifier_target_typed_bytes": target_typed,
        "current_verifier_target_json_bytes": target_json,
        "compact_statement_typed_bytes": compact_typed,
        "compact_statement_json_bytes": compact_json,
        "typed_bytes_to_remove_to_equal_nanozk": target_typed - NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "json_bytes_to_remove_to_equal_nanozk": target_json - NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
        "typed_required_share_of_current_target": rounded_ratio(
            NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES, target_typed
        ),
        "typed_required_reduction_ratio": rounded_ratio(
            target_typed - NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES, target_typed
        ),
        "json_required_share_of_current_target": rounded_ratio(
            NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES, target_json
        ),
        "json_required_reduction_ratio": rounded_ratio(
            target_json - NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES, target_json
        ),
        "current_target_typed_over_nanozk": rounded_ratio(
            target_typed, NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
        ),
        "current_target_json_over_nanozk": rounded_ratio(
            target_json, NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES
        ),
        "current_target_typed_over_compact_statement": rounded_ratio(target_typed, compact_typed),
        "current_target_json_over_compact_statement": rounded_ratio(target_json, compact_json),
        "compact_statement_typed_share_of_target": rounded_ratio(compact_typed, target_typed),
        "compact_statement_json_share_of_target": rounded_ratio(compact_json, target_json),
    }
    if computed != EXPECTED_COMPRESSION_BUDGET:
        raise CompressionBudgetGateError(f"compression budget drift: {computed}")
    return computed


def build_payload() -> dict[str, Any]:
    target, compact, descriptors = load_sources()
    objects = comparison_objects(target, compact)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "question": QUESTION,
        "claim_boundary": CLAIM_BOUNDARY,
        "comparison_baseline": {
            "nanozk_paper_reported_d128_block_proof_bytes": NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES,
            "status": "paper_reported_not_locally_reproduced_not_matched_object_class",
        },
        "source_evidence": descriptors,
        "comparison_objects": objects,
        "compression_budget": compression_budget(objects),
        "attack_paths": ATTACK_PATHS,
        "first_blocker": FIRST_BLOCKER,
        "next_research_step": (
            "try component_native_reprove first, then native_stwo_verifier_execution_air if the component "
            "route cannot preserve the same source and statement commitments"
        ),
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    cases = mutation_cases(payload)
    rejected = collect_mutation_rejections(cases)
    payload["mutation_cases"] = rejected
    payload["mutations_checked"] = len(rejected)
    payload["mutations_rejected"] = sum(1 for case in rejected if case["rejected"])
    payload["all_mutations_rejected"] = all(case["rejected"] for case in rejected)
    payload["payload_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any], *, allow_missing_mutation_summary: bool = False) -> None:
    expected_keys = {
        "schema",
        "decision",
        "result",
        "question",
        "claim_boundary",
        "comparison_baseline",
        "source_evidence",
        "comparison_objects",
        "compression_budget",
        "attack_paths",
        "first_blocker",
        "next_research_step",
        "non_claims",
        "validation_commands",
        "payload_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    keys = set(payload)
    if allow_missing_mutation_summary:
        if not keys.issubset(expected_keys | mutation_keys) or not expected_keys.issubset(keys):
            raise CompressionBudgetGateError("payload field drift")
        present_mutation_keys = keys & mutation_keys
        if present_mutation_keys and present_mutation_keys != mutation_keys:
            raise CompressionBudgetGateError("partial mutation summary drift")
    elif keys != expected_keys | mutation_keys:
        raise CompressionBudgetGateError("payload field drift")
    if payload.get("schema") != SCHEMA:
        raise CompressionBudgetGateError("schema drift")
    if payload.get("decision") != DECISION:
        raise CompressionBudgetGateError("decision drift")
    if payload.get("result") != RESULT:
        raise CompressionBudgetGateError("result drift")
    if payload.get("question") != QUESTION:
        raise CompressionBudgetGateError("question drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise CompressionBudgetGateError("claim boundary drift")
    baseline = require_dict(payload.get("comparison_baseline"), "comparison baseline")
    if baseline.get("nanozk_paper_reported_d128_block_proof_bytes") != NANOZK_PAPER_REPORTED_D128_BLOCK_PROOF_BYTES:
        raise CompressionBudgetGateError("NANOZK baseline drift")
    if baseline.get("status") != "paper_reported_not_locally_reproduced_not_matched_object_class":
        raise CompressionBudgetGateError("comparison baseline status drift")
    descriptors = require_list(payload.get("source_evidence"), "source evidence")
    expected_descriptors = [
        {"source_id": source_id, **descriptor}
        for source_id, descriptor in EXPECTED_SOURCE_DESCRIPTORS.items()
    ]
    if descriptors != expected_descriptors:
        raise CompressionBudgetGateError("source evidence drift")
    if payload.get("comparison_objects") != EXPECTED_COMPARISON_OBJECTS:
        raise CompressionBudgetGateError("comparison objects drift")
    if payload.get("compression_budget") != EXPECTED_COMPRESSION_BUDGET:
        raise CompressionBudgetGateError("compression budget drift")
    if payload.get("attack_paths") != ATTACK_PATHS:
        raise CompressionBudgetGateError("attack paths drift")
    if payload.get("first_blocker") != FIRST_BLOCKER:
        raise CompressionBudgetGateError("first blocker drift")
    if payload.get("next_research_step") != (
        "try component_native_reprove first, then native_stwo_verifier_execution_air if the component "
        "route cannot preserve the same source and statement commitments"
    ):
        raise CompressionBudgetGateError("next research step drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise CompressionBudgetGateError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise CompressionBudgetGateError("validation commands drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise CompressionBudgetGateError("payload commitment drift")
    if not allow_missing_mutation_summary or (set(payload) & mutation_keys):
        validate_mutation_summary(payload)


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    cases = require_list(payload.get("mutation_cases"), "mutation cases")
    names = tuple(require_str(require_dict(case, "mutation case").get("name"), "mutation case name") for case in cases)
    if names != MUTATION_NAMES:
        raise CompressionBudgetGateError("mutation inventory drift")
    checked = require_int(payload.get("mutations_checked"), "mutations_checked")
    rejected = require_int(payload.get("mutations_rejected"), "mutations_rejected")
    if checked != len(MUTATION_NAMES) or rejected != len(MUTATION_NAMES):
        raise CompressionBudgetGateError("mutation count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise CompressionBudgetGateError("mutation rejection summary drift")
    for case in cases:
        case = require_dict(case, "mutation case")
        if case.get("rejected") is not True:
            raise CompressionBudgetGateError("mutation was not rejected")
        require_str(case.get("error"), "mutation error")


def mutation_cases(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple({"name": name, "payload": mutate_payload(payload, name)} for name in MUTATION_NAMES)


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if name == "target_source_file_hash_drift":
        mutated["source_evidence"][0]["file_sha256"] = "0" * 64
    elif name == "compact_source_payload_hash_drift":
        mutated["source_evidence"][1]["payload_sha256"] = "0" * 64
    elif name == "target_typed_metric_smuggling":
        mutated["comparison_objects"]["selected_inner_verifier_execution_target"]["local_typed_bytes"] -= 1
    elif name == "target_json_metric_smuggling":
        mutated["comparison_objects"]["selected_inner_verifier_execution_target"]["proof_json_size_bytes"] -= 1
    elif name == "compact_promoted_to_comparable":
        mutated["comparison_objects"]["compact_statement_binding"]["comparable_to_nanozk_block_proof"] = True
    elif name == "nanozk_baseline_smuggling":
        mutated["comparison_baseline"]["nanozk_paper_reported_d128_block_proof_bytes"] = 5_000
    elif name == "typed_reduction_budget_drift":
        mutated["compression_budget"]["typed_required_reduction_ratio"] -= 0.000001
    elif name == "json_reduction_budget_drift":
        mutated["compression_budget"]["json_bytes_to_remove_to_equal_nanozk"] -= 1
    elif name == "claim_boundary_overclaim":
        mutated["claim_boundary"] = "D128_VERIFIER_EXECUTION_COMPRESSION_BUDGET_IS_NANOZK_WIN"
    elif name == "result_changed_to_win":
        mutated["result"] = "MATCHED_NANOZK_PROOF_SIZE_WIN"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "component_native_route_demoted":
        mutated["attack_paths"][0]["classification"] = "LOW_PRIORITY"
    elif name == "semantic_digest_promoted":
        mutated["attack_paths"][2]["comparison_status"] = "matched_nanozk_comparable"
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "validation_command_drift":
        mutated["validation_commands"] = mutated["validation_commands"][:-1]
    elif name == "source_decision_relabeling":
        mutated["source_evidence"][1]["decision"] = "MATCHED_NANOZK_WIN"
    elif name == "payload_commitment_relabeling":
        mutated["payload_commitment"] = "sha256:" + ("0" * 64)
        return mutated
    elif name == "unknown_top_level_field_added":
        mutated["unexpected"] = True
    else:
        raise AssertionError(f"unhandled mutation {name}")
    mutated["payload_commitment"] = payload_commitment(mutated)
    return mutated


def collect_mutation_rejections(cases: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    rejected = []
    for case in cases:
        try:
            validate_payload(case["payload"], allow_missing_mutation_summary=True)
        except Exception as err:
            rejected.append({"name": case["name"], "rejected": True, "error": str(err)})
        else:
            rejected.append({"name": case["name"], "rejected": False, "error": ""})
    return rejected


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=TSV_COLUMNS, delimiter="\t", extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for object_id, row in payload["comparison_objects"].items():
        writer.writerow({"object_id": object_id, **row})
    return output.getvalue()


def reject_symlinked_path_components(path: pathlib.Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as err:
        raise CompressionBudgetGateError(f"{label} is not under repo root: {path}") from err
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CompressionBudgetGateError(f"{label} component must not be a symlink: {current}")


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    raw_path = path if path.is_absolute() else ROOT / path
    reject_symlinked_path_components(EVIDENCE_DIR, "evidence dir")
    reject_symlinked_path_components(raw_path, "output path")
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise CompressionBudgetGateError(f"output path must be under evidence dir: {raw_path}") from err
    if not resolved.parent.exists():
        raise CompressionBudgetGateError(f"output parent does not exist: {resolved.parent}")
    if resolved.exists() and resolved.is_dir():
        raise CompressionBudgetGateError(f"output path must be a file: {resolved}")
    return resolved


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    path = validate_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp_path.replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    write_text_atomic(path, pretty_json(payload) + "\n")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    write_text_atomic(path, to_tsv(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    payload = build_payload()
    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload)
    if not args.write_json and not args.write_tsv:
        print(pretty_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
