#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "target" / "phase44b-public-projection-logup-probe" / "evidence.json"
M31_MODULUS = (1 << 31) - 1
PHASE43_PROJECTION_MAX_STEPS = 64
PHASE43_PROJECTION_PREFIX_WIDTH = 13
PHASE43_PROJECTION_HASH_LIMBS = 16
PHASE44B_LOGUP_TRANSCRIPT_SCHEMA = "phase44b-public-projection-logup-transcript-v2"
PHASE44B_LOGUP_CHALLENGE_SCHEMA = "phase44b-public-projection-logup-challenge-v1"
PHASE44B_LOGUP_RELATION_SCHEMA = "phase44b-public-projection-logup-relation-v1"
PHASE44B_LOGUP_TRANSCRIPT_DOMAIN = "phase44b-public-projection-logup-transcript-v2"
PHASE44B_LOGUP_CHALLENGE_DOMAIN = "phase44b-public-projection-logup-challenge-v1"
PHASE44B_LOGUP_ROW_DOMAIN = "phase44b-public-projection-logup-row-v1"
PHASE44B_LOGUP_BINDING_DOMAIN = "phase44b-public-projection-logup-binding-v2"
STWO_BACKEND_VERSION_PHASE12 = "stwo-phase12-decoding-family-v9"
STWO_DECODING_STATE_VERSION_PHASE12 = "stwo-decoding-state-v11"
STWO_DECODING_STATE_VERSION_PHASE14 = "stwo-decoding-state-v6"
STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30 = (
    "stwo-phase30-decoding-step-proof-envelope-manifest-v1"
)
STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43 = "phase43-history-replay-trace-v1"
STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43 = "normalized_replay_trace"
STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43 = "phase12-chain-to-phase14-chunked-history-trace-v1"


def phase29_update_usize(hasher: "hashlib._Hash", value: int) -> None:
    hasher.update(int(value).to_bytes(16, byteorder="little", signed=False))


def phase29_update_bool(hasher: "hashlib._Hash", value: bool) -> None:
    hasher.update(bytes([1 if value else 0]))


def phase29_update_len_prefixed(hasher: "hashlib._Hash", value: bytes | str) -> None:
    if isinstance(value, str):
        value = value.encode("utf-8")
    phase29_update_usize(hasher, len(value))
    hasher.update(value)


def lower_hex(bytes_value: bytes) -> str:
    return bytes_value.hex()


def hash32(label: str) -> str:
    return hashlib.blake2b(label.encode("utf-8"), digest_size=32).hexdigest()


def require_hash32(label: str, value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} must be a 32-byte lowercase hex commitment")
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a 32-byte lowercase hex commitment")


def transcript_term(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return ",".join(transcript_term(item) for item in value)
    return str(value)


def field_from_hash32(label: str, *parts: str) -> int:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, label)
    for part in parts:
        phase29_update_len_prefixed(hasher, part)
    return int.from_bytes(hasher.digest(), byteorder="little", signed=False) % M31_MODULUS


def nonzero_field_from_hash32(label: str, *parts: str) -> int:
    value = field_from_hash32(label, *parts)
    if value == 0:
        return 1
    return value


def i16_base(value: int) -> int:
    if value >= 0:
        return value
    return M31_MODULUS + value


def i16_base_with_label(label: str, value: int) -> int:
    encoded = i16_base(value)
    if encoded >= M31_MODULUS:
        raise ValueError(f"projection i16 value {label} encoded outside M31")
    return encoded


def usize_base(label: str, value: int) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    if value >= M31_MODULUS:
        raise ValueError(f"projection value {label}={value} exceeds M31 capacity")
    return value


def hash32_u16_limbs(label: str, value: str) -> list[int]:
    require_hash32(label, value)
    limbs = []
    for chunk in (value[i : i + 4] for i in range(0, 64, 4)):
        limbs.append(int(chunk, 16))
    return limbs


def phase43_update_phase12_state(hasher: "hashlib._Hash", state: dict[str, Any]) -> None:
    for part in [
        state["state_version"],
        state["layout_commitment"],
        state["persistent_state_commitment"],
        state["kv_history_commitment"],
        state["kv_cache_commitment"],
        state["incoming_token_commitment"],
        state["query_commitment"],
        state["output_commitment"],
        state["lookup_rows_commitment"],
        state["public_state_commitment"],
    ]:
        phase29_update_len_prefixed(hasher, part)
    phase29_update_usize(hasher, state["step_index"])
    hasher.update(int(state["position"]).to_bytes(2, byteorder="little", signed=True))
    phase29_update_usize(hasher, state["kv_history_length"])


def phase43_update_phase14_state(hasher: "hashlib._Hash", state: dict[str, Any]) -> None:
    for part in [
        state["state_version"],
        state["layout_commitment"],
        state["persistent_state_commitment"],
        state["kv_history_commitment"],
        state["kv_history_sealed_commitment"],
        state["kv_history_open_chunk_commitment"],
        state["kv_history_frontier_commitment"],
        state["lookup_transcript_commitment"],
        state["lookup_frontier_commitment"],
        state["kv_cache_commitment"],
        state["incoming_token_commitment"],
        state["query_commitment"],
        state["output_commitment"],
        state["lookup_rows_commitment"],
        state["public_state_commitment"],
    ]:
        phase29_update_len_prefixed(hasher, part)
    phase29_update_usize(hasher, state["step_index"])
    hasher.update(int(state["position"]).to_bytes(2, byteorder="little", signed=True))
    phase29_update_usize(hasher, state["kv_history_length"])
    phase29_update_usize(hasher, state["kv_history_chunk_size"])
    phase29_update_usize(hasher, state["kv_history_sealed_chunks"])
    phase29_update_usize(hasher, state["kv_history_open_chunk_pairs"])
    phase29_update_usize(hasher, state["kv_history_frontier_pairs"])
    phase29_update_usize(hasher, state["lookup_transcript_entries"])
    phase29_update_usize(hasher, state["lookup_frontier_entries"])


