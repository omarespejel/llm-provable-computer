#!/usr/bin/env python3
"""Controlled Stwo component grid for fused attention/table proof objects.

This gate is deliberately derived from already checked artifacts. It does not
generate new proofs and it does not claim a full factorial benchmark. Its job is
to answer a narrower question: does the fine-grained typed-component saving from
fusing attention arithmetic with Softmax-table LogUp membership hold across the
checked width, head-count, sequence, and combined-axis controls?
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
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_fused_softmax_table_route_matrix_gate as matrix
from scripts import zkai_attention_kv_stwo_fine_grained_component_schema_gate as components

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-controlled-component-grid-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-controlled-component-grid-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-controlled-component-grid-v1"
ISSUE = 536
SOURCE_ISSUES = (505, 531, 534)
DECISION = "GO_CHECKED_STWO_COMPONENT_GRID_WITH_FULL_FACTORIAL_GRID_NO_GO"
ROUTE_ID = "local_stwo_attention_kv_controlled_component_grid"
GRID_STATUS = "GO_NINE_PROFILE_CONTROLLED_COMPONENT_GRID_FROM_CHECKED_STWO_ARTIFACTS"
FULL_FACTORIAL_GRID_STATUS = "NO_GO_NO_SEQ32_OR_D32_PROOF_ARTIFACTS_IN_THIS_GATE"
CLAIM_BOUNDARY = (
    "ENGINEERING_TYPED_COMPONENT_GRID_FOR_NINE_CHECKED_NATIVE_STWO_FUSED_SOFTMAX_TABLE_PROFILES_"
    "WIDTH_HEAD_SEQUENCE_AND_COMBINED_AXIS_CONTROLS_NOT_FULL_FACTORIAL_GRID_NOT_TIMING_"
    "NOT_STABLE_BINARY_SERIALIZATION_NOT_EXACT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE"
)
TIMING_POLICY = "proof_component_size_accounting_only_not_timing_not_public_benchmark"
COMPONENT_SCHEMA_STATUS = components.COMPONENT_SCHEMA_STATUS
STABLE_BINARY_SERIALIZER_STATUS = components.STABLE_BINARY_SERIALIZER_STATUS
NON_CLAIMS = (
    "not a full factorial d8/d16/d32 by 1/2/4/8/16 heads by seq8/seq16/seq32 grid",
    "not stable canonical binary Stwo proof serialization",
    "not verifier-facing binary proof bytes",
    "not backend-internal source arithmetic versus LogUp lookup column attribution",
    "not timing evidence",
    "not exact real-valued Softmax",
    "not implementation-exact model Softmax",
    "not full inference",
    "not recursion or PCD",
)
MISSING_CONTROLS = (
    "seq32 fused/source/sidecar proof artifacts",
    "d32 fused/source/sidecar proof artifacts",
    "full factorial crossing of width, head count, and sequence length",
    "publication-grade timing repetitions",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_controlled_component_grid_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_controlled_component_grid_gate",
    "python3 scripts/zkai_attention_kv_stwo_fine_grained_component_schema_gate.py --no-write",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "profile_id",
    "axis_role",
    "key_width",
    "value_width",
    "head_count",
    "steps_per_head",
    "lookup_claims",
    "trace_rows",
    "source_plus_sidecar_typed_size_bytes",
    "fused_typed_size_bytes",
    "typed_savings_bytes",
    "typed_saving_share",
    "source_plus_sidecar_json_proof_size_bytes",
    "fused_json_proof_size_bytes",
    "json_savings_bytes",
    "json_saving_share",
    "dominant_component_saving_bucket",
    "dominant_component_saving_bytes",
    "fri_trace_merkle_path_savings_bytes",
    "opening_plumbing_savings_bytes",
)
EXPECTED_PROFILE_SAVINGS = {
    "d8_single_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 21_400,
        "fused_typed_size_bytes": 18_124,
        "typed_savings_bytes": 3_276,
        "typed_saving_share": 0.153084,
        "source_plus_sidecar_json_proof_size_bytes": 59_437,
        "fused_json_proof_size_bytes": 47_698,
        "json_savings_bytes": 11_739,
        "json_saving_share": 0.197503,
        "dominant_component_saving_bucket": "trace_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 1_408,
        "fri_trace_merkle_path_savings_bytes": 2_432,
        "opening_plumbing_savings_bytes": 2_720,
    },
    "d16_single_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 31_768,
        "fused_typed_size_bytes": 28_876,
        "typed_savings_bytes": 2_892,
        "typed_saving_share": 0.091035,
        "source_plus_sidecar_json_proof_size_bytes": 74_961,
        "fused_json_proof_size_bytes": 64_503,
        "json_savings_bytes": 10_458,
        "json_saving_share": 0.139513,
        "dominant_component_saving_bucket": "trace_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 1_152,
        "fri_trace_merkle_path_savings_bytes": 2_080,
        "opening_plumbing_savings_bytes": 2_368,
    },
    "d8_two_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 22_832,
        "fused_typed_size_bytes": 18_436,
        "typed_savings_bytes": 4_396,
        "typed_saving_share": 0.192537,
        "source_plus_sidecar_json_proof_size_bytes": 65_208,
        "fused_json_proof_size_bytes": 49_508,
        "json_savings_bytes": 15_700,
        "json_saving_share": 0.240768,
        "dominant_component_saving_bucket": "trace_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 1_888,
        "fri_trace_merkle_path_savings_bytes": 3_456,
        "opening_plumbing_savings_bytes": 3_776,
    },
    "d8_four_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 25_296,
        "fused_typed_size_bytes": 19_412,
        "typed_savings_bytes": 5_884,
        "typed_saving_share": 0.232606,
        "source_plus_sidecar_json_proof_size_bytes": 74_529,
        "fused_json_proof_size_bytes": 53_468,
        "json_savings_bytes": 21_061,
        "json_saving_share": 0.282588,
        "dominant_component_saving_bucket": "fri_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 2_464,
        "fri_trace_merkle_path_savings_bytes": 4_832,
        "opening_plumbing_savings_bytes": 5_184,
    },
    "d8_eight_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 25_136,
        "fused_typed_size_bytes": 21_060,
        "typed_savings_bytes": 4_076,
        "typed_saving_share": 0.162158,
        "source_plus_sidecar_json_proof_size_bytes": 74_086,
        "fused_json_proof_size_bytes": 59_375,
        "json_savings_bytes": 14_711,
        "json_saving_share": 0.198567,
        "dominant_component_saving_bucket": "fri_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 1_632,
        "fri_trace_merkle_path_savings_bytes": 3_136,
        "opening_plumbing_savings_bytes": 3_520,
    },
    "d8_sixteen_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 29_264,
        "fused_typed_size_bytes": 22_660,
        "typed_savings_bytes": 6_604,
        "typed_saving_share": 0.22567,
        "source_plus_sidecar_json_proof_size_bytes": 88_711,
        "fused_json_proof_size_bytes": 65_006,
        "json_savings_bytes": 23_705,
        "json_saving_share": 0.267216,
        "dominant_component_saving_bucket": "fri_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 3_168,
        "fri_trace_merkle_path_savings_bytes": 5_472,
        "opening_plumbing_savings_bytes": 5_888,
    },
    "d8_two_head_seq16": {
        "source_plus_sidecar_typed_size_bytes": 26_640,
        "fused_typed_size_bytes": 21_396,
        "typed_savings_bytes": 5_244,
        "typed_saving_share": 0.196847,
        "source_plus_sidecar_json_proof_size_bytes": 79_444,
        "fused_json_proof_size_bytes": 60_502,
        "json_savings_bytes": 18_942,
        "json_saving_share": 0.238432,
        "dominant_component_saving_bucket": "fri_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 2_304,
        "fri_trace_merkle_path_savings_bytes": 4_224,
        "opening_plumbing_savings_bytes": 4_608,
    },
    "d16_two_head_seq8": {
        "source_plus_sidecar_typed_size_bytes": 33_584,
        "fused_typed_size_bytes": 29_908,
        "typed_savings_bytes": 3_676,
        "typed_saving_share": 0.109457,
        "source_plus_sidecar_json_proof_size_bytes": 91_596,
        "fused_json_proof_size_bytes": 78_211,
        "json_savings_bytes": 13_385,
        "json_saving_share": 0.146131,
        "dominant_component_saving_bucket": "trace_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 1_504,
        "fri_trace_merkle_path_savings_bytes": 2_784,
        "opening_plumbing_savings_bytes": 3_104,
    },
    "d16_two_head_seq16": {
        "source_plus_sidecar_typed_size_bytes": 37_952,
        "fused_typed_size_bytes": 31_508,
        "typed_savings_bytes": 6_444,
        "typed_saving_share": 0.169793,
        "source_plus_sidecar_json_proof_size_bytes": 108_158,
        "fused_json_proof_size_bytes": 84_868,
        "json_savings_bytes": 23_290,
        "json_saving_share": 0.215333,
        "dominant_component_saving_bucket": "fri_decommitment_merkle_path_bytes",
        "dominant_component_saving_bytes": 2_944,
        "fri_trace_merkle_path_savings_bytes": 5_344,
        "opening_plumbing_savings_bytes": 5_728,
    },
}
EXPECTED_AGGREGATE = {
    "profiles_checked": 9,
    "all_profiles_save_typed_components": True,
    "source_plus_sidecar_typed_size_bytes_total": 253_872,
    "fused_typed_size_bytes_total": 211_380,
    "typed_savings_bytes_total": 42_492,
    "typed_saving_share_total": 0.167376,
    "min_typed_saving_share": 0.091035,
    "max_typed_saving_share": 0.232606,
    "mean_typed_saving_share": 0.170354,
    "source_plus_sidecar_json_proof_size_bytes_total": 716_130,
    "fused_json_proof_size_bytes_total": 563_139,
    "json_savings_bytes_total": 152_991,
    "json_saving_share_total": 0.213636,
    "min_json_saving_share": 0.139513,
    "max_json_saving_share": 0.282588,
    "mean_json_saving_share": 0.214006,
    "fri_trace_merkle_path_savings_bytes_total": 33_760,
    "fri_trace_merkle_path_share_of_typed_savings": 0.794502,
    "opening_plumbing_savings_bytes_total": 36_896,
    "opening_plumbing_share_of_typed_savings": 0.868305,
    "largest_component_saving_bucket": "fri_decommitment_merkle_path_bytes",
    "largest_component_saving_bucket_bytes": 17_312,
}
EXPECTED_AXIS_SUMMARY = {
    "head_axis_d8_seq8": {
        "profile_ids": [
            "d8_single_head_seq8",
            "d8_two_head_seq8",
            "d8_four_head_seq8",
            "d8_eight_head_seq8",
            "d8_sixteen_head_seq8",
        ],
        "head_counts": [1, 2, 4, 8, 16],
        "typed_saving_shares": [0.153084, 0.192537, 0.232606, 0.162158, 0.22567],
        "min_typed_saving_share": 0.153084,
        "max_typed_saving_share": 0.232606,
        "mean_typed_saving_share": 0.193211,
    },
    "sequence_axis_d8_two_head": {
        "profile_ids": ["d8_two_head_seq8", "d8_two_head_seq16"],
        "steps_per_head": [8, 16],
        "typed_saving_shares": [0.192537, 0.196847],
        "mean_typed_saving_share": 0.194692,
    },
    "width_axis_single_head_seq8": {
        "profile_ids": ["d8_single_head_seq8", "d16_single_head_seq8"],
        "key_widths": [8, 16],
        "typed_saving_shares": [0.153084, 0.091035],
        "mean_typed_saving_share": 0.12206,
    },
    "combined_width_head_sequence_axis": {
        "profile_ids": ["d16_two_head_seq8", "d16_two_head_seq16"],
        "typed_saving_shares": [0.109457, 0.169793],
        "mean_typed_saving_share": 0.139625,
    },
}
EXPECTED_COMPONENT_GRID_COMMITMENT = "blake2b-256:36f1d66e2371d4b51233e915b01bf0b1502c25246e2c585b3fdedc7d9f5e129f"
EXPECTED_MUTATION_NAMES = (
    "decision_overclaim",
    "grid_status_overclaim",
    "full_factorial_status_overclaim",
    "missing_controls_removed",
    "binary_serializer_overclaim",
    "component_schema_status_overclaim",
    "profile_order_drift",
    "profile_relabeling",
    "typed_savings_smuggling",
    "component_delta_smuggling",
    "aggregate_share_smuggling",
    "axis_summary_smuggling",
    "all_profiles_save_flag_smuggling",
    "upstream_commitment_smuggling",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)


class StwoControlledComponentGridGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        raise StwoControlledComponentGridGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def mean(values: list[float]) -> float:
    if not values:
        raise StwoControlledComponentGridGateError("mean requires at least one value")
    return round(sum(values) / len(values), 6)


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StwoControlledComponentGridGateError(f"{label} must be an integer")
    return value


def read_checked_fine_grained_payload() -> dict[str, Any]:
    payload = json.loads(components.JSON_OUT.read_text(encoding="utf-8"))
    components.validate_payload(payload, expected_rows=payload["rows"])
    return payload


def read_checked_route_matrix() -> dict[str, Any]:
    result = matrix.build_result()
    matrix.validate_result(result)
    return result


def row_by_role(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = {}
    for row in payload["rows"]:
        rows[(row["profile_id"], row["role"])] = row
    expected_pairs = {(profile_id, role) for profile_id in matrix.PROFILE_IDS for role in components.ROLES}
    if set(rows) != expected_pairs:
        raise StwoControlledComponentGridGateError("fine-grained row pair drift")
    return rows


def component_delta(source: dict[str, Any], sidecar: dict[str, Any], fused: dict[str, Any]) -> dict[str, int]:
    delta = {}
    for bucket in components.COMPONENT_BUCKETS:
        value = (
            source["component_bytes"][bucket]
            + sidecar["component_bytes"][bucket]
            - fused["component_bytes"][bucket]
        )
        if value < 0:
            raise StwoControlledComponentGridGateError(f"negative component saving for {bucket}")
        delta[bucket] = value
    return delta


def build_grid_row(route_row: dict[str, Any], rows: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    profile_id = route_row["profile_id"]
    source = rows[(profile_id, "source")]
    sidecar = rows[(profile_id, "sidecar")]
    fused = rows[(profile_id, "fused")]
    source_plus_sidecar_typed = source["typed_size_estimate_bytes"] + sidecar["typed_size_estimate_bytes"]
    source_plus_sidecar_json = source["json_proof_size_bytes"] + sidecar["json_proof_size_bytes"]
    typed_savings = source_plus_sidecar_typed - fused["typed_size_estimate_bytes"]
    json_savings = source_plus_sidecar_json - fused["json_proof_size_bytes"]
    if typed_savings <= 0 or json_savings <= 0:
        raise StwoControlledComponentGridGateError(f"{profile_id} fused route does not save bytes")
    delta = component_delta(source, sidecar, fused)
    dominant = max(components.COMPONENT_BUCKETS, key=lambda key: delta[key])
    fri_trace_merkle_path_savings = (
        delta["fri_decommitment_merkle_path_bytes"]
        + delta["trace_decommitment_merkle_path_bytes"]
    )
    opening_plumbing_savings = (
        fri_trace_merkle_path_savings
        + delta["fri_commitment_bytes"]
        + delta["trace_commitment_bytes"]
    )
    row = {
        "profile_id": profile_id,
        "axis_role": route_row["axis_role"],
        "key_width": route_row["key_width"],
        "value_width": route_row["value_width"],
        "head_count": route_row["head_count"],
        "steps_per_head": route_row["steps_per_head"],
        "lookup_claims": route_row["lookup_claims"],
        "trace_rows": route_row["trace_rows"],
        "source_plus_sidecar_typed_size_bytes": source_plus_sidecar_typed,
        "fused_typed_size_bytes": fused["typed_size_estimate_bytes"],
        "typed_savings_bytes": typed_savings,
        "typed_saving_share": ratio(typed_savings, source_plus_sidecar_typed),
        "source_plus_sidecar_json_proof_size_bytes": source_plus_sidecar_json,
        "fused_json_proof_size_bytes": fused["json_proof_size_bytes"],
        "json_savings_bytes": json_savings,
        "json_saving_share": ratio(json_savings, source_plus_sidecar_json),
        "component_savings_bytes": delta,
        "dominant_component_saving_bucket": dominant,
        "dominant_component_saving_bytes": delta[dominant],
        "fri_trace_merkle_path_savings_bytes": fri_trace_merkle_path_savings,
        "opening_plumbing_savings_bytes": opening_plumbing_savings,
    }
    validate_grid_row(row)
    return row


def validate_grid_row(row: Any) -> None:
    expected = {
        "profile_id",
        "axis_role",
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "lookup_claims",
        "trace_rows",
        "source_plus_sidecar_typed_size_bytes",
        "fused_typed_size_bytes",
        "typed_savings_bytes",
        "typed_saving_share",
        "source_plus_sidecar_json_proof_size_bytes",
        "fused_json_proof_size_bytes",
        "json_savings_bytes",
        "json_saving_share",
        "component_savings_bytes",
        "dominant_component_saving_bucket",
        "dominant_component_saving_bytes",
        "fri_trace_merkle_path_savings_bytes",
        "opening_plumbing_savings_bytes",
    }
    if not isinstance(row, dict) or set(row) != expected:
        raise StwoControlledComponentGridGateError("grid row field drift")
    profile_id = row["profile_id"]
    if profile_id not in EXPECTED_PROFILE_SAVINGS:
        raise StwoControlledComponentGridGateError("profile_id drift")
    for key in (
        "key_width",
        "value_width",
        "head_count",
        "steps_per_head",
        "lookup_claims",
        "trace_rows",
        "source_plus_sidecar_typed_size_bytes",
        "fused_typed_size_bytes",
        "typed_savings_bytes",
        "source_plus_sidecar_json_proof_size_bytes",
        "fused_json_proof_size_bytes",
        "json_savings_bytes",
        "dominant_component_saving_bytes",
        "fri_trace_merkle_path_savings_bytes",
        "opening_plumbing_savings_bytes",
    ):
        if require_int(row[key], key) <= 0:
            raise StwoControlledComponentGridGateError(f"{key} must be positive")
    if row["typed_savings_bytes"] != row["source_plus_sidecar_typed_size_bytes"] - row["fused_typed_size_bytes"]:
        raise StwoControlledComponentGridGateError("typed savings drift")
    if row["json_savings_bytes"] != row["source_plus_sidecar_json_proof_size_bytes"] - row["fused_json_proof_size_bytes"]:
        raise StwoControlledComponentGridGateError("json savings drift")
    if row["typed_saving_share"] != ratio(row["typed_savings_bytes"], row["source_plus_sidecar_typed_size_bytes"]):
        raise StwoControlledComponentGridGateError("typed saving share drift")
    if row["json_saving_share"] != ratio(row["json_savings_bytes"], row["source_plus_sidecar_json_proof_size_bytes"]):
        raise StwoControlledComponentGridGateError("json saving share drift")
    delta = row["component_savings_bytes"]
    if not isinstance(delta, dict) or set(delta) != set(components.COMPONENT_BUCKETS):
        raise StwoControlledComponentGridGateError("component saving field drift")
    for key in components.COMPONENT_BUCKETS:
        if require_int(delta[key], key) < 0:
            raise StwoControlledComponentGridGateError("component saving must be non-negative")
    if sum(delta.values()) != row["typed_savings_bytes"]:
        raise StwoControlledComponentGridGateError("component savings sum drift")
    if row["dominant_component_saving_bucket"] != max(components.COMPONENT_BUCKETS, key=lambda key: delta[key]):
        raise StwoControlledComponentGridGateError("dominant component drift")
    if row["dominant_component_saving_bytes"] != delta[row["dominant_component_saving_bucket"]]:
        raise StwoControlledComponentGridGateError("dominant component byte drift")
    expected_savings = EXPECTED_PROFILE_SAVINGS[profile_id]
    for key, expected_value in expected_savings.items():
        if row[key] != expected_value:
            raise StwoControlledComponentGridGateError(f"{profile_id} {key} drift")


def build_grid_rows(route_result: dict[str, Any], fine_payload: dict[str, Any]) -> list[dict[str, Any]]:
    fine_rows = row_by_role(fine_payload)
    rows = [build_grid_row(route_row, fine_rows) for route_row in route_result["route_rows"]]
    if [row["profile_id"] for row in rows] != list(matrix.PROFILE_IDS):
        raise StwoControlledComponentGridGateError("profile order drift")
    return rows


def component_totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        bucket: sum(row["component_savings_bytes"][bucket] for row in rows)
        for bucket in components.COMPONENT_BUCKETS
    }


def build_axis_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_profile = {row["profile_id"]: row for row in rows}

    def axis(profile_ids: list[str], dimension_key: str) -> dict[str, Any]:
        axis_rows = [by_profile[profile_id] for profile_id in profile_ids]
        values = [row[dimension_key] for row in axis_rows]
        shares = [row["typed_saving_share"] for row in axis_rows]
        value_key = {
            "head_count": "head_counts",
            "steps_per_head": "steps_per_head",
            "key_width": "key_widths",
        }[dimension_key]
        payload = {
            "profile_ids": profile_ids,
            value_key: values,
            "typed_saving_shares": shares,
            "mean_typed_saving_share": mean(shares),
        }
        if len(shares) > 2:
            payload["min_typed_saving_share"] = min(shares)
            payload["max_typed_saving_share"] = max(shares)
        return payload

    summary = {
        "head_axis_d8_seq8": axis(
            [
                "d8_single_head_seq8",
                "d8_two_head_seq8",
                "d8_four_head_seq8",
                "d8_eight_head_seq8",
                "d8_sixteen_head_seq8",
            ],
            "head_count",
        ),
        "sequence_axis_d8_two_head": axis(["d8_two_head_seq8", "d8_two_head_seq16"], "steps_per_head"),
        "width_axis_single_head_seq8": axis(["d8_single_head_seq8", "d16_single_head_seq8"], "key_width"),
        "combined_width_head_sequence_axis": {
            "profile_ids": ["d16_two_head_seq8", "d16_two_head_seq16"],
            "typed_saving_shares": [
                by_profile["d16_two_head_seq8"]["typed_saving_share"],
                by_profile["d16_two_head_seq16"]["typed_saving_share"],
            ],
            "mean_typed_saving_share": mean(
                [
                    by_profile["d16_two_head_seq8"]["typed_saving_share"],
                    by_profile["d16_two_head_seq16"]["typed_saving_share"],
                ]
            ),
        },
    }
    validate_axis_summary(summary)
    return summary


def validate_axis_summary(summary: Any) -> None:
    if summary != EXPECTED_AXIS_SUMMARY:
        raise StwoControlledComponentGridGateError("axis summary drift")


def build_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    typed_shares = [row["typed_saving_share"] for row in rows]
    json_shares = [row["json_saving_share"] for row in rows]
    totals = component_totals(rows)
    typed_savings_total = sum(row["typed_savings_bytes"] for row in rows)
    aggregate = {
        "profiles_checked": len(rows),
        "all_profiles_save_typed_components": all(row["typed_savings_bytes"] > 0 for row in rows),
        "source_plus_sidecar_typed_size_bytes_total": sum(
            row["source_plus_sidecar_typed_size_bytes"] for row in rows
        ),
        "fused_typed_size_bytes_total": sum(row["fused_typed_size_bytes"] for row in rows),
        "typed_savings_bytes_total": typed_savings_total,
        "typed_saving_share_total": ratio(
            typed_savings_total,
            sum(row["source_plus_sidecar_typed_size_bytes"] for row in rows),
        ),
        "min_typed_saving_share": min(typed_shares),
        "max_typed_saving_share": max(typed_shares),
        "mean_typed_saving_share": mean(typed_shares),
        "source_plus_sidecar_json_proof_size_bytes_total": sum(
            row["source_plus_sidecar_json_proof_size_bytes"] for row in rows
        ),
        "fused_json_proof_size_bytes_total": sum(row["fused_json_proof_size_bytes"] for row in rows),
        "json_savings_bytes_total": sum(row["json_savings_bytes"] for row in rows),
        "json_saving_share_total": ratio(
            sum(row["json_savings_bytes"] for row in rows),
            sum(row["source_plus_sidecar_json_proof_size_bytes"] for row in rows),
        ),
        "min_json_saving_share": min(json_shares),
        "max_json_saving_share": max(json_shares),
        "mean_json_saving_share": mean(json_shares),
        "fri_trace_merkle_path_savings_bytes_total": sum(
            row["fri_trace_merkle_path_savings_bytes"] for row in rows
        ),
        "fri_trace_merkle_path_share_of_typed_savings": ratio(
            sum(row["fri_trace_merkle_path_savings_bytes"] for row in rows),
            typed_savings_total,
        ),
        "opening_plumbing_savings_bytes_total": sum(row["opening_plumbing_savings_bytes"] for row in rows),
        "opening_plumbing_share_of_typed_savings": ratio(
            sum(row["opening_plumbing_savings_bytes"] for row in rows),
            typed_savings_total,
        ),
        "largest_component_saving_bucket": max(components.COMPONENT_BUCKETS, key=lambda key: totals[key]),
        "largest_component_saving_bucket_bytes": max(totals.values()),
    }
    validate_aggregate(aggregate)
    return aggregate


def validate_aggregate(aggregate: Any) -> None:
    if aggregate != EXPECTED_AGGREGATE:
        raise StwoControlledComponentGridGateError("aggregate drift")


def payload_commitment(payload: dict[str, Any]) -> str:
    payload_for_commitment = copy.deepcopy(payload)
    payload_for_commitment.pop("component_grid_commitment", None)
    return blake2b_commitment(payload_for_commitment, SCHEMA)


def build_base_payload() -> dict[str, Any]:
    fine_payload = read_checked_fine_grained_payload()
    route_result = read_checked_route_matrix()
    rows = build_grid_rows(route_result, fine_payload)
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issues": list(SOURCE_ISSUES),
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "grid_status": GRID_STATUS,
        "full_factorial_grid_status": FULL_FACTORIAL_GRID_STATUS,
        "claim_boundary": CLAIM_BOUNDARY,
        "timing_policy": TIMING_POLICY,
        "component_schema_status": COMPONENT_SCHEMA_STATUS,
        "stable_binary_serializer_status": STABLE_BINARY_SERIALIZER_STATUS,
        "upstream_commitments": {
            "fine_grained_component_schema_commitment": fine_payload["fine_grained_component_schema_commitment"],
        },
        "missing_controls": list(MISSING_CONTROLS),
        "profile_ids": list(matrix.PROFILE_IDS),
        "grid_rows": rows,
        "component_savings_totals": component_totals(rows),
        "axis_summary": build_axis_summary(rows),
        "aggregate": build_aggregate(rows),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["component_grid_commitment"] = payload_commitment(payload)
    validate_payload(payload, allow_missing_mutation_summary=True)
    return payload


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    expected = {
        "schema",
        "issue",
        "source_issues",
        "decision",
        "route_id",
        "grid_status",
        "full_factorial_grid_status",
        "claim_boundary",
        "timing_policy",
        "component_schema_status",
        "stable_binary_serializer_status",
        "upstream_commitments",
        "missing_controls",
        "profile_ids",
        "grid_rows",
        "component_savings_totals",
        "axis_summary",
        "aggregate",
        "non_claims",
        "validation_commands",
        "component_grid_commitment",
    }
    mutation_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if not isinstance(payload, dict) or set(payload) - (expected | mutation_keys):
        raise StwoControlledComponentGridGateError("payload field drift")
    if expected - set(payload):
        raise StwoControlledComponentGridGateError("payload field drift")
    for key, expected_value in (
        ("schema", SCHEMA),
        ("issue", ISSUE),
        ("source_issues", list(SOURCE_ISSUES)),
        ("decision", DECISION),
        ("route_id", ROUTE_ID),
        ("grid_status", GRID_STATUS),
        ("full_factorial_grid_status", FULL_FACTORIAL_GRID_STATUS),
        ("claim_boundary", CLAIM_BOUNDARY),
        ("timing_policy", TIMING_POLICY),
        ("component_schema_status", COMPONENT_SCHEMA_STATUS),
        ("stable_binary_serializer_status", STABLE_BINARY_SERIALIZER_STATUS),
        ("missing_controls", list(MISSING_CONTROLS)),
        ("profile_ids", list(matrix.PROFILE_IDS)),
        ("non_claims", list(NON_CLAIMS)),
        ("validation_commands", list(VALIDATION_COMMANDS)),
    ):
        if payload[key] != expected_value:
            raise StwoControlledComponentGridGateError(f"{key} drift")
    if payload["upstream_commitments"] != {
        "fine_grained_component_schema_commitment": components.EXPECTED_FINE_GRAINED_COMPONENT_SCHEMA_COMMITMENT,
    }:
        raise StwoControlledComponentGridGateError("upstream commitment drift")
    rows = payload["grid_rows"]
    if not isinstance(rows, list) or len(rows) != len(matrix.PROFILE_IDS):
        raise StwoControlledComponentGridGateError("grid row count drift")
    for row in rows:
        validate_grid_row(row)
    if [row["profile_id"] for row in rows] != list(matrix.PROFILE_IDS):
        raise StwoControlledComponentGridGateError("profile order drift")
    if payload["component_savings_totals"] != component_totals(rows):
        raise StwoControlledComponentGridGateError("component totals drift")
    validate_axis_summary(payload["axis_summary"])
    if payload["axis_summary"] != build_axis_summary(rows):
        raise StwoControlledComponentGridGateError("axis summary row drift")
    if payload["aggregate"] != build_aggregate(rows):
        raise StwoControlledComponentGridGateError("aggregate row drift")
    validate_aggregate(payload["aggregate"])
    if payload_commitment(payload) != payload["component_grid_commitment"]:
        raise StwoControlledComponentGridGateError("commitment drift")
    if (
        not allow_missing_mutation_summary
        and EXPECTED_COMPONENT_GRID_COMMITMENT
        and payload["component_grid_commitment"] != EXPECTED_COMPONENT_GRID_COMMITMENT
    ):
        raise StwoControlledComponentGridGateError("published commitment drift")
    if not allow_missing_mutation_summary or any(key in payload for key in mutation_keys):
        if not mutation_keys <= set(payload):
            raise StwoControlledComponentGridGateError("mutation summary missing")
        if payload["mutations_checked"] != EXPECTED_MUTATION_COUNT:
            raise StwoControlledComponentGridGateError("mutation count drift")
        if payload["mutations_rejected"] != EXPECTED_MUTATION_COUNT:
            raise StwoControlledComponentGridGateError("mutation rejection drift")
        if payload["all_mutations_rejected"] is not True:
            raise StwoControlledComponentGridGateError("mutation rejection flag drift")
        cases = payload["mutation_cases"]
        if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
            raise StwoControlledComponentGridGateError("mutation case count drift")
        if [case.get("name") if isinstance(case, dict) else None for case in cases] != list(EXPECTED_MUTATION_NAMES):
            raise StwoControlledComponentGridGateError("mutation case name drift")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "rejected", "error"}:
                raise StwoControlledComponentGridGateError("mutation case field drift")
            if case["rejected"] is not True:
                raise StwoControlledComponentGridGateError("mutation survived")


def mutation_cases_for(payload: dict[str, Any]) -> list[dict[str, Any]]:
    base = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        base.pop(key, None)
    mutations = []

    def add(name: str, fn: Any) -> None:
        mutations.append((name, fn))

    add("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_FACTORIAL_PUBLIC_BENCHMARK"))
    add("grid_status_overclaim", lambda p: p.__setitem__("grid_status", "GO_FULL_FACTORIAL_COMPONENT_GRID"))
    add("full_factorial_status_overclaim", lambda p: p.__setitem__("full_factorial_grid_status", "GO_SEQ32_D32_COMPLETE"))
    add("missing_controls_removed", lambda p: p["missing_controls"].pop())
    add("binary_serializer_overclaim", lambda p: p.__setitem__("stable_binary_serializer_status", "GO_STABLE_BINARY_SERIALIZER"))
    add("component_schema_status_overclaim", lambda p: p.__setitem__("component_schema_status", "GO_VERIFIER_BINARY_COMPONENTS"))
    add("profile_order_drift", lambda p: p["grid_rows"].reverse())
    add("profile_relabeling", lambda p: p["grid_rows"][0].__setitem__("profile_id", "different"))
    add("typed_savings_smuggling", lambda p: p["grid_rows"][0].__setitem__("typed_savings_bytes", p["grid_rows"][0]["typed_savings_bytes"] + 1))
    add("component_delta_smuggling", lambda p: p["grid_rows"][0]["component_savings_bytes"].__setitem__("fri_decommitment_merkle_path_bytes", p["grid_rows"][0]["component_savings_bytes"]["fri_decommitment_merkle_path_bytes"] + 1))
    add("aggregate_share_smuggling", lambda p: p["aggregate"].__setitem__("typed_saving_share_total", 1.0))
    add("axis_summary_smuggling", lambda p: p["axis_summary"]["head_axis_d8_seq8"].__setitem__("mean_typed_saving_share", 1.0))
    add("all_profiles_save_flag_smuggling", lambda p: p["aggregate"].__setitem__("all_profiles_save_typed_components", False))
    add("upstream_commitment_smuggling", lambda p: p["upstream_commitments"].__setitem__("fine_grained_component_schema_commitment", "blake2b-256:" + "0" * 64))
    add("non_claim_removed", lambda p: p["non_claims"].pop(0))
    add("unknown_field_injection", lambda p: p.__setitem__("unexpected", True))
    if [name for name, _fn in mutations] != list(EXPECTED_MUTATION_NAMES):
        raise StwoControlledComponentGridGateError("mutation spec drift")
    cases = []
    for name, fn in mutations:
        candidate = copy.deepcopy(base)
        fn(candidate)
        try:
            validate_payload(candidate, allow_missing_mutation_summary=True)
        except StwoControlledComponentGridGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "mutation survived"})
    return cases


def build_payload() -> dict[str, Any]:
    payload = build_base_payload()
    cases = mutation_cases_for(payload)
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    payload["component_grid_commitment"] = payload_commitment(payload)
    validate_payload(payload)
    return payload


def to_tsv(payload: dict[str, Any]) -> str:
    rows = []
    for row in payload["grid_rows"]:
        rows.append({column: row[column] for column in TSV_COLUMNS})
    with tempfile.SpooledTemporaryFile(mode="w+", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        handle.seek(0)
        return handle.read()


def require_output_path(path: pathlib.Path) -> pathlib.Path:
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise StwoControlledComponentGridGateError(f"output path must stay under {EVIDENCE_DIR}: {path}") from err
    return resolved


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path, tsv_path: pathlib.Path) -> None:
    json_out = require_output_path(json_path)
    tsv_out = require_output_path(tsv_path)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tsv_out.write_text(to_tsv(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    payload = build_payload()
    if args.no_write:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    write_outputs(payload, args.write_json or JSON_OUT, args.write_tsv or TSV_OUT)
    print(f"wrote {args.write_json or JSON_OUT}")
    print(f"wrote {args.write_tsv or TSV_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
