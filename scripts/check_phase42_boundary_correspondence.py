#!/usr/bin/env python3
"""Phase42 boundary-correspondence decision gate.

Control issue: https://github.com/omarespejel/provable-transformer-vm/issues/180

This checker intentionally treats source-bound Phase41 compatibility as a
blocked decision, not as breakthrough success. A clean Phase42 relation needs
the Phase12 public-state preimage and Phase14/23 boundary-state preimage, or a
public transform between them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ISSUE = 180
PHASE = "phase42-boundary-correspondence-decision-gate"
ISSUE_URL = "https://github.com/omarespejel/provable-transformer-vm/issues/180"

STWO_BACKEND_VERSION_PHASE12 = "stwo-phase12-decoding-family-v9"
CLAIM_STATEMENT_VERSION_V1 = "statement-v1"
STWO_DECODING_CHAIN_VERSION_PHASE12 = "stwo-phase12-decoding-chain-v9"
STWO_DECODING_CHAIN_SCOPE_PHASE12 = "stwo_execution_parameterized_proof_carrying_decoding_chain"
STWO_DECODING_LAYOUT_VERSION_PHASE12 = "stwo-decoding-layout-v1"
STWO_DECODING_STATE_VERSION_PHASE12 = "stwo-decoding-state-v11"
STWO_DECODING_STATE_VERSION_PHASE14 = "stwo-decoding-state-v6"
STWO_DECODING_STEP_ENVELOPE_VERSION_PHASE30 = "stwo-phase30-decoding-step-proof-envelope-v1"
STWO_DECODING_STEP_ENVELOPE_SCOPE_PHASE30 = "stwo_execution_parameterized_decoding_step_proof_envelope"
STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30 = (
    "stwo-phase30-decoding-step-proof-envelope-manifest-v1"
)
STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30 = (
    "stwo_execution_parameterized_decoding_step_proof_envelope_manifest"
)
STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 = "decoding_step_v2"
STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29 = (
    "stwo-phase29-recursive-compression-input-contract-v1"
)
STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29 = "stwo_phase29_recursive_compression_input_contract"
STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE = "pre-recursive-proof-carrying-aggregation"
STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41 = "stwo-phase41-boundary-translation-witness-v1"
STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41 = (
    "stwo_execution_parameterized_boundary_translation_witness"
)
STWO_BOUNDARY_TRANSLATION_RULE_PHASE41 = "explicit-phase29-phase30-boundary-pair-v1"
STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23 = (
    "stwo-phase23-decoding-cross-step-lookup-accumulator-v1"
)
PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_VERSION = "phase42-boundary-preimage-evidence-v1"
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_USIZE = (1 << 64) - 1

PHASE12_OUTPUT_WIDTH = 3
PHASE12_SHARED_LOOKUP_ROWS = 8
MAX_DECODING_CHAIN_STEPS = 1_024
HASH32_RE = re.compile(r"^[0-9a-f]{64}$")

PHASE29_FIELDS = (
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

PHASE30_MANIFEST_FIELDS = (
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

PHASE30_ENVELOPE_FIELDS = (
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

PHASE41_FIELDS = (
    "proof_backend",
    "witness_version",
    "semantic_scope",
    "proof_backend_version",
    "statement_version",
    "step_relation",
    "required_recursion_posture",
    "recursive_verification_claimed",
    "cryptographic_compression_claimed",
    "derivation_proof_claimed",
    "translation_rule",
    "phase29_contract_version",
    "phase29_semantic_scope",
    "phase29_contract_commitment",
    "phase30_manifest_version",
    "phase30_semantic_scope",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "total_steps",
    "phase29_global_start_state_commitment",
    "phase29_global_end_state_commitment",
    "phase30_chain_start_boundary_commitment",
    "phase30_chain_end_boundary_commitment",
    "source_template_commitment",
    "aggregation_template_commitment",
    "boundary_domains_differ",
    "start_boundary_translation_commitment",
    "end_boundary_translation_commitment",
    "boundary_translation_witness_commitment",
)

PHASE12_STATE_FIELDS = (
    "state_version",
    "step_index",
    "position",
    "layout_commitment",
    "persistent_state_commitment",
    "kv_history_commitment",
    "kv_history_length",
    "kv_cache_commitment",
    "incoming_token_commitment",
    "query_commitment",
    "output_commitment",
    "lookup_rows_commitment",
    "public_state_commitment",
)

PHASE14_STATE_FIELDS = (
    "state_version",
    "step_index",
    "position",
    "layout_commitment",
    "persistent_state_commitment",
    "kv_history_commitment",
    "kv_history_length",
    "kv_history_chunk_size",
    "kv_history_sealed_commitment",
    "kv_history_sealed_chunks",
    "kv_history_open_chunk_commitment",
    "kv_history_open_chunk_pairs",
    "kv_history_frontier_commitment",
    "kv_history_frontier_pairs",
    "lookup_transcript_commitment",
    "lookup_transcript_entries",
    "lookup_frontier_commitment",
    "lookup_frontier_entries",
    "kv_cache_commitment",
    "incoming_token_commitment",
    "query_commitment",
    "output_commitment",
    "lookup_rows_commitment",
    "public_state_commitment",
)

PHASE42_EVIDENCE_FIELDS = (
    "issue",
    "evidence_version",
    "relation_outcome",
    "phase12_start_state",
    "phase12_end_state",
    "phase14_start_state",
    "phase14_end_state",
)

SHARED_STATE_FIELDS = (
    "step_index",
    "position",
    "layout_commitment",
    "persistent_state_commitment",
    "kv_history_commitment",
    "kv_history_length",
    "kv_cache_commitment",
    "incoming_token_commitment",
    "query_commitment",
    "output_commitment",
    "lookup_rows_commitment",
)


class Phase42Error(Exception):
    """Raised when a supplied artifact fails the Phase42 source checks."""


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        if size > MAX_JSON_BYTES:
            raise Phase42Error(f"{path}: JSON artifact exceeds {MAX_JSON_BYTES} bytes")
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Phase42Error(f"{path}: unable to read JSON artifact: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Phase42Error(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Phase42Error(f"{path}: expected a JSON object")
    return data


def blake2b32() -> Any:
    return hashlib.blake2b(digest_size=32)


def lower_hex(digest: bytes) -> str:
    return digest.hex()


def require_fields(obj: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in obj]
    if missing:
        raise Phase42Error(f"{label}: missing required fields: {', '.join(missing)}")
    unknown = sorted(set(obj) - set(fields))
    if unknown:
        raise Phase42Error(f"{label}: unknown fields are not allowed: {', '.join(unknown)}")


def require_hash32(label: str, value: Any) -> None:
    if not isinstance(value, str) or not HASH32_RE.fullmatch(value):
        raise Phase42Error(f"{label}: expected a 32-byte lowercase hex commitment")


def require_bool(label: str, value: Any) -> None:
    if not isinstance(value, bool):
        raise Phase42Error(f"{label}: expected a boolean")


def require_usize(label: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise Phase42Error(f"{label}: expected a non-negative integer")
    if value > MAX_USIZE:
        raise Phase42Error(f"{label}: expected an unsigned 64-bit integer")
    return value


def require_i16(label: str, value: Any) -> int:
    if type(value) is not int or value < -32768 or value > 32767:
        raise Phase42Error(f"{label}: expected an i16 integer")
    return value


def update_i16(hasher: Any, value: int) -> None:
    hasher.update(require_i16("i16 hash input", value).to_bytes(2, "little", signed=True))


def update_len_prefixed(hasher: Any, value: str | bytes) -> None:
    raw = value if isinstance(value, bytes) else value.encode()
    hasher.update(len(raw).to_bytes(16, "little"))
    hasher.update(raw)


def update_bool(hasher: Any, value: bool) -> None:
    hasher.update(bytes([1 if value else 0]))


def update_usize(hasher: Any, value: int) -> None:
    hasher.update(value.to_bytes(16, "little"))


def phase30_hash_part(hasher: Any, value: str | bytes) -> None:
    raw = value if isinstance(value, bytes) else value.encode()
    hasher.update(len(raw).to_bytes(8, "little"))
    hasher.update(raw)


def commit_phase12_layout(layout: dict[str, Any]) -> str:
    if not isinstance(layout, dict):
        raise Phase42Error("Phase30 layout: layout must be an object")
    if set(layout) != {"layout_version", "rolling_kv_pairs", "pair_width"}:
        raise Phase42Error("Phase30 layout: unexpected fields")
    if layout["layout_version"] != STWO_DECODING_LAYOUT_VERSION_PHASE12:
        raise Phase42Error("Phase30 layout: unsupported layout_version")
    rolling_kv_pairs = require_usize("Phase30 layout rolling_kv_pairs", layout["rolling_kv_pairs"])
    pair_width = require_usize("Phase30 layout pair_width", layout["pair_width"])
    if rolling_kv_pairs == 0 or pair_width == 0:
        raise Phase42Error("Phase30 layout: rolling_kv_pairs and pair_width must be non-zero")
    memory_size = rolling_kv_pairs * pair_width + (2 * pair_width) + PHASE12_OUTPUT_WIDTH
    memory_size += PHASE12_SHARED_LOOKUP_ROWS + 2
    if memory_size > 256:
        raise Phase42Error(f"Phase30 layout: memory size {memory_size} exceeds encoded limit 256")
    hasher = blake2b32()
    hasher.update(STWO_DECODING_LAYOUT_VERSION_PHASE12.encode())
    hasher.update(rolling_kv_pairs.to_bytes(8, "little"))
    hasher.update(pair_width.to_bytes(8, "little"))
    return lower_hex(hasher.digest())


def commit_phase29_contract(contract: dict[str, Any]) -> str:
    hasher = blake2b32()
    update_len_prefixed(hasher, b"phase29-contract")
    for field in (
        "proof_backend",
        "contract_version",
        "semantic_scope",
        "phase28_artifact_version",
        "phase28_semantic_scope",
        "phase28_proof_backend_version",
        "statement_version",
        "required_recursion_posture",
    ):
        update_len_prefixed(hasher, str(contract[field]))
    update_bool(hasher, contract["recursive_verification_claimed"])
    update_bool(hasher, contract["cryptographic_compression_claimed"])
    for field in (
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
    ):
        update_usize(hasher, require_usize(f"Phase29 {field}", contract[field]))
    for field in (
        "source_template_commitment",
        "global_start_state_commitment",
        "global_end_state_commitment",
        "aggregation_template_commitment",
        "aggregated_chained_folded_interval_accumulator_commitment",
    ):
        update_len_prefixed(hasher, contract[field])
    return lower_hex(hasher.digest())


def verify_phase12_state(state: dict[str, Any], label: str) -> None:
    require_fields(state, PHASE12_STATE_FIELDS, label)
    if state["state_version"] != STWO_DECODING_STATE_VERSION_PHASE12:
        raise Phase42Error(f"{label}: unsupported state_version")
    require_usize(f"{label} step_index", state["step_index"])
    require_i16(f"{label} position", state["position"])
    require_usize(f"{label} kv_history_length", state["kv_history_length"])
    for field in (
        "layout_commitment",
        "persistent_state_commitment",
        "kv_history_commitment",
        "kv_cache_commitment",
        "incoming_token_commitment",
        "query_commitment",
        "output_commitment",
        "lookup_rows_commitment",
        "public_state_commitment",
    ):
        require_hash32(f"{label} {field}", state[field])
    expected = commit_phase12_public_state(state)
    if state["public_state_commitment"] != expected:
        raise Phase42Error(f"{label}: public_state_commitment mismatch")


def verify_phase14_state(state: dict[str, Any], label: str) -> None:
    require_fields(state, PHASE14_STATE_FIELDS, label)
    if state["state_version"] != STWO_DECODING_STATE_VERSION_PHASE14:
        raise Phase42Error(f"{label}: unsupported state_version")
    require_usize(f"{label} step_index", state["step_index"])
    require_i16(f"{label} position", state["position"])
    for field in (
        "kv_history_length",
        "kv_history_chunk_size",
        "kv_history_sealed_chunks",
        "kv_history_open_chunk_pairs",
        "kv_history_frontier_pairs",
        "lookup_transcript_entries",
        "lookup_frontier_entries",
    ):
        require_usize(f"{label} {field}", state[field])
    for field in (
        "layout_commitment",
        "persistent_state_commitment",
        "kv_history_commitment",
        "kv_history_sealed_commitment",
        "kv_history_open_chunk_commitment",
        "kv_history_frontier_commitment",
        "lookup_transcript_commitment",
        "lookup_frontier_commitment",
        "kv_cache_commitment",
        "incoming_token_commitment",
        "query_commitment",
        "output_commitment",
        "lookup_rows_commitment",
        "public_state_commitment",
    ):
        require_hash32(f"{label} {field}", state[field])
    expected = commit_phase14_public_state(state)
    if state["public_state_commitment"] != expected:
        raise Phase42Error(f"{label}: public_state_commitment mismatch")


def commit_phase12_public_state(state: dict[str, Any]) -> str:
    hasher = blake2b32()
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE12.encode())
    hasher.update(b"public-state")
    hasher.update(state["state_version"].encode())
    hasher.update(require_usize("Phase12 step_index", state["step_index"]).to_bytes(8, "little"))
    update_i16(hasher, state["position"])
    hasher.update(state["layout_commitment"].encode())
    hasher.update(state["persistent_state_commitment"].encode())
    hasher.update(state["kv_history_commitment"].encode())
    hasher.update(require_usize("Phase12 kv_history_length", state["kv_history_length"]).to_bytes(8, "little"))
    hasher.update(state["kv_cache_commitment"].encode())
    return lower_hex(hasher.digest())


def commit_phase14_public_state(state: dict[str, Any]) -> str:
    hasher = blake2b32()
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.encode())
    hasher.update(b"public-state")
    hasher.update(state["state_version"].encode())
    hasher.update(require_usize("Phase14 step_index", state["step_index"]).to_bytes(8, "little"))
    update_i16(hasher, state["position"])
    hasher.update(state["layout_commitment"].encode())
    hasher.update(state["persistent_state_commitment"].encode())
    hasher.update(state["kv_history_commitment"].encode())
    hasher.update(require_usize("Phase14 kv_history_length", state["kv_history_length"]).to_bytes(8, "little"))
    hasher.update(require_usize("Phase14 kv_history_chunk_size", state["kv_history_chunk_size"]).to_bytes(8, "little"))
    hasher.update(state["kv_history_sealed_commitment"].encode())
    hasher.update(require_usize("Phase14 kv_history_sealed_chunks", state["kv_history_sealed_chunks"]).to_bytes(8, "little"))
    hasher.update(state["kv_history_open_chunk_commitment"].encode())
    hasher.update(require_usize("Phase14 kv_history_open_chunk_pairs", state["kv_history_open_chunk_pairs"]).to_bytes(8, "little"))
    hasher.update(state["kv_history_frontier_commitment"].encode())
    hasher.update(require_usize("Phase14 kv_history_frontier_pairs", state["kv_history_frontier_pairs"]).to_bytes(8, "little"))
    hasher.update(state["lookup_transcript_commitment"].encode())
    hasher.update(require_usize("Phase14 lookup_transcript_entries", state["lookup_transcript_entries"]).to_bytes(8, "little"))
    hasher.update(state["lookup_frontier_commitment"].encode())
    hasher.update(require_usize("Phase14 lookup_frontier_entries", state["lookup_frontier_entries"]).to_bytes(8, "little"))
    hasher.update(state["kv_cache_commitment"].encode())
    return lower_hex(hasher.digest())


def commit_phase23_boundary_state(state: dict[str, Any]) -> str:
    hasher = blake2b32()
    hasher.update(STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23.encode())
    hasher.update(b"boundary-state")
    update_i16(hasher, state["position"])
    hasher.update(state["layout_commitment"].encode())
    hasher.update(state["persistent_state_commitment"].encode())
    hasher.update(state["kv_history_commitment"].encode())
    hasher.update(require_usize("Phase23 kv_history_length", state["kv_history_length"]).to_bytes(8, "little"))
    hasher.update(require_usize("Phase23 kv_history_chunk_size", state["kv_history_chunk_size"]).to_bytes(8, "little"))
    hasher.update(state["kv_history_sealed_commitment"].encode())
    hasher.update(require_usize("Phase23 kv_history_sealed_chunks", state["kv_history_sealed_chunks"]).to_bytes(8, "little"))
    hasher.update(state["kv_history_open_chunk_commitment"].encode())
    hasher.update(require_usize("Phase23 kv_history_open_chunk_pairs", state["kv_history_open_chunk_pairs"]).to_bytes(8, "little"))
    hasher.update(state["kv_history_frontier_commitment"].encode())
    hasher.update(require_usize("Phase23 kv_history_frontier_pairs", state["kv_history_frontier_pairs"]).to_bytes(8, "little"))
    hasher.update(state["lookup_transcript_commitment"].encode())
    hasher.update(require_usize("Phase23 lookup_transcript_entries", state["lookup_transcript_entries"]).to_bytes(8, "little"))
    hasher.update(state["lookup_frontier_commitment"].encode())
    hasher.update(require_usize("Phase23 lookup_frontier_entries", state["lookup_frontier_entries"]).to_bytes(8, "little"))
    hasher.update(state["kv_cache_commitment"].encode())
    return lower_hex(hasher.digest())


def verify_phase29_contract(contract: dict[str, Any]) -> None:
    require_fields(contract, PHASE29_FIELDS, "Phase29 contract")
    if contract["proof_backend"] != "stwo":
        raise Phase42Error("Phase29 contract: proof_backend must be stwo")
    if contract["contract_version"] != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29:
        raise Phase42Error("Phase29 contract: unsupported contract_version")
    if contract["semantic_scope"] != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29:
        raise Phase42Error("Phase29 contract: unsupported semantic_scope")
    if contract["phase28_proof_backend_version"] != STWO_BACKEND_VERSION_PHASE12:
        raise Phase42Error("Phase29 contract: unexpected phase28_proof_backend_version")
    if contract["statement_version"] != CLAIM_STATEMENT_VERSION_V1:
        raise Phase42Error("Phase29 contract: unexpected statement_version")
    if contract["required_recursion_posture"] != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE:
        raise Phase42Error("Phase29 contract: unexpected required_recursion_posture")
    require_bool("Phase29 recursive_verification_claimed", contract["recursive_verification_claimed"])
    require_bool(
        "Phase29 cryptographic_compression_claimed",
        contract["cryptographic_compression_claimed"],
    )
    if contract["recursive_verification_claimed"] or contract["cryptographic_compression_claimed"]:
        raise Phase42Error("Phase29 contract: recursive/compression claims must be false")
    for field in (
        "source_template_commitment",
        "global_start_state_commitment",
        "global_end_state_commitment",
        "aggregation_template_commitment",
        "aggregated_chained_folded_interval_accumulator_commitment",
        "input_contract_commitment",
    ):
        require_hash32(f"Phase29 {field}", contract[field])
    expected = commit_phase29_contract(contract)
    if contract["input_contract_commitment"] != expected:
        raise Phase42Error(
            "Phase29 contract: input_contract_commitment does not match recomputed commitment"
        )


def commit_phase30_step_envelope(envelope: dict[str, Any]) -> str:
    hasher = blake2b32()
    hasher.update(STWO_DECODING_STEP_ENVELOPE_VERSION_PHASE30.encode())
    hasher.update(b"step-envelope")
    for field in (
        "envelope_version",
        "semantic_scope",
        "proof_backend",
        "proof_backend_version",
        "statement_version",
        "relation",
        "layout_commitment",
        "source_chain_commitment",
    ):
        phase30_hash_part(hasher, str(envelope[field]))
    hasher.update(require_usize("Phase30 envelope step_index", envelope["step_index"]).to_bytes(8, "little"))
    for field in (
        "input_boundary_commitment",
        "output_boundary_commitment",
        "input_lookup_rows_commitment",
        "output_lookup_rows_commitment",
        "shared_lookup_artifact_commitment",
        "static_lookup_registry_commitment",
        "proof_commitment",
    ):
        phase30_hash_part(hasher, str(envelope[field]))
    return lower_hex(hasher.digest())


def commit_phase30_step_envelope_list(envelopes: list[dict[str, Any]]) -> str:
    hasher = blake2b32()
    hasher.update(STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30.encode())
    hasher.update(b"step-envelope-list")
    hasher.update(len(envelopes).to_bytes(8, "little"))
    for envelope in envelopes:
        hasher.update(envelope["envelope_commitment"].encode())
    return lower_hex(hasher.digest())


def verify_phase30_manifest(manifest: dict[str, Any]) -> None:
    require_fields(manifest, PHASE30_MANIFEST_FIELDS, "Phase30 manifest")
    if manifest["proof_backend"] != "stwo":
        raise Phase42Error("Phase30 manifest: proof_backend must be stwo")
    if manifest["manifest_version"] != STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30:
        raise Phase42Error("Phase30 manifest: unsupported manifest_version")
    if manifest["semantic_scope"] != STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30:
        raise Phase42Error("Phase30 manifest: unsupported semantic_scope")
    if manifest["proof_backend_version"] != STWO_BACKEND_VERSION_PHASE12:
        raise Phase42Error("Phase30 manifest: unexpected proof_backend_version")
    if manifest["statement_version"] != CLAIM_STATEMENT_VERSION_V1:
        raise Phase42Error("Phase30 manifest: unexpected statement_version")
    if manifest["source_chain_version"] != STWO_DECODING_CHAIN_VERSION_PHASE12:
        raise Phase42Error("Phase30 manifest: source_chain_version must be Phase12")
    if manifest["source_chain_semantic_scope"] != STWO_DECODING_CHAIN_SCOPE_PHASE12:
        raise Phase42Error("Phase30 manifest: source_chain_semantic_scope must be Phase12")
    require_hash32("Phase30 source_chain_commitment", manifest["source_chain_commitment"])
    require_hash32("Phase30 chain_start_boundary_commitment", manifest["chain_start_boundary_commitment"])
    require_hash32("Phase30 chain_end_boundary_commitment", manifest["chain_end_boundary_commitment"])
    require_hash32("Phase30 step_envelopes_commitment", manifest["step_envelopes_commitment"])

    layout_commitment = commit_phase12_layout(manifest["layout"])
    envelopes = manifest["envelopes"]
    if not isinstance(envelopes, list):
        raise Phase42Error("Phase30 manifest: envelopes must be an array")
    total_steps = require_usize("Phase30 total_steps", manifest["total_steps"])
    if not envelopes:
        raise Phase42Error("Phase30 manifest: must contain at least one envelope")
    if len(envelopes) > MAX_DECODING_CHAIN_STEPS:
        raise Phase42Error("Phase30 manifest: too many envelopes")
    if total_steps != len(envelopes):
        raise Phase42Error("Phase30 manifest: total_steps does not match envelopes length")

    for index, envelope in enumerate(envelopes):
        if not isinstance(envelope, dict):
            raise Phase42Error(f"Phase30 envelope {index}: expected object")
        require_fields(envelope, PHASE30_ENVELOPE_FIELDS, f"Phase30 envelope {index}")
        if envelope["envelope_version"] != STWO_DECODING_STEP_ENVELOPE_VERSION_PHASE30:
            raise Phase42Error(f"Phase30 envelope {index}: unsupported envelope_version")
        if envelope["semantic_scope"] != STWO_DECODING_STEP_ENVELOPE_SCOPE_PHASE30:
            raise Phase42Error(f"Phase30 envelope {index}: unsupported semantic_scope")
        if envelope["proof_backend"] != "stwo":
            raise Phase42Error(f"Phase30 envelope {index}: proof_backend must be stwo")
        if envelope["proof_backend_version"] != manifest["proof_backend_version"]:
            raise Phase42Error(f"Phase30 envelope {index}: backend version mismatch")
        if envelope["statement_version"] != manifest["statement_version"]:
            raise Phase42Error(f"Phase30 envelope {index}: statement version mismatch")
        if envelope["relation"] != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30:
            raise Phase42Error(f"Phase30 envelope {index}: unsupported relation")
        if envelope["layout_commitment"] != layout_commitment:
            raise Phase42Error(f"Phase30 envelope {index}: layout commitment mismatch")
        if envelope["source_chain_commitment"] != manifest["source_chain_commitment"]:
            raise Phase42Error(f"Phase30 envelope {index}: source_chain_commitment mismatch")
        if envelope["step_index"] != index:
            raise Phase42Error(f"Phase30 envelope {index}: step_index mismatch")
        for field in (
            "input_boundary_commitment",
            "output_boundary_commitment",
            "input_lookup_rows_commitment",
            "output_lookup_rows_commitment",
            "shared_lookup_artifact_commitment",
            "static_lookup_registry_commitment",
            "proof_commitment",
            "envelope_commitment",
        ):
            require_hash32(f"Phase30 envelope {index} {field}", envelope[field])
        expected_envelope = commit_phase30_step_envelope(envelope)
        if envelope["envelope_commitment"] != expected_envelope:
            raise Phase42Error(f"Phase30 envelope {index}: envelope_commitment mismatch")
        if index > 0:
            previous = envelopes[index - 1]
            if previous["output_boundary_commitment"] != envelope["input_boundary_commitment"]:
                raise Phase42Error(f"Phase30 envelope link {index - 1}->{index}: boundary mismatch")

    if manifest["chain_start_boundary_commitment"] != envelopes[0]["input_boundary_commitment"]:
        raise Phase42Error("Phase30 manifest: start boundary does not match first envelope")
    if manifest["chain_end_boundary_commitment"] != envelopes[-1]["output_boundary_commitment"]:
        raise Phase42Error("Phase30 manifest: end boundary does not match final envelope")
    expected_list = commit_phase30_step_envelope_list(envelopes)
    if manifest["step_envelopes_commitment"] != expected_list:
        raise Phase42Error("Phase30 manifest: step_envelopes_commitment mismatch")


def commit_phase41_boundary_translation_pair(
    boundary_label: str,
    phase29_boundary_commitment: str,
    phase30_boundary_commitment: str,
    witness: dict[str, Any],
) -> str:
    hasher = blake2b32()
    update_len_prefixed(hasher, b"phase41-boundary-translation-pair")
    update_len_prefixed(hasher, boundary_label)
    update_len_prefixed(hasher, witness["translation_rule"])
    update_len_prefixed(hasher, witness["phase29_contract_commitment"])
    update_len_prefixed(hasher, witness["phase30_source_chain_commitment"])
    update_len_prefixed(hasher, witness["phase30_step_envelopes_commitment"])
    update_usize(hasher, require_usize("Phase41 total_steps", witness["total_steps"]))
    update_len_prefixed(hasher, phase29_boundary_commitment)
    update_len_prefixed(hasher, phase30_boundary_commitment)
    return lower_hex(hasher.digest())


def commit_phase41_boundary_translation_witness(witness: dict[str, Any]) -> str:
    hasher = blake2b32()
    update_len_prefixed(hasher, b"phase41-boundary-translation-witness")
    for field in (
        "proof_backend",
        "witness_version",
        "semantic_scope",
        "proof_backend_version",
        "statement_version",
        "step_relation",
        "required_recursion_posture",
    ):
        update_len_prefixed(hasher, str(witness[field]))
    update_bool(hasher, witness["recursive_verification_claimed"])
    update_bool(hasher, witness["cryptographic_compression_claimed"])
    update_bool(hasher, witness["derivation_proof_claimed"])
    for field in (
        "translation_rule",
        "phase29_contract_version",
        "phase29_semantic_scope",
        "phase29_contract_commitment",
        "phase30_manifest_version",
        "phase30_semantic_scope",
        "phase30_source_chain_commitment",
        "phase30_step_envelopes_commitment",
    ):
        update_len_prefixed(hasher, str(witness[field]))
    update_usize(hasher, require_usize("Phase41 total_steps", witness["total_steps"]))
    for field in (
        "phase29_global_start_state_commitment",
        "phase29_global_end_state_commitment",
        "phase30_chain_start_boundary_commitment",
        "phase30_chain_end_boundary_commitment",
        "source_template_commitment",
        "aggregation_template_commitment",
    ):
        update_len_prefixed(hasher, str(witness[field]))
    update_bool(hasher, witness["boundary_domains_differ"])
    update_len_prefixed(hasher, witness["start_boundary_translation_commitment"])
    update_len_prefixed(hasher, witness["end_boundary_translation_commitment"])
    return lower_hex(hasher.digest())


def prepare_phase41_expected(
    phase29: dict[str, Any], phase30: dict[str, Any]
) -> dict[str, Any]:
    witness = {
        "proof_backend": "stwo",
        "witness_version": STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41,
        "semantic_scope": STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41,
        "proof_backend_version": phase29["phase28_proof_backend_version"],
        "statement_version": phase29["statement_version"],
        "step_relation": STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30,
        "required_recursion_posture": phase29["required_recursion_posture"],
        "recursive_verification_claimed": False,
        "cryptographic_compression_claimed": False,
        "derivation_proof_claimed": False,
        "translation_rule": STWO_BOUNDARY_TRANSLATION_RULE_PHASE41,
        "phase29_contract_version": phase29["contract_version"],
        "phase29_semantic_scope": phase29["semantic_scope"],
        "phase29_contract_commitment": phase29["input_contract_commitment"],
        "phase30_manifest_version": phase30["manifest_version"],
        "phase30_semantic_scope": phase30["semantic_scope"],
        "phase30_source_chain_commitment": phase30["source_chain_commitment"],
        "phase30_step_envelopes_commitment": phase30["step_envelopes_commitment"],
        "total_steps": phase30["total_steps"],
        "phase29_global_start_state_commitment": phase29["global_start_state_commitment"],
        "phase29_global_end_state_commitment": phase29["global_end_state_commitment"],
        "phase30_chain_start_boundary_commitment": phase30["chain_start_boundary_commitment"],
        "phase30_chain_end_boundary_commitment": phase30["chain_end_boundary_commitment"],
        "source_template_commitment": phase29["source_template_commitment"],
        "aggregation_template_commitment": phase29["aggregation_template_commitment"],
        "boundary_domains_differ": True,
        "start_boundary_translation_commitment": "",
        "end_boundary_translation_commitment": "",
        "boundary_translation_witness_commitment": "",
    }
    witness["start_boundary_translation_commitment"] = commit_phase41_boundary_translation_pair(
        "start",
        witness["phase29_global_start_state_commitment"],
        witness["phase30_chain_start_boundary_commitment"],
        witness,
    )
    witness["end_boundary_translation_commitment"] = commit_phase41_boundary_translation_pair(
        "end",
        witness["phase29_global_end_state_commitment"],
        witness["phase30_chain_end_boundary_commitment"],
        witness,
    )
    witness["boundary_translation_witness_commitment"] = commit_phase41_boundary_translation_witness(
        witness
    )
    return witness


def verify_phase41_witness(witness: dict[str, Any]) -> None:
    require_fields(witness, PHASE41_FIELDS, "Phase41 witness")
    if witness["proof_backend"] != "stwo":
        raise Phase42Error("Phase41 witness: proof_backend must be stwo")
    if witness["witness_version"] != STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41:
        raise Phase42Error("Phase41 witness: unsupported witness_version")
    if witness["semantic_scope"] != STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41:
        raise Phase42Error("Phase41 witness: unsupported semantic_scope")
    if witness["proof_backend_version"] != STWO_BACKEND_VERSION_PHASE12:
        raise Phase42Error("Phase41 witness: unexpected proof_backend_version")
    if witness["statement_version"] != CLAIM_STATEMENT_VERSION_V1:
        raise Phase42Error("Phase41 witness: unexpected statement_version")
    if witness["step_relation"] != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30:
        raise Phase42Error("Phase41 witness: unexpected step_relation")
    if witness["required_recursion_posture"] != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE:
        raise Phase42Error("Phase41 witness: unexpected recursion posture")
    if witness["translation_rule"] != STWO_BOUNDARY_TRANSLATION_RULE_PHASE41:
        raise Phase42Error("Phase41 witness: unexpected translation_rule")
    for field in (
        "recursive_verification_claimed",
        "cryptographic_compression_claimed",
        "derivation_proof_claimed",
    ):
        require_bool(f"Phase41 {field}", witness[field])
        if witness[field]:
            raise Phase42Error(f"Phase41 witness: {field} must be false")
    require_bool("Phase41 boundary_domains_differ", witness["boundary_domains_differ"])
    if not witness["boundary_domains_differ"]:
        raise Phase42Error("Phase41 witness: boundary_domains_differ must be true")
    for field in (
        "phase29_contract_commitment",
        "phase30_source_chain_commitment",
        "phase30_step_envelopes_commitment",
        "phase29_global_start_state_commitment",
        "phase29_global_end_state_commitment",
        "phase30_chain_start_boundary_commitment",
        "phase30_chain_end_boundary_commitment",
        "source_template_commitment",
        "aggregation_template_commitment",
        "start_boundary_translation_commitment",
        "end_boundary_translation_commitment",
        "boundary_translation_witness_commitment",
    ):
        require_hash32(f"Phase41 {field}", witness[field])
    if (
        witness["phase29_global_start_state_commitment"]
        == witness["phase30_chain_start_boundary_commitment"]
        and witness["phase29_global_end_state_commitment"]
        == witness["phase30_chain_end_boundary_commitment"]
    ):
        raise Phase42Error("Phase41 witness: direct equality is not a translation witness")
    expected_start = commit_phase41_boundary_translation_pair(
        "start",
        witness["phase29_global_start_state_commitment"],
        witness["phase30_chain_start_boundary_commitment"],
        witness,
    )
    expected_end = commit_phase41_boundary_translation_pair(
        "end",
        witness["phase29_global_end_state_commitment"],
        witness["phase30_chain_end_boundary_commitment"],
        witness,
    )
    if witness["start_boundary_translation_commitment"] != expected_start:
        raise Phase42Error("Phase41 witness: start_boundary_translation_commitment mismatch")
    if witness["end_boundary_translation_commitment"] != expected_end:
        raise Phase42Error("Phase41 witness: end_boundary_translation_commitment mismatch")
    expected_witness = commit_phase41_boundary_translation_witness(witness)
    if witness["boundary_translation_witness_commitment"] != expected_witness:
        raise Phase42Error("Phase41 witness: boundary_translation_witness_commitment mismatch")


def verify_phase41_against_sources(
    witness: dict[str, Any], phase29: dict[str, Any], phase30: dict[str, Any]
) -> None:
    verify_phase41_witness(witness)
    expected = prepare_phase41_expected(phase29, phase30)
    if witness != expected:
        raise Phase42Error("source-bound Phase41 witness does not match Phase29 + Phase30")


def compare_shared_boundary_core(
    phase12_state: dict[str, Any],
    phase14_state: dict[str, Any],
    label: str,
) -> None:
    for field in SHARED_STATE_FIELDS:
        if phase12_state[field] != phase14_state[field]:
            raise Phase42Error(
                f"Phase42 {label}: shared carried-state field `{field}` differs between Phase12 and Phase14"
            )


def verify_boundary_preimage_evidence(
    evidence: dict[str, Any],
    phase29: dict[str, Any],
    phase30: dict[str, Any],
) -> dict[str, Any]:
    require_fields(evidence, PHASE42_EVIDENCE_FIELDS, "Phase42 boundary preimage evidence")
    if evidence["issue"] != ISSUE:
        raise Phase42Error("Phase42 boundary preimage evidence: issue must be 180")
    if evidence["evidence_version"] != PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_VERSION:
        raise Phase42Error("Phase42 boundary preimage evidence: unsupported evidence_version")
    if evidence["relation_outcome"] != "hash_preimage_relation":
        raise Phase42Error(
            "Phase42 boundary preimage evidence: relation_outcome must be hash_preimage_relation"
        )

    phase12_start = evidence["phase12_start_state"]
    phase12_end = evidence["phase12_end_state"]
    phase14_start = evidence["phase14_start_state"]
    phase14_end = evidence["phase14_end_state"]
    for label, state, verifier in (
        ("phase12_start_state", phase12_start, verify_phase12_state),
        ("phase12_end_state", phase12_end, verify_phase12_state),
        ("phase14_start_state", phase14_start, verify_phase14_state),
        ("phase14_end_state", phase14_end, verify_phase14_state),
    ):
        if not isinstance(state, dict):
            raise Phase42Error(f"Phase42 boundary preimage evidence: {label} must be an object")
        verifier(state, f"Phase42 {label}")

    expected_layout = commit_phase12_layout(phase30["layout"])
    for label, state in (
        ("phase12_start_state", phase12_start),
        ("phase12_end_state", phase12_end),
        ("phase14_start_state", phase14_start),
        ("phase14_end_state", phase14_end),
    ):
        if state["layout_commitment"] != expected_layout:
            raise Phase42Error(
                f"Phase42 evidence: {label} layout_commitment does not match Phase30 layout"
            )

    if phase12_start["public_state_commitment"] != phase30["chain_start_boundary_commitment"]:
        raise Phase42Error("Phase42 evidence: Phase12 start preimage does not bind Phase30 start")
    if phase12_end["public_state_commitment"] != phase30["chain_end_boundary_commitment"]:
        raise Phase42Error("Phase42 evidence: Phase12 end preimage does not bind Phase30 end")

    phase23_start = commit_phase23_boundary_state(phase14_start)
    phase23_end = commit_phase23_boundary_state(phase14_end)
    if phase23_start != phase29["global_start_state_commitment"]:
        raise Phase42Error("Phase42 evidence: Phase14 start preimage does not bind Phase29 start")
    if phase23_end != phase29["global_end_state_commitment"]:
        raise Phase42Error("Phase42 evidence: Phase14 end preimage does not bind Phase29 end")

    compare_shared_boundary_core(phase12_start, phase14_start, "start")
    compare_shared_boundary_core(phase12_end, phase14_end, "end")

    if phase12_start["step_index"] != 0 or phase14_start["step_index"] != 0:
        raise Phase42Error("Phase42 evidence: start states must have step_index=0")
    if phase12_end["step_index"] != phase30["total_steps"]:
        raise Phase42Error("Phase42 evidence: Phase12 end step_index must equal total_steps")
    if phase14_end["step_index"] != phase30["total_steps"]:
        raise Phase42Error("Phase42 evidence: Phase14 end step_index must equal total_steps")

    return {
        "phase12_start_public_state_commitment": phase12_start["public_state_commitment"],
        "phase12_end_public_state_commitment": phase12_end["public_state_commitment"],
        "phase14_start_public_state_commitment": phase14_start["public_state_commitment"],
        "phase14_end_public_state_commitment": phase14_end["public_state_commitment"],
        "phase23_start_boundary_commitment": phase23_start,
        "phase23_end_boundary_commitment": phase23_end,
    }


def evaluate(
    phase29: dict[str, Any],
    phase30: dict[str, Any],
    phase41: dict[str, Any] | None = None,
    boundary_preimage_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verify_phase29_contract(phase29)
    verify_phase30_manifest(phase30)
    if phase29["phase28_proof_backend_version"] != phase30["proof_backend_version"]:
        raise Phase42Error("Phase29/Phase30 backend version mismatch")
    if phase29["statement_version"] != phase30["statement_version"]:
        raise Phase42Error("Phase29/Phase30 statement version mismatch")
    if phase29["total_steps"] != phase30["total_steps"]:
        raise Phase42Error("Phase29/Phase30 total_steps mismatch")

    direct_start = phase29["global_start_state_commitment"] == phase30["chain_start_boundary_commitment"]
    direct_end = phase29["global_end_state_commitment"] == phase30["chain_end_boundary_commitment"]
    base = {
        "issue": ISSUE,
        "issue_url": ISSUE_URL,
        "phase": PHASE,
        "total_steps": phase30["total_steps"],
        "direct_boundary_equality": {"start": direct_start, "end": direct_end},
        "phase29_contract_commitment": phase29["input_contract_commitment"],
        "phase30_source_chain_commitment": phase30["source_chain_commitment"],
        "phase30_step_envelopes_commitment": phase30["step_envelopes_commitment"],
    }

    if direct_start and direct_end:
        return {
            **base,
            "accepted": True,
            "relation_outcome": "equality",
            "decision": "stay_current_path",
            "reason": "Phase29 and Phase30 boundaries already match; Phase31 direct binding is the clean path.",
            "required_next_step": "Use direct Phase31/37 binding; no Phase41 translation is needed.",
        }

    if phase41 is None and boundary_preimage_evidence is None:
        return {
            **base,
            "accepted": False,
            "relation_outcome": "impossible",
            "decision": "patch_once_then_stay",
            "reason": "Phase29/30 boundaries differ and no source-bound Phase41 witness was supplied.",
            "required_next_step": "Supply Phase41 plus Phase12 and Phase14/23 boundary preimage evidence, or pivot per Issue #180.",
        }

    if phase41 is not None:
        verify_phase41_against_sources(phase41, phase29, phase30)

    if boundary_preimage_evidence is not None:
        evidence_commitments = verify_boundary_preimage_evidence(
            boundary_preimage_evidence, phase29, phase30
        )
        return {
            **base,
            "accepted": True,
            "relation_outcome": "hash_preimage_relation",
            "decision": "stay_current_path",
            "phase41_source_bound": phase41 is not None,
            "boundary_preimage_evidence_version": PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_VERSION,
            "boundary_preimage_commitments": evidence_commitments,
            "reason": (
                "Phase12 and Phase14/23 boundary preimages recompute to the Phase30 and Phase29 "
                "boundary commitments and share the same carried-state core."
            ),
            "required_next_step": (
                "Promote the preimage evidence into a Rust-produced Phase42 artifact and consume it in Phase31/37."
            ),
        }

    assert phase41 is not None
    return {
        **base,
        "accepted": False,
        "relation_outcome": "impossible",
        "decision": "patch_once_then_stay",
        "phase41_witness_commitment": phase41["boundary_translation_witness_commitment"],
        "phase41_source_bound": True,
        "missing_evidence": [
            "Phase12 public-state boundary preimage",
            "Phase14/Phase23 boundary-state commitment preimage",
            "public projection/transform/hash-preimage relation between those preimages",
        ],
        "reason": (
            "Phase41 is source-bound, but it only binds an explicit Phase29/Phase30 boundary pair. "
            "It does not expose the shared preimage or transform needed for a clean Phase42 relation."
        ),
        "required_next_step": (
            "Expose one minimal source preimage/transform surface. If that cannot be made recomputable, pivot per Issue #180."
        ),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase29", required=True, type=pathlib.Path)
    parser.add_argument("--phase30", required=True, type=pathlib.Path)
    parser.add_argument("--phase41", type=pathlib.Path)
    parser.add_argument("--boundary-preimage-evidence", type=pathlib.Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument(
        "--require-clean-relation",
        action="store_true",
        help="Exit non-zero unless the decision gate accepts a clean relation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        phase29 = load_json(args.phase29)
        phase30 = load_json(args.phase30)
        phase41 = load_json(args.phase41) if args.phase41 else None
        evidence = (
            load_json(args.boundary_preimage_evidence)
            if args.boundary_preimage_evidence
            else None
        )
        result = evaluate(phase29, phase30, phase41, evidence)
    except Phase42Error as exc:
        print(f"Phase42 issue #{ISSUE}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    if args.require_clean_relation and not result["accepted"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