def phase43_update_trace_row(hasher: "hashlib._Hash", row: dict[str, Any]) -> None:
    phase29_update_usize(hasher, row["step_index"])
    phase29_update_usize(hasher, len(row["appended_pair"]))
    for value in row["appended_pair"]:
        hasher.update(int(value).to_bytes(2, byteorder="little", signed=True))
    for part in [
        row["input_lookup_rows_commitment"],
        row["output_lookup_rows_commitment"],
        row["phase30_step_envelope_commitment"],
    ]:
        phase29_update_len_prefixed(hasher, part)
    phase43_update_phase12_state(hasher, row["phase12_from_state"])
    phase43_update_phase12_state(hasher, row["phase12_to_state"])
    phase43_update_phase14_state(hasher, row["phase14_from_state"])
    phase43_update_phase14_state(hasher, row["phase14_to_state"])


def commit_phase43_history_replay_trace(trace: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, "phase43-history-replay-trace")
    phase29_update_usize(hasher, trace["issue"])
    proof_backend = trace["proof_backend"]
    for part in [
        trace["trace_version"],
        trace["relation_outcome"],
        trace["transform_rule"],
        proof_backend,
        trace["proof_backend_version"],
        trace["statement_version"],
        trace["phase42_witness_commitment"],
        trace["phase29_contract_commitment"],
        trace["phase28_aggregate_commitment"],
        trace["phase30_source_chain_commitment"],
        trace["phase30_step_envelopes_commitment"],
    ]:
        phase29_update_len_prefixed(hasher, part)
    phase29_update_usize(hasher, trace["total_steps"])
    phase29_update_len_prefixed(hasher, trace["layout_commitment"])
    phase29_update_usize(hasher, trace["rolling_kv_pairs"])
    phase29_update_usize(hasher, trace["pair_width"])
    for part in [
        trace["phase12_start_public_state_commitment"],
        trace["phase12_end_public_state_commitment"],
        trace["phase14_start_boundary_commitment"],
        trace["phase14_end_boundary_commitment"],
        trace["phase12_start_history_commitment"],
        trace["phase12_end_history_commitment"],
        trace["phase14_start_history_commitment"],
        trace["phase14_end_history_commitment"],
        trace["initial_kv_cache_commitment"],
        trace["appended_pairs_commitment"],
        trace["lookup_rows_commitments_commitment"],
    ]:
        phase29_update_len_prefixed(hasher, part)
    phase29_update_usize(hasher, len(trace["rows"]))
    for row in trace["rows"]:
        phase43_update_trace_row(hasher, row)
    phase29_update_bool(hasher, trace["full_history_replay_required"])
    phase29_update_bool(hasher, trace["cryptographic_compression_claimed"])
    phase29_update_bool(hasher, trace["stwo_air_proof_claimed"])
    return hasher.hexdigest()


@dataclass(frozen=True)
class ProjectionLayout:
    pair_width: int

    @property
    def appended_pair_start(self) -> int:
        return PHASE43_PROJECTION_PREFIX_WIDTH

    @property
    def input_lookup_start(self) -> int:
        return self.appended_pair_start + self.pair_width

    @property
    def output_lookup_start(self) -> int:
        return self.input_lookup_start + PHASE43_PROJECTION_HASH_LIMBS

    @property
    def phase12_from_public_start(self) -> int:
        return self.output_lookup_start + PHASE43_PROJECTION_HASH_LIMBS

    @property
    def phase12_to_public_start(self) -> int:
        return self.phase12_from_public_start + PHASE43_PROJECTION_HASH_LIMBS

    @property
    def phase14_from_public_start(self) -> int:
        return self.phase12_to_public_start + PHASE43_PROJECTION_HASH_LIMBS

    @property
    def phase14_to_public_start(self) -> int:
        return self.phase14_from_public_start + PHASE43_PROJECTION_HASH_LIMBS

    @property
    def column_count(self) -> int:
        return self.phase14_to_public_start + PHASE43_PROJECTION_HASH_LIMBS


def commit_phase43_projection(projection: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, "phase43-history-replay-field-projection")
    phase29_update_usize(hasher, len(projection["rows"]))
    phase29_update_usize(hasher, projection["layout"]["pair_width"])
    phase29_update_usize(hasher, projection["layout"]["column_count"])
    for row_index, row in enumerate(projection["rows"]):
        phase29_update_usize(hasher, row_index)
        phase29_update_usize(hasher, len(row))
        for value in row:
            hasher.update(int(value).to_bytes(4, byteorder="little", signed=False))
    return hasher.hexdigest()


def commit_phase43_trace_appended_pairs(trace: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, "phase42-source-appended-pairs")
    phase29_update_len_prefixed(hasher, trace["layout_commitment"])
    phase29_update_usize(hasher, trace["pair_width"])
    phase29_update_usize(hasher, len(trace["rows"]))
    for step_index, row in enumerate(trace["rows"]):
        if len(row["appended_pair"]) != trace["pair_width"]:
            raise ValueError(
                f"row {step_index} appended_pair length does not match pair_width"
            )
        phase29_update_usize(hasher, step_index)
        for value in row["appended_pair"]:
            hasher.update(int(value).to_bytes(2, byteorder="little", signed=True))
    return hasher.hexdigest()


