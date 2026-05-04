#!/usr/bin/env python3
"""Audit cryptographic-backend availability for the d128 two-slice contract.

This gate answers issue #426.  It consumes the checked proof-native d128
two-slice transcript/public-input compression artifact from issue #424 and
asks a stricter question: does any executable cryptographic backend in this
repository prove or receipt that exact contract today?

The answer is allowed to be a bounded no-go.  A backend route is GO only if a
real proof/receipt/PCD/zkVM/SNARK artifact and verifier handle exist and bind
the #424 public-input contract.  This script deliberately refuses to infer
proof size, verifier time, or proof-generation metrics from the compressed
transcript object itself.
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
import os
import pathlib
import secrets
import stat
import sys
import tomllib
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
PROOF_NATIVE_SCRIPT = ROOT / "scripts" / "zkai_d128_proof_native_two_slice_compression_gate.py"
PROOF_NATIVE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-proof-native-two-slice-compression-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-cryptographic-backend-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-cryptographic-backend-2026-05.tsv"

SCHEMA = "zkai-d128-cryptographic-backend-gate-v1"
DECISION = "NO_GO_D128_CRYPTOGRAPHIC_BACKEND_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT"
RESULT = "BOUNDED_NO_GO"
ISSUE = 426
SOURCE_ISSUE = 424
CLAIM_BOUNDARY = "PROOF_NATIVE_TWO_SLICE_CONTRACT_AVAILABLE_BACKEND_MISSING"
PRIMARY_BLOCKER = "NO_EXECUTABLE_CRYPTOGRAPHIC_BACKEND_ARTIFACT_FOR_D128_TWO_SLICE_CONTRACT"
FIRST_MISSING_OBJECT = (
    "nested verifier AIR/circuit or external zkVM/SNARK/IVC receipt artifact "
    "that proves the #424 public-input contract"
)
GO_CRITERION = (
    "a real executable proof, PCD, zkVM, SNARK/IVC, or recursive-verifier artifact exists; "
    "a verifier handle accepts it; and its public inputs or receipt journal bind the #424 "
    "two_slice_target_commitment, selected statement commitments, source evidence hashes, "
    "public-instance commitments, proof-native parameter commitments, verifier domain, "
    "backend version, source accumulator commitment, and source verifier-handle commitment"
)
NEXT_ROUTE = "EXTERNAL_ZKVM_STATEMENT_RECEIPT_ADAPTER_TRACKED_BY_422_OR_LOCAL_NESTED_VERIFIER_DESIGN"

EXPECTED_PROOF_NATIVE_SCHEMA = "zkai-d128-proof-native-two-slice-compression-gate-v1"
EXPECTED_PROOF_NATIVE_DECISION = "GO_D128_PROOF_NATIVE_TWO_SLICE_TRANSCRIPT_COMPRESSION"
EXPECTED_PROOF_NATIVE_RESULT = "GO"
EXPECTED_COMPRESSION_RESULT = "GO_PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION"
EXPECTED_RECURSIVE_OR_PCD_RESULT = "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING"
EXPECTED_PROOF_NATIVE_CLAIM_BOUNDARY = "PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION"
EXPECTED_SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")
EXPECTED_SELECTED_ROWS = 256

DEPENDENCY_TABLE_KEYS = frozenset({"dependencies", "dev-dependencies", "build-dependencies"})
EXTERNAL_ZKVM_DEPENDENCIES = frozenset(
    {"risc0", "risc0-zkvm", "sp1", "sp1-sdk", "nexus", "nexus-sdk", "jolt", "jolt-core", "jolt-sdk"}
)
EXTERNAL_SNARK_IVC_DEPENDENCIES = frozenset(
    {"halo2", "halo2_proofs", "nova", "nova-snark", "groth16", "ark-groth16", "plonk", "snark"}
)

FIXED_BACKEND_ARTIFACTS = (
    (
        "local_stwo_nested_verifier_module",
        "src/stwo_backend/d128_two_slice_recursive_pcd_backend.rs",
    ),
    (
        "local_recursive_pcd_proof_artifact",
        "docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-proof-2026-05.json",
    ),
    (
        "local_recursive_pcd_verifier_handle",
        "docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-verifier-2026-05.json",
    ),
    (
        "external_zkvm_statement_receipt_artifact",
        "docs/engineering/evidence/zkai-d128-zkvm-statement-receipt-2026-05.json",
    ),
    (
        "external_snark_ivc_statement_receipt_artifact",
        "docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.json",
    ),
)

CANDIDATE_ARTIFACT_GLOBS = (
    "docs/engineering/evidence/zkai-d128-*risc0*.json",
    "docs/engineering/evidence/zkai-d128-*sp1*.json",
    "docs/engineering/evidence/zkai-d128-*zkvm*.json",
    "docs/engineering/evidence/zkai-d128-*snark*.json",
    "docs/engineering/evidence/zkai-d128-*ivc*.json",
    "docs/engineering/evidence/zkai-d128-*recursive-pcd-proof*.json",
)

NON_CLAIMS = [
    "not recursive aggregation",
    "not proof-carrying data",
    "not STARK-in-STARK verification",
    "not a zkVM receipt",
    "not a SNARK or IVC receipt",
    "not proof-size evidence for a cryptographic backend",
    "not verifier-time evidence for a cryptographic backend",
    "not proof-generation-time evidence for a cryptographic backend",
    "not a claim that RISC Zero, SP1, Halo2, Nova, or other external systems cannot implement the contract",
    "not a public zkML benchmark row",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_cryptographic_backend_gate.py --write-json docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_cryptographic_backend_gate",
    "python3 -m py_compile scripts/zkai_d128_cryptographic_backend_gate.py scripts/tests/test_zkai_d128_cryptographic_backend_gate.py",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
]

ROUTE_IDS = (
    "source_proof_native_two_slice_contract",
    "local_stwo_nested_verifier_backend",
    "local_pcd_or_ivc_outer_proof_backend",
    "external_zkvm_statement_receipt_backend",
    "external_snark_or_ivc_statement_receipt_backend",
    "starknet_settlement_adapter",
)

TSV_COLUMNS = (
    "route_id",
    "route_kind",
    "status",
    "cryptographic_backend",
    "usable_today",
    "claim_boundary",
    "blocking_missing_object",
    "next_action",
)

EXPECTED_MUTATION_INVENTORY = (
    ("source_file_hash_drift", "source_proof_native_contract"),
    ("source_payload_hash_drift", "source_proof_native_contract"),
    ("source_result_drift", "source_proof_native_contract"),
    ("source_compression_result_drift", "source_proof_native_contract"),
    ("source_recursive_result_relabel_to_go", "source_proof_native_contract"),
    ("source_claim_boundary_drift", "source_proof_native_contract"),
    ("source_target_commitment_drift", "source_public_input_contract"),
    ("source_selected_statement_drift", "source_public_input_contract"),
    ("source_selected_source_hash_drift", "source_public_input_contract"),
    ("source_selected_public_instance_drift", "source_public_input_contract"),
    ("source_selected_parameter_commitment_drift", "source_public_input_contract"),
    ("source_verifier_domain_drift", "source_public_input_contract"),
    ("source_required_backend_version_drift", "source_public_input_contract"),
    ("source_accumulator_commitment_drift", "source_public_input_contract"),
    ("source_verifier_handle_commitment_drift", "source_public_input_contract"),
    ("compressed_artifact_commitment_drift", "source_proof_native_contract"),
    ("verifier_handle_commitment_drift", "source_proof_native_contract"),
    ("repo_probe_cargo_hash_drift", "backend_probe"),
    ("repo_probe_dependency_hint_drift", "backend_probe"),
    ("repo_probe_artifact_presence_relabeling", "backend_probe"),
    ("route_local_nested_verifier_relabel_to_go", "backend_routes"),
    ("route_local_pcd_relabel_to_go", "backend_routes"),
    ("route_external_zkvm_relabel_to_go", "backend_routes"),
    ("route_external_snark_relabel_to_go", "backend_routes"),
    ("route_blocker_removed", "backend_routes"),
    ("route_metric_smuggled", "backend_routes"),
    ("backend_decision_changed_to_go", "backend_decision"),
    ("primary_blocker_removed", "backend_decision"),
    ("proof_size_metric_smuggled", "backend_decision"),
    ("verifier_time_metric_smuggled", "backend_decision"),
    ("proof_generation_time_metric_smuggled", "backend_decision"),
    ("next_route_changed_to_settlement", "backend_decision"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
    ("unknown_top_level_field_added", "parser_or_schema"),
)

TOP_LEVEL_KEYS = {
    "all_mutations_rejected",
    "backend_decision",
    "backend_probe",
    "backend_routes",
    "case_count",
    "cases",
    "claim_boundary",
    "decision",
    "issue",
    "mutation_inventory",
    "non_claims",
    "result",
    "schema",
    "source_proof_native_contract",
    "summary",
    "validation_commands",
}
DRAFT_TOP_LEVEL_KEYS = TOP_LEVEL_KEYS - {"all_mutations_rejected", "case_count", "cases", "mutation_inventory"}

SOURCE_CONTRACT_KEYS = {
    "claim_boundary",
    "compressed_artifact_commitment",
    "compression_metrics",
    "compression_result",
    "decision",
    "file_sha256",
    "issue",
    "path",
    "payload_sha256",
    "public_input_contract",
    "recursive_or_pcd_result",
    "result",
    "schema",
    "selected_checked_rows",
    "selected_slice_ids",
    "two_slice_target_commitment",
    "verifier_handle_commitment",
}
PUBLIC_INPUT_CONTRACT_KEYS = {
    "required_backend_version",
    "required_public_inputs",
    "selected_slice_proof_native_parameter_commitments",
    "selected_slice_public_instance_commitments",
    "selected_slice_statement_commitments",
    "selected_source_evidence_hashes",
    "source_accumulator_commitment",
    "source_verifier_handle_commitment",
    "two_slice_target_commitment",
    "verifier_domain",
}
BACKEND_PROBE_KEYS = {
    "artifact_candidates",
    "cargo_lock_sha256",
    "cargo_toml_sha256",
    "external_snark_ivc_dependencies_declared",
    "external_snark_ivc_dependency_names",
    "external_zkvm_dependencies_declared",
    "external_zkvm_dependency_names",
    "fixed_backend_artifacts",
    "local_stwo_version",
}
ARTIFACT_STATUS_KEYS = {"artifact_id", "exists", "path"}
ROUTE_KEYS = {
    "blocking_missing_object",
    "claim_boundary",
    "cryptographic_backend",
    "evidence",
    "next_action",
    "proof_metrics",
    "route_id",
    "route_kind",
    "status",
    "usable_today",
}
ROUTE_METRIC_KEYS = {
    "proof_generation_time_ms",
    "proof_size_bytes",
    "verifier_time_ms",
}
BACKEND_DECISION_KEYS = {
    "blocked_before_metrics",
    "candidate_route_ids",
    "first_missing_object",
    "go_criterion",
    "next_route",
    "primary_blocker",
    "proof_metrics",
    "source_issue",
    "usable_cryptographic_backend_route_ids",
}
BACKEND_DECISION_METRIC_KEYS = {
    "metrics_enabled",
    "proof_generation_time_ms",
    "proof_size_bytes",
    "verifier_time_ms",
}
MUTATION_CASE_KEYS = {
    "baseline_result",
    "error_code",
    "mutated_accepted",
    "mutation",
    "rejected",
    "rejection_layer",
    "surface",
}
SUMMARY_KEYS = {
    "candidate_route_ids",
    "compressed_artifact_commitment",
    "compressed_artifact_serialized_bytes",
    "first_missing_object",
    "go_criterion",
    "primary_blocker",
    "result",
    "selected_checked_rows",
    "source_issue",
    "source_result",
    "two_slice_target_commitment",
    "usable_cryptographic_backend_route_ids",
    "verifier_handle_commitment",
}
SUMMARY_WITH_CASE_KEYS = SUMMARY_KEYS | {"mutation_cases", "mutations_rejected"}


class D128CryptographicBackendGateError(ValueError):
    def __init__(self, message: str, *, layer: str = "parser_or_schema") -> None:
        super().__init__(message)
        self.layer = layer


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128CryptographicBackendGateError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


PROOF_NATIVE = _load_module(PROOF_NATIVE_SCRIPT, "zkai_d128_proof_native_for_cryptographic_backend_gate")


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


def expect_equal(actual: Any, expected: Any, field: str, *, layer: str = "parser_or_schema") -> None:
    if actual != expected:
        raise D128CryptographicBackendGateError(f"{field} mismatch", layer=layer)


def expect_keys(value: dict[str, Any], expected: set[str], field: str, *, layer: str = "parser_or_schema") -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise D128CryptographicBackendGateError(
            f"{field} keys mismatch: missing={missing} extra={extra}",
            layer=layer,
        )


def require_object(value: Any, field: str, *, layer: str = "parser_or_schema") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128CryptographicBackendGateError(f"{field} must be an object", layer=layer)
    return value


def require_list(value: Any, field: str, *, layer: str = "parser_or_schema") -> list[Any]:
    if not isinstance(value, list):
        raise D128CryptographicBackendGateError(f"{field} must be a list", layer=layer)
    return value


def require_str(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    if not isinstance(value, str) or not value:
        raise D128CryptographicBackendGateError(f"{field} must be a non-empty string", layer=layer)
    return value


def require_bool(value: Any, field: str, *, layer: str = "parser_or_schema") -> bool:
    if not isinstance(value, bool):
        raise D128CryptographicBackendGateError(f"{field} must be a boolean", layer=layer)
    return value


def require_commitment(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    value = require_str(value, field, layer=layer)
    if not value.startswith("blake2b-256:"):
        raise D128CryptographicBackendGateError(f"{field} must be blake2b-256 domain-separated", layer=layer)
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128CryptographicBackendGateError(f"{field} must be a 32-byte lowercase hex digest", layer=layer)
    return value


def require_sha256_hex(value: Any, field: str, *, layer: str = "parser_or_schema") -> str:
    value = require_str(value, field, layer=layer)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise D128CryptographicBackendGateError(f"{field} must be a 32-byte lowercase hex digest", layer=layer)
    return value


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D128CryptographicBackendGateError(f"source evidence is not a regular file: {path}", layer="source_proof_native_contract")
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128CryptographicBackendGateError(f"source evidence path escapes repository: {path}", layer="source_proof_native_contract") from err
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as err:
        raise D128CryptographicBackendGateError(f"failed to load source evidence {path}: {err}", layer="source_proof_native_contract") from err
    if not isinstance(payload, dict):
        raise D128CryptographicBackendGateError(f"source evidence must be a JSON object: {path}", layer="source_proof_native_contract")
    return payload


@functools.lru_cache(maxsize=4)
def load_checked_proof_native(path: pathlib.Path = PROOF_NATIVE_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        PROOF_NATIVE.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128CryptographicBackendGateError(f"proof-native source validation failed: {err}", layer="source_proof_native_contract") from err
    expect_equal(payload.get("schema"), EXPECTED_PROOF_NATIVE_SCHEMA, "source schema", layer="source_proof_native_contract")
    expect_equal(payload.get("decision"), EXPECTED_PROOF_NATIVE_DECISION, "source decision", layer="source_proof_native_contract")
    expect_equal(payload.get("result"), EXPECTED_PROOF_NATIVE_RESULT, "source result", layer="source_proof_native_contract")
    expect_equal(payload.get("compression_result"), EXPECTED_COMPRESSION_RESULT, "source compression result", layer="source_proof_native_contract")
    expect_equal(payload.get("recursive_or_pcd_result"), EXPECTED_RECURSIVE_OR_PCD_RESULT, "source recursive result", layer="source_proof_native_contract")
    expect_equal(payload.get("claim_boundary"), EXPECTED_PROOF_NATIVE_CLAIM_BOUNDARY, "source claim boundary", layer="source_proof_native_contract")
    if payload.get("all_mutations_rejected") is not True:
        raise D128CryptographicBackendGateError("source proof-native gate did not reject all mutations", layer="source_proof_native_contract")
    return payload


def source_proof_native_contract(source: dict[str, Any], path: pathlib.Path = PROOF_NATIVE_EVIDENCE) -> dict[str, Any]:
    summary = require_object(source.get("summary"), "source summary", layer="source_proof_native_contract")
    artifact = require_object(source.get("compressed_artifact"), "source compressed artifact", layer="source_proof_native_contract")
    handle = require_object(source.get("verifier_handle"), "source verifier handle", layer="source_proof_native_contract")
    preimage = require_object(artifact.get("preimage"), "source compressed artifact preimage", layer="source_proof_native_contract")
    public_inputs = copy.deepcopy(require_object(preimage.get("proof_native_public_input_contract"), "source public input contract", layer="source_public_input_contract"))
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(source),
        "schema": source["schema"],
        "decision": source["decision"],
        "result": source["result"],
        "issue": SOURCE_ISSUE,
        "compression_result": source["compression_result"],
        "recursive_or_pcd_result": source["recursive_or_pcd_result"],
        "claim_boundary": source["claim_boundary"],
        "two_slice_target_commitment": summary["two_slice_target_commitment"],
        "selected_slice_ids": copy.deepcopy(summary["selected_slice_ids"]),
        "selected_checked_rows": summary["selected_checked_rows"],
        "compressed_artifact_commitment": artifact["compressed_artifact_commitment"],
        "verifier_handle_commitment": handle["verifier_handle_commitment"],
        "public_input_contract": public_inputs,
        "compression_metrics": copy.deepcopy(summary["compression_metrics"]),
    }


def cargo_dependency_names(cargo_toml: dict[str, Any]) -> set[str]:
    names: set[str] = set()

    def collect_table(deps: Any) -> None:
        if not isinstance(deps, dict):
            return
        for name, spec in deps.items():
            if isinstance(name, str):
                names.add(name)
            if isinstance(spec, dict):
                package = spec.get("package")
                if isinstance(package, str):
                    names.add(package)

    def walk(section: Any) -> None:
        if not isinstance(section, dict):
            return
        for key, value in section.items():
            if key in DEPENDENCY_TABLE_KEYS:
                collect_table(value)
            elif isinstance(value, dict):
                walk(value)

    walk(cargo_toml)
    return names


def cargo_lock_package_version(cargo_lock: dict[str, Any], name: str) -> str | None:
    packages = cargo_lock.get("package")
    if not isinstance(packages, list):
        return None
    for package in packages:
        if isinstance(package, dict) and package.get("name") == name:
            version = package.get("version")
            return version if isinstance(version, str) else None
    return None


def _artifact_status(artifact_id: str, raw_path: str) -> dict[str, Any]:
    path = ROOT / raw_path
    return {
        "artifact_id": artifact_id,
        "path": raw_path,
        "exists": path.exists(),
    }


def _glob_candidate_artifacts() -> list[str]:
    candidates: set[str] = set()
    for pattern in CANDIDATE_ARTIFACT_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                candidates.add(relative_path(path))
    return sorted(candidates)


def backend_probe() -> dict[str, Any]:
    cargo_toml = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    cargo_lock = tomllib.loads((ROOT / "Cargo.lock").read_text(encoding="utf-8"))
    dependency_names = cargo_dependency_names(cargo_toml)
    zkvm_dependencies = sorted(EXTERNAL_ZKVM_DEPENDENCIES & dependency_names)
    snark_ivc_dependencies = sorted(EXTERNAL_SNARK_IVC_DEPENDENCIES & dependency_names)
    return {
        "cargo_toml_sha256": file_sha256(ROOT / "Cargo.toml"),
        "cargo_lock_sha256": file_sha256(ROOT / "Cargo.lock"),
        "local_stwo_version": cargo_lock_package_version(cargo_lock, "stwo"),
        "external_zkvm_dependency_names": zkvm_dependencies,
        "external_zkvm_dependencies_declared": bool(zkvm_dependencies),
        "external_snark_ivc_dependency_names": snark_ivc_dependencies,
        "external_snark_ivc_dependencies_declared": bool(snark_ivc_dependencies),
        "fixed_backend_artifacts": [_artifact_status(artifact_id, raw_path) for artifact_id, raw_path in FIXED_BACKEND_ARTIFACTS],
        "artifact_candidates": _glob_candidate_artifacts(),
    }


def _artifact_exists(probe: dict[str, Any], artifact_id: str) -> bool:
    for artifact in probe["fixed_backend_artifacts"]:
        if artifact["artifact_id"] == artifact_id:
            return bool(artifact["exists"])
    raise D128CryptographicBackendGateError(f"unknown artifact id {artifact_id}", layer="backend_probe")


def backend_routes(probe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "route_id": "source_proof_native_two_slice_contract",
            "route_kind": "source_contract_available",
            "status": "GO_INPUT_CONTRACT_ONLY_NOT_CRYPTOGRAPHIC_BACKEND",
            "cryptographic_backend": False,
            "usable_today": True,
            "claim_boundary": EXPECTED_PROOF_NATIVE_CLAIM_BOUNDARY,
            "blocking_missing_object": "none_for_source_contract",
            "next_action": "use as the exact public-input contract a real backend must prove or receipt",
            "proof_metrics": {
                "proof_size_bytes": None,
                "verifier_time_ms": None,
                "proof_generation_time_ms": None,
            },
            "evidence": {
                "source": relative_path(PROOF_NATIVE_EVIDENCE),
                "tracked_issue": SOURCE_ISSUE,
            },
        },
        {
            "route_id": "local_stwo_nested_verifier_backend",
            "route_kind": "local_stwo_native_recursion",
            "status": "NO_GO_MISSING_NESTED_VERIFIER_AIR_OR_CIRCUIT",
            "cryptographic_backend": True,
            "usable_today": False,
            "claim_boundary": "missing_executable_backend",
            "blocking_missing_object": "src/stwo_backend/d128_two_slice_recursive_pcd_backend.rs",
            "next_action": "design or import a verifier-in-AIR/circuit that proves the selected d128 slice verifier checks",
            "proof_metrics": {
                "proof_size_bytes": None,
                "verifier_time_ms": None,
                "proof_generation_time_ms": None,
            },
            "evidence": {
                "backend_module_exists": _artifact_exists(probe, "local_stwo_nested_verifier_module"),
            },
        },
        {
            "route_id": "local_pcd_or_ivc_outer_proof_backend",
            "route_kind": "local_pcd_or_ivc_backend",
            "status": "NO_GO_MISSING_OUTER_PROOF_GENERATOR_AND_VERIFIER_HANDLE",
            "cryptographic_backend": True,
            "usable_today": False,
            "claim_boundary": "missing_executable_backend",
            "blocking_missing_object": "recursive_or_pcd_outer_proof_generator_and_verifier_handle",
            "next_action": "add an executable PCD/IVC backend and bind the #424 public-input contract",
            "proof_metrics": {
                "proof_size_bytes": None,
                "verifier_time_ms": None,
                "proof_generation_time_ms": None,
            },
            "evidence": {
                "proof_artifact_exists": _artifact_exists(probe, "local_recursive_pcd_proof_artifact"),
                "verifier_handle_exists": _artifact_exists(probe, "local_recursive_pcd_verifier_handle"),
            },
        },
        {
            "route_id": "external_zkvm_statement_receipt_backend",
            "route_kind": "external_zkvm_statement_receipt",
            "status": "NO_GO_ZKVM_RECEIPT_ADAPTER_NOT_IMPLEMENTED_FOR_D128_CONTRACT",
            "cryptographic_backend": True,
            "usable_today": False,
            "claim_boundary": "external_adapter_candidate_not_checked_backend",
            "blocking_missing_object": "checked_external_zkvm_receipt_for_d128_two_slice_contract",
            "next_action": "work issue #422 with the #424 public inputs as receipt journal fields",
            "proof_metrics": {
                "proof_size_bytes": None,
                "verifier_time_ms": None,
                "proof_generation_time_ms": None,
            },
            "evidence": {
                "local_dependencies_declared": probe["external_zkvm_dependencies_declared"],
                "dependency_names": copy.deepcopy(probe["external_zkvm_dependency_names"]),
                "receipt_artifact_exists": _artifact_exists(probe, "external_zkvm_statement_receipt_artifact"),
                "tracked_issue": 422,
            },
        },
        {
            "route_id": "external_snark_or_ivc_statement_receipt_backend",
            "route_kind": "external_snark_or_ivc_statement_receipt",
            "status": "NO_GO_SNARK_OR_IVC_RECEIPT_ADAPTER_NOT_IMPLEMENTED_FOR_D128_CONTRACT",
            "cryptographic_backend": True,
            "usable_today": False,
            "claim_boundary": "external_adapter_candidate_not_checked_backend",
            "blocking_missing_object": "checked_external_snark_or_ivc_receipt_for_d128_two_slice_contract",
            "next_action": "build a SNARK/IVC statement-receipt adapter only if it can bind the same #424 public-input contract",
            "proof_metrics": {
                "proof_size_bytes": None,
                "verifier_time_ms": None,
                "proof_generation_time_ms": None,
            },
            "evidence": {
                "local_dependencies_declared": probe["external_snark_ivc_dependencies_declared"],
                "dependency_names": copy.deepcopy(probe["external_snark_ivc_dependency_names"]),
                "receipt_artifact_exists": _artifact_exists(probe, "external_snark_ivc_statement_receipt_artifact"),
            },
        },
        {
            "route_id": "starknet_settlement_adapter",
            "route_kind": "settlement_adapter",
            "status": "DEFERRED_UNTIL_A_PROOF_OBJECT_EXISTS",
            "cryptographic_backend": False,
            "usable_today": False,
            "claim_boundary": "deployment_adapter_after_backend_proof_object",
            "blocking_missing_object": "proof_object_suitable_for_settlement_facts",
            "next_action": "keep parked until a local or external proof object exists for the same public-input contract",
            "proof_metrics": {
                "proof_size_bytes": None,
                "verifier_time_ms": None,
                "proof_generation_time_ms": None,
            },
            "evidence": {
                "snip36_parked": True,
            },
        },
    ]


def backend_decision(routes: list[dict[str, Any]]) -> dict[str, Any]:
    usable_crypto = [
        route["route_id"]
        for route in routes
        if route["cryptographic_backend"] is True and route["usable_today"] is True
    ]
    candidate_routes = [
        route["route_id"]
        for route in routes
        if route["cryptographic_backend"] is True and route["usable_today"] is False
    ]
    return {
        "primary_blocker": PRIMARY_BLOCKER,
        "first_missing_object": FIRST_MISSING_OBJECT,
        "go_criterion": GO_CRITERION,
        "source_issue": SOURCE_ISSUE,
        "next_route": NEXT_ROUTE,
        "usable_cryptographic_backend_route_ids": usable_crypto,
        "candidate_route_ids": candidate_routes,
        "blocked_before_metrics": True,
        "proof_metrics": {
            "metrics_enabled": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "proof_generation_time_ms": None,
        },
    }


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def build_core_payload() -> dict[str, Any]:
    source = load_checked_proof_native()
    source_contract = source_proof_native_contract(source)
    probe = backend_probe()
    routes = backend_routes(probe)
    decision = backend_decision(routes)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_proof_native_contract": source_contract,
        "backend_probe": probe,
        "backend_routes": routes,
        "backend_decision": decision,
        "summary": {
            "result": RESULT,
            "source_issue": SOURCE_ISSUE,
            "source_result": source_contract["result"],
            "selected_checked_rows": source_contract["selected_checked_rows"],
            "two_slice_target_commitment": source_contract["two_slice_target_commitment"],
            "compressed_artifact_commitment": source_contract["compressed_artifact_commitment"],
            "verifier_handle_commitment": source_contract["verifier_handle_commitment"],
            "compressed_artifact_serialized_bytes": source_contract["compression_metrics"]["compressed_artifact_serialized_bytes"],
            "primary_blocker": PRIMARY_BLOCKER,
            "first_missing_object": FIRST_MISSING_OBJECT,
            "go_criterion": GO_CRITERION,
            "usable_cryptographic_backend_route_ids": decision["usable_cryptographic_backend_route_ids"],
            "candidate_route_ids": decision["candidate_route_ids"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    return payload


def _validate_artifact_statuses(statuses: Any) -> list[dict[str, Any]]:
    statuses = require_list(statuses, "fixed backend artifacts", layer="backend_probe")
    expected_ids = [artifact_id for artifact_id, _path in FIXED_BACKEND_ARTIFACTS]
    if [require_object(status, f"fixed backend artifact {index}", layer="backend_probe").get("artifact_id") for index, status in enumerate(statuses)] != expected_ids:
        raise D128CryptographicBackendGateError("fixed backend artifact ids mismatch", layer="backend_probe")
    for index, status in enumerate(statuses):
        status = require_object(status, f"fixed backend artifact {index}", layer="backend_probe")
        expect_keys(status, ARTIFACT_STATUS_KEYS, f"fixed backend artifact {index}", layer="backend_probe")
        require_str(status["artifact_id"], f"fixed backend artifact {index} id", layer="backend_probe")
        path = require_str(status["path"], f"fixed backend artifact {index} path", layer="backend_probe")
        require_bool(status["exists"], f"fixed backend artifact {index} exists", layer="backend_probe")
        expect_equal(status["exists"], (ROOT / path).exists(), f"fixed backend artifact {index} existence", layer="backend_probe")
    return statuses


def validate_source_contract(contract: Any) -> dict[str, Any]:
    contract = require_object(contract, "source proof-native contract", layer="source_proof_native_contract")
    expect_keys(contract, SOURCE_CONTRACT_KEYS, "source proof-native contract", layer="source_proof_native_contract")
    public_inputs = require_object(contract.get("public_input_contract"), "source public input contract", layer="source_public_input_contract")
    expect_keys(public_inputs, PUBLIC_INPUT_CONTRACT_KEYS, "source public input contract", layer="source_public_input_contract")
    for key in (
        "two_slice_target_commitment",
        "source_accumulator_commitment",
        "source_verifier_handle_commitment",
    ):
        require_commitment(public_inputs.get(key), key, layer="source_public_input_contract")
    for key in (
        "selected_slice_statement_commitments",
        "selected_source_evidence_hashes",
        "selected_slice_public_instance_commitments",
        "selected_slice_proof_native_parameter_commitments",
    ):
        require_list(public_inputs.get(key), key, layer="source_public_input_contract")
    source = load_checked_proof_native()
    expected = source_proof_native_contract(source)
    expect_equal(contract, expected, "source proof-native contract", layer="source_proof_native_contract")
    expect_equal(contract["issue"], SOURCE_ISSUE, "source issue", layer="source_proof_native_contract")
    expect_equal(contract["selected_slice_ids"], list(EXPECTED_SELECTED_SLICE_IDS), "selected slice ids", layer="source_proof_native_contract")
    expect_equal(contract["selected_checked_rows"], EXPECTED_SELECTED_ROWS, "selected rows", layer="source_proof_native_contract")
    require_sha256_hex(contract["file_sha256"], "source file sha256", layer="source_proof_native_contract")
    require_sha256_hex(contract["payload_sha256"], "source payload sha256", layer="source_proof_native_contract")
    require_commitment(contract["two_slice_target_commitment"], "source target commitment", layer="source_proof_native_contract")
    require_commitment(contract["compressed_artifact_commitment"], "compressed artifact commitment", layer="source_proof_native_contract")
    require_commitment(contract["verifier_handle_commitment"], "verifier handle commitment", layer="source_proof_native_contract")
    return contract


def validate_backend_probe(value: Any) -> dict[str, Any]:
    probe = require_object(value, "backend probe", layer="backend_probe")
    expect_keys(probe, BACKEND_PROBE_KEYS, "backend probe", layer="backend_probe")
    require_sha256_hex(probe["cargo_toml_sha256"], "Cargo.toml sha256", layer="backend_probe")
    require_sha256_hex(probe["cargo_lock_sha256"], "Cargo.lock sha256", layer="backend_probe")
    require_list(probe["external_zkvm_dependency_names"], "external zkVM dependency names", layer="backend_probe")
    require_bool(probe["external_zkvm_dependencies_declared"], "external zkVM dependencies declared", layer="backend_probe")
    require_list(probe["external_snark_ivc_dependency_names"], "external SNARK/IVC dependency names", layer="backend_probe")
    require_bool(probe["external_snark_ivc_dependencies_declared"], "external SNARK/IVC dependencies declared", layer="backend_probe")
    _validate_artifact_statuses(probe["fixed_backend_artifacts"])
    candidates = require_list(probe["artifact_candidates"], "artifact candidates", layer="backend_probe")
    for candidate in candidates:
        require_str(candidate, "artifact candidate", layer="backend_probe")
    expected = backend_probe()
    expect_equal(probe, expected, "backend probe", layer="backend_probe")
    return probe


def validate_route(route: Any, index: int) -> dict[str, Any]:
    route = require_object(route, f"backend route {index}", layer="backend_routes")
    expect_keys(route, ROUTE_KEYS, f"backend route {index}", layer="backend_routes")
    expect_equal(route.get("route_id"), ROUTE_IDS[index], f"route {index} id", layer="backend_routes")
    require_str(route["route_kind"], f"route {index} kind", layer="backend_routes")
    require_str(route["status"], f"route {index} status", layer="backend_routes")
    require_bool(route["cryptographic_backend"], f"route {index} cryptographic backend", layer="backend_routes")
    require_bool(route["usable_today"], f"route {index} usable_today", layer="backend_routes")
    require_str(route["claim_boundary"], f"route {index} claim boundary", layer="backend_routes")
    require_str(route["blocking_missing_object"], f"route {index} blocker", layer="backend_routes")
    require_str(route["next_action"], f"route {index} next action", layer="backend_routes")
    require_object(route["evidence"], f"route {index} evidence", layer="backend_routes")
    metrics = require_object(route["proof_metrics"], f"route {index} proof metrics", layer="backend_routes")
    expect_keys(metrics, ROUTE_METRIC_KEYS, f"route {index} proof metrics", layer="backend_routes")
    if any(value is not None for value in metrics.values()):
        raise D128CryptographicBackendGateError(f"route {index} smuggles proof metrics before backend exists", layer="backend_routes")
    if route["cryptographic_backend"] is True and route["usable_today"] is True:
        raise D128CryptographicBackendGateError("cryptographic route cannot be usable without a checked backend artifact", layer="backend_routes")
    return route


def validate_backend_routes(value: Any, probe: dict[str, Any]) -> list[dict[str, Any]]:
    routes = require_list(value, "backend routes", layer="backend_routes")
    if len(routes) != len(ROUTE_IDS):
        raise D128CryptographicBackendGateError("backend route count mismatch", layer="backend_routes")
    route_objects = [validate_route(route, index) for index, route in enumerate(routes)]
    expected = backend_routes(probe)
    expect_equal(route_objects, expected, "backend routes", layer="backend_routes")
    return route_objects


def validate_backend_decision(value: Any, routes: list[dict[str, Any]]) -> dict[str, Any]:
    decision = require_object(value, "backend decision", layer="backend_decision")
    expect_keys(decision, BACKEND_DECISION_KEYS, "backend decision", layer="backend_decision")
    metrics = require_object(decision["proof_metrics"], "backend decision proof metrics", layer="backend_decision")
    expect_keys(metrics, BACKEND_DECISION_METRIC_KEYS, "backend decision proof metrics", layer="backend_decision")
    expect_equal(decision["primary_blocker"], PRIMARY_BLOCKER, "primary blocker", layer="backend_decision")
    expect_equal(decision["first_missing_object"], FIRST_MISSING_OBJECT, "first missing object", layer="backend_decision")
    expect_equal(decision["go_criterion"], GO_CRITERION, "go criterion", layer="backend_decision")
    expect_equal(decision["source_issue"], SOURCE_ISSUE, "source issue", layer="backend_decision")
    expect_equal(decision["next_route"], NEXT_ROUTE, "next route", layer="backend_decision")
    expect_equal(decision["blocked_before_metrics"], True, "blocked before metrics", layer="backend_decision")
    expect_equal(metrics["metrics_enabled"], False, "metrics enabled", layer="backend_decision")
    if any(metrics[key] is not None for key in ("proof_size_bytes", "verifier_time_ms", "proof_generation_time_ms")):
        raise D128CryptographicBackendGateError("backend decision smuggles proof metrics before backend exists", layer="backend_decision")
    expected = backend_decision(routes)
    expect_equal(decision, expected, "backend decision", layer="backend_decision")
    return decision


def expected_summary(core_payload: dict[str, Any]) -> dict[str, Any]:
    source = core_payload["source_proof_native_contract"]
    decision = core_payload["backend_decision"]
    return {
        "result": RESULT,
        "source_issue": SOURCE_ISSUE,
        "source_result": source["result"],
        "selected_checked_rows": source["selected_checked_rows"],
        "two_slice_target_commitment": source["two_slice_target_commitment"],
        "compressed_artifact_commitment": source["compressed_artifact_commitment"],
        "verifier_handle_commitment": source["verifier_handle_commitment"],
        "compressed_artifact_serialized_bytes": source["compression_metrics"]["compressed_artifact_serialized_bytes"],
        "primary_blocker": PRIMARY_BLOCKER,
        "first_missing_object": FIRST_MISSING_OBJECT,
        "go_criterion": GO_CRITERION,
        "usable_cryptographic_backend_route_ids": decision["usable_cryptographic_backend_route_ids"],
        "candidate_route_ids": decision["candidate_route_ids"],
    }


def validate_core_payload(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "cryptographic backend payload")
    expect_keys(payload, DRAFT_TOP_LEVEL_KEYS, "cryptographic backend payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("issue"), ISSUE, "issue")
    expect_equal(payload.get("claim_boundary"), CLAIM_BOUNDARY, "claim boundary")
    validate_source_contract(payload.get("source_proof_native_contract"))
    probe = validate_backend_probe(payload.get("backend_probe"))
    routes = validate_backend_routes(payload.get("backend_routes"), probe)
    validate_backend_decision(payload.get("backend_decision"), routes)
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    summary = require_object(payload.get("summary"), "summary")
    expect_keys(summary, SUMMARY_KEYS, "summary")
    expect_equal(summary, expected_summary(payload), "summary")
    expected = build_core_payload()
    expect_equal(payload, expected, "cryptographic backend payload")
    return payload


def _core_payload_for_case_replay(payload: dict[str, Any]) -> dict[str, Any]:
    draft = copy.deepcopy(payload)
    for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected"):
        draft.pop(field, None)
    summary = require_object(draft.get("summary"), "summary")
    summary.pop("mutation_cases", None)
    summary.pop("mutations_rejected", None)
    return draft


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    inventory = require_list(payload.get("mutation_inventory"), "mutation inventory")
    expect_equal(inventory, expected_mutation_inventory(), "mutation inventory")
    cases = require_list(payload.get("cases"), "mutation cases")
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    rejected = 0
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        expect_keys(case, MUTATION_CASE_KEYS, f"mutation case {index}")
        pair = (require_str(case["mutation"], f"mutation case {index} mutation"), require_str(case["surface"], f"mutation case {index} surface"))
        if pair in seen:
            raise D128CryptographicBackendGateError(f"duplicate mutation case {index}")
        seen.add(pair)
        pairs.append(pair)
        expect_equal(case["baseline_result"], RESULT, f"mutation case {index} baseline result")
        accepted = require_bool(case["mutated_accepted"], f"mutation case {index} mutated_accepted")
        rejected_flag = require_bool(case["rejected"], f"mutation case {index} rejected")
        if accepted == rejected_flag:
            raise D128CryptographicBackendGateError(f"mutation case {index} rejected/accepted mismatch")
        rejection_layer = require_str(case["rejection_layer"], f"mutation case {index} rejection layer")
        error_code = require_str(case["error_code"], f"mutation case {index} error code")
        if accepted:
            expect_equal(rejection_layer, "accepted", f"mutation case {index} rejection layer")
            expect_equal(error_code, "accepted", f"mutation case {index} error_code")
        else:
            if error_code == "accepted":
                raise D128CryptographicBackendGateError(f"mutation case {index} error_code must identify the rejection")
            rejected += 1
    expect_equal(tuple(pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), len(cases), "case count")
    expect_equal(payload.get("all_mutations_rejected"), all(case["rejected"] for case in cases), "all mutations rejected")
    expected_by_pair = {
        (case["mutation"], case["surface"]): case
        for case in mutation_cases(_core_payload_for_case_replay(payload))
    }
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        expected = expected_by_pair.get((case["mutation"], case["surface"]))
        if expected is None:
            raise D128CryptographicBackendGateError(f"missing recomputed mutation case {index}")
        expect_equal(case, expected, f"mutation case {index}")
    return len(cases), rejected


def validate_payload(payload: Any) -> dict[str, Any]:
    payload = require_object(payload, "cryptographic backend payload")
    has_mutation_metadata = [field in payload for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected")]
    if any(has_mutation_metadata) and not all(has_mutation_metadata):
        raise D128CryptographicBackendGateError("mutation metadata must be all-or-nothing")
    expect_keys(payload, TOP_LEVEL_KEYS, "cryptographic backend payload")
    draft = _core_payload_for_case_replay(payload)
    validate_core_payload(draft)
    case_count, rejected = _validate_case_metadata(payload)
    if rejected != case_count:
        raise D128CryptographicBackendGateError("not all cryptographic-backend mutations rejected")
    expected = expected_summary(draft)
    expected["mutation_cases"] = case_count
    expected["mutations_rejected"] = rejected
    summary = require_object(payload.get("summary"), "summary")
    expect_keys(summary, SUMMARY_WITH_CASE_KEYS, "summary")
    expect_equal(summary, expected, "summary")
    return payload


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None]) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        cases.append((name, surface, mutated))

    add("source_file_hash_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("file_sha256", "00" * 32))
    add("source_payload_hash_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("payload_sha256", "11" * 32))
    add("source_result_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("result", "BOUNDED_NO_GO"))
    add("source_compression_result_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("compression_result", "NO_GO"))
    add("source_recursive_result_relabel_to_go", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("recursive_or_pcd_result", "GO_RECURSIVE_OUTER_PROOF"))
    add("source_claim_boundary_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("source_target_commitment_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "22" * 32))
    add("source_selected_statement_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"]["selected_slice_statement_commitments"][0].__setitem__("statement_commitment", "blake2b-256:" + "33" * 32))
    add("source_selected_source_hash_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"]["selected_source_evidence_hashes"][0].__setitem__("source_payload_sha256", "44" * 32))
    add("source_selected_public_instance_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"]["selected_slice_public_instance_commitments"][0].__setitem__("public_instance_commitment", "blake2b-256:" + "55" * 32))
    add("source_selected_parameter_commitment_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"]["selected_slice_proof_native_parameter_commitments"][0].__setitem__("proof_native_parameter_commitment", "blake2b-256:" + "66" * 32))
    add("source_verifier_domain_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"].__setitem__("verifier_domain", "ptvm:tampered:v0"))
    add("source_required_backend_version_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"].__setitem__("required_backend_version", "wrong-backend"))
    add("source_accumulator_commitment_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"].__setitem__("source_accumulator_commitment", "blake2b-256:" + "77" * 32))
    add("source_verifier_handle_commitment_drift", "source_public_input_contract", lambda p: p["source_proof_native_contract"]["public_input_contract"].__setitem__("source_verifier_handle_commitment", "blake2b-256:" + "88" * 32))
    add("compressed_artifact_commitment_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("compressed_artifact_commitment", "blake2b-256:" + "99" * 32))
    add("verifier_handle_commitment_drift", "source_proof_native_contract", lambda p: p["source_proof_native_contract"].__setitem__("verifier_handle_commitment", "blake2b-256:" + "aa" * 32))
    add("repo_probe_cargo_hash_drift", "backend_probe", lambda p: p["backend_probe"].__setitem__("cargo_toml_sha256", "bb" * 32))
    add("repo_probe_dependency_hint_drift", "backend_probe", lambda p: p["backend_probe"].__setitem__("external_zkvm_dependencies_declared", not p["backend_probe"]["external_zkvm_dependencies_declared"]))
    add("repo_probe_artifact_presence_relabeling", "backend_probe", lambda p: p["backend_probe"]["fixed_backend_artifacts"][0].__setitem__("exists", not p["backend_probe"]["fixed_backend_artifacts"][0]["exists"]))
    add("route_local_nested_verifier_relabel_to_go", "backend_routes", lambda p: (p["backend_routes"][1].__setitem__("status", "GO_EXECUTABLE_BACKEND"), p["backend_routes"][1].__setitem__("usable_today", True)))
    add("route_local_pcd_relabel_to_go", "backend_routes", lambda p: (p["backend_routes"][2].__setitem__("status", "GO_EXECUTABLE_BACKEND"), p["backend_routes"][2].__setitem__("usable_today", True)))
    add("route_external_zkvm_relabel_to_go", "backend_routes", lambda p: (p["backend_routes"][3].__setitem__("status", "GO_EXECUTABLE_BACKEND"), p["backend_routes"][3].__setitem__("usable_today", True)))
    add("route_external_snark_relabel_to_go", "backend_routes", lambda p: (p["backend_routes"][4].__setitem__("status", "GO_EXECUTABLE_BACKEND"), p["backend_routes"][4].__setitem__("usable_today", True)))
    add("route_blocker_removed", "backend_routes", lambda p: p["backend_routes"][1].__setitem__("blocking_missing_object", ""))
    add("route_metric_smuggled", "backend_routes", lambda p: p["backend_routes"][2]["proof_metrics"].__setitem__("verifier_time_ms", 1.0))
    add("backend_decision_changed_to_go", "backend_decision", lambda p: p.__setitem__("result", "GO"))
    add("primary_blocker_removed", "backend_decision", lambda p: p["backend_decision"].__setitem__("primary_blocker", ""))
    add("proof_size_metric_smuggled", "backend_decision", lambda p: p["backend_decision"]["proof_metrics"].__setitem__("proof_size_bytes", 1024))
    add("verifier_time_metric_smuggled", "backend_decision", lambda p: p["backend_decision"]["proof_metrics"].__setitem__("verifier_time_ms", 1.0))
    add("proof_generation_time_metric_smuggled", "backend_decision", lambda p: p["backend_decision"]["proof_metrics"].__setitem__("proof_generation_time_ms", 1.0))
    add("next_route_changed_to_settlement", "backend_decision", lambda p: p["backend_decision"].__setitem__("next_route", "STARKNET_SETTLEMENT_NOW"))
    add("non_claims_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1]))
    add("validation_command_drift", "parser_or_schema", lambda p: p["validation_commands"].append("echo unsafe"))
    add("unknown_top_level_field_added", "parser_or_schema", lambda p: p.__setitem__("unexpected", True))
    return cases


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_core_payload())
    validate_core_payload(baseline)
    cases: list[dict[str, Any]] = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            validate_core_payload(mutated)
            accepted = True
            layer = "accepted"
            error_code = "accepted"
        except D128CryptographicBackendGateError:
            accepted = False
            layer = surface
            error_code = mutation
        cases.append(
            {
                "mutation": mutation,
                "surface": surface,
                "baseline_result": RESULT,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer,
                "error_code": error_code,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    payload = build_core_payload()
    cases = mutation_cases(payload)
    payload["mutation_inventory"] = expected_mutation_inventory()
    payload["cases"] = cases
    payload["case_count"] = len(cases)
    payload["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    payload["summary"]["mutation_cases"] = len(cases)
    payload["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(payload)
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for route in payload["backend_routes"]:
        writer.writerow({column: route[column] for column in TSV_COLUMNS})
    return output.getvalue()


def _safe_output_path(path: pathlib.Path, expected_suffix: str) -> pathlib.Path:
    if path.is_absolute():
        raise D128CryptographicBackendGateError(f"output path must be repo-relative: {path}")
    if path.suffix != expected_suffix:
        raise D128CryptographicBackendGateError(f"output path must end in {expected_suffix}: {path}")
    pure = pathlib.PurePosixPath(path.as_posix())
    if path.as_posix() != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise D128CryptographicBackendGateError(f"output path must be repo-relative without traversal: {path}")
    candidate = ROOT.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise D128CryptographicBackendGateError(f"output path must stay under docs/engineering/evidence: {path}") from err
    return candidate


def _resolved_output_target(path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    evidence_root = EVIDENCE_DIR.resolve(strict=True)
    resolved_parent = path.parent.resolve(strict=True)
    try:
        resolved_parent.relative_to(evidence_root)
    except ValueError as err:
        raise D128CryptographicBackendGateError(f"output parent escaped docs/engineering/evidence: {path}") from err
    final_path = resolved_parent / path.name
    resolved_final = final_path.resolve(strict=False)
    try:
        resolved_final.relative_to(evidence_root)
    except ValueError as err:
        raise D128CryptographicBackendGateError(f"output path must stay under docs/engineering/evidence: {path}") from err
    return final_path, resolved_final


def _write_bytes_via_dirfd(final_path: pathlib.Path, data: bytes) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    dir_fd = os.open(final_path.parent, flags)
    tmp_name = f".{final_path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    tmp_fd: int | None = None
    tmp_created = False
    try:
        if not stat.S_ISDIR(os.fstat(dir_fd).st_mode):
            raise D128CryptographicBackendGateError(f"output parent is not a directory: {final_path.parent}")
        tmp_fd = os.open(tmp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
        tmp_created = True
        with os.fdopen(tmp_fd, "wb", closefd=True) as handle:
            tmp_fd = None
            handle.write(data)
        os.replace(tmp_name, final_path.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        tmp_created = False
    finally:
        if tmp_fd is not None:
            os.close(tmp_fd)
        if tmp_created:
            try:
                os.unlink(tmp_name, dir_fd=dir_fd)
            except FileNotFoundError:
                pass
        os.close(dir_fd)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    outputs: list[tuple[pathlib.Path, bytes]] = []
    if json_path is not None:
        outputs.append((_safe_output_path(json_path, ".json"), json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"))
    if tsv_path is not None:
        outputs.append((_safe_output_path(tsv_path, ".tsv"), to_tsv(payload).encode("utf-8")))
    resolved_targets = [(path, data, *_resolved_output_target(path)) for path, data in outputs]
    resolved_outputs = [resolved_final for _path, _data, _final_path, resolved_final in resolved_targets]
    if len(resolved_outputs) != len(set(resolved_outputs)):
        raise D128CryptographicBackendGateError("write-json and write-tsv output paths must be distinct")
    for _path, data, final_path, _resolved_final in resolved_targets:
        _write_bytes_via_dirfd(final_path, data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build d128 cryptographic-backend availability evidence. "
            "GO requires an executable proof/receipt backend; absent that, the result is a bounded no-go."
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
