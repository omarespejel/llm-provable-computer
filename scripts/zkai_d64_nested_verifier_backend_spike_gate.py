#!/usr/bin/env python3
"""Hard backend spike gate for the d64 two-slice nested-verifier target.

This gate is deliberately stricter than the contract gate. It consumes the
checked two-slice contract and then inventories the repository for an executable
outer proof/PCD backend artifact. The result is GO only if a real outer proof or
accumulator and verifier handle exist and bind nested_verifier_contract_commitment
as public input. Otherwise it records the exact NO-GO blocker and withholds
proof-size/verifier-time metrics.
"""

from __future__ import annotations

import argparse
import copy
import csv
import functools
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
CONTRACT_SCRIPT = ROOT / "scripts" / "zkai_d64_nested_verifier_backend_contract_gate.py"
CONTRACT_EVIDENCE = EVIDENCE_DIR / "zkai-d64-nested-verifier-backend-contract-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d64-nested-verifier-backend-spike-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d64-nested-verifier-backend-spike-2026-05.tsv"

SCHEMA = "zkai-d64-nested-verifier-backend-spike-v1"
DECISION = "NO_GO_D64_TWO_SLICE_NESTED_VERIFIER_BACKEND_ARTIFACT_MISSING"
RESULT = "HARD_NO_GO"
BACKEND_RESULT = "NO_GO_EXECUTABLE_OUTER_BACKEND_ARTIFACT_MISSING"
SAFE_MAIN_COMMIT_AFTER_PR381 = "6fae0d115f6554258782d00612c2cecdc376af38"
SAFE_CHECKPOINT_LABEL = "main-after-pr-381"
SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")

GO_CRITERION = (
    "a checked outer proof or PCD accumulator exists, verifies the selected d64 "
    "slice-verifier checks, and binds nested_verifier_contract_commitment as a "
    "public input"
)
FIRST_BLOCKER = (
    "no executable outer proof/PCD backend artifact in the current repository can "
    "prove the selected two d64 slice-verifier checks and bind "
    "nested_verifier_contract_commitment as a public input"
)

MISSING_BACKEND_FEATURES = [
    "nested verifier program/AIR/circuit for rmsnorm_public_rows",
    "nested verifier program/AIR/circuit for rmsnorm_projection_bridge",
    "outer proof or PCD accumulator object over those selected verifier checks",
    "outer verifier handle for that proof or accumulator object",
    "public-input binding inside the outer backend for nested_verifier_contract_commitment",
    "mutation tests against relabeling of the outer proof public inputs",
]

PIVOT_OPTIONS = [
    {
        "track": "proof_native_two_slice_compression",
        "description": "compress the two-slice receipt into a proof-native object without calling it recursion",
        "claim_boundary": "compression only, not recursive verification",
    },
    {
        "track": "simpler_non_recursive_accumulator",
        "description": "build a verifier-facing accumulator over the two selected checks and keep proof semantics explicit",
        "claim_boundary": "accumulator integrity only unless backed by an outer proof",
    },
    {
        "track": "different_backend_route",
        "description": "try an external recursion-capable backend for the two-slice statement envelope",
        "claim_boundary": "adapter result until Stwo-native recursion exists",
    },
]

NON_CLAIMS = [
    "not a recursive proof object",
    "not a PCD accumulator",
    "not a benchmark",
    "not proof-size evidence",
    "not verifier-time evidence",
    "not six-slice d64 aggregation",
    "not d128 evidence",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "just gate-fast",
    "python3 scripts/zkai_d64_nested_verifier_backend_spike_gate.py --write-json docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_nested_verifier_backend_spike_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate",
]

TSV_COLUMNS = (
    "mutation",
    "surface",
    "baseline_result",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
)