def commit_phase43_trace_lookup_rows_commitments(trace: dict[str, Any]) -> str:
    if not trace["rows"]:
        raise ValueError("lookup-row commitment requires a non-empty trace")
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, "phase42-source-lookup-rows")
    phase29_update_len_prefixed(hasher, trace["layout_commitment"])
    phase29_update_usize(hasher, len(trace["rows"]) + 1)
    phase29_update_usize(hasher, 0)
    phase29_update_len_prefixed(hasher, trace["rows"][0]["input_lookup_rows_commitment"])
    for index, row in enumerate(trace["rows"], start=1):
        phase29_update_usize(hasher, index)
        phase29_update_len_prefixed(hasher, row["output_lookup_rows_commitment"])
    return hasher.hexdigest()


def commit_phase43_trace_phase30_step_envelopes(trace: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    hasher.update(STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30.encode("utf-8"))
    hasher.update(b"step-envelope-list")
    hasher.update(int(len(trace["rows"])).to_bytes(8, byteorder="little", signed=False))
    for row in trace["rows"]:
        require_hash32("phase30_step_envelope_commitment", row["phase30_step_envelope_commitment"])
        hasher.update(row["phase30_step_envelope_commitment"].encode("utf-8"))
    return hasher.hexdigest()


def commit_phase43_trace_source_chain(trace: dict[str, Any]) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, "phase43-source-chain-v1")
    phase29_update_len_prefixed(hasher, trace["layout_commitment"])
    phase29_update_usize(hasher, trace["total_steps"])
    phase29_update_usize(hasher, trace["pair_width"])
    phase29_update_len_prefixed(hasher, trace["phase30_step_envelopes_commitment"])
    for row in trace["rows"]:
        phase29_update_usize(hasher, row["step_index"])
        phase29_update_len_prefixed(hasher, row["phase30_step_envelope_commitment"])
        phase29_update_len_prefixed(hasher, row["input_lookup_rows_commitment"])
        phase29_update_len_prefixed(hasher, row["output_lookup_rows_commitment"])
        phase29_update_len_prefixed(hasher, row["phase12_from_state"]["lookup_rows_commitment"])
        phase29_update_len_prefixed(hasher, row["phase12_to_state"]["lookup_rows_commitment"])
        phase29_update_len_prefixed(hasher, row["phase14_from_state"]["lookup_rows_commitment"])
        phase29_update_len_prefixed(hasher, row["phase14_to_state"]["lookup_rows_commitment"])
    return hasher.hexdigest()


def build_projection(trace: dict[str, Any]) -> dict[str, Any]:
    layout = ProjectionLayout(pair_width=trace["pair_width"])
    rows: list[list[int]] = []
    for row_index, row in enumerate(trace["rows"]):
        values = [
            usize_base("row.step_index", row["step_index"]),
            usize_base("row.phase12_from_state.step_index", row["phase12_from_state"]["step_index"]),
            usize_base("row.phase12_to_state.step_index", row["phase12_to_state"]["step_index"]),
            usize_base("row.phase14_from_state.step_index", row["phase14_from_state"]["step_index"]),
            usize_base("row.phase14_to_state.step_index", row["phase14_to_state"]["step_index"]),
            i16_base_with_label("row.phase12_from_state.position", row["phase12_from_state"]["position"]),
            i16_base_with_label("row.phase12_to_state.position", row["phase12_to_state"]["position"]),
            i16_base_with_label("row.phase14_from_state.position", row["phase14_from_state"]["position"]),
            i16_base_with_label("row.phase14_to_state.position", row["phase14_to_state"]["position"]),
            usize_base(
                "row.phase12_from_state.kv_history_length",
                row["phase12_from_state"]["kv_history_length"],
            ),
            usize_base(
                "row.phase12_to_state.kv_history_length",
                row["phase12_to_state"]["kv_history_length"],
            ),
            usize_base(
                "row.phase14_from_state.kv_history_length",
                row["phase14_from_state"]["kv_history_length"],
            ),
            usize_base(
                "row.phase14_to_state.kv_history_length",
                row["phase14_to_state"]["kv_history_length"],
            ),
        ]
        for value in row["appended_pair"]:
            values.append(i16_base_with_label(f"row[{row_index}].appended_pair", value))
        values.extend(hash32_u16_limbs("input_lookup_rows_commitment", row["input_lookup_rows_commitment"]))
        values.extend(hash32_u16_limbs("output_lookup_rows_commitment", row["output_lookup_rows_commitment"]))
        values.extend(
            hash32_u16_limbs(
                "phase12_from_state.public_state_commitment",
                row["phase12_from_state"]["public_state_commitment"],
            )
        )
        values.extend(
            hash32_u16_limbs(
                "phase12_to_state.public_state_commitment",
                row["phase12_to_state"]["public_state_commitment"],
            )
        )
        values.extend(
            hash32_u16_limbs(
                "phase14_from_state.public_state_commitment",
                row["phase14_from_state"]["public_state_commitment"],
            )
        )
        values.extend(
            hash32_u16_limbs(
                "phase14_to_state.public_state_commitment",
                row["phase14_to_state"]["public_state_commitment"],
            )
        )
        if len(values) != layout.column_count:
            raise ValueError(
                f"projection row {row_index} produced {len(values)} columns, expected {layout.column_count}"
            )
        rows.append(values)

    projection = {
        "layout": {
            "pair_width": layout.pair_width,
            "column_count": layout.column_count,
        },
        "rows": rows,
    }
    projection["commitment"] = commit_phase43_projection(projection)
    return projection


