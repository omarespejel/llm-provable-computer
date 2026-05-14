#!/usr/bin/env python3
"""Classify the native d128 two-slice outer proof backend route.

Issue #581 asks for the smallest honest native outer-proof backend over the two
selected d128 slice checks:

* rmsnorm_public_rows
* rmsnorm_projection_bridge

This gate is intentionally strict.  It keeps the already-useful positives
visible, but it refuses to promote an inner Stwo proof, non-recursive
accumulator, compressed transcript, external SNARK receipt, or package byte
count into the missing native Stwo outer proof object.
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
import re
import stat as stat_module
import sys
import tempfile
import tomllib
from functools import lru_cache
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

ACCUMULATOR_EVIDENCE = EVIDENCE_DIR / "zkai-d128-two-slice-accumulator-backend-2026-05.json"
RECURSIVE_PCD_EVIDENCE = EVIDENCE_DIR / "zkai-d128-two-slice-recursive-pcd-backend-2026-05.json"
COMPRESSION_EVIDENCE = EVIDENCE_DIR / "zkai-d128-proof-native-two-slice-compression-2026-05.json"
SNARK_RECEIPT_EVIDENCE = EVIDENCE_DIR / "zkai-d128-snark-ivc-statement-receipt-2026-05.json"
BLOCK_ROUTE_EVIDENCE = EVIDENCE_DIR / "zkai-native-d128-block-proof-object-route-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-backend-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-d128-two-slice-outer-backend-2026-05.tsv"

SCHEMA = "zkai-native-d128-two-slice-outer-backend-gate-v1"
DECISION = "NO_GO_EXECUTABLE_NATIVE_D128_TWO_SLICE_OUTER_PROOF_BACKEND_MISSING"
RESULT = "BOUNDED_NO_GO_WITH_INNER_STWO_AND_COMPACT_PACKAGE_SIGNAL"
ISSUE = 581
NATIVE_OUTER_BACKEND_RESULT = "NO_GO_NATIVE_STWO_OUTER_VERIFIER_EXECUTION_BACKEND_MISSING"
INNER_STWO_BASELINE_RESULT = "GO_TWO_SELECTED_INNER_STWO_SLICE_PROOFS_EXIST"
CLAIM_BOUNDARY = (
    "INNER_STWO_PROOFS_ACCUMULATORS_COMPRESSION_AND_EXTERNAL_RECEIPTS_EXIST_"
    "NATIVE_TWO_SLICE_OUTER_PROOF_BACKEND_MISSING"
)

EXPECTED_SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")
EXPECTED_SELECTED_ROWS = 256
EXPECTED_SLICE_ROWS = 128
EXPECTED_ACCUMULATOR_COMMITMENT = "blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d"
EXPECTED_ACCUMULATOR_VERIFIER_HANDLE = "blake2b-256:8dd18b7b5b8d0a5399535f0a02f9a1fe4128211bad8f3e69bb44c92cdf07a131"
EXPECTED_TWO_SLICE_TARGET_COMMITMENT = "blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6"
EXPECTED_COMPRESSED_ARTIFACT_BYTES = 4_435
EXPECTED_SOURCE_ACCUMULATOR_BYTES = 8_822
EXPECTED_COMPRESSION_RATIO = 0.50272
EXPECTED_EXTERNAL_SNARK_PROOF_BYTES = 802
EXPECTED_EXTERNAL_SNARK_PUBLIC_SIGNAL_BYTES = 1_389
EXPECTED_EXTERNAL_SNARK_VK_BYTES = 5_854
EXPECTED_PACKAGE_WITHOUT_VK_BYTES = 4_752
EXPECTED_PACKAGE_WITH_VK_BYTES = 10_608
EXPECTED_NANOZK_REPORTED_BYTES = 6_900
EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK = 0.688696
EXPECTED_PACKAGE_WITH_VK_VS_NANOZK = 1.537391
EXPECTED_VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
EXPECTED_REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
EXPECTED_SELECTED_PROOF_BACKEND_VERSIONS = (
    {
        "slice_id": "rmsnorm_public_rows",
        "proof_backend_version": "stwo-d128-rmsnorm-public-row-air-proof-v3",
    },
    {
        "slice_id": "rmsnorm_projection_bridge",
        "proof_backend_version": "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
    },
)
EXPECTED_BOUND_FIELDS = (
    "selected_slice_ids",
    "selected_checked_rows",
    "two_slice_target_commitment",
    "accumulator_commitment",
    "accumulator_verifier_handle_commitment",
    "selected_source_evidence_hashes",
    "selected_slice_statement_commitments",
    "selected_slice_public_instance_commitments",
    "selected_slice_proof_native_parameter_commitments",
    "verifier_domain_labels",
    "required_backend_versions",
    "selected_slice_proof_backend_versions",
)
MAX_SOURCE_BYTES = 16 * 1024 * 1024

FIRST_BLOCKER = (
    "no parameterized Stwo AIR/verifier-execution route exists for the selected "
    "d128 rmsnorm_public_rows and rmsnorm_projection_bridge verifier checks"
)

GO_GATE = (
    "one executable native Stwo outer proof object exists for the two selected d128 "
    "slice-verifier checks; the local verifier accepts it; proof bytes are measured "
    "from that native object; and relabeling mutations reject changed slice IDs, "
    "source hashes, target commitment, verifier-domain labels, backend versions, "
    "and public-input ordering"
)

NO_GO_GATE = (
    "no native verifier-execution AIR/backend exists, or any candidate result is only "
    "an inner proof, non-recursive accumulator, compressed transcript, external SNARK "
    "receipt, package accounting row, or unmatched external benchmark row"
)

NEXT_BACKEND_STEP = (
    "build the native Stwo verifier-execution surface for the two selected slice "
    "verifiers before attempting a six-slice d128 block proof-size comparison"
)

MISSING_BACKEND_FEATURES = [
    "native Stwo outer AIR for rmsnorm_public_rows verifier execution",
    "native Stwo outer AIR for rmsnorm_projection_bridge verifier execution",
    "outer proof generator that consumes the two selected verifier transcripts",
    "outer verifier handle that binds two_slice_target_commitment",
    "public-input ordering for selected slice statements and selected source hashes",
    "backend-version and verifier-domain binding inside the outer statement",
    "proof-byte accounting measured from the native outer proof object",
    "fail-closed mutation tests for native outer-proof relabeling",
]

NON_CLAIMS = [
    "not a native d128 two-slice outer proof",
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched benchmark against NANOZK or another public zkML system",
    "not recursive aggregation or proof-carrying data",
    "not proof-size evidence for a native outer proof",
    "not verifier-time or prover-time evidence for a native outer proof",
    "not verification of the selected Stwo slice verifiers inside Stwo",
    "not full transformer inference",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_native_d128_two_slice_outer_backend_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_d128_two_slice_outer_backend_gate.py scripts/tests/test_zkai_native_d128_two_slice_outer_backend_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_d128_two_slice_outer_backend_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "name",
    "kind",
    "classification",
    "exists",
    "required_for_go",
    "rows",
    "bytes",
    "supports_native_outer_claim",
    "reason",
)

EXPECTED_MUTATION_INVENTORY = (
    ("source_accumulator_hash_drift", "source_artifacts"),
    ("source_recursive_result_changed_to_go", "source_artifacts"),
    ("source_compression_promoted_to_recursion", "source_artifacts"),
    ("source_snark_relabelled_as_native_stwo", "source_artifacts"),
    ("source_block_route_claim_changed_to_go", "source_artifacts"),
    ("source_payload_hash_drift", "source_artifacts"),
    ("inner_stwo_promoted_to_outer_backend", "candidate_inventory"),
    ("accumulator_promoted_to_native_outer_proof", "candidate_inventory"),
    ("compression_promoted_to_native_outer_proof", "candidate_inventory"),
    ("snark_receipt_promoted_to_native_outer_proof", "candidate_inventory"),
    ("required_backend_module_removed", "candidate_inventory"),
    ("candidate_file_hash_tampered", "candidate_inventory"),
    ("candidate_required_token_removed", "candidate_inventory"),
    ("native_outer_artifact_claimed", "native_outer_attempt"),
    ("local_verifier_handle_claimed", "native_outer_attempt"),
    ("public_input_binding_claimed", "native_outer_attempt"),
    ("native_proof_bytes_smuggled", "native_outer_attempt"),
    ("selected_slice_ids_reordered", "native_outer_attempt"),
    ("selected_checked_rows_drift", "native_outer_attempt"),
    ("target_commitment_drift", "native_outer_attempt"),
    ("accumulator_commitment_drift", "native_outer_attempt"),
    ("verifier_handle_commitment_drift", "native_outer_attempt"),
    ("required_bound_field_removed", "native_outer_attempt"),
    ("verifier_domain_label_drift", "native_outer_attempt"),
    ("backend_version_label_drift", "native_outer_attempt"),
    ("proof_backend_version_label_drift", "native_outer_attempt"),
    ("package_bytes_relabelled_as_native_proof_bytes", "claim_guard"),
    ("snark_bytes_relabelled_as_native_proof_bytes", "claim_guard"),
    ("matched_nanozk_claim_enabled", "claim_guard"),
    ("first_blocker_removed", "native_outer_attempt"),
    ("missing_backend_feature_removed", "native_outer_attempt"),
    ("go_gate_weakened", "native_outer_attempt"),
    ("decision_changed_to_go", "parser_or_schema"),
    ("result_changed_to_go", "parser_or_schema"),
    ("issue_changed", "parser_or_schema"),
    ("claim_boundary_changed", "parser_or_schema"),
    ("non_claim_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)

CANDIDATE_SPECS = (
    {
        "name": "rmsnorm_public_rows_inner_stwo_proof",
        "kind": "inner_slice_stwo_module",
        "path": "src/stwo_backend/d128_native_rmsnorm_public_row_proof.rs",
        "expected_exists": True,
        "required_for_go": False,
        "rows": EXPECTED_SLICE_ROWS,
        "bytes": None,
        "classification": "INNER_STWO_SLICE_PROOF_NOT_OUTER_VERIFIER_EXECUTION",
        "required_tokens": (
            "rust_fn:prove_zkai_d128_rmsnorm_public_row_envelope",
            "rust_fn:verify_zkai_d128_rmsnorm_public_row_envelope",
        ),
        "reason": "proves and verifies the selected RMSNorm slice, but does not prove that verifier inside a native outer proof",
    },
    {
        "name": "rmsnorm_projection_bridge_inner_stwo_proof",
        "kind": "inner_slice_stwo_module",
        "path": "src/stwo_backend/d128_native_rmsnorm_to_projection_bridge_proof.rs",
        "expected_exists": True,
        "required_for_go": False,
        "rows": EXPECTED_SLICE_ROWS,
        "bytes": None,
        "classification": "INNER_STWO_SLICE_PROOF_NOT_OUTER_VERIFIER_EXECUTION",
        "required_tokens": (
            "rust_fn:prove_zkai_d128_rmsnorm_to_projection_bridge_envelope",
            "rust_fn:verify_zkai_d128_rmsnorm_to_projection_bridge_envelope",
        ),
        "reason": "proves and verifies the selected bridge slice, but does not prove that verifier inside a native outer proof",
    },
    {
        "name": "two_slice_non_recursive_accumulator",
        "kind": "non_recursive_accumulator_evidence",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-accumulator-backend-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "rows": EXPECTED_SELECTED_ROWS,
        "bytes": None,
        "classification": "GO_NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF",
        "required_tokens": (),
        "reason": "binds selected statements and source hashes, but does not execute verifier constraints in an outer proof",
    },
    {
        "name": "two_slice_proof_native_transcript_compression",
        "kind": "compressed_public_input_contract",
        "path": "docs/engineering/evidence/zkai-d128-proof-native-two-slice-compression-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "rows": EXPECTED_SELECTED_ROWS,
        "bytes": EXPECTED_COMPRESSED_ARTIFACT_BYTES,
        "classification": "GO_TRANSCRIPT_COMPRESSION_NOT_OUTER_PROOF",
        "required_tokens": (),
        "reason": "compresses proof-native public inputs; it is not a native outer cryptographic proof object",
    },
    {
        "name": "external_groth16_statement_receipt",
        "kind": "external_snark_statement_receipt",
        "path": "docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "rows": None,
        "bytes": EXPECTED_EXTERNAL_SNARK_PROOF_BYTES,
        "classification": "GO_EXTERNAL_SNARK_RECEIPT_NOT_NATIVE_STWO",
        "required_tokens": (),
        "reason": "proves a statement contract with Groth16; it is external and does not make the selected Stwo verifier checks native",
    },
    {
        "name": "native_d128_block_route_no_go",
        "kind": "route_gate_evidence",
        "path": "docs/engineering/evidence/zkai-native-d128-block-proof-object-route-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "rows": None,
        "bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "classification": "NO_GO_BLOCK_ROUTE_BLOCKED_BY_TWO_SLICE_OUTER_BACKEND",
        "required_tokens": (),
        "reason": "records the compact package signal and blocks native d128 proof claims until this two-slice backend exists",
    },
    {
        "name": "stwo_dependency_surface",
        "kind": "dependency_surface",
        "path": "Cargo.toml",
        "expected_exists": True,
        "required_for_go": False,
        "rows": None,
        "bytes": None,
        "classification": "STWO_PROVER_AVAILABLE_NO_LOCAL_OUTER_VERIFIER_BACKEND",
        "required_tokens": (
            "toml_dependency:stwo.version=2.2.0",
            "toml_dependency_features:stwo=std,prover",
            "toml_feature_contains:stwo-backend=dep:stwo,dep:stwo-constraint-framework,dep:flate2",
        ),
        "reason": "the repository can build native Stwo slice proofs, but has no selected-verifier execution AIR for an outer proof",
    },
    {
        "name": "required_native_two_slice_outer_backend_module",
        "kind": "required_backend_module",
        "path": "src/stwo_backend/d128_native_two_slice_outer_backend.rs",
        "expected_exists": False,
        "required_for_go": True,
        "rows": None,
        "bytes": None,
        "classification": "MISSING_REQUIRED_NATIVE_OUTER_BACKEND",
        "required_tokens": (),
        "reason": "no executable native Stwo backend module exists for the two selected verifier checks",
    },
    {
        "name": "required_native_two_slice_outer_proof_artifact",
        "kind": "required_native_proof_artifact",
        "path": "docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-proof-2026-05.json",
        "expected_exists": False,
        "required_for_go": True,
        "rows": None,
        "bytes": None,
        "classification": "MISSING_REQUIRED_NATIVE_OUTER_PROOF_ARTIFACT",
        "required_tokens": (),
        "reason": "no checked native outer proof artifact exists for the selected two-slice target",
    },
    {
        "name": "required_native_two_slice_outer_verifier_handle",
        "kind": "required_native_verifier_handle",
        "path": "docs/engineering/evidence/zkai-native-d128-two-slice-outer-backend-verifier-2026-05.json",
        "expected_exists": False,
        "required_for_go": True,
        "rows": None,
        "bytes": None,
        "classification": "MISSING_REQUIRED_NATIVE_OUTER_VERIFIER_HANDLE",
        "required_tokens": (),
        "reason": "no local verifier handle exists for a native two-slice outer proof object",
    },
    {
        "name": "required_native_two_slice_outer_artifact_tests",
        "kind": "required_future_backend_test_surface",
        "path": "scripts/tests/test_zkai_native_d128_two_slice_outer_backend_proof.py",
        "expected_exists": False,
        "required_for_go": True,
        "rows": None,
        "bytes": None,
        "classification": "MISSING_REQUIRED_NATIVE_OUTER_MUTATION_TESTS",
        "required_tokens": (),
        "reason": "a future native GO must include fail-closed relabeling tests for the proof artifact",
    },
    {
        "name": "current_no_go_gate_tests",
        "kind": "current_no_go_audit_tests",
        "path": "scripts/tests/test_zkai_native_d128_two_slice_outer_backend_gate.py",
        "expected_exists": True,
        "required_for_go": False,
        "rows": None,
        "bytes": None,
        "classification": "NO_GO_AUDIT_TESTS_NOT_NATIVE_OUTER_PROOF_TESTS",
        "required_tokens": (
            "python_def:test_gate_records_native_outer_no_go_without_downgrading_inner_stwo",
            "python_def:test_rejects_native_outer_overclaims_and_metric_smuggling",
        ),
        "reason": "tests this route classifier and overclaim guardrails, not a future executable native outer proof",
    },
)


class NativeD128TwoSliceOuterBackendError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise NativeD128TwoSliceOuterBackendError(f"invalid JSON value: {err}") from err


def sha256_hex_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_hex_json(value: Any) -> str:
    return sha256_hex_bytes(canonical_json_bytes(value))


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_json_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in items:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def _open_repo_regular_file(path: pathlib.Path, max_bytes: int, *, layer: str) -> bytes:
    resolved = path.resolve(strict=False)
    root = ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as err:
        raise NativeD128TwoSliceOuterBackendError(f"path escapes repository: {path}", layer=layer) from err
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(resolved, flags)
    except OSError as err:
        raise NativeD128TwoSliceOuterBackendError(f"failed to open source file {path}: {err}", layer=layer) from err
    with os.fdopen(fd, "rb") as handle:
        stat = os.fstat(handle.fileno())
        if not stat_module.S_ISREG(stat.st_mode):
            raise NativeD128TwoSliceOuterBackendError(f"source file is not a regular file: {path}", layer=layer)
        if stat.st_size > max_bytes:
            raise NativeD128TwoSliceOuterBackendError(
                f"source file exceeds max size: got {stat.st_size} bytes, limit {max_bytes} bytes",
                layer=layer,
            )
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise NativeD128TwoSliceOuterBackendError(
            f"source file exceeds max size: got more than {max_bytes} bytes",
            layer=layer,
        )
    return data


def relative_path(path: pathlib.Path) -> str:
    return str(path.resolve(strict=False).relative_to(ROOT.resolve()))


def file_sha256(path: pathlib.Path, *, max_bytes: int = MAX_SOURCE_BYTES) -> str:
    return sha256_hex_bytes(_open_repo_regular_file(path, max_bytes, layer="candidate_inventory"))


def load_json(path: pathlib.Path, *, layer: str = "source_artifacts") -> dict[str, Any]:
    raw = _open_repo_regular_file(path, MAX_SOURCE_BYTES, layer=layer)
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise NativeD128TwoSliceOuterBackendError(f"failed to load JSON from {path}: {err}", layer=layer) from err
    if not isinstance(payload, dict):
        raise NativeD128TwoSliceOuterBackendError(f"source evidence must be a JSON object: {path}", layer=layer)
    return payload


def expect_equal(actual: Any, expected: Any, field: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise NativeD128TwoSliceOuterBackendError(f"{field} mismatch", layer=layer)


def expect_key_set(value: dict[str, Any], expected: set[str], field: str, *, layer: str = "parser_or_schema") -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise NativeD128TwoSliceOuterBackendError(
            f"{field} key set mismatch: missing={missing} extra={extra}",
            layer=layer,
        )


def require_object(value: Any, field: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be an object", layer=layer)
    return value


def require_list(value: Any, field: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be a list", layer=layer)
    return value


def require_bool(value: Any, field: str, *, layer: str = "parser_or_schema") -> bool:
    if not isinstance(value, bool):
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be a boolean", layer=layer)
    return value


def require_int(value: Any, field: str, *, layer: str = "parser_or_schema") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be an integer", layer=layer)
    return value


def require_str(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    if not isinstance(value, str) or not value:
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be a non-empty string", layer=layer)
    return value


def require_commitment(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    text = require_str(value, field, layer=layer)
    if not text.startswith("blake2b-256:"):
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be blake2b-256 domain-separated", layer=layer)
    digest = text.removeprefix("blake2b-256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise NativeD128TwoSliceOuterBackendError(f"{field} must be a 32-byte lowercase hex digest", layer=layer)
    return text


def source_descriptor(path: pathlib.Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(payload),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "result": payload.get("result"),
        "claim_boundary": payload.get("claim_boundary"),
    }


@lru_cache(maxsize=1)
def _source_descriptors_cached() -> tuple[tuple[str, tuple[tuple[str, Any], ...]], ...]:
    bundle: dict[str, dict[str, Any]] = {}
    for key, path in (
        ("accumulator", ACCUMULATOR_EVIDENCE),
        ("recursive_pcd", RECURSIVE_PCD_EVIDENCE),
        ("compression", COMPRESSION_EVIDENCE),
        ("snark_receipt", SNARK_RECEIPT_EVIDENCE),
        ("block_route", BLOCK_ROUTE_EVIDENCE),
    ):
        payload = load_json(path)
        bundle[key] = {
            "path": relative_path(path),
            "payload": payload,
            "descriptor": source_descriptor(path, payload),
        }
    validate_source_bundle(bundle)
    return tuple((key, tuple(bundle[key]["descriptor"].items())) for key in sorted(bundle))


def source_descriptors() -> list[dict[str, Any]]:
    return [dict(items) for _key, items in _source_descriptors_cached()]


def validate_source_bundle(bundle: dict[str, dict[str, Any]]) -> None:
    accumulator = require_object(bundle["accumulator"]["payload"], "accumulator source", layer="source_artifacts")
    acc_summary = require_object(accumulator.get("summary"), "accumulator summary", layer="source_artifacts")
    expect_equal(accumulator.get("schema"), "zkai-d128-two-slice-accumulator-backend-v1", "accumulator schema", layer="source_artifacts")
    expect_equal(accumulator.get("decision"), "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR_BACKEND", "accumulator decision", layer="source_artifacts")
    expect_equal(accumulator.get("accumulator_result"), "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR", "accumulator result", layer="source_artifacts")
    expect_equal(accumulator.get("claim_boundary"), "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF", "accumulator claim boundary", layer="source_artifacts")
    expect_equal(accumulator.get("all_mutations_rejected"), True, "accumulator mutations", layer="source_artifacts")
    expect_equal(acc_summary.get("selected_checked_rows"), EXPECTED_SELECTED_ROWS, "accumulator selected rows", layer="source_artifacts")
    expect_equal(tuple(acc_summary.get("selected_slice_ids", [])), EXPECTED_SELECTED_SLICE_IDS, "accumulator selected slices", layer="source_artifacts")
    expect_equal(acc_summary.get("two_slice_target_commitment"), EXPECTED_TWO_SLICE_TARGET_COMMITMENT, "accumulator target", layer="source_artifacts")
    expect_equal(acc_summary.get("accumulator_commitment"), EXPECTED_ACCUMULATOR_COMMITMENT, "accumulator commitment", layer="source_artifacts")
    expect_equal(acc_summary.get("verifier_handle_commitment"), EXPECTED_ACCUMULATOR_VERIFIER_HANDLE, "accumulator verifier handle", layer="source_artifacts")

    recursive = require_object(bundle["recursive_pcd"]["payload"], "recursive source", layer="source_artifacts")
    recursive_summary = require_object(recursive.get("summary"), "recursive summary", layer="source_artifacts")
    expect_equal(recursive.get("schema"), "zkai-d128-two-slice-recursive-pcd-backend-gate-v1", "recursive schema", layer="source_artifacts")
    expect_equal(recursive.get("decision"), "NO_GO_D128_TWO_SLICE_RECURSIVE_PCD_BACKEND_UNAVAILABLE", "recursive decision", layer="source_artifacts")
    expect_equal(recursive.get("recursive_or_pcd_result"), "NO_GO_EXECUTABLE_RECURSIVE_PCD_OUTER_PROOF_BACKEND_MISSING", "recursive result", layer="source_artifacts")
    expect_equal(recursive.get("all_mutations_rejected"), True, "recursive mutations", layer="source_artifacts")
    expect_equal(recursive_summary.get("two_slice_target_commitment"), EXPECTED_TWO_SLICE_TARGET_COMMITMENT, "recursive target", layer="source_artifacts")
    expect_equal(recursive_summary.get("selected_checked_rows"), EXPECTED_SELECTED_ROWS, "recursive rows", layer="source_artifacts")

    compression = require_object(bundle["compression"]["payload"], "compression source", layer="source_artifacts")
    compression_summary = require_object(compression.get("summary"), "compression summary", layer="source_artifacts")
    metrics = require_object(compression_summary.get("compression_metrics"), "compression metrics", layer="source_artifacts")
    expect_equal(compression.get("schema"), "zkai-d128-proof-native-two-slice-compression-gate-v1", "compression schema", layer="source_artifacts")
    expect_equal(compression.get("compression_result"), "GO_PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION", "compression result", layer="source_artifacts")
    expect_equal(compression.get("recursive_or_pcd_result"), "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING", "compression recursive status", layer="source_artifacts")
    expect_equal(compression.get("claim_boundary"), "PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION", "compression claim boundary", layer="source_artifacts")
    expect_equal(compression.get("all_mutations_rejected"), True, "compression mutations", layer="source_artifacts")
    expect_equal(compression_summary.get("selected_checked_rows"), EXPECTED_SELECTED_ROWS, "compression rows", layer="source_artifacts")
    expect_equal(compression_summary.get("two_slice_target_commitment"), EXPECTED_TWO_SLICE_TARGET_COMMITMENT, "compression target", layer="source_artifacts")
    expect_equal(metrics.get("compressed_artifact_serialized_bytes"), EXPECTED_COMPRESSED_ARTIFACT_BYTES, "compressed bytes", layer="source_artifacts")
    expect_equal(metrics.get("source_accumulator_artifact_serialized_bytes"), EXPECTED_SOURCE_ACCUMULATOR_BYTES, "source accumulator bytes", layer="source_artifacts")
    expect_equal(metrics.get("artifact_bytes_ratio_vs_source_accumulator"), EXPECTED_COMPRESSION_RATIO, "compression ratio", layer="source_artifacts")

    snark = require_object(bundle["snark_receipt"]["payload"], "snark source", layer="source_artifacts")
    snark_metrics = require_object(snark.get("receipt_metrics"), "snark metrics", layer="source_artifacts")
    expect_equal(snark.get("schema"), "zkai-d128-snark-ivc-statement-receipt-gate-v1", "snark schema", layer="source_artifacts")
    expect_equal(snark.get("decision"), "GO_D128_SNARK_STATEMENT_RECEIPT_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT", "snark decision", layer="source_artifacts")
    expect_equal(snark.get("claim_boundary"), "SNARK_STATEMENT_RECEIPT_BINDS_D128_TWO_SLICE_PUBLIC_INPUT_CONTRACT_NOT_RECURSION", "snark claim boundary", layer="source_artifacts")
    expect_equal(snark.get("all_mutations_rejected"), True, "snark mutations", layer="source_artifacts")
    expect_equal(snark_metrics.get("proof_size_bytes"), EXPECTED_EXTERNAL_SNARK_PROOF_BYTES, "snark proof bytes", layer="source_artifacts")
    expect_equal(snark_metrics.get("public_signals_bytes"), EXPECTED_EXTERNAL_SNARK_PUBLIC_SIGNAL_BYTES, "snark public bytes", layer="source_artifacts")
    expect_equal(snark_metrics.get("verification_key_bytes"), EXPECTED_EXTERNAL_SNARK_VK_BYTES, "snark vk bytes", layer="source_artifacts")

    block = require_object(bundle["block_route"]["payload"], "block route source", layer="source_artifacts")
    block_summary = require_object(block.get("summary"), "block route summary", layer="source_artifacts")
    expect_equal(block.get("schema"), "zkai-native-d128-block-proof-object-route-v1", "block route schema", layer="source_artifacts")
    expect_equal(block.get("decision"), "NO_GO_EXECUTABLE_NATIVE_D128_BLOCK_OUTER_PROOF_BACKEND_MISSING", "block route decision", layer="source_artifacts")
    expect_equal(block_summary.get("native_block_proof_object_status"), "NO_GO_EXECUTABLE_NATIVE_D128_BLOCK_OUTER_PROOF_BACKEND_MISSING", "block route native status", layer="source_artifacts")
    expect_equal(block_summary.get("two_slice_outer_target_rows"), EXPECTED_SELECTED_ROWS, "block route two-slice rows", layer="source_artifacts")
    expect_equal(block_summary.get("package_without_vk_bytes"), EXPECTED_PACKAGE_WITHOUT_VK_BYTES, "package without VK", layer="source_artifacts")
    expect_equal(block_summary.get("package_with_vk_bytes"), EXPECTED_PACKAGE_WITH_VK_BYTES, "package with VK", layer="source_artifacts")
    expect_equal(block_summary.get("package_without_vk_vs_nanozk_reported_ratio"), EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK, "package ratio", layer="source_artifacts")
    expect_equal(block_summary.get("package_with_vk_vs_nanozk_reported_ratio"), EXPECTED_PACKAGE_WITH_VK_VS_NANOZK, "package with VK ratio", layer="source_artifacts")
    expect_equal(block.get("all_mutations_rejected"), True, "block route mutations", layer="source_artifacts")


def toml_data(raw: str) -> dict[str, Any]:
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as err:
        raise NativeD128TwoSliceOuterBackendError(f"failed to parse TOML: {err}", layer="candidate_inventory") from err
    if not isinstance(data, dict):
        raise NativeD128TwoSliceOuterBackendError("TOML root must be an object", layer="candidate_inventory")
    return data


def required_token_present(raw: str, token: str) -> bool:
    if token.startswith("rust_fn:"):
        name = re.escape(token.removeprefix("rust_fn:"))
        return re.search(rf"(?m)^\s*pub\s+fn\s+{name}\s*\(", raw) is not None
    if token.startswith("python_def:"):
        name = re.escape(token.removeprefix("python_def:"))
        return re.search(rf"(?m)^\s*def\s+{name}\s*\(", raw) is not None
    if token.startswith("toml_dependency:"):
        spec = token.removeprefix("toml_dependency:")
        dep_name, raw_expected = spec.split(".", maxsplit=1)
        field, expected = raw_expected.split("=", maxsplit=1)
        dependency = toml_data(raw).get("dependencies", {}).get(dep_name)
        if isinstance(dependency, str):
            return field == "version" and dependency == expected
        if isinstance(dependency, dict):
            return dependency.get(field) == expected
        return False
    if token.startswith("toml_dependency_features:"):
        spec = token.removeprefix("toml_dependency_features:")
        dep_name, raw_features = spec.split("=", maxsplit=1)
        dependency = toml_data(raw).get("dependencies", {}).get(dep_name)
        features = dependency.get("features") if isinstance(dependency, dict) else None
        if not isinstance(features, list):
            return False
        return set(raw_features.split(",")).issubset(set(features))
    if token.startswith("toml_feature_contains:"):
        spec = token.removeprefix("toml_feature_contains:")
        feature_name, raw_members = spec.split("=", maxsplit=1)
        members = toml_data(raw).get("features", {}).get(feature_name)
        if not isinstance(members, list):
            return False
        return set(raw_members.split(",")).issubset(set(members))
    raise NativeD128TwoSliceOuterBackendError(f"unsupported required token matcher: {token}", layer="candidate_inventory")


def candidate_file_info(path_text: str, required_tokens: tuple[str, ...]) -> dict[str, Any]:
    path = ROOT / path_text
    if not path.exists():
        return {
            "exists": False,
            "file_sha256": None,
            "required_tokens": list(required_tokens),
            "required_tokens_present": None,
            "missing_required_tokens": None,
        }
    data = _open_repo_regular_file(path, MAX_SOURCE_BYTES, layer="candidate_inventory")
    missing: list[str] = []
    if required_tokens:
        raw = data.decode("utf-8", errors="replace")
        missing = [token for token in required_tokens if not required_token_present(raw, token)]
    return {
        "exists": True,
        "file_sha256": sha256_hex_bytes(data),
        "required_tokens": list(required_tokens),
        "required_tokens_present": len(missing) == 0 if required_tokens else None,
        "missing_required_tokens": missing if required_tokens else None,
    }


@lru_cache(maxsize=1)
def _candidate_inventory_cached() -> tuple[tuple[tuple[str, Any], ...], ...]:
    inventory: list[dict[str, Any]] = []
    for spec in CANDIDATE_SPECS:
        item = {
            "name": spec["name"],
            "kind": spec["kind"],
            "path": spec["path"],
            "expected_exists": spec["expected_exists"],
            "required_for_go": spec["required_for_go"],
            "classification": spec["classification"],
            "rows": spec["rows"],
            "bytes": spec["bytes"],
            "supports_native_outer_claim": False,
            "reason": spec["reason"],
        }
        item.update(candidate_file_info(spec["path"], tuple(spec["required_tokens"])))
        inventory.append(item)
    return tuple(tuple(item.items()) for item in inventory)


def candidate_inventory() -> list[dict[str, Any]]:
    return copy.deepcopy([dict(item) for item in _candidate_inventory_cached()])


def native_outer_attempt() -> dict[str, Any]:
    return {
        "go_gate": GO_GATE,
        "no_go_gate": NO_GO_GATE,
        "first_blocker": FIRST_BLOCKER,
        "next_backend_step": NEXT_BACKEND_STEP,
        "native_outer_backend_result": NATIVE_OUTER_BACKEND_RESULT,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "two_slice_target_commitment": EXPECTED_TWO_SLICE_TARGET_COMMITMENT,
        "accumulator_commitment": EXPECTED_ACCUMULATOR_COMMITMENT,
        "accumulator_verifier_handle_commitment": EXPECTED_ACCUMULATOR_VERIFIER_HANDLE,
        "required_bound_fields": list(EXPECTED_BOUND_FIELDS),
        "verifier_domain_labels": [
            {
                "slice_id": "rmsnorm_public_rows",
                "verifier_domain": EXPECTED_VERIFIER_DOMAIN,
            },
            {
                "slice_id": "rmsnorm_projection_bridge",
                "verifier_domain": EXPECTED_VERIFIER_DOMAIN,
            },
        ],
        "required_backend_versions": [
            {
                "slice_id": "rmsnorm_public_rows",
                "required_backend_version": EXPECTED_REQUIRED_BACKEND_VERSION,
            },
            {
                "slice_id": "rmsnorm_projection_bridge",
                "required_backend_version": EXPECTED_REQUIRED_BACKEND_VERSION,
            },
        ],
        "selected_slice_proof_backend_versions": list(EXPECTED_SELECTED_PROOF_BACKEND_VERSIONS),
        "attempt": {
            "native_outer_proof_artifact_exists": False,
            "native_outer_verifier_handle_exists": False,
            "native_outer_public_input_binding_executable": False,
            "native_outer_proof_bytes": None,
            "proof_metrics_enabled": False,
            "blocked_before_native_proof_bytes": True,
            "first_blocker": FIRST_BLOCKER,
            "missing_backend_features": copy.deepcopy(MISSING_BACKEND_FEATURES),
        },
    }


def claim_guard() -> dict[str, Any]:
    return {
        "native_two_slice_outer_proof_exists": False,
        "native_two_slice_outer_proof_bytes": None,
        "native_outer_proof_size_claim_allowed": False,
        "inner_stwo_proofs_are_outer_proof": False,
        "accumulator_is_outer_proof": False,
        "compressed_transcript_is_outer_proof": False,
        "external_snark_receipt_is_native_stwo": False,
        "package_bytes_are_native_proof_bytes": False,
        "snark_bytes_are_native_proof_bytes": False,
        "matched_nanozk_claim_allowed": False,
    }


def summary(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    missing_required = [item["name"] for item in inventory if item["required_for_go"] and not item["exists"]]
    available_not_native = [
        item["name"]
        for item in inventory
        if item["exists"] and item["classification"] != "NO_GO_AUDIT_TESTS_NOT_NATIVE_OUTER_PROOF_TESTS"
    ]
    return {
        "issue": ISSUE,
        "decision": DECISION,
        "result": RESULT,
        "inner_stwo_baseline_result": INNER_STWO_BASELINE_RESULT,
        "native_outer_backend_result": NATIVE_OUTER_BACKEND_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "two_slice_target_commitment": EXPECTED_TWO_SLICE_TARGET_COMMITMENT,
        "accumulator_commitment": EXPECTED_ACCUMULATOR_COMMITMENT,
        "accumulator_verifier_handle_commitment": EXPECTED_ACCUMULATOR_VERIFIER_HANDLE,
        "source_accumulator_artifact_bytes": EXPECTED_SOURCE_ACCUMULATOR_BYTES,
        "compressed_artifact_bytes": EXPECTED_COMPRESSED_ARTIFACT_BYTES,
        "compressed_artifact_vs_source_ratio": EXPECTED_COMPRESSION_RATIO,
        "external_snark_proof_bytes": EXPECTED_EXTERNAL_SNARK_PROOF_BYTES,
        "external_snark_public_signal_bytes": EXPECTED_EXTERNAL_SNARK_PUBLIC_SIGNAL_BYTES,
        "external_snark_vk_bytes": EXPECTED_EXTERNAL_SNARK_VK_BYTES,
        "package_without_vk_bytes": EXPECTED_PACKAGE_WITHOUT_VK_BYTES,
        "package_without_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITHOUT_VK_VS_NANOZK,
        "package_with_vk_bytes": EXPECTED_PACKAGE_WITH_VK_BYTES,
        "package_with_vk_vs_nanozk_reported_ratio": EXPECTED_PACKAGE_WITH_VK_VS_NANOZK,
        "nanozk_reported_block_proof_bytes_decimal": EXPECTED_NANOZK_REPORTED_BYTES,
        "first_blocker": FIRST_BLOCKER,
        "go_gate": GO_GATE,
        "no_go_gate": NO_GO_GATE,
        "next_backend_step": NEXT_BACKEND_STEP,
        "available_surfaces_that_do_not_support_native_outer_claim": available_not_native,
        "required_go_artifacts_missing": missing_required,
        "missing_backend_feature_count": len(MISSING_BACKEND_FEATURES),
        "proof_metrics_enabled": False,
    }


def mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def build_core_payload() -> dict[str, Any]:
    inventory = candidate_inventory()
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "inner_stwo_baseline_result": INNER_STWO_BASELINE_RESULT,
        "native_outer_backend_result": NATIVE_OUTER_BACKEND_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": source_descriptors(),
        "candidate_inventory": inventory,
        "native_outer_attempt": native_outer_attempt(),
        "claim_guard": claim_guard(),
        "summary": summary(inventory),
        "missing_backend_features": copy.deepcopy(MISSING_BACKEND_FEATURES),
        "non_claims": copy.deepcopy(NON_CLAIMS),
        "validation_commands": copy.deepcopy(VALIDATION_COMMANDS),
        "mutation_inventory": mutation_inventory(),
    }
    validate_core_payload(payload)
    return payload


def _candidate_by_name(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for candidate in require_list(payload.get("candidate_inventory"), "candidate inventory", layer="candidate_inventory"):
        item = require_object(candidate, "candidate inventory item", layer="candidate_inventory")
        if item.get("name") == name:
            return item
    raise NativeD128TwoSliceOuterBackendError(f"candidate not found: {name}", layer="candidate_inventory")


def _source_by_path_suffix(payload: dict[str, Any], suffix: str) -> dict[str, Any]:
    for source in require_list(payload.get("source_artifacts"), "source artifacts", layer="source_artifacts"):
        item = require_object(source, "source artifact", layer="source_artifacts")
        path = require_str(item.get("path"), "source artifact path", layer="source_artifacts")
        if path.endswith(suffix):
            return item
    raise NativeD128TwoSliceOuterBackendError(f"source artifact not found: {suffix}", layer="source_artifacts")


def mutate_payload(payload: dict[str, Any], mutation: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if mutation == "source_accumulator_hash_drift":
        _source_by_path_suffix(mutated, "zkai-d128-two-slice-accumulator-backend-2026-05.json")["file_sha256"] = "0" * 64
    elif mutation == "source_recursive_result_changed_to_go":
        _source_by_path_suffix(mutated, "zkai-d128-two-slice-recursive-pcd-backend-2026-05.json")[
            "decision"
        ] = "GO_D128_TWO_SLICE_RECURSIVE_PCD_BACKEND"
    elif mutation == "source_compression_promoted_to_recursion":
        _source_by_path_suffix(mutated, "zkai-d128-proof-native-two-slice-compression-2026-05.json")[
            "claim_boundary"
        ] = "RECURSIVE_OR_NATIVE_OUTER_PROOF"
    elif mutation == "source_snark_relabelled_as_native_stwo":
        _source_by_path_suffix(mutated, "zkai-d128-snark-ivc-statement-receipt-2026-05.json")[
            "claim_boundary"
        ] = "NATIVE_STWO_OUTER_PROOF"
    elif mutation == "source_block_route_claim_changed_to_go":
        _source_by_path_suffix(mutated, "zkai-native-d128-block-proof-object-route-2026-05.json")[
            "decision"
        ] = "GO_NATIVE_D128_BLOCK_PROOF_OBJECT"
    elif mutation == "source_payload_hash_drift":
        _source_by_path_suffix(mutated, "zkai-native-d128-block-proof-object-route-2026-05.json")[
            "payload_sha256"
        ] = "2" * 64
    elif mutation == "inner_stwo_promoted_to_outer_backend":
        _candidate_by_name(mutated, "rmsnorm_public_rows_inner_stwo_proof")["classification"] = "GO_NATIVE_OUTER_BACKEND"
    elif mutation == "accumulator_promoted_to_native_outer_proof":
        _candidate_by_name(mutated, "two_slice_non_recursive_accumulator")["supports_native_outer_claim"] = True
    elif mutation == "compression_promoted_to_native_outer_proof":
        _candidate_by_name(mutated, "two_slice_proof_native_transcript_compression")["classification"] = "GO_NATIVE_OUTER_PROOF"
    elif mutation == "snark_receipt_promoted_to_native_outer_proof":
        _candidate_by_name(mutated, "external_groth16_statement_receipt")["classification"] = "GO_NATIVE_STWO_OUTER_PROOF"
    elif mutation == "required_backend_module_removed":
        mutated["candidate_inventory"] = [
            item
            for item in mutated["candidate_inventory"]
            if item["name"] != "required_native_two_slice_outer_backend_module"
        ]
    elif mutation == "candidate_file_hash_tampered":
        _candidate_by_name(mutated, "rmsnorm_projection_bridge_inner_stwo_proof")["file_sha256"] = "1" * 64
    elif mutation == "candidate_required_token_removed":
        _candidate_by_name(mutated, "current_no_go_gate_tests")["required_tokens"] = []
    elif mutation == "native_outer_artifact_claimed":
        mutated["native_outer_attempt"]["attempt"]["native_outer_proof_artifact_exists"] = True
    elif mutation == "local_verifier_handle_claimed":
        mutated["native_outer_attempt"]["attempt"]["native_outer_verifier_handle_exists"] = True
    elif mutation == "public_input_binding_claimed":
        mutated["native_outer_attempt"]["attempt"]["native_outer_public_input_binding_executable"] = True
    elif mutation == "native_proof_bytes_smuggled":
        mutated["native_outer_attempt"]["attempt"]["native_outer_proof_bytes"] = 4096
    elif mutation == "selected_slice_ids_reordered":
        mutated["native_outer_attempt"]["selected_slice_ids"] = [
            "rmsnorm_projection_bridge",
            "rmsnorm_public_rows",
        ]
    elif mutation == "selected_checked_rows_drift":
        mutated["native_outer_attempt"]["selected_checked_rows"] = 255
    elif mutation == "target_commitment_drift":
        mutated["native_outer_attempt"]["two_slice_target_commitment"] = "blake2b-256:" + "3" * 64
    elif mutation == "accumulator_commitment_drift":
        mutated["native_outer_attempt"]["accumulator_commitment"] = "blake2b-256:" + "4" * 64
    elif mutation == "verifier_handle_commitment_drift":
        mutated["native_outer_attempt"]["accumulator_verifier_handle_commitment"] = "blake2b-256:" + "5" * 64
    elif mutation == "required_bound_field_removed":
        mutated["native_outer_attempt"]["required_bound_fields"].remove("selected_source_evidence_hashes")
    elif mutation == "verifier_domain_label_drift":
        mutated["native_outer_attempt"]["verifier_domain_labels"][0]["verifier_domain"] = "ptvm:zkai:wrong:v1"
    elif mutation == "backend_version_label_drift":
        mutated["native_outer_attempt"]["required_backend_versions"][0][
            "required_backend_version"
        ] = "stwo-rmsnorm-swiglu-residual-d128-v2"
    elif mutation == "proof_backend_version_label_drift":
        mutated["native_outer_attempt"]["selected_slice_proof_backend_versions"][0][
            "proof_backend_version"
        ] = "stwo-d128-rmsnorm-public-row-air-proof-v4"
    elif mutation == "package_bytes_relabelled_as_native_proof_bytes":
        mutated["claim_guard"]["package_bytes_are_native_proof_bytes"] = True
    elif mutation == "snark_bytes_relabelled_as_native_proof_bytes":
        mutated["claim_guard"]["snark_bytes_are_native_proof_bytes"] = True
    elif mutation == "matched_nanozk_claim_enabled":
        mutated["claim_guard"]["matched_nanozk_claim_allowed"] = True
    elif mutation == "first_blocker_removed":
        mutated["native_outer_attempt"]["attempt"]["first_blocker"] = ""
    elif mutation == "missing_backend_feature_removed":
        mutated["native_outer_attempt"]["attempt"]["missing_backend_features"].pop()
    elif mutation == "go_gate_weakened":
        mutated["native_outer_attempt"]["go_gate"] = "one accumulator exists"
    elif mutation == "decision_changed_to_go":
        mutated["decision"] = "GO_NATIVE_D128_TWO_SLICE_OUTER_PROOF_BACKEND"
    elif mutation == "result_changed_to_go":
        mutated["result"] = "GO"
    elif mutation == "issue_changed":
        mutated["issue"] = 387
    elif mutation == "claim_boundary_changed":
        mutated["claim_boundary"] = "NATIVE_TWO_SLICE_OUTER_PROOF_EXISTS"
    elif mutation == "non_claim_removed":
        mutated["non_claims"].remove("not a native d128 two-slice outer proof")
    elif mutation == "validation_command_drift":
        mutated["validation_commands"][0] = "python3 scripts/fake.py"
    elif mutation == "unknown_top_level_field_added":
        mutated["invented_native_outer_metric"] = 1
    else:
        raise NativeD128TwoSliceOuterBackendError(f"unknown mutation: {mutation}")
    return mutated


SOURCE_DESCRIPTOR_KEYS = {"path", "file_sha256", "payload_sha256", "schema", "decision", "result", "claim_boundary"}
CANDIDATE_KEYS = {
    "name",
    "kind",
    "path",
    "expected_exists",
    "required_for_go",
    "classification",
    "rows",
    "bytes",
    "supports_native_outer_claim",
    "reason",
    "exists",
    "file_sha256",
    "required_tokens",
    "required_tokens_present",
    "missing_required_tokens",
}
ATTEMPT_KEYS = {
    "native_outer_proof_artifact_exists",
    "native_outer_verifier_handle_exists",
    "native_outer_public_input_binding_executable",
    "native_outer_proof_bytes",
    "proof_metrics_enabled",
    "blocked_before_native_proof_bytes",
    "first_blocker",
    "missing_backend_features",
}
NATIVE_OUTER_ATTEMPT_KEYS = {
    "go_gate",
    "no_go_gate",
    "first_blocker",
    "next_backend_step",
    "native_outer_backend_result",
    "selected_slice_ids",
    "selected_checked_rows",
    "two_slice_target_commitment",
    "accumulator_commitment",
    "accumulator_verifier_handle_commitment",
    "required_bound_fields",
    "verifier_domain_labels",
    "required_backend_versions",
    "selected_slice_proof_backend_versions",
    "attempt",
}
SUMMARY_KEYS = {
    "issue",
    "decision",
    "result",
    "inner_stwo_baseline_result",
    "native_outer_backend_result",
    "claim_boundary",
    "selected_slice_ids",
    "selected_checked_rows",
    "two_slice_target_commitment",
    "accumulator_commitment",
    "accumulator_verifier_handle_commitment",
    "source_accumulator_artifact_bytes",
    "compressed_artifact_bytes",
    "compressed_artifact_vs_source_ratio",
    "external_snark_proof_bytes",
    "external_snark_public_signal_bytes",
    "external_snark_vk_bytes",
    "package_without_vk_bytes",
    "package_without_vk_vs_nanozk_reported_ratio",
    "package_with_vk_bytes",
    "package_with_vk_vs_nanozk_reported_ratio",
    "nanozk_reported_block_proof_bytes_decimal",
    "first_blocker",
    "go_gate",
    "no_go_gate",
    "next_backend_step",
    "available_surfaces_that_do_not_support_native_outer_claim",
    "required_go_artifacts_missing",
    "missing_backend_feature_count",
    "proof_metrics_enabled",
}
CASE_KEYS = {"index", "mutation", "surface", "baseline_result", "mutated_accepted", "rejected", "rejection_layer", "error"}
CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "inner_stwo_baseline_result",
    "native_outer_backend_result",
    "claim_boundary",
    "source_artifacts",
    "candidate_inventory",
    "native_outer_attempt",
    "claim_guard",
    "summary",
    "missing_backend_features",
    "non_claims",
    "validation_commands",
    "mutation_inventory",
}
FINAL_KEYS = CORE_KEYS | {"cases", "case_count", "all_mutations_rejected"}


def validate_source_artifacts(value: Any) -> None:
    descriptors = require_list(value, "source artifacts", layer="source_artifacts")
    expected = source_descriptors()
    expect_equal(descriptors, expected, "source artifacts", layer="source_artifacts")
    for index, descriptor in enumerate(descriptors):
        item = require_object(descriptor, f"source artifact {index}", layer="source_artifacts")
        expect_key_set(item, SOURCE_DESCRIPTOR_KEYS, f"source artifact {index}", layer="source_artifacts")


def validate_candidate_inventory(value: Any) -> None:
    inventory = require_list(value, "candidate inventory", layer="candidate_inventory")
    expected = candidate_inventory()
    expect_equal(inventory, expected, "candidate inventory", layer="candidate_inventory")
    seen: set[str] = set()
    for index, item in enumerate(inventory):
        candidate = require_object(item, f"candidate inventory item {index}", layer="candidate_inventory")
        expect_key_set(candidate, CANDIDATE_KEYS, f"candidate inventory item {index}", layer="candidate_inventory")
        name = require_str(candidate["name"], f"candidate {index} name", layer="candidate_inventory")
        if name in seen:
            raise NativeD128TwoSliceOuterBackendError("duplicate candidate inventory name", layer="candidate_inventory")
        seen.add(name)
        require_bool(candidate["expected_exists"], f"candidate {name} expected_exists", layer="candidate_inventory")
        require_bool(candidate["required_for_go"], f"candidate {name} required_for_go", layer="candidate_inventory")
        require_bool(candidate["exists"], f"candidate {name} exists", layer="candidate_inventory")
        if candidate["exists"] != candidate["expected_exists"]:
            raise NativeD128TwoSliceOuterBackendError(f"candidate {name} existence changed; update gate", layer="candidate_inventory")
        if candidate["required_for_go"] and candidate["exists"]:
            raise NativeD128TwoSliceOuterBackendError(
                f"candidate {name} now exists; replace no-go with native proof validation",
                layer="candidate_inventory",
            )
        if candidate["supports_native_outer_claim"] is not False:
            raise NativeD128TwoSliceOuterBackendError(f"candidate {name} promoted to native outer claim", layer="candidate_inventory")
        tokens = require_list(candidate["required_tokens"], f"candidate {name} required tokens", layer="candidate_inventory")
        if tokens:
            expect_equal(candidate["required_tokens_present"], True, f"candidate {name} required tokens", layer="candidate_inventory")
            expect_equal(candidate["missing_required_tokens"], [], f"candidate {name} missing tokens", layer="candidate_inventory")


def validate_native_outer_attempt(value: Any) -> None:
    attempt = require_object(value, "native outer attempt", layer="native_outer_attempt")
    expect_key_set(attempt, NATIVE_OUTER_ATTEMPT_KEYS, "native outer attempt", layer="native_outer_attempt")
    expect_equal(attempt, native_outer_attempt(), "native outer attempt", layer="native_outer_attempt")
    require_commitment(attempt["two_slice_target_commitment"], "native target", layer="native_outer_attempt")
    require_commitment(attempt["accumulator_commitment"], "native accumulator", layer="native_outer_attempt")
    require_commitment(attempt["accumulator_verifier_handle_commitment"], "native verifier handle", layer="native_outer_attempt")
    inner = require_object(attempt["attempt"], "native attempt inner", layer="native_outer_attempt")
    expect_key_set(inner, ATTEMPT_KEYS, "native attempt inner", layer="native_outer_attempt")
    for field in (
        "native_outer_proof_artifact_exists",
        "native_outer_verifier_handle_exists",
        "native_outer_public_input_binding_executable",
        "proof_metrics_enabled",
    ):
        expect_equal(inner[field], False, f"native attempt {field}", layer="native_outer_attempt")
    expect_equal(inner["native_outer_proof_bytes"], None, "native proof bytes", layer="native_outer_attempt")
    expect_equal(inner["blocked_before_native_proof_bytes"], True, "blocked before proof bytes", layer="native_outer_attempt")
    expect_equal(inner["first_blocker"], FIRST_BLOCKER, "native first blocker", layer="native_outer_attempt")
    expect_equal(inner["missing_backend_features"], MISSING_BACKEND_FEATURES, "missing backend features", layer="native_outer_attempt")


def validate_claim_guard(value: Any) -> None:
    guard = require_object(value, "claim guard", layer="claim_guard")
    expect_equal(guard, claim_guard(), "claim guard", layer="claim_guard")


def validate_summary(value: Any, inventory: list[dict[str, Any]]) -> None:
    item = require_object(value, "summary", layer="summary")
    expect_key_set(item, SUMMARY_KEYS, "summary", layer="summary")
    expect_equal(item, summary(inventory), "summary", layer="summary")
    expect_equal(item["proof_metrics_enabled"], False, "summary proof metrics", layer="summary")
    expect_equal(item["required_go_artifacts_missing"], [
        "required_native_two_slice_outer_backend_module",
        "required_native_two_slice_outer_proof_artifact",
        "required_native_two_slice_outer_verifier_handle",
        "required_native_two_slice_outer_artifact_tests",
    ], "summary missing artifacts", layer="summary")


def validate_core_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise NativeD128TwoSliceOuterBackendError("payload must be a JSON object")
    allowed = FINAL_KEYS if any(key in payload for key in ("cases", "case_count", "all_mutations_rejected")) else CORE_KEYS
    expect_key_set(payload, allowed, "top-level payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["inner_stwo_baseline_result"], INNER_STWO_BASELINE_RESULT, "inner Stwo baseline")
    expect_equal(payload["native_outer_backend_result"], NATIVE_OUTER_BACKEND_RESULT, "native outer result", layer="native_outer_attempt")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    validate_source_artifacts(payload["source_artifacts"])
    validate_candidate_inventory(payload["candidate_inventory"])
    inventory = require_list(payload["candidate_inventory"], "candidate inventory", layer="candidate_inventory")
    validate_native_outer_attempt(payload["native_outer_attempt"])
    validate_claim_guard(payload["claim_guard"])
    validate_summary(payload["summary"], inventory)
    expect_equal(payload["missing_backend_features"], MISSING_BACKEND_FEATURES, "missing backend features", layer="native_outer_attempt")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non_claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation_commands")
    expect_equal(payload["mutation_inventory"], mutation_inventory(), "mutation inventory")


def classify_error(error: Exception) -> str:
    if isinstance(error, NativeD128TwoSliceOuterBackendError):
        return error.layer
    return "parser_or_schema"


def run_mutations(core_payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY):
        mutated = mutate_payload(core_payload, mutation)
        accepted = False
        error_text = ""
        layer = ""
        try:
            validate_core_payload(mutated)
            accepted = True
        except Exception as err:  # noqa: BLE001 - evidence records exact rejection.
            error_text = str(err)
            layer = classify_error(err)
        cases.append(
            {
                "index": index,
                "mutation": mutation,
                "surface": surface,
                "baseline_result": RESULT,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer if not accepted else "accepted",
                "error": error_text,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    core = build_core_payload()
    cases = run_mutations(core)
    payload = copy.deepcopy(core)
    payload["cases"] = cases
    payload["case_count"] = len(cases)
    payload["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    validate_payload(payload, expected_core=core, expected_cases=cases)
    return payload


def validate_cases(value: Any, expected_cases: list[dict[str, Any]]) -> None:
    cases = require_list(value, "cases")
    expect_equal(cases, expected_cases, "cases")
    for index, case in enumerate(cases):
        item = require_object(case, f"case {index}")
        expect_key_set(item, CASE_KEYS, f"case {index}")
        expect_equal(item["index"], index, f"case {index} index")
        require_str(item["mutation"], f"case {index} mutation")
        require_str(item["surface"], f"case {index} surface")
        require_bool(item["mutated_accepted"], f"case {index} accepted")
        require_bool(item["rejected"], f"case {index} rejected")
        if item["mutated_accepted"] or not item["rejected"]:
            raise NativeD128TwoSliceOuterBackendError(f"mutation case {index} was accepted")
        require_str(item["rejection_layer"], f"case {index} layer")
        require_str(item["error"], f"case {index} error")


def validate_payload(
    payload: dict[str, Any],
    *,
    expected_core: dict[str, Any] | None = None,
    expected_cases: list[dict[str, Any]] | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise NativeD128TwoSliceOuterBackendError("payload must be a JSON object")
    expect_key_set(payload, FINAL_KEYS, "top-level payload")
    validate_core_payload(payload)
    if expected_core is None:
        expected_core = build_core_payload()
    if expected_cases is None:
        expected_cases = run_mutations(expected_core)
    validate_cases(payload["cases"], expected_cases)
    expect_equal(payload["case_count"], len(expected_cases), "case_count")
    expect_equal(payload["all_mutations_rejected"], True, "all_mutations_rejected")


def to_tsv(payload: dict[str, Any], *, validate: bool = True) -> str:
    if validate:
        validate_payload(payload)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for item in payload["candidate_inventory"]:
        writer.writerow({column: item[column] for column in TSV_COLUMNS})
    return output.getvalue()


def _safe_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_absolute():
        raise NativeD128TwoSliceOuterBackendError(f"output path must be repo-relative: {path}")
    pure = pathlib.PurePosixPath(path.as_posix())
    if path.as_posix() != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise NativeD128TwoSliceOuterBackendError(f"output path must be repo-relative without traversal: {path}")
    candidate = ROOT.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise NativeD128TwoSliceOuterBackendError(f"output path escapes repository: {path}") from err
    return candidate


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs: list[tuple[pathlib.Path, bytes]] = []
    if json_path is not None:
        outputs.append((_safe_output_path(json_path), json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"))
    if tsv_path is not None:
        outputs.append((_safe_output_path(tsv_path), to_tsv(payload, validate=False).encode("utf-8")))
    if not outputs:
        raise NativeD128TwoSliceOuterBackendError("at least one output path is required")
    resolved_outputs = [path.resolve(strict=False) for path, _data in outputs]
    if len(resolved_outputs) != len(set(resolved_outputs)):
        raise NativeD128TwoSliceOuterBackendError("write-json and write-tsv output paths must be distinct")
    for path, data in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as handle:
            tmp = pathlib.Path(handle.name)
            handle.write(data)
        try:
            tmp.replace(path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = build_gate_result()
        if args.write_json or args.write_tsv:
            write_outputs(payload, args.write_json, args.write_tsv)
            print(
                json.dumps(
                    {
                        "decision": payload["decision"],
                        "native_outer_backend_result": payload["native_outer_backend_result"],
                        "selected_checked_rows": payload["summary"]["selected_checked_rows"],
                        "compressed_artifact_bytes": payload["summary"]["compressed_artifact_bytes"],
                        "external_snark_proof_bytes": payload["summary"]["external_snark_proof_bytes"],
                        "package_without_vk_bytes": payload["summary"]["package_without_vk_bytes"],
                        "mutations_rejected": payload["case_count"],
                    },
                    sort_keys=True,
                )
            )
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
    except NativeD128TwoSliceOuterBackendError as err:
        print(f"native d128 two-slice outer backend gate failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
