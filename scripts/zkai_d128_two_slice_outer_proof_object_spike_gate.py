#!/usr/bin/env python3
"""Classify the smallest d128 two-slice outer proof-object target.

This is the narrow follow-up to the full d128 aggregation feasibility gate. It
does not try to aggregate all six d128 slices. It projects the first two checked
slice-verifier inputs into a smaller target and then asks whether the repository
contains a real outer proof, accumulator, or verifier-facing object for that
target. The result is GO only if that object exists and binds the target
commitment as a public input. Otherwise the gate records a bounded NO-GO.
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
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
AGGREGATION_SCRIPT = ROOT / "scripts" / "zkai_d128_aggregated_proof_object_feasibility_gate.py"
AGGREGATION_EVIDENCE = EVIDENCE_DIR / "zkai-d128-aggregated-proof-object-feasibility-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-two-slice-outer-proof-object-spike-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-two-slice-outer-proof-object-spike-2026-05.tsv"

SCHEMA = "zkai-d128-two-slice-outer-proof-object-spike-v1"
DECISION = "NO_GO_D128_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING"
RESULT = "BOUNDED_NO_GO"
TARGET_RESULT = "GO_D128_TWO_SLICE_OUTER_PROOF_TARGET"
OUTER_PROOF_RESULT = "NO_GO_EXECUTABLE_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING"
ISSUE = 408
WIDTH = 128
FF_DIM = 512
TARGET_VERSION = "zkai-d128-two-slice-outer-proof-target-v1"
TARGET_KIND = "d128-two-slice-outer-proof-target"
TARGET_DOMAIN = "ptvm:zkai:d128-two-slice-outer-proof:target:v1"
SELECTED_SLICE_CHAIN_DOMAIN = "ptvm:zkai:d128-two-slice-outer-proof:selected-slices:v1"
SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")
EXPECTED_SELECTED_ROWS = 256

GO_CRITERION = (
    "one outer proof, accumulator, or proof-carrying artifact verifies the two selected "
    "d128 slice-verifier checks and binds two_slice_target_commitment as a public input"
)
FIRST_BLOCKER = (
    "no executable outer proof/accumulator backend artifact in the current repository can "
    "prove the selected two d128 slice-verifier checks and bind two_slice_target_commitment "
    "as a public input"
)

MISSING_BACKEND_FEATURES = [
    "nested verifier program/AIR/circuit for d128 rmsnorm_public_rows",
    "nested verifier program/AIR/circuit for d128 rmsnorm_projection_bridge",
    "outer proof or PCD accumulator object over the selected d128 verifier checks",
    "outer verifier handle for that proof or accumulator object",
    "public-input binding inside the outer backend for two_slice_target_commitment",
    "mutation tests against relabeling of the selected outer proof public inputs",
]

PIVOT_OPTIONS = [
    {
        "track": "proof_native_two_slice_compression",
        "description": "compress the two-slice target into a proof-native object without claiming recursion",
        "claim_boundary": "compression or receipt integrity only, not recursive verification",
    },
    {
        "track": "external_recursion_capable_adapter",
        "description": "try the same two-slice statement envelope against an external recursion-capable backend",
        "claim_boundary": "external adapter result until Stwo-native recursion exists",
    },
    {
        "track": "simpler_non_recursive_accumulator",
        "description": "build a verifier-facing accumulator over the two selected checks before proving the verifier",
        "claim_boundary": "accumulator integrity only unless backed by an outer proof",
    },
]

NON_CLAIMS = [
    "not a recursive proof object",
    "not a PCD accumulator",
    "not aggregation of all six d128 slice proofs",
    "not d128 full-block proof-size evidence",
    "not d128 full-block verifier-time evidence",
    "not d128 full-block proof-generation-time evidence",
    "not matched NANOZK, DeepProve, EZKL, or snarkjs comparison evidence",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_two_slice_outer_proof_object_spike_gate.py --write-json docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_two_slice_outer_proof_object_spike_gate",
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
    ("source_feasibility_path_drift", "source_aggregation_evidence"),
    ("source_feasibility_file_hash_drift", "source_aggregation_evidence"),
    ("source_feasibility_payload_hash_drift", "source_aggregation_evidence"),
    ("source_feasibility_result_drift", "source_aggregation_evidence"),
    ("source_aggregation_target_commitment_drift", "two_slice_target"),
    ("block_receipt_commitment_drift", "two_slice_target"),
    ("statement_commitment_drift", "two_slice_target"),
    ("selected_slice_chain_commitment_drift", "two_slice_target"),
    ("two_slice_target_commitment_drift", "two_slice_target_commitment"),
    ("selected_slice_removed", "two_slice_target"),
    ("selected_slice_duplicated", "two_slice_target"),
    ("selected_slice_reordered", "two_slice_target"),
    ("selected_slice_source_file_hash_drift", "two_slice_target"),
    ("selected_slice_source_payload_hash_drift", "two_slice_target"),
    ("selected_slice_statement_commitment_drift", "two_slice_target"),
    ("selected_slice_public_instance_commitment_drift", "two_slice_target"),
    ("selected_slice_proof_parameter_commitment_drift", "two_slice_target"),
    ("selected_slice_row_count_drift", "two_slice_target"),
    ("selected_checked_rows_drift", "two_slice_target"),
    ("candidate_inventory_acceptance_relabel", "candidate_inventory"),
    ("candidate_inventory_file_sha256_tampered", "candidate_inventory"),
    ("candidate_inventory_required_artifact_removed", "candidate_inventory"),
    ("outer_proof_claimed_without_artifact", "proof_object_attempt"),
    ("pcd_claimed_without_artifact", "proof_object_attempt"),
    ("verifier_handle_claimed_without_artifact", "proof_object_attempt"),
    ("target_public_input_claimed_without_proof", "proof_object_attempt"),
    ("selected_statements_claimed_without_proof", "proof_object_attempt"),
    ("selected_source_hashes_claimed_without_proof", "proof_object_attempt"),
    ("proof_size_metric_smuggled_before_proof", "proof_object_attempt"),
    ("verifier_time_metric_smuggled_before_proof", "proof_object_attempt"),
    ("proof_generation_time_metric_smuggled_before_proof", "proof_object_attempt"),
    ("blocked_before_metrics_disabled", "proof_object_attempt"),
    ("first_blocker_removed", "proof_object_attempt"),
    ("missing_backend_feature_removed", "proof_object_attempt"),
    ("outer_proof_result_changed_to_go", "parser_or_schema"),
    ("decision_changed_to_go", "parser_or_schema"),
    ("result_changed_to_go", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
)

CANDIDATE_SPECS = (
    {
        "name": "d128_full_aggregation_target_gate",
        "kind": "checked_full_target_evidence",
        "path": "docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.json",
        "expected_exists": True,
        "classification": "FULL_TARGET_ONLY_NOT_TWO_SLICE_OUTER_PROOF",
        "required_for_go": False,
        "reason": "defines the full d128 aggregation target and the selected slice checks, but is not an outer proof object",
    },
    {
        "name": "d64_two_slice_nested_verifier_spike",
        "kind": "smaller_width_reference",
        "path": "docs/engineering/evidence/zkai-d64-nested-verifier-backend-spike-2026-05.json",
        "expected_exists": True,
        "classification": "REFERENCE_ONLY_NOT_D128",
        "required_for_go": False,
        "reason": "d64 two-slice no-go evidence is useful prior art but cannot be relabeled as d128 proof evidence",
    },
    {
        "name": "phase36_recursive_harness_surface",
        "kind": "rust_harness_surface",
        "path": "src/stwo_backend/recursion.rs",
        "expected_exists": True,
        "classification": "HARNESS_SURFACE_NOT_D128_TWO_SLICE_PROOF",
        "required_for_go": False,
        "required_tokens": (
            "phase36_prepare_recursive_verifier_harness_receipt",
            "verify_phase36_recursive_verifier_harness_receipt",
        ),
        "reason": "the recursive harness records claim boundaries; it does not execute the selected d128 slice verifiers in an outer proof",
    },
    {
        "name": "archived_stwo_accumulation_bundle",
        "kind": "archived_pre_recursive_artifact",
        "path": "docs/paper/artifacts/stwo-accumulation-v1-2026-04-09/APPENDIX_ARTIFACT_INDEX.md",
        "expected_exists": True,
        "classification": "ARCHIVED_DECODING_ARTIFACT_NOT_CURRENT_D128_TWO_SLICE_PROOF",
        "required_for_go": False,
        "reason": "archived decoding accumulators are not verifier-facing d128 outer proof objects",
    },
    {
        "name": "required_two_slice_outer_module",
        "kind": "required_outer_module",
        "path": "src/stwo_backend/d128_two_slice_outer_proof_object.rs",
        "expected_exists": False,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_for_go": True,
        "reason": "no current Stwo-native outer proof module exists for the selected d128 verifier checks",
    },
    {
        "name": "required_two_slice_outer_proof_artifact",
        "kind": "required_outer_proof_artifact",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-2026-05.json",
        "expected_exists": False,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_for_go": True,
        "reason": "no checked d128 two-slice outer proof or accumulator artifact exists",
    },
    {
        "name": "required_two_slice_outer_verifier_handle",
        "kind": "required_outer_verifier_handle",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-verifier-2026-05.json",
        "expected_exists": False,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_for_go": True,
        "reason": "no local verifier handle exists for a d128 two-slice outer proof object",
    },
    {
        "name": "required_two_slice_outer_mutation_tests",
        "kind": "required_outer_proof_test_surface",
        "path": "scripts/tests/test_zkai_d128_two_slice_outer_proof_object_backend.py",
        "expected_exists": False,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_for_go": True,
        "reason": "future outer proof public inputs must reject relabeling before metrics are meaningful",
    },
)


class D128TwoSliceOuterProofObjectSpikeError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128TwoSliceOuterProofObjectSpikeError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


AGGREGATION = _load_module(AGGREGATION_SCRIPT, "zkai_d128_aggregation_feasibility_for_two_slice_spike")


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


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be a list")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be a non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be an integer")
    return value


def require_commitment(value: Any, field: str) -> str:
    value = require_str(value, field)
    if not value.startswith("blake2b-256:"):
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def require_sha256_hex(value: Any, field: str) -> str:
    value = require_str(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise D128TwoSliceOuterProofObjectSpikeError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return AGGREGATION.load_json(path)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceOuterProofObjectSpikeError(f"failed to load source evidence {path}: {err}") from err


def file_sha256(path: pathlib.Path) -> str:
    try:
        return AGGREGATION.file_sha256(path)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceOuterProofObjectSpikeError(f"failed to hash source evidence {path}: {err}") from err


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _safe_candidate_path(raw_path: str) -> pathlib.Path:
    pure_path = pathlib.PurePosixPath(require_str(raw_path, "candidate path"))
    if pure_path.is_absolute() or raw_path != pure_path.as_posix() or any(part in ("", ".", "..") for part in pure_path.parts):
        raise D128TwoSliceOuterProofObjectSpikeError(f"candidate path must be repo-relative: {raw_path}")
    return ROOT.joinpath(*pure_path.parts)


def _path_entry_exists(path: pathlib.Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as err:
        raise D128TwoSliceOuterProofObjectSpikeError(f"failed to inspect candidate path {path}: {err}") from err
    return True


def load_checked_source(path: pathlib.Path = AGGREGATION_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        AGGREGATION.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceOuterProofObjectSpikeError(f"d128 aggregation feasibility validation failed: {err}") from err
    expect_equal(payload.get("schema"), AGGREGATION.SCHEMA, "source aggregation schema")
    expect_equal(payload.get("result"), AGGREGATION.RESULT, "source aggregation result")
    expect_equal(payload.get("aggregation_target_result"), AGGREGATION.TARGET_RESULT, "source aggregation target result")
    expect_equal(
        payload.get("aggregated_proof_object_result"),
        AGGREGATION.AGGREGATED_PROOF_RESULT,
        "source aggregated proof-object result",
    )
    if payload.get("case_count") != len(AGGREGATION.EXPECTED_MUTATION_INVENTORY):
        raise D128TwoSliceOuterProofObjectSpikeError("source aggregation mutation case_count mismatch")
    if payload.get("all_mutations_rejected") is not True:
        raise D128TwoSliceOuterProofObjectSpikeError("source aggregation did not reject all checked mutations")
    return payload


def source_descriptor(source: dict[str, Any], path: pathlib.Path = AGGREGATION_EVIDENCE) -> dict[str, Any]:
    summary = require_object(source.get("summary"), "source summary")
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "result": source["result"],
        "aggregation_target_result": source["aggregation_target_result"],
        "aggregated_proof_object_result": source["aggregated_proof_object_result"],
        "aggregation_target_commitment": source["aggregation_target_commitment"],
        "block_receipt_commitment": summary["block_receipt_commitment"],
        "statement_commitment": summary["statement_commitment"],
    }


def selected_slice_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = require_object(source.get("aggregation_target_manifest"), "source aggregation target manifest")
    checks = require_list(manifest.get("required_nested_verifier_checks"), "source nested verifier checks")
    by_slice = {}
    for check in checks:
        item = require_object(check, "source nested verifier check")
        slice_id = require_str(item.get("slice_id"), "source nested verifier check slice_id")
        if slice_id in by_slice:
            raise D128TwoSliceOuterProofObjectSpikeError("duplicate source nested verifier slice_id")
        by_slice[slice_id] = item
    selected = []
    for expected_index, slice_id in enumerate(SELECTED_SLICE_IDS):
        item = copy.deepcopy(by_slice.get(slice_id))
        if item is None:
            raise D128TwoSliceOuterProofObjectSpikeError(f"missing selected slice {slice_id}")
        expect_equal(item.get("index"), expected_index, f"selected slice {slice_id} index")
        for field in (
            "schema",
            "decision",
            "proof_backend_version",
            "source_path",
            "source_file_sha256",
            "source_payload_sha256",
        ):
            require_str(item.get(field), f"selected slice {slice_id} {field}")
        for field in ("proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment"):
            require_commitment(item.get(field), f"selected slice {slice_id} {field}")
        require_object(item.get("source_commitments"), f"selected slice {slice_id} source_commitments")
        require_object(item.get("target_commitments"), f"selected slice {slice_id} target_commitments")
        row_count = require_int(item.get("row_count"), f"selected slice {slice_id} row_count")
        if row_count <= 0:
            raise D128TwoSliceOuterProofObjectSpikeError(f"selected slice {slice_id} row_count must be positive")
        selected.append(item)
    if sum(check["row_count"] for check in selected) != EXPECTED_SELECTED_ROWS:
        raise D128TwoSliceOuterProofObjectSpikeError("selected slice checked-row total mismatch")
    return selected


def two_slice_target_manifest(source: dict[str, Any]) -> dict[str, Any]:
    summary = require_object(source.get("summary"), "source summary")
    public_inputs = require_object(source.get("block_receipt_public_inputs"), "source block receipt public inputs")
    selected = selected_slice_checks(source)
    selected_commitment = blake2b_commitment(selected, SELECTED_SLICE_CHAIN_DOMAIN)
    return {
        "target_version": TARGET_VERSION,
        "target_kind": TARGET_KIND,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "selected_slice_ids": list(SELECTED_SLICE_IDS),
        "selected_slice_count": len(SELECTED_SLICE_IDS),
        "selected_checked_rows": sum(check["row_count"] for check in selected),
        "source_full_aggregation_target_commitment": source["aggregation_target_commitment"],
        "block_receipt_commitment": public_inputs["block_receipt_commitment"],
        "statement_commitment": public_inputs["statement_commitment"],
        "slice_chain_commitment": public_inputs["slice_chain_commitment"],
        "evidence_manifest_commitment": public_inputs["evidence_manifest_commitment"],
        "input_activation_commitment": public_inputs["input_activation_commitment"],
        "output_activation_commitment": public_inputs["output_activation_commitment"],
        "required_backend_version": public_inputs["required_backend_version"],
        "verifier_domain": public_inputs["verifier_domain"],
        "aggregation_target_kind": summary["aggregation_target_kind"],
        "aggregation_target_version": summary["aggregation_target_version"],
        "selected_slice_chain_commitment": selected_commitment,
        "selected_slice_checks": selected,
    }


def candidate_inventory() -> list[dict[str, Any]]:
    inventory = []
    for spec in CANDIDATE_SPECS:
        path = _safe_candidate_path(spec["path"])
        exists = _path_entry_exists(path)
        if spec["expected_exists"] is True and exists is not True:
            raise D128TwoSliceOuterProofObjectSpikeError(f"expected candidate artifact is missing: {spec['path']}")
        if spec["expected_exists"] is False and exists is not False:
            raise D128TwoSliceOuterProofObjectSpikeError(
                f"required two-slice outer proof artifact now exists; rerun GO/NO-GO: {spec['path']}"
            )
        file_hash = file_sha256(path) if exists else None
        if "required_tokens" in spec and exists:
            text = path.read_text(encoding="utf-8")
            for token in spec["required_tokens"]:
                if token not in text:
                    raise D128TwoSliceOuterProofObjectSpikeError(
                        f"candidate artifact missing required token {token}: {spec['path']}"
                    )
        inventory.append(
            {
                "name": spec["name"],
                "kind": spec["kind"],
                "path": spec["path"],
                "exists": exists,
                "expected_exists": spec["expected_exists"],
                "required_for_go": spec["required_for_go"],
                "file_sha256": file_hash,
                "classification": spec["classification"],
                "accepted_as_outer_proof_object": False,
                "reason": spec["reason"],
            }
        )
    return inventory


def proof_object_attempt() -> dict[str, Any]:
    return {
        "go_criterion": GO_CRITERION,
        "outer_proof_object_claimed": False,
        "pcd_accumulator_claimed": False,
        "verifier_handle_claimed": False,
        "two_slice_target_commitment_bound_as_public_input": False,
        "selected_slice_statements_bound": False,
        "selected_source_evidence_hashes_bound": False,
        "outer_proof_artifacts": [],
        "verifier_handles": [],
        "proof_metrics": {
            "proof_size_bytes": None,
            "proof_generation_time_ms": None,
            "verifier_time_ms": None,
            "compressed_proof_size_bytes": None,
        },
        "missing_backend_features": list(MISSING_BACKEND_FEATURES),
        "first_blocker": FIRST_BLOCKER,
        "blocked_before_metrics": True,
    }


def refresh_commitments(payload: dict[str, Any]) -> None:
    target = require_object(payload.get("two_slice_target_manifest"), "two-slice target manifest")
    payload["two_slice_target_commitment"] = blake2b_commitment(target, TARGET_DOMAIN)
    payload["outer_public_input_contract"] = {
        "required_public_inputs": ["two_slice_target_commitment"],
        "two_slice_target_commitment": payload["two_slice_target_commitment"],
        "source_full_aggregation_target_commitment": target["source_full_aggregation_target_commitment"],
        "block_receipt_commitment": target["block_receipt_commitment"],
        "statement_commitment": target["statement_commitment"],
        "selected_slice_chain_commitment": target["selected_slice_chain_commitment"],
    }


def build_payload() -> dict[str, Any]:
    source = load_checked_source()
    target = two_slice_target_manifest(source)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "target_result": TARGET_RESULT,
        "outer_proof_object_result": OUTER_PROOF_RESULT,
        "source_aggregation_evidence": source_descriptor(source),
        "two_slice_target_manifest": target,
        "two_slice_target_commitment": None,
        "outer_public_input_contract": None,
        "candidate_inventory": candidate_inventory(),
        "proof_object_attempt": proof_object_attempt(),
        "summary": {
            "target_status": TARGET_RESULT,
            "outer_proof_object_status": OUTER_PROOF_RESULT,
            "selected_slice_ids": list(SELECTED_SLICE_IDS),
            "selected_slice_count": len(SELECTED_SLICE_IDS),
            "selected_checked_rows": target["selected_checked_rows"],
            "two_slice_target_kind": TARGET_KIND,
            "two_slice_target_version": TARGET_VERSION,
            "source_full_aggregation_target_commitment": source["aggregation_target_commitment"],
            "block_receipt_commitment": target["block_receipt_commitment"],
            "statement_commitment": target["statement_commitment"],
            "first_blocker": FIRST_BLOCKER,
            "blocked_before_metrics": True,
        },
        "non_claims": list(NON_CLAIMS),
        "pivot_options": copy.deepcopy(PIVOT_OPTIONS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_commitments(payload)
    return payload


def _validate_source_descriptor(payload: dict[str, Any], source_override: dict[str, Any] | None = None) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_aggregation_evidence"), "source aggregation evidence")
    path_value = require_str(descriptor.get("path"), "source aggregation evidence path")
    expect_equal(path_value, relative_path(AGGREGATION_EVIDENCE), "source aggregation evidence path")
    path = ROOT / path_value
    source = copy.deepcopy(source_override) if source_override is not None else load_checked_source(path)
    expect_equal(descriptor.get("file_sha256"), file_sha256(path), "source aggregation file_sha256")
    expect_equal(descriptor.get("payload_sha256"), sha256_hex_json(source), "source aggregation payload_sha256")
    for field in ("schema", "decision", "result", "aggregation_target_result", "aggregated_proof_object_result"):
        expect_equal(descriptor.get(field), source[field], f"source aggregation {field}")
    expect_equal(descriptor.get("aggregation_target_commitment"), source["aggregation_target_commitment"], "source target commitment")
    summary = require_object(source.get("summary"), "source summary")
    expect_equal(descriptor.get("block_receipt_commitment"), summary["block_receipt_commitment"], "source block receipt commitment")
    expect_equal(descriptor.get("statement_commitment"), summary["statement_commitment"], "source statement commitment")
    return source


def _validate_target(payload: dict[str, Any], source: dict[str, Any]) -> None:
    expected = two_slice_target_manifest(source)
    target = require_object(payload.get("two_slice_target_manifest"), "two-slice target manifest")
    expect_equal(target, expected, "two-slice target manifest")
    expect_equal(payload.get("two_slice_target_commitment"), blake2b_commitment(target, TARGET_DOMAIN), "two-slice target commitment")
    public_input_contract = require_object(payload.get("outer_public_input_contract"), "outer public input contract")
    expect_equal(
        public_input_contract,
        {
            "required_public_inputs": ["two_slice_target_commitment"],
            "two_slice_target_commitment": payload["two_slice_target_commitment"],
            "source_full_aggregation_target_commitment": target["source_full_aggregation_target_commitment"],
            "block_receipt_commitment": target["block_receipt_commitment"],
            "statement_commitment": target["statement_commitment"],
            "selected_slice_chain_commitment": target["selected_slice_chain_commitment"],
        },
        "outer public input contract",
    )


def _validate_candidate_inventory(payload: dict[str, Any]) -> None:
    inventory = require_list(payload.get("candidate_inventory"), "candidate inventory")
    expected = candidate_inventory()
    expect_equal(inventory, expected, "candidate inventory")
    if any(require_object(item, "candidate inventory row").get("accepted_as_outer_proof_object") for item in inventory):
        raise D128TwoSliceOuterProofObjectSpikeError("candidate inventory must not accept any current outer proof object")
    required_missing = [
        item for item in inventory if item["required_for_go"] is True and item["classification"] == "MISSING_REQUIRED_ARTIFACT"
    ]
    if len(required_missing) != 4:
        raise D128TwoSliceOuterProofObjectSpikeError("required missing outer-proof artifact count mismatch")


def _validate_attempt(payload: dict[str, Any]) -> None:
    attempt = require_object(payload.get("proof_object_attempt"), "proof object attempt")
    for field in (
        "outer_proof_object_claimed",
        "pcd_accumulator_claimed",
        "verifier_handle_claimed",
        "two_slice_target_commitment_bound_as_public_input",
        "selected_slice_statements_bound",
        "selected_source_evidence_hashes_bound",
    ):
        if attempt.get(field) is not False:
            raise D128TwoSliceOuterProofObjectSpikeError(f"{field} claimed without checked two-slice outer proof object")
    expect_equal(attempt.get("outer_proof_artifacts"), [], "outer proof artifacts")
    expect_equal(attempt.get("verifier_handles"), [], "verifier handles")
    metrics = require_object(attempt.get("proof_metrics"), "proof metrics")
    if any(value is not None for value in metrics.values()):
        raise D128TwoSliceOuterProofObjectSpikeError("proof metric smuggled before proof object exists")
    expect_equal(attempt.get("missing_backend_features"), MISSING_BACKEND_FEATURES, "missing backend features")
    expect_equal(attempt.get("first_blocker"), FIRST_BLOCKER, "first blocker")
    if attempt.get("blocked_before_metrics") is not True:
        raise D128TwoSliceOuterProofObjectSpikeError("proof attempt must be blocked before metrics")


def _validate_summary(payload: dict[str, Any], source: dict[str, Any]) -> None:
    summary = require_object(payload.get("summary"), "summary")
    target = require_object(payload.get("two_slice_target_manifest"), "two-slice target manifest")
    expect_equal(summary.get("target_status"), TARGET_RESULT, "summary target status")
    expect_equal(summary.get("outer_proof_object_status"), OUTER_PROOF_RESULT, "summary outer proof status")
    expect_equal(summary.get("selected_slice_ids"), list(SELECTED_SLICE_IDS), "summary selected slice ids")
    expect_equal(summary.get("selected_slice_count"), len(SELECTED_SLICE_IDS), "summary selected slice count")
    expect_equal(summary.get("selected_checked_rows"), EXPECTED_SELECTED_ROWS, "summary selected checked rows")
    expect_equal(summary.get("two_slice_target_kind"), TARGET_KIND, "summary target kind")
    expect_equal(summary.get("two_slice_target_version"), TARGET_VERSION, "summary target version")
    expect_equal(summary.get("source_full_aggregation_target_commitment"), source["aggregation_target_commitment"], "summary source target")
    expect_equal(summary.get("block_receipt_commitment"), target["block_receipt_commitment"], "summary block receipt")
    expect_equal(summary.get("statement_commitment"), target["statement_commitment"], "summary statement")
    expect_equal(summary.get("first_blocker"), FIRST_BLOCKER, "summary first blocker")
    if summary.get("blocked_before_metrics") is not True:
        raise D128TwoSliceOuterProofObjectSpikeError("summary must record blocked_before_metrics")
    if "mutation_cases" in summary:
        expect_equal(summary.get("mutation_cases"), len(EXPECTED_MUTATION_INVENTORY), "summary mutation cases")
        expect_equal(summary.get("mutations_rejected"), len(EXPECTED_MUTATION_INVENTORY), "summary mutations rejected")


def validate_payload(payload: Any, *, source_override: dict[str, Any] | None = None) -> None:
    payload = require_object(payload, "two-slice outer proof-object spike payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("issue"), ISSUE, "issue")
    expect_equal(payload.get("target_result"), TARGET_RESULT, "target result")
    expect_equal(payload.get("outer_proof_object_result"), OUTER_PROOF_RESULT, "outer proof-object result")
    source = _validate_source_descriptor(payload, source_override=source_override)
    _validate_target(payload, source)
    _validate_candidate_inventory(payload)
    _validate_attempt(payload)
    _validate_summary(payload, source)
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("pivot_options"), PIVOT_OPTIONS, "pivot options")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    if "mutation_inventory" not in payload:
        return
    expect_equal(payload.get("mutation_inventory"), expected_mutation_inventory(), "mutation inventory")
    cases = require_list(payload.get("cases"), "mutation cases")
    expect_equal(payload.get("case_count"), len(EXPECTED_MUTATION_INVENTORY), "mutation case_count")
    if payload.get("all_mutations_rejected") is not True:
        raise D128TwoSliceOuterProofObjectSpikeError("not all two-slice outer proof-object mutations rejected")
    seen = set()
    for case in cases:
        case = require_object(case, "mutation case")
        mutation = require_str(case.get("mutation"), "mutation case mutation")
        if mutation in seen:
            raise D128TwoSliceOuterProofObjectSpikeError("duplicate mutation case")
        seen.add(mutation)
        if case.get("mutated_accepted") is not False or case.get("rejected") is not True:
            raise D128TwoSliceOuterProofObjectSpikeError("mutation case did not fail closed")
        require_str(case.get("error"), "mutation case error")
    expect_equal(seen, {mutation for mutation, _surface in EXPECTED_MUTATION_INVENTORY}, "mutation case inventory")
    expect_equal(payload["summary"].get("mutation_cases"), len(EXPECTED_MUTATION_INVENTORY), "summary mutation case count")
    expect_equal(payload["summary"].get("mutations_rejected"), len(EXPECTED_MUTATION_INVENTORY), "summary mutation rejection count")


MutationFn = Callable[[dict[str, Any]], None]


def _case(name: str, surface: str, baseline: dict[str, Any], mutate: MutationFn) -> dict[str, Any]:
    mutated = copy.deepcopy(baseline)
    try:
        mutate(mutated)
        validate_payload(mutated, source_override=load_checked_source())
        return {
            "mutation": name,
            "surface": surface,
            "baseline_result": baseline["result"],
            "mutated_accepted": True,
            "rejected": False,
            "rejection_layer": "",
            "error": "",
        }
    except Exception as err:  # noqa: BLE001 - mutations intentionally collect rejection diagnostics.
        message = str(err) or f"{type(err).__name__} with empty message"
        return {
            "mutation": name,
            "surface": surface,
            "baseline_result": baseline["result"],
            "mutated_accepted": False,
            "rejected": True,
            "rejection_layer": surface,
            "error": message,
        }


def _selected_check(payload: dict[str, Any], index: int = 0) -> dict[str, Any]:
    checks = payload["two_slice_target_manifest"]["selected_slice_checks"]
    return checks[index]


def mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    mutators: dict[str, MutationFn] = {
        "source_feasibility_path_drift": lambda p: p["source_aggregation_evidence"].__setitem__("path", "docs/engineering/evidence/../evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.json"),
        "source_feasibility_file_hash_drift": lambda p: p["source_aggregation_evidence"].__setitem__("file_sha256", "0" * 64),
        "source_feasibility_payload_hash_drift": lambda p: p["source_aggregation_evidence"].__setitem__("payload_sha256", "1" * 64),
        "source_feasibility_result_drift": lambda p: p["source_aggregation_evidence"].__setitem__("result", "GO"),
        "source_aggregation_target_commitment_drift": lambda p: p["two_slice_target_manifest"].__setitem__("source_full_aggregation_target_commitment", "blake2b-256:" + "22" * 32),
        "block_receipt_commitment_drift": lambda p: p["two_slice_target_manifest"].__setitem__("block_receipt_commitment", "blake2b-256:" + "33" * 32),
        "statement_commitment_drift": lambda p: p["two_slice_target_manifest"].__setitem__("statement_commitment", "blake2b-256:" + "44" * 32),
        "selected_slice_chain_commitment_drift": lambda p: p["two_slice_target_manifest"].__setitem__("selected_slice_chain_commitment", "blake2b-256:" + "55" * 32),
        "two_slice_target_commitment_drift": lambda p: p.__setitem__("two_slice_target_commitment", "blake2b-256:" + "66" * 32),
        "selected_slice_removed": lambda p: p["two_slice_target_manifest"]["selected_slice_checks"].pop(),
        "selected_slice_duplicated": lambda p: p["two_slice_target_manifest"]["selected_slice_checks"].append(copy.deepcopy(p["two_slice_target_manifest"]["selected_slice_checks"][0])),
        "selected_slice_reordered": lambda p: p["two_slice_target_manifest"]["selected_slice_checks"].reverse(),
        "selected_slice_source_file_hash_drift": lambda p: _selected_check(p).__setitem__("source_file_sha256", "2" * 64),
        "selected_slice_source_payload_hash_drift": lambda p: _selected_check(p).__setitem__("source_payload_sha256", "3" * 64),
        "selected_slice_statement_commitment_drift": lambda p: _selected_check(p).__setitem__("statement_commitment", "blake2b-256:" + "77" * 32),
        "selected_slice_public_instance_commitment_drift": lambda p: _selected_check(p).__setitem__("public_instance_commitment", "blake2b-256:" + "88" * 32),
        "selected_slice_proof_parameter_commitment_drift": lambda p: _selected_check(p).__setitem__("proof_native_parameter_commitment", "blake2b-256:" + "99" * 32),
        "selected_slice_row_count_drift": lambda p: _selected_check(p).__setitem__("row_count", 129),
        "selected_checked_rows_drift": lambda p: p["two_slice_target_manifest"].__setitem__("selected_checked_rows", 999),
        "candidate_inventory_acceptance_relabel": lambda p: p["candidate_inventory"][0].__setitem__("accepted_as_outer_proof_object", True),
        "candidate_inventory_file_sha256_tampered": lambda p: p["candidate_inventory"][0].__setitem__("file_sha256", "4" * 64),
        "candidate_inventory_required_artifact_removed": lambda p: p["candidate_inventory"].pop(),
        "outer_proof_claimed_without_artifact": lambda p: p["proof_object_attempt"].__setitem__("outer_proof_object_claimed", True),
        "pcd_claimed_without_artifact": lambda p: p["proof_object_attempt"].__setitem__("pcd_accumulator_claimed", True),
        "verifier_handle_claimed_without_artifact": lambda p: p["proof_object_attempt"].__setitem__("verifier_handle_claimed", True),
        "target_public_input_claimed_without_proof": lambda p: p["proof_object_attempt"].__setitem__("two_slice_target_commitment_bound_as_public_input", True),
        "selected_statements_claimed_without_proof": lambda p: p["proof_object_attempt"].__setitem__("selected_slice_statements_bound", True),
        "selected_source_hashes_claimed_without_proof": lambda p: p["proof_object_attempt"].__setitem__("selected_source_evidence_hashes_bound", True),
        "proof_size_metric_smuggled_before_proof": lambda p: p["proof_object_attempt"]["proof_metrics"].__setitem__("proof_size_bytes", 8192),
        "verifier_time_metric_smuggled_before_proof": lambda p: p["proof_object_attempt"]["proof_metrics"].__setitem__("verifier_time_ms", 1.5),
        "proof_generation_time_metric_smuggled_before_proof": lambda p: p["proof_object_attempt"]["proof_metrics"].__setitem__("proof_generation_time_ms", 2.5),
        "blocked_before_metrics_disabled": lambda p: p["proof_object_attempt"].__setitem__("blocked_before_metrics", False),
        "first_blocker_removed": lambda p: p["proof_object_attempt"].__setitem__("first_blocker", ""),
        "missing_backend_feature_removed": lambda p: p["proof_object_attempt"]["missing_backend_features"].pop(),
        "outer_proof_result_changed_to_go": lambda p: p.__setitem__("outer_proof_object_result", "GO"),
        "decision_changed_to_go": lambda p: p.__setitem__("decision", "GO_D128_TWO_SLICE_OUTER_PROOF_OBJECT"),
        "result_changed_to_go": lambda p: p.__setitem__("result", "GO"),
        "non_claims_removed": lambda p: p.__setitem__("non_claims", []),
        "validation_command_drift": lambda p: p["validation_commands"].__setitem__(0, "python3 scripts/tampered.py"),
    }
    cases = []
    for mutation, surface in EXPECTED_MUTATION_INVENTORY:
        cases.append(_case(mutation, surface, payload, mutators[mutation]))
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
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=json_path.parent, delete=False) as handle:
            tmp = pathlib.Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        tmp.replace(json_path)
    if tsv_path is not None:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=tsv_path.parent, delete=False) as handle:
            tmp = pathlib.Path(handle.name)
            handle.write(to_tsv(payload))
        tmp.replace(tsv_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(
        json.dumps(
            {
                "target_status": payload["target_result"],
                "outer_proof_object_status": payload["outer_proof_object_result"],
                "two_slice_target_commitment": payload["two_slice_target_commitment"],
                "selected_slice_ids": payload["summary"]["selected_slice_ids"],
                "selected_checked_rows": payload["summary"]["selected_checked_rows"],
                "mutation_cases": payload["case_count"],
                "mutations_rejected": payload["summary"]["mutations_rejected"],
                "first_blocker": payload["summary"]["first_blocker"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