EXPECTED_MUTATION_INVENTORY = (
    ("safe_checkpoint_commit_drift", "safe_checkpoint"),
    ("source_contract_path_drift", "source_contract_evidence"),
    ("source_contract_file_hash_drift", "source_contract_evidence"),
    ("source_contract_payload_hash_drift", "source_contract_evidence"),
    ("source_contract_result_drift", "source_contract_evidence"),
    ("nested_verifier_contract_commitment_drift", "nested_verifier_contract"),
    ("selected_slice_id_drift", "nested_verifier_contract"),
    ("candidate_inventory_status_relabel", "candidate_inventory"),
    ("candidate_inventory_acceptance_relabel", "candidate_inventory"),
    ("candidate_inventory_missing_required_path_removed", "candidate_inventory"),
    ("proof_object_claimed_without_artifact", "backend_attempt"),
    ("verifier_handle_claimed_without_artifact", "backend_attempt"),
    ("proof_size_metric_smuggled_before_proof", "backend_attempt"),
    ("verifier_time_metric_smuggled_before_proof", "backend_attempt"),
    ("blocked_before_metrics_disabled", "backend_attempt"),
    ("missing_backend_feature_removed", "backend_attempt"),
    ("first_blocker_removed", "backend_attempt"),
    ("backend_result_changed_to_go", "backend_attempt"),
    ("decision_changed_to_go", "parser_or_schema"),
    ("result_changed_to_go", "parser_or_schema"),
)

CANDIDATE_SPECS = [
    {
        "candidate_id": "checked_two_slice_nested_verifier_contract",
        "path": "docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json",
        "kind": "checked_contract_evidence",
        "required_for_go": False,
        "status_if_present": "CONTRACT_ONLY_NOT_OUTER_PROOF",
        "status_if_missing": "MISSING_CONTRACT_EVIDENCE",
        "reason": "defines what an outer backend must bind, but is not itself an outer proof or accumulator",
    },
    {
        "candidate_id": "d64_recursive_pcd_aggregation_feasibility_gate",
        "path": "docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json",
        "kind": "checked_aggregation_target_evidence",
        "required_for_go": False,
        "status_if_present": "AGGREGATION_TARGET_ONLY_NOT_OUTER_PROOF",
        "status_if_missing": "MISSING_AGGREGATION_TARGET_EVIDENCE",
        "reason": "shows the receipt can be an aggregation target, not that nested verifier execution is proven",
    },
    {
        "candidate_id": "phase36_recursive_verifier_harness_receipt",
        "path": "src/stwo_backend/recursion.rs",
        "kind": "rust_harness_surface",
        "required_for_go": False,
        "required_tokens": [
            "phase36_prepare_recursive_verifier_harness_receipt",
            "verify_phase36_recursive_verifier_harness_receipt",
        ],
        "status_if_present": "HARNESS_RECEIPT_NOT_NESTED_PROOF",
        "status_if_missing": "MISSING_HARNESS_SURFACE",
        "reason": "a harness receipt rejects recursive claims; it does not execute d64 slice verifiers inside an outer proof",
    },
    {
        "candidate_id": "decoding_accumulator_demos",
        "path": "src/stwo_backend/decoding.rs",
        "kind": "pre_recursive_accumulator_demo",
        "required_for_go": False,
        "required_tokens": [
            "Phase21DecodingMatrixAccumulatorManifest",
            "Phase24DecodingStateRelationAccumulatorManifest",
        ],
        "status_if_present": "PRE_RECURSIVE_ACCUMULATOR_DEMO_NOT_D64_SLICE_VERIFIER_PROOF",
        "status_if_missing": "MISSING_DECODING_ACCUMULATOR_DEMOS",
        "reason": "older accumulator demos are not nested verifier proofs for the d64 RMSNorm/bridge checks",
    },
    {
        "candidate_id": "archived_stwo_accumulation_bundle",
        "path": "docs/paper/artifacts/stwo-accumulation-v1-2026-04-09/APPENDIX_ARTIFACT_INDEX.md",
        "kind": "archived_artifact_bundle",
        "required_for_go": False,
        "status_if_present": "ARCHIVED_DECODING_ARTIFACT_NOT_CURRENT_D64_BACKEND",
        "status_if_missing": "MISSING_ARCHIVED_BUNDLE",
        "reason": "archived decoding artifacts are useful provenance but cannot satisfy the current d64 nested-verifier GO criterion",
    },
    {
        "candidate_id": "required_two_slice_outer_proof_artifact",
        "path": "docs/engineering/evidence/zkai-d64-two-slice-nested-verifier-proof-2026-05.json",
        "kind": "required_go_artifact",
        "required_for_go": True,
        "status_if_present": "PRESENT_BUT_UNVALIDATED_BY_SPIKE_GATE",
        "status_if_missing": "MISSING_REQUIRED_GO_ARTIFACT",
        "reason": "this is the first artifact that would need to exist before a recursive/PCD GO can be considered",
    },
    {
        "candidate_id": "required_two_slice_outer_verifier_handle",
        "path": "docs/engineering/evidence/zkai-d64-two-slice-nested-verifier-handle-2026-05.json",
        "kind": "required_go_artifact",
        "required_for_go": True,
        "status_if_present": "PRESENT_BUT_UNVALIDATED_BY_SPIKE_GATE",
        "status_if_missing": "MISSING_REQUIRED_GO_ARTIFACT",
        "reason": "a proof object without a checked verifier handle is not verifier-facing evidence",
    },
    {
        "candidate_id": "required_two_slice_outer_mutation_tests",
        "path": "scripts/tests/test_zkai_d64_two_slice_nested_verifier_backend.py",
        "kind": "required_go_test_surface",
        "required_for_go": True,
        "status_if_present": "PRESENT_BUT_UNVALIDATED_BY_SPIKE_GATE",
        "status_if_missing": "MISSING_REQUIRED_GO_ARTIFACT",
        "reason": "the outer backend must reject relabeling of bound public inputs before metrics are meaningful",
    },
]