def build_public_projection_logup_transcript_bundle(
    trace: dict[str, Any], projection: dict[str, Any]
) -> dict[str, Any]:
    fields: list[dict[str, Any]] = [
        {"name": "schema_version", "value": PHASE44B_LOGUP_TRANSCRIPT_SCHEMA},
        {"name": "issue", "value": trace["issue"]},
        {"name": "trace_version", "value": trace["trace_version"]},
        {"name": "relation_outcome", "value": trace["relation_outcome"]},
        {"name": "transform_rule", "value": trace["transform_rule"]},
        {"name": "proof_backend", "value": trace["proof_backend"]},
        {"name": "proof_backend_version", "value": trace["proof_backend_version"]},
        {"name": "statement_version", "value": trace["statement_version"]},
        {"name": "trace_commitment", "value": trace["trace_commitment"]},
        {"name": "projection_commitment", "value": projection["commitment"]},
        {
            "name": "phase30_source_chain_commitment",
            "value": trace["phase30_source_chain_commitment"],
        },
        {"name": "appended_pairs_commitment", "value": trace["appended_pairs_commitment"]},
        {
            "name": "lookup_rows_commitments_commitment",
            "value": trace["lookup_rows_commitments_commitment"],
        },
        {
            "name": "phase30_step_envelopes_commitment",
            "value": trace["phase30_step_envelopes_commitment"],
        },
        {
            "name": "phase12_start_public_state_commitment",
            "value": trace["phase12_start_public_state_commitment"],
        },
        {
            "name": "phase12_end_public_state_commitment",
            "value": trace["phase12_end_public_state_commitment"],
        },
        {
            "name": "phase14_start_boundary_commitment",
            "value": trace["phase14_start_boundary_commitment"],
        },
        {
            "name": "phase14_end_boundary_commitment",
            "value": trace["phase14_end_boundary_commitment"],
        },
        {
            "name": "phase12_start_history_commitment",
            "value": trace["phase12_start_history_commitment"],
        },
        {
            "name": "phase12_end_history_commitment",
            "value": trace["phase12_end_history_commitment"],
        },
        {
            "name": "phase14_start_history_commitment",
            "value": trace["phase14_start_history_commitment"],
        },
        {
            "name": "phase14_end_history_commitment",
            "value": trace["phase14_end_history_commitment"],
        },
        {"name": "initial_kv_cache_commitment", "value": trace["initial_kv_cache_commitment"]},
        {"name": "total_steps", "value": trace["total_steps"]},
        {"name": "pair_width", "value": trace["pair_width"]},
        {"name": "projection_row_count", "value": len(projection["rows"])},
        {"name": "projection_column_count", "value": projection["layout"]["column_count"]},
    ]
    for row in trace["rows"]:
        fields.extend(
            [
                {"name": f"row[{row['step_index']}].step_index", "value": row["step_index"]},
                {
                    "name": f"row[{row['step_index']}].appended_pair",
                    "value": row["appended_pair"],
                },
                {
                    "name": f"row[{row['step_index']}].input_lookup_rows_commitment",
                    "value": row["input_lookup_rows_commitment"],
                },
                {
                    "name": f"row[{row['step_index']}].output_lookup_rows_commitment",
                    "value": row["output_lookup_rows_commitment"],
                },
                {
                    "name": f"row[{row['step_index']}].phase30_step_envelope_commitment",
                    "value": row["phase30_step_envelope_commitment"],
                },
                {
                    "name": f"row[{row['step_index']}].phase12_from_state.public_state_commitment",
                    "value": row["phase12_from_state"]["public_state_commitment"],
                },
                {
                    "name": f"row[{row['step_index']}].phase12_to_state.public_state_commitment",
                    "value": row["phase12_to_state"]["public_state_commitment"],
                },
                {
                    "name": f"row[{row['step_index']}].phase14_from_state.public_state_commitment",
                    "value": row["phase14_from_state"]["public_state_commitment"],
                },
                {
                    "name": f"row[{row['step_index']}].phase14_to_state.public_state_commitment",
                    "value": row["phase14_to_state"]["public_state_commitment"],
                },
            ]
        )

    terms = [transcript_term(field["value"]) for field in fields]
    commitment = commit_transcript_terms(terms, PHASE44B_LOGUP_TRANSCRIPT_DOMAIN)
    return {
        "schema_version": PHASE44B_LOGUP_TRANSCRIPT_SCHEMA,
        "domain_separator": PHASE44B_LOGUP_TRANSCRIPT_DOMAIN,
        "fields": fields,
        "terms": terms,
        "commitment": commitment,
    }


def compute_public_projection_logup_transcript(trace: dict[str, Any], projection: dict[str, Any]) -> list[str]:
    return build_public_projection_logup_transcript_bundle(trace, projection)["terms"]


def derive_public_projection_logup_challenges(
    transcript_bundle: dict[str, Any], trace: dict[str, Any], projection: dict[str, Any]
) -> dict[str, Any]:
    seed_commitment = commit_transcript_terms(
        [
            transcript_bundle["commitment"],
            trace["phase30_source_chain_commitment"],
            projection["commitment"],
        ],
        PHASE44B_LOGUP_CHALLENGE_DOMAIN,
    )
    lookup_z = nonzero_field_from_hash32(
        f"{PHASE44B_LOGUP_CHALLENGE_DOMAIN}/z", seed_commitment
    )
    lookup_alpha = nonzero_field_from_hash32(
        f"{PHASE44B_LOGUP_CHALLENGE_DOMAIN}/alpha", seed_commitment
    )
    alpha_powers = [1]
    for _ in range(1, len(trace["rows"])):
        alpha_powers.append((alpha_powers[-1] * lookup_alpha) % M31_MODULUS)
    return {
        "schema_version": PHASE44B_LOGUP_CHALLENGE_SCHEMA,
        "domain_separator": PHASE44B_LOGUP_CHALLENGE_DOMAIN,
        "seed_commitment": seed_commitment,
        "lookup_z": lookup_z,
        "lookup_alpha": lookup_alpha,
        "lookup_alpha_powers": alpha_powers,
    }


