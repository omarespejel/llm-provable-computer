#!/usr/bin/env python3
"""Independent reference checks for paper-facing proof-carrying artifacts.

This module intentionally does not import the Rust crate, generated bindings, or
repo-local schemas. It re-implements a narrow Phase 37 receipt check with the
Python standard library so common-mode parser/struct mistakes are easier to
spot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HASH32_RE = re.compile(r"^[0-9a-f]{64}$")

PHASE37_DOMAIN = b"phase37-recursive-artifact-chain-harness-receipt"
PHASE37_REQUIRED_FIELDS = (
    "proof_backend",
    "receipt_version",
    "semantic_scope",
    "verifier_harness",
    "proof_backend_version",
    "statement_version",
    "step_relation",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "phase29_input_contract_verified",
    "phase30_step_envelope_manifest_verified",
    "phase31_decode_boundary_bridge_verified",
    "phase32_statement_contract_verified",
    "phase33_public_inputs_verified",
    "phase34_shared_lookup_verified",
    "phase35_target_manifest_verified",
    "phase36_verifier_harness_receipt_verified",
    "source_binding_verified",
    "phase29_contract_version",
    "phase29_semantic_scope",
    "phase29_input_contract_commitment",
    "phase30_manifest_version",
    "phase30_semantic_scope",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "phase31_decode_boundary_bridge_commitment",
    "phase32_recursive_statement_contract_commitment",
    "phase33_recursive_public_inputs_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "phase35_recursive_target_manifest_commitment",
    "phase36_recursive_verifier_harness_receipt_commitment",
    "total_steps",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
    "recursive_artifact_chain_harness_receipt_commitment",
)

PHASE37_CONSTS = {
    "proof_backend": "stwo",
    "receipt_version": "stwo-phase37-recursive-artifact-chain-harness-receipt-v1",
    "semantic_scope": "stwo_execution_parameterized_recursive_artifact_chain_harness_receipt",
    "verifier_harness": "source-bound-recursive-artifact-chain-verifier-v1",
    "proof_backend_version": "stwo-phase12-decoding-family-v9",
    "statement_version": "statement-v1",
    "step_relation": "decoding_step_v2",
    "required_recursion_posture": "pre-recursive-proof-carrying-aggregation",
    "phase29_contract_version": "stwo-phase29-recursive-compression-input-contract-v1",
    "phase29_semantic_scope": "stwo_phase29_recursive_compression_input_contract",
    "phase30_manifest_version": "stwo-phase30-decoding-step-proof-envelope-manifest-v1",
    "phase30_semantic_scope": "stwo_execution_parameterized_decoding_step_proof_envelope_manifest",
}

PHASE37_FALSE_FLAGS = (
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
)
PHASE37_TRUE_FLAGS = (
    "phase29_input_contract_verified",
    "phase30_step_envelope_manifest_verified",
    "phase31_decode_boundary_bridge_verified",
    "phase32_statement_contract_verified",
    "phase33_public_inputs_verified",
    "phase34_shared_lookup_verified",
    "phase35_target_manifest_verified",
    "phase36_verifier_harness_receipt_verified",
    "source_binding_verified",
)
PHASE37_HASH_FIELDS = (
    "phase29_input_contract_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "phase31_decode_boundary_bridge_commitment",
    "phase32_recursive_statement_contract_commitment",
    "phase33_recursive_public_inputs_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "phase35_recursive_target_manifest_commitment",
    "phase36_recursive_verifier_harness_receipt_commitment",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
    "recursive_artifact_chain_harness_receipt_commitment",
)
PHASE37_COMMIT_STRING_FIELDS = (
    "proof_backend",
    "receipt_version",
    "semantic_scope",
    "verifier_harness",
    "proof_backend_version",
    "statement_version",
    "step_relation",
    "required_recursion_posture",
    "phase29_contract_version",
    "phase29_semantic_scope",
    "phase29_input_contract_commitment",
    "phase30_manifest_version",
    "phase30_semantic_scope",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "phase31_decode_boundary_bridge_commitment",
    "phase32_recursive_statement_contract_commitment",
    "phase33_recursive_public_inputs_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "phase35_recursive_target_manifest_commitment",
    "phase36_recursive_verifier_harness_receipt_commitment",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
)

PHASE38_LOOKUP_IDENTITY_DOMAIN = b"phase38-paper3-lookup-identity"
PHASE38_SHARED_LOOKUP_IDENTITY_DOMAIN = b"phase38-paper3-shared-lookup-identity"
PHASE38_SEGMENT_LIST_DOMAIN = b"phase38-paper3-composition-segment-list"
PHASE38_PROTOTYPE_DOMAIN = b"phase38-paper3-composition-prototype"
PHASE38_REQUIRED_FIELDS = (
    "proof_backend",
    "prototype_version",
    "semantic_scope",
    "proof_backend_version",
    "statement_version",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "segment_count",
    "total_steps",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "shared_lookup_identity_commitment",
    "segment_list_commitment",
    "naive_per_step_package_count",
    "composed_segment_package_count",
    "package_count_delta",
    "segments",
    "composition_commitment",
)
PHASE38_SEGMENT_REQUIRED_FIELDS = (
    "segment_index",
    "step_start",
    "step_end",
    "total_steps",
    "phase29_contract",
    "phase30_manifest",
    "phase37_receipt",
    "phase37_receipt_commitment",
    "lookup_identity_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
)
PHASE38_PHASE29_CONTRACT_REQUIRED_FIELDS = (
    "proof_backend",
    "contract_version",
    "semantic_scope",
    "phase28_artifact_version",
    "phase28_semantic_scope",
    "phase28_proof_backend_version",
    "statement_version",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "phase28_bounded_aggregation_arity",
    "phase28_member_count",
    "phase28_member_summaries",
    "phase28_nested_members",
    "total_phase26_members",
    "total_phase25_members",
    "max_nested_chain_arity",
    "max_nested_fold_arity",
    "total_matrices",
    "total_layouts",
    "total_rollups",
    "total_segments",
    "total_steps",
    "lookup_delta_entries",
    "max_lookup_frontier_entries",
    "source_template_commitment",
    "global_start_state_commitment",
    "global_end_state_commitment",
    "aggregation_template_commitment",
    "aggregated_chained_folded_interval_accumulator_commitment",
    "input_contract_commitment",
)
PHASE38_PHASE30_MANIFEST_REQUIRED_FIELDS = (
    "proof_backend",
    "manifest_version",
    "semantic_scope",
    "proof_backend_version",
    "statement_version",
    "source_chain_version",
    "source_chain_semantic_scope",
    "source_chain_commitment",
    "layout",
    "total_steps",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "step_envelopes_commitment",
    "envelopes",
)
PHASE38_PHASE30_LAYOUT_REQUIRED_FIELDS = (
    "layout_version",
    "rolling_kv_pairs",
    "pair_width",
)
PHASE38_PHASE30_ENVELOPE_REQUIRED_FIELDS = (
    "envelope_version",
    "semantic_scope",
    "proof_backend",
    "proof_backend_version",
    "statement_version",
    "relation",
    "layout_commitment",
    "source_chain_commitment",
    "step_index",
    "input_boundary_commitment",
    "output_boundary_commitment",
    "input_lookup_rows_commitment",
    "output_lookup_rows_commitment",
    "shared_lookup_artifact_commitment",
    "static_lookup_registry_commitment",
    "proof_commitment",
    "envelope_commitment",
)
PHASE38_CONSTS = {
    "proof_backend": "stwo",
    "prototype_version": "stwo-phase38-paper3-composition-prototype-v1",
    "semantic_scope": "stwo_execution_parameterized_paper3_composition_prototype",
    "proof_backend_version": "stwo-phase12-decoding-family-v9",
    "statement_version": "statement-v1",
    "required_recursion_posture": "pre-recursive-proof-carrying-aggregation",
}
PHASE38_PHASE29_CONTRACT_CONSTS = {
    "proof_backend": "stwo",
    "contract_version": "stwo-phase29-recursive-compression-input-contract-v1",
    "semantic_scope": "stwo_phase29_recursive_compression_input_contract",
    "phase28_artifact_version": "stwo-phase28-aggregated-chained-folded-intervalized-decoding-state-relation-v1",
    "phase28_semantic_scope": "stwo_execution_parameterized_aggregated_chained_folded_intervalized_proof_carrying_decoding_state_relation",
    "phase28_proof_backend_version": "stwo-phase12-decoding-family-v9",
    "statement_version": "statement-v1",
    "required_recursion_posture": "pre-recursive-proof-carrying-aggregation",
}
PHASE38_PHASE30_MANIFEST_CONSTS = {
    "proof_backend": "stwo",
    "manifest_version": "stwo-phase30-decoding-step-proof-envelope-manifest-v1",
    "semantic_scope": "stwo_execution_parameterized_decoding_step_proof_envelope_manifest",
    "proof_backend_version": "stwo-phase12-decoding-family-v9",
    "statement_version": "statement-v1",
    "source_chain_version": "stwo-phase12-decoding-chain-v9",
    "source_chain_semantic_scope": "stwo_execution_parameterized_proof_carrying_decoding_chain",
}
PHASE38_PHASE30_ENVELOPE_CONSTS = {
    "envelope_version": "stwo-phase30-decoding-step-proof-envelope-v1",
    "semantic_scope": "stwo_execution_parameterized_decoding_step_proof_envelope",
    "proof_backend": "stwo",
    "proof_backend_version": "stwo-phase12-decoding-family-v9",
    "statement_version": "statement-v1",
    "relation": "decoding_step_v2",
}
PHASE38_FALSE_FLAGS = (
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
)
PHASE38_HASH_FIELDS = (
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "shared_lookup_identity_commitment",
    "segment_list_commitment",
    "composition_commitment",
)
PHASE38_SEGMENT_HASH_FIELDS = (
    "phase37_receipt_commitment",
    "lookup_identity_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "phase34_shared_lookup_public_inputs_commitment",
    "input_lookup_rows_commitments_commitment",
    "output_lookup_rows_commitments_commitment",
    "shared_lookup_artifact_commitments_commitment",
    "static_lookup_registry_commitments_commitment",
)
PHASE38_PHASE29_CONTRACT_HASH_FIELDS = (
    "source_template_commitment",
    "global_start_state_commitment",
    "global_end_state_commitment",
    "aggregation_template_commitment",
    "aggregated_chained_folded_interval_accumulator_commitment",
    "input_contract_commitment",
)
PHASE38_PHASE30_MANIFEST_HASH_FIELDS = (
    "source_chain_commitment",
    "chain_start_boundary_commitment",
    "chain_end_boundary_commitment",
    "step_envelopes_commitment",
)
PHASE38_PHASE30_ENVELOPE_HASH_FIELDS = (
    "layout_commitment",
    "source_chain_commitment",
    "input_boundary_commitment",
    "output_boundary_commitment",
    "input_lookup_rows_commitment",
    "output_lookup_rows_commitment",
    "shared_lookup_artifact_commitment",
    "static_lookup_registry_commitment",
    "proof_commitment",
    "envelope_commitment",
)


class ReferenceVerifierError(ValueError):
    """Raised when a reference artifact check fails."""


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReferenceVerifierError(f"{path}: failed to read JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReferenceVerifierError(f"{path}: JSON root must be an object")
    return payload


def update_len_prefixed(hasher: Any, data: bytes) -> None:
    hasher.update(len(data).to_bytes(16, byteorder="little", signed=False))
    hasher.update(data)


def update_bool(hasher: Any, value: bool) -> None:
    hasher.update(b"\x01" if value else b"\x00")


def update_usize(hasher: Any, value: int) -> None:
    if value < 0:
        raise ReferenceVerifierError("usize commitment input must be non-negative")
    if value >= 2**128:
        raise ReferenceVerifierError("usize commitment input exceeds 128-bit encoding")
    hasher.update(value.to_bytes(16, byteorder="little", signed=False))


def commit_phase37_receipt(receipt: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    update_len_prefixed(hasher, PHASE37_DOMAIN)
    for key in PHASE37_COMMIT_STRING_FIELDS[:8]:
        update_len_prefixed(hasher, require_string(receipt, key).encode("utf-8"))
    for key in (*PHASE37_FALSE_FLAGS, *PHASE37_TRUE_FLAGS):
        update_bool(hasher, require_bool(receipt, key))
    for key in PHASE37_COMMIT_STRING_FIELDS[8:21]:
        update_len_prefixed(hasher, require_string(receipt, key).encode("utf-8"))
    update_usize(hasher, require_positive_int(receipt, "total_steps"))
    for key in PHASE37_COMMIT_STRING_FIELDS[21:]:
        update_len_prefixed(hasher, require_string(receipt, key).encode("utf-8"))
    return hasher.hexdigest()


def require_string(receipt: dict[str, Any], key: str) -> str:
    value = receipt.get(key)
    if not isinstance(value, str):
        raise ReferenceVerifierError(f"{key} must be a string")
    return value


def require_bool(receipt: dict[str, Any], key: str) -> bool:
    value = receipt.get(key)
    if not isinstance(value, bool):
        raise ReferenceVerifierError(f"{key} must be boolean")
    return value


def require_positive_int(receipt: dict[str, Any], key: str) -> int:
    value = receipt.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferenceVerifierError(f"{key} must be an integer")
    if value <= 0:
        raise ReferenceVerifierError(f"{key} must be positive")
    return value


def require_non_negative_int(receipt: dict[str, Any], key: str) -> int:
    value = receipt.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferenceVerifierError(f"{key} must be an integer")
    if value < 0:
        raise ReferenceVerifierError(f"{key} must be non-negative")
    return value


def require_object(receipt: dict[str, Any], key: str) -> dict[str, Any]:
    value = receipt.get(key)
    if not isinstance(value, dict):
        raise ReferenceVerifierError(f"{key} must be an object")
    return value


def require_list(receipt: dict[str, Any], key: str) -> list[Any]:
    value = receipt.get(key)
    if not isinstance(value, list):
        raise ReferenceVerifierError(f"{key} must be an array")
    return value


def require_exact_fields(value: dict[str, Any], required_fields: tuple[str, ...], label: str) -> None:
    keys = set(value)
    required = set(required_fields)
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing:
        raise ReferenceVerifierError(f"missing {label} fields: {missing}")
    if extra:
        raise ReferenceVerifierError(f"unknown {label} fields: {extra}")


def require_hash32(receipt: dict[str, Any], key: str) -> str:
    value = require_string(receipt, key)
    if not HASH32_RE.fullmatch(value):
        raise ReferenceVerifierError(f"{key} must be lowercase 64-character hex")
    return value


def require_consts(receipt: dict[str, Any], consts: dict[str, str]) -> None:
    for key, expected in consts.items():
        actual = require_string(receipt, key)
        if actual != expected:
            raise ReferenceVerifierError(f"{key} expected {expected!r}, got {actual!r}")


def verify_phase37_receipt(receipt: dict[str, Any]) -> None:
    require_exact_fields(receipt, PHASE37_REQUIRED_FIELDS, "Phase 37")

    require_consts(receipt, PHASE37_CONSTS)

    for key in PHASE37_FALSE_FLAGS:
        if require_bool(receipt, key):
            raise ReferenceVerifierError(f"{key} must be false")
    for key in PHASE37_TRUE_FLAGS:
        if not require_bool(receipt, key):
            raise ReferenceVerifierError(f"{key} must be true")

    require_positive_int(receipt, "total_steps")
    for key in PHASE37_HASH_FIELDS:
        require_hash32(receipt, key)

    expected = commit_phase37_receipt(receipt)
    actual = require_string(receipt, "recursive_artifact_chain_harness_receipt_commitment")
    if actual != expected:
        raise ReferenceVerifierError(
            "recursive_artifact_chain_harness_receipt_commitment mismatch: "
            f"got {actual}, recomputed {expected}"
        )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def phase38_layout_json_bytes(layout: dict[str, Any]) -> bytes:
    require_exact_fields(layout, PHASE38_PHASE30_LAYOUT_REQUIRED_FIELDS, "Phase 38 Phase 30 layout")
    ordered_layout = {
        "layout_version": require_string(layout, "layout_version"),
        "rolling_kv_pairs": require_positive_int(layout, "rolling_kv_pairs"),
        "pair_width": require_positive_int(layout, "pair_width"),
    }
    return canonical_json_bytes(ordered_layout)


def commit_phase38_lookup_identity(manifest: dict[str, Any]) -> str:
    layout = require_object(manifest, "layout")
    envelopes = require_list(manifest, "envelopes")
    static_registries = []
    for envelope_value in envelopes:
        if not isinstance(envelope_value, dict):
            raise ReferenceVerifierError("phase30_manifest.envelopes entries must be objects")
        static_registries.append(require_hash32(envelope_value, "static_lookup_registry_commitment"))
    static_registries = sorted(set(static_registries))
    hasher = hashlib.blake2b(digest_size=32)
    update_len_prefixed(hasher, PHASE38_LOOKUP_IDENTITY_DOMAIN)
    update_len_prefixed(hasher, require_string(manifest, "proof_backend_version").encode("utf-8"))
    update_len_prefixed(hasher, require_string(manifest, "statement_version").encode("utf-8"))
    update_len_prefixed(hasher, require_string(manifest, "source_chain_version").encode("utf-8"))
    update_len_prefixed(
        hasher,
        require_string(manifest, "source_chain_semantic_scope").encode("utf-8"),
    )
    update_len_prefixed(hasher, phase38_layout_json_bytes(layout))
    update_usize(hasher, len(static_registries))
    for registry in static_registries:
        update_len_prefixed(hasher, registry.encode("utf-8"))
    return hasher.hexdigest()


def commit_phase38_shared_lookup_identity(segment: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    update_len_prefixed(hasher, PHASE38_SHARED_LOOKUP_IDENTITY_DOMAIN)
    update_len_prefixed(hasher, require_hash32(segment, "lookup_identity_commitment").encode("utf-8"))
    return hasher.hexdigest()


def commit_phase38_segment_list(segments: list[dict[str, Any]]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    update_len_prefixed(hasher, PHASE38_SEGMENT_LIST_DOMAIN)
    update_usize(hasher, len(segments))
    for segment in segments:
        update_usize(hasher, require_non_negative_int(segment, "segment_index"))
        update_usize(hasher, require_non_negative_int(segment, "step_start"))
        update_usize(hasher, require_positive_int(segment, "step_end"))
        update_usize(hasher, require_positive_int(segment, "total_steps"))
        for key in PHASE38_SEGMENT_HASH_FIELDS:
            update_len_prefixed(hasher, require_hash32(segment, key).encode("utf-8"))
    return hasher.hexdigest()


def commit_phase38_composition_prototype(prototype: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    update_len_prefixed(hasher, PHASE38_PROTOTYPE_DOMAIN)
    for key in (
        "proof_backend",
        "prototype_version",
        "semantic_scope",
        "proof_backend_version",
        "statement_version",
        "required_recursion_posture",
    ):
        update_len_prefixed(hasher, require_string(prototype, key).encode("utf-8"))
    for key in PHASE38_FALSE_FLAGS:
        update_bool(hasher, require_bool(prototype, key))
    for key in ("segment_count", "total_steps"):
        update_usize(hasher, require_positive_int(prototype, key))
    for key in (
        "chain_start_boundary_commitment",
        "chain_end_boundary_commitment",
        "shared_lookup_identity_commitment",
        "segment_list_commitment",
    ):
        update_len_prefixed(hasher, require_hash32(prototype, key).encode("utf-8"))
    for key in (
        "naive_per_step_package_count",
        "composed_segment_package_count",
        "package_count_delta",
    ):
        update_usize(hasher, require_non_negative_int(prototype, key))
    return hasher.hexdigest()


def verify_phase38_phase29_contract(contract: dict[str, Any]) -> None:
    require_exact_fields(contract, PHASE38_PHASE29_CONTRACT_REQUIRED_FIELDS, "Phase 38 Phase 29 contract")
    require_consts(contract, PHASE38_PHASE29_CONTRACT_CONSTS)
    for key in PHASE38_FALSE_FLAGS:
        if require_bool(contract, key):
            raise ReferenceVerifierError(f"phase29_contract.{key} must be false")
    for key in (
        "phase28_bounded_aggregation_arity",
        "phase28_member_count",
        "phase28_member_summaries",
        "phase28_nested_members",
        "total_phase26_members",
        "total_phase25_members",
        "max_nested_chain_arity",
        "max_nested_fold_arity",
        "total_matrices",
        "total_layouts",
        "total_rollups",
        "total_segments",
        "total_steps",
    ):
        require_positive_int(contract, key)
    for key in ("lookup_delta_entries", "max_lookup_frontier_entries"):
        require_non_negative_int(contract, key)
    for key in PHASE38_PHASE29_CONTRACT_HASH_FIELDS:
        require_hash32(contract, key)


def verify_phase38_phase30_manifest(manifest: dict[str, Any]) -> None:
    require_exact_fields(manifest, PHASE38_PHASE30_MANIFEST_REQUIRED_FIELDS, "Phase 38 Phase 30 manifest")
    require_consts(manifest, PHASE38_PHASE30_MANIFEST_CONSTS)
    for key in PHASE38_PHASE30_MANIFEST_HASH_FIELDS:
        require_hash32(manifest, key)
    total_steps = require_positive_int(manifest, "total_steps")

    layout = require_object(manifest, "layout")
    require_exact_fields(layout, PHASE38_PHASE30_LAYOUT_REQUIRED_FIELDS, "Phase 38 Phase 30 layout")
    if require_string(layout, "layout_version") != "stwo-decoding-layout-v1":
        raise ReferenceVerifierError("phase30_manifest.layout.layout_version is invalid")
    require_positive_int(layout, "rolling_kv_pairs")
    require_positive_int(layout, "pair_width")

    envelopes = require_list(manifest, "envelopes")
    if len(envelopes) != total_steps:
        raise ReferenceVerifierError("phase30_manifest.envelopes length must match total_steps")
    previous_output = None
    for expected_index, envelope_value in enumerate(envelopes):
        if not isinstance(envelope_value, dict):
            raise ReferenceVerifierError("phase30_manifest.envelopes entries must be objects")
        envelope = envelope_value
        require_exact_fields(envelope, PHASE38_PHASE30_ENVELOPE_REQUIRED_FIELDS, "Phase 38 Phase 30 envelope")
        require_consts(envelope, PHASE38_PHASE30_ENVELOPE_CONSTS)
        if require_hash32(envelope, "source_chain_commitment") != require_hash32(
            manifest, "source_chain_commitment"
        ):
            raise ReferenceVerifierError("phase30_manifest envelope source-chain drift")
        if require_non_negative_int(envelope, "step_index") != expected_index:
            raise ReferenceVerifierError("phase30_manifest envelope step_index is not contiguous")
        for key in PHASE38_PHASE30_ENVELOPE_HASH_FIELDS:
            require_hash32(envelope, key)
        if expected_index == 0 and require_hash32(envelope, "input_boundary_commitment") != require_hash32(
            manifest, "chain_start_boundary_commitment"
        ):
            raise ReferenceVerifierError("phase30_manifest first envelope does not match chain start")
        if previous_output is not None and require_hash32(envelope, "input_boundary_commitment") != previous_output:
            raise ReferenceVerifierError("phase30_manifest envelope boundary gap")
        previous_output = require_hash32(envelope, "output_boundary_commitment")
    if previous_output != require_hash32(manifest, "chain_end_boundary_commitment"):
        raise ReferenceVerifierError("phase30_manifest last envelope does not match chain end")


def verify_phase38_segment(segment: dict[str, Any], expected_index: int, expected_start: int) -> int:
    require_exact_fields(segment, PHASE38_SEGMENT_REQUIRED_FIELDS, "Phase 38 segment")
    if require_non_negative_int(segment, "segment_index") != expected_index:
        raise ReferenceVerifierError("segment_index does not match position")
    if require_non_negative_int(segment, "step_start") != expected_start:
        raise ReferenceVerifierError("segment step_start is not contiguous")
    total_steps = require_positive_int(segment, "total_steps")
    expected_end = expected_start + total_steps
    if require_positive_int(segment, "step_end") != expected_end:
        raise ReferenceVerifierError("segment step_end does not match step_start + total_steps")
    for key in PHASE38_SEGMENT_HASH_FIELDS:
        require_hash32(segment, key)

    contract = require_object(segment, "phase29_contract")
    manifest = require_object(segment, "phase30_manifest")
    receipt = require_object(segment, "phase37_receipt")
    verify_phase38_phase29_contract(contract)
    verify_phase38_phase30_manifest(manifest)
    verify_phase37_receipt(receipt)

    expected_receipt_commitment = commit_phase37_receipt(receipt)
    if require_hash32(segment, "phase37_receipt_commitment") != expected_receipt_commitment:
        raise ReferenceVerifierError("segment Phase 37 receipt commitment mismatch")
    expected_lookup_identity = commit_phase38_lookup_identity(manifest)
    if require_hash32(segment, "lookup_identity_commitment") != expected_lookup_identity:
        raise ReferenceVerifierError("segment lookup identity commitment mismatch")

    field_pairs = (
        ("phase30_source_chain_commitment", receipt["phase30_source_chain_commitment"]),
        ("phase30_step_envelopes_commitment", receipt["phase30_step_envelopes_commitment"]),
        ("chain_start_boundary_commitment", receipt["chain_start_boundary_commitment"]),
        ("chain_end_boundary_commitment", receipt["chain_end_boundary_commitment"]),
        ("source_template_commitment", receipt["source_template_commitment"]),
        ("aggregation_template_commitment", receipt["aggregation_template_commitment"]),
        (
            "phase34_shared_lookup_public_inputs_commitment",
            receipt["phase34_shared_lookup_public_inputs_commitment"],
        ),
        ("input_lookup_rows_commitments_commitment", receipt["input_lookup_rows_commitments_commitment"]),
        ("output_lookup_rows_commitments_commitment", receipt["output_lookup_rows_commitments_commitment"]),
        ("shared_lookup_artifact_commitments_commitment", receipt["shared_lookup_artifact_commitments_commitment"]),
        ("static_lookup_registry_commitments_commitment", receipt["static_lookup_registry_commitments_commitment"]),
    )
    for segment_key, receipt_value in field_pairs:
        if require_hash32(segment, segment_key) != receipt_value:
            raise ReferenceVerifierError(f"segment {segment_key} does not match embedded receipt")

    if contract["contract_version"] != receipt["phase29_contract_version"]:
        raise ReferenceVerifierError("phase29 contract version does not match receipt")
    if contract["semantic_scope"] != receipt["phase29_semantic_scope"]:
        raise ReferenceVerifierError("phase29 semantic scope does not match receipt")
    if contract["input_contract_commitment"] != receipt["phase29_input_contract_commitment"]:
        raise ReferenceVerifierError("phase29 input contract commitment does not match receipt")
    if manifest["manifest_version"] != receipt["phase30_manifest_version"]:
        raise ReferenceVerifierError("phase30 manifest version does not match receipt")
    if manifest["semantic_scope"] != receipt["phase30_semantic_scope"]:
        raise ReferenceVerifierError("phase30 semantic scope does not match receipt")
    if manifest["source_chain_commitment"] != receipt["phase30_source_chain_commitment"]:
        raise ReferenceVerifierError("phase30 source-chain commitment does not match receipt")
    if manifest["step_envelopes_commitment"] != receipt["phase30_step_envelopes_commitment"]:
        raise ReferenceVerifierError("phase30 step-envelopes commitment does not match receipt")
    if manifest["total_steps"] != receipt["total_steps"]:
        raise ReferenceVerifierError("phase30 total_steps does not match receipt")
    if manifest["chain_start_boundary_commitment"] != receipt["chain_start_boundary_commitment"]:
        raise ReferenceVerifierError("phase30 chain start does not match receipt")
    if manifest["chain_end_boundary_commitment"] != receipt["chain_end_boundary_commitment"]:
        raise ReferenceVerifierError("phase30 chain end does not match receipt")
    return expected_end


def verify_phase38_composition(prototype: dict[str, Any]) -> None:
    require_exact_fields(prototype, PHASE38_REQUIRED_FIELDS, "Phase 38 composition")
    require_consts(prototype, PHASE38_CONSTS)
    for key in PHASE38_FALSE_FLAGS:
        if require_bool(prototype, key):
            raise ReferenceVerifierError(f"{key} must be false")
    for key in PHASE38_HASH_FIELDS:
        require_hash32(prototype, key)

    segments = require_list(prototype, "segments")
    segment_count = require_positive_int(prototype, "segment_count")
    if segment_count != len(segments) or segment_count < 2:
        raise ReferenceVerifierError("segment_count must match at least two segments")
    total_steps = require_positive_int(prototype, "total_steps")
    if require_positive_int(prototype, "naive_per_step_package_count") != total_steps:
        raise ReferenceVerifierError("naive_per_step_package_count must equal total_steps")
    if require_positive_int(prototype, "composed_segment_package_count") != segment_count:
        raise ReferenceVerifierError("composed_segment_package_count must equal segment_count")
    if require_non_negative_int(prototype, "package_count_delta") != total_steps - segment_count:
        raise ReferenceVerifierError("package_count_delta mismatch")

    cursor = 0
    first_segment: dict[str, Any] | None = None
    previous_end_boundary = None
    for index, segment_value in enumerate(segments):
        if not isinstance(segment_value, dict):
            raise ReferenceVerifierError("segments entries must be objects")
        segment = segment_value
        cursor = verify_phase38_segment(segment, index, cursor)
        if first_segment is None:
            first_segment = segment
        if previous_end_boundary is not None and segment["chain_start_boundary_commitment"] != previous_end_boundary:
            raise ReferenceVerifierError("boundary gap between Phase 38 segments")
        previous_end_boundary = segment["chain_end_boundary_commitment"]
        if index > 0:
            assert first_segment is not None
            if segment["lookup_identity_commitment"] != first_segment["lookup_identity_commitment"]:
                raise ReferenceVerifierError("shared lookup identity drift")
            if segment["phase30_source_chain_commitment"] != first_segment["phase30_source_chain_commitment"]:
                raise ReferenceVerifierError("source-chain identity drift")
            if segment["source_template_commitment"] != first_segment["source_template_commitment"]:
                raise ReferenceVerifierError("source template drift")
            if segment["aggregation_template_commitment"] != first_segment["aggregation_template_commitment"]:
                raise ReferenceVerifierError("aggregation template drift")

    assert first_segment is not None
    if cursor != total_steps:
        raise ReferenceVerifierError("total_steps does not match segment sum")
    if prototype["chain_start_boundary_commitment"] != first_segment["chain_start_boundary_commitment"]:
        raise ReferenceVerifierError("prototype start boundary does not match first segment")
    if prototype["chain_end_boundary_commitment"] != segments[-1]["chain_end_boundary_commitment"]:
        raise ReferenceVerifierError("prototype end boundary does not match last segment")
    if prototype["shared_lookup_identity_commitment"] != commit_phase38_shared_lookup_identity(first_segment):
        raise ReferenceVerifierError("shared_lookup_identity_commitment mismatch")
    if prototype["segment_list_commitment"] != commit_phase38_segment_list(segments):
        raise ReferenceVerifierError("segment_list_commitment mismatch")
    if prototype["composition_commitment"] != commit_phase38_composition_prototype(prototype):
        raise ReferenceVerifierError("composition_commitment mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify-phase37", help="verify a Phase 37 receipt JSON")
    verify.add_argument("path", type=Path)
    verify_phase38 = subparsers.add_parser(
        "verify-phase38",
        help="verify a Phase 38 Paper 3 composition prototype JSON",
    )
    verify_phase38.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "verify-phase37":
            verify_phase37_receipt(load_json_object(args.path))
        elif args.command == "verify-phase38":
            verify_phase38_composition(load_json_object(args.path))
        else:  # pragma: no cover - argparse prevents this.
            raise AssertionError(args.command)
    except ReferenceVerifierError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"reference verifier: {args.command} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