class D64NestedVerifierBackendSpikeError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D64NestedVerifierBackendSpikeError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


CONTRACT = _load_module(CONTRACT_SCRIPT, "zkai_d64_nested_verifier_backend_contract_for_spike")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_hex_json(value: Any) -> str:
    return sha256_hex_bytes(canonical_json_bytes(value))


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D64NestedVerifierBackendSpikeError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D64NestedVerifierBackendSpikeError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D64NestedVerifierBackendSpikeError(f"{field} must be a list")
    return value


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D64NestedVerifierBackendSpikeError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D64NestedVerifierBackendSpikeError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D64NestedVerifierBackendSpikeError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D64NestedVerifierBackendSpikeError(f"source evidence is not a regular file: {path}")
    if ROOT.resolve() not in resolved.parents:
        raise D64NestedVerifierBackendSpikeError(f"source evidence path escapes repository: {path}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D64NestedVerifierBackendSpikeError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D64NestedVerifierBackendSpikeError(f"source evidence must be a JSON object: {path}")
    return payload


def load_checked_contract(path: pathlib.Path = CONTRACT_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        CONTRACT.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D64NestedVerifierBackendSpikeError(f"nested-verifier contract validation failed: {err}") from err
    if payload.get("contract_result") != CONTRACT.CONTRACT_RESULT:
        raise D64NestedVerifierBackendSpikeError("source contract result mismatch")
    if payload.get("backend_proof_result") != CONTRACT.BACKEND_RESULT:
        raise D64NestedVerifierBackendSpikeError("source contract backend proof result mismatch")
    if payload.get("case_count") != 20:
        raise D64NestedVerifierBackendSpikeError("source contract mutation case count mismatch")
    if payload.get("all_mutations_rejected") is not True:
        raise D64NestedVerifierBackendSpikeError("source contract did not reject all checked mutations")
    return payload


def source_contract_descriptor(source: dict[str, Any], path: pathlib.Path = CONTRACT_EVIDENCE) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "contract_result": source["contract_result"],
        "backend_proof_result": source["backend_proof_result"],
        "nested_verifier_contract_commitment": source["nested_verifier_contract_commitment"],
    }


def safe_checkpoint_descriptor() -> dict[str, Any]:
    return {
        "label": SAFE_CHECKPOINT_LABEL,
        "main_commit": SAFE_MAIN_COMMIT_AFTER_PR381,
        "recorded_after_pr": 381,
        "purpose": "safe rollback checkpoint before the executable nested-verifier backend spike",
    }


def _tokens_present(path: pathlib.Path, tokens: list[str]) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return all(token in text for token in tokens)


@functools.lru_cache(maxsize=1)
def _candidate_inventory_cached() -> tuple[tuple[tuple[str, Any], ...], ...]:
    inventory: list[dict[str, Any]] = []
    for spec in CANDIDATE_SPECS:
        path = ROOT / spec["path"]
        exists = path.is_file()
        tokens = list(spec.get("required_tokens", []))
        tokens_present = _tokens_present(path, tokens) if tokens else exists
        present_for_status = exists and tokens_present
        if present_for_status:
            status = spec["status_if_present"]
        elif exists and tokens and not tokens_present:
            status = "PRESENT_BUT_REQUIRED_SYMBOLS_MISSING"
        else:
            status = spec["status_if_missing"]
        accepted = False
        inventory.append(
            {
                "candidate_id": spec["candidate_id"],
                "path": spec["path"],
                "kind": spec["kind"],
                "exists": exists,
                "required_tokens_present": tokens_present,
                "required_for_go": bool(spec["required_for_go"]),
                "status": status,
                "accepted_as_outer_backend": accepted,
                "reason": spec["reason"],
            }
        )
    return tuple(tuple(item.items()) for item in inventory)


def candidate_inventory() -> list[dict[str, Any]]:
    return [dict(item) for item in _candidate_inventory_cached()]


def backend_attempt(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "go_criterion": GO_CRITERION,
        "backend_result": BACKEND_RESULT,
        "proof_object_exists": False,
        "verifier_handle_exists": False,
        "nested_verifier_contract_commitment_bound_in_outer_backend": False,
        "proof_size_bytes": None,
        "verifier_time_ms": None,
        "blocked_before_metrics": True,
        "candidate_inventory": copy.deepcopy(inventory),
        "missing_backend_features": MISSING_BACKEND_FEATURES,
        "first_blocker": FIRST_BLOCKER,
        "pivot_options_if_no_go": PIVOT_OPTIONS,
    }


def _selected_slice_ids(source: dict[str, Any]) -> list[str]:
    contract = require_object(source.get("nested_verifier_contract"), "source nested verifier contract")
    ids = contract.get("selected_slice_ids")
    if ids != list(SELECTED_SLICE_IDS):
        raise D64NestedVerifierBackendSpikeError("source selected slice ids mismatch")
    return ids


def build_payload() -> dict[str, Any]:
    source = load_checked_contract()
    inventory = candidate_inventory()
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "safe_checkpoint": safe_checkpoint_descriptor(),
        "source_contract_evidence": source_contract_descriptor(source),
        "selected_slice_ids": _selected_slice_ids(source),
        "nested_verifier_contract_commitment": source["nested_verifier_contract_commitment"],
        "backend_result": BACKEND_RESULT,
        "backend_attempt": backend_attempt(inventory),
        "summary": {
            "decision": DECISION,
            "result": RESULT,
            "safe_main_commit": SAFE_MAIN_COMMIT_AFTER_PR381,
            "source_contract_commitment": source["nested_verifier_contract_commitment"],
            "selected_slice_count": len(SELECTED_SLICE_IDS),
            "selected_slice_ids": list(SELECTED_SLICE_IDS),
            "backend_result": BACKEND_RESULT,
            "proof_object_exists": False,
            "verifier_handle_exists": False,
            "blocked_before_metrics": True,
            "candidate_count": len(inventory),
            "required_go_artifacts_missing": sum(
                1 for item in inventory if item["required_for_go"] and not item["accepted_as_outer_backend"]
            ),
            "first_blocker": FIRST_BLOCKER,
        },
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    _validate_draft_payload(payload)
    return payload


def _validate_source_contract_descriptor(payload: dict[str, Any]) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_contract_evidence"), "source contract evidence")
    path_value = descriptor.get("path")
    if not isinstance(path_value, str):
        raise D64NestedVerifierBackendSpikeError("source contract evidence path must be a string")
    expect_equal(path_value, relative_path(CONTRACT_EVIDENCE), "source contract evidence path")
    path = (ROOT / path_value).resolve()
    if path != CONTRACT_EVIDENCE.resolve():
        raise D64NestedVerifierBackendSpikeError("source contract evidence path mismatch")
    source = load_checked_contract(path)
    expected = source_contract_descriptor(source, path)
    expect_equal(descriptor, expected, "source contract evidence")
    return source


def _validate_backend_attempt(payload: dict[str, Any]) -> None:
    attempt = require_object(payload.get("backend_attempt"), "backend attempt")
    expect_equal(attempt.get("go_criterion"), GO_CRITERION, "backend go criterion")
    expect_equal(attempt.get("backend_result"), BACKEND_RESULT, "backend result")
    if attempt.get("proof_object_exists") is not False:
        raise D64NestedVerifierBackendSpikeError("proof object claimed without a checked outer backend artifact")
    if attempt.get("verifier_handle_exists") is not False:
        raise D64NestedVerifierBackendSpikeError("verifier handle claimed without a checked outer backend artifact")
    if attempt.get("nested_verifier_contract_commitment_bound_in_outer_backend") is not False:
        raise D64NestedVerifierBackendSpikeError("outer backend binding claimed without a checked proof artifact")
    if attempt.get("proof_size_bytes") is not None:
        raise D64NestedVerifierBackendSpikeError("proof-size metric supplied before a proof object exists")
    if attempt.get("verifier_time_ms") is not None:
        raise D64NestedVerifierBackendSpikeError("verifier-time metric supplied before a proof object exists")
    if attempt.get("blocked_before_metrics") is not True:
        raise D64NestedVerifierBackendSpikeError("blocked-before-metrics flag must stay true until a proof object exists")
    inventory = require_list(attempt.get("candidate_inventory"), "candidate inventory")
    expect_equal(inventory, candidate_inventory(), "candidate inventory")
    if any(item.get("accepted_as_outer_backend") for item in inventory if isinstance(item, dict)):
        raise D64NestedVerifierBackendSpikeError("candidate inventory accepted a non-proof surface as outer backend")
    expect_equal(attempt.get("missing_backend_features"), MISSING_BACKEND_FEATURES, "missing backend features")
    expect_equal(attempt.get("first_blocker"), FIRST_BLOCKER, "first backend blocker")
    expect_equal(attempt.get("pivot_options_if_no_go"), PIVOT_OPTIONS, "no-go pivot options")


def _expected_summary(source: dict[str, Any]) -> dict[str, Any]:
    inventory = candidate_inventory()
    return {
        "decision": DECISION,
        "result": RESULT,
        "safe_main_commit": SAFE_MAIN_COMMIT_AFTER_PR381,
        "source_contract_commitment": source["nested_verifier_contract_commitment"],
        "selected_slice_count": len(SELECTED_SLICE_IDS),
        "selected_slice_ids": list(SELECTED_SLICE_IDS),
        "backend_result": BACKEND_RESULT,
        "proof_object_exists": False,
        "verifier_handle_exists": False,
        "blocked_before_metrics": True,
        "candidate_count": len(inventory),
        "required_go_artifacts_missing": sum(
            1 for item in inventory if item["required_for_go"] and not item["accepted_as_outer_backend"]
        ),
        "first_blocker": FIRST_BLOCKER,
    }


def _validate_common_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "nested-verifier backend spike payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    safe = require_object(payload.get("safe_checkpoint"), "safe checkpoint")
    expect_equal(safe, safe_checkpoint_descriptor(), "safe checkpoint")
    source = _validate_source_contract_descriptor(payload)
    expect_equal(payload.get("selected_slice_ids"), list(SELECTED_SLICE_IDS), "selected slice ids")
    expect_equal(
        require_commitment(payload.get("nested_verifier_contract_commitment"), "nested verifier contract commitment"),
        source["nested_verifier_contract_commitment"],
        "nested verifier contract commitment",
    )
    expect_equal(payload.get("backend_result"), BACKEND_RESULT, "backend result")
    _validate_backend_attempt(payload)
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    return source, _expected_summary(source)


def _validate_draft_payload(payload: Any) -> None:
    _, expected_summary = _validate_common_payload(payload)
    if (
        "mutation_inventory" in payload
        or "cases" in payload
        or "case_count" in payload
        or "all_mutations_rejected" in payload
    ):
        raise D64NestedVerifierBackendSpikeError("draft payload must not include mutation metadata")
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_cases = "cases" in payload
    has_case_count = "case_count" in payload
    has_all_mutations_rejected = "all_mutations_rejected" in payload
    has_mutation_inventory = "mutation_inventory" in payload
    if not (has_cases or has_case_count or has_all_mutations_rejected or has_mutation_inventory):
        raise D64NestedVerifierBackendSpikeError(
            "mutation metadata must include mutation_inventory, cases, case_count, and all_mutations_rejected"
        )
    if not (has_mutation_inventory and has_cases and has_case_count and has_all_mutations_rejected):
        raise D64NestedVerifierBackendSpikeError(
            "mutation metadata must include mutation_inventory, cases, case_count, and all_mutations_rejected together"
        )

    inventory = require_list(payload.get("mutation_inventory"), "mutation inventory")
    expect_equal(inventory, expected_mutation_inventory(), "mutation inventory")
    cases = require_list(payload.get("cases"), "mutation cases")
    computed_rejected = 0
    case_pairs: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        for column in TSV_COLUMNS:
            if column not in case:
                raise D64NestedVerifierBackendSpikeError(f"mutation case {index} missing {column}")
        pair = (case["mutation"], case["surface"])
        if pair in seen_pairs:
            raise D64NestedVerifierBackendSpikeError(f"duplicate mutation case {index}")
        seen_pairs.add(pair)
        case_pairs.append(pair)
        if case["baseline_result"] != RESULT:
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} baseline_result mismatch")
        if not isinstance(case["mutated_accepted"], bool):
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} mutated_accepted must be boolean")
        if not isinstance(case["rejected"], bool):
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} rejected must be boolean")
        if case["rejected"] == case["mutated_accepted"]:
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} rejected/accepted fields are inconsistent")
        if not isinstance(case["rejection_layer"], str) or not case["rejection_layer"]:
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} rejection_layer must be a non-empty string")
        if not isinstance(case["error"], str):
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} error must be a string")
        if case["rejected"] and not case["error"]:
            raise D64NestedVerifierBackendSpikeError(f"mutation case {index} rejected case error must be non-empty")
        if case["rejected"]:
            computed_rejected += 1
    computed_case_count = len(cases)
    expect_equal(tuple(case_pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), computed_case_count, "mutation case_count")
    expect_equal(payload.get("all_mutations_rejected"), all(case["rejected"] for case in cases), "all_mutations_rejected")
    return computed_case_count, computed_rejected


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "nested-verifier backend spike payload")
    source, expected_summary = _validate_common_payload(payload)
    computed_case_count, computed_rejected = _validate_case_metadata(payload)
    if computed_rejected != computed_case_count:
        raise D64NestedVerifierBackendSpikeError("not all backend spike mutations rejected")
    expected_summary["mutation_cases"] = computed_case_count
    expected_summary["mutations_rejected"] = computed_rejected
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")
    # Source is kept in scope to make accidental validator rewrites visible in coverage.
    expect_equal(source["nested_verifier_contract_commitment"], payload["nested_verifier_contract_commitment"], "source contract commitment")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "safe checkpoint" in text:
        return "safe_checkpoint"
    if "source contract" in text or "source evidence" in text or "file_sha" in text or "payload_sha" in text:
        return "source_contract_evidence"
    if "contract commitment" in text or "selected slice" in text:
        return "nested_verifier_contract"
    if "candidate inventory" in text:
        return "candidate_inventory"
    if "proof" in text or "verifier" in text or "backend" in text or "metric" in text or "feature" in text or "blocker" in text:
        return "backend_attempt"
    if "summary" in text:
        return "summary"
    return "parser_or_schema"