def build_public_projection_logup_relation_bundle(
    trace: dict[str, Any],
    projection: dict[str, Any],
    transcript_bundle: dict[str, Any],
    challenge_bundle: dict[str, Any],
) -> dict[str, Any]:
    row_terms: list[dict[str, Any]] = []
    claimed_sum = 0
    for row_index, row in enumerate(trace["rows"]):
        projection_row = projection["rows"][row_index]
        row_field_terms = [
            f"row:{row_index}",
            transcript_term(row["step_index"]),
            transcript_term(row["appended_pair"]),
            row["input_lookup_rows_commitment"],
            row["output_lookup_rows_commitment"],
            row["phase30_step_envelope_commitment"],
            row["phase12_from_state"]["public_state_commitment"],
            row["phase12_to_state"]["public_state_commitment"],
            row["phase14_from_state"]["public_state_commitment"],
            row["phase14_to_state"]["public_state_commitment"],
            transcript_term(projection_row),
        ]
        row_digest_commitment = commit_transcript_terms(
            row_field_terms, PHASE44B_LOGUP_ROW_DOMAIN
        )
        row_digest = nonzero_field_from_hash32(
            f"{PHASE44B_LOGUP_ROW_DOMAIN}/value", row_digest_commitment
        )
        alpha_power = challenge_bundle["lookup_alpha_powers"][row_index]
        denominator = (challenge_bundle["lookup_z"] + row_digest) % M31_MODULUS
        if denominator == 0:
            denominator = 1
        inverse_denominator = pow(denominator, M31_MODULUS - 2, M31_MODULUS)
        term = (alpha_power * inverse_denominator) % M31_MODULUS
        claimed_sum = (claimed_sum + term) % M31_MODULUS
        row_terms.append(
            {
                "row_index": row_index,
                "row_digest_commitment": row_digest_commitment,
                "row_digest": row_digest,
                "alpha_power": alpha_power,
                "denominator": denominator,
                "inverse_denominator": inverse_denominator,
                "term": term,
                "public_row_fields": row_field_terms,
            }
        )

    relation_commitment = commit_transcript_terms(
        [
            PHASE44B_LOGUP_RELATION_SCHEMA,
            transcript_bundle["commitment"],
            challenge_bundle["seed_commitment"],
            str(challenge_bundle["lookup_z"]),
            str(challenge_bundle["lookup_alpha"]),
            str(claimed_sum),
            *[row_term["row_digest_commitment"] for row_term in row_terms],
        ],
        PHASE44B_LOGUP_BINDING_DOMAIN,
    )
    return {
        "schema_version": PHASE44B_LOGUP_RELATION_SCHEMA,
        "domain_separator": PHASE44B_LOGUP_RELATION_SCHEMA,
        "row_count": len(row_terms),
        "row_order": [row_term["row_index"] for row_term in row_terms],
        "lookup_z": challenge_bundle["lookup_z"],
        "lookup_alpha": challenge_bundle["lookup_alpha"],
        "lookup_alpha_powers": list(challenge_bundle["lookup_alpha_powers"]),
        "claimed_sum": claimed_sum,
        "row_terms": row_terms,
        "commitment": relation_commitment,
    }


def build_demo_phase12_state(
    label: str, step_index: int, position: int, layout_commitment: str
) -> dict[str, Any]:
    return {
        "state_version": STWO_DECODING_STATE_VERSION_PHASE12,
        "step_index": step_index,
        "position": position,
        "layout_commitment": layout_commitment,
        "persistent_state_commitment": hash32(f"{label}/persistent"),
        "kv_history_commitment": hash32(f"{label}/history"),
        "kv_history_length": step_index,
        "kv_cache_commitment": hash32(f"{label}/cache"),
        "incoming_token_commitment": hash32(f"{label}/token"),
        "query_commitment": hash32(f"{label}/query"),
        "output_commitment": hash32(f"{label}/output"),
        "lookup_rows_commitment": hash32(f"{label}/lookup-rows"),
        "public_state_commitment": hash32(f"{label}/public"),
    }


def build_demo_phase14_state(
    label: str, phase12_state: dict[str, Any], *, step_index: int, position: int
) -> dict[str, Any]:
    state = dict(phase12_state)
    state.update(
        {
            "state_version": STWO_DECODING_STATE_VERSION_PHASE14,
            "step_index": step_index,
            "position": position,
            "kv_history_sealed_commitment": hash32(f"{label}/sealed"),
            "kv_history_open_chunk_commitment": hash32(f"{label}/open-chunk"),
            "kv_history_frontier_commitment": hash32(f"{label}/frontier"),
            "lookup_transcript_commitment": hash32(f"{label}/lookup-transcript"),
            "lookup_frontier_commitment": hash32(f"{label}/lookup-frontier"),
            "kv_history_chunk_size": 2,
            "kv_history_sealed_chunks": 1,
            "kv_history_open_chunk_pairs": 1,
            "kv_history_frontier_pairs": 1,
            "lookup_transcript_entries": step_index + 1,
            "lookup_frontier_entries": 1,
        }
    )
    return state


