#!/usr/bin/env python3
"""Classify the d64 block receipt as a recursive/PCD aggregation target.

This gate intentionally does not synthesize a recursive proof. It checks whether
the existing d64 block receipt is complete enough to be the input object for a
future recursive or proof-carrying-data layer, then records the first blocker
for claiming such a layer today.
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
COMPOSITION_SCRIPT = ROOT / "scripts" / "zkai_d64_block_receipt_composition_gate.py"
BLOCK_RECEIPT_EVIDENCE = EVIDENCE_DIR / "zkai-d64-block-receipt-composition-gate-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.tsv"

SCHEMA = "zkai-d64-recursive-pcd-aggregation-feasibility-v1"
DECISION = "NO_GO_D64_RECURSIVE_PCD_AGGREGATION_PROVER_UNAVAILABLE"
RESULT = "BOUNDED_NO_GO"
TARGET_RESULT = "GO_D64_BLOCK_RECEIPT_AGGREGATION_TARGET"
RECURSIVE_OR_PCD_RESULT = "NO_GO_RECURSIVE_OR_PCD_PROOF_ARTIFACT_UNAVAILABLE"
TARGET_VERSION = "zkai-d64-recursive-pcd-aggregation-target-v1"
TARGET_KIND = "d64-block-receipt-recursive-pcd-target"
TARGET_DOMAIN = "ptvm:zkai:d64-recursive-pcd:aggregation-target:v1"

FIRST_BLOCKER = (
    "missing recursive verifier or PCD backend artifact that proves the six d64 "
    "slice verifier checks inside one verifier-facing proof or accumulator"
)

MISSING_ARTIFACTS = [
    "recursive verifier program/AIR/circuit for each d64 slice verifier",
    "adapter that binds the d64 aggregation target commitment into recursive public inputs",
    "recursive or PCD proof object over the nested slice-verifier checks",
    "verifier handle for the resulting recursive or PCD proof object",
]

NON_CLAIMS = [
    "not recursive aggregation of the six d64 slice proofs",
    "not proof-carrying-data accumulation",
    "not one compressed verifier object",
    "not a verifier-time benchmark",
    "not onchain deployment evidence",
    "not private parameter-opening proof",
    "not full transformer inference",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_recursive_pcd_aggregation_feasibility_gate.py --write-json docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_recursive_pcd_aggregation_feasibility_gate",
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
    ("aggregation_target_commitment_drift", "aggregation_target_commitment"),
    ("source_block_receipt_file_hash_drift", "source_block_receipt_evidence"),
    ("source_block_receipt_payload_hash_drift", "source_block_receipt_evidence"),
    ("block_receipt_commitment_drift", "block_receipt_projection"),
    ("proof_native_parameter_commitment_removed", "block_receipt_projection"),
    ("public_instance_commitment_drift", "block_receipt_projection"),
    ("statement_commitment_drift", "block_receipt_projection"),
    ("verifier_domain_drift", "block_receipt_projection"),
    ("target_manifest_slice_version_drift", "aggregation_target_manifest"),
    ("target_manifest_source_hash_drift", "aggregation_target_manifest"),
    ("composition_mutation_count_drift", "aggregation_target_manifest"),
    ("recursive_claim_true_without_proof", "recursive_or_pcd_attempt"),
    ("pcd_claim_true_without_proof", "recursive_or_pcd_attempt"),
    ("invented_recursive_proof_artifact", "recursive_or_pcd_attempt"),
    ("first_blocker_removed", "recursive_or_pcd_attempt"),
    ("result_changed_to_go", "parser_or_schema"),
)


class D64RecursivePCDFeasibilityError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D64RecursivePCDFeasibilityError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


COMPOSITION = _load_module(COMPOSITION_SCRIPT, "zkai_d64_block_receipt_composition_for_recursive_pcd")


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
        raise D64RecursivePCDFeasibilityError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D64RecursivePCDFeasibilityError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D64RecursivePCDFeasibilityError(f"{field} must be a list")
    return value


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D64RecursivePCDFeasibilityError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D64RecursivePCDFeasibilityError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D64RecursivePCDFeasibilityError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D64RecursivePCDFeasibilityError(f"source evidence is not a regular file: {path}")
    if ROOT.resolve() not in resolved.parents:
        raise D64RecursivePCDFeasibilityError(f"source evidence path escapes repository: {path}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D64RecursivePCDFeasibilityError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D64RecursivePCDFeasibilityError(f"source evidence must be a JSON object: {path}")
    return payload


def load_checked_block_receipt(path: pathlib.Path = BLOCK_RECEIPT_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        COMPOSITION.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D64RecursivePCDFeasibilityError(f"d64 block receipt validation failed: {err}") from err
    if payload.get("case_count") != 14:
        raise D64RecursivePCDFeasibilityError("d64 block receipt mutation case count mismatch")
    if payload.get("all_mutations_rejected") is not True:
        raise D64RecursivePCDFeasibilityError("d64 block receipt did not reject all checked mutations")
    summary = require_object(payload.get("summary"), "d64 block receipt summary")
    expect_equal(summary.get("mutations_rejected"), 14, "d64 block receipt rejected mutation count")
    return payload


def source_evidence_descriptor(source: dict[str, Any], path: pathlib.Path = BLOCK_RECEIPT_EVIDENCE) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "block_receipt_commitment": receipt["block_receipt_commitment"],
    }


def block_receipt_projection(source: dict[str, Any]) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    fields = [
        "receipt_version",
        "statement_kind",
        "target_id",
        "model_config",
        "input_activation_commitment",
        "output_activation_commitment",
        "proof_native_parameter_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "required_backend_version",
        "verifier_domain",
        "slice_versions",
        "slice_chain_commitment",
        "evidence_manifest_commitment",
        "block_receipt_commitment",
    ]
    return {field: copy.deepcopy(receipt[field]) for field in fields}


def _manifest_by_slice(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = require_list(source.get("source_evidence_manifest"), "source block evidence manifest")
    by_slice: dict[str, dict[str, Any]] = {}
    for item in manifest:
        item = require_object(item, "source block evidence manifest item")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D64RecursivePCDFeasibilityError("source manifest slice_id must be a string")
        if slice_id in by_slice:
            raise D64RecursivePCDFeasibilityError("duplicate source manifest slice_id")
        by_slice[slice_id] = item
    return by_slice


def required_nested_verifier_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    slice_versions = require_list(receipt.get("slice_versions"), "source block receipt slice_versions")
    manifest_by_slice = _manifest_by_slice(source)
    checks = []
    for index, version in enumerate(slice_versions):
        version = require_object(version, "source block receipt slice version")
        slice_id = version.get("slice_id")
        if not isinstance(slice_id, str):
            raise D64RecursivePCDFeasibilityError("slice version slice_id must be a string")
        manifest = manifest_by_slice.get(slice_id)
        if manifest is None:
            raise D64RecursivePCDFeasibilityError(f"missing source manifest for slice {slice_id}")
        checks.append(
            {
                "index": index,
                "slice_id": slice_id,
                "schema": version.get("schema"),
                "proof_backend_version": version.get("proof_backend_version"),
                "source_path": manifest.get("path"),
                "source_file_sha256": manifest.get("file_sha256"),
                "source_payload_sha256": manifest.get("payload_sha256"),
            }
        )
    return checks


def aggregation_target_manifest(source: dict[str, Any]) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    summary = require_object(source.get("summary"), "source block receipt summary")
    return {
        "target_version": TARGET_VERSION,
        "target_kind": TARGET_KIND,
        "input_block_receipt_commitment": receipt["block_receipt_commitment"],
        "slice_chain_commitment": source["slice_chain_commitment"],
        "evidence_manifest_commitment": source["evidence_manifest_commitment"],
        "statement_commitment": receipt["statement_commitment"],
        "public_instance_commitment": receipt["public_instance_commitment"],
        "proof_native_parameter_commitment": receipt["proof_native_parameter_commitment"],
        "input_activation_commitment": receipt["input_activation_commitment"],
        "output_activation_commitment": receipt["output_activation_commitment"],
        "verifier_domain": receipt["verifier_domain"],
        "model_config": copy.deepcopy(receipt["model_config"]),
        "required_nested_verifier_checks": required_nested_verifier_checks(source),
        "composition_evidence": {
            "schema": source["schema"],
            "decision": source["decision"],
            "case_count": source["case_count"],
            "mutations_rejected": summary["mutations_rejected"],
            "all_mutations_rejected": source["all_mutations_rejected"],
        },
    }


def recursive_or_pcd_attempt() -> dict[str, Any]:
    return {
        "go_criterion": (
            "one recursive/PCD proof object verifies at least two d64 slice-verifier "
            "checks and binds the aggregation_target_commitment as public input"
        ),
        "recursive_aggregation_claimed": False,
        "pcd_accumulator_claimed": False,
        "recursive_proof_artifacts": [],
        "missing_artifacts": MISSING_ARTIFACTS,
        "first_blocker": FIRST_BLOCKER,
        "blocked_before_metrics": ["proof_size", "recursive_verifier_time", "onchain_cost"],
    }


def refresh_commitments(payload: dict[str, Any]) -> None:
    manifest = require_object(payload.get("aggregation_target_manifest"), "aggregation target manifest")
    payload["aggregation_target_commitment"] = blake2b_commitment(manifest, TARGET_DOMAIN)


def _build_payload_from_canonical_source(source: dict[str, Any]) -> dict[str, Any]:
    """Build the draft payload from the already-loaded canonical receipt evidence."""
    source = copy.deepcopy(source)
    COMPOSITION.validate_payload(source)
    projection = block_receipt_projection(source)
    target = aggregation_target_manifest(source)
    summary = require_object(source.get("summary"), "source block receipt summary")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "aggregation_target_result": TARGET_RESULT,
        "recursive_or_pcd_proof_result": RECURSIVE_OR_PCD_RESULT,
        "source_block_receipt_evidence": source_evidence_descriptor(source),
        "block_receipt_projection": projection,
        "aggregation_target_manifest": target,
        "aggregation_target_commitment": None,
        "recursive_or_pcd_attempt": recursive_or_pcd_attempt(),
        "summary": {
            "target_status": TARGET_RESULT,
            "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
            "first_blocker": FIRST_BLOCKER,
            "slice_count": summary["slice_count"],
            "total_checked_rows": summary["total_checked_rows"],
            "composition_mutation_cases": source["case_count"],
            "composition_mutations_rejected": summary["mutations_rejected"],
            "block_receipt_commitment": projection["block_receipt_commitment"],
            "aggregation_target_kind": TARGET_KIND,
            "aggregation_target_version": TARGET_VERSION,
        },
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    refresh_commitments(payload)
    _validate_draft_payload(payload)
    return payload


def build_payload() -> dict[str, Any]:
    return _build_payload_from_canonical_source(load_checked_block_receipt())


def _validate_source_descriptor(payload: dict[str, Any]) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_block_receipt_evidence"), "source block receipt evidence")
    path_value = descriptor.get("path")
    if not isinstance(path_value, str):
        raise D64RecursivePCDFeasibilityError("source block receipt evidence path must be a string")
    path = (ROOT / path_value).resolve()
    if path != BLOCK_RECEIPT_EVIDENCE.resolve():
        raise D64RecursivePCDFeasibilityError("source block receipt evidence path mismatch")
    source = load_checked_block_receipt(path)
    expect_equal(descriptor.get("file_sha256"), file_sha256(path), "source block receipt file_sha256")
    expect_equal(descriptor.get("payload_sha256"), sha256_hex_json(source), "source block receipt payload_sha256")
    expect_equal(descriptor.get("schema"), source["schema"], "source block receipt schema")
    expect_equal(descriptor.get("decision"), source["decision"], "source block receipt decision")
    expect_equal(
        descriptor.get("block_receipt_commitment"),
        source["block_receipt"]["block_receipt_commitment"],
        "source block receipt commitment",
    )
    return source


def _validate_attempt(payload: dict[str, Any]) -> None:
    attempt = require_object(payload.get("recursive_or_pcd_attempt"), "recursive or PCD attempt")
    if attempt.get("recursive_aggregation_claimed") is not False:
        raise D64RecursivePCDFeasibilityError("recursive aggregation claimed without a checked recursive proof artifact")
    if attempt.get("pcd_accumulator_claimed") is not False:
        raise D64RecursivePCDFeasibilityError("PCD accumulator claimed without a checked PCD proof artifact")
    artifacts = require_list(attempt.get("recursive_proof_artifacts"), "recursive proof artifacts")
    if artifacts:
        raise D64RecursivePCDFeasibilityError("recursive proof artifact supplied to no-go feasibility gate")
    expect_equal(attempt.get("missing_artifacts"), MISSING_ARTIFACTS, "missing recursive artifacts")
    expect_equal(attempt.get("first_blocker"), FIRST_BLOCKER, "first recursive blocker")
    expect_equal(
        attempt.get("go_criterion"),
        recursive_or_pcd_attempt()["go_criterion"],
        "recursive or PCD go criterion",
    )
    expect_equal(
        attempt.get("blocked_before_metrics"),
        recursive_or_pcd_attempt()["blocked_before_metrics"],
        "blocked-before metrics",
    )


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_cases = "cases" in payload
    has_case_count = "case_count" in payload
    has_all_mutations_rejected = "all_mutations_rejected" in payload
    has_mutation_inventory = "mutation_inventory" in payload
    if not (has_cases or has_case_count or has_all_mutations_rejected or has_mutation_inventory):
        raise D64RecursivePCDFeasibilityError(
            "mutation metadata must include mutation_inventory, cases, case_count, and all_mutations_rejected"
        )
    if not (has_mutation_inventory and has_cases and has_case_count and has_all_mutations_rejected):
        raise D64RecursivePCDFeasibilityError(
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
                raise D64RecursivePCDFeasibilityError(f"mutation case {index} missing {column}")
        if not isinstance(case["mutation"], str) or not case["mutation"]:
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} mutation must be a non-empty string")
        if not isinstance(case["surface"], str) or not case["surface"]:
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} surface must be a non-empty string")
        pair = (case["mutation"], case["surface"])
        if pair in seen_pairs:
            raise D64RecursivePCDFeasibilityError(f"duplicate mutation case {index}")
        seen_pairs.add(pair)
        case_pairs.append(pair)
        if case["baseline_result"] != RESULT:
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} baseline_result mismatch")
        if not isinstance(case["mutated_accepted"], bool):
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} mutated_accepted must be boolean")
        if not isinstance(case["rejected"], bool):
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} rejected must be boolean")
        if case["rejected"] == case["mutated_accepted"]:
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} rejected/accepted fields are inconsistent")
        if not isinstance(case["rejection_layer"], str) or not case["rejection_layer"]:
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} rejection_layer must be a non-empty string")
        if not isinstance(case["error"], str):
            raise D64RecursivePCDFeasibilityError(f"mutation case {index} error must be a string")
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
    payload = require_object(payload, "recursive/PCD feasibility payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("aggregation_target_result"), TARGET_RESULT, "aggregation target result")
    expect_equal(payload.get("recursive_or_pcd_proof_result"), RECURSIVE_OR_PCD_RESULT, "recursive or PCD proof result")
    source = _validate_source_descriptor(payload)
    expect_equal(
        payload.get("block_receipt_projection"),
        block_receipt_projection(source),
        "block receipt projection",
    )
    target = aggregation_target_manifest(source)
    expect_equal(payload.get("aggregation_target_manifest"), target, "aggregation target manifest")
    expect_equal(
        require_commitment(payload.get("aggregation_target_commitment"), "aggregation target commitment"),
        blake2b_commitment(target, TARGET_DOMAIN),
        "aggregation target commitment",
    )
    _validate_attempt(payload)
    source_summary = require_object(source.get("summary"), "source block receipt summary")
    expected_summary = {
        "target_status": TARGET_RESULT,
        "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
        "first_blocker": FIRST_BLOCKER,
        "slice_count": source_summary["slice_count"],
        "total_checked_rows": source_summary["total_checked_rows"],
        "composition_mutation_cases": source["case_count"],
        "composition_mutations_rejected": source_summary["mutations_rejected"],
        "block_receipt_commitment": source["block_receipt"]["block_receipt_commitment"],
        "aggregation_target_kind": TARGET_KIND,
        "aggregation_target_version": TARGET_VERSION,
    }
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    return source, expected_summary


def _validate_draft_payload(payload: Any) -> None:
    _, expected_summary = _validate_common_payload(payload)
    if (
        "mutation_inventory" in payload
        or "cases" in payload
        or "case_count" in payload
        or "all_mutations_rejected" in payload
    ):
        raise D64RecursivePCDFeasibilityError("draft payload must not include mutation metadata")
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def validate_payload(payload: Any) -> None:
    _, expected_summary = _validate_common_payload(payload)
    computed_case_count, computed_rejected = _validate_case_metadata(require_object(payload, "recursive/PCD feasibility payload"))
    expected_summary["mutation_cases"] = computed_case_count
    expected_summary["mutations_rejected"] = computed_rejected
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "source block receipt" in text or "file_sha" in text or "payload_sha" in text:
        return "source_block_receipt_evidence"
    if "projection" in text:
        return "block_receipt_projection"
    if "aggregation target commitment" in text:
        return "aggregation_target_commitment"
    if "aggregation target" in text:
        return "aggregation_target_manifest"
    if "recursive" in text or "pcd" in text or "artifact" in text or "blocker" in text:
        return "recursive_or_pcd_attempt"
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
        cases.append((name, surface, mutated))

    add(
        "aggregation_target_commitment_drift",
        "aggregation_target_commitment",
        lambda p: p.__setitem__("aggregation_target_commitment", "blake2b-256:" + "00" * 32),
        refresh=False,
    )
    add(
        "source_block_receipt_file_hash_drift",
        "source_block_receipt_evidence",
        lambda p: p["source_block_receipt_evidence"].__setitem__("file_sha256", "11" * 32),
    )
    add(
        "source_block_receipt_payload_hash_drift",
        "source_block_receipt_evidence",
        lambda p: p["source_block_receipt_evidence"].__setitem__("payload_sha256", "22" * 32),
    )
    add(
        "block_receipt_commitment_drift",
        "block_receipt_projection",
        lambda p: p["block_receipt_projection"].__setitem__("block_receipt_commitment", "blake2b-256:" + "33" * 32),
    )
    add(
        "proof_native_parameter_commitment_removed",
        "block_receipt_projection",
        lambda p: p["block_receipt_projection"].pop("proof_native_parameter_commitment"),
    )
    add(
        "public_instance_commitment_drift",
        "block_receipt_projection",
        lambda p: p["block_receipt_projection"].__setitem__("public_instance_commitment", "blake2b-256:" + "44" * 32),
    )
    add(
        "statement_commitment_drift",
        "block_receipt_projection",
        lambda p: p["block_receipt_projection"].__setitem__("statement_commitment", "blake2b-256:" + "55" * 32),
    )
    add(
        "verifier_domain_drift",
        "block_receipt_projection",
        lambda p: p["block_receipt_projection"].__setitem__("verifier_domain", "ptvm:tampered-recursive-domain:v0"),
    )
    add(
        "target_manifest_slice_version_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["required_nested_verifier_checks"][0].__setitem__(
            "proof_backend_version",
            "stwo-d64-rmsnorm-public-row-air-proof-v3",
        ),
    )
    add(
        "target_manifest_source_hash_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["required_nested_verifier_checks"][0].__setitem__(
            "source_payload_sha256",
            "66" * 32,
        ),
    )
    add(
        "composition_mutation_count_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["composition_evidence"].__setitem__("mutations_rejected", 13),
    )
    add(
        "recursive_claim_true_without_proof",
        "recursive_or_pcd_attempt",
        lambda p: p["recursive_or_pcd_attempt"].__setitem__("recursive_aggregation_claimed", True),
    )
    add(
        "pcd_claim_true_without_proof",
        "recursive_or_pcd_attempt",
        lambda p: p["recursive_or_pcd_attempt"].__setitem__("pcd_accumulator_claimed", True),
    )
    add(
        "invented_recursive_proof_artifact",
        "recursive_or_pcd_attempt",
        lambda p: p["recursive_or_pcd_attempt"]["recursive_proof_artifacts"].append(
            {"path": "docs/engineering/evidence/nonexistent-recursive-proof.json", "commitment": "blake2b-256:" + "77" * 32}
        ),
    )
    add(
        "first_blocker_removed",
        "recursive_or_pcd_attempt",
        lambda p: p["recursive_or_pcd_attempt"].__setitem__("first_blocker", ""),
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
        except D64RecursivePCDFeasibilityError as err:
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
        raise D64RecursivePCDFeasibilityError("not all recursive/PCD feasibility mutations rejected")
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
