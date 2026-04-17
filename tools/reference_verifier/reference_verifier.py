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


def verify_phase37_receipt(receipt: dict[str, Any]) -> None:
    keys = set(receipt)
    required = set(PHASE37_REQUIRED_FIELDS)
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing:
        raise ReferenceVerifierError(f"missing Phase 37 fields: {missing}")
    if extra:
        raise ReferenceVerifierError(f"unknown Phase 37 fields: {extra}")

    for key, expected in PHASE37_CONSTS.items():
        actual = require_string(receipt, key)
        if actual != expected:
            raise ReferenceVerifierError(f"{key} expected {expected!r}, got {actual!r}")

    for key in PHASE37_FALSE_FLAGS:
        if require_bool(receipt, key):
            raise ReferenceVerifierError(f"{key} must be false")
    for key in PHASE37_TRUE_FLAGS:
        if not require_bool(receipt, key):
            raise ReferenceVerifierError(f"{key} must be true")

    require_positive_int(receipt, "total_steps")
    for key in PHASE37_HASH_FIELDS:
        value = require_string(receipt, key)
        if not HASH32_RE.fullmatch(value):
            raise ReferenceVerifierError(f"{key} must be lowercase 64-character hex")

    expected = commit_phase37_receipt(receipt)
    actual = require_string(receipt, "recursive_artifact_chain_harness_receipt_commitment")
    if actual != expected:
        raise ReferenceVerifierError(
            "recursive_artifact_chain_harness_receipt_commitment mismatch: "
            f"got {actual}, recomputed {expected}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify-phase37", help="verify a Phase 37 receipt JSON")
    verify.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "verify-phase37":
            verify_phase37_receipt(load_json_object(args.path))
        else:  # pragma: no cover - argparse prevents this.
            raise AssertionError(args.command)
    except ReferenceVerifierError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"reference verifier: {args.command} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