def build_demo_trace() -> dict[str, Any]:
    layout_commitment = hash32("phase44b/layout")
    start_state = build_demo_phase12_state("phase44b/s0", 0, 0, layout_commitment)
    mid_state = build_demo_phase12_state("phase44b/s1", 1, 1, layout_commitment)
    end_state = build_demo_phase12_state("phase44b/s2", 2, 2, layout_commitment)

    start_state_phase14 = build_demo_phase14_state(
        "phase44b/p14s0", start_state, step_index=0, position=0
    )
    mid_state_phase14 = build_demo_phase14_state("phase44b/p14s1", mid_state, step_index=1, position=1)
    end_state_phase14 = build_demo_phase14_state("phase44b/p14s2", end_state, step_index=2, position=2)

    rows = [
        {
            "step_index": 0,
            "appended_pair": [11, 12],
            "input_lookup_rows_commitment": start_state["lookup_rows_commitment"],
            "output_lookup_rows_commitment": mid_state["lookup_rows_commitment"],
            "phase30_step_envelope_commitment": hash32("phase44b/envelope/0"),
            "phase12_from_state": start_state,
            "phase12_to_state": mid_state,
            "phase14_from_state": start_state_phase14,
            "phase14_to_state": mid_state_phase14,
        },
        {
            "step_index": 1,
            "appended_pair": [13, 14],
            "input_lookup_rows_commitment": mid_state["lookup_rows_commitment"],
            "output_lookup_rows_commitment": end_state["lookup_rows_commitment"],
            "phase30_step_envelope_commitment": hash32("phase44b/envelope/1"),
            "phase12_from_state": mid_state,
            "phase12_to_state": end_state,
            "phase14_from_state": mid_state_phase14,
            "phase14_to_state": end_state_phase14,
        },
    ]

    trace = {
        "issue": 180,
        "trace_version": STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43,
        "relation_outcome": STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43,
        "transform_rule": STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43,
        "proof_backend": "stwo",
        "proof_backend_version": STWO_BACKEND_VERSION_PHASE12,
        "statement_version": "statement-v1",
        "phase42_witness_commitment": hash32("phase44b/phase42"),
        "phase29_contract_commitment": hash32("phase44b/phase29"),
        "phase28_aggregate_commitment": hash32("phase44b/phase28"),
        "phase30_source_chain_commitment": "",
        "phase30_step_envelopes_commitment": "",
        "total_steps": len(rows),
        "layout_commitment": layout_commitment,
        "rolling_kv_pairs": 4,
        "pair_width": 2,
        "phase12_start_public_state_commitment": start_state["public_state_commitment"],
        "phase12_end_public_state_commitment": end_state["public_state_commitment"],
        "phase14_start_boundary_commitment": hash32("phase44b/p14-boundary/start"),
        "phase14_end_boundary_commitment": hash32("phase44b/p14-boundary/end"),
        "phase12_start_history_commitment": start_state["kv_history_commitment"],
        "phase12_end_history_commitment": end_state["kv_history_commitment"],
        "phase14_start_history_commitment": start_state_phase14["kv_history_commitment"],
        "phase14_end_history_commitment": end_state_phase14["kv_history_commitment"],
        "initial_kv_cache_commitment": start_state["kv_cache_commitment"],
        "appended_pairs_commitment": "",
        "lookup_rows_commitments_commitment": "",
        "rows": rows,
        "full_history_replay_required": True,
        "cryptographic_compression_claimed": False,
        "stwo_air_proof_claimed": False,
        "trace_commitment": "",
    }
    trace["appended_pairs_commitment"] = commit_phase43_trace_appended_pairs(trace)
    trace["lookup_rows_commitments_commitment"] = commit_phase43_trace_lookup_rows_commitments(trace)
    trace["phase30_step_envelopes_commitment"] = commit_phase43_trace_phase30_step_envelopes(trace)
    trace["phase30_source_chain_commitment"] = commit_phase43_trace_source_chain(trace)
    trace["trace_commitment"] = commit_phase43_history_replay_trace(trace)
    return trace


def verify_demo_trace(trace: dict[str, Any]) -> None:
    if trace["issue"] != 180:
        raise ValueError("Phase44B probe must reference issue #180")
    if trace["proof_backend"] != "stwo":
        raise ValueError("Phase44B probe must use the stwo backend")
    if trace["statement_version"] != "statement-v1":
        raise ValueError("Phase44B probe must keep statement-v1")
    if trace["total_steps"] < 2 or trace["total_steps"] > PHASE43_PROJECTION_MAX_STEPS:
        raise ValueError("Phase44B probe must stay within the bounded row budget")
    if trace["total_steps"] != len(trace["rows"]):
        raise ValueError("Phase44B probe trace row count mismatch")
    if trace["total_steps"] & (trace["total_steps"] - 1):
        raise ValueError("Phase44B probe trace must have a power-of-two row count")

    for index, row in enumerate(trace["rows"]):
        if row["step_index"] != index:
            raise ValueError(f"row {index} step_index drift")
        if len(row["appended_pair"]) != trace["pair_width"]:
            raise ValueError(f"row {index} appended_pair length mismatch")
        for field in (
            "input_lookup_rows_commitment",
            "output_lookup_rows_commitment",
            "phase30_step_envelope_commitment",
        ):
            require_hash32(f"row[{index}].{field}", row[field])
        if row["phase12_from_state"]["lookup_rows_commitment"] != row["input_lookup_rows_commitment"]:
            raise ValueError(f"row {index} Phase12 input lookup commitment mismatch")
        if row["phase12_to_state"]["lookup_rows_commitment"] != row["output_lookup_rows_commitment"]:
            raise ValueError(f"row {index} Phase12 output lookup commitment mismatch")
        if row["phase14_from_state"]["lookup_rows_commitment"] != row["input_lookup_rows_commitment"]:
            raise ValueError(f"row {index} Phase14 input lookup commitment mismatch")
        if row["phase14_to_state"]["lookup_rows_commitment"] != row["output_lookup_rows_commitment"]:
            raise ValueError(f"row {index} Phase14 output lookup commitment mismatch")
        if row["phase12_from_state"]["public_state_commitment"] != row["phase14_from_state"]["public_state_commitment"]:
            raise ValueError(f"row {index} shared public-state mismatch on from-state")
        if row["phase12_to_state"]["public_state_commitment"] != row["phase14_to_state"]["public_state_commitment"]:
            raise ValueError(f"row {index} shared public-state mismatch on to-state")
        if row["phase12_from_state"]["layout_commitment"] != trace["layout_commitment"]:
            raise ValueError(f"row {index} Phase12 from-state layout mismatch")

    if trace["phase30_source_chain_commitment"] != commit_phase43_trace_source_chain(trace):
        raise ValueError("source-chain commitment drift")

    for key in (
        "phase42_witness_commitment",
        "phase29_contract_commitment",
        "phase28_aggregate_commitment",
        "phase30_source_chain_commitment",
        "phase30_step_envelopes_commitment",
        "phase12_start_public_state_commitment",
        "phase12_end_public_state_commitment",
        "phase14_start_boundary_commitment",
        "phase14_end_boundary_commitment",
        "phase12_start_history_commitment",
        "phase12_end_history_commitment",
        "phase14_start_history_commitment",
        "phase14_end_history_commitment",
        "initial_kv_cache_commitment",
        "appended_pairs_commitment",
        "lookup_rows_commitments_commitment",
        "trace_commitment",
    ):
        require_hash32(key, trace[key])

    if trace["phase30_step_envelopes_commitment"] != commit_phase43_trace_phase30_step_envelopes(trace):
        raise ValueError("Phase30 step-envelope commitment drift")
    if trace["appended_pairs_commitment"] != commit_phase43_trace_appended_pairs(trace):
        raise ValueError("appended-pairs commitment drift")
    if trace["lookup_rows_commitments_commitment"] != commit_phase43_trace_lookup_rows_commitments(trace):
        raise ValueError("lookup-row commitment drift")
    if trace["trace_commitment"] != commit_phase43_history_replay_trace(trace):
        raise ValueError("trace commitment drift")


