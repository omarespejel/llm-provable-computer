#!/usr/bin/env python3
"""Classify the d128 block receipt as an aggregated proof-object target.

This gate is deliberately conservative.  It accepts the current d128 block
receipt composition as a checked statement-bound target, then asks whether the
repository currently contains a real outer proof, accumulator, or verifier-facing
proof object that binds that receipt.  If not, it records a bounded NO-GO and
rejects fake proof metrics or relabeling of the target commitments.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import stat as stat_module
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
BLOCK_RECEIPT_EVIDENCE = EVIDENCE_DIR / "zkai-d128-block-receipt-composition-gate-2026-05.json"
BACKEND_SPIKE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-proof-artifact-backend-spike-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-aggregated-proof-object-feasibility-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-aggregated-proof-object-feasibility-2026-05.tsv"

SCHEMA = "zkai-d128-aggregated-proof-object-feasibility-v1"
DECISION = "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING"
RESULT = "BOUNDED_NO_GO"
TARGET_RESULT = "GO_D128_AGGREGATION_TARGET_ONLY"
AGGREGATED_PROOF_RESULT = "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING"
ISSUE = 405
TARGET_VERSION = "zkai-d128-aggregated-proof-object-target-v1"
TARGET_KIND = "d128-block-receipt-aggregated-proof-object-target"
TARGET_DOMAIN = "ptvm:zkai:d128-aggregated-proof-object:target:v1"
WIDTH = 128
FF_DIM = 512
MAX_SOURCE_JSON_BYTES = 16 * 1024 * 1024
BLOCK_RECEIPT_SCHEMA = "zkai-d128-block-receipt-composition-gate-v1"
BLOCK_RECEIPT_DECISION = "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE"
BLOCK_RECEIPT_RESULT = "GO"
EXPECTED_BLOCK_RECEIPT_COMMITMENT = "blake2b-256:20b656e0d52771ff91751bb6beace60a8609b9a76264342a6130457066fbacea"
EXPECTED_BLOCK_STATEMENT_COMMITMENT = "blake2b-256:4e34c91eaa458ae421cfc18a11811b331f0c85ca74e291496be1d50ce7adf02c"
EXPECTED_INPUT_ACTIVATION_COMMITMENT = "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78"
EXPECTED_OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1"
EXPECTED_RANGE_POLICY_COMMITMENT = "blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985"
EXPECTED_TOTAL_CHECKED_ROWS = 197_504
EXPECTED_COMPOSITION_MUTATIONS = 21
EXPECTED_SLICE_IDS = (
    "rmsnorm_public_rows",
    "rmsnorm_projection_bridge",
    "gate_value_projection",
    "activation_swiglu",
    "down_projection",
    "residual_add",
)

FIRST_BLOCKER = (
    "missing outer proof or accumulator backend that proves the six d128 slice-verifier "
    "checks and binds the d128 block receipt, statement, and range-policy commitments as public inputs"
)

GO_CRITERION = (
    "one outer proof, accumulator, or proof-carrying artifact verifies the six d128 "
    "slice-verifier checks and binds block_receipt_commitment, statement_commitment, "
    "and range_policy_commitment as public inputs"
)

MISSING_BACKEND_FEATURES = [
    "recursive verifier program/AIR/circuit for each d128 slice verifier",
    "outer proof or PCD accumulator object over the six d128 slice-verifier checks",
    "adapter that binds block_receipt_commitment, statement_commitment, and range_policy_commitment into outer public inputs",
    "local verifier handle for the resulting aggregated proof object",
    "fail-closed mutation tests for source manifest, slice chain, commitments, verifier-domain, and fake metrics",
]

NON_CLAIMS = [
    "not recursive aggregation of the six d128 slice proofs",
    "not one compressed verifier object",
    "not proof-carrying-data accumulation",
    "not verifier-time benchmark evidence for an aggregated d128 proof",
    "not proof-size benchmark evidence for an aggregated d128 proof",
    "not proof-generation-time benchmark evidence for an aggregated d128 proof",
    "not matched NANOZK, DeepProve, EZKL, or snarkjs comparison evidence",
    "not onchain deployment evidence",
    "not a claim that d128 aggregation is impossible",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_aggregated_proof_object_feasibility_gate.py --write-json docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_aggregated_proof_object_feasibility_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate-fast",
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
    ("aggregation_target_commitment_drift", "aggregation_target_commitment"),
    ("source_block_receipt_file_hash_drift", "source_block_receipt_evidence"),
    ("source_block_receipt_payload_hash_drift", "source_block_receipt_evidence"),
    ("source_block_receipt_decision_drift", "source_block_receipt_evidence"),
    ("block_receipt_commitment_drift", "aggregation_target_manifest"),
    ("statement_commitment_drift", "aggregation_target_manifest"),
    ("input_commitment_drift", "aggregation_target_manifest"),
    ("output_commitment_drift", "aggregation_target_manifest"),
    ("range_policy_commitment_drift", "aggregation_target_manifest"),
    ("slice_chain_commitment_drift", "aggregation_target_manifest"),
    ("evidence_manifest_commitment_drift", "aggregation_target_manifest"),
    ("nested_verifier_check_removed", "aggregation_target_manifest"),
    ("nested_verifier_check_reordered", "aggregation_target_manifest"),
    ("nested_verifier_source_hash_drift", "aggregation_target_manifest"),
    ("nested_verifier_statement_drift", "aggregation_target_manifest"),
    ("verifier_domain_drift", "aggregation_target_manifest"),
    ("required_backend_version_drift", "aggregation_target_manifest"),
    ("composition_mutation_count_drift", "aggregation_target_manifest"),
    ("candidate_inventory_acceptance_relabel", "candidate_inventory"),
    ("candidate_inventory_file_sha256_tampered", "candidate_inventory"),
    ("candidate_inventory_required_artifact_removed", "candidate_inventory"),
    ("aggregated_proof_claimed_without_artifact", "proof_object_attempt"),
    ("recursive_claimed_without_artifact", "proof_object_attempt"),
    ("pcd_claimed_without_artifact", "proof_object_attempt"),
    ("verifier_handle_claimed_without_artifact", "proof_object_attempt"),
    ("aggregation_target_public_input_claimed_without_proof", "proof_object_attempt"),
    ("block_receipt_public_input_claimed_without_proof", "proof_object_attempt"),
    ("statement_public_input_claimed_without_proof", "proof_object_attempt"),
    ("range_policy_public_input_claimed_without_proof", "proof_object_attempt"),
    ("invented_aggregated_proof_artifact", "proof_object_attempt"),
    ("proof_size_metric_smuggled_before_proof", "proof_object_attempt"),
    ("verifier_time_metric_smuggled_before_proof", "proof_object_attempt"),
    ("proof_generation_time_metric_smuggled_before_proof", "proof_object_attempt"),
    ("first_blocker_removed", "proof_object_attempt"),
    ("missing_backend_feature_removed", "proof_object_attempt"),
    ("decision_changed_to_go", "parser_or_schema"),
    ("result_changed_to_go", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
)

CANDIDATE_SURFACES = (
    {
        "name": "d128_block_receipt_composition_gate",
        "kind": "statement_bound_receipt",
        "path": "docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json",
        "expected_exists": True,
        "expected_file_sha256": "87c0d6bef7527c7d26013bb50a4f03ef9042e03c27699f85bb9c0851a47c259f",
        "classification": "GO_AGGREGATION_TARGET_ONLY",
        "reason": "binds the six d128 slice handles into one statement-bound receipt, but is not an outer proof object",
    },
    {
        "name": "d128_backend_spike_gate",
        "kind": "backend_route_classification",
        "path": "docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json",
        "expected_exists": True,
        "expected_file_sha256": "f670fea5f90af8c8e8d49776b2f4ba3588bfd16aa9aaeb7e899b87c6910586fe",
        "classification": "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING",
        "reason": "records the current full-block blocker; it does not provide a verifier-facing proof object",
    },
    {
        "name": "d64_recursive_pcd_feasibility_gate",
        "kind": "smaller_width_no_go_reference",
        "path": "docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json",
        "expected_exists": True,
        "expected_file_sha256": "2c2949da569f8019f89b2867b3150093290ace4168c7fe3e67762b5ed999079e",
        "classification": "REFERENCE_ONLY_NOT_D128",
        "reason": "d64 feasibility evidence is useful prior art, but cannot be relabeled as a d128 proof object",
    },
    {
        "name": "d128_full_block_native_module",
        "kind": "required_outer_module",
        "path": "src/stwo_backend/d128_native_transformer_block_proof.rs",
        "expected_exists": False,
        "expected_file_sha256": None,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no direct native full-block d128 proof/verifier module is present",
    },
    {
        "name": "d128_nested_verifier_aggregation_module",
        "kind": "required_outer_module",
        "path": "src/stwo_backend/d128_nested_verifier_aggregation_proof.rs",
        "expected_exists": False,
        "expected_file_sha256": None,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no nested verifier aggregation module exists for the six d128 slice verifiers",
    },
    {
        "name": "d128_aggregated_proof_artifact",
        "kind": "required_proof_artifact",
        "path": "docs/engineering/evidence/zkai-d128-aggregated-proof-object-2026-05.json",
        "expected_exists": False,
        "expected_file_sha256": None,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no checked aggregated proof object artifact exists",
    },
    {
        "name": "d128_aggregated_verifier_handle",
        "kind": "required_verifier_handle",
        "path": "docs/engineering/evidence/zkai-d128-aggregated-proof-object-verifier-2026-05.json",
        "expected_exists": False,
        "expected_file_sha256": None,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "reason": "no verifier handle exists for an aggregated d128 proof object",
    },
)


class D128AggregatedProofObjectFeasibilityError(ValueError):
    pass


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
        raise D128AggregatedProofObjectFeasibilityError(f"{field} mismatch")


def expect_key_set(value: dict[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise D128AggregatedProofObjectFeasibilityError(
            f"{field} key set mismatch: missing={missing} extra={extra}"
        )


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be a list")
    return value


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be a boolean")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be an integer")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be a non-empty string")
    return value


def require_sha256_hex(value: Any, field: str) -> str:
    value = require_str(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128AggregatedProofObjectFeasibilityError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def _open_repo_regular_file(path: pathlib.Path | str) -> tuple[int, pathlib.Path]:
    candidate = pathlib.Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        if candidate.is_symlink():
            raise D128AggregatedProofObjectFeasibilityError(f"source evidence must not be a symlink: {path}")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as err:
            raise D128AggregatedProofObjectFeasibilityError(
                f"source evidence path escapes repository: {path}"
            ) from err
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128AggregatedProofObjectFeasibilityError(f"source evidence is not a regular file: {path}")
        fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128AggregatedProofObjectFeasibilityError(f"source evidence is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128AggregatedProofObjectFeasibilityError(f"source evidence changed while reading: {path}")
            opened_fd = fd
            fd = None
            return opened_fd, resolved
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise D128AggregatedProofObjectFeasibilityError(f"failed to read source evidence {path}: {err}") from err


def load_json(path: pathlib.Path | str) -> dict[str, Any]:
    fd, _resolved = _open_repo_regular_file(path)
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read(MAX_SOURCE_JSON_BYTES + 1)
    if len(raw) > MAX_SOURCE_JSON_BYTES:
        raise D128AggregatedProofObjectFeasibilityError(f"source evidence exceeds max size: {path}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128AggregatedProofObjectFeasibilityError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128AggregatedProofObjectFeasibilityError(f"source evidence must be a JSON object: {path}")
    return payload


def file_sha256(path: pathlib.Path | str) -> str:
    digest = hashlib.sha256()
    fd, _resolved = _open_repo_regular_file(path)
    with os.fdopen(fd, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path | str) -> str:
    return pathlib.Path(path).resolve().relative_to(ROOT.resolve()).as_posix()


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def _validate_checked_block_receipt_payload(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "d128 block receipt evidence")
    expect_equal(payload.get("schema"), BLOCK_RECEIPT_SCHEMA, "d128 block receipt schema")
    expect_equal(payload.get("decision"), BLOCK_RECEIPT_DECISION, "d128 block receipt decision")
    expect_equal(payload.get("result"), BLOCK_RECEIPT_RESULT, "d128 block receipt result")
    if payload.get("case_count") != EXPECTED_COMPOSITION_MUTATIONS:
        raise D128AggregatedProofObjectFeasibilityError("d128 block receipt mutation case count mismatch")
    if payload.get("all_mutations_rejected") is not True:
        raise D128AggregatedProofObjectFeasibilityError("d128 block receipt did not reject all checked mutations")
    summary = require_object(payload.get("summary"), "d128 block receipt summary")
    expect_equal(summary.get("slice_count"), len(EXPECTED_SLICE_IDS), "d128 block receipt slice count")
    expect_equal(summary.get("total_checked_rows"), EXPECTED_TOTAL_CHECKED_ROWS, "d128 block receipt checked rows")
    expect_equal(
        summary.get("mutations_rejected"),
        EXPECTED_COMPOSITION_MUTATIONS,
        "d128 block receipt rejected mutation count",
    )
    receipt = require_object(payload.get("block_receipt"), "d128 block receipt")
    expect_equal(
        receipt.get("block_receipt_commitment"),
        EXPECTED_BLOCK_RECEIPT_COMMITMENT,
        "d128 block receipt commitment",
    )
    expect_equal(
        receipt.get("statement_commitment"),
        EXPECTED_BLOCK_STATEMENT_COMMITMENT,
        "d128 block statement commitment",
    )
    expect_equal(
        receipt.get("input_activation_commitment"),
        EXPECTED_INPUT_ACTIVATION_COMMITMENT,
        "d128 block input activation commitment",
    )
    expect_equal(
        receipt.get("output_activation_commitment"),
        EXPECTED_OUTPUT_ACTIVATION_COMMITMENT,
        "d128 block output activation commitment",
    )
    expect_equal(
        receipt.get("range_policy_commitment"),
        EXPECTED_RANGE_POLICY_COMMITMENT,
        "d128 block range policy commitment",
    )
    require_commitment(payload.get("slice_chain_commitment"), "d128 slice chain commitment")
    require_commitment(payload.get("evidence_manifest_commitment"), "d128 evidence manifest commitment")
    chain = require_list(payload.get("slice_chain"), "d128 slice chain")
    manifest = require_list(payload.get("source_evidence_manifest"), "d128 source evidence manifest")
    if len(chain) != len(EXPECTED_SLICE_IDS) or len(manifest) != len(EXPECTED_SLICE_IDS):
        raise D128AggregatedProofObjectFeasibilityError("d128 block receipt slice inventory mismatch")
    for index, slice_id in enumerate(EXPECTED_SLICE_IDS):
        chain_item = require_object(chain[index], f"d128 slice chain item {index}")
        manifest_item = require_object(manifest[index], f"d128 source manifest item {index}")
        expect_key_set(
            chain_item,
            {
                "index",
                "slice_id",
                "schema",
                "decision",
                "proof_backend_version",
                "proof_native_parameter_commitment",
                "public_instance_commitment",
                "statement_commitment",
                "source_commitments",
                "target_commitments",
                "row_count",
            },
            f"d128 slice chain item {index}",
        )
        expect_key_set(
            manifest_item,
            {
                "index",
                "slice_id",
                "path",
                "file_sha256",
                "payload_sha256",
                "schema",
                "decision",
                "proof_backend_version",
            },
            f"d128 source manifest item {index}",
        )
        expect_equal(chain_item.get("index"), index, f"d128 slice chain item {index} index")
        expect_equal(chain_item.get("slice_id"), slice_id, f"d128 slice chain item {index} slice_id")
        expect_equal(manifest_item.get("index"), index, f"d128 source manifest item {index} index")
        expect_equal(manifest_item.get("slice_id"), slice_id, f"d128 source manifest item {index} slice_id")
        require_str(chain_item.get("schema"), f"d128 slice {slice_id} schema")
        require_str(chain_item.get("decision"), f"d128 slice {slice_id} decision")
        require_str(chain_item.get("proof_backend_version"), f"d128 slice {slice_id} proof version")
        require_str(manifest_item.get("path"), f"d128 source manifest {slice_id} path")
        require_sha256_hex(manifest_item.get("file_sha256"), f"d128 source manifest {slice_id} file_sha256")
        require_sha256_hex(manifest_item.get("payload_sha256"), f"d128 source manifest {slice_id} payload_sha256")
        require_str(manifest_item.get("schema"), f"d128 source manifest {slice_id} schema")
        require_str(manifest_item.get("decision"), f"d128 source manifest {slice_id} decision")
        require_str(
            manifest_item.get("proof_backend_version"),
            f"d128 source manifest {slice_id} proof version",
        )
        expect_equal(
            chain_item.get("proof_backend_version"),
            manifest_item.get("proof_backend_version"),
            f"d128 slice {slice_id} proof version",
        )
        expect_equal(chain_item.get("schema"), manifest_item.get("schema"), f"d128 slice {slice_id} schema")
        for field in ("proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment"):
            require_commitment(chain_item.get(field), f"d128 slice {slice_id} {field}")
        source_commitments = require_object(
            chain_item.get("source_commitments"),
            f"d128 slice {slice_id} source commitments",
        )
        target_commitments = require_object(
            chain_item.get("target_commitments"),
            f"d128 slice {slice_id} target commitments",
        )
        for field, commitment in [*source_commitments.items(), *target_commitments.items()]:
            require_commitment(commitment, f"d128 slice {slice_id} {field}")
        row_count = require_int(chain_item.get("row_count"), f"d128 slice {slice_id} row_count")
        if row_count <= 0:
            raise D128AggregatedProofObjectFeasibilityError(f"d128 slice {slice_id} row_count must be positive")
    expect_equal(
        sum(require_int(require_object(item, "slice item").get("row_count"), "slice row count") for item in chain),
        EXPECTED_TOTAL_CHECKED_ROWS,
        "d128 block receipt row-count sum",
    )
    return payload


def load_checked_block_receipt(path: pathlib.Path = BLOCK_RECEIPT_EVIDENCE) -> dict[str, Any]:
    return _validate_checked_block_receipt_payload(load_json(path))


def source_evidence_descriptor(source: dict[str, Any], path: pathlib.Path = BLOCK_RECEIPT_EVIDENCE) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "result": source["result"],
        "block_receipt_commitment": receipt["block_receipt_commitment"],
        "statement_commitment": receipt["statement_commitment"],
        "range_policy_commitment": receipt["range_policy_commitment"],
    }


def block_receipt_public_inputs(source: dict[str, Any]) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    return {
        "block_receipt_commitment": receipt["block_receipt_commitment"],
        "statement_commitment": receipt["statement_commitment"],
        "range_policy_commitment": receipt["range_policy_commitment"],
        "slice_chain_commitment": source["slice_chain_commitment"],
        "evidence_manifest_commitment": source["evidence_manifest_commitment"],
        "input_activation_commitment": receipt["input_activation_commitment"],
        "output_activation_commitment": receipt["output_activation_commitment"],
        "target_id": receipt["target_id"],
        "statement_kind": receipt["statement_kind"],
        "required_backend_version": receipt["required_backend_version"],
        "verifier_domain": receipt["verifier_domain"],
    }


def _manifest_by_slice(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = require_list(source.get("source_evidence_manifest"), "source evidence manifest")
    by_slice: dict[str, dict[str, Any]] = {}
    for item in manifest:
        item = require_object(item, "source evidence manifest item")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D128AggregatedProofObjectFeasibilityError("source manifest slice_id must be a string")
        if slice_id in by_slice:
            raise D128AggregatedProofObjectFeasibilityError("duplicate source manifest slice_id")
        by_slice[slice_id] = item
    return by_slice


def required_nested_verifier_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    chain = require_list(source.get("slice_chain"), "source slice chain")
    manifest_by_slice = _manifest_by_slice(source)
    checks = []
    for expected_index, raw_item in enumerate(chain):
        item = require_object(raw_item, "source slice chain item")
        if item.get("index") != expected_index:
            raise D128AggregatedProofObjectFeasibilityError("source slice chain index mismatch")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D128AggregatedProofObjectFeasibilityError("source slice chain slice_id must be a string")
        manifest = manifest_by_slice.get(slice_id)
        if manifest is None:
            raise D128AggregatedProofObjectFeasibilityError(f"missing source manifest for slice {slice_id}")
        checks.append(
            {
                "index": expected_index,
                "slice_id": slice_id,
                "schema": item["schema"],
                "decision": item["decision"],
                "proof_backend_version": item["proof_backend_version"],
                "source_path": manifest["path"],
                "source_file_sha256": manifest["file_sha256"],
                "source_payload_sha256": manifest["payload_sha256"],
                "proof_native_parameter_commitment": item["proof_native_parameter_commitment"],
                "public_instance_commitment": item["public_instance_commitment"],
                "statement_commitment": item["statement_commitment"],
                "source_commitments": copy.deepcopy(item["source_commitments"]),
                "target_commitments": copy.deepcopy(item["target_commitments"]),
                "row_count": item["row_count"],
            }
        )
    return checks


def aggregation_target_manifest(source: dict[str, Any]) -> dict[str, Any]:
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    summary = require_object(source.get("summary"), "source block receipt summary")
    return {
        "target_version": TARGET_VERSION,
        "target_kind": TARGET_KIND,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "target_id": receipt["target_id"],
        "statement_kind": receipt["statement_kind"],
        "model_config": copy.deepcopy(receipt["model_config"]),
        "required_backend_version": receipt["required_backend_version"],
        "verifier_domain": receipt["verifier_domain"],
        "public_inputs": block_receipt_public_inputs(source),
        "block_receipt_commitment": receipt["block_receipt_commitment"],
        "statement_commitment": receipt["statement_commitment"],
        "range_policy_commitment": receipt["range_policy_commitment"],
        "slice_chain_commitment": source["slice_chain_commitment"],
        "evidence_manifest_commitment": source["evidence_manifest_commitment"],
        "input_activation_commitment": receipt["input_activation_commitment"],
        "output_activation_commitment": receipt["output_activation_commitment"],
        "required_nested_verifier_checks": required_nested_verifier_checks(source),
        "composition_evidence": {
            "schema": source["schema"],
            "decision": source["decision"],
            "result": source["result"],
            "case_count": source["case_count"],
            "mutations_rejected": summary["mutations_rejected"],
            "all_mutations_rejected": source["all_mutations_rejected"],
            "total_checked_rows": summary["total_checked_rows"],
        },
    }


def _candidate_path_from_spec(spec: dict[str, Any]) -> pathlib.Path:
    raw_path = require_str(spec.get("path"), "candidate surface path")
    pure_path = pathlib.PurePosixPath(raw_path)
    if pure_path.is_absolute() or raw_path != pure_path.as_posix() or any(part in ("", ".", "..") for part in pure_path.parts):
        raise D128AggregatedProofObjectFeasibilityError(f"candidate surface path must be repo-relative: {raw_path}")
    return ROOT.joinpath(*pure_path.parts)


def _candidate_path_present(path: pathlib.Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as err:
        raise D128AggregatedProofObjectFeasibilityError(f"failed to inspect candidate artifact path {path}: {err}") from err
    return True


def _candidate_file_sha256(path: pathlib.Path) -> str | None:
    if not _candidate_path_present(path):
        return None
    return file_sha256(path)


def candidate_inventory() -> list[dict[str, Any]]:
    inventory = []
    for spec in CANDIDATE_SURFACES:
        path = _candidate_path_from_spec(spec)
        exists = _candidate_path_present(path)
        expected_sha256 = spec["expected_file_sha256"]
        if spec["expected_exists"] is True and exists is not True:
            raise D128AggregatedProofObjectFeasibilityError(
                f"expected candidate artifact is missing: {spec['path']}"
            )
        if spec["expected_exists"] is False and exists is not False:
            raise D128AggregatedProofObjectFeasibilityError(
                f"required aggregated proof artifact now exists; rerun GO/NO-GO: {spec['path']}"
            )
        actual_sha256 = _candidate_file_sha256(path)
        if expected_sha256 is not None and actual_sha256 != expected_sha256:
            raise D128AggregatedProofObjectFeasibilityError(
                f"candidate inventory file_sha256 drift for {spec['path']}"
            )
        inventory.append(
            {
                "name": spec["name"],
                "kind": spec["kind"],
                "path": spec["path"],
                "exists": exists,
                "expected_exists": spec["expected_exists"],
                "file_sha256": actual_sha256,
                "classification": spec["classification"],
                "accepted_as_aggregated_proof_object": False,
                "reason": spec["reason"],
            }
        )
    return inventory


def proof_object_attempt() -> dict[str, Any]:
    return {
        "go_criterion": GO_CRITERION,
        "aggregated_proof_object_claimed": False,
        "recursive_aggregation_claimed": False,
        "pcd_accumulator_claimed": False,
        "verifier_handle_claimed": False,
        "aggregation_target_commitment_bound_as_public_input": False,
        "block_receipt_commitment_bound_as_public_input": False,
        "statement_commitment_bound_as_public_input": False,
        "range_policy_commitment_bound_as_public_input": False,
        "aggregated_proof_artifacts": [],
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
    manifest = require_object(payload.get("aggregation_target_manifest"), "aggregation target manifest")
    payload["aggregation_target_commitment"] = blake2b_commitment(manifest, TARGET_DOMAIN)


def _build_payload_from_canonical_source(source: dict[str, Any]) -> dict[str, Any]:
    source = _validate_checked_block_receipt_payload(copy.deepcopy(source))
    summary = require_object(source.get("summary"), "source block receipt summary")
    target = aggregation_target_manifest(source)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "aggregation_target_result": TARGET_RESULT,
        "aggregated_proof_object_result": AGGREGATED_PROOF_RESULT,
        "source_block_receipt_evidence": source_evidence_descriptor(source),
        "block_receipt_public_inputs": block_receipt_public_inputs(source),
        "aggregation_target_manifest": target,
        "aggregation_target_commitment": None,
        "candidate_inventory": candidate_inventory(),
        "proof_object_attempt": proof_object_attempt(),
        "summary": {
            "target_status": TARGET_RESULT,
            "aggregated_proof_object_status": AGGREGATED_PROOF_RESULT,
            "first_blocker": FIRST_BLOCKER,
            "slice_count": summary["slice_count"],
            "total_checked_rows": summary["total_checked_rows"],
            "composition_mutation_cases": source["case_count"],
            "composition_mutations_rejected": summary["mutations_rejected"],
            "block_receipt_commitment": source["block_receipt"]["block_receipt_commitment"],
            "statement_commitment": source["block_receipt"]["statement_commitment"],
            "range_policy_commitment": source["block_receipt"]["range_policy_commitment"],
            "aggregation_target_kind": TARGET_KIND,
            "aggregation_target_version": TARGET_VERSION,
            "blocked_before_metrics": True,
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_commitments(payload)
    _validate_draft_payload(payload)
    return payload


def build_payload() -> dict[str, Any]:
    return _build_payload_from_canonical_source(load_checked_block_receipt())


def _validate_source_descriptor(
    payload: dict[str, Any],
    *,
    source_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_block_receipt_evidence"), "source block receipt evidence")
    expect_key_set(
        descriptor,
        {
            "path",
            "file_sha256",
            "payload_sha256",
            "schema",
            "decision",
            "result",
            "block_receipt_commitment",
            "statement_commitment",
            "range_policy_commitment",
        },
        "source block receipt evidence",
    )
    path_value = descriptor.get("path")
    if not isinstance(path_value, str):
        raise D128AggregatedProofObjectFeasibilityError("source block receipt evidence path must be a string")
    expect_equal(path_value, relative_path(BLOCK_RECEIPT_EVIDENCE), "source block receipt evidence path")
    path = (ROOT / path_value).resolve()
    if path != BLOCK_RECEIPT_EVIDENCE.resolve():
        raise D128AggregatedProofObjectFeasibilityError("source block receipt evidence path mismatch")
    if source_override is None:
        source = load_checked_block_receipt(path)
    else:
        # Mutation generation passes the already-validated canonical receipt so
        # each synthetic negative case does not re-run all six source validators.
        # Public validate_payload() still reloads and validates from disk.
        source = _validate_checked_block_receipt_payload(copy.deepcopy(source_override))
    expect_equal(descriptor.get("file_sha256"), file_sha256(path), "source block receipt file_sha256")
    expect_equal(descriptor.get("payload_sha256"), sha256_hex_json(source), "source block receipt payload_sha256")
    expect_equal(descriptor.get("schema"), source["schema"], "source block receipt schema")
    expect_equal(descriptor.get("decision"), source["decision"], "source block receipt decision")
    expect_equal(descriptor.get("result"), source["result"], "source block receipt result")
    receipt = require_object(source.get("block_receipt"), "source block receipt")
    expect_equal(
        descriptor.get("block_receipt_commitment"),
        receipt["block_receipt_commitment"],
        "source block receipt commitment",
    )
    expect_equal(descriptor.get("statement_commitment"), receipt["statement_commitment"], "source statement commitment")
    expect_equal(
        descriptor.get("range_policy_commitment"),
        receipt["range_policy_commitment"],
        "source range policy commitment",
    )
    return source


def _validate_public_inputs(payload: dict[str, Any], source: dict[str, Any]) -> None:
    expected = block_receipt_public_inputs(source)
    public_inputs = require_object(payload.get("block_receipt_public_inputs"), "block receipt public inputs")
    expect_equal(public_inputs, expected, "block receipt public inputs")
    for field in (
        "block_receipt_commitment",
        "statement_commitment",
        "range_policy_commitment",
        "slice_chain_commitment",
        "evidence_manifest_commitment",
        "input_activation_commitment",
        "output_activation_commitment",
    ):
        require_commitment(public_inputs.get(field), f"public input {field}")


def _validate_target_manifest(payload: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    target = aggregation_target_manifest(source)
    manifest = require_object(payload.get("aggregation_target_manifest"), "aggregation target manifest")
    expect_equal(manifest, target, "aggregation target manifest")
    expect_equal(
        require_commitment(payload.get("aggregation_target_commitment"), "aggregation target commitment"),
        blake2b_commitment(target, TARGET_DOMAIN),
        "aggregation target commitment",
    )
    checks = require_list(manifest.get("required_nested_verifier_checks"), "required nested verifier checks")
    if len(checks) != 6:
        raise D128AggregatedProofObjectFeasibilityError("required nested verifier check count mismatch")
    for expected_index, raw_check in enumerate(checks):
        check = require_object(raw_check, f"nested verifier check {expected_index}")
        expect_equal(check.get("index"), expected_index, f"nested verifier check {expected_index} index")
        require_commitment(check.get("proof_native_parameter_commitment"), "nested proof_native_parameter_commitment")
        require_commitment(check.get("public_instance_commitment"), "nested public_instance_commitment")
        require_commitment(check.get("statement_commitment"), "nested statement_commitment")
        row_count = require_int(check.get("row_count"), f"nested verifier check {expected_index} row_count")
        if row_count <= 0:
            raise D128AggregatedProofObjectFeasibilityError("nested verifier row_count must be positive")
    return target


def _validate_candidate_inventory(payload: dict[str, Any]) -> None:
    inventory = require_list(payload.get("candidate_inventory"), "candidate inventory")
    expected = candidate_inventory()
    expect_equal(inventory, expected, "candidate inventory")
    required_missing = 0
    for index, raw_item in enumerate(inventory):
        item = require_object(raw_item, f"candidate inventory item {index}")
        if require_bool(item.get("accepted_as_aggregated_proof_object"), "candidate accepted flag"):
            raise D128AggregatedProofObjectFeasibilityError("candidate inventory accepts a non-proof object")
        if item.get("classification") == "MISSING_REQUIRED_ARTIFACT":
            required_missing += 1
            if item.get("exists") is not False:
                raise D128AggregatedProofObjectFeasibilityError("required aggregated proof artifact now exists; rerun GO/NO-GO")
    if required_missing < 3:
        raise D128AggregatedProofObjectFeasibilityError("required aggregated proof artifact inventory too small")


def _validate_attempt(payload: dict[str, Any]) -> None:
    attempt = require_object(payload.get("proof_object_attempt"), "proof object attempt")
    expect_key_set(
        attempt,
        {
            "go_criterion",
            "aggregated_proof_object_claimed",
            "recursive_aggregation_claimed",
            "pcd_accumulator_claimed",
            "verifier_handle_claimed",
            "aggregation_target_commitment_bound_as_public_input",
            "block_receipt_commitment_bound_as_public_input",
            "statement_commitment_bound_as_public_input",
            "range_policy_commitment_bound_as_public_input",
            "aggregated_proof_artifacts",
            "verifier_handles",
            "proof_metrics",
            "missing_backend_features",
            "first_blocker",
            "blocked_before_metrics",
        },
        "proof object attempt",
    )
    for field in (
        "aggregated_proof_object_claimed",
        "recursive_aggregation_claimed",
        "pcd_accumulator_claimed",
        "verifier_handle_claimed",
        "aggregation_target_commitment_bound_as_public_input",
        "block_receipt_commitment_bound_as_public_input",
        "statement_commitment_bound_as_public_input",
        "range_policy_commitment_bound_as_public_input",
    ):
        if attempt.get(field) is not False:
            raise D128AggregatedProofObjectFeasibilityError(f"{field} claimed without checked aggregated proof object")
    if require_list(attempt.get("aggregated_proof_artifacts"), "aggregated proof artifacts"):
        raise D128AggregatedProofObjectFeasibilityError("aggregated proof artifact supplied to no-go feasibility gate")
    if require_list(attempt.get("verifier_handles"), "verifier handles"):
        raise D128AggregatedProofObjectFeasibilityError("verifier handle supplied to no-go feasibility gate")
    metrics = require_object(attempt.get("proof_metrics"), "proof metrics")
    expect_key_set(
        metrics,
        {"proof_size_bytes", "proof_generation_time_ms", "verifier_time_ms", "compressed_proof_size_bytes"},
        "proof metrics",
    )
    for field, value in metrics.items():
        if value is not None:
            raise D128AggregatedProofObjectFeasibilityError(f"{field} metric supplied before proof object exists")
    expect_equal(attempt.get("go_criterion"), GO_CRITERION, "go criterion")
    expect_equal(attempt.get("missing_backend_features"), MISSING_BACKEND_FEATURES, "missing backend features")
    expect_equal(attempt.get("first_blocker"), FIRST_BLOCKER, "first blocker")
    expect_equal(attempt.get("blocked_before_metrics"), True, "blocked before metrics")


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_cases = "cases" in payload
    has_case_count = "case_count" in payload
    has_all_rejected = "all_mutations_rejected" in payload
    has_inventory = "mutation_inventory" in payload
    if not (has_cases or has_case_count or has_all_rejected or has_inventory):
        raise D128AggregatedProofObjectFeasibilityError(
            "mutation metadata must include mutation_inventory, cases, case_count, and all_mutations_rejected"
        )
    if not (has_cases and has_case_count and has_all_rejected and has_inventory):
        raise D128AggregatedProofObjectFeasibilityError(
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
        expect_key_set(case, set(TSV_COLUMNS), f"mutation case {index}")
        if not isinstance(case["mutation"], str) or not case["mutation"]:
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} mutation must be a string")
        if not isinstance(case["surface"], str) or not case["surface"]:
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} surface must be a string")
        pair = (case["mutation"], case["surface"])
        if pair in seen_pairs:
            raise D128AggregatedProofObjectFeasibilityError(f"duplicate mutation case {index}")
        seen_pairs.add(pair)
        case_pairs.append(pair)
        expect_equal(case.get("baseline_result"), RESULT, f"mutation case {index} baseline_result")
        if not isinstance(case.get("mutated_accepted"), bool):
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} mutated_accepted must be boolean")
        if not isinstance(case.get("rejected"), bool):
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} rejected must be boolean")
        if case["rejected"] == case["mutated_accepted"]:
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} rejected/accepted fields are inconsistent")
        if not isinstance(case.get("rejection_layer"), str) or not case["rejection_layer"]:
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} rejection layer must be a string")
        if not isinstance(case.get("error"), str):
            raise D128AggregatedProofObjectFeasibilityError(f"mutation case {index} error must be a string")
        if case["rejected"]:
            computed_rejected += 1
    expect_equal(tuple(case_pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), len(cases), "mutation case_count")
    expect_equal(payload.get("all_mutations_rejected"), all(case["rejected"] for case in cases), "all mutations rejected")
    return len(cases), computed_rejected


def _validate_common_payload(
    payload: Any,
    *,
    source_override: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "d128 aggregated proof-object feasibility payload")
    expected_top = {
        "schema",
        "decision",
        "result",
        "issue",
        "aggregation_target_result",
        "aggregated_proof_object_result",
        "source_block_receipt_evidence",
        "block_receipt_public_inputs",
        "aggregation_target_manifest",
        "aggregation_target_commitment",
        "candidate_inventory",
        "proof_object_attempt",
        "summary",
        "non_claims",
        "validation_commands",
    }
    if "mutation_inventory" in payload or "cases" in payload or "case_count" in payload or "all_mutations_rejected" in payload:
        expected_top |= {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
    expect_key_set(payload, expected_top, "d128 aggregated proof-object feasibility payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("issue"), ISSUE, "issue")
    expect_equal(payload.get("aggregation_target_result"), TARGET_RESULT, "aggregation target result")
    expect_equal(payload.get("aggregated_proof_object_result"), AGGREGATED_PROOF_RESULT, "aggregated proof result")
    source = _validate_source_descriptor(payload, source_override=source_override)
    _validate_public_inputs(payload, source)
    _validate_target_manifest(payload, source)
    _validate_candidate_inventory(payload)
    _validate_attempt(payload)
    source_summary = require_object(source.get("summary"), "source block receipt summary")
    expected_summary = {
        "target_status": TARGET_RESULT,
        "aggregated_proof_object_status": AGGREGATED_PROOF_RESULT,
        "first_blocker": FIRST_BLOCKER,
        "slice_count": source_summary["slice_count"],
        "total_checked_rows": source_summary["total_checked_rows"],
        "composition_mutation_cases": source["case_count"],
        "composition_mutations_rejected": source_summary["mutations_rejected"],
        "block_receipt_commitment": source["block_receipt"]["block_receipt_commitment"],
        "statement_commitment": source["block_receipt"]["statement_commitment"],
        "range_policy_commitment": source["block_receipt"]["range_policy_commitment"],
        "aggregation_target_kind": TARGET_KIND,
        "aggregation_target_version": TARGET_VERSION,
        "blocked_before_metrics": True,
    }
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    return source, expected_summary


def _validate_draft_payload(payload: Any, *, source_override: dict[str, Any] | None = None) -> None:
    _, expected_summary = _validate_common_payload(payload, source_override=source_override)
    if "mutation_inventory" in payload or "cases" in payload or "case_count" in payload or "all_mutations_rejected" in payload:
        raise D128AggregatedProofObjectFeasibilityError("draft payload must not include mutation metadata")
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def validate_payload(payload: Any) -> None:
    _, expected_summary = _validate_common_payload(payload)
    case_count, rejected_count = _validate_case_metadata(require_object(payload, "payload"))
    if rejected_count != case_count:
        raise D128AggregatedProofObjectFeasibilityError("not all aggregated proof-object feasibility mutations rejected")
    expected_summary["mutation_cases"] = case_count
    expected_summary["mutations_rejected"] = rejected_count
    summary = require_object(payload.get("summary"), "summary")
    expect_equal(summary, expected_summary, "summary")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "source block receipt" in text or "file_sha" in text or "payload_sha" in text:
        return "source_block_receipt_evidence"
    if "aggregation target commitment" in text:
        return "aggregation_target_commitment"
    if "candidate inventory" in text or "required aggregated proof artifact" in text:
        return "candidate_inventory"
    if "proof" in text or "pcd" in text or "recursive" in text or "verifier handle" in text or "metric" in text or "blocker" in text:
        return "proof_object_attempt"
    if "aggregation target" in text or "nested verifier" in text or "public input" in text:
        return "aggregation_target_manifest"
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
        "source_block_receipt_decision_drift",
        "source_block_receipt_evidence",
        lambda p: p["source_block_receipt_evidence"].__setitem__("decision", "GO_FAKE_D128_BLOCK_RECEIPT"),
    )
    add(
        "block_receipt_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("block_receipt_commitment", "blake2b-256:" + "33" * 32),
    )
    add(
        "statement_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("statement_commitment", "blake2b-256:" + "44" * 32),
    )
    add(
        "input_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("input_activation_commitment", "blake2b-256:" + "55" * 32),
    )
    add(
        "output_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("output_activation_commitment", "blake2b-256:" + "66" * 32),
    )
    add(
        "range_policy_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("range_policy_commitment", "blake2b-256:" + "67" * 32),
    )
    add(
        "slice_chain_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("slice_chain_commitment", "blake2b-256:" + "77" * 32),
    )
    add(
        "evidence_manifest_commitment_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("evidence_manifest_commitment", "blake2b-256:" + "88" * 32),
    )
    add(
        "nested_verifier_check_removed",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["required_nested_verifier_checks"].pop(2),
    )
    add(
        "nested_verifier_check_reordered",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["required_nested_verifier_checks"].reverse(),
    )
    add(
        "nested_verifier_source_hash_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["required_nested_verifier_checks"][0].__setitem__(
            "source_payload_sha256",
            "99" * 32,
        ),
    )
    add(
        "nested_verifier_statement_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["required_nested_verifier_checks"][4].__setitem__(
            "statement_commitment",
            "blake2b-256:" + "aa" * 32,
        ),
    )
    add(
        "verifier_domain_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("verifier_domain", "ptvm:tampered-d128-outer-domain:v0"),
    )
    add(
        "required_backend_version_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"].__setitem__("required_backend_version", "stwo-d128-fake-v0"),
    )
    add(
        "composition_mutation_count_drift",
        "aggregation_target_manifest",
        lambda p: p["aggregation_target_manifest"]["composition_evidence"].__setitem__("mutations_rejected", 19),
    )
    add(
        "candidate_inventory_acceptance_relabel",
        "candidate_inventory",
        lambda p: p["candidate_inventory"][0].__setitem__("accepted_as_aggregated_proof_object", True),
    )
    add(
        "candidate_inventory_file_sha256_tampered",
        "candidate_inventory",
        lambda p: p["candidate_inventory"][0].__setitem__("file_sha256", "00" * 32),
    )
    add(
        "candidate_inventory_required_artifact_removed",
        "candidate_inventory",
        lambda p: p["candidate_inventory"].pop(),
    )
    add(
        "aggregated_proof_claimed_without_artifact",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("aggregated_proof_object_claimed", True),
    )
    add(
        "recursive_claimed_without_artifact",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("recursive_aggregation_claimed", True),
    )
    add(
        "pcd_claimed_without_artifact",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("pcd_accumulator_claimed", True),
    )
    add(
        "verifier_handle_claimed_without_artifact",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("verifier_handle_claimed", True),
    )
    add(
        "aggregation_target_public_input_claimed_without_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__(
            "aggregation_target_commitment_bound_as_public_input",
            True,
        ),
    )
    add(
        "block_receipt_public_input_claimed_without_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("block_receipt_commitment_bound_as_public_input", True),
    )
    add(
        "statement_public_input_claimed_without_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("statement_commitment_bound_as_public_input", True),
    )
    add(
        "range_policy_public_input_claimed_without_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("range_policy_commitment_bound_as_public_input", True),
    )
    add(
        "invented_aggregated_proof_artifact",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"]["aggregated_proof_artifacts"].append(
            {"path": "docs/engineering/evidence/fake-d128-aggregated-proof.json", "commitment": "blake2b-256:" + "bb" * 32}
        ),
    )
    add(
        "proof_size_metric_smuggled_before_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"]["proof_metrics"].__setitem__("proof_size_bytes", 1234),
    )
    add(
        "verifier_time_metric_smuggled_before_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"]["proof_metrics"].__setitem__("verifier_time_ms", 1.23),
    )
    add(
        "proof_generation_time_metric_smuggled_before_proof",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"]["proof_metrics"].__setitem__("proof_generation_time_ms", 4.56),
    )
    add(
        "first_blocker_removed",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"].__setitem__("first_blocker", ""),
    )
    add(
        "missing_backend_feature_removed",
        "proof_object_attempt",
        lambda p: p["proof_object_attempt"]["missing_backend_features"].pop(),
    )
    add("decision_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("decision", "GO_FAKE_D128_AGGREGATED_PROOF"))
    add("result_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("result", "GO"))
    add(
        "non_claims_removed",
        "parser_or_schema",
        lambda p: p.__setitem__("non_claims", []),
        refresh=False,
    )
    add(
        "validation_command_drift",
        "parser_or_schema",
        lambda p: p["validation_commands"].__setitem__(0, "python3 scripts/fake_d128_aggregation.py"),
    )
    return cases


def mutation_cases(
    baseline: dict[str, Any] | None = None,
    *,
    source_override: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    _validate_draft_payload(baseline, source_override=source_override)
    cases = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            _validate_draft_payload(mutated, source_override=source_override)
            accepted = True
            error = ""
            layer = "accepted"
        except D128AggregatedProofObjectFeasibilityError as err:
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
    source = load_checked_block_receipt()
    payload = _build_payload_from_canonical_source(source)
    cases = mutation_cases(payload, source_override=source)
    result = copy.deepcopy(payload)
    result["mutation_inventory"] = expected_mutation_inventory()
    result["case_count"] = len(cases)
    result["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    result["cases"] = cases
    result["summary"]["mutation_cases"] = len(cases)
    result["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(result)
    if not result["all_mutations_rejected"]:
        raise D128AggregatedProofObjectFeasibilityError("not all aggregated proof-object feasibility mutations rejected")
    return result


def to_tsv(payload: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: case[key] for key in TSV_COLUMNS} for case in payload["cases"])
    return buffer.getvalue()


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise D128AggregatedProofObjectFeasibilityError(f"output path must not be a symlink: {path}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128AggregatedProofObjectFeasibilityError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128AggregatedProofObjectFeasibilityError(f"output path must not be a directory: {path}")
    parent = resolved.parent
    if parent.exists() and not parent.is_dir():
        raise D128AggregatedProofObjectFeasibilityError(f"output parent is not a directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _atomic_write_text(path: pathlib.Path, text: str) -> pathlib.Path:
    resolved = _assert_repo_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=resolved.parent, delete=False) as handle:
        tmp = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(tmp, resolved)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return resolved


def _fsync_parent_directories(paths: list[pathlib.Path]) -> None:
    seen: set[pathlib.Path] = set()
    for path in paths:
        parent = path.resolve().parent
        if parent in seen:
            continue
        seen.add(parent)
        flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
        try:
            fd = os.open(parent, flags)
        except OSError:
            continue
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    written: list[pathlib.Path] = []
    if json_path is not None:
        written.append(_atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"))
    if tsv_path is not None:
        written.append(_atomic_write_text(tsv_path, to_tsv(payload)))
    _fsync_parent_directories(written)


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
