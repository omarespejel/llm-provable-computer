#!/usr/bin/env python3
"""Audit the d128 two-slice recursive/PCD backend route.

This gate answers issue #411.  It is deliberately stricter than the earlier
two-slice target and accumulator gates: a GO requires an executable recursive or
PCD outer proof object that proves the two selected d128 slice-verifier checks
inside one cryptographic object.  A verifier-facing non-recursive accumulator is
not enough.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import stat as stat_module
import sys
import tempfile
from collections.abc import Callable
from functools import lru_cache
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
ACCUMULATOR_SCRIPT = ROOT / "scripts" / "zkai_d128_two_slice_accumulator_backend_gate.py"
SOURCE_ACCUMULATOR_EVIDENCE = EVIDENCE_DIR / "zkai-d128-two-slice-accumulator-backend-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-two-slice-recursive-pcd-backend-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-two-slice-recursive-pcd-backend-2026-05.tsv"

SCHEMA = "zkai-d128-two-slice-recursive-pcd-backend-gate-v1"
DECISION = "NO_GO_D128_TWO_SLICE_RECURSIVE_PCD_BACKEND_UNAVAILABLE"
RESULT = "BOUNDED_NO_GO"
ISSUE = 411
ACCUMULATOR_BASELINE_RESULT = "GO_D128_TWO_SLICE_NON_RECURSIVE_ACCUMULATOR_BASELINE"
RECURSIVE_OR_PCD_RESULT = "NO_GO_EXECUTABLE_RECURSIVE_PCD_OUTER_PROOF_BACKEND_MISSING"
CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_AVAILABLE_RECURSIVE_PCD_BACKEND_MISSING"
EXPECTED_SOURCE_SCHEMA = "zkai-d128-two-slice-accumulator-backend-v1"
EXPECTED_SOURCE_DECISION = "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR_BACKEND"
EXPECTED_SOURCE_RESULT = "GO"
EXPECTED_SOURCE_ACCUMULATOR_RESULT = "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR"
EXPECTED_SOURCE_RECURSIVE_RESULT = "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING"
EXPECTED_SOURCE_CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF"
EXPECTED_SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")
EXPECTED_SELECTED_ROWS = 256
MAX_SOURCE_JSON_BYTES = 16 * 1024 * 1024

GO_CRITERION = (
    "one executable recursive or PCD outer proof artifact exists for the two selected d128 "
    "slice-verifier checks; a local verifier handle accepts it; and the artifact binds "
    "two_slice_target_commitment, selected slice statement commitments, and selected source "
    "evidence hashes as public inputs"
)

FIRST_BLOCKER = (
    "missing executable nested-verifier AIR/circuit or PCD backend that proves the two selected "
    "d128 slice verifiers inside one cryptographic outer object"
)

MISSING_BACKEND_FEATURES = [
    "nested verifier AIR/circuit for d128 rmsnorm_public_rows verifier",
    "nested verifier AIR/circuit for d128 rmsnorm_projection_bridge verifier",
    "recursive or PCD outer proof generator over the selected verifier checks",
    "recursive or PCD artifact schema that carries two_slice_target_commitment as a public input",
    "local verifier handle for the recursive or PCD artifact",
    "fail-closed mutation tests for recursive public-input relabeling",
]

NON_CLAIMS = [
    "not recursive aggregation of the selected d128 slice proofs",
    "not proof-carrying-data accumulation",
    "not a STARK-in-STARK verifier proof",
    "not one compressed cryptographic verifier object",
    "not proof-size evidence for a recursive or PCD outer proof",
    "not verifier-time evidence for a recursive or PCD outer proof",
    "not proof-generation-time evidence for a recursive or PCD outer proof",
    "not aggregation of all six d128 slice proofs",
    "not a matched public-system benchmark",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_two_slice_recursive_pcd_backend_gate.py --write-json docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-backend-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-backend-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_two_slice_recursive_pcd_backend_gate",
    "python3 -m py_compile scripts/zkai_d128_two_slice_recursive_pcd_backend_gate.py scripts/tests/test_zkai_d128_two_slice_recursive_pcd_backend_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
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
    ("source_accumulator_file_hash_drift", "source_accumulator"),
    ("source_accumulator_payload_hash_drift", "source_accumulator"),
    ("source_accumulator_result_drift", "source_accumulator"),
    ("source_accumulator_claim_boundary_changed_to_recursive", "source_accumulator"),
    ("two_slice_target_commitment_drift", "backend_probe"),
    ("accumulator_commitment_drift", "backend_probe"),
    ("verifier_handle_commitment_drift", "backend_probe"),
    ("candidate_inventory_acceptance_relabel", "candidate_inventory"),
    ("candidate_inventory_required_artifact_removed", "candidate_inventory"),
    ("candidate_inventory_file_sha256_tampered", "candidate_inventory"),
    ("candidate_inventory_required_token_removed", "candidate_inventory"),
    ("recursive_artifact_claimed_without_artifact", "recursive_or_pcd_attempt"),
    ("pcd_artifact_claimed_without_artifact", "recursive_or_pcd_attempt"),
    ("local_verifier_handle_claimed_without_artifact", "recursive_or_pcd_attempt"),
    ("target_public_input_binding_claimed_without_backend", "recursive_or_pcd_attempt"),
    ("selected_statement_binding_claimed_without_backend", "recursive_or_pcd_attempt"),
    ("selected_source_hash_binding_claimed_without_backend", "recursive_or_pcd_attempt"),
    ("proof_size_metric_smuggled_before_artifact", "recursive_or_pcd_attempt"),
    ("verifier_time_metric_smuggled_before_artifact", "recursive_or_pcd_attempt"),
    ("proof_generation_time_metric_smuggled_before_artifact", "recursive_or_pcd_attempt"),
    ("first_blocker_removed", "recursive_or_pcd_attempt"),
    ("missing_backend_feature_removed", "recursive_or_pcd_attempt"),
    ("go_criterion_weakened", "recursive_or_pcd_attempt"),
    ("recursive_or_pcd_result_changed_to_go", "parser_or_schema"),
    ("decision_changed_to_go", "parser_or_schema"),
    ("result_changed_to_go", "parser_or_schema"),
    ("issue_changed", "parser_or_schema"),
    ("claim_boundary_changed_to_recursive", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)

CANDIDATE_SURFACE_SPECS = (
    {
        "name": "d128_two_slice_accumulator_backend",
        "kind": "non_recursive_accumulator",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-accumulator-backend-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "GO_NON_RECURSIVE_ACCUMULATOR_ONLY",
        "required_tokens": (),
        "reason": "binds the selected target and source evidence, but does not prove the selected verifiers inside an outer cryptographic proof",
    },
    {
        "name": "d128_two_slice_outer_target_spike",
        "kind": "target_definition",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.json",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "GO_TARGET_ONLY_NOT_RECURSIVE_BACKEND",
        "required_tokens": (),
        "reason": "defines the smallest useful recursive target, but records missing outer proof-object backend",
    },
    {
        "name": "d128_rmsnorm_public_row_inner_stark",
        "kind": "inner_slice_stark_module",
        "path": "src/stwo_backend/d128_native_rmsnorm_public_row_proof.rs",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "INNER_STARK_VERIFIER_NOT_NESTED_VERIFIER_CIRCUIT",
        "required_tokens": ("prove_zkai_d128_rmsnorm_public_row_envelope", "verify_zkai_d128_rmsnorm_public_row_envelope"),
        "reason": "proves and verifies the inner RMSNorm public-row slice; it is not an AIR/circuit for proving that verifier inside another proof",
    },
    {
        "name": "d128_rmsnorm_projection_bridge_inner_stark",
        "kind": "inner_slice_stark_module",
        "path": "src/stwo_backend/d128_native_rmsnorm_to_projection_bridge_proof.rs",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "INNER_STARK_VERIFIER_NOT_NESTED_VERIFIER_CIRCUIT",
        "required_tokens": (
            "prove_zkai_d128_rmsnorm_to_projection_bridge_envelope",
            "verify_zkai_d128_rmsnorm_to_projection_bridge_envelope",
        ),
        "reason": "proves and verifies the inner bridge slice; it is not an AIR/circuit for proving that verifier inside another proof",
    },
    {
        "name": "phase36_recursive_harness_surface",
        "kind": "historical_harness",
        "path": "src/stwo_backend/recursion.rs",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "HARNESS_SURFACE_NOT_D128_RECURSIVE_PCD_BACKEND",
        "required_tokens": (
            "phase36_prepare_recursive_verifier_harness_receipt",
            "verify_phase36_recursive_verifier_harness_receipt",
        ),
        "reason": "records recursive claim boundaries and source checks; it does not execute the selected d128 slice verifiers inside an outer proof",
    },
    {
        "name": "cargo_stwo_backend_features",
        "kind": "dependency_surface",
        "path": "Cargo.toml",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "NO_LOCAL_RECURSIVE_PCD_INTEGRATION_EXPOSED",
        "required_tokens": ('stwo = { version = "2.2.0"', 'stwo-backend = ["dep:stwo"'),
        "reason": "the local dependency surface exposes Stwo proving/verifying support, but this repository has no recursive/PCD backend module wired to d128 verifier checks",
    },
    {
        "name": "required_d128_two_slice_recursive_pcd_backend_module",
        "kind": "required_backend_module",
        "path": "src/stwo_backend/d128_two_slice_recursive_pcd_backend.rs",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_tokens": (),
        "reason": "no executable nested-verifier or PCD backend module exists for the selected d128 verifier checks",
    },
    {
        "name": "required_d128_two_slice_recursive_pcd_proof_artifact",
        "kind": "required_recursive_or_pcd_artifact",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-proof-2026-05.json",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_tokens": (),
        "reason": "no checked recursive or PCD proof artifact exists for the two-slice target",
    },
    {
        "name": "required_d128_two_slice_recursive_pcd_verifier_handle",
        "kind": "required_verifier_handle",
        "path": "docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-verifier-2026-05.json",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_tokens": (),
        "reason": "no local verifier handle exists for a recursive or PCD two-slice artifact",
    },
    {
        "name": "d128_two_slice_recursive_pcd_no_go_audit_tests",
        "kind": "current_no_go_audit_test_surface",
        "path": "scripts/tests/test_zkai_d128_two_slice_recursive_pcd_backend_gate.py",
        "expected_exists": True,
        "required_for_go": False,
        "classification": "NO_GO_AUDIT_TEST_SURFACE_NOT_RECURSIVE_BACKEND_TESTS",
        "required_tokens": (
            "test_rejects_recursive_claim_relabeling_and_metric_smuggling",
            "test_rejects_candidate_inventory_tampering",
        ),
        "reason": "tests this bounded no-go gate and relabeling guardrails, but does not test a future executable recursive proof artifact",
    },
    {
        "name": "required_d128_two_slice_recursive_pcd_artifact_mutation_tests",
        "kind": "required_future_backend_test_surface",
        "path": "scripts/tests/test_zkai_d128_two_slice_recursive_pcd_proof_backend.py",
        "expected_exists": False,
        "required_for_go": True,
        "classification": "MISSING_REQUIRED_ARTIFACT",
        "required_tokens": (),
        "reason": "a future recursive GO must include fail-closed public-input relabeling tests",
    },
)


class D128TwoSliceRecursivePCDBackendError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128TwoSliceRecursivePCDBackendError(f"failed to load {module_name} from {path}", layer="source_accumulator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ACCUMULATOR = _load_module(ACCUMULATOR_SCRIPT, "zkai_d128_two_slice_accumulator_for_recursive_pcd_gate")


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


def _open_repo_regular_file(path: pathlib.Path, max_bytes: int, *, layer: str) -> bytes:
    resolved = path.resolve(strict=False)
    root = ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as err:
        raise D128TwoSliceRecursivePCDBackendError(f"path escapes repository: {path}", layer=layer) from err
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(resolved, flags)
    except OSError as err:
        raise D128TwoSliceRecursivePCDBackendError(f"failed to open source file {path}: {err}", layer=layer) from err
    with os.fdopen(fd, "rb") as handle:
        stat = os.fstat(handle.fileno())
        if not stat_module.S_ISREG(stat.st_mode):
            raise D128TwoSliceRecursivePCDBackendError(f"source file is not a regular file: {path}", layer=layer)
        if stat.st_size > max_bytes:
            raise D128TwoSliceRecursivePCDBackendError(
                f"source file exceeds max size: got {stat.st_size} bytes, limit {max_bytes} bytes",
                layer=layer,
            )
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise D128TwoSliceRecursivePCDBackendError(
            f"source file exceeds max size: got more than {max_bytes} bytes",
            layer=layer,
        )
    return data


def file_sha256(path: pathlib.Path, *, max_bytes: int = MAX_SOURCE_JSON_BYTES) -> str:
    return sha256_hex_bytes(_open_repo_regular_file(path, max_bytes, layer="candidate_inventory"))


def relative_path(path: pathlib.Path) -> str:
    return str(path.resolve(strict=False).relative_to(ROOT.resolve()))


def load_json(path: pathlib.Path, *, layer: str = "source_accumulator") -> dict[str, Any]:
    data = _open_repo_regular_file(path, MAX_SOURCE_JSON_BYTES, layer=layer)
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128TwoSliceRecursivePCDBackendError(f"failed to load JSON from {path}: {err}", layer=layer) from err
    if not isinstance(payload, dict):
        raise D128TwoSliceRecursivePCDBackendError(f"source evidence must be a JSON object: {path}", layer=layer)
    return payload


def expect_equal(actual: Any, expected: Any, field: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128TwoSliceRecursivePCDBackendError(f"{field} mismatch", layer=layer)


def expect_key_set(value: dict[str, Any], expected: set[str], field: str, *, layer: str = "parser_or_schema") -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise D128TwoSliceRecursivePCDBackendError(
            f"{field} key set mismatch: missing={missing} extra={extra}",
            layer=layer,
        )


def require_object(value: Any, field: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be an object", layer=layer)
    return value


def require_list(value: Any, field: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be a list", layer=layer)
    return value


def require_bool(value: Any, field: str, *, layer: str = "parser_or_schema") -> bool:
    if not isinstance(value, bool):
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be a boolean", layer=layer)
    return value


def require_int(value: Any, field: str, *, layer: str = "parser_or_schema") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be an integer", layer=layer)
    return value


def require_str(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    if not isinstance(value, str) or not value:
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be a non-empty string", layer=layer)
    return value


def require_commitment(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    text = require_str(value, field, layer=layer)
    if not text.startswith("blake2b-256:"):
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be blake2b-256 domain-separated", layer=layer)
    raw = text.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128TwoSliceRecursivePCDBackendError(f"{field} must be a 32-byte lowercase hex digest", layer=layer)
    return text


@lru_cache(maxsize=4)
def _load_checked_source_accumulator_cached(path_text: str) -> dict[str, Any]:
    path = pathlib.Path(path_text)
    payload = load_json(path, layer="source_accumulator")
    try:
        ACCUMULATOR.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128TwoSliceRecursivePCDBackendError(f"d128 two-slice accumulator validation failed: {err}", layer="source_accumulator") from err
    expect_equal(payload.get("schema"), EXPECTED_SOURCE_SCHEMA, "source accumulator schema", layer="source_accumulator")
    expect_equal(payload.get("decision"), EXPECTED_SOURCE_DECISION, "source accumulator decision", layer="source_accumulator")
    expect_equal(payload.get("result"), EXPECTED_SOURCE_RESULT, "source accumulator result", layer="source_accumulator")
    expect_equal(
        payload.get("accumulator_result"),
        EXPECTED_SOURCE_ACCUMULATOR_RESULT,
        "source accumulator accumulator_result",
        layer="source_accumulator",
    )
    expect_equal(
        payload.get("recursive_or_pcd_result"),
        EXPECTED_SOURCE_RECURSIVE_RESULT,
        "source accumulator recursive_or_pcd_result",
        layer="source_accumulator",
    )
    expect_equal(
        payload.get("claim_boundary"),
        EXPECTED_SOURCE_CLAIM_BOUNDARY,
        "source accumulator claim_boundary",
        layer="source_accumulator",
    )
    expect_equal(payload.get("all_mutations_rejected"), True, "source accumulator all_mutations_rejected", layer="source_accumulator")
    return payload


def load_checked_source_accumulator(path: pathlib.Path = SOURCE_ACCUMULATOR_EVIDENCE) -> dict[str, Any]:
    return copy.deepcopy(_load_checked_source_accumulator_cached(str(path)))


def source_accumulator_descriptor(source: dict[str, Any], path: pathlib.Path = SOURCE_ACCUMULATOR_EVIDENCE) -> dict[str, Any]:
    summary = require_object(source.get("summary"), "source accumulator summary", layer="source_accumulator")
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "result": source["result"],
        "accumulator_result": source["accumulator_result"],
        "recursive_or_pcd_result": source["recursive_or_pcd_result"],
        "claim_boundary": source["claim_boundary"],
        "two_slice_target_commitment": summary["two_slice_target_commitment"],
        "selected_slice_ids": copy.deepcopy(summary["selected_slice_ids"]),
        "selected_checked_rows": summary["selected_checked_rows"],
        "accumulator_commitment": summary["accumulator_commitment"],
        "verifier_handle_commitment": summary["verifier_handle_commitment"],
    }


def _candidate_file_info(path_text: str) -> dict[str, Any]:
    path = ROOT / path_text
    exists = path.exists()
    if not exists:
        return {"exists": False, "file_sha256": None, "required_tokens_present": None, "missing_required_tokens": None}
    data = _open_repo_regular_file(path, MAX_SOURCE_JSON_BYTES, layer="candidate_inventory")
    return {"exists": True, "file_sha256": sha256_hex_bytes(data), "required_tokens_present": None, "missing_required_tokens": None}


@lru_cache(maxsize=1)
def _candidate_inventory_cached() -> tuple[tuple[tuple[str, Any], ...], ...]:
    inventory: list[dict[str, Any]] = []
    for spec in CANDIDATE_SURFACE_SPECS:
        item = {
            "name": spec["name"],
            "kind": spec["kind"],
            "path": spec["path"],
            "expected_exists": spec["expected_exists"],
            "required_for_go": spec["required_for_go"],
            "classification": spec["classification"],
            "reason": spec["reason"],
        }
        info = _candidate_file_info(spec["path"])
        item.update(info)
        required_tokens = list(spec["required_tokens"])
        item["required_tokens"] = required_tokens
        if item["exists"] and required_tokens:
            raw = _open_repo_regular_file(ROOT / spec["path"], MAX_SOURCE_JSON_BYTES, layer="candidate_inventory").decode(
                "utf-8", errors="replace"
            )
            missing = [token for token in required_tokens if token not in raw]
            item["required_tokens_present"] = len(missing) == 0
            item["missing_required_tokens"] = missing
        inventory.append(item)
    return tuple(tuple(item.items()) for item in inventory)


def candidate_inventory() -> list[dict[str, Any]]:
    return copy.deepcopy([dict(item) for item in _candidate_inventory_cached()])


def backend_probe(source: dict[str, Any]) -> dict[str, Any]:
    descriptor = source_accumulator_descriptor(source)
    selected_slices = [
        {
            "slice_id": slice_id,
            "role": role,
        }
        for slice_id, role in (
            ("rmsnorm_public_rows", "first selected inner STARK verifier"),
            ("rmsnorm_projection_bridge", "second selected inner STARK verifier"),
        )
    ]
    return {
        "go_criterion": GO_CRITERION,
        "recursive_or_pcd_result": RECURSIVE_OR_PCD_RESULT,
        "first_blocker": FIRST_BLOCKER,
        "claim_boundary": CLAIM_BOUNDARY,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "two_slice_target_commitment": descriptor["two_slice_target_commitment"],
        "accumulator_commitment": descriptor["accumulator_commitment"],
        "verifier_handle_commitment": descriptor["verifier_handle_commitment"],
        "selected_slices": selected_slices,
        "required_public_inputs_for_future_go": [
            "two_slice_target_commitment",
            "selected slice statement commitments",
            "selected source evidence hashes",
        ],
        "attempt": {
            "recursive_artifact_exists": False,
            "pcd_artifact_exists": False,
            "local_verifier_handle_exists": False,
            "target_public_input_binding_executable": False,
            "selected_statement_binding_executable": False,
            "selected_source_hash_binding_executable": False,
            "proof_metrics_enabled": False,
            "blocked_before_metrics": True,
            "first_blocker": FIRST_BLOCKER,
            "missing_backend_features": copy.deepcopy(MISSING_BACKEND_FEATURES),
        },
    }


def summary(source: dict[str, Any], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    descriptor = source_accumulator_descriptor(source)
    missing_required = [item["name"] for item in inventory if item["required_for_go"] and not item["exists"]]
    non_recursive_surfaces = [
        item["name"]
        for item in inventory
        if item["classification"] in {"GO_NON_RECURSIVE_ACCUMULATOR_ONLY", "GO_TARGET_ONLY_NOT_RECURSIVE_BACKEND"}
    ]
    return {
        "issue": ISSUE,
        "result": RESULT,
        "recursive_or_pcd_result": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "go_criterion": GO_CRITERION,
        "first_blocker": FIRST_BLOCKER,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "two_slice_target_commitment": descriptor["two_slice_target_commitment"],
        "accumulator_commitment": descriptor["accumulator_commitment"],
        "verifier_handle_commitment": descriptor["verifier_handle_commitment"],
        "non_recursive_surfaces_available": non_recursive_surfaces,
        "required_go_artifacts_missing": missing_required,
        "missing_backend_feature_count": len(MISSING_BACKEND_FEATURES),
        "proof_metrics_enabled": False,
    }


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def build_core_payload() -> dict[str, Any]:
    source = load_checked_source_accumulator()
    inventory = candidate_inventory()
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "accumulator_baseline_result": ACCUMULATOR_BASELINE_RESULT,
        "recursive_or_pcd_result": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_accumulator": source_accumulator_descriptor(source),
        "candidate_inventory": inventory,
        "backend_probe": backend_probe(source),
        "summary": summary(source, inventory),
        "missing_backend_features": copy.deepcopy(MISSING_BACKEND_FEATURES),
        "non_claims": copy.deepcopy(NON_CLAIMS),
        "validation_commands": copy.deepcopy(VALIDATION_COMMANDS),
        "mutation_inventory": expected_mutation_inventory(),
    }


def _candidate_by_name(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for candidate in require_list(payload.get("candidate_inventory"), "candidate inventory", layer="candidate_inventory"):
        candidate = require_object(candidate, "candidate inventory item", layer="candidate_inventory")
        if candidate.get("name") == name:
            return candidate
    raise D128TwoSliceRecursivePCDBackendError(f"candidate not found: {name}", layer="candidate_inventory")


def mutate_payload(payload: dict[str, Any], mutation: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if mutation == "source_accumulator_file_hash_drift":
        mutated["source_accumulator"]["file_sha256"] = "0" * 64
    elif mutation == "source_accumulator_payload_hash_drift":
        mutated["source_accumulator"]["payload_sha256"] = "1" * 64
    elif mutation == "source_accumulator_result_drift":
        mutated["source_accumulator"]["result"] = "BOUNDED_NO_GO"
    elif mutation == "source_accumulator_claim_boundary_changed_to_recursive":
        mutated["source_accumulator"]["claim_boundary"] = "RECURSIVE_OUTER_PROOF"
    elif mutation == "two_slice_target_commitment_drift":
        mutated["backend_probe"]["two_slice_target_commitment"] = "blake2b-256:" + "2" * 64
    elif mutation == "accumulator_commitment_drift":
        mutated["backend_probe"]["accumulator_commitment"] = "blake2b-256:" + "3" * 64
    elif mutation == "verifier_handle_commitment_drift":
        mutated["backend_probe"]["verifier_handle_commitment"] = "blake2b-256:" + "4" * 64
    elif mutation == "candidate_inventory_acceptance_relabel":
        _candidate_by_name(mutated, "required_d128_two_slice_recursive_pcd_backend_module")["classification"] = "GO_RECURSIVE_BACKEND"
    elif mutation == "candidate_inventory_required_artifact_removed":
        mutated["candidate_inventory"] = [
            item
            for item in mutated["candidate_inventory"]
            if item["name"] != "required_d128_two_slice_recursive_pcd_proof_artifact"
        ]
    elif mutation == "candidate_inventory_file_sha256_tampered":
        _candidate_by_name(mutated, "d128_rmsnorm_public_row_inner_stark")["file_sha256"] = "5" * 64
    elif mutation == "candidate_inventory_required_token_removed":
        _candidate_by_name(mutated, "phase36_recursive_harness_surface")["required_tokens"] = []
    elif mutation == "recursive_artifact_claimed_without_artifact":
        mutated["backend_probe"]["attempt"]["recursive_artifact_exists"] = True
    elif mutation == "pcd_artifact_claimed_without_artifact":
        mutated["backend_probe"]["attempt"]["pcd_artifact_exists"] = True
    elif mutation == "local_verifier_handle_claimed_without_artifact":
        mutated["backend_probe"]["attempt"]["local_verifier_handle_exists"] = True
    elif mutation == "target_public_input_binding_claimed_without_backend":
        mutated["backend_probe"]["attempt"]["target_public_input_binding_executable"] = True
    elif mutation == "selected_statement_binding_claimed_without_backend":
        mutated["backend_probe"]["attempt"]["selected_statement_binding_executable"] = True
    elif mutation == "selected_source_hash_binding_claimed_without_backend":
        mutated["backend_probe"]["attempt"]["selected_source_hash_binding_executable"] = True
    elif mutation == "proof_size_metric_smuggled_before_artifact":
        mutated["backend_probe"]["attempt"]["recursive_proof_size_bytes"] = 4096
    elif mutation == "verifier_time_metric_smuggled_before_artifact":
        mutated["backend_probe"]["attempt"]["recursive_verifier_ms"] = 1.5
    elif mutation == "proof_generation_time_metric_smuggled_before_artifact":
        mutated["backend_probe"]["attempt"]["recursive_proof_generation_ms"] = 99.0
    elif mutation == "first_blocker_removed":
        mutated["backend_probe"]["attempt"]["first_blocker"] = ""
    elif mutation == "missing_backend_feature_removed":
        mutated["backend_probe"]["attempt"]["missing_backend_features"].pop()
    elif mutation == "go_criterion_weakened":
        mutated["backend_probe"]["go_criterion"] = "one accumulator exists"
    elif mutation == "recursive_or_pcd_result_changed_to_go":
        mutated["recursive_or_pcd_result"] = "GO_RECURSIVE_PCD_OUTER_PROOF"
    elif mutation == "decision_changed_to_go":
        mutated["decision"] = "GO_D128_TWO_SLICE_RECURSIVE_PCD_BACKEND"
    elif mutation == "result_changed_to_go":
        mutated["result"] = "GO"
    elif mutation == "issue_changed":
        mutated["issue"] = 409
    elif mutation == "claim_boundary_changed_to_recursive":
        mutated["claim_boundary"] = "RECURSIVE_PCD_BACKEND"
    elif mutation == "non_claims_removed":
        mutated["non_claims"].pop()
    elif mutation == "validation_command_drift":
        mutated["validation_commands"][0] = "python3 scripts/fake.py"
    elif mutation == "unknown_top_level_field_added":
        mutated["invented_recursive_metric"] = 1
    else:
        raise D128TwoSliceRecursivePCDBackendError(f"unknown mutation: {mutation}")
    return mutated


def classify_error(error: Exception) -> str:
    if isinstance(error, D128TwoSliceRecursivePCDBackendError):
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
    validate_payload(payload)
    return payload


CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "accumulator_baseline_result",
    "recursive_or_pcd_result",
    "claim_boundary",
    "source_accumulator",
    "candidate_inventory",
    "backend_probe",
    "summary",
    "missing_backend_features",
    "non_claims",
    "validation_commands",
    "mutation_inventory",
}
FINAL_KEYS = CORE_KEYS | {"cases", "case_count", "all_mutations_rejected"}

SOURCE_ACCUMULATOR_KEYS = {
    "path",
    "file_sha256",
    "payload_sha256",
    "schema",
    "decision",
    "result",
    "accumulator_result",
    "recursive_or_pcd_result",
    "claim_boundary",
    "two_slice_target_commitment",
    "selected_slice_ids",
    "selected_checked_rows",
    "accumulator_commitment",
    "verifier_handle_commitment",
}

CANDIDATE_KEYS = {
    "name",
    "kind",
    "path",
    "expected_exists",
    "required_for_go",
    "classification",
    "reason",
    "exists",
    "file_sha256",
    "required_tokens_present",
    "missing_required_tokens",
    "required_tokens",
}

ATTEMPT_KEYS = {
    "recursive_artifact_exists",
    "pcd_artifact_exists",
    "local_verifier_handle_exists",
    "target_public_input_binding_executable",
    "selected_statement_binding_executable",
    "selected_source_hash_binding_executable",
    "proof_metrics_enabled",
    "blocked_before_metrics",
    "first_blocker",
    "missing_backend_features",
}

BACKEND_PROBE_KEYS = {
    "go_criterion",
    "recursive_or_pcd_result",
    "first_blocker",
    "claim_boundary",
    "selected_slice_ids",
    "selected_checked_rows",
    "two_slice_target_commitment",
    "accumulator_commitment",
    "verifier_handle_commitment",
    "selected_slices",
    "required_public_inputs_for_future_go",
    "attempt",
}

SUMMARY_KEYS = {
    "issue",
    "result",
    "recursive_or_pcd_result",
    "claim_boundary",
    "go_criterion",
    "first_blocker",
    "selected_slice_ids",
    "selected_checked_rows",
    "two_slice_target_commitment",
    "accumulator_commitment",
    "verifier_handle_commitment",
    "non_recursive_surfaces_available",
    "required_go_artifacts_missing",
    "missing_backend_feature_count",
    "proof_metrics_enabled",
}

CASE_KEYS = {"index", "mutation", "surface", "baseline_result", "mutated_accepted", "rejected", "rejection_layer", "error"}


def validate_source_accumulator_descriptor(value: Any) -> None:
    descriptor = require_object(value, "source accumulator", layer="source_accumulator")
    expect_key_set(descriptor, SOURCE_ACCUMULATOR_KEYS, "source accumulator", layer="source_accumulator")
    expected = source_accumulator_descriptor(load_checked_source_accumulator())
    expect_equal(descriptor, expected, "source accumulator descriptor", layer="source_accumulator")
    require_commitment(descriptor["two_slice_target_commitment"], "source target commitment", layer="source_accumulator")
    require_commitment(descriptor["accumulator_commitment"], "source accumulator commitment", layer="source_accumulator")
    require_commitment(descriptor["verifier_handle_commitment"], "source verifier handle commitment", layer="source_accumulator")
    expect_equal(tuple(descriptor["selected_slice_ids"]), EXPECTED_SELECTED_SLICE_IDS, "selected slice ids", layer="source_accumulator")
    expect_equal(descriptor["selected_checked_rows"], EXPECTED_SELECTED_ROWS, "selected checked rows", layer="source_accumulator")


def validate_candidate_inventory(value: Any) -> None:
    inventory = require_list(value, "candidate inventory", layer="candidate_inventory")
    expected = candidate_inventory()
    expect_equal(inventory, expected, "candidate inventory", layer="candidate_inventory")
    seen: set[str] = set()
    for index, item in enumerate(inventory):
        candidate = require_object(item, f"candidate inventory item {index}", layer="candidate_inventory")
        expect_key_set(candidate, CANDIDATE_KEYS, f"candidate inventory item {index}", layer="candidate_inventory")
        name = require_str(candidate["name"], f"candidate inventory item {index} name", layer="candidate_inventory")
        if name in seen:
            raise D128TwoSliceRecursivePCDBackendError("duplicate candidate inventory name", layer="candidate_inventory")
        seen.add(name)
        require_bool(candidate["expected_exists"], f"candidate {name} expected_exists", layer="candidate_inventory")
        require_bool(candidate["required_for_go"], f"candidate {name} required_for_go", layer="candidate_inventory")
        require_bool(candidate["exists"], f"candidate {name} exists", layer="candidate_inventory")
        if candidate["exists"] != candidate["expected_exists"]:
            raise D128TwoSliceRecursivePCDBackendError(f"candidate {name} existence changed; update gate", layer="candidate_inventory")
        if candidate["required_for_go"] and candidate["exists"]:
            raise D128TwoSliceRecursivePCDBackendError(
                f"candidate {name} now exists; replace no-go with real backend validation",
                layer="candidate_inventory",
            )
        tokens = require_list(candidate["required_tokens"], f"candidate {name} required_tokens", layer="candidate_inventory")
        if tokens:
            expect_equal(candidate["required_tokens_present"], True, f"candidate {name} required tokens", layer="candidate_inventory")
            expect_equal(candidate["missing_required_tokens"], [], f"candidate {name} missing required tokens", layer="candidate_inventory")


def validate_backend_probe(value: Any, descriptor: dict[str, Any]) -> None:
    probe = require_object(value, "backend probe", layer="recursive_or_pcd_attempt")
    expect_key_set(probe, BACKEND_PROBE_KEYS, "backend probe", layer="recursive_or_pcd_attempt")
    expect_equal(probe, backend_probe(load_checked_source_accumulator()), "backend probe", layer="recursive_or_pcd_attempt")
    expect_equal(probe["go_criterion"], GO_CRITERION, "backend go criterion", layer="recursive_or_pcd_attempt")
    expect_equal(probe["recursive_or_pcd_result"], RECURSIVE_OR_PCD_RESULT, "backend recursive result", layer="recursive_or_pcd_attempt")
    expect_equal(probe["first_blocker"], FIRST_BLOCKER, "backend first blocker", layer="recursive_or_pcd_attempt")
    expect_equal(probe["claim_boundary"], CLAIM_BOUNDARY, "backend claim boundary", layer="recursive_or_pcd_attempt")
    expect_equal(probe["two_slice_target_commitment"], descriptor["two_slice_target_commitment"], "backend target", layer="recursive_or_pcd_attempt")
    expect_equal(probe["accumulator_commitment"], descriptor["accumulator_commitment"], "backend accumulator", layer="recursive_or_pcd_attempt")
    expect_equal(probe["verifier_handle_commitment"], descriptor["verifier_handle_commitment"], "backend verifier handle", layer="recursive_or_pcd_attempt")
    attempt = require_object(probe["attempt"], "backend attempt", layer="recursive_or_pcd_attempt")
    expect_key_set(attempt, ATTEMPT_KEYS, "backend attempt", layer="recursive_or_pcd_attempt")
    for field in (
        "recursive_artifact_exists",
        "pcd_artifact_exists",
        "local_verifier_handle_exists",
        "target_public_input_binding_executable",
        "selected_statement_binding_executable",
        "selected_source_hash_binding_executable",
        "proof_metrics_enabled",
    ):
        expect_equal(attempt[field], False, f"backend attempt {field}", layer="recursive_or_pcd_attempt")
    expect_equal(attempt["blocked_before_metrics"], True, "backend blocked_before_metrics", layer="recursive_or_pcd_attempt")
    expect_equal(attempt["first_blocker"], FIRST_BLOCKER, "backend attempt first blocker", layer="recursive_or_pcd_attempt")
    expect_equal(attempt["missing_backend_features"], MISSING_BACKEND_FEATURES, "missing backend features", layer="recursive_or_pcd_attempt")


def validate_summary(value: Any, descriptor: dict[str, Any]) -> None:
    item = require_object(value, "summary", layer="summary")
    expect_key_set(item, SUMMARY_KEYS, "summary", layer="summary")
    expected = summary(load_checked_source_accumulator(), candidate_inventory())
    expect_equal(item, expected, "summary", layer="summary")
    expect_equal(item["two_slice_target_commitment"], descriptor["two_slice_target_commitment"], "summary target", layer="summary")
    expect_equal(item["accumulator_commitment"], descriptor["accumulator_commitment"], "summary accumulator", layer="summary")
    expect_equal(item["verifier_handle_commitment"], descriptor["verifier_handle_commitment"], "summary verifier handle", layer="summary")


def validate_core_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise D128TwoSliceRecursivePCDBackendError("payload must be a JSON object")
    allowed = FINAL_KEYS if any(key in payload for key in ("cases", "case_count", "all_mutations_rejected")) else CORE_KEYS
    expect_key_set(payload, allowed, "top-level payload")
    expect_equal(payload["schema"], SCHEMA, "schema")
    expect_equal(payload["decision"], DECISION, "decision")
    expect_equal(payload["result"], RESULT, "result")
    expect_equal(payload["issue"], ISSUE, "issue")
    expect_equal(payload["accumulator_baseline_result"], ACCUMULATOR_BASELINE_RESULT, "accumulator baseline result")
    expect_equal(payload["recursive_or_pcd_result"], RECURSIVE_OR_PCD_RESULT, "recursive_or_pcd_result", layer="recursive_or_pcd_attempt")
    expect_equal(payload["claim_boundary"], CLAIM_BOUNDARY, "claim boundary")
    validate_source_accumulator_descriptor(payload["source_accumulator"])
    descriptor = require_object(payload["source_accumulator"], "source accumulator", layer="source_accumulator")
    validate_candidate_inventory(payload["candidate_inventory"])
    validate_backend_probe(payload["backend_probe"], descriptor)
    validate_summary(payload["summary"], descriptor)
    expect_equal(payload["missing_backend_features"], MISSING_BACKEND_FEATURES, "missing backend features", layer="recursive_or_pcd_attempt")
    expect_equal(payload["non_claims"], NON_CLAIMS, "non_claims")
    expect_equal(payload["validation_commands"], VALIDATION_COMMANDS, "validation_commands")
    expect_equal(payload["mutation_inventory"], expected_mutation_inventory(), "mutation inventory")


def validate_cases(value: Any, expected_cases: list[dict[str, Any]]) -> None:
    cases = require_list(value, "cases")
    expect_equal(cases, expected_cases, "cases")
    for index, case in enumerate(cases):
        item = require_object(case, f"case {index}")
        expect_key_set(item, CASE_KEYS, f"case {index}")
        expect_equal(item["index"], index, f"case {index} index")
        require_str(item["mutation"], f"case {index} mutation")
        require_str(item["surface"], f"case {index} surface")
        require_bool(item["mutated_accepted"], f"case {index} mutated_accepted")
        require_bool(item["rejected"], f"case {index} rejected")
        if item["mutated_accepted"] or not item["rejected"]:
            raise D128TwoSliceRecursivePCDBackendError(f"mutation case {index} was accepted")
        require_str(item["rejection_layer"], f"case {index} rejection_layer")
        require_str(item["error"], f"case {index} error")


def validate_payload(payload: dict[str, Any]) -> None:
    validate_core_payload(payload)
    expected_core = build_core_payload()
    expected_cases = run_mutations(expected_core)
    validate_cases(payload["cases"], expected_cases)
    expect_equal(payload["case_count"], len(expected_cases), "case_count")
    expect_equal(payload["all_mutations_rejected"], True, "all_mutations_rejected")


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for case in payload["cases"]:
        writer.writerow({column: case[column] for column in TSV_COLUMNS})
    return output.getvalue()


def _safe_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_absolute():
        raise D128TwoSliceRecursivePCDBackendError(f"output path must be repo-relative: {path}")
    pure = pathlib.PurePosixPath(path.as_posix())
    if path.as_posix() != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise D128TwoSliceRecursivePCDBackendError(f"output path must be repo-relative without traversal: {path}")
    candidate = ROOT.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128TwoSliceRecursivePCDBackendError(f"output path escapes repository: {path}") from err
    return candidate


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs: list[tuple[pathlib.Path, bytes]] = []
    if json_path is not None:
        outputs.append((_safe_output_path(json_path), json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"))
    if tsv_path is not None:
        outputs.append((_safe_output_path(tsv_path), to_tsv(payload).encode("utf-8")))
    resolved_outputs = [path.resolve(strict=False) for path, _data in outputs]
    if len(resolved_outputs) != len(set(resolved_outputs)):
        raise D128TwoSliceRecursivePCDBackendError("write-json and write-tsv output paths must be distinct")
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
    parser = argparse.ArgumentParser(
        description=(
            "Audit the d128 two-slice recursive/PCD backend route. "
            "GO requires a real recursive/PCD outer proof object; current result is bounded NO-GO if missing."
        )
    )
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    if args.write_json is None and args.write_tsv is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