def validate_public_projection_logup_evidence(
    trace: dict[str, Any], projection: dict[str, Any], evidence: dict[str, Any]
) -> None:
    transcript_bundle = build_public_projection_logup_transcript_bundle(trace, projection)
    challenge_bundle = derive_public_projection_logup_challenges(
        transcript_bundle, trace, projection
    )
    relation_bundle = build_public_projection_logup_relation_bundle(
        trace, projection, transcript_bundle, challenge_bundle
    )

    if evidence["schema_version"] != "phase44b-public-projection-logup-probe-evidence-v1":
        raise ValueError("Phase44B probe schema drift")
    if evidence["probe"] != "phase44b-public-projection-logup-binding":
        raise ValueError("Phase44B probe id drift")
    if evidence["issue"] != trace["issue"]:
        raise ValueError("issue drift")
    if evidence["proof_backend"] != trace["proof_backend"]:
        raise ValueError("proof backend drift")
    if evidence["proof_backend_version"] != trace["proof_backend_version"]:
        raise ValueError("proof backend version drift")
    if evidence["statement_version"] != trace["statement_version"]:
        raise ValueError("statement version drift")
    if evidence["phase30_source_chain_commitment"] != trace["phase30_source_chain_commitment"]:
        raise ValueError("source-chain commitment drift")
    if evidence["trace_commitment"] != trace["trace_commitment"]:
        raise ValueError("trace commitment drift")
    if evidence["projection_commitment"] != projection["commitment"]:
        raise ValueError("projection commitment drift")
    if evidence["appended_pairs_commitment"] != trace["appended_pairs_commitment"]:
        raise ValueError("appended-pairs commitment drift")
    if (
        evidence["lookup_rows_commitments_commitment"]
        != trace["lookup_rows_commitments_commitment"]
    ):
        raise ValueError("lookup-row commitment drift")
    if (
        evidence["phase30_step_envelopes_commitment"]
        != trace["phase30_step_envelopes_commitment"]
    ):
        raise ValueError("phase30 step-envelope commitment drift")
    if evidence["total_steps"] != trace["total_steps"]:
        raise ValueError("total_steps drift")
    if evidence["pair_width"] != trace["pair_width"]:
        raise ValueError("pair_width drift")
    if evidence["projection_row_count"] != len(projection["rows"]):
        raise ValueError("projection row count drift")
    if evidence["projection_column_count"] != projection["layout"]["column_count"]:
        raise ValueError("projection column count drift")
    if evidence["public_projection_logup_transcript_commitment"] != transcript_bundle["commitment"]:
        raise ValueError("transcript commitment drift")
    if evidence["public_projection_logup_challenge_seed_commitment"] != challenge_bundle["seed_commitment"]:
        raise ValueError("challenge seed drift")
    if evidence["public_projection_logup_relation_commitment"] != relation_bundle["commitment"]:
        raise ValueError("relation commitment drift")
    if evidence["public_projection_logup_challenges"] != {
        key: value
        for key, value in challenge_bundle.items()
        if key != "schema_version"
    }:
        raise ValueError("challenge bundle drift")
    if evidence["public_projection_logup_relation_shape"] != {
        key: value
        for key, value in relation_bundle.items()
        if key != "schema_version"
    }:
        raise ValueError("relation shape drift")
    if evidence["public_projection_logup_transcript_fields"] != transcript_bundle["fields"]:
        raise ValueError("transcript field drift")
    if evidence["public_projection_logup_transcript_terms"] != transcript_bundle["terms"]:
        raise ValueError("transcript term drift")
    if evidence["public_projection_logup_transcript_fields"][0]["name"] != "schema_version":
        raise ValueError("transcript field order drift")
    if evidence["public_projection_logup_binding_commitment"] != compute_public_projection_logup_binding(
        trace, projection
    )["public_projection_logup_binding_commitment"]:
        raise ValueError("binding commitment drift")


