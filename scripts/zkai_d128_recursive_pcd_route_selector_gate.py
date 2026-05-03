#!/usr/bin/env python3
"""Select the next honest d128 recursive/PCD backend route.

This gate answers issue #420 without manufacturing a recursive proof object.
It consumes the existing d128 accumulator and recursive/PCD no-go evidence,
then classifies the plausible next routes.  A route is allowed to be "GO" only
if an executable proof or verifier artifact exists today.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import tomllib
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-recursive-pcd-route-selector-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-recursive-pcd-route-selector-2026-05.tsv"

TWO_SLICE_ACCUMULATOR_EVIDENCE = (
    EVIDENCE_DIR / "zkai-d128-two-slice-accumulator-backend-2026-05.json"
)
FULL_BLOCK_ACCUMULATOR_EVIDENCE = (
    EVIDENCE_DIR / "zkai-d128-full-block-accumulator-backend-2026-05.json"
)
RECURSIVE_PCD_AUDIT_EVIDENCE = (
    EVIDENCE_DIR / "zkai-d128-two-slice-recursive-pcd-backend-2026-05.json"
)

SCHEMA = "zkai-d128-recursive-pcd-route-selector-v1"
DECISION = "NO_GO_LOCAL_D128_RECURSIVE_PCD_BACKEND_TODAY"
RESULT = "ROUTE_SELECTED_BOUNDED_NO_GO"
ISSUE = 420
PRIMARY_BLOCKER = "NO_EXECUTABLE_NESTED_VERIFIER_BACKEND_FOR_D128_TWO_SLICE_TARGET"
NEXT_ROUTE = "EXTERNAL_ZKVM_STATEMENT_RECEIPT_ADAPTER_OR_PROOF_NATIVE_COMPRESSION_SPIKE"

EXPECTED_TWO_SLICE_ACCUMULATOR_SCHEMA = "zkai-d128-two-slice-accumulator-backend-v1"
EXPECTED_TWO_SLICE_ACCUMULATOR_DECISION = "GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR_BACKEND"
EXPECTED_TWO_SLICE_ACCUMULATOR_RESULT = "GO"
EXPECTED_TWO_SLICE_ACCUMULATOR_CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF"
EXPECTED_FULL_BLOCK_ACCUMULATOR_SCHEMA = "zkai-d128-full-block-accumulator-backend-v1"
EXPECTED_FULL_BLOCK_ACCUMULATOR_DECISION = "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_BACKEND"
EXPECTED_FULL_BLOCK_ACCUMULATOR_RESULT = "GO"
EXPECTED_FULL_BLOCK_ACCUMULATOR_CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF"
EXPECTED_RECURSIVE_PCD_SCHEMA = "zkai-d128-two-slice-recursive-pcd-backend-gate-v1"
EXPECTED_RECURSIVE_PCD_DECISION = "NO_GO_D128_TWO_SLICE_RECURSIVE_PCD_BACKEND_UNAVAILABLE"
EXPECTED_RECURSIVE_PCD_RESULT = "BOUNDED_NO_GO"
EXPECTED_RECURSIVE_PCD_CLAIM_BOUNDARY = "NON_RECURSIVE_ACCUMULATOR_AVAILABLE_RECURSIVE_PCD_BACKEND_MISSING"
EXPECTED_RECURSIVE_OR_PCD_RESULT = "NO_GO_EXECUTABLE_RECURSIVE_PCD_OUTER_PROOF_BACKEND_MISSING"
EXPECTED_STWO_VERSION = "2.2.0"
EXPECTED_SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")
EXPECTED_SELECTED_ROWS = 256
EXPECTED_FULL_BLOCK_ROWS = 197_504
MAX_SOURCE_JSON_BYTES = 16 * 1024 * 1024

GO_CRITERION = (
    "an executable recursive or PCD proof object exists for the d128 two-slice "
    "target, a verifier handle accepts it, and the public inputs bind "
    "two_slice_target_commitment, selected slice statement commitments, selected "
    "source evidence hashes, and verifier domain/version"
)

NON_CLAIMS = [
    "not recursive aggregation",
    "not proof-carrying data",
    "not one compressed cryptographic verifier object",
    "not proof-size evidence for a recursive or PCD proof",
    "not verifier-time evidence for a recursive or PCD proof",
    "not proof-generation-time evidence for a recursive or PCD proof",
    "not a public zkML benchmark row",
    "not onchain deployment evidence",
    "not a claim that external zkVM or SNARK routes already satisfy the d128 contract",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_recursive_pcd_route_selector_gate.py --write-json docs/engineering/evidence/zkai-d128-recursive-pcd-route-selector-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-recursive-pcd-route-selector-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_recursive_pcd_route_selector_gate",
    "python3 -m py_compile scripts/zkai_d128_recursive_pcd_route_selector_gate.py scripts/tests/test_zkai_d128_recursive_pcd_route_selector_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "route_id",
    "route_kind",
    "status",
    "usable_today",
    "claim_boundary",
    "next_action",
    "blocking_missing_object",
)

ROUTE_IDS = (
    "local_stwo_nested_verifier_air",
    "local_stwo_pcd_outer_proof",
    "local_two_slice_non_recursive_accumulator",
    "local_full_block_non_recursive_accumulator",
    "proof_native_two_slice_compression_without_recursion",
    "external_zkvm_statement_receipt_adapter",
    "external_snark_or_ivc_statement_adapter",
    "starknet_settlement_adapter",
)

EXPECTED_MUTATION_INVENTORY = (
    ("source_two_slice_file_hash_drift", "source_evidence"),
    ("source_recursive_path_drift", "source_evidence"),
    ("source_two_slice_result_drift", "source_evidence"),
    ("source_two_slice_claim_boundary_drift", "source_evidence"),
    ("source_full_block_result_drift", "source_evidence"),
    ("source_recursive_no_go_result_changed_to_go", "source_evidence"),
    ("source_recursive_blocker_removed", "source_evidence"),
    ("route_local_stwo_nested_verifier_relabel_to_go", "route_table"),
    ("route_local_pcd_relabel_to_go", "route_table"),
    ("route_external_adapter_relabel_to_go", "route_table"),
    ("route_removed", "route_table"),
    ("blocking_missing_object_removed", "route_table"),
    ("next_route_changed_to_local_recursive", "route_decision"),
    ("primary_blocker_removed", "route_decision"),
    ("proof_size_metric_smuggled", "route_decision"),
    ("verifier_time_metric_smuggled", "route_decision"),
    ("proof_generation_time_metric_smuggled", "route_decision"),
    ("decision_changed_to_go", "parser_or_schema"),
    ("result_changed_to_go", "parser_or_schema"),
    ("issue_changed", "parser_or_schema"),
    ("go_criterion_weakened", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)


class D128RecursivePCDRouteSelectorError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_hex_json(value: Any) -> str:
    return sha256_hex_bytes(canonical_json_bytes(value))


def read_json_file(path: pathlib.Path) -> Any:
    try:
        if not path.exists():
            raise D128RecursivePCDRouteSelectorError(f"missing source evidence: {path}", layer="source_evidence")
        if path.stat().st_size > MAX_SOURCE_JSON_BYTES:
            raise D128RecursivePCDRouteSelectorError(f"source evidence too large: {path}", layer="source_evidence")
        return json.loads(path.read_text(encoding="utf-8"))
    except D128RecursivePCDRouteSelectorError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as err:
        raise D128RecursivePCDRouteSelectorError(
            f"unreadable or malformed source evidence {path}: {err}",
            layer="source_evidence",
        ) from err


def file_sha256(path: pathlib.Path) -> str:
    return sha256_hex_bytes(path.read_bytes())


def require_object(value: Any, field: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be an object", layer=layer)
    return value


def require_list(value: Any, field: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be a list", layer=layer)
    return value


def require_str(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    if not isinstance(value, str) or not value:
        raise D128RecursivePCDRouteSelectorError(f"{field} must be a non-empty string", layer=layer)
    return value


def require_bool(value: Any, field: str, *, layer: str = "parser_or_schema") -> bool:
    if not isinstance(value, bool):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be a boolean", layer=layer)
    return value


def require_int(value: Any, field: str, *, layer: str = "parser_or_schema") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be an integer", layer=layer)
    return value


def expect_equal(actual: Any, expected: Any, field: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128RecursivePCDRouteSelectorError(f"{field} mismatch", layer=layer)


def expect_key_set(value: dict[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise D128RecursivePCDRouteSelectorError(
            f"{field} key set mismatch: missing={missing} extra={extra}",
            layer="parser_or_schema",
        )


def require_commitment(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    value = require_str(value, field, layer=layer)
    if not value.startswith("blake2b-256:"):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be blake2b-256 domain-separated", layer=layer)
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be a 32-byte lowercase hex digest", layer=layer)
    return value


def require_sha256_hex(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    value = require_str(value, field, layer=layer)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be a 32-byte lowercase hex digest", layer=layer)
    return value


def require_safe_evidence_path(value: Any, field: str, *, expected: str | None = None) -> str:
    value = require_str(value, field, layer="route_table")
    path = pathlib.Path(value)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be a safe repo-relative path", layer="route_table")
    if path.parts[:3] != ("docs", "engineering", "evidence"):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be under docs/engineering/evidence", layer="route_table")
    if expected is not None:
        expect_equal(value, expected, field, layer="route_table")
    return value


def source_descriptor(path: pathlib.Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(payload),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "result": payload.get("result"),
        "claim_boundary": payload.get("claim_boundary"),
    }


def cargo_dependency_version(cargo_toml: dict[str, Any], name: str) -> str | None:
    deps = cargo_toml.get("dependencies")
    if not isinstance(deps, dict):
        return None
    value = deps.get(name)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        version = value.get("version")
        return version if isinstance(version, str) else None
    return None


def cargo_lock_package_version(cargo_lock: dict[str, Any], name: str) -> str | None:
    packages = cargo_lock.get("package")
    if not isinstance(packages, list):
        return None
    for package in packages:
        if isinstance(package, dict) and package.get("name") == name:
            version = package.get("version")
            return version if isinstance(version, str) else None
    return None


def local_repo_probe() -> dict[str, Any]:
    cargo_toml = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    cargo_lock = tomllib.loads((ROOT / "Cargo.lock").read_text(encoding="utf-8"))
    dependency_names = set(cargo_toml.get("dependencies", {}))
    return {
        "cargo_toml_sha256": file_sha256(ROOT / "Cargo.toml"),
        "cargo_lock_sha256": file_sha256(ROOT / "Cargo.lock"),
        "stwo_dependency_declared": cargo_dependency_version(cargo_toml, "stwo") == EXPECTED_STWO_VERSION,
        "stwo_constraint_framework_declared": (
            cargo_dependency_version(cargo_toml, "stwo-constraint-framework") == EXPECTED_STWO_VERSION
        ),
        "local_stwo_version": cargo_lock_package_version(cargo_lock, "stwo"),
        "local_d128_recursive_backend_module_exists": (
            ROOT / "src" / "stwo_backend" / "d128_two_slice_recursive_pcd_backend.rs"
        ).exists(),
        "local_d128_recursive_proof_artifact_exists": (
            EVIDENCE_DIR / "zkai-d128-two-slice-recursive-pcd-proof-2026-05.json"
        ).exists(),
        "local_d128_recursive_verifier_handle_exists": (
            EVIDENCE_DIR / "zkai-d128-two-slice-recursive-pcd-verifier-2026-05.json"
        ).exists(),
        "external_zkvm_dependencies_declared": bool({"risc0", "sp1", "nexus", "jolt"} & dependency_names),
        "external_snark_ivc_dependencies_declared": bool(
            {"halo2", "nova", "groth16", "plonk", "snark"} & dependency_names
        ),
    }


def build_source_evidence() -> dict[str, Any]:
    two_slice = require_object(read_json_file(TWO_SLICE_ACCUMULATOR_EVIDENCE), "two_slice_accumulator", layer="source_evidence")
    full_block = require_object(read_json_file(FULL_BLOCK_ACCUMULATOR_EVIDENCE), "full_block_accumulator", layer="source_evidence")
    recursive = require_object(read_json_file(RECURSIVE_PCD_AUDIT_EVIDENCE), "recursive_pcd_audit", layer="source_evidence")

    expect_equal(two_slice.get("schema"), EXPECTED_TWO_SLICE_ACCUMULATOR_SCHEMA, "two-slice schema", layer="source_evidence")
    expect_equal(two_slice.get("result"), EXPECTED_TWO_SLICE_ACCUMULATOR_RESULT, "two-slice result", layer="source_evidence")
    expect_equal(
        two_slice.get("claim_boundary"),
        EXPECTED_TWO_SLICE_ACCUMULATOR_CLAIM_BOUNDARY,
        "two-slice claim boundary",
        layer="source_evidence",
    )
    expect_equal(full_block.get("schema"), EXPECTED_FULL_BLOCK_ACCUMULATOR_SCHEMA, "full-block schema", layer="source_evidence")
    expect_equal(full_block.get("result"), EXPECTED_FULL_BLOCK_ACCUMULATOR_RESULT, "full-block result", layer="source_evidence")
    expect_equal(
        full_block.get("claim_boundary"),
        EXPECTED_FULL_BLOCK_ACCUMULATOR_CLAIM_BOUNDARY,
        "full-block claim boundary",
        layer="source_evidence",
    )
    expect_equal(recursive.get("schema"), EXPECTED_RECURSIVE_PCD_SCHEMA, "recursive audit schema", layer="source_evidence")
    expect_equal(recursive.get("result"), EXPECTED_RECURSIVE_PCD_RESULT, "recursive audit result", layer="source_evidence")
    expect_equal(
        recursive.get("recursive_or_pcd_result"),
        EXPECTED_RECURSIVE_OR_PCD_RESULT,
        "recursive audit recursive_or_pcd_result",
        layer="source_evidence",
    )
    recursive_probe = require_object(recursive.get("backend_probe"), "recursive backend probe", layer="source_evidence")
    expect_equal(
        recursive_probe.get("selected_slice_ids"),
        list(EXPECTED_SELECTED_SLICE_IDS),
        "recursive selected slice ids",
        layer="source_evidence",
    )
    expect_equal(
        recursive_probe.get("selected_checked_rows"),
        EXPECTED_SELECTED_ROWS,
        "recursive selected checked rows",
        layer="source_evidence",
    )

    return {
        "two_slice_accumulator": source_descriptor(TWO_SLICE_ACCUMULATOR_EVIDENCE, two_slice),
        "full_block_accumulator": source_descriptor(FULL_BLOCK_ACCUMULATOR_EVIDENCE, full_block),
        "recursive_pcd_audit": source_descriptor(RECURSIVE_PCD_AUDIT_EVIDENCE, recursive),
        "two_slice_target_commitment": require_commitment(
            recursive_probe.get("two_slice_target_commitment"),
            "two_slice_target_commitment",
            layer="source_evidence",
        ),
        "two_slice_accumulator_commitment": require_commitment(
            recursive_probe.get("accumulator_commitment"),
            "two_slice_accumulator_commitment",
            layer="source_evidence",
        ),
        "two_slice_verifier_handle_commitment": require_commitment(
            recursive_probe.get("verifier_handle_commitment"),
            "two_slice_verifier_handle_commitment",
            layer="source_evidence",
        ),
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "full_block_checked_rows": EXPECTED_FULL_BLOCK_ROWS,
    }


def route_table(repo_probe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "route_id": "local_stwo_nested_verifier_air",
            "route_kind": "local_stwo_native_recursion",
            "status": "NO_GO_MISSING_NESTED_VERIFIER_AIR",
            "usable_today": False,
            "claim_boundary": "missing_executable_backend",
            "next_action": "design or import a verifier-in-AIR/circuit for the two selected d128 slice verifiers",
            "blocking_missing_object": "src/stwo_backend/d128_two_slice_recursive_pcd_backend.rs",
            "evidence": {
                "backend_module_exists": repo_probe["local_d128_recursive_backend_module_exists"],
                "requires_new_trusted_core": True,
            },
        },
        {
            "route_id": "local_stwo_pcd_outer_proof",
            "route_kind": "local_stwo_or_pcd_backend",
            "status": "NO_GO_MISSING_OUTER_PCD_PROOF_SYSTEM",
            "usable_today": False,
            "claim_boundary": "missing_executable_backend",
            "next_action": "add a PCD/IVC backend that proves the selected verifier checks and binds the same public inputs",
            "blocking_missing_object": "recursive_or_pcd_outer_proof_generator_and_verifier_handle",
            "evidence": {
                "recursive_proof_artifact_exists": repo_probe["local_d128_recursive_proof_artifact_exists"],
                "recursive_verifier_handle_exists": repo_probe["local_d128_recursive_verifier_handle_exists"],
            },
        },
        {
            "route_id": "local_two_slice_non_recursive_accumulator",
            "route_kind": "local_pre_recursive_accumulator",
            "status": "GO_PRE_RECURSIVE_INTEGRITY_ONLY",
            "usable_today": True,
            "claim_boundary": EXPECTED_TWO_SLICE_ACCUMULATOR_CLAIM_BOUNDARY,
            "next_action": "keep as source-bound handoff object; do not report recursive metrics from it",
            "blocking_missing_object": "none_for_accumulator_integrity",
            "evidence": {"source": TWO_SLICE_ACCUMULATOR_EVIDENCE.relative_to(ROOT).as_posix()},
        },
        {
            "route_id": "local_full_block_non_recursive_accumulator",
            "route_kind": "local_pre_recursive_accumulator",
            "status": "GO_PRE_RECURSIVE_INTEGRITY_ONLY",
            "usable_today": True,
            "claim_boundary": EXPECTED_FULL_BLOCK_ACCUMULATOR_CLAIM_BOUNDARY,
            "next_action": "keep as the strongest local statement-bound d128 handoff object",
            "blocking_missing_object": "none_for_accumulator_integrity",
            "evidence": {"source": FULL_BLOCK_ACCUMULATOR_EVIDENCE.relative_to(ROOT).as_posix()},
        },
        {
            "route_id": "proof_native_two_slice_compression_without_recursion",
            "route_kind": "local_non_recursive_compression_spike",
            "status": "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO",
            "usable_today": False,
            "claim_boundary": "future_proof_native_compression_not_recursion",
            "next_action": "try one proof-native object for the two-slice transcript, explicitly not recursive aggregation",
            "blocking_missing_object": "proof_native_two_slice_compression_artifact",
            "evidence": {"would_reuse": "two_slice_target_commitment", "tracked_issue": 424},
        },
        {
            "route_id": "external_zkvm_statement_receipt_adapter",
            "route_kind": "external_recursion_capable_adapter",
            "status": "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO",
            "usable_today": False,
            "claim_boundary": "external_adapter_result_until_local_stwo_recursion_exists",
            "next_action": "map the exact two-slice statement into a zkVM receipt adapter and test relabeling",
            "blocking_missing_object": "checked_external_zkvm_receipt_for_d128_two_slice_contract",
            "evidence": {
                "local_dependencies_declared": repo_probe["external_zkvm_dependencies_declared"],
                "tracked_issue": 422,
            },
        },
        {
            "route_id": "external_snark_or_ivc_statement_adapter",
            "route_kind": "external_snark_or_ivc_adapter",
            "status": "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO",
            "usable_today": False,
            "claim_boundary": "external_adapter_result_not_stwo_native",
            "next_action": "test whether a SNARK/IVC receipt can bind the same d128 two-slice statement contract",
            "blocking_missing_object": "checked_external_snark_or_ivc_receipt_for_d128_two_slice_contract",
            "evidence": {"local_dependencies_declared": repo_probe["external_snark_ivc_dependencies_declared"]},
        },
        {
            "route_id": "starknet_settlement_adapter",
            "route_kind": "settlement_adapter",
            "status": "DEFERRED_UNTIL_LOCAL_OR_EXTERNAL_PROOF_OBJECT_EXISTS",
            "usable_today": False,
            "claim_boundary": "deployment_adapter_after_proof_object",
            "next_action": "do not prioritize until one proof object exists for the same public-input contract",
            "blocking_missing_object": "proof_object_suitable_for_settlement_facts",
            "evidence": {"snip36_parked": True},
        },
    ]


def build_route_decision(routes: list[dict[str, Any]], source_evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary_blocker": PRIMARY_BLOCKER,
        "go_criterion": GO_CRITERION,
        "next_route": NEXT_ROUTE,
        "why_not_local_stwo_next": (
            "the local Stwo route is blocked before metrics because no nested verifier "
            "AIR/circuit or PCD verifier handle exists for the selected d128 slice verifiers"
        ),
        "why_external_or_proof_native_next": (
            "the statement contract and non-recursive accumulators are already bound; the "
            "next useful experiment is to test a real proof object outside the missing local "
            "nested-verifier surface, or to compress the two-slice transcript without calling it recursion"
        ),
        "selected_target": {
            "slice_ids": source_evidence["selected_slice_ids"],
            "checked_rows": source_evidence["selected_checked_rows"],
            "two_slice_target_commitment": source_evidence["two_slice_target_commitment"],
        },
        "proof_metrics": {
            "recursive_proof_size_bytes": None,
            "recursive_verifier_time_ms": None,
            "recursive_proof_generation_time_ms": None,
            "metrics_enabled": False,
            "blocked_before_metrics": True,
        },
        "usable_today_route_ids": [route["route_id"] for route in routes if route["usable_today"]],
        "candidate_route_ids": [
            route["route_id"]
            for route in routes
            if route["status"] == "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO"
        ],
    }


def validate_source_descriptor(
    descriptor: dict[str, Any],
    *,
    expected_path: pathlib.Path,
    expected_schema: str,
    expected_decision: str,
    expected_result: str,
    expected_boundary: str,
    field: str,
) -> None:
    expect_equal(
        set(descriptor),
        {"path", "file_sha256", "payload_sha256", "schema", "decision", "result", "claim_boundary"},
        f"{field} descriptor keys",
        layer="source_evidence",
    )
    require_sha256_hex(descriptor.get("file_sha256"), f"{field}.file_sha256", layer="source_evidence")
    require_sha256_hex(descriptor.get("payload_sha256"), f"{field}.payload_sha256", layer="source_evidence")
    source_payload = require_object(read_json_file(expected_path), f"{field} payload", layer="source_evidence")
    expected_descriptor = source_descriptor(expected_path, source_payload)
    expect_equal(descriptor, expected_descriptor, f"{field} descriptor", layer="source_evidence")
    expect_equal(descriptor.get("path"), expected_path.relative_to(ROOT).as_posix(), f"{field} path", layer="source_evidence")
    expect_equal(descriptor.get("schema"), expected_schema, f"{field} schema", layer="source_evidence")
    expect_equal(descriptor.get("decision"), expected_decision, f"{field} decision", layer="source_evidence")
    expect_equal(descriptor.get("result"), expected_result, f"{field} result", layer="source_evidence")
    expect_equal(
        descriptor.get("claim_boundary"),
        expected_boundary,
        f"{field} claim boundary",
        layer="source_evidence",
    )


def build_core_payload() -> dict[str, Any]:
    source_evidence = build_source_evidence()
    repo_probe = local_repo_probe()
    routes = route_table(repo_probe)
    route_decision = build_route_decision(routes, source_evidence)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "source_evidence": source_evidence,
        "local_repo_probe": repo_probe,
        "route_table": routes,
        "route_decision": route_decision,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }


def validate_source_evidence(value: Any) -> dict[str, Any]:
    source = require_object(value, "source_evidence", layer="source_evidence")
    expect_equal(set(source), {
        "two_slice_accumulator",
        "full_block_accumulator",
        "recursive_pcd_audit",
        "two_slice_target_commitment",
        "two_slice_accumulator_commitment",
        "two_slice_verifier_handle_commitment",
        "selected_slice_ids",
        "selected_checked_rows",
        "full_block_checked_rows",
    }, "source_evidence keys", layer="source_evidence")
    for key, expected_path, expected_schema, expected_decision, expected_result, expected_boundary in (
        (
            "two_slice_accumulator",
            TWO_SLICE_ACCUMULATOR_EVIDENCE,
            EXPECTED_TWO_SLICE_ACCUMULATOR_SCHEMA,
            EXPECTED_TWO_SLICE_ACCUMULATOR_DECISION,
            EXPECTED_TWO_SLICE_ACCUMULATOR_RESULT,
            EXPECTED_TWO_SLICE_ACCUMULATOR_CLAIM_BOUNDARY,
        ),
        (
            "full_block_accumulator",
            FULL_BLOCK_ACCUMULATOR_EVIDENCE,
            EXPECTED_FULL_BLOCK_ACCUMULATOR_SCHEMA,
            EXPECTED_FULL_BLOCK_ACCUMULATOR_DECISION,
            EXPECTED_FULL_BLOCK_ACCUMULATOR_RESULT,
            EXPECTED_FULL_BLOCK_ACCUMULATOR_CLAIM_BOUNDARY,
        ),
    ):
        descriptor = require_object(source[key], key, layer="source_evidence")
        validate_source_descriptor(
            descriptor,
            expected_path=expected_path,
            expected_schema=expected_schema,
            expected_decision=expected_decision,
            expected_result=expected_result,
            expected_boundary=expected_boundary,
            field=key,
        )
        expect_equal(descriptor.get("schema"), expected_schema, f"{key} schema", layer="source_evidence")
        expect_equal(descriptor.get("decision"), expected_decision, f"{key} decision", layer="source_evidence")
        expect_equal(descriptor.get("result"), expected_result, f"{key} result", layer="source_evidence")
        expect_equal(descriptor.get("claim_boundary"), expected_boundary, f"{key} claim boundary", layer="source_evidence")
    recursive = require_object(source["recursive_pcd_audit"], "recursive_pcd_audit", layer="source_evidence")
    validate_source_descriptor(
        recursive,
        expected_path=RECURSIVE_PCD_AUDIT_EVIDENCE,
        expected_schema=EXPECTED_RECURSIVE_PCD_SCHEMA,
        expected_decision=EXPECTED_RECURSIVE_PCD_DECISION,
        expected_result=EXPECTED_RECURSIVE_PCD_RESULT,
        expected_boundary=EXPECTED_RECURSIVE_PCD_CLAIM_BOUNDARY,
        field="recursive_pcd_audit",
    )
    expect_equal(recursive.get("schema"), EXPECTED_RECURSIVE_PCD_SCHEMA, "recursive schema", layer="source_evidence")
    expect_equal(recursive.get("decision"), EXPECTED_RECURSIVE_PCD_DECISION, "recursive decision", layer="source_evidence")
    expect_equal(recursive.get("result"), EXPECTED_RECURSIVE_PCD_RESULT, "recursive result", layer="source_evidence")
    expect_equal(
        recursive.get("claim_boundary"),
        EXPECTED_RECURSIVE_PCD_CLAIM_BOUNDARY,
        "recursive claim boundary",
            layer="source_evidence",
        )
    expect_equal(source.get("selected_slice_ids"), list(EXPECTED_SELECTED_SLICE_IDS), "selected slice ids", layer="source_evidence")
    expect_equal(source.get("selected_checked_rows"), EXPECTED_SELECTED_ROWS, "selected rows", layer="source_evidence")
    expect_equal(source.get("full_block_checked_rows"), EXPECTED_FULL_BLOCK_ROWS, "full block rows", layer="source_evidence")
    recursive_payload = require_object(read_json_file(RECURSIVE_PCD_AUDIT_EVIDENCE), "recursive payload", layer="source_evidence")
    recursive_source_accumulator = require_object(
        recursive_payload.get("source_accumulator"),
        "recursive source_accumulator",
        layer="source_evidence",
    )
    recursive_backend_probe = require_object(
        recursive_payload.get("backend_probe"),
        "recursive backend_probe",
        layer="source_evidence",
    )
    expect_equal(
        recursive_source_accumulator.get("path"),
        source["two_slice_accumulator"]["path"],
        "recursive source accumulator path",
        layer="source_evidence",
    )
    expect_equal(
        recursive_source_accumulator.get("file_sha256"),
        source["two_slice_accumulator"]["file_sha256"],
        "recursive source accumulator file hash",
        layer="source_evidence",
    )
    expect_equal(
        recursive_source_accumulator.get("payload_sha256"),
        source["two_slice_accumulator"]["payload_sha256"],
        "recursive source accumulator payload hash",
        layer="source_evidence",
    )
    expect_equal(
        recursive_source_accumulator.get("decision"),
        source["two_slice_accumulator"]["decision"],
        "recursive source accumulator decision",
        layer="source_evidence",
    )
    expect_equal(
        recursive_source_accumulator.get("result"),
        source["two_slice_accumulator"]["result"],
        "recursive source accumulator result",
        layer="source_evidence",
    )
    expect_equal(
        recursive_source_accumulator.get("claim_boundary"),
        source["two_slice_accumulator"]["claim_boundary"],
        "recursive source accumulator claim boundary",
        layer="source_evidence",
    )
    source_target_commitment = require_commitment(
        source.get("two_slice_target_commitment"),
        "two_slice_target_commitment",
        layer="source_evidence",
    )
    source_accumulator_commitment = require_commitment(
        source.get("two_slice_accumulator_commitment"),
        "two_slice_accumulator_commitment",
        layer="source_evidence",
    )
    source_verifier_handle_commitment = require_commitment(
        source.get("two_slice_verifier_handle_commitment"),
        "two_slice_verifier_handle_commitment",
        layer="source_evidence",
    )
    expect_equal(
        source_target_commitment,
        recursive_backend_probe.get("two_slice_target_commitment"),
        "recursive backend target commitment",
        layer="source_evidence",
    )
    expect_equal(
        source_accumulator_commitment,
        recursive_backend_probe.get("accumulator_commitment"),
        "recursive backend accumulator commitment",
        layer="source_evidence",
    )
    expect_equal(
        source_verifier_handle_commitment,
        recursive_backend_probe.get("verifier_handle_commitment"),
        "recursive backend verifier handle commitment",
        layer="source_evidence",
    )
    expect_equal(
        source_target_commitment,
        recursive_source_accumulator.get("two_slice_target_commitment"),
        "recursive source target commitment",
        layer="source_evidence",
    )
    expect_equal(
        source_accumulator_commitment,
        recursive_source_accumulator.get("accumulator_commitment"),
        "recursive source accumulator commitment",
        layer="source_evidence",
    )
    expect_equal(
        source_verifier_handle_commitment,
        recursive_source_accumulator.get("verifier_handle_commitment"),
        "recursive source verifier handle commitment",
        layer="source_evidence",
    )
    return source


def validate_local_repo_probe(value: Any) -> dict[str, Any]:
    probe = require_object(value, "local_repo_probe")
    expect_equal(set(probe), {
        "cargo_toml_sha256",
        "cargo_lock_sha256",
        "stwo_dependency_declared",
        "stwo_constraint_framework_declared",
        "local_stwo_version",
        "local_d128_recursive_backend_module_exists",
        "local_d128_recursive_proof_artifact_exists",
        "local_d128_recursive_verifier_handle_exists",
        "external_zkvm_dependencies_declared",
        "external_snark_ivc_dependencies_declared",
    }, "local_repo_probe keys")
    require_sha256_hex(probe.get("cargo_toml_sha256"), "cargo_toml_sha256")
    require_sha256_hex(probe.get("cargo_lock_sha256"), "cargo_lock_sha256")
    expect_equal(probe.get("cargo_toml_sha256"), file_sha256(ROOT / "Cargo.toml"), "Cargo.toml sha256")
    expect_equal(probe.get("cargo_lock_sha256"), file_sha256(ROOT / "Cargo.lock"), "Cargo.lock sha256")
    expect_equal(probe.get("stwo_dependency_declared"), True, "Stwo dependency declared")
    expect_equal(probe.get("stwo_constraint_framework_declared"), True, "Stwo constraint framework declared")
    expect_equal(probe.get("local_stwo_version"), "2.2.0", "local Stwo version")
    expect_equal(probe.get("local_d128_recursive_backend_module_exists"), False, "local recursive backend module exists")
    expect_equal(probe.get("local_d128_recursive_proof_artifact_exists"), False, "local recursive proof artifact exists")
    expect_equal(probe.get("local_d128_recursive_verifier_handle_exists"), False, "local recursive verifier handle exists")
    return probe


def validate_route_evidence(route_id: str, evidence: Any) -> dict[str, Any]:
    evidence = require_object(evidence, f"{route_id}.evidence", layer="route_table")
    if route_id == "local_stwo_nested_verifier_air":
        expect_equal(set(evidence), {"backend_module_exists", "requires_new_trusted_core"}, f"{route_id}.evidence keys", layer="route_table")
        expect_equal(require_bool(evidence.get("backend_module_exists"), f"{route_id}.backend_module_exists", layer="route_table"), False, f"{route_id}.backend_module_exists", layer="route_table")
        expect_equal(require_bool(evidence.get("requires_new_trusted_core"), f"{route_id}.requires_new_trusted_core", layer="route_table"), True, f"{route_id}.requires_new_trusted_core", layer="route_table")
    elif route_id == "local_stwo_pcd_outer_proof":
        expect_equal(set(evidence), {"recursive_proof_artifact_exists", "recursive_verifier_handle_exists"}, f"{route_id}.evidence keys", layer="route_table")
        expect_equal(require_bool(evidence.get("recursive_proof_artifact_exists"), f"{route_id}.recursive_proof_artifact_exists", layer="route_table"), False, f"{route_id}.recursive_proof_artifact_exists", layer="route_table")
        expect_equal(require_bool(evidence.get("recursive_verifier_handle_exists"), f"{route_id}.recursive_verifier_handle_exists", layer="route_table"), False, f"{route_id}.recursive_verifier_handle_exists", layer="route_table")
    elif route_id == "local_two_slice_non_recursive_accumulator":
        expect_equal(set(evidence), {"source"}, f"{route_id}.evidence keys", layer="route_table")
        require_safe_evidence_path(
            evidence.get("source"),
            f"{route_id}.source",
            expected=TWO_SLICE_ACCUMULATOR_EVIDENCE.relative_to(ROOT).as_posix(),
        )
    elif route_id == "local_full_block_non_recursive_accumulator":
        expect_equal(set(evidence), {"source"}, f"{route_id}.evidence keys", layer="route_table")
        require_safe_evidence_path(
            evidence.get("source"),
            f"{route_id}.source",
            expected=FULL_BLOCK_ACCUMULATOR_EVIDENCE.relative_to(ROOT).as_posix(),
        )
    elif route_id == "proof_native_two_slice_compression_without_recursion":
        expect_equal(set(evidence), {"would_reuse", "tracked_issue"}, f"{route_id}.evidence keys", layer="route_table")
        expect_equal(require_str(evidence.get("would_reuse"), f"{route_id}.would_reuse", layer="route_table"), "two_slice_target_commitment", f"{route_id}.would_reuse", layer="route_table")
        expect_equal(require_int(evidence.get("tracked_issue"), f"{route_id}.tracked_issue", layer="route_table"), 424, f"{route_id}.tracked_issue", layer="route_table")
    elif route_id == "external_zkvm_statement_receipt_adapter":
        expect_equal(set(evidence), {"local_dependencies_declared", "tracked_issue"}, f"{route_id}.evidence keys", layer="route_table")
        require_bool(evidence.get("local_dependencies_declared"), f"{route_id}.local_dependencies_declared", layer="route_table")
        expect_equal(require_int(evidence.get("tracked_issue"), f"{route_id}.tracked_issue", layer="route_table"), 422, f"{route_id}.tracked_issue", layer="route_table")
    elif route_id == "external_snark_or_ivc_statement_adapter":
        expect_equal(set(evidence), {"local_dependencies_declared"}, f"{route_id}.evidence keys", layer="route_table")
        require_bool(evidence.get("local_dependencies_declared"), f"{route_id}.local_dependencies_declared", layer="route_table")
    elif route_id == "starknet_settlement_adapter":
        expect_equal(set(evidence), {"snip36_parked"}, f"{route_id}.evidence keys", layer="route_table")
        expect_equal(require_bool(evidence.get("snip36_parked"), f"{route_id}.snip36_parked", layer="route_table"), True, f"{route_id}.snip36_parked", layer="route_table")
    else:
        raise D128RecursivePCDRouteSelectorError(f"unknown route evidence id: {route_id}", layer="route_table")
    return evidence


def validate_route_table(value: Any) -> list[dict[str, Any]]:
    routes = require_list(value, "route_table", layer="route_table")
    route_objects = [
        require_object(route, f"route_table[{index}]", layer="route_table")
        for index, route in enumerate(routes)
    ]
    expect_equal([route.get("route_id") for route in route_objects], list(ROUTE_IDS), "route ids", layer="route_table")
    by_id: dict[str, dict[str, Any]] = {}
    for route in route_objects:
        expect_equal(set(route), {
            "route_id",
            "route_kind",
            "status",
            "usable_today",
            "claim_boundary",
            "next_action",
            "blocking_missing_object",
            "evidence",
        }, "route keys", layer="route_table")
        route_id = require_str(route.get("route_id"), "route_id", layer="route_table")
        by_id[route_id] = route
        require_str(route.get("route_kind"), f"{route_id}.route_kind", layer="route_table")
        require_str(route.get("status"), f"{route_id}.status", layer="route_table")
        require_bool(route.get("usable_today"), f"{route_id}.usable_today", layer="route_table")
        require_str(route.get("claim_boundary"), f"{route_id}.claim_boundary", layer="route_table")
        require_str(route.get("next_action"), f"{route_id}.next_action", layer="route_table")
        require_str(route.get("blocking_missing_object"), f"{route_id}.blocking_missing_object", layer="route_table")
        validate_route_evidence(route_id, route.get("evidence"))

    expect_equal(
        by_id["local_stwo_nested_verifier_air"]["status"],
        "NO_GO_MISSING_NESTED_VERIFIER_AIR",
        "local nested verifier status",
        layer="route_table",
    )
    expect_equal(by_id["local_stwo_nested_verifier_air"]["usable_today"], False, "local nested verifier usable", layer="route_table")
    expect_equal(
        by_id["local_stwo_pcd_outer_proof"]["status"],
        "NO_GO_MISSING_OUTER_PCD_PROOF_SYSTEM",
        "local PCD status",
        layer="route_table",
    )
    expect_equal(by_id["local_stwo_pcd_outer_proof"]["usable_today"], False, "local PCD usable", layer="route_table")
    for route_id in ("local_two_slice_non_recursive_accumulator", "local_full_block_non_recursive_accumulator"):
        expect_equal(by_id[route_id]["status"], "GO_PRE_RECURSIVE_INTEGRITY_ONLY", f"{route_id} status", layer="route_table")
        expect_equal(by_id[route_id]["usable_today"], True, f"{route_id} usable", layer="route_table")
        if by_id[route_id]["claim_boundary"] != "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF":
            raise D128RecursivePCDRouteSelectorError(
                f"{route_id} claim boundary must stay explicitly non-recursive",
                layer="route_table",
            )
    for route_id in (
        "proof_native_two_slice_compression_without_recursion",
        "external_zkvm_statement_receipt_adapter",
        "external_snark_or_ivc_statement_adapter",
    ):
        expect_equal(by_id[route_id]["status"], "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO", f"{route_id} status", layer="route_table")
        expect_equal(by_id[route_id]["usable_today"], False, f"{route_id} usable", layer="route_table")
    expect_equal(
        by_id["starknet_settlement_adapter"]["status"],
        "DEFERRED_UNTIL_LOCAL_OR_EXTERNAL_PROOF_OBJECT_EXISTS",
        "settlement route status",
        layer="route_table",
    )
    return route_objects


def validate_route_decision(value: Any, source: dict[str, Any], routes: list[dict[str, Any]]) -> dict[str, Any]:
    decision = require_object(value, "route_decision", layer="route_decision")
    expect_equal(set(decision), {
        "primary_blocker",
        "go_criterion",
        "next_route",
        "why_not_local_stwo_next",
        "why_external_or_proof_native_next",
        "selected_target",
        "proof_metrics",
        "usable_today_route_ids",
        "candidate_route_ids",
    }, "route_decision keys", layer="route_decision")
    expect_equal(decision.get("primary_blocker"), PRIMARY_BLOCKER, "primary blocker", layer="route_decision")
    expect_equal(decision.get("go_criterion"), GO_CRITERION, "go criterion", layer="route_decision")
    expect_equal(decision.get("next_route"), NEXT_ROUTE, "next route", layer="route_decision")

    selected_target = require_object(decision.get("selected_target"), "selected_target", layer="route_decision")
    expect_equal(selected_target.get("slice_ids"), source["selected_slice_ids"], "selected target slice ids", layer="route_decision")
    expect_equal(selected_target.get("checked_rows"), source["selected_checked_rows"], "selected target rows", layer="route_decision")
    expect_equal(
        selected_target.get("two_slice_target_commitment"),
        source["two_slice_target_commitment"],
        "selected target commitment",
        layer="route_decision",
    )
    metrics = require_object(decision.get("proof_metrics"), "proof_metrics", layer="route_decision")
    expect_equal(metrics.get("metrics_enabled"), False, "metrics enabled", layer="route_decision")
    expect_equal(metrics.get("blocked_before_metrics"), True, "blocked before metrics", layer="route_decision")
    for key in ("recursive_proof_size_bytes", "recursive_verifier_time_ms", "recursive_proof_generation_time_ms"):
        expect_equal(metrics.get(key), None, key, layer="route_decision")

    usable_ids = [route["route_id"] for route in routes if route["usable_today"]]
    candidate_ids = [
        route["route_id"]
        for route in routes
        if route["status"] == "RESEARCH_SPIKE_CANDIDATE_NOT_YET_GO"
    ]
    expect_equal(decision.get("usable_today_route_ids"), usable_ids, "usable_today_route_ids", layer="route_decision")
    expect_equal(decision.get("candidate_route_ids"), candidate_ids, "candidate_route_ids", layer="route_decision")
    return decision


BASE_TOP_LEVEL_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "source_evidence",
    "local_repo_probe",
    "route_table",
    "route_decision",
    "non_claims",
    "validation_commands",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_TOP_LEVEL_KEYS = BASE_TOP_LEVEL_KEYS | MUTATION_KEYS


def validate_core_payload(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "payload")
    expect_equal(set(payload), BASE_TOP_LEVEL_KEYS, "core payload keys")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("issue"), ISSUE, "issue")
    source = validate_source_evidence(payload.get("source_evidence"))
    validate_local_repo_probe(payload.get("local_repo_probe"))
    routes = validate_route_table(payload.get("route_table"))
    validate_route_decision(payload.get("route_decision"), source, routes)
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non_claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation_commands")
    return payload


def mutation_surface(mutation: str) -> str:
    for expected, surface in EXPECTED_MUTATION_INVENTORY:
        if expected == mutation:
            return surface
    raise D128RecursivePCDRouteSelectorError(f"unknown mutation {mutation}")


def mutate_payload(payload: dict[str, Any], mutation: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    def find_route(route_id: str) -> dict[str, Any]:
        for route in mutated["route_table"]:
            if route["route_id"] == route_id:
                return route
        raise AssertionError(route_id)

    if mutation == "source_two_slice_file_hash_drift":
        mutated["source_evidence"]["two_slice_accumulator"]["file_sha256"] = "0" * 64
    elif mutation == "source_recursive_path_drift":
        mutated["source_evidence"]["recursive_pcd_audit"]["path"] = "docs/engineering/evidence/other.json"
    elif mutation == "source_two_slice_result_drift":
        mutated["source_evidence"]["two_slice_accumulator"]["result"] = "NO_GO"
    elif mutation == "source_two_slice_claim_boundary_drift":
        mutated["source_evidence"]["two_slice_accumulator"]["claim_boundary"] = "RECURSIVE_OUTER_PROOF"
    elif mutation == "source_full_block_result_drift":
        mutated["source_evidence"]["full_block_accumulator"]["result"] = "NO_GO"
    elif mutation == "source_recursive_no_go_result_changed_to_go":
        mutated["source_evidence"]["recursive_pcd_audit"]["result"] = "GO"
    elif mutation == "source_recursive_blocker_removed":
        mutated["source_evidence"]["recursive_pcd_audit"]["result"] = "GO"
        mutated["source_evidence"]["recursive_pcd_audit"]["decision"] = "GO_RECURSIVE_PCD"
    elif mutation == "route_local_stwo_nested_verifier_relabel_to_go":
        route = find_route("local_stwo_nested_verifier_air")
        route["status"] = "GO_RECURSIVE_BACKEND"
        route["usable_today"] = True
    elif mutation == "route_local_pcd_relabel_to_go":
        route = find_route("local_stwo_pcd_outer_proof")
        route["status"] = "GO_PCD_BACKEND"
        route["usable_today"] = True
    elif mutation == "route_external_adapter_relabel_to_go":
        route = find_route("external_zkvm_statement_receipt_adapter")
        route["status"] = "GO_EXTERNAL_RECURSIVE_ADAPTER"
        route["usable_today"] = True
    elif mutation == "route_removed":
        mutated["route_table"] = [
            route for route in mutated["route_table"] if route["route_id"] != "local_stwo_nested_verifier_air"
        ]
    elif mutation == "blocking_missing_object_removed":
        find_route("local_stwo_nested_verifier_air")["blocking_missing_object"] = ""
    elif mutation == "next_route_changed_to_local_recursive":
        mutated["route_decision"]["next_route"] = "LOCAL_STWO_RECURSIVE_BACKEND_GO"
    elif mutation == "primary_blocker_removed":
        mutated["route_decision"]["primary_blocker"] = ""
    elif mutation == "proof_size_metric_smuggled":
        mutated["route_decision"]["proof_metrics"]["recursive_proof_size_bytes"] = 1024
        mutated["route_decision"]["proof_metrics"]["metrics_enabled"] = True
    elif mutation == "verifier_time_metric_smuggled":
        mutated["route_decision"]["proof_metrics"]["recursive_verifier_time_ms"] = 1.0
        mutated["route_decision"]["proof_metrics"]["metrics_enabled"] = True
    elif mutation == "proof_generation_time_metric_smuggled":
        mutated["route_decision"]["proof_metrics"]["recursive_proof_generation_time_ms"] = 10.0
        mutated["route_decision"]["proof_metrics"]["metrics_enabled"] = True
    elif mutation == "decision_changed_to_go":
        mutated["decision"] = "GO_D128_RECURSIVE_PCD_BACKEND"
    elif mutation == "result_changed_to_go":
        mutated["result"] = "GO"
    elif mutation == "issue_changed":
        mutated["issue"] = 0
    elif mutation == "go_criterion_weakened":
        mutated["route_decision"]["go_criterion"] = "accumulator exists"
    elif mutation == "non_claims_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif mutation == "validation_command_drift":
        mutated["validation_commands"] = mutated["validation_commands"][:-1]
    elif mutation == "unknown_top_level_field_added":
        mutated["invented_recursive_success"] = True
    else:
        raise D128RecursivePCDRouteSelectorError(f"unknown mutation {mutation}")
    return mutated


def build_mutation_cases(core_payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY):
        mutated = mutate_payload(core_payload, mutation)
        try:
            validate_core_payload(mutated)
        except D128RecursivePCDRouteSelectorError as err:
            cases.append(
                {
                    "index": index,
                    "mutation": mutation,
                    "surface": surface,
                    "baseline_result": RESULT,
                    "mutated_accepted": False,
                    "rejected": True,
                    "rejection_layer": err.layer,
                    "error": str(err),
                }
            )
        else:
            cases.append(
                {
                    "index": index,
                    "mutation": mutation,
                    "surface": surface,
                    "baseline_result": RESULT,
                    "mutated_accepted": True,
                    "rejected": False,
                    "rejection_layer": "none",
                    "error": "",
                }
            )
    return cases


def build_gate_result() -> dict[str, Any]:
    core = build_core_payload()
    validate_core_payload(core)
    cases = build_mutation_cases(core)
    payload = {
        **core,
        "mutation_inventory": [
            {"mutation": mutation, "surface": surface}
            for mutation, surface in EXPECTED_MUTATION_INVENTORY
        ],
        "cases": cases,
        "case_count": len(cases),
        "all_mutations_rejected": all(case["rejected"] and not case["mutated_accepted"] for case in cases),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "payload")
    expect_equal(set(payload), FINAL_TOP_LEVEL_KEYS, "top-level payload keys")
    core = {key: payload[key] for key in BASE_TOP_LEVEL_KEYS}
    validate_core_payload(core)
    inventory = require_list(payload.get("mutation_inventory"), "mutation_inventory")
    inventory_objects = [
        require_object(item, f"mutation_inventory[{index}]")
        for index, item in enumerate(inventory)
    ]
    expect_equal(
        [(item.get("mutation"), item.get("surface")) for item in inventory_objects],
        list(EXPECTED_MUTATION_INVENTORY),
        "mutation_inventory",
    )
    for index, item in enumerate(inventory_objects):
        expect_equal(set(item), {"mutation", "surface"}, f"mutation_inventory[{index}] keys")
    cases = require_list(payload.get("cases"), "cases")
    expect_equal(payload.get("case_count"), len(EXPECTED_MUTATION_INVENTORY), "case_count")
    expect_equal(len(cases), len(EXPECTED_MUTATION_INVENTORY), "case count")
    for index, case in enumerate(cases):
        case = require_object(case, f"cases[{index}]")
        expect_equal(
            set(case),
            {"index", "mutation", "surface", "baseline_result", "mutated_accepted", "rejected", "rejection_layer", "error"},
            f"cases[{index}] keys",
        )
        mutation, surface = EXPECTED_MUTATION_INVENTORY[index]
        expect_equal(case.get("index"), index, f"cases[{index}].index")
        expect_equal(case.get("mutation"), mutation, f"cases[{index}].mutation")
        expect_equal(case.get("surface"), surface, f"cases[{index}].surface")
        expect_equal(case.get("baseline_result"), RESULT, f"cases[{index}].baseline_result")
        expect_equal(case.get("mutated_accepted"), False, f"cases[{index}].mutated_accepted")
        expect_equal(case.get("rejected"), True, f"cases[{index}].rejected")
        require_str(case.get("rejection_layer"), f"cases[{index}].rejection_layer")
        require_str(case.get("error"), f"cases[{index}].error")
    expect_equal(payload.get("all_mutations_rejected"), True, "all_mutations_rejected")
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for route in payload["route_table"]:
        writer.writerow({column: route[column] for column in TSV_COLUMNS})
    return out.getvalue()


def _ensure_repo_relative(path: pathlib.Path | None, *, field: str) -> pathlib.Path | None:
    if path is None:
        return None
    if path.is_absolute():
        raise D128RecursivePCDRouteSelectorError(f"{field} must be repo-relative")
    normalized = pathlib.Path(path.as_posix())
    if any(part == ".." for part in normalized.parts):
        raise D128RecursivePCDRouteSelectorError(f"{field} must be repo-relative without traversal")
    return normalized


def _ensure_evidence_output(path: pathlib.Path | None, *, field: str, suffix: str) -> pathlib.Path | None:
    normalized = _ensure_repo_relative(path, field=field)
    if normalized is None:
        return None
    if normalized.suffix != suffix:
        raise D128RecursivePCDRouteSelectorError(f"{field} must end with {suffix}")
    full_path = (ROOT / normalized).resolve()
    try:
        full_path.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise D128RecursivePCDRouteSelectorError(
            f"{field} must stay under {EVIDENCE_DIR.relative_to(ROOT).as_posix()}",
        ) from err
    return normalized


def _atomic_write(path: pathlib.Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            tmp.write(data)
            tmp_path = pathlib.Path(tmp.name)
        tmp_path.replace(path)
    except Exception:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        raise


def write_outputs(payload: dict[str, Any], json_out: pathlib.Path | None, tsv_out: pathlib.Path | None) -> None:
    json_out = _ensure_evidence_output(json_out, field="json output path", suffix=".json")
    tsv_out = _ensure_evidence_output(tsv_out, field="tsv output path", suffix=".tsv")
    if json_out is not None and tsv_out is not None and json_out == tsv_out:
        raise D128RecursivePCDRouteSelectorError("json and tsv output paths must be distinct")
    if json_out is not None:
        _atomic_write(ROOT / json_out, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if tsv_out is not None:
        _atomic_write(ROOT / tsv_out, to_tsv(payload))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    payload = build_gate_result()
    json_out = args.write_json
    tsv_out = args.write_tsv
    if json_out is None and tsv_out is None:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    write_outputs(payload, json_out, tsv_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
