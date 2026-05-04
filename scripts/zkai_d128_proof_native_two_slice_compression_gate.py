#!/usr/bin/env python3
"""Build a proof-native d128 two-slice transcript-compression artifact.

This gate answers issue #424.  It consumes the checked d128 two-slice
non-recursive accumulator and asks a narrower question than recursion: can the
same two-slice public-input/transcript contract be compressed into one
proof-native verifier-facing object without claiming recursive aggregation, PCD,
or STARK-in-STARK verification?
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
import secrets
import stat
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
ACCUMULATOR_SCRIPT = ROOT / "scripts" / "zkai_d128_two_slice_accumulator_backend_gate.py"
ACCUMULATOR_EVIDENCE = EVIDENCE_DIR / "zkai-d128-two-slice-accumulator-backend-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-proof-native-two-slice-compression-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-proof-native-two-slice-compression-2026-05.tsv"

SCHEMA = "zkai-d128-proof-native-two-slice-compression-gate-v1"
DECISION = "GO_D128_PROOF_NATIVE_TWO_SLICE_TRANSCRIPT_COMPRESSION"
RESULT = "GO"
ISSUE = 424
COMPRESSION_RESULT = "GO_PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION"
RECURSIVE_OR_PCD_RESULT = "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING"
COMPRESSED_ARTIFACT_SCHEMA = "zkai-d128-proof-native-two-slice-compressed-artifact-v1"
VERIFIER_HANDLE_SCHEMA = "zkai-d128-proof-native-two-slice-compression-verifier-handle-v1"
ARTIFACT_KIND = "proof-native-two-slice-transcript-compression"
CLAIM_BOUNDARY = "PROOF_NATIVE_TRANSCRIPT_COMPRESSION_NOT_RECURSION"
WIDTH = 128
EXPECTED_SELECTED_ROWS = 256
EXPECTED_SELECTED_SLICE_IDS = ("rmsnorm_public_rows", "rmsnorm_projection_bridge")

COMPRESSED_ARTIFACT_DOMAIN = "ptvm:zkai:d128-two-slice:proof-native-compressed-artifact:v1"
VERIFIER_HANDLE_DOMAIN = "ptvm:zkai:d128-two-slice:proof-native-compression-verifier-handle:v1"

GO_CRITERION = (
    "one proof-native compressed transcript/public-input artifact exists for the d128 two-slice contract, "
    "a local verifier handle accepts it by recomputing the same bound public inputs, and the serialized "
    "artifact is smaller than the source non-recursive accumulator artifact"
)

RECURSIVE_BLOCKER = (
    "no executable recursive/PCD outer proof backend currently proves the two selected d128 slice-verifier "
    "checks inside one cryptographic outer proof"
)

NON_CLAIMS = [
    "not recursive aggregation of selected slice proofs",
    "not proof-carrying data",
    "not STARK-in-STARK verification",
    "not one cryptographic outer proof over the two selected verifiers",
    "not proof-size evidence for a recursive outer proof",
    "not verifier-time evidence for a recursive outer proof",
    "not proof-generation-time evidence for a recursive outer proof",
    "not aggregation of all six d128 slice proofs",
    "not matched public zkML benchmark evidence",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_proof_native_two_slice_compression_gate.py --write-json docs/engineering/evidence/zkai-d128-proof-native-two-slice-compression-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-proof-native-two-slice-compression-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_proof_native_two_slice_compression_gate",
    "python3 -m py_compile scripts/zkai_d128_proof_native_two_slice_compression_gate.py scripts/tests/test_zkai_d128_proof_native_two_slice_compression_gate.py",
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
    "error_code",
    "error",
)
MUTATION_CASE_KEYS = set(TSV_COLUMNS)

EXPECTED_MUTATION_INVENTORY = (
    ("source_accumulator_file_hash_drift", "source_accumulator"),
    ("source_accumulator_payload_hash_drift", "source_accumulator"),
    ("source_accumulator_result_drift", "source_accumulator"),
    ("source_accumulator_claim_boundary_drift", "source_accumulator"),
    ("source_accumulator_commitment_drift", "source_accumulator"),
    ("compressed_artifact_commitment_drift", "compressed_artifact"),
    ("compressed_artifact_claim_boundary_changed_to_recursive", "compressed_artifact"),
    ("compressed_public_target_commitment_drift", "compressed_public_inputs"),
    ("compressed_selected_statement_drift", "compressed_public_inputs"),
    ("compressed_selected_source_hash_drift", "compressed_public_inputs"),
    ("compressed_selected_public_instance_drift", "compressed_public_inputs"),
    ("compressed_selected_parameter_commitment_drift", "compressed_public_inputs"),
    ("compressed_verifier_domain_drift", "compressed_public_inputs"),
    ("compressed_backend_version_drift", "compressed_public_inputs"),
    ("compressed_source_accumulator_commitment_drift", "compressed_public_inputs"),
    ("compressed_slice_removed", "compressed_transcript"),
    ("compressed_slice_duplicated", "compressed_transcript"),
    ("compressed_slice_reordered", "compressed_transcript"),
    ("compressed_slice_row_count_drift", "compressed_transcript"),
    ("compression_ratio_relabeling", "compression_metrics"),
    ("verifier_handle_commitment_drift", "verifier_handle"),
    ("verifier_handle_claim_boundary_changed_to_recursive", "verifier_handle"),
    ("verifier_handle_artifact_commitment_drift", "verifier_handle"),
    ("verifier_handle_missing_required_public_input", "verifier_handle"),
    ("recursive_outer_proof_claimed", "recursive_or_pcd_status"),
    ("pcd_outer_proof_claimed", "recursive_or_pcd_status"),
    ("recursive_proof_metric_smuggled", "recursive_or_pcd_status"),
    ("recursive_blocker_removed", "recursive_or_pcd_status"),
    ("decision_changed_to_no_go", "parser_or_schema"),
    ("result_changed_to_no_go", "parser_or_schema"),
    ("compression_result_changed_to_no_go", "parser_or_schema"),
    ("recursive_result_changed_to_go", "parser_or_schema"),
    ("non_claims_removed", "parser_or_schema"),
    ("validation_command_drift", "parser_or_schema"),
)

TOP_LEVEL_KEYS = {
    "all_mutations_rejected",
    "case_count",
    "cases",
    "claim_boundary",
    "compressed_artifact",
    "compression_result",
    "compression_status",
    "decision",
    "issue",
    "mutation_inventory",
    "non_claims",
    "recursive_or_pcd_result",
    "recursive_or_pcd_status",
    "result",
    "schema",
    "source_accumulator",
    "summary",
    "validation_commands",
    "verifier_handle",
}

DRAFT_TOP_LEVEL_KEYS = TOP_LEVEL_KEYS - {"all_mutations_rejected", "case_count", "cases", "mutation_inventory"}

COMPRESSED_ARTIFACT_KEYS = {
    "artifact_kind",
    "claim_boundary",
    "compressed_artifact_commitment",
    "issue",
    "preimage",
    "schema",
}

COMPRESSED_ARTIFACT_PREIMAGE_KEYS = {
    "artifact_kind",
    "claim_boundary",
    "compressed_transcript",
    "issue",
    "proof_native_public_input_contract",
    "schema",
    "selected_checked_rows",
    "selected_slice_ids",
    "width",
}

COMPRESSED_PUBLIC_INPUT_KEYS = {
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

COMPRESSED_TRANSCRIPT_ENTRY_KEYS = {
    "index",
    "proof_native_parameter_commitment",
    "public_instance_commitment",
    "row_count",
    "slice_id",
    "source_file_sha256",
    "source_payload_sha256",
    "statement_commitment",
    "target_commitments",
}

VERIFIER_HANDLE_KEYS = {
    "accepted",
    "claim_boundary",
    "preimage",
    "schema",
    "verifier_handle_commitment",
}

VERIFIER_HANDLE_PREIMAGE_KEYS = {
    "accepted_artifact_commitment",
    "accepted_artifact_kind",
    "accepted_artifact_schema",
    "accepted_claim_boundary",
    "required_backend_version",
    "required_public_inputs",
    "schema",
    "selected_slice_proof_native_parameter_commitments",
    "selected_slice_public_instance_commitments",
    "selected_slice_statement_commitments",
    "selected_source_evidence_hashes",
    "source_accumulator_file_sha256",
    "source_accumulator_path",
    "source_accumulator_payload_sha256",
    "two_slice_target_commitment",
    "verifier_domain",
    "verifier_steps",
}

COMPRESSION_STATUS_KEYS = {
    "compressed_artifact_exists",
    "compression_metrics",
    "not_pcd",
    "not_recursive",
    "not_stark_in_stark",
    "result",
    "verifier_handle_accepts",
}

COMPRESSION_METRIC_KEYS = {
    "artifact_bytes_ratio_vs_source_accumulator",
    "byte_savings",
    "compressed_artifact_serialized_bytes",
    "recursive_proof_metrics",
    "source_accumulator_artifact_serialized_bytes",
    "timing_mode",
}

RECURSIVE_STATUS_KEYS = {
    "first_blocker",
    "outer_proof_artifacts",
    "pcd_outer_proof_claimed",
    "proof_metrics",
    "recursive_outer_proof_claimed",
    "result",
    "stark_in_stark_claimed",
}

RECURSIVE_METRIC_KEYS = {
    "recursive_proof_generation_time_ms",
    "recursive_proof_size_bytes",
    "recursive_verifier_time_ms",
}

SUMMARY_KEYS = {
    "claim_boundary",
    "compressed_artifact_commitment",
    "compression_metrics",
    "compression_status",
    "go_criterion",
    "recursive_blocker",
    "recursive_or_pcd_status",
    "selected_checked_rows",
    "selected_slice_ids",
    "source_accumulator_commitment",
    "two_slice_target_commitment",
    "verifier_handle_commitment",
}

SUMMARY_WITH_CASE_KEYS = SUMMARY_KEYS | {"mutation_cases", "mutations_rejected"}


class D128ProofNativeTwoSliceCompressionError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128ProofNativeTwoSliceCompressionError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ACCUMULATOR = _load_module(ACCUMULATOR_SCRIPT, "zkai_d128_two_slice_accumulator_for_proof_native_compression")


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
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D128ProofNativeTwoSliceCompressionError(f"{field} mismatch")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be a list")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be a non-empty string")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be an integer")
    return value


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be a boolean")
    return value


def expect_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise D128ProofNativeTwoSliceCompressionError(f"{field} keys mismatch: missing={missing} extra={extra}")


def require_commitment(value: Any, field: str) -> str:
    value = require_str(value, field)
    if not value.startswith("blake2b-256:"):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def require_sha256_hex(value: Any, field: str) -> str:
    value = require_str(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise D128ProofNativeTwoSliceCompressionError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D128ProofNativeTwoSliceCompressionError(f"source evidence is not a regular file: {path}")
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128ProofNativeTwoSliceCompressionError(f"source evidence path escapes repository: {path}") from err
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as err:
        raise D128ProofNativeTwoSliceCompressionError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128ProofNativeTwoSliceCompressionError(f"source evidence must be a JSON object: {path}")
    return payload


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def load_checked_accumulator(path: pathlib.Path = ACCUMULATOR_EVIDENCE) -> dict[str, Any]:
    payload = load_json(path)
    try:
        ACCUMULATOR.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128ProofNativeTwoSliceCompressionError(f"source accumulator validation failed: {err}") from err
    expect_equal(payload.get("schema"), ACCUMULATOR.SCHEMA, "source accumulator schema")
    expect_equal(payload.get("decision"), ACCUMULATOR.DECISION, "source accumulator decision")
    expect_equal(payload.get("result"), ACCUMULATOR.RESULT, "source accumulator result")
    expect_equal(payload.get("accumulator_result"), ACCUMULATOR.ACCUMULATOR_RESULT, "source accumulator result")
    expect_equal(payload.get("recursive_or_pcd_result"), ACCUMULATOR.RECURSIVE_OR_PCD_RESULT, "source recursive result")
    expect_equal(payload.get("claim_boundary"), ACCUMULATOR.CLAIM_BOUNDARY, "source claim boundary")
    if payload.get("all_mutations_rejected") is not True:
        raise D128ProofNativeTwoSliceCompressionError("source accumulator did not reject all checked mutations")
    return payload


def source_accumulator_descriptor(source: dict[str, Any], path: pathlib.Path = ACCUMULATOR_EVIDENCE) -> dict[str, Any]:
    summary = require_object(source.get("summary"), "source accumulator summary")
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
        "accumulator_commitment": summary["accumulator_commitment"],
        "verifier_handle_commitment": summary["verifier_handle_commitment"],
        "selected_checked_rows": summary["selected_checked_rows"],
    }


def _source_accumulator_artifact(source: dict[str, Any]) -> dict[str, Any]:
    return require_object(source.get("accumulator_artifact"), "source accumulator artifact")


def _source_accumulator_preimage(source: dict[str, Any]) -> dict[str, Any]:
    return require_object(_source_accumulator_artifact(source).get("preimage"), "source accumulator preimage")


def _source_verifier_handle(source: dict[str, Any]) -> dict[str, Any]:
    return require_object(source.get("verifier_handle"), "source verifier handle")


def _public_inputs_from_source(source: dict[str, Any]) -> dict[str, Any]:
    return require_object(_source_accumulator_preimage(source).get("public_inputs"), "source public inputs")


def _target_manifest_from_source(source: dict[str, Any]) -> dict[str, Any]:
    return require_object(_source_accumulator_preimage(source).get("two_slice_target_manifest"), "source target manifest")


def _transcript_from_source(source: dict[str, Any]) -> list[dict[str, Any]]:
    transcript = [require_object(entry, f"source transcript {index}") for index, entry in enumerate(require_list(_source_accumulator_preimage(source).get("verifier_transcript"), "source verifier transcript"))]
    expect_equal([entry.get("slice_id") for entry in transcript], list(EXPECTED_SELECTED_SLICE_IDS), "selected slice ids")
    expect_equal(sum(require_int(entry.get("row_count"), f"{entry.get('slice_id')} row_count") for entry in transcript), EXPECTED_SELECTED_ROWS, "selected checked rows")
    return transcript


def _selected_public_instance_commitments(transcript: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"slice_id": entry["slice_id"], "public_instance_commitment": entry["public_instance_commitment"]}
        for entry in transcript
    ]


def _selected_parameter_commitments(transcript: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"slice_id": entry["slice_id"], "proof_native_parameter_commitment": entry["proof_native_parameter_commitment"]}
        for entry in transcript
    ]


def _compressed_slice_facts(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": entry["index"],
            "slice_id": entry["slice_id"],
            "row_count": entry["row_count"],
            "statement_commitment": entry["statement_commitment"],
            "public_instance_commitment": entry["public_instance_commitment"],
            "proof_native_parameter_commitment": entry["proof_native_parameter_commitment"],
            "source_file_sha256": entry["source_file_sha256"],
            "source_payload_sha256": entry["source_payload_sha256"],
            "target_commitments": copy.deepcopy(entry["target_commitments"]),
        }
        for entry in transcript
    ]


def compressed_artifact_preimage(source: dict[str, Any]) -> dict[str, Any]:
    public_inputs = copy.deepcopy(_public_inputs_from_source(source))
    transcript = _transcript_from_source(source)
    target = _target_manifest_from_source(source)
    source_artifact = _source_accumulator_artifact(source)
    source_handle = _source_verifier_handle(source)
    expect_equal(public_inputs["two_slice_target_commitment"], source["summary"]["two_slice_target_commitment"], "public target")
    expect_equal(public_inputs["selected_slice_statement_commitments"], [
        {"slice_id": entry["slice_id"], "statement_commitment": entry["statement_commitment"]}
        for entry in transcript
    ], "public selected statements")
    expect_equal(public_inputs["selected_source_evidence_hashes"], [
        {
            "slice_id": entry["slice_id"],
            "source_file_sha256": entry["source_file_sha256"],
            "source_payload_sha256": entry["source_payload_sha256"],
        }
        for entry in transcript
    ], "public selected source hashes")
    return {
        "schema": COMPRESSED_ARTIFACT_SCHEMA,
        "artifact_kind": ARTIFACT_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "issue": ISSUE,
        "width": WIDTH,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "proof_native_public_input_contract": {
            "required_public_inputs": [
                "two_slice_target_commitment",
                "selected_slice_statement_commitments",
                "selected_source_evidence_hashes",
                "selected_slice_public_instance_commitments",
                "selected_slice_proof_native_parameter_commitments",
                "verifier_domain",
                "required_backend_version",
                "source_accumulator_commitment",
                "source_verifier_handle_commitment",
            ],
            "two_slice_target_commitment": public_inputs["two_slice_target_commitment"],
            "selected_slice_statement_commitments": copy.deepcopy(public_inputs["selected_slice_statement_commitments"]),
            "selected_source_evidence_hashes": copy.deepcopy(public_inputs["selected_source_evidence_hashes"]),
            "selected_slice_public_instance_commitments": _selected_public_instance_commitments(transcript),
            "selected_slice_proof_native_parameter_commitments": _selected_parameter_commitments(transcript),
            "verifier_domain": target["verifier_domain"],
            "required_backend_version": target["required_backend_version"],
            "source_accumulator_commitment": source_artifact["accumulator_commitment"],
            "source_verifier_handle_commitment": source_handle["verifier_handle_commitment"],
        },
        "compressed_transcript": _compressed_slice_facts(transcript),
    }


def compressed_artifact(source: dict[str, Any]) -> dict[str, Any]:
    preimage = compressed_artifact_preimage(source)
    artifact = {
        "schema": COMPRESSED_ARTIFACT_SCHEMA,
        "artifact_kind": ARTIFACT_KIND,
        "claim_boundary": CLAIM_BOUNDARY,
        "issue": ISSUE,
        "compressed_artifact_commitment": blake2b_commitment(preimage, COMPRESSED_ARTIFACT_DOMAIN),
        "preimage": preimage,
    }
    source_bytes = len(canonical_json_bytes(_source_accumulator_artifact(source)))
    artifact_bytes = len(canonical_json_bytes(artifact))
    if artifact_bytes >= source_bytes:
        raise D128ProofNativeTwoSliceCompressionError("compressed artifact is not smaller than source accumulator artifact")
    return artifact


def verifier_handle_preimage(artifact: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    preimage = require_object(artifact.get("preimage"), "compressed artifact preimage")
    public_inputs = require_object(preimage.get("proof_native_public_input_contract"), "compressed public input contract")
    return {
        "schema": VERIFIER_HANDLE_SCHEMA,
        "accepted_artifact_schema": artifact["schema"],
        "accepted_artifact_kind": artifact["artifact_kind"],
        "accepted_artifact_commitment": artifact["compressed_artifact_commitment"],
        "accepted_claim_boundary": CLAIM_BOUNDARY,
        "source_accumulator_path": relative_path(ACCUMULATOR_EVIDENCE),
        "source_accumulator_file_sha256": file_sha256(ACCUMULATOR_EVIDENCE),
        "source_accumulator_payload_sha256": sha256_hex_json(source),
        "required_public_inputs": copy.deepcopy(public_inputs["required_public_inputs"]),
        "two_slice_target_commitment": public_inputs["two_slice_target_commitment"],
        "selected_slice_statement_commitments": copy.deepcopy(public_inputs["selected_slice_statement_commitments"]),
        "selected_source_evidence_hashes": copy.deepcopy(public_inputs["selected_source_evidence_hashes"]),
        "selected_slice_public_instance_commitments": copy.deepcopy(public_inputs["selected_slice_public_instance_commitments"]),
        "selected_slice_proof_native_parameter_commitments": copy.deepcopy(public_inputs["selected_slice_proof_native_parameter_commitments"]),
        "verifier_domain": public_inputs["verifier_domain"],
        "required_backend_version": public_inputs["required_backend_version"],
        "verifier_steps": [
            "validate source two-slice accumulator evidence",
            "recompute compressed proof-native public input contract",
            "recompute compressed transcript commitment",
            "reject recursive/PCD metric claims",
        ],
    }


def verifier_handle(artifact: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    preimage = verifier_handle_preimage(artifact, source)
    return {
        "schema": VERIFIER_HANDLE_SCHEMA,
        "claim_boundary": CLAIM_BOUNDARY,
        "verifier_handle_commitment": blake2b_commitment(preimage, VERIFIER_HANDLE_DOMAIN),
        "preimage": preimage,
        "accepted": True,
    }


def compression_metrics(source: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    source_bytes = len(canonical_json_bytes(_source_accumulator_artifact(source)))
    artifact_bytes = len(canonical_json_bytes(artifact))
    return {
        "source_accumulator_artifact_serialized_bytes": source_bytes,
        "compressed_artifact_serialized_bytes": artifact_bytes,
        "byte_savings": source_bytes - artifact_bytes,
        "artifact_bytes_ratio_vs_source_accumulator": round(artifact_bytes / source_bytes, 6),
        "timing_mode": "not_timed",
        "recursive_proof_metrics": None,
    }


def compression_status(source: dict[str, Any], artifact: dict[str, Any], handle: dict[str, Any]) -> dict[str, Any]:
    metrics = compression_metrics(source, artifact)
    if metrics["byte_savings"] <= 0:
        raise D128ProofNativeTwoSliceCompressionError("compression byte savings must be positive")
    return {
        "result": COMPRESSION_RESULT,
        "compressed_artifact_exists": True,
        "verifier_handle_accepts": handle["accepted"],
        "not_recursive": True,
        "not_pcd": True,
        "not_stark_in_stark": True,
        "compression_metrics": metrics,
    }


def recursive_or_pcd_status() -> dict[str, Any]:
    return {
        "result": RECURSIVE_OR_PCD_RESULT,
        "recursive_outer_proof_claimed": False,
        "pcd_outer_proof_claimed": False,
        "stark_in_stark_claimed": False,
        "outer_proof_artifacts": [],
        "proof_metrics": {
            "recursive_proof_size_bytes": None,
            "recursive_verifier_time_ms": None,
            "recursive_proof_generation_time_ms": None,
        },
        "first_blocker": RECURSIVE_BLOCKER,
    }


def build_payload() -> dict[str, Any]:
    source = load_checked_accumulator()
    artifact = compressed_artifact(source)
    handle = verifier_handle(artifact, source)
    status = compression_status(source, artifact, handle)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "compression_result": COMPRESSION_RESULT,
        "recursive_or_pcd_result": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_accumulator": source_accumulator_descriptor(source),
        "compressed_artifact": artifact,
        "verifier_handle": handle,
        "compression_status": status,
        "recursive_or_pcd_status": recursive_or_pcd_status(),
        "summary": {
            "compression_status": COMPRESSION_RESULT,
            "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
            "claim_boundary": CLAIM_BOUNDARY,
            "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
            "selected_checked_rows": EXPECTED_SELECTED_ROWS,
            "two_slice_target_commitment": artifact["preimage"]["proof_native_public_input_contract"]["two_slice_target_commitment"],
            "compressed_artifact_commitment": artifact["compressed_artifact_commitment"],
            "verifier_handle_commitment": handle["verifier_handle_commitment"],
            "source_accumulator_commitment": source["summary"]["accumulator_commitment"],
            "go_criterion": GO_CRITERION,
            "recursive_blocker": RECURSIVE_BLOCKER,
            "compression_metrics": status["compression_metrics"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    _validate_draft_payload(payload)
    return payload


def _validate_source_descriptor(payload: dict[str, Any]) -> dict[str, Any]:
    descriptor = require_object(payload.get("source_accumulator"), "source accumulator")
    expected_path = relative_path(ACCUMULATOR_EVIDENCE)
    expect_equal(descriptor.get("path"), expected_path, "source accumulator path")
    source = load_checked_accumulator(ROOT / descriptor["path"])
    expect_equal(descriptor.get("file_sha256"), file_sha256(ACCUMULATOR_EVIDENCE), "source accumulator file hash")
    expect_equal(descriptor.get("payload_sha256"), sha256_hex_json(source), "source accumulator payload hash")
    expected_descriptor = source_accumulator_descriptor(source)
    expect_equal(descriptor, expected_descriptor, "source accumulator descriptor")
    return source


def verify_compressed_artifact(artifact: Any, source: dict[str, Any] | None = None) -> None:
    artifact = require_object(artifact, "compressed artifact")
    expect_keys(artifact, COMPRESSED_ARTIFACT_KEYS, "compressed artifact")
    expect_equal(artifact.get("schema"), COMPRESSED_ARTIFACT_SCHEMA, "compressed artifact schema")
    expect_equal(artifact.get("artifact_kind"), ARTIFACT_KIND, "compressed artifact kind")
    expect_equal(artifact.get("claim_boundary"), CLAIM_BOUNDARY, "compressed artifact claim boundary")
    expect_equal(artifact.get("issue"), ISSUE, "compressed artifact issue")
    preimage = require_object(artifact.get("preimage"), "compressed artifact preimage")
    expect_keys(preimage, COMPRESSED_ARTIFACT_PREIMAGE_KEYS, "compressed artifact preimage")
    public_inputs = require_object(preimage.get("proof_native_public_input_contract"), "compressed public inputs")
    expect_keys(public_inputs, COMPRESSED_PUBLIC_INPUT_KEYS, "compressed public inputs")
    for index, raw_entry in enumerate(require_list(preimage.get("compressed_transcript"), "compressed transcript")):
        entry = require_object(raw_entry, f"compressed transcript entry {index}")
        expect_keys(entry, COMPRESSED_TRANSCRIPT_ENTRY_KEYS, f"compressed transcript entry {index}")
    source = copy.deepcopy(source) if source is not None else load_checked_accumulator()
    expected_artifact = compressed_artifact(source)
    expect_equal(artifact, expected_artifact, "compressed artifact")


def verify_verifier_handle(handle: Any, artifact: dict[str, Any], source: dict[str, Any]) -> None:
    handle = require_object(handle, "verifier handle")
    expect_keys(handle, VERIFIER_HANDLE_KEYS, "verifier handle")
    expect_equal(handle.get("schema"), VERIFIER_HANDLE_SCHEMA, "verifier handle schema")
    expect_equal(handle.get("claim_boundary"), CLAIM_BOUNDARY, "verifier handle claim boundary")
    expect_equal(handle.get("accepted"), True, "verifier handle accepted")
    preimage = require_object(handle.get("preimage"), "verifier handle preimage")
    expect_keys(preimage, VERIFIER_HANDLE_PREIMAGE_KEYS, "verifier handle preimage")
    expected = verifier_handle(artifact, source)
    expect_equal(handle, expected, "verifier handle")


def _validate_compression_status(payload: dict[str, Any], source: dict[str, Any], artifact: dict[str, Any], handle: dict[str, Any]) -> None:
    status = require_object(payload.get("compression_status"), "compression status")
    expect_keys(status, COMPRESSION_STATUS_KEYS, "compression status")
    metrics = require_object(status.get("compression_metrics"), "compression metrics")
    expect_keys(metrics, COMPRESSION_METRIC_KEYS, "compression metrics")
    expect_equal(status, compression_status(source, artifact, handle), "compression status")


def _validate_recursive_status(payload: dict[str, Any]) -> None:
    status = require_object(payload.get("recursive_or_pcd_status"), "recursive or PCD status")
    expect_keys(status, RECURSIVE_STATUS_KEYS, "recursive or PCD status")
    metrics = require_object(status.get("proof_metrics"), "recursive or PCD metrics")
    expect_keys(metrics, RECURSIVE_METRIC_KEYS, "recursive or PCD metrics")
    expect_equal(status, recursive_or_pcd_status(), "recursive or PCD status")


def _expected_summary(source: dict[str, Any], artifact: dict[str, Any], handle: dict[str, Any]) -> dict[str, Any]:
    status = compression_status(source, artifact, handle)
    return {
        "compression_status": COMPRESSION_RESULT,
        "recursive_or_pcd_status": RECURSIVE_OR_PCD_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "selected_slice_ids": list(EXPECTED_SELECTED_SLICE_IDS),
        "selected_checked_rows": EXPECTED_SELECTED_ROWS,
        "two_slice_target_commitment": artifact["preimage"]["proof_native_public_input_contract"]["two_slice_target_commitment"],
        "compressed_artifact_commitment": artifact["compressed_artifact_commitment"],
        "verifier_handle_commitment": handle["verifier_handle_commitment"],
        "source_accumulator_commitment": source["summary"]["accumulator_commitment"],
        "go_criterion": GO_CRITERION,
        "recursive_blocker": RECURSIVE_BLOCKER,
        "compression_metrics": status["compression_metrics"],
    }


def _validate_common_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = require_object(payload, "proof-native two-slice compression payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), RESULT, "result")
    expect_equal(payload.get("issue"), ISSUE, "issue")
    expect_equal(payload.get("compression_result"), COMPRESSION_RESULT, "compression result")
    expect_equal(payload.get("recursive_or_pcd_result"), RECURSIVE_OR_PCD_RESULT, "recursive or PCD result")
    expect_equal(payload.get("claim_boundary"), CLAIM_BOUNDARY, "claim boundary")
    source = _validate_source_descriptor(payload)
    artifact = require_object(payload.get("compressed_artifact"), "compressed artifact")
    verify_compressed_artifact(artifact, source)
    handle = require_object(payload.get("verifier_handle"), "verifier handle")
    verify_verifier_handle(handle, artifact, source)
    _validate_compression_status(payload, source, artifact, handle)
    _validate_recursive_status(payload)
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non-claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    return source, artifact, handle, _expected_summary(source, artifact, handle)


def _validate_draft_payload(payload: Any) -> None:
    expect_keys(require_object(payload, "draft payload"), DRAFT_TOP_LEVEL_KEYS, "draft payload")
    _source, _artifact, _handle, expected_summary = _validate_common_payload(payload)
    if (
        "mutation_inventory" in payload
        or "cases" in payload
        or "case_count" in payload
        or "all_mutations_rejected" in payload
    ):
        raise D128ProofNativeTwoSliceCompressionError("draft payload must not include mutation metadata")
    expect_keys(require_object(payload.get("summary"), "summary"), SUMMARY_KEYS, "summary")
    expect_equal(payload.get("summary"), expected_summary, "summary")


def _validate_case_metadata(payload: dict[str, Any]) -> tuple[int, int]:
    has_mutation_metadata = [field in payload for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected")]
    if not any(has_mutation_metadata):
        raise D128ProofNativeTwoSliceCompressionError("mutation metadata missing")
    if not all(has_mutation_metadata):
        raise D128ProofNativeTwoSliceCompressionError("mutation metadata must be all-or-nothing")
    inventory = require_list(payload.get("mutation_inventory"), "mutation inventory")
    expect_equal(inventory, expected_mutation_inventory(), "mutation inventory")
    cases = require_list(payload.get("cases"), "mutation cases")
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    rejected = 0
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        expect_keys(case, MUTATION_CASE_KEYS, f"mutation case {index}")
        for column in TSV_COLUMNS:
            if column not in case:
                raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} missing {column}")
        pair = (require_str(case["mutation"], f"mutation case {index} mutation"), require_str(case["surface"], f"mutation case {index} surface"))
        if pair in seen:
            raise D128ProofNativeTwoSliceCompressionError(f"duplicate mutation case {index}")
        seen.add(pair)
        pairs.append(pair)
        expect_equal(case["baseline_result"], RESULT, f"mutation case {index} baseline result")
        accepted = require_bool(case["mutated_accepted"], f"mutation case {index} mutated_accepted")
        rejected_flag = require_bool(case["rejected"], f"mutation case {index} rejected")
        if accepted == rejected_flag:
            raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} rejected/accepted mismatch")
        rejection_layer = require_str(case["rejection_layer"], f"mutation case {index} rejection layer")
        error_code = require_str(case["error_code"], f"mutation case {index} error_code")
        if accepted:
            expect_equal(error_code, "accepted", f"mutation case {index} error_code")
        else:
            if error_code == "accepted" or not error_code:
                raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} error_code must identify the rejection")
        if not isinstance(case["error"], str):
            raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} error must be a string")
        if "\t" in case["error"] or "\n" in case["error"] or "\r" in case["error"]:
            raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} error must be single-line TSV-safe text")
        if accepted and case["error"]:
            raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} accepted error must be empty")
        if rejected_flag and not case["error"]:
            raise D128ProofNativeTwoSliceCompressionError(f"mutation case {index} rejected error must be non-empty")
        if rejected_flag:
            rejected += 1
    expect_equal(tuple(pairs), EXPECTED_MUTATION_INVENTORY, "mutation case inventory")
    expect_equal(payload.get("case_count"), len(cases), "case_count")
    expect_equal(payload.get("all_mutations_rejected"), all(case["rejected"] for case in cases), "all_mutations_rejected")
    expected_by_pair = {(case["mutation"], case["surface"]): case for case in mutation_cases(_draft_payload_for_case_replay(payload))}
    for index, raw_case in enumerate(cases):
        case = require_object(raw_case, f"mutation case {index}")
        expected = expected_by_pair.get((case["mutation"], case["surface"]))
        if expected is None:
            raise D128ProofNativeTwoSliceCompressionError(f"missing recomputed mutation case {index}")
        for column in TSV_COLUMNS:
            if column == "error":
                continue
            expect_equal(case[column], expected[column], f"mutation case {index} {column}")
    return len(cases), rejected


def _draft_payload_for_case_replay(payload: dict[str, Any]) -> dict[str, Any]:
    draft = copy.deepcopy(payload)
    for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected"):
        draft.pop(field, None)
    summary = require_object(draft.get("summary"), "summary")
    summary.pop("mutation_cases", None)
    summary.pop("mutations_rejected", None)
    return draft


def validate_payload(payload: Any) -> None:
    payload = require_object(payload, "proof-native two-slice compression payload")
    has_mutation_metadata = [field in payload for field in ("mutation_inventory", "cases", "case_count", "all_mutations_rejected")]
    if any(has_mutation_metadata) and not all(has_mutation_metadata):
        raise D128ProofNativeTwoSliceCompressionError("mutation metadata must be all-or-nothing")
    expect_keys(payload, TOP_LEVEL_KEYS, "proof-native two-slice compression payload")
    _source, _artifact, _handle, expected_summary = _validate_common_payload(payload)
    case_count, rejected = _validate_case_metadata(payload)
    if rejected != case_count:
        raise D128ProofNativeTwoSliceCompressionError("not all proof-native compression mutations rejected")
    expected_summary["mutation_cases"] = case_count
    expected_summary["mutations_rejected"] = rejected
    expect_keys(require_object(payload.get("summary"), "summary"), SUMMARY_WITH_CASE_KEYS, "summary")
    expect_equal(payload.get("summary"), expected_summary, "summary")


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None]) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        cases.append((name, surface, mutated))

    add("source_accumulator_file_hash_drift", "source_accumulator", lambda p: p["source_accumulator"].__setitem__("file_sha256", "00" * 32))
    add("source_accumulator_payload_hash_drift", "source_accumulator", lambda p: p["source_accumulator"].__setitem__("payload_sha256", "11" * 32))
    add("source_accumulator_result_drift", "source_accumulator", lambda p: p["source_accumulator"].__setitem__("result", "NO_GO"))
    add("source_accumulator_claim_boundary_drift", "source_accumulator", lambda p: p["source_accumulator"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("source_accumulator_commitment_drift", "source_accumulator", lambda p: p["source_accumulator"].__setitem__("accumulator_commitment", "blake2b-256:" + "22" * 32))
    add("compressed_artifact_commitment_drift", "compressed_artifact", lambda p: p["compressed_artifact"].__setitem__("compressed_artifact_commitment", "blake2b-256:" + "33" * 32))
    add("compressed_artifact_claim_boundary_changed_to_recursive", "compressed_artifact", lambda p: p["compressed_artifact"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("compressed_public_target_commitment_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"].__setitem__("two_slice_target_commitment", "blake2b-256:" + "44" * 32))
    add("compressed_selected_statement_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["selected_slice_statement_commitments"][0].__setitem__("statement_commitment", "blake2b-256:" + "55" * 32))
    add("compressed_selected_source_hash_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["selected_source_evidence_hashes"][0].__setitem__("source_payload_sha256", "66" * 32))
    add("compressed_selected_public_instance_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["selected_slice_public_instance_commitments"][0].__setitem__("public_instance_commitment", "blake2b-256:" + "77" * 32))
    add("compressed_selected_parameter_commitment_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"]["selected_slice_proof_native_parameter_commitments"][0].__setitem__("proof_native_parameter_commitment", "blake2b-256:" + "88" * 32))
    add("compressed_verifier_domain_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"].__setitem__("verifier_domain", "ptvm:tampered:v0"))
    add("compressed_backend_version_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"].__setitem__("required_backend_version", "wrong-backend"))
    add("compressed_source_accumulator_commitment_drift", "compressed_public_inputs", lambda p: p["compressed_artifact"]["preimage"]["proof_native_public_input_contract"].__setitem__("source_accumulator_commitment", "blake2b-256:" + "99" * 32))
    add("compressed_slice_removed", "compressed_transcript", lambda p: p["compressed_artifact"]["preimage"]["compressed_transcript"].pop())
    add("compressed_slice_duplicated", "compressed_transcript", lambda p: p["compressed_artifact"]["preimage"]["compressed_transcript"].append(copy.deepcopy(p["compressed_artifact"]["preimage"]["compressed_transcript"][0])))
    add("compressed_slice_reordered", "compressed_transcript", lambda p: p["compressed_artifact"]["preimage"]["compressed_transcript"].reverse())
    add("compressed_slice_row_count_drift", "compressed_transcript", lambda p: p["compressed_artifact"]["preimage"]["compressed_transcript"][0].__setitem__("row_count", 127))
    add("compression_ratio_relabeling", "compression_metrics", lambda p: p["compression_status"]["compression_metrics"].__setitem__("artifact_bytes_ratio_vs_source_accumulator", 0.001))
    add("verifier_handle_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"].__setitem__("verifier_handle_commitment", "blake2b-256:" + "aa" * 32))
    add("verifier_handle_claim_boundary_changed_to_recursive", "verifier_handle", lambda p: p["verifier_handle"].__setitem__("claim_boundary", "RECURSIVE_OUTER_PROOF"))
    add("verifier_handle_artifact_commitment_drift", "verifier_handle", lambda p: p["verifier_handle"]["preimage"].__setitem__("accepted_artifact_commitment", "blake2b-256:" + "bb" * 32))
    add("verifier_handle_missing_required_public_input", "verifier_handle", lambda p: p["verifier_handle"]["preimage"]["required_public_inputs"].pop())
    add("recursive_outer_proof_claimed", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"].__setitem__("recursive_outer_proof_claimed", True))
    add("pcd_outer_proof_claimed", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"].__setitem__("pcd_outer_proof_claimed", True))
    add("recursive_proof_metric_smuggled", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"]["proof_metrics"].__setitem__("recursive_verifier_time_ms", 1.0))
    add("recursive_blocker_removed", "recursive_or_pcd_status", lambda p: p["recursive_or_pcd_status"].__setitem__("first_blocker", ""))
    add("decision_changed_to_no_go", "parser_or_schema", lambda p: p.__setitem__("decision", "NO_GO"))
    add("result_changed_to_no_go", "parser_or_schema", lambda p: p.__setitem__("result", "BOUNDED_NO_GO"))
    add("compression_result_changed_to_no_go", "parser_or_schema", lambda p: p.__setitem__("compression_result", "NO_GO"))
    add("recursive_result_changed_to_go", "parser_or_schema", lambda p: p.__setitem__("recursive_or_pcd_result", "GO_RECURSIVE_OUTER_PROOF"))
    add("non_claims_removed", "parser_or_schema", lambda p: p.__setitem__("non_claims", p["non_claims"][:-1]))
    add("validation_command_drift", "parser_or_schema", lambda p: p["validation_commands"].append("echo unsafe"))
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
            error_code = "accepted"
        except D128ProofNativeTwoSliceCompressionError as err:
            accepted = False
            error = str(err)
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
                "error": error,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    payload = build_payload()
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
    for case in payload["cases"]:
        writer.writerow({column: case[column] for column in TSV_COLUMNS})
    return output.getvalue()


def _safe_output_path(path: pathlib.Path, expected_suffix: str) -> pathlib.Path:
    if path.is_absolute():
        raise D128ProofNativeTwoSliceCompressionError(f"output path must be repo-relative: {path}")
    if path.suffix != expected_suffix:
        raise D128ProofNativeTwoSliceCompressionError(f"output path must end in {expected_suffix}: {path}")
    pure = pathlib.PurePosixPath(path.as_posix())
    if path.as_posix() != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise D128ProofNativeTwoSliceCompressionError(f"output path must be repo-relative without traversal: {path}")
    candidate = ROOT.joinpath(*pure.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise D128ProofNativeTwoSliceCompressionError(f"output path must stay under docs/engineering/evidence: {path}") from err
    return candidate


def _resolved_output_target(path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    evidence_root = EVIDENCE_DIR.resolve(strict=True)
    resolved_parent = path.parent.resolve(strict=True)
    try:
        resolved_parent.relative_to(evidence_root)
    except ValueError as err:
        raise D128ProofNativeTwoSliceCompressionError(f"output parent escaped docs/engineering/evidence: {path}") from err
    final_path = resolved_parent / path.name
    resolved_final = final_path.resolve(strict=False)
    try:
        resolved_final.relative_to(evidence_root)
    except ValueError as err:
        raise D128ProofNativeTwoSliceCompressionError(f"output path must stay under docs/engineering/evidence: {path}") from err
    return final_path, resolved_final


def _write_bytes_via_dirfd(final_path: pathlib.Path, data: bytes) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    dir_fd = os.open(final_path.parent, flags)
    tmp_name = f".{final_path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    tmp_fd: int | None = None
    tmp_created = False
    try:
        if not stat.S_ISDIR(os.fstat(dir_fd).st_mode):
            raise D128ProofNativeTwoSliceCompressionError(f"output parent is not a directory: {final_path.parent}")
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
        raise D128ProofNativeTwoSliceCompressionError("write-json and write-tsv output paths must be distinct")
    for _path, data, final_path, _resolved_final in resolved_targets:
        _write_bytes_via_dirfd(final_path, data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build d128 proof-native two-slice transcript-compression evidence. "
            "GO means compressed public-input/transcript object only; recursive/PCD outer proof remains NO-GO."
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
