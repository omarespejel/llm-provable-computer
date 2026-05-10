#!/usr/bin/env python3
"""Checked fused Softmax-table proof-size microprofile for issue #526.

This gate reads the already checked fused Softmax-table route matrix, parses the
fused proof envelopes for every profile row, and records top-level STARK proof
section byte buckets. It is deliberately an engineering microprofile: it explains
where the serialized proof bytes go at the exposed proof-object boundary, while
recording that backend-internal source-arithmetic-vs-lookup columns are not yet
exposed by the current gates.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import pathlib
import sys
import tempfile
import uuid
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_fused_softmax_table_route_matrix_gate as matrix

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-fused-softmax-table-microprofile-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-fused-softmax-table-microprofile-2026-05.tsv"

SCHEMA = "zkai-attention-kv-fused-softmax-table-microprofile-v1"
ISSUE = 526
SOURCE_ISSUE = matrix.ISSUE
DECISION = "GO_TOP_LEVEL_FUSED_SOFTMAX_TABLE_PROOF_BYTE_MICROPROFILE_WITH_BACKEND_INTERNAL_SPLIT_NO_GO"
ROUTE_ID = "local_stwo_attention_kv_fused_softmax_table_microprofile"
CLAIM_BOUNDARY = (
    "ENGINEERING_MICROPROFILE_FOR_TOP_LEVEL_NATIVE_STWO_FUSED_SOFTMAX_TABLE_PROOF_BYTE_BUCKETS_"
    "NOT_BINARY_PCS_FRI_INTERNAL_ACCOUNTING_NOT_SOURCE_VS_LOOKUP_COLUMN_SPLIT_NOT_TIMING_NOT_BENCHMARK"
)
TIMING_POLICY = "no_timing_microprofile_proof_bytes_only"
PROOF_OBJECT_SCOPE = "serialized_stark_proof_json_sections_inside_checked_fused_envelopes"
BACKEND_INTERNAL_SPLIT_STATUS = "NO_GO_BACKEND_DOES_NOT_EXPOSE_SOURCE_ARITHMETIC_VS_LOGUP_COLUMN_BYTE_SPLIT"
COLUMN_BREAKDOWN_STATUS = "NO_GO_PREPROCESSED_BASE_EXTENSION_COLUMN_COUNTS_NOT_EXPOSED_BY_CURRENT_FUSED_GATES"
RELATION_WIDTH_STATUS_EXPOSED = "EXPOSED_BY_GATE"
RELATION_WIDTH_STATUS_INFERRED_MISSING = "NOT_EXPOSED_BY_GATE_DO_NOT_INFER"
PROOF_BUCKET_STATUS = "GO_TOP_LEVEL_STARK_PROOF_JSON_SECTION_BUCKETS_EXTRACTED_FROM_FUSED_ENVELOPES"
NON_CLAIMS = (
    "not real-valued Softmax",
    "not implementation-exact model Softmax",
    "not full inference",
    "not timing evidence",
    "not a public benchmark",
    "not binary PCS/FRI internal accounting",
    "not source-arithmetic versus lookup column attribution",
    "not recursion or PCD",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv",
    "python3 scripts/zkai_attention_kv_fused_softmax_table_microprofile_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_microprofile_gate",
    "just gate-fast",
    "just gate",
)
PROOF_SECTION_KEYS = (
    "config",
    "commitments",
    "sampled_values",
    "decommitments",
    "queried_values",
    "proof_of_work",
    "fri_proof",
)
PROOF_CONFIG = {
    "fri_config": {
        "fold_step": 1,
        "log_blowup_factor": 1,
        "log_last_layer_degree_bound": 0,
        "n_queries": 3,
    },
    "lifting_log_size": None,
    "pow_bits": 10,
}
TSV_COLUMNS = (
    "profile_id",
    "axis_role",
    "key_width",
    "value_width",
    "head_count",
    "steps_per_head",
    "lookup_claims",
    "trace_rows",
    "table_rows",
    "lookup_relation_width",
    "lookup_relation_width_status",
    "fused_proof_size_bytes",
    "proof_section_payload_bytes_total",
    "proof_json_wrapper_bytes",
    "config_bytes",
    "commitments_bytes",
    "sampled_values_bytes",
    "decommitments_bytes",
    "queried_values_bytes",
    "proof_of_work_bytes",
    "fri_proof_bytes",
    "commitment_bucket_bytes",
    "query_bucket_bytes",
    "opening_bucket_bytes",
    "backend_internal_split_status",
)
EXPECTED_PROFILE_IDS = matrix.PROFILE_IDS
EXPECTED_TOTAL_FUSED_PROOF_BYTES = 563_139
EXPECTED_TOTAL_SECTION_PAYLOAD_BYTES = 562_014
EXPECTED_TOTAL_WRAPPER_BYTES = 1_125
EXPECTED_LARGEST_PROFILE_ID = "d16_two_head_seq16"
EXPECTED_LARGEST_PROFILE_PROOF_BYTES = 84_868
EXPECTED_TOTAL_LOOKUP_CLAIMS = 2_440
EXPECTED_TOTAL_TRACE_ROWS = 3_200
EXPECTED_TOTAL_SOURCE_PLUS_SIDECAR_BYTES = 716_130
EXPECTED_TOTAL_FUSED_SAVINGS_BYTES = 152_991
EXPECTED_EXPOSED_RELATION_WIDTH_PROFILES = (
    "d8_single_head_seq8",
    "d16_single_head_seq8",
    "d8_two_head_seq8",
    "d8_four_head_seq8",
    "d16_two_head_seq8",
    "d16_two_head_seq16",
)
EXPECTED_MISSING_RELATION_WIDTH_PROFILES = tuple(
    profile_id for profile_id in EXPECTED_PROFILE_IDS if profile_id not in EXPECTED_EXPOSED_RELATION_WIDTH_PROFILES
)
EXPECTED_MUTATION_NAMES = (
    "decision_relabeling",
    "claim_boundary_overclaim",
    "timing_policy_overclaim",
    "proof_bucket_status_overclaim",
    "backend_internal_split_overclaim",
    "column_breakdown_overclaim",
    "route_row_order_drift",
    "profile_id_relabeling",
    "lookup_relation_width_smuggling",
    "fused_proof_size_smuggling",
    "proof_section_bucket_smuggling",
    "query_bucket_smuggling",
    "opening_bucket_smuggling",
    "trace_column_count_smuggling",
    "aggregate_total_smuggling",
    "largest_profile_smuggling",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = 18


class FusedSoftmaxTableMicroprofileGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FusedSoftmaxTableMicroprofileGateError(f"{label} must be an integer")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise FusedSoftmaxTableMicroprofileGateError(f"{label} must be a non-empty string")
    return value


def read_fused_proof_sections(profile: matrix.Profile) -> dict[str, Any]:
    module = profile.gate_module
    envelope = module.read_bounded_json(module.FUSED_ENVELOPE_JSON, module.MAX_FUSED_ENVELOPE_JSON_BYTES, profile.profile_id)
    if not isinstance(envelope, dict):
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} fused envelope must be object")
    proof_backend = require_str(envelope.get("proof_backend"), f"{profile.profile_id} proof_backend")
    proof_backend_version = require_str(
        envelope.get("proof_backend_version"),
        f"{profile.profile_id} proof_backend_version",
    )
    proof_schema_version = require_str(
        envelope.get("proof_schema_version"),
        f"{profile.profile_id} proof_schema_version",
    )
    statement_version = require_str(envelope.get("statement_version"), f"{profile.profile_id} statement_version")
    if proof_backend != "stwo":
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} proof backend drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not proof:
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} proof byte array missing")
    proof_bytes = bytearray()
    for index, value in enumerate(proof):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 255:
            raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} proof byte[{index}] invalid")
        proof_bytes.append(value)
    try:
        proof_json = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} proof is not JSON: {err}") from err
    stark_proof = proof_json.get("stark_proof") if isinstance(proof_json, dict) else None
    if not isinstance(stark_proof, dict) or set(stark_proof) != set(PROOF_SECTION_KEYS):
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} stark_proof section drift")
    if stark_proof["config"] != PROOF_CONFIG:
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} proof config drift")
    section_bytes = {key: len(canonical_json_bytes(stark_proof[key])) for key in PROOF_SECTION_KEYS}
    payload_total = sum(section_bytes.values())
    wrapper_bytes = len(proof_bytes) - payload_total
    if wrapper_bytes <= 0:
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} wrapper byte accounting drift")
    return {
        "proof_backend": proof_backend,
        "proof_backend_version": proof_backend_version,
        "proof_schema_version": proof_schema_version,
        "statement_version": statement_version,
        "proof_section_bytes": section_bytes,
        "proof_section_payload_bytes_total": payload_total,
        "proof_json_wrapper_bytes": wrapper_bytes,
        "proof_config": stark_proof["config"],
    }


def build_microprofile_row(profile: matrix.Profile) -> dict[str, Any]:
    route_row = matrix.build_route_row(profile)
    gate_result = matrix.read_json(profile.gate_json, f"{profile.profile_id} gate result")
    proof_sections = read_fused_proof_sections(profile)
    relation_width = gate_result.get("lookup_relation_width")
    relation_width_status = RELATION_WIDTH_STATUS_EXPOSED
    if relation_width is None:
        relation_width_status = RELATION_WIDTH_STATUS_INFERRED_MISSING
    elif require_int(relation_width, f"{profile.profile_id} lookup_relation_width") <= 0:
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} lookup relation width must be positive")
    section_bytes = proof_sections["proof_section_bytes"]
    row = {
        "profile_id": route_row["profile_id"],
        "axis_role": route_row["axis_role"],
        "key_width": route_row["key_width"],
        "value_width": route_row["value_width"],
        "head_count": route_row["head_count"],
        "steps_per_head": route_row["steps_per_head"],
        "lookup_claims": route_row["lookup_claims"],
        "trace_rows": route_row["trace_rows"],
        "table_rows": route_row["table_rows"],
        "lookup_relation": gate_result.get("lookup_relation"),
        "lookup_relation_width": relation_width,
        "lookup_relation_width_status": relation_width_status,
        "fused_proof_size_bytes": route_row["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": route_row["fused_envelope_size_bytes"],
        "source_plus_sidecar_raw_proof_bytes": route_row["source_plus_sidecar_raw_proof_bytes"],
        "fused_to_source_plus_sidecar_ratio": route_row["fused_to_source_plus_sidecar_ratio"],
        "proof_section_bytes": section_bytes,
        "proof_section_payload_bytes_total": proof_sections["proof_section_payload_bytes_total"],
        "proof_json_wrapper_bytes": proof_sections["proof_json_wrapper_bytes"],
        "proof_backend": proof_sections["proof_backend"],
        "proof_backend_version": proof_sections["proof_backend_version"],
        "proof_schema_version": proof_sections["proof_schema_version"],
        "statement_version": proof_sections["statement_version"],
        "proof_config": proof_sections["proof_config"],
        "proof_byte_buckets": {
            "commitment_bucket_bytes": section_bytes["commitments"],
            "query_bucket_bytes": section_bytes["sampled_values"] + section_bytes["queried_values"],
            "opening_bucket_bytes": section_bytes["decommitments"] + section_bytes["fri_proof"],
            "config_and_pow_bytes": section_bytes["config"] + section_bytes["proof_of_work"],
            "json_wrapper_bytes": proof_sections["proof_json_wrapper_bytes"],
        },
        "trace_rows_by_component": {
            "fused_trace_rows": route_row["trace_rows"],
            "lookup_claim_rows": route_row["lookup_claims"],
            "multiplicity_table_rows": route_row["table_rows"],
            "source_arithmetic_rows_status": BACKEND_INTERNAL_SPLIT_STATUS,
            "logup_lookup_rows_status": BACKEND_INTERNAL_SPLIT_STATUS,
        },
        "trace_columns_by_component": {
            "fused_trace_columns": None,
            "fused_trace_columns_status": COLUMN_BREAKDOWN_STATUS,
            "source_arithmetic_columns": None,
            "source_arithmetic_columns_status": BACKEND_INTERNAL_SPLIT_STATUS,
            "logup_lookup_columns": None,
            "logup_lookup_columns_status": BACKEND_INTERNAL_SPLIT_STATUS,
            "preprocessed_columns": None,
            "preprocessed_columns_status": COLUMN_BREAKDOWN_STATUS,
            "base_columns": None,
            "base_columns_status": COLUMN_BREAKDOWN_STATUS,
            "extension_columns": None,
            "extension_columns_status": COLUMN_BREAKDOWN_STATUS,
        },
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
        "column_breakdown_status": COLUMN_BREAKDOWN_STATUS,
        "evidence_json": route_row["evidence_json"],
        "fused_envelope_json": str(profile.gate_module.FUSED_ENVELOPE_JSON.relative_to(ROOT)),
    }
    validate_microprofile_row(row)
    if row["fused_proof_size_bytes"] != row["proof_section_payload_bytes_total"] + row["proof_json_wrapper_bytes"]:
        raise FusedSoftmaxTableMicroprofileGateError(f"{profile.profile_id} proof byte total drift")
    return row


def validate_microprofile_row(row: Any) -> None:
    if not isinstance(row, dict):
        raise FusedSoftmaxTableMicroprofileGateError("microprofile row must be object")
    expected = {
        "profile_id",
        "axis_role",
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "lookup_claims",
        "trace_rows",
        "table_rows",
        "lookup_relation",
        "lookup_relation_width",
        "lookup_relation_width_status",
        "fused_proof_size_bytes",
        "fused_envelope_size_bytes",
        "source_plus_sidecar_raw_proof_bytes",
        "fused_to_source_plus_sidecar_ratio",
        "proof_section_bytes",
        "proof_section_payload_bytes_total",
        "proof_json_wrapper_bytes",
        "proof_backend",
        "proof_backend_version",
        "proof_schema_version",
        "statement_version",
        "proof_config",
        "proof_byte_buckets",
        "trace_rows_by_component",
        "trace_columns_by_component",
        "backend_internal_split_status",
        "column_breakdown_status",
        "evidence_json",
        "fused_envelope_json",
    }
    if set(row) != expected:
        raise FusedSoftmaxTableMicroprofileGateError("microprofile row field drift")
    if row["profile_id"] not in EXPECTED_PROFILE_IDS:
        raise FusedSoftmaxTableMicroprofileGateError("profile_id drift")
    for key in (
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "lookup_claims",
        "trace_rows",
        "table_rows",
        "fused_proof_size_bytes",
        "fused_envelope_size_bytes",
        "source_plus_sidecar_raw_proof_bytes",
        "proof_section_payload_bytes_total",
        "proof_json_wrapper_bytes",
    ):
        if require_int(row[key], f"{row['profile_id']} {key}") <= 0:
            raise FusedSoftmaxTableMicroprofileGateError(f"{row['profile_id']} {key} must be positive")
    section_bytes = row["proof_section_bytes"]
    if not isinstance(section_bytes, dict) or set(section_bytes) != set(PROOF_SECTION_KEYS):
        raise FusedSoftmaxTableMicroprofileGateError("proof section field drift")
    for key in PROOF_SECTION_KEYS:
        if require_int(section_bytes[key], f"{row['profile_id']} {key} bytes") <= 0:
            raise FusedSoftmaxTableMicroprofileGateError(f"{row['profile_id']} {key} bytes must be positive")
    if row["proof_config"] != PROOF_CONFIG:
        raise FusedSoftmaxTableMicroprofileGateError("proof config drift")
    if row["proof_backend"] != "stwo":
        raise FusedSoftmaxTableMicroprofileGateError("proof backend drift")
    require_str(row["proof_backend_version"], "proof_backend_version")
    require_str(row["proof_schema_version"], "proof_schema_version")
    require_str(row["statement_version"], "statement_version")
    if row["fused_proof_size_bytes"] != row["proof_section_payload_bytes_total"] + row["proof_json_wrapper_bytes"]:
        raise FusedSoftmaxTableMicroprofileGateError("proof byte total drift")
    buckets = row["proof_byte_buckets"]
    expected_bucket_keys = {
        "commitment_bucket_bytes",
        "query_bucket_bytes",
        "opening_bucket_bytes",
        "config_and_pow_bytes",
        "json_wrapper_bytes",
    }
    if not isinstance(buckets, dict) or set(buckets) != expected_bucket_keys:
        raise FusedSoftmaxTableMicroprofileGateError("proof bucket field drift")
    if buckets["commitment_bucket_bytes"] != section_bytes["commitments"]:
        raise FusedSoftmaxTableMicroprofileGateError("commitment bucket drift")
    if buckets["query_bucket_bytes"] != section_bytes["sampled_values"] + section_bytes["queried_values"]:
        raise FusedSoftmaxTableMicroprofileGateError("query bucket drift")
    if buckets["opening_bucket_bytes"] != section_bytes["decommitments"] + section_bytes["fri_proof"]:
        raise FusedSoftmaxTableMicroprofileGateError("opening bucket drift")
    if buckets["config_and_pow_bytes"] != section_bytes["config"] + section_bytes["proof_of_work"]:
        raise FusedSoftmaxTableMicroprofileGateError("config-and-pow bucket drift")
    if buckets["json_wrapper_bytes"] != row["proof_json_wrapper_bytes"]:
        raise FusedSoftmaxTableMicroprofileGateError("JSON wrapper bucket drift")
    if row["lookup_relation_width"] is None:
        if row["lookup_relation_width_status"] != RELATION_WIDTH_STATUS_INFERRED_MISSING:
            raise FusedSoftmaxTableMicroprofileGateError("lookup relation width status drift")
    else:
        require_int(row["lookup_relation_width"], "lookup_relation_width")
        if row["lookup_relation_width_status"] != RELATION_WIDTH_STATUS_EXPOSED:
            raise FusedSoftmaxTableMicroprofileGateError("lookup relation width status drift")
    component_rows = row["trace_rows_by_component"]
    expected_component_row_keys = {
        "fused_trace_rows",
        "lookup_claim_rows",
        "multiplicity_table_rows",
        "source_arithmetic_rows_status",
        "logup_lookup_rows_status",
    }
    if not isinstance(component_rows, dict):
        raise FusedSoftmaxTableMicroprofileGateError("trace component rows must be object")
    if set(component_rows) != expected_component_row_keys:
        raise FusedSoftmaxTableMicroprofileGateError("trace component row field drift")
    if component_rows.get("fused_trace_rows") != row["trace_rows"]:
        raise FusedSoftmaxTableMicroprofileGateError("fused trace-row component drift")
    if component_rows.get("lookup_claim_rows") != row["lookup_claims"]:
        raise FusedSoftmaxTableMicroprofileGateError("lookup claim component drift")
    if component_rows.get("multiplicity_table_rows") != row["table_rows"]:
        raise FusedSoftmaxTableMicroprofileGateError("multiplicity table component drift")
    if component_rows["source_arithmetic_rows_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("source arithmetic row status drift")
    if component_rows["logup_lookup_rows_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("logup lookup row status drift")
    component_columns = row["trace_columns_by_component"]
    expected_column_keys = {
        "fused_trace_columns",
        "fused_trace_columns_status",
        "source_arithmetic_columns",
        "source_arithmetic_columns_status",
        "logup_lookup_columns",
        "logup_lookup_columns_status",
        "preprocessed_columns",
        "preprocessed_columns_status",
        "base_columns",
        "base_columns_status",
        "extension_columns",
        "extension_columns_status",
    }
    if not isinstance(component_columns, dict) or set(component_columns) != expected_column_keys:
        raise FusedSoftmaxTableMicroprofileGateError("trace column component field drift")
    for key in (
        "fused_trace_columns",
        "source_arithmetic_columns",
        "logup_lookup_columns",
        "preprocessed_columns",
        "base_columns",
        "extension_columns",
    ):
        if component_columns[key] is not None:
            raise FusedSoftmaxTableMicroprofileGateError("trace column component count overclaim")
    if component_columns["fused_trace_columns_status"] != COLUMN_BREAKDOWN_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("fused trace column status drift")
    if component_columns["source_arithmetic_columns_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("source arithmetic column status drift")
    if component_columns["logup_lookup_columns_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("logup lookup column status drift")
    for key in ("preprocessed_columns_status", "base_columns_status", "extension_columns_status"):
        if component_columns[key] != COLUMN_BREAKDOWN_STATUS:
            raise FusedSoftmaxTableMicroprofileGateError("backend column status drift")
    if row["backend_internal_split_status"] != BACKEND_INTERNAL_SPLIT_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("backend internal split status drift")
    if row["column_breakdown_status"] != COLUMN_BREAKDOWN_STATUS:
        raise FusedSoftmaxTableMicroprofileGateError("column breakdown status drift")
    require_str(row["evidence_json"], "evidence_json")
    require_str(row["fused_envelope_json"], "fused_envelope_json")


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    section_totals = {key: sum(row["proof_section_bytes"][key] for row in rows) for key in PROOF_SECTION_KEYS}
    bucket_totals = {
        "commitment_bucket_bytes": sum(row["proof_byte_buckets"]["commitment_bucket_bytes"] for row in rows),
        "query_bucket_bytes": sum(row["proof_byte_buckets"]["query_bucket_bytes"] for row in rows),
        "opening_bucket_bytes": sum(row["proof_byte_buckets"]["opening_bucket_bytes"] for row in rows),
        "config_and_pow_bytes": sum(row["proof_byte_buckets"]["config_and_pow_bytes"] for row in rows),
        "json_wrapper_bytes": sum(row["proof_byte_buckets"]["json_wrapper_bytes"] for row in rows),
    }
    largest = max(rows, key=lambda row: row["fused_proof_size_bytes"])
    aggregate = {
        "profiles_checked": len(rows),
        "total_lookup_claims": sum(row["lookup_claims"] for row in rows),
        "total_trace_rows": sum(row["trace_rows"] for row in rows),
        "total_table_rows": sum(row["table_rows"] for row in rows),
        "total_fused_proof_size_bytes": sum(row["fused_proof_size_bytes"] for row in rows),
        "total_source_plus_sidecar_raw_proof_bytes": sum(
            row["source_plus_sidecar_raw_proof_bytes"] for row in rows
        ),
        "total_fused_savings_vs_source_plus_sidecar_bytes": sum(
            row["source_plus_sidecar_raw_proof_bytes"] - row["fused_proof_size_bytes"] for row in rows
        ),
        "total_section_payload_bytes": sum(row["proof_section_payload_bytes_total"] for row in rows),
        "total_json_wrapper_bytes": sum(row["proof_json_wrapper_bytes"] for row in rows),
        "section_totals": section_totals,
        "bucket_totals": bucket_totals,
        "largest_profile_id": largest["profile_id"],
        "largest_profile_fused_proof_size_bytes": largest["fused_proof_size_bytes"],
        "proof_backend_versions": sorted({row["proof_backend_version"] for row in rows}),
        "exposed_relation_width_profiles": [
            row["profile_id"] for row in rows if row["lookup_relation_width_status"] == RELATION_WIDTH_STATUS_EXPOSED
        ],
        "missing_relation_width_profiles": [
            row["profile_id"] for row in rows if row["lookup_relation_width_status"] == RELATION_WIDTH_STATUS_INFERRED_MISSING
        ],
    }
    validate_aggregate(aggregate)
    return aggregate


def validate_aggregate(aggregate: Any) -> None:
    if not isinstance(aggregate, dict):
        raise FusedSoftmaxTableMicroprofileGateError("aggregate must be object")
    expected_keys = {
        "profiles_checked",
        "total_lookup_claims",
        "total_trace_rows",
        "total_table_rows",
        "total_fused_proof_size_bytes",
        "total_source_plus_sidecar_raw_proof_bytes",
        "total_fused_savings_vs_source_plus_sidecar_bytes",
        "total_section_payload_bytes",
        "total_json_wrapper_bytes",
        "section_totals",
        "bucket_totals",
        "largest_profile_id",
        "largest_profile_fused_proof_size_bytes",
        "proof_backend_versions",
        "exposed_relation_width_profiles",
        "missing_relation_width_profiles",
    }
    if set(aggregate) != expected_keys:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate field drift")
    if aggregate["profiles_checked"] != len(EXPECTED_PROFILE_IDS):
        raise FusedSoftmaxTableMicroprofileGateError("profile count drift")
    if aggregate["total_lookup_claims"] != EXPECTED_TOTAL_LOOKUP_CLAIMS:
        raise FusedSoftmaxTableMicroprofileGateError("lookup-claim total drift")
    if aggregate["total_trace_rows"] != EXPECTED_TOTAL_TRACE_ROWS:
        raise FusedSoftmaxTableMicroprofileGateError("trace-row total drift")
    if aggregate["total_fused_proof_size_bytes"] != EXPECTED_TOTAL_FUSED_PROOF_BYTES:
        raise FusedSoftmaxTableMicroprofileGateError("fused-proof total drift")
    if aggregate["total_source_plus_sidecar_raw_proof_bytes"] != EXPECTED_TOTAL_SOURCE_PLUS_SIDECAR_BYTES:
        raise FusedSoftmaxTableMicroprofileGateError("source-plus-sidecar total drift")
    if aggregate["total_fused_savings_vs_source_plus_sidecar_bytes"] != EXPECTED_TOTAL_FUSED_SAVINGS_BYTES:
        raise FusedSoftmaxTableMicroprofileGateError("fused savings total drift")
    if aggregate["total_section_payload_bytes"] != EXPECTED_TOTAL_SECTION_PAYLOAD_BYTES:
        raise FusedSoftmaxTableMicroprofileGateError("section-payload total drift")
    if aggregate["total_json_wrapper_bytes"] != EXPECTED_TOTAL_WRAPPER_BYTES:
        raise FusedSoftmaxTableMicroprofileGateError("wrapper total drift")
    if aggregate["largest_profile_id"] != EXPECTED_LARGEST_PROFILE_ID:
        raise FusedSoftmaxTableMicroprofileGateError("largest profile drift")
    if aggregate["largest_profile_fused_proof_size_bytes"] != EXPECTED_LARGEST_PROFILE_PROOF_BYTES:
        raise FusedSoftmaxTableMicroprofileGateError("largest profile bytes drift")
    if not isinstance(aggregate["proof_backend_versions"], list) or not aggregate["proof_backend_versions"]:
        raise FusedSoftmaxTableMicroprofileGateError("proof backend version inventory drift")
    for version in aggregate["proof_backend_versions"]:
        require_str(version, "proof_backend_version")
    if tuple(aggregate["exposed_relation_width_profiles"]) != EXPECTED_EXPOSED_RELATION_WIDTH_PROFILES:
        raise FusedSoftmaxTableMicroprofileGateError("exposed relation-width profile drift")
    if tuple(aggregate["missing_relation_width_profiles"]) != EXPECTED_MISSING_RELATION_WIDTH_PROFILES:
        raise FusedSoftmaxTableMicroprofileGateError("missing relation-width profile drift")
    section_totals = aggregate["section_totals"]
    if not isinstance(section_totals, dict) or set(section_totals) != set(PROOF_SECTION_KEYS):
        raise FusedSoftmaxTableMicroprofileGateError("section total field drift")
    if sum(section_totals.values()) != aggregate["total_section_payload_bytes"]:
        raise FusedSoftmaxTableMicroprofileGateError("section total sum drift")
    buckets = aggregate["bucket_totals"]
    expected_bucket_keys = {
        "commitment_bucket_bytes",
        "query_bucket_bytes",
        "opening_bucket_bytes",
        "config_and_pow_bytes",
        "json_wrapper_bytes",
    }
    if not isinstance(buckets, dict) or set(buckets) != expected_bucket_keys:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate bucket total field drift")
    if buckets["commitment_bucket_bytes"] != section_totals["commitments"]:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate commitment bucket drift")
    if buckets["query_bucket_bytes"] != section_totals["sampled_values"] + section_totals["queried_values"]:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate query bucket drift")
    if buckets["opening_bucket_bytes"] != section_totals["decommitments"] + section_totals["fri_proof"]:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate opening bucket drift")
    if buckets["config_and_pow_bytes"] != section_totals["config"] + section_totals["proof_of_work"]:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate config-and-pow bucket drift")
    if buckets["json_wrapper_bytes"] != aggregate["total_json_wrapper_bytes"]:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate JSON wrapper bucket drift")
    if aggregate["total_section_payload_bytes"] + aggregate["total_json_wrapper_bytes"] != aggregate[
        "total_fused_proof_size_bytes"
    ]:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate proof-byte accounting drift")


def build_base_payload() -> dict[str, Any]:
    rows = [build_microprofile_row(profile) for profile in matrix.PROFILES]
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "proof_object_scope": PROOF_OBJECT_SCOPE,
        "proof_bucket_status": PROOF_BUCKET_STATUS,
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
        "column_breakdown_status": COLUMN_BREAKDOWN_STATUS,
        "timing_policy": TIMING_POLICY,
        "profile_ids": list(EXPECTED_PROFILE_IDS),
        "profile_rows": rows,
        "aggregate": build_aggregate(rows),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["microprofile_commitment"] = microprofile_commitment(payload)
    validate_payload(payload, allow_missing_mutation_summary=True, expected_rows=rows)
    return payload


def microprofile_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "schema": payload["schema"],
            "issue": payload["issue"],
            "source_issue": payload["source_issue"],
            "decision": payload["decision"],
            "route_id": payload["route_id"],
            "claim_boundary": payload["claim_boundary"],
            "proof_object_scope": payload["proof_object_scope"],
            "proof_bucket_status": payload["proof_bucket_status"],
            "backend_internal_split_status": payload["backend_internal_split_status"],
            "column_breakdown_status": payload["column_breakdown_status"],
            "timing_policy": payload["timing_policy"],
            "profile_ids": payload["profile_ids"],
            "profile_rows": payload["profile_rows"],
            "aggregate": payload["aggregate"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-fused-softmax-table-microprofile:v1",
    )


def build_payload() -> dict[str, Any]:
    payload = build_base_payload()
    cases = mutation_cases_for(payload, expected_rows=payload["profile_rows"])
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"] is True)
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def strip_mutations(payload: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        out.pop(key, None)
    return out


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    out = strip_mutations(payload)
    if name == "decision_relabeling":
        out["decision"] = "GO_PUBLIC_BENCHMARK"
    elif name == "claim_boundary_overclaim":
        out["claim_boundary"] = "GO_BINARY_PCS_FRI_INTERNAL_ACCOUNTING"
    elif name == "timing_policy_overclaim":
        out["timing_policy"] = "median_of_5_public_benchmark"
    elif name == "proof_bucket_status_overclaim":
        out["proof_bucket_status"] = "GO_BINARY_PCS_FRI_BUCKETS_EXTRACTED"
    elif name == "backend_internal_split_overclaim":
        out["backend_internal_split_status"] = "GO_SOURCE_ARITHMETIC_VS_LOOKUP_SPLIT_EXPOSED"
    elif name == "column_breakdown_overclaim":
        out["column_breakdown_status"] = "GO_BASE_AND_EXTENSION_COLUMNS_EXPOSED"
    elif name == "route_row_order_drift":
        out["profile_rows"] = list(reversed(out["profile_rows"]))
    elif name == "profile_id_relabeling":
        out["profile_rows"][0]["profile_id"] = "different"
    elif name == "lookup_relation_width_smuggling":
        row = next(row for row in out["profile_rows"] if row["lookup_relation_width"] is None)
        row["lookup_relation_width"] = 2
        row["lookup_relation_width_status"] = RELATION_WIDTH_STATUS_EXPOSED
    elif name == "fused_proof_size_smuggling":
        out["profile_rows"][0]["fused_proof_size_bytes"] += 1
    elif name == "proof_section_bucket_smuggling":
        out["profile_rows"][0]["proof_section_bytes"]["fri_proof"] += 1
    elif name == "query_bucket_smuggling":
        out["profile_rows"][0]["proof_byte_buckets"]["query_bucket_bytes"] += 1
    elif name == "opening_bucket_smuggling":
        out["profile_rows"][0]["proof_byte_buckets"]["opening_bucket_bytes"] += 1
    elif name == "trace_column_count_smuggling":
        out["profile_rows"][0]["trace_columns_by_component"]["fused_trace_columns"] = 12
    elif name == "aggregate_total_smuggling":
        out["aggregate"]["total_fused_proof_size_bytes"] += 1
    elif name == "largest_profile_smuggling":
        out["aggregate"]["largest_profile_id"] = "d8_single_head_seq8"
    elif name == "non_claim_removed":
        out["non_claims"] = out["non_claims"][:-1]
    elif name == "unknown_field_injection":
        out["unexpected"] = True
    else:
        raise FusedSoftmaxTableMicroprofileGateError(f"unknown mutation: {name}")
    return out


def mutation_cases_for(payload: dict[str, Any], *, expected_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    validate_mutation_spec()
    if expected_rows is None:
        expected_rows = payload["profile_rows"]
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True, expected_rows=expected_rows)
        except FusedSoftmaxTableMicroprofileGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "accepted mutated payload"})
    return cases


def profile_row_ids(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        raise FusedSoftmaxTableMicroprofileGateError("profile rows must be list")
    ids = []
    for row in rows:
        if not isinstance(row, dict):
            raise FusedSoftmaxTableMicroprofileGateError("profile row must be object")
        ids.append(row.get("profile_id"))
    return ids


def mutation_case_names(cases: Any) -> list[str]:
    if not isinstance(cases, list):
        raise FusedSoftmaxTableMicroprofileGateError("mutation cases must be list")
    names = []
    for case in cases:
        if not isinstance(case, dict):
            raise FusedSoftmaxTableMicroprofileGateError("mutation case must be object")
        names.append(case.get("name"))
    return names


def validate_payload(
    payload: Any,
    *,
    allow_missing_mutation_summary: bool = False,
    expected_rows: list[dict[str, Any]] | None = None,
) -> None:
    validate_mutation_spec()
    if not isinstance(payload, dict):
        raise FusedSoftmaxTableMicroprofileGateError("payload must be object")
    allowed = {
        "schema",
        "issue",
        "source_issue",
        "decision",
        "route_id",
        "claim_boundary",
        "proof_object_scope",
        "proof_bucket_status",
        "backend_internal_split_status",
        "column_breakdown_status",
        "timing_policy",
        "profile_ids",
        "profile_rows",
        "aggregate",
        "non_claims",
        "validation_commands",
        "microprofile_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    }
    if set(payload) - allowed:
        raise FusedSoftmaxTableMicroprofileGateError("unknown field")
    expected_scalars = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "proof_object_scope": PROOF_OBJECT_SCOPE,
        "proof_bucket_status": PROOF_BUCKET_STATUS,
        "backend_internal_split_status": BACKEND_INTERNAL_SPLIT_STATUS,
        "column_breakdown_status": COLUMN_BREAKDOWN_STATUS,
        "timing_policy": TIMING_POLICY,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            raise FusedSoftmaxTableMicroprofileGateError(f"{key} drift")
    if tuple(payload.get("profile_ids") or ()) != EXPECTED_PROFILE_IDS:
        raise FusedSoftmaxTableMicroprofileGateError("profile id inventory drift")
    rows = payload.get("profile_rows")
    if profile_row_ids(rows) != list(EXPECTED_PROFILE_IDS):
        raise FusedSoftmaxTableMicroprofileGateError("profile row order drift")
    for row in rows:
        validate_microprofile_row(row)
    if expected_rows is None:
        expected_rows = [build_microprofile_row(profile) for profile in matrix.PROFILES]
    if rows != expected_rows:
        raise FusedSoftmaxTableMicroprofileGateError("microprofile row drift against source artifacts")
    validate_aggregate(payload.get("aggregate"))
    recomputed_aggregate = build_aggregate(rows)
    if payload["aggregate"] != recomputed_aggregate:
        raise FusedSoftmaxTableMicroprofileGateError("aggregate recomputation drift")
    if tuple(payload.get("non_claims") or ()) != NON_CLAIMS:
        raise FusedSoftmaxTableMicroprofileGateError("non-claim drift")
    if tuple(payload.get("validation_commands") or ()) != VALIDATION_COMMANDS:
        raise FusedSoftmaxTableMicroprofileGateError("validation command drift")
    if payload.get("microprofile_commitment") != microprofile_commitment(payload):
        raise FusedSoftmaxTableMicroprofileGateError("microprofile commitment drift")
    if allow_missing_mutation_summary:
        return
    cases = payload.get("mutation_cases")
    if mutation_case_names(cases) != list(EXPECTED_MUTATION_NAMES):
        raise FusedSoftmaxTableMicroprofileGateError("mutation case inventory drift")
    if any(case.get("rejected") is not True for case in cases):
        raise FusedSoftmaxTableMicroprofileGateError("mutation rejection drift")
    if payload.get("mutations_checked") != EXPECTED_MUTATION_COUNT:
        raise FusedSoftmaxTableMicroprofileGateError("mutation checked count drift")
    if payload.get("mutations_rejected") != EXPECTED_MUTATION_COUNT:
        raise FusedSoftmaxTableMicroprofileGateError("mutation rejected count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise FusedSoftmaxTableMicroprofileGateError("mutation fail-closed drift")


def validate_mutation_spec() -> None:
    if len(EXPECTED_MUTATION_NAMES) != EXPECTED_MUTATION_COUNT:
        raise FusedSoftmaxTableMicroprofileGateError("mutation spec count drift")
    if len(set(EXPECTED_MUTATION_NAMES)) != len(EXPECTED_MUTATION_NAMES):
        raise FusedSoftmaxTableMicroprofileGateError("duplicate mutation name")


def tsv_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def tsv_row_projection(row: dict[str, Any]) -> dict[str, str]:
    return {
        "profile_id": tsv_value(row["profile_id"]),
        "axis_role": tsv_value(row["axis_role"]),
        "key_width": tsv_value(row["key_width"]),
        "value_width": tsv_value(row["value_width"]),
        "head_count": tsv_value(row["head_count"]),
        "steps_per_head": tsv_value(row["steps_per_head"]),
        "lookup_claims": tsv_value(row["lookup_claims"]),
        "trace_rows": tsv_value(row["trace_rows"]),
        "table_rows": tsv_value(row["table_rows"]),
        "lookup_relation_width": tsv_value(row["lookup_relation_width"]),
        "lookup_relation_width_status": tsv_value(row["lookup_relation_width_status"]),
        "fused_proof_size_bytes": tsv_value(row["fused_proof_size_bytes"]),
        "proof_section_payload_bytes_total": tsv_value(row["proof_section_payload_bytes_total"]),
        "proof_json_wrapper_bytes": tsv_value(row["proof_json_wrapper_bytes"]),
        "config_bytes": tsv_value(row["proof_section_bytes"]["config"]),
        "commitments_bytes": tsv_value(row["proof_section_bytes"]["commitments"]),
        "sampled_values_bytes": tsv_value(row["proof_section_bytes"]["sampled_values"]),
        "decommitments_bytes": tsv_value(row["proof_section_bytes"]["decommitments"]),
        "queried_values_bytes": tsv_value(row["proof_section_bytes"]["queried_values"]),
        "proof_of_work_bytes": tsv_value(row["proof_section_bytes"]["proof_of_work"]),
        "fri_proof_bytes": tsv_value(row["proof_section_bytes"]["fri_proof"]),
        "commitment_bucket_bytes": tsv_value(row["proof_byte_buckets"]["commitment_bucket_bytes"]),
        "query_bucket_bytes": tsv_value(row["proof_byte_buckets"]["query_bucket_bytes"]),
        "opening_bucket_bytes": tsv_value(row["proof_byte_buckets"]["opening_bucket_bytes"]),
        "backend_internal_split_status": tsv_value(row["backend_internal_split_status"]),
    }


def to_tsv(payload: dict[str, Any], *, validate: bool = True, expected_rows: list[dict[str, Any]] | None = None) -> str:
    if validate:
        validate_payload(payload, expected_rows=expected_rows)
    rows = []
    writer = csv.DictWriter(_ListWriter(rows), fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in payload["profile_rows"]:
        writer.writerow(tsv_row_projection(row))
    return "".join(rows)


class _ListWriter:
    def __init__(self, rows: list[str]) -> None:
        self.rows = rows

    def write(self, value: str) -> int:
        self.rows.append(value)
        return len(value)


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        tmp = pathlib.Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    try:
        loaded = json.loads(tmp.read_text(encoding="utf-8"))
        validate_payload(loaded, expected_rows=payload["profile_rows"])
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    validate_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = to_tsv(payload, validate=False)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        tmp = pathlib.Path(handle.name)
        handle.write(text)
    try:
        reader = csv.DictReader(tmp.read_text(encoding="utf-8").splitlines(), delimiter="\t")
        if reader.fieldnames != list(TSV_COLUMNS):
            raise FusedSoftmaxTableMicroprofileGateError("TSV header drift")
        loaded_rows = list(reader)
        expected_rows = [tsv_row_projection(row) for row in payload["profile_rows"]]
        if len(loaded_rows) != len(expected_rows):
            raise FusedSoftmaxTableMicroprofileGateError("TSV row count drift")
        if loaded_rows != expected_rows:
            raise FusedSoftmaxTableMicroprofileGateError("TSV row projection drift")
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def staged_output_path(path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.staged.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        return pathlib.Path(handle.name)


def backup_output_path(path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.parent / f".{path.name}.backup.{uuid.uuid4().hex}.tmp"


def require_evidence_output_path(path: pathlib.Path, label: str) -> pathlib.Path:
    resolved = path.expanduser().resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    try:
        resolved.relative_to(evidence_root)
    except ValueError as exc:
        raise FusedSoftmaxTableMicroprofileGateError(f"{label} must stay under {evidence_root}") from exc
    return resolved


def replace_staged_outputs_with_rollback(
    staged_json: pathlib.Path,
    json_path: pathlib.Path,
    staged_tsv: pathlib.Path,
    tsv_path: pathlib.Path,
) -> None:
    backup_json: pathlib.Path | None = None
    backup_tsv: pathlib.Path | None = None
    json_replaced = False
    tsv_replaced = False
    try:
        if json_path.exists():
            backup_json = backup_output_path(json_path)
            json_path.replace(backup_json)
        if tsv_path.exists():
            backup_tsv = backup_output_path(tsv_path)
            tsv_path.replace(backup_tsv)

        staged_json.replace(json_path)
        json_replaced = True
        staged_tsv.replace(tsv_path)
        tsv_replaced = True
    except Exception:
        if json_replaced:
            json_path.unlink(missing_ok=True)
        if tsv_replaced:
            tsv_path.unlink(missing_ok=True)
        if backup_json is not None and backup_json.exists():
            backup_json.replace(json_path)
        if backup_tsv is not None and backup_tsv.exists():
            backup_tsv.replace(tsv_path)
        raise
    else:
        if backup_json is not None:
            backup_json.unlink(missing_ok=True)
        if backup_tsv is not None:
            backup_tsv.unlink(missing_ok=True)


def write_outputs_atomically(json_path: pathlib.Path, tsv_path: pathlib.Path, payload: dict[str, Any]) -> None:
    if json_path == tsv_path:
        raise FusedSoftmaxTableMicroprofileGateError("JSON and TSV output paths must differ")
    staged_json = staged_output_path(json_path)
    staged_tsv = staged_output_path(tsv_path)
    staged_json.unlink(missing_ok=True)
    staged_tsv.unlink(missing_ok=True)
    try:
        write_json(staged_json, payload)
        write_tsv(staged_tsv, payload)
        replace_staged_outputs_with_rollback(staged_json, json_path, staged_tsv, tsv_path)
    except Exception:
        staged_json.unlink(missing_ok=True)
        staged_tsv.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_json_path = require_evidence_output_path(args.write_json, "write-json")
        write_tsv_path = require_evidence_output_path(args.write_tsv, "write-tsv")
        write_outputs_atomically(write_json_path, write_tsv_path, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