def commit_transcript_terms(terms: Iterable[str], domain_separator: str) -> str:
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, domain_separator)
    for term in terms:
        phase29_update_len_prefixed(hasher, term)
    return hasher.hexdigest()


def compute_public_projection_logup_binding(trace: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    transcript_bundle = build_public_projection_logup_transcript_bundle(trace, projection)
    challenge_bundle = derive_public_projection_logup_challenges(
        transcript_bundle, trace, projection
    )
    relation_bundle = build_public_projection_logup_relation_bundle(
        trace, projection, transcript_bundle, challenge_bundle
    )
    hasher = hashlib.blake2b(digest_size=32)
    phase29_update_len_prefixed(hasher, PHASE44B_LOGUP_BINDING_DOMAIN)
    for term in [
        trace["trace_commitment"],
        projection["commitment"],
        trace["phase30_source_chain_commitment"],
        transcript_bundle["commitment"],
        challenge_bundle["seed_commitment"],
        str(challenge_bundle["lookup_z"]),
        str(challenge_bundle["lookup_alpha"]),
        relation_bundle["commitment"],
        str(relation_bundle["claimed_sum"]),
        str(trace["total_steps"]),
        str(trace["pair_width"]),
    ]:
        phase29_update_len_prefixed(hasher, term)
    binding_commitment = hasher.hexdigest()
    return {
        "public_projection_logup_transcript_commitment": transcript_bundle["commitment"],
        "public_projection_logup_challenge_seed_commitment": challenge_bundle["seed_commitment"],
        "public_projection_logup_relation_commitment": relation_bundle["commitment"],
        "public_projection_logup_binding_commitment": binding_commitment,
        "public_projection_logup_transcript_fields": transcript_bundle["fields"],
        "public_projection_logup_transcript_terms": list(transcript_bundle["terms"]),
        "public_projection_logup_challenges": {
            key: value for key, value in challenge_bundle.items() if key != "schema_version"
        },
        "public_projection_logup_relation_shape": {
            key: value for key, value in relation_bundle.items() if key != "schema_version"
        },
    }


def build_probe_evidence(trace: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    verify_demo_trace(trace)
    projection_commitment = commit_phase43_projection(projection)
    if projection_commitment != projection["commitment"]:
        raise ValueError("projection commitment drift")
    if projection["layout"]["pair_width"] != trace["pair_width"]:
        raise ValueError("projection pair_width mismatch")
    if projection["layout"]["column_count"] != PHASE43_PROJECTION_PREFIX_WIDTH + trace["pair_width"] + PHASE43_PROJECTION_HASH_LIMBS * 6:
        raise ValueError("projection column count mismatch")

    binding = compute_public_projection_logup_binding(trace, projection)
    evidence = {
        "schema_version": "phase44b-public-projection-logup-probe-evidence-v1",
        "issue": trace["issue"],
        "probe": "phase44b-public-projection-logup-binding",
        "proof_backend": trace["proof_backend"],
        "proof_backend_version": trace["proof_backend_version"],
        "statement_version": trace["statement_version"],
        "phase30_source_chain_commitment": trace["phase30_source_chain_commitment"],
        "trace_commitment": trace["trace_commitment"],
        "projection_commitment": projection["commitment"],
        "appended_pairs_commitment": trace["appended_pairs_commitment"],
        "lookup_rows_commitments_commitment": trace["lookup_rows_commitments_commitment"],
        "phase30_step_envelopes_commitment": trace["phase30_step_envelopes_commitment"],
        "phase12_start_public_state_commitment": trace["phase12_start_public_state_commitment"],
        "phase12_end_public_state_commitment": trace["phase12_end_public_state_commitment"],
        "phase14_start_boundary_commitment": trace["phase14_start_boundary_commitment"],
        "phase14_end_boundary_commitment": trace["phase14_end_boundary_commitment"],
        "phase12_start_history_commitment": trace["phase12_start_history_commitment"],
        "phase12_end_history_commitment": trace["phase12_end_history_commitment"],
        "phase14_start_history_commitment": trace["phase14_start_history_commitment"],
        "phase14_end_history_commitment": trace["phase14_end_history_commitment"],
        "initial_kv_cache_commitment": trace["initial_kv_cache_commitment"],
        "total_steps": trace["total_steps"],
        "pair_width": trace["pair_width"],
        "projection_row_count": len(projection["rows"]),
        "projection_column_count": projection["layout"]["column_count"],
        "probe_decision": "keep_alive_bridge_bound_not_compression",
        "non_claims": [
            "Does not claim recursive proof closure.",
            "Does not claim cryptographic compression.",
            "Does not claim exact Cairo QM31 evaluation of PublicData.logup_sum(...).",
            "Does not claim a full Phase43 breakthrough result.",
        ],
        **binding,
    }
    validate_public_projection_logup_evidence(trace, projection, evidence)
    return evidence


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT,
        help="Write the Phase44B evidence JSON here.",
    )
    parser.add_argument(
        "--trace-json",
        type=pathlib.Path,
        help="Optional Phase43 trace JSON to bind instead of the synthetic bounded demo.",
    )
    parser.add_argument(
        "--emit-surfaces",
        action="store_true",
        help="Also write the synthetic trace and projection JSON surfaces next to the evidence.",
    )
    args = parser.parse_args(argv)

    if args.trace_json is not None:
        trace = json.loads(args.trace_json.read_text(encoding="utf-8"))
    else:
        trace = build_demo_trace()
    projection = build_projection(trace)
    evidence = build_probe_evidence(trace, projection)
    write_json(args.output, evidence)
    if args.emit_surfaces:
        write_json(args.output.with_name("phase43-trace.json"), trace)
        write_json(args.output.with_name("phase43-projection.json"), projection)
    print(f"Phase44B evidence written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