def exception_message(error: Exception) -> str:
    text = str(error)
    if text:
        return text
    return f"{type(error).__name__} with empty message"


def _candidate_row(payload: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for item in payload["backend_attempt"]["candidate_inventory"]:
        if item["candidate_id"] == candidate_id:
            return item
    raise D64NestedVerifierBackendSpikeError(f"candidate inventory row missing: {candidate_id}")


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any], Exception | None]]:
    cases: list[tuple[str, str, dict[str, Any], Exception | None]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None]) -> None:
        mutated = copy.deepcopy(baseline)
        generation_error = None
        try:
            mutator(mutated)
        except Exception as err:  # noqa: BLE001 - mutation failures are recorded as rejected cases.
            generation_error = err
        cases.append((name, surface, mutated, generation_error))

    add("safe_checkpoint_commit_drift", "safe_checkpoint", lambda p: p["safe_checkpoint"].__setitem__("main_commit", "0" * 40))
    add("source_contract_path_drift", "source_contract_evidence", lambda p: p["source_contract_evidence"].__setitem__("path", "docs/engineering/evidence/../evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json"))
    add("source_contract_file_hash_drift", "source_contract_evidence", lambda p: p["source_contract_evidence"].__setitem__("file_sha256", "11" * 32))
    add("source_contract_payload_hash_drift", "source_contract_evidence", lambda p: p["source_contract_evidence"].__setitem__("payload_sha256", "22" * 32))
    add("source_contract_result_drift", "source_contract_evidence", lambda p: p["source_contract_evidence"].__setitem__("contract_result", "NO_GO"))
    add("nested_verifier_contract_commitment_drift", "nested_verifier_contract", lambda p: p.__setitem__("nested_verifier_contract_commitment", "blake2b-256:" + "33" * 32))
    add("selected_slice_id_drift", "nested_verifier_contract", lambda p: p["selected_slice_ids"].__setitem__(1, "tampered_bridge"))
    add("candidate_inventory_status_relabel", "candidate_inventory", lambda p: _candidate_row(p, "phase36_recursive_verifier_harness_receipt").__setitem__("status", "OUTER_PROOF_VERIFIED"))
    add("candidate_inventory_acceptance_relabel", "candidate_inventory", lambda p: _candidate_row(p, "phase36_recursive_verifier_harness_receipt").__setitem__("accepted_as_outer_backend", True))
    add("candidate_inventory_missing_required_path_removed", "candidate_inventory", lambda p: p["backend_attempt"]["candidate_inventory"].remove(_candidate_row(p, "required_two_slice_outer_mutation_tests")))
    add("proof_object_claimed_without_artifact", "backend_attempt", lambda p: p["backend_attempt"].__setitem__("proof_object_exists", True))
    add("verifier_handle_claimed_without_artifact", "backend_attempt", lambda p: p["backend_attempt"].__setitem__("verifier_handle_exists", True))
    add("proof_size_metric_smuggled_before_proof", "backend_attempt", lambda p: p["backend_attempt"].__setitem__("proof_size_bytes", 4096))
    add("verifier_time_metric_smuggled_before_proof", "backend_attempt", lambda p: p["backend_attempt"].__setitem__("verifier_time_ms", 12.5))
    add("blocked_before_metrics_disabled", "backend_attempt", lambda p: p["backend_attempt"].__setitem__("blocked_before_metrics", False))
    add("missing_backend_feature_removed", "backend_attempt", lambda p: p["backend_attempt"]["missing_backend_features"].pop())
    add("first_blocker_removed", "backend_attempt", lambda p: p["backend_attempt"].__setitem__("first_blocker", ""))
    add("backend_result_changed_to_go", "backend_attempt", lambda p: p.__setitem__("backend_result", "GO"))
    add("decision_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("decision", "GO_D64_TWO_SLICE_NESTED_VERIFIER_BACKEND"))
    add("result_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("result", "GO"))
    return cases


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    _validate_draft_payload(baseline)
    cases = []
    for mutation, surface, mutated, generation_error in _mutated_cases(baseline):
        if generation_error is not None:
            accepted = False
            error = exception_message(generation_error)
            layer = classify_error(generation_error)
        else:
            try:
                _validate_draft_payload(mutated)
                accepted = True
                error = ""
                layer = "accepted"
            except D64NestedVerifierBackendSpikeError as err:
                accepted = False
                error = str(err)
                layer = classify_error(err)
        cases.append(
            {
                "mutation": mutation,
                "surface": surface,
                "baseline_result": RESULT,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer,
                "error": error,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    payload = build_payload()
    cases = mutation_cases(payload)
    result = copy.deepcopy(payload)
    result["mutation_inventory"] = expected_mutation_inventory()
    result["case_count"] = len(cases)
    result["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    result["cases"] = cases
    result["summary"]["mutation_cases"] = len(cases)
    result["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(result)
    if not result["all_mutations_rejected"]:
        raise D64NestedVerifierBackendSpikeError("not all backend spike mutations rejected")
    return result


def to_tsv(payload: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: case[key] for key in TSV_COLUMNS} for case in payload["cases"])
    return buffer.getvalue()


def _validated_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D64NestedVerifierBackendSpikeError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise D64NestedVerifierBackendSpikeError(f"output path escapes repository: {path}")
    if resolved.exists() and resolved.is_dir():
        raise D64NestedVerifierBackendSpikeError(f"output path must be a file, not a directory: {path}")
    if resolved.parent.exists() and not resolved.parent.is_dir():
        raise D64NestedVerifierBackendSpikeError(f"output path parent is not a directory: {path}")
    return resolved


def _stage_text(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        return pathlib.Path(handle.name)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    json_output = _validated_output_path(json_path) if json_path is not None else None
    tsv_output = _validated_output_path(tsv_path) if tsv_path is not None else None
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n" if json_path is not None else None
    tsv_text = to_tsv(payload) if tsv_path is not None else None
    staged: list[tuple[pathlib.Path, pathlib.Path]] = []
    committed: list[tuple[pathlib.Path, bool, bytes | None]] = []
    try:
        if json_output is not None:
            staged.append((_stage_text(json_output, json_text), json_output))
        if tsv_output is not None:
            staged.append((_stage_text(tsv_output, tsv_text), tsv_output))
        for tmp_path, output_path in staged:
            existed = output_path.exists()
            previous = output_path.read_bytes() if existed else None
            tmp_path.replace(output_path)
            committed.append((output_path, existed, previous))
    except Exception as err:
        cleanup_errors: list[str] = []
        for tmp_path, _ in staged:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError as cleanup_err:
                cleanup_errors.append(f"cleanup failed for {tmp_path}: {cleanup_err}")
        for output_path, existed, previous in reversed(committed):
            try:
                if existed and previous is not None:
                    output_path.write_bytes(previous)
                else:
                    output_path.unlink(missing_ok=True)
            except OSError as rollback_err:
                cleanup_errors.append(f"rollback failed for {output_path}: {rollback_err}")
        if isinstance(err, OSError):
            detail = f"failed to write outputs: {err}"
            if cleanup_errors:
                detail += "; " + "; ".join(cleanup_errors)
            raise D64NestedVerifierBackendSpikeError(detail) from err
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
