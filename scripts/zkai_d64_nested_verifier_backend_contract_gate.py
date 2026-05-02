#!/usr/bin/env python3
"""Define the first d64 nested-verifier backend contract and record the proof blocker.

This gate consumes the checked d64 recursive/PCD aggregation-target evidence. It
narrows the next backend implementation to a two-slice nested-verifier contract:
an outer backend must verify the first two d64 slice-verifier checks and bind the
contract commitment as public input. The gate intentionally records a bounded
NO-GO for the backend proof artifact until such an outer proof/accumulator and
verifier handle exist.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
FEASIBILITY_SCRIPT = ROOT / "scripts" / "zkai_d64_recursive_pcd_aggregation_feasibility_gate.py"
FEASIBILITY_EVIDENCE = EVIDENCE_DIR / "zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d64-nested-verifier-backend-contract-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d64-nested-verifier-backend-contract-2026-05.tsv"

SCHEMA = "zkai-d64-nested-verifier-backend-contract-v1"
DECISION = "NO_GO_D64_NESTED_VERIFIER_BACKEND_PROOF_ARTIFACT_UNAVAILABLE"
RESULT = "BOUNDED_NO_GO"
CONTRACT_RESULT = "GO_D64_NESTED_VERIFIER_BACKEND_CONTRACT"
BACKEND_RESULT = "NO_GO_NESTED_VERIFIER_BACKEND_PROOF_ARTIFACT_UNAVAILABLE"
CONTRACT_VERSION = "zkai-d64-two-slice-nested-verifier-contract-v1"
CONTRACT_KIND = "d64-two-slice-nested-verifier-backend-contract"
CONTRACT_DOMAIN = "ptvm:zkai:d64-nested-verifier:backend-contract:v1"
MINIMUM_NESTED_SLICE_CHECKS = 2
SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")

FIRST_BLOCKER = (
    "missing executable nested-verifier backend artifact that proves the selected d64 "
    "slice-verifier checks inside one verifier-facing proof or PCD accumulator"
)

MISSING_ARTIFACTS = [
    "nested verifier program/AIR/circuit for the d64 RMSNorm public-row slice verifier",
    "nested verifier program/AIR/circuit for the d64 RMSNorm-to-projection bridge verifier",
    "outer proof or PCD accumulator object over the selected nested verifier checks",
    "outer verifier handle for the resulting nested-verifier proof or accumulator",
    "public-input binding test that derives nested_verifier_contract_commitment inside the outer backend",
]

NON_CLAIMS = [
    "not a recursive proof object",
    "not a PCD accumulator",
    "not aggregation of all six d64 slice proofs",
    "not proof-size or verifier-time evidence",
    "not onchain deployment evidence",
    "not private parameter-opening proof",
    "not full transformer inference",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_nested_verifier_backend_contract_gate.py --write-json docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_nested_verifier_backend_contract_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
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
    ("source_feasibility_file_hash_drift", "source_feasibility_evidence"),
    ("source_feasibility_payload_hash_drift", "source_feasibility_evidence"),
    ("aggregation_target_commitment_drift", "nested_verifier_contract"),
    ("input_block_receipt_commitment_drift", "nested_verifier_contract"),
    ("verifier_domain_drift", "nested_verifier_contract"),
    ("public_instance_commitment_drift", "nested_verifier_contract"),
    ("proof_native_parameter_commitment_drift", "nested_verifier_contract"),
    ("statement_commitment_drift", "nested_verifier_contract"),
    ("selected_slice_version_drift", "nested_verifier_contract"),
    ("selected_slice_source_hash_drift", "nested_verifier_contract"),
    ("selected_slice_removed", "nested_verifier_contract"),
    ("selected_slice_duplicated", "nested_verifier_contract"),
    ("selected_slice_reordered", "nested_verifier_contract"),
    ("minimum_slice_check_count_drift", "nested_verifier_contract"),
    ("nested_verifier_contract_commitment_drift", "nested_verifier_contract_commitment"),
    ("nested_verifier_claim_true_without_artifact", "backend_attempt"),
    ("pcd_accumulator_claim_true_without_artifact", "backend_attempt"),
    ("invented_outer_backend_artifact", "backend_attempt"),
    ("first_blocker_removed", "backend_attempt"),
    ("result_changed_to_go", "parser_or_schema"),
)


class D64NestedVerifierBackendContractError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D64NestedVerifierBackendContractError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


FEASIBILITY = _load_module(FEASIBILITY_SCRIPT, "zkai_d64_recursive_pcd_feasibility_for_nested_contract")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_hex_json(value: Any) -> str:
    return sha256_hex_bytes(canonical_json_bytes(value))


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


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
        raise D64NestedVerifierBackendContractError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D64NestedVerifierBackendContractError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D64NestedVerifierBackendContractError(f"{field} must be a list")
    return value


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D64NestedVerifierBackendContractError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D64NestedVerifierBackendContractError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D64NestedVerifierBackendContractError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D64NestedVerifierBackendContractError(f"source evidence is not a regular file: {path}")
    if ROOT.resolve() not in resolved.parents:
        raise D64NestedVerifierBackendContractError(f"source evidence path escapes repository: {path}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D64NestedVerifierBackendContractError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D64NestedVerifierBackendContractError(f"source evidence must be a JSON object: {path}")
    return payload


def load_checked_feasibility(path: pathlib.Path = FEASIBILITY_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        FEASIBILITY.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D64NestedVerifierBackendContractError(f"d64 recursive/PCD feasibility validation failed: {err}") from err
    if payload.get("aggregation_target_result") != FEASIBILITY.TARGET_RESULT:
        raise D64NestedVerifierBackendContractError("source feasibility does not expose an aggregation target")
    if payload.get("recursive_or_pcd_proof_result") != FEASIBILITY.RECURSIVE_OR_PCD_RESULT:
        raise D64NestedVerifierBackendContractError("source feasibility recursive/PCD result mismatch")
    if payload.get("case_count") != 16:
        raise D64NestedVerifierBackendContractError("source feasibility mutation case count mismatch")
    if payload.get("all_mutations_rejected") is not True:
        raise D64NestedVerifierBackendContractError("source feasibility did not reject all checked mutations")
    return payload


def source_evidence_descriptor(source: dict[str, Any], path: pathlib.Path = FEASIBILITY_EVIDENCE) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "aggregation_target_commitment": source["aggregation_target_commitment"],
    }


def selected_nested_verifier_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = require_object(source.get("aggregation_target_manifest"), "source aggregation target manifest")
    checks = require_list(manifest.get("required_nested_verifier_checks"), "source nested verifier checks")
    if len(checks) < MINIMUM_NESTED_SLICE_CHECKS:
        raise D64NestedVerifierBackendContractError("source aggregation target has too few nested verifier checks")
    selected = copy.deepcopy(checks[:MINIMUM_NESTED_SLICE_CHECKS])
    selected_ids = tuple(check.get("slice_id") for check in selected if isinstance(check, dict))
    if selected_ids != SELECTED_SLICE_IDS:
        raise D64NestedVerifierBackendContractError("selected nested verifier slice ids mismatch")
    for index, check in enumerate(selected):
        check = require_object(check, f"selected nested verifier check {index}")
        expect_equal(check.get("index"), index, f"selected nested verifier check {index} index")
        for field in ("slice_id", "schema", "proof_backend_version", "source_path", "source_file_sha256", "source_payload_sha256"):
            if not isinstance(check.get(field), str) or not check[field]:
                raise D64NestedVerifierBackendContractError(f"selected nested verifier check {index} missing {field}")
    return selected


def nested_verifier_contract(source: dict[str, Any]) -> dict[str, Any]:
    projection = require_object(source.get("block_receipt_projection"), "source block receipt projection")
    target = require_object(source.get("aggregation_target_manifest"), "source aggregation target manifest")
    summary = require_object(source.get("summary"), "source feasibility summary")
    return {
        "contract_version": CONTRACT_VERSION,
        "contract_kind": CONTRACT_KIND,
        "minimum_nested_slice_checks": MINIMUM_NESTED_SLICE_CHECKS,
        "selected_slice_ids": list(SELECTED_SLICE_IDS),
        "source_aggregation_target_commitment": source["aggregation_target_commitment"],
        "input_block_receipt_commitment": projection["block_receipt_commitment"],
        "verifier_domain": projection["verifier_domain"],
        "public_instance_commitment": projection["public_instance_commitment"],
        "proof_native_parameter_commitment": projection["proof_native_parameter_commitment"],
        "statement_commitment": projection["statement_commitment"],
        "input_activation_commitment": projection["input_activation_commitment"],
        "output_activation_commitment": projection["output_activation_commitment"],
        "slice_chain_commitment": target["slice_chain_commitment"],
        "evidence_manifest_commitment": target["evidence_manifest_commitment"],
        "model_config": copy.deepcopy(projection["model_config"]),
        "selected_nested_verifier_checks": selected_nested_verifier_checks(source),
        "source_aggregation_target": {
            "target_version": target["target_version"],
            "target_kind": target["target_kind"],
            "slice_count": summary["slice_count"],
            "total_checked_rows": summary["total_checked_rows"],
            "composition_mutation_cases": summary["composition_mutation_cases"],
            "feasibility_mutation_cases": source["case_count"],
            "feasibility_mutations_rejected": summary["mutations_rejected"],
            "recursive_or_pcd_status": source["recursive_or_pcd_proof_result"],
        },
    }


def backend_attempt() -> dict[str, Any]:
    return {
        "go_criterion": (
            "one checked outer proof or PCD accumulator verifies the selected d64 slice-verifier "
            "checks and binds nested_verifier_contract_commitment as public input"
        ),
        "minimum_nested_slice_checks": MINIMUM_NESTED_SLICE_CHECKS,
        "selected_slice_ids": list(SELECTED_SLICE_IDS),
        "nested_verifier_proof_claimed": False,
        "pcd_accumulator_claimed": False,
        "outer_backend_artifacts": [],
        "proof_or_accumulator_artifacts": [],
        "missing_artifacts": MISSING_ARTIFACTS,
        "first_blocker": FIRST_BLOCKER,
        "blocked_before_metrics": ["outer_proof_size", "outer_verifier_time", "recursive_verifier_rows", "onchain_cost"],
    }


def refresh_commitments(payload: dict[str, Any]) -> None:
    contract = require_object(payload.get("nested_verifier_contract"), "nested verifier contract")
    payload["nested_verifier_contract_commitment"] = blake2b_commitment(contract, CONTRACT_DOMAIN)


def _build_payload_from_canonical_source(source: dict[str, Any]) -> dict[str, Any]:
    source = copy.deepcopy(source)
    FEASIBILITY.validate_payload(source)
    contract = nested_verifier_contract(source)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "contract_result": CONTRACT_RESULT,
        "backend_proof_result": BACKEND_RESULT,
        "source_feasibility_evidence": source_evidence_descriptor(source),
        "nested_verifier_contract": contract,
        "nested_verifier_contract_commitment": None,
        "backend_attempt": backend_attempt(),
        "summary": {
            "contract_status": CONTRACT_RESULT,
            "backend_status": BACKEND_RESULT,
            "first_blocker": FIRST_BLOCKER,
            "minimum_nested_slice_checks": MINIMUM_NESTED_SLICE_CHECKS,
            "selected_slice_count": MINIMUM_NESTED_SLICE_CHECKS,
            "selected_slice_ids": list(SELECTED_SLICE_IDS),
            "source_aggregation_target_commitment": source["aggregation_target_commitment"],
            "nested_verifier_contract_commitment": None,
            "source_feasibility_mutation_cases": source["case_count"],
            "source_feasibility_mutations_rejected": source["summary"]["mutations_rejected"],
            "source_recursive_or_pcd_status": source["recursive_or_pcd_proof_result"],
        },
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    refresh_commitments(payload)
    payload["summary"]["nested_verifier_contract_commitment"] = payload["nested_verifier_contract_commitment"]
    _validate_draft_payload(payload)
    return payload


def build_payload() -> dict[str, Any]:
    return _build_payload_from_canonical_source(load_checked_feasibility())


def _validate_source_descriptor(payload: dict[str, Any]) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_feasibility_evidence"), "source feasibility evidence")
    path_value = descriptor.get("path")
    if not isinstance(path_value, str):
        raise D64NestedVerifierBackendContractError("source feasibility evidence path must be a string")
    expect_equal(path_value, relative_path(FEASIBILITY_EVIDENCE), "source feasibility evidence path")
    path = (ROOT / path_value).resolve()
    if path != FEASIBILITY_EVIDENCE.resolve():
        raise D64NestedVerifierBackendContractError("source feasibility evidence path mismatch")
    source = load_checked_feasibility(path)
    expect_equal(descriptor.get("file_sha256"), file_sha256(path), "source feasibility file_sha256")
    expect_equal(descriptor.get("payload_sha256"), sha256_hex_json(source), "source feasibility payload_sha256")
    expect_equal(descriptor.get("schema"), source["schema"], "source feasibility schema")
    expect_equal(descriptor.get("decision"), source["decision"], "source feasibility decision")
    expect_equal(
        descriptor.get("aggregation_target_commitment"),
        source["aggregation_target_commitment"],
        "source aggregation target commitment",
    )
    return source


def _validate_backend_attempt(payload: dict[str, Any]) -> None:
    attempt = require_object(payload.get("backend_attempt"), "backend attempt")
    if attempt.get("nested_verifier_proof_claimed") is not False:
        raise D64NestedVerifierBackendContractError("nested verifier proof claimed without a checked backend artifact")
    if attempt.get("pcd_accumulator_claimed") is not False:
        raise D64NestedVerifierBackendContractError("PCD accumulator claimed without a checked backend artifact")
    outer_artifacts = require_list(attempt.get("outer_backend_artifacts"), "outer backend artifacts")
    proof_artifacts = require_list(attempt.get("proof_or_accumulator_artifacts"), "proof or accumulator artifacts")
    if outer_artifacts or proof_artifacts:
        raise D64NestedVerifierBackendContractError("outer backend artifact supplied to no-go contract gate")
    expect_equal(attempt.get("missing_artifacts"), MISSING_ARTIFACTS, "missing backend artifacts")
    expect_equal(attempt.get("first_blocker"), FIRST_BLOCKER, "first backend blocker")
    expect_equal(attempt.get("go_criterion"), backend_attempt()["go_criterion"], "backend go criterion")
    expect_equal(
        attempt.get("minimum_nested_slice_checks"),
        MINIMUM_NESTED_SLICE_CHECKS,
        "backend minimum nested slice checks",
    )
    expect_equal(attempt.get("selected_slice_ids"), list(SELECTED_SLICE_IDS), "backend selected slice ids")
    expect_equal(attempt.get("blocked_before_metrics"), backend_attempt()["blocked_before_metrics"], "blocked-before metrics")


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_cases = "cases" in payload
    has_case_count = "case_count" in payload
    has_all_mutations_rejected = "all_mutations_rejected" in payload
    has_mutation_inventory = "mutation_inventory" in payload
    if not (has_cases or has_case_count or has_all_mutations_rejected or has_mutation_inventory):
        raise D64NestedVerifierBackendContractError(
            "mutation metadata must include mutation_inventory, cases, case_count, and all_mutations_rejected"
        )
    if not (has_mutation_inventory and has_cases and has_case_count and has_all_mutations_rejected):
        raise D64NestedVerifierBackendContractError(
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
                raise D64NestedVerifierBackendContractError(f"mutation case {index} missing {column}")
        if not isinstance(case["mutation"], str) or not case["mutation"]:
            raise D64NestedVerifierBackendContractError(f"mutation case {index} mutation must be a non-empty string")
        if not isinstance(case["surface"], str) or not case["surface"]:
            raise D64NestedVerifierBackendContractError(f"mutation case {index} surface must be a non-empty string")
        pair = (case["mutation"], case["surface"])
        if pair in seen_pairs:
            raise D64NestedVerifierBackendContractError(f"duplicate mutation case {index}")
        seen_pairs.add(pair)
        case_pairs.append(pair)
        if case["baseline_result"] != RESULT:
            raise D64NestedVerifierBackendContractError(f"mutation case {index} baseline_result mismatch")
        if not isinstance(case["mutated_accepted"], bool):
            raise D64NestedVerifierBackendContractError(f"mutation case {index} mutated_accepted must be boolean")
        if not isinstance(case["rejected"], bool):
            raise D64NestedVerifierBackendContractError(f"mutation case {index} rejected must be boolean")
        if case["rejected"] == case["mutated_accepted"]:
            raise D64NestedVerifierBackendContractError(f"mutation case {index} rejected/accepted fields are inconsistent")
        if not isinstance(case["rejection_layer"], str) or not case["rejection_layer"]:
            raise D64NestedVerifierBackendContractError(f"mutation case {index} rejection_layer must be a non-empty string")
        if not isinstance(case["error"], str):
            raise D64NestedVerifierBackendContractError(f"mutation case {index} error must be a string")
        if case["rejected"]:
            computed_rejected += 1

    computed_case_count = len(cases)
    expect_equal(tuple(case_pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), computed_case_count, "mutation case_count")
    expect_equal(
        payload.get("all_mutations_rejected"),
        all(case["rejected"] for case in cases),
        "all_mutations_rejected",
    )
    return computed_case_count, computed_rejected


def _validate_common_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "nested-verifier backend contract payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("contract_result"), CONTRACT_RESULT, "contract result")
    expect_equal(payload.get("backend_proof_result"), BACKEND_RESULT, "backend proof result")
    source = _validate_source_descriptor(payload)
    expected_contract = nested_verifier_contract(source)
    expect_equal(payload.get("nested_verifier_contract"), expected_contract, "nested verifier contract")
    expected_commitment = blake2b_commitment(expected_contract, CONTRACT_DOMAIN)
    expect_equal(
        require_commitment(payload.get("nested_verifier_contract_commitment"), "nested verifier contract commitment"),
        expected_commitment,
        "nested verifier contract commitment",
    )
    _validate_backend_attempt(payload)
    expected_summary = {
        "contract_status": CONTRACT_RESULT,
        "backend_status": BACKEND_RESULT,
        "first_blocker": FIRST_BLOCKER,
        "minimum_nested_slice_checks": MINIMUM_NESTED_SLICE_CHECKS,
        "selected_slice_count": MINIMUM_NESTED_SLICE_CHECKS,
        "selected_slice_ids": list(SELECTED_SLICE_IDS),
        "source_aggregation_target_commitment": source["aggregation_target_commitment"],
        "nested_verifier_contract_commitment": expected_commitment,
        "source_feasibility_mutation_cases": source["case_count"],
        "source_feasibility_mutations_rejected": source["summary"]["mutations_rejected"],
        "source_recursive_or_pcd_status": source["recursive_or_pcd_proof_result"],
    }
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    return source, expected_summary


def _validate_draft_payload(payload: Any) -> None:
    _, expected_summary = _validate_common_payload(payload)
    if (
        "mutation_inventory" in payload
        or "cases" in payload
        or "case_count" in payload
        or "all_mutations_rejected" in payload
    ):
        raise D64NestedVerifierBackendContractError("draft payload must not include mutation metadata")
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "nested-verifier backend contract payload")
    _, expected_summary = _validate_common_payload(payload)
    computed_case_count, computed_rejected = _validate_case_metadata(payload)
    if computed_rejected != computed_case_count:
        raise D64NestedVerifierBackendContractError("not all nested-verifier contract mutations rejected")
    expected_summary["mutation_cases"] = computed_case_count
    expected_summary["mutations_rejected"] = computed_rejected
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "source feasibility" in text or "source evidence" in text or "file_sha" in text or "payload_sha" in text:
        return "source_feasibility_evidence"
    if "nested verifier contract commitment" in text:
        return "nested_verifier_contract_commitment"
    if "nested verifier contract" in text or "selected nested" in text:
        return "nested_verifier_contract"
    if "backend" in text or "pcd" in text or "artifact" in text or "blocker" in text:
        return "backend_attempt"
    if "summary" in text:
        return "summary"
    return "parser_or_schema"


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None], refresh: bool = True) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        if refresh:
            refresh_commitments(mutated)
            if "summary" in mutated:
                mutated["summary"]["nested_verifier_contract_commitment"] = mutated.get(
                    "nested_verifier_contract_commitment"
                )
        cases.append((name, surface, mutated))

    add(
        "source_feasibility_file_hash_drift",
        "source_feasibility_evidence",
        lambda p: p["source_feasibility_evidence"].__setitem__("file_sha256", "11" * 32),
    )
    add(
        "source_feasibility_payload_hash_drift",
        "source_feasibility_evidence",
        lambda p: p["source_feasibility_evidence"].__setitem__("payload_sha256", "22" * 32),
    )
    add(
        "aggregation_target_commitment_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("source_aggregation_target_commitment", "blake2b-256:" + "33" * 32),
    )
    add(
        "input_block_receipt_commitment_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("input_block_receipt_commitment", "blake2b-256:" + "44" * 32),
    )
    add(
        "verifier_domain_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("verifier_domain", "ptvm:zkai:d64-nested-verifier:tampered:v0"),
    )
    add(
        "public_instance_commitment_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("public_instance_commitment", "blake2b-256:" + "55" * 32),
    )
    add(
        "proof_native_parameter_commitment_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("proof_native_parameter_commitment", "blake2b-256:" + "66" * 32),
    )
    add(
        "statement_commitment_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("statement_commitment", "blake2b-256:" + "77" * 32),
    )
    add(
        "selected_slice_version_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"]["selected_nested_verifier_checks"][0].__setitem__(
            "proof_backend_version", "stwo-d64-rmsnorm-public-row-air-proof-v999"
        ),
    )
    add(
        "selected_slice_source_hash_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"]["selected_nested_verifier_checks"][1].__setitem__(
            "source_payload_sha256", "88" * 32
        ),
    )
    add(
        "selected_slice_removed",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"]["selected_nested_verifier_checks"].pop(),
    )
    add(
        "selected_slice_duplicated",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"]["selected_nested_verifier_checks"].append(
            copy.deepcopy(p["nested_verifier_contract"]["selected_nested_verifier_checks"][0])
        ),
    )
    add(
        "selected_slice_reordered",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"]["selected_nested_verifier_checks"].reverse(),
    )
    add(
        "minimum_slice_check_count_drift",
        "nested_verifier_contract",
        lambda p: p["nested_verifier_contract"].__setitem__("minimum_nested_slice_checks", 1),
    )
    add(
        "nested_verifier_contract_commitment_drift",
        "nested_verifier_contract_commitment",
        lambda p: p.__setitem__("nested_verifier_contract_commitment", "blake2b-256:" + "99" * 32),
        refresh=False,
    )
    add(
        "nested_verifier_claim_true_without_artifact",
        "backend_attempt",
        lambda p: p["backend_attempt"].__setitem__("nested_verifier_proof_claimed", True),
    )
    add(
        "pcd_accumulator_claim_true_without_artifact",
        "backend_attempt",
        lambda p: p["backend_attempt"].__setitem__("pcd_accumulator_claimed", True),
    )
    add(
        "invented_outer_backend_artifact",
        "backend_attempt",
        lambda p: p["backend_attempt"]["outer_backend_artifacts"].append(
            {"path": "docs/engineering/evidence/nonexistent-nested-verifier-proof.json", "commitment": "blake2b-256:" + "aa" * 32}
        ),
    )
    add(
        "first_blocker_removed",
        "backend_attempt",
        lambda p: p["backend_attempt"].__setitem__("first_blocker", ""),
    )
    add(
        "result_changed_to_go",
        "parser_or_schema",
        lambda p: p.__setitem__("result", "GO"),
    )
    return cases


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    _validate_draft_payload(baseline)
    cases = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            _validate_draft_payload(mutated)
            accepted = True
            error = ""
            layer = "accepted"
        except D64NestedVerifierBackendContractError as err:
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
        raise D64NestedVerifierBackendContractError("not all nested-verifier contract mutations rejected")
    return result


def to_tsv(payload: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: case[key] for key in TSV_COLUMNS} for case in payload["cases"])
    return buffer.getvalue()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if tsv_path is not None:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        tsv_path.write_text(to_tsv(payload), encoding="utf-8")


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
