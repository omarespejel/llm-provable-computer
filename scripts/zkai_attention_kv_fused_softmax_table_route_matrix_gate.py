#!/usr/bin/env python3
"""Controlled fused Softmax-table route matrix for issue #505.

This gate aggregates already checked native Stwo fused Softmax-table evidence
across one-axis-at-a-time controls. It intentionally reports proof-byte
accounting only: no timing, no real-valued Softmax, no full inference, and no
recursion/PCD claim.
"""

from __future__ import annotations

import argparse
import copy
import csv
import inspect
import json
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_d16_fused_softmax_table_native_gate as d16_fused
from scripts import zkai_attention_kv_d16_two_head_fused_softmax_table_native_gate as d16_two_head_fused
from scripts import zkai_attention_kv_d16_two_head_longseq_fused_softmax_table_native_gate as d16_two_head_longseq_fused
from scripts import zkai_attention_kv_d8_fused_softmax_table_native_gate as d8_fused
from scripts import zkai_attention_kv_eight_head_fused_softmax_table_native_gate as eight_head_fused
from scripts import zkai_attention_kv_four_head_fused_softmax_table_native_gate as four_head_fused
from scripts import zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate as sixteen_head_fused
from scripts import zkai_attention_kv_two_head_fused_softmax_table_native_gate as two_head_fused
from scripts import zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate as longseq_fused
from scripts import zkai_attention_kv_two_head_seq32_fused_softmax_table_native_gate as seq32_fused

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv"

SCHEMA = "zkai-attention-kv-fused-softmax-table-route-matrix-v1"
ISSUE = 505
DECISION = "GO_NATIVE_STWO_FUSED_SOFTMAX_TABLE_CONTROLLED_ROUTE_MATRIX"
ROUTE_ID = "local_stwo_attention_kv_fused_softmax_table_controlled_route_matrix"
CLAIM_BOUNDARY = (
    "ENGINEERING_PROOF_BYTE_ACCOUNTING_FOR_NATIVE_STWO_FUSED_BOUNDED_SOFTMAX_TABLE_FIXTURE_FAMILY_"
    "NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_TIMING_NOT_RECURSION_OR_PCD_"
    "NOT_A_PUBLIC_BENCHMARK_WITH_MATCHED_SOURCE_PLUS_SIDECAR_COMPARATORS_FOR_ALL_PROFILE_ROWS"
)
TIMING_POLICY = "proof_existence_and_byte_accounting_only_not_public_benchmark"
KERNEL_SCOPE = "bounded_integer_softmax_table_floor_division_kernel_with_fused_attention_arithmetic_and_logup_membership"
COMPARATOR_POLICY = "source_plus_sidecar_ratio_reported_only_when_matched_source_and_logup_sidecar_controls_exist"
NO_COMPARATOR_STATUS = "NO_CHECKED_SOURCE_PLUS_SIDECAR_COMPARATOR_DO_NOT_REPORT_FUSED_SAVINGS"
MATCHED_COMPARATOR_STATUS = "GO_MATCHED_SOURCE_PLUS_LOGUP_SIDECAR_COMPARATOR_RECORDED"

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate",
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
    "source_proof_size_bytes",
    "sidecar_proof_size_bytes",
    "source_plus_sidecar_raw_proof_bytes",
    "fused_proof_size_bytes",
    "fused_envelope_size_bytes",
    "fused_saves_vs_source_plus_sidecar_bytes",
    "fused_to_source_plus_sidecar_ratio",
    "matched_source_sidecar_status",
    "mutations_checked",
    "mutations_rejected",
)

EXPECTED_MUTATION_NAMES = (
    "decision_relabeling",
    "route_id_relabeling",
    "claim_boundary_real_softmax_overclaim",
    "timing_policy_benchmark_overclaim",
    "kernel_scope_overclaim",
    "comparator_policy_relabeling",
    "row_count_metric_smuggling",
    "route_row_order_drift",
    "route_row_label_relabeling",
    "route_row_decision_relabeling",
    "route_row_evidence_path_relabeling",
    "d16_width_metric_smuggling",
    "two_head_head_count_metric_smuggling",
    "longseq_steps_metric_smuggling",
    "seq32_steps_metric_smuggling",
    "fused_proof_size_metric_smuggling",
    "matched_ratio_metric_smuggling",
    "eight_head_comparator_metric_smuggling",
    "sixteen_head_comparator_metric_smuggling",
    "d16_two_head_combined_axis_metric_smuggling",
    "d16_two_head_longseq_combined_axis_metric_smuggling",
    "axis_summary_width_ratio_drift",
    "axis_summary_head_axis_ratio_drift",
    "axis_summary_sequence_ratio_drift",
    "axis_summary_sequence_seq32_ratio_drift",
    "axis_summary_combined_axis_ratio_drift",
    "axis_summary_combined_longseq_axis_ratio_drift",
    "unknown_field_injection",
)


class FusedSoftmaxTableRouteMatrixGateError(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    profile_id: str
    axis_role: str
    label: str
    gate_module: Any
    gate_json: pathlib.Path
    source_input_json: pathlib.Path
    expected_key_width: int
    expected_value_width: int
    expected_head_count: int
    expected_steps_per_head: int
    comparator_required: bool


PROFILES = (
    Profile(
        profile_id="d8_single_head_seq8",
        axis_role="baseline",
        label="d8 single-head seq8 fused Softmax-table route",
        gate_module=d8_fused,
        gate_json=d8_fused.JSON_OUT,
        source_input_json=d8_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=1,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d16_single_head_seq8",
        axis_role="width_axis",
        label="d16 single-head seq8 fused Softmax-table route",
        gate_module=d16_fused,
        gate_json=d16_fused.JSON_OUT,
        source_input_json=d16_fused.SOURCE_INPUT_JSON,
        expected_key_width=16,
        expected_value_width=16,
        expected_head_count=1,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d8_two_head_seq8",
        axis_role="head_axis",
        label="d8 two-head seq8 fused Softmax-table route",
        gate_module=two_head_fused,
        gate_json=two_head_fused.JSON_OUT,
        source_input_json=two_head_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=2,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d8_four_head_seq8",
        axis_role="head_axis_extension",
        label="d8 four-head seq8 fused Softmax-table route",
        gate_module=four_head_fused,
        gate_json=four_head_fused.JSON_OUT,
        source_input_json=four_head_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=4,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d8_eight_head_seq8",
        axis_role="head_axis_extension",
        label="d8 eight-head seq8 fused Softmax-table route with matched sidecar comparator",
        gate_module=eight_head_fused,
        gate_json=eight_head_fused.JSON_OUT,
        source_input_json=eight_head_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=8,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d8_sixteen_head_seq8",
        axis_role="head_axis_extension",
        label="d8 sixteen-head seq8 fused Softmax-table route with matched sidecar comparator",
        gate_module=sixteen_head_fused,
        gate_json=sixteen_head_fused.JSON_OUT,
        source_input_json=sixteen_head_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=16,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d8_two_head_seq16",
        axis_role="sequence_axis",
        label="d8 two-head seq16 fused Softmax-table route",
        gate_module=longseq_fused,
        gate_json=longseq_fused.JSON_OUT,
        source_input_json=longseq_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=2,
        expected_steps_per_head=16,
        comparator_required=True,
    ),
    Profile(
        profile_id="d8_two_head_seq32",
        axis_role="sequence_axis_extension",
        label="d8 two-head seq32 fused Softmax-table route",
        gate_module=seq32_fused,
        gate_json=seq32_fused.JSON_OUT,
        source_input_json=seq32_fused.SOURCE_INPUT_JSON,
        expected_key_width=8,
        expected_value_width=8,
        expected_head_count=2,
        expected_steps_per_head=32,
        comparator_required=True,
    ),
    Profile(
        profile_id="d16_two_head_seq8",
        axis_role="combined_width_head_axis",
        label="d16 two-head seq8 fused Softmax-table route",
        gate_module=d16_two_head_fused,
        gate_json=d16_two_head_fused.JSON_OUT,
        source_input_json=d16_two_head_fused.SOURCE_INPUT_JSON,
        expected_key_width=16,
        expected_value_width=16,
        expected_head_count=2,
        expected_steps_per_head=8,
        comparator_required=True,
    ),
    Profile(
        profile_id="d16_two_head_seq16",
        axis_role="combined_width_head_sequence_axis",
        label="d16 two-head seq16 fused Softmax-table route",
        gate_module=d16_two_head_longseq_fused,
        gate_json=d16_two_head_longseq_fused.JSON_OUT,
        source_input_json=d16_two_head_longseq_fused.SOURCE_INPUT_JSON,
        expected_key_width=16,
        expected_value_width=16,
        expected_head_count=2,
        expected_steps_per_head=16,
        comparator_required=True,
    ),
)
PROFILE_IDS = tuple(profile.profile_id for profile in PROFILES)


def read_json(path: pathlib.Path, label: str) -> Any:
    if not path.is_file():
        raise FusedSoftmaxTableRouteMatrixGateError(f"missing {label}: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise FusedSoftmaxTableRouteMatrixGateError(f"{label} is not JSON: {err}") from err


def validate_existing_gate(profile: Profile, gate_result: dict[str, Any]) -> None:
    module = profile.gate_module
    signature = inspect.signature(module.validate_result)
    if len(signature.parameters) == 1:
        module.validate_result(gate_result)
        return
    source_input = module.read_bounded_json(module.SOURCE_INPUT_JSON, module.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    envelope = module.read_bounded_json(module.FUSED_ENVELOPE_JSON, module.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")
    module.validate_result(gate_result, envelope, source_input)


def parse_integer_dimension(value: Any) -> int:
    if isinstance(value, bool):
        raise FusedSoftmaxTableRouteMatrixGateError("source dimensions must be integer-like")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise FusedSoftmaxTableRouteMatrixGateError("source dimensions must be integer-like")
    if isinstance(value, str):
        stripped = value.strip()
        digits = stripped[1:] if stripped[:1] in ("+", "-") else stripped
        if digits.isdigit():
            return int(stripped, 10)
    raise FusedSoftmaxTableRouteMatrixGateError("source dimensions must be integer-like")


def source_dimensions(source_input: dict[str, Any]) -> dict[str, int]:
    score_rows = source_input.get("score_rows")
    if not isinstance(score_rows, list) or not score_rows:
        raise FusedSoftmaxTableRouteMatrixGateError("source score_rows missing")
    grid: dict[tuple[int, int], set[int]] = {}
    for index, row in enumerate(score_rows):
        if not isinstance(row, dict):
            raise FusedSoftmaxTableRouteMatrixGateError("source score row shape drift")
        if "step_index" not in row:
            raise FusedSoftmaxTableRouteMatrixGateError("source step_index missing")
        if "candidate_index" not in row:
            raise FusedSoftmaxTableRouteMatrixGateError("source candidate_index missing")
        head_index = parse_integer_dimension(row.get("head_index", 0))
        step_index = parse_integer_dimension(row["step_index"])
        candidate_index = parse_integer_dimension(row["candidate_index"])
        if head_index < 0 or step_index < 0 or candidate_index < 0:
            raise FusedSoftmaxTableRouteMatrixGateError("source indices must be non-negative")
        candidates = grid.setdefault((head_index, step_index), set())
        if candidate_index in candidates:
            raise FusedSoftmaxTableRouteMatrixGateError(f"source duplicate candidate row: {index}")
        candidates.add(candidate_index)
    heads = sorted({head_index for head_index, _step_index in grid})
    steps = sorted({step_index for _head_index, step_index in grid})
    if heads != list(range(len(heads))):
        raise FusedSoftmaxTableRouteMatrixGateError("source head_index grid drift")
    if steps != list(range(len(steps))):
        raise FusedSoftmaxTableRouteMatrixGateError("source step_index grid drift")
    if not steps:
        raise FusedSoftmaxTableRouteMatrixGateError("source step_index missing")
    missing_pairs = [(head_index, step_index) for head_index in heads for step_index in steps if (head_index, step_index) not in grid]
    if missing_pairs:
        raise FusedSoftmaxTableRouteMatrixGateError("source head/step grid incomplete")
    for head_index in heads:
        for step_index in steps:
            expected_candidates = set(range(step_index + 3))
            if grid[(head_index, step_index)] != expected_candidates:
                raise FusedSoftmaxTableRouteMatrixGateError("source candidate grid drift")
    first = score_rows[0]
    key_width = source_input.get("key_width")
    if key_width is None and isinstance(first.get("key"), list):
        key_width = len(first["key"])
    if key_width is None:
        raise FusedSoftmaxTableRouteMatrixGateError("source key_width missing")
    value_width = source_input.get("value_width")
    if value_width is None and isinstance(first.get("value"), list):
        value_width = len(first["value"])
    if value_width is None:
        raise FusedSoftmaxTableRouteMatrixGateError("source value_width missing")
    trace_rows = source_input.get("trace_row_count", source_input.get("trace_rows"))
    if trace_rows is None:
        raise FusedSoftmaxTableRouteMatrixGateError("source trace_rows missing")
    key_width_int = parse_integer_dimension(key_width)
    value_width_int = parse_integer_dimension(value_width)
    trace_rows_int = parse_integer_dimension(trace_rows)
    if key_width_int <= 0 or value_width_int <= 0 or trace_rows_int <= 0:
        raise FusedSoftmaxTableRouteMatrixGateError("source dimensions must be positive")
    return {
        "key_width": key_width_int,
        "value_width": value_width_int,
        "head_count": len(heads) if heads else 1,
        "steps_per_head": len(steps),
        "score_rows": len(score_rows),
        "trace_rows": trace_rows_int,
    }


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise FusedSoftmaxTableRouteMatrixGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def build_route_row(profile: Profile) -> dict[str, Any]:
    gate_result = read_json(profile.gate_json, f"{profile.profile_id} gate result")
    validate_existing_gate(profile, gate_result)
    source_input = read_json(profile.source_input_json, f"{profile.profile_id} source input")
    dims = source_dimensions(source_input)
    expected_dims = {
        "key_width": profile.expected_key_width,
        "value_width": profile.expected_value_width,
        "head_count": profile.expected_head_count,
        "steps_per_head": profile.expected_steps_per_head,
        "score_rows": int(gate_result["lookup_claims"]),
        "trace_rows": int(gate_result["trace_rows"]),
    }
    if dims != expected_dims:
        raise FusedSoftmaxTableRouteMatrixGateError(
            f"{profile.profile_id} dimension drift: got {dims}, expected {expected_dims}"
        )

    source_proof = int(gate_result["source_proof_size_bytes"])
    source_plus_sidecar = int(gate_result.get("source_plus_sidecar_raw_proof_bytes") or 0)
    sidecar_proof = gate_result.get("sidecar_proof_size_bytes")
    if sidecar_proof in (None, 0) and source_plus_sidecar > source_proof:
        sidecar_proof = source_plus_sidecar - source_proof
    has_comparator = source_plus_sidecar > 0 and sidecar_proof not in (None, 0)
    if profile.comparator_required and not has_comparator:
        raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} missing required matched comparator")
    if not profile.comparator_required and has_comparator:
        raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} unexpectedly has matched comparator")

    fused_proof = int(gate_result["fused_proof_size_bytes"])
    row = {
        "profile_id": profile.profile_id,
        "axis_role": profile.axis_role,
        "label": profile.label,
        "source_issue": int(gate_result.get("source_issue", gate_result.get("issue", 0))),
        "sidecar_issue": gate_result.get("sidecar_issue"),
        "fused_issue": int(gate_result["issue"]),
        "route_id": gate_result["route_id"],
        "decision": gate_result["decision"],
        "key_width": dims["key_width"],
        "value_width": dims["value_width"],
        "head_count": dims["head_count"],
        "steps_per_head": dims["steps_per_head"],
        "lookup_claims": dims["score_rows"],
        "score_rows": dims["score_rows"],
        "trace_rows": dims["trace_rows"],
        "table_rows": int(gate_result["table_rows"]),
        "source_proof_size_bytes": source_proof,
        "source_envelope_size_bytes": int(gate_result.get("source_envelope_size_bytes", 0)),
        "sidecar_proof_size_bytes": int(sidecar_proof) if has_comparator else None,
        "source_plus_sidecar_raw_proof_bytes": source_plus_sidecar if has_comparator else None,
        "fused_proof_size_bytes": fused_proof,
        "fused_envelope_size_bytes": int(gate_result["fused_envelope_size_bytes"]),
        "fused_over_source_proof_bytes": int(gate_result["fused_over_source_proof_bytes"]),
        "fused_saves_vs_source_plus_sidecar_bytes": (source_plus_sidecar - fused_proof) if has_comparator else None,
        "fused_to_source_plus_sidecar_ratio": ratio(fused_proof, source_plus_sidecar) if has_comparator else None,
        "matched_source_sidecar_status": MATCHED_COMPARATOR_STATUS if has_comparator else NO_COMPARATOR_STATUS,
        "mutations_checked": int(gate_result["mutations_checked"]),
        "mutations_rejected": int(gate_result["mutations_rejected"]),
        "evidence_json": str(profile.gate_json.relative_to(ROOT)),
        "source_input_json": str(profile.source_input_json.relative_to(ROOT)),
    }
    return row


def row_by_id(rows: list[dict[str, Any]], profile_id: str) -> dict[str, Any]:
    for row in rows:
        if row["profile_id"] == profile_id:
            return row
    raise FusedSoftmaxTableRouteMatrixGateError(f"missing route row: {profile_id}")


def build_axis_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    d8 = row_by_id(rows, "d8_single_head_seq8")
    d16 = row_by_id(rows, "d16_single_head_seq8")
    two = row_by_id(rows, "d8_two_head_seq8")
    four = row_by_id(rows, "d8_four_head_seq8")
    eight = row_by_id(rows, "d8_eight_head_seq8")
    sixteen = row_by_id(rows, "d8_sixteen_head_seq8")
    longseq = row_by_id(rows, "d8_two_head_seq16")
    seq32 = row_by_id(rows, "d8_two_head_seq32")
    d16_two = row_by_id(rows, "d16_two_head_seq8")
    d16_two_longseq = row_by_id(rows, "d16_two_head_seq16")
    return {
        "width_axis_d8_to_d16": {
            "held_constant": "single_head_seq8_score_rows_52_trace_rows_64",
            "key_width_ratio": ratio(d16["key_width"], d8["key_width"]),
            "lookup_claim_ratio": ratio(d16["lookup_claims"], d8["lookup_claims"]),
            "fused_proof_size_ratio": ratio(d16["fused_proof_size_bytes"], d8["fused_proof_size_bytes"]),
            "source_plus_sidecar_ratio": ratio(
                d16["source_plus_sidecar_raw_proof_bytes"], d8["source_plus_sidecar_raw_proof_bytes"]
            ),
        },
        "head_axis_d8_seq8": {
            "held_constant": "key_width_8_value_width_8_steps_per_head_8",
            "head_counts": [1, 2, 4, 8, 16],
            "lookup_claims": [
                d8["lookup_claims"],
                two["lookup_claims"],
                four["lookup_claims"],
                eight["lookup_claims"],
                sixteen["lookup_claims"],
            ],
            "fused_proof_size_bytes": [
                d8["fused_proof_size_bytes"],
                two["fused_proof_size_bytes"],
                four["fused_proof_size_bytes"],
                eight["fused_proof_size_bytes"],
                sixteen["fused_proof_size_bytes"],
            ],
            "fused_proof_ratio_1_to_16": ratio(sixteen["fused_proof_size_bytes"], d8["fused_proof_size_bytes"]),
            "fused_proof_ratio_8_to_16": ratio(sixteen["fused_proof_size_bytes"], eight["fused_proof_size_bytes"]),
            "lookup_claim_ratio_1_to_16": ratio(sixteen["lookup_claims"], d8["lookup_claims"]),
            "lookup_claim_ratio_8_to_16": ratio(sixteen["lookup_claims"], eight["lookup_claims"]),
            "matched_comparator_head_counts": [1, 2, 4, 8, 16],
            "matched_fused_to_source_plus_sidecar_ratios": [
                d8["fused_to_source_plus_sidecar_ratio"],
                two["fused_to_source_plus_sidecar_ratio"],
                four["fused_to_source_plus_sidecar_ratio"],
                eight["fused_to_source_plus_sidecar_ratio"],
                sixteen["fused_to_source_plus_sidecar_ratio"],
            ],
            "eight_head_comparator_status": eight["matched_source_sidecar_status"],
            "sixteen_head_comparator_status": sixteen["matched_source_sidecar_status"],
        },
        "sequence_axis_two_head_d8": {
            "held_constant": "key_width_8_value_width_8_head_count_2",
            "profile_ids": ["d8_two_head_seq8", "d8_two_head_seq16", "d8_two_head_seq32"],
            "steps_per_head": [two["steps_per_head"], longseq["steps_per_head"], seq32["steps_per_head"]],
            "lookup_claims": [two["lookup_claims"], longseq["lookup_claims"], seq32["lookup_claims"]],
            "trace_rows": [two["trace_rows"], longseq["trace_rows"], seq32["trace_rows"]],
            "fused_proof_size_bytes": [
                two["fused_proof_size_bytes"],
                longseq["fused_proof_size_bytes"],
                seq32["fused_proof_size_bytes"],
            ],
            "source_plus_sidecar_raw_proof_bytes": [
                two["source_plus_sidecar_raw_proof_bytes"],
                longseq["source_plus_sidecar_raw_proof_bytes"],
                seq32["source_plus_sidecar_raw_proof_bytes"],
            ],
            "fused_to_source_plus_sidecar_ratios": [
                two["fused_to_source_plus_sidecar_ratio"],
                longseq["fused_to_source_plus_sidecar_ratio"],
                seq32["fused_to_source_plus_sidecar_ratio"],
            ],
            "seq8_to_seq16_steps_ratio": ratio(longseq["steps_per_head"], two["steps_per_head"]),
            "seq8_to_seq16_lookup_claim_ratio": ratio(longseq["lookup_claims"], two["lookup_claims"]),
            "seq8_to_seq16_trace_row_ratio": ratio(longseq["trace_rows"], two["trace_rows"]),
            "seq8_to_seq16_fused_proof_size_ratio": ratio(
                longseq["fused_proof_size_bytes"], two["fused_proof_size_bytes"]
            ),
            "seq8_to_seq16_source_plus_sidecar_ratio": ratio(
                longseq["source_plus_sidecar_raw_proof_bytes"], two["source_plus_sidecar_raw_proof_bytes"]
            ),
            "seq16_to_seq32_steps_ratio": ratio(seq32["steps_per_head"], longseq["steps_per_head"]),
            "seq16_to_seq32_lookup_claim_ratio": ratio(seq32["lookup_claims"], longseq["lookup_claims"]),
            "seq16_to_seq32_trace_row_ratio": ratio(seq32["trace_rows"], longseq["trace_rows"]),
            "seq16_to_seq32_fused_proof_size_ratio": ratio(
                seq32["fused_proof_size_bytes"], longseq["fused_proof_size_bytes"]
            ),
            "seq16_to_seq32_source_plus_sidecar_ratio": ratio(
                seq32["source_plus_sidecar_raw_proof_bytes"], longseq["source_plus_sidecar_raw_proof_bytes"]
            ),
        },
        "combined_width_head_axis_seq8": {
            "held_constant": "steps_per_head_8_bounded_softmax_table_kernel",
            "profile_id": d16_two["profile_id"],
            "key_width": d16_two["key_width"],
            "head_count": d16_two["head_count"],
            "lookup_claims": d16_two["lookup_claims"],
            "trace_rows": d16_two["trace_rows"],
            "vs_d16_single_head_lookup_claim_ratio": ratio(d16_two["lookup_claims"], d16["lookup_claims"]),
            "vs_d16_single_head_trace_row_ratio": ratio(d16_two["trace_rows"], d16["trace_rows"]),
            "vs_d16_single_head_fused_proof_size_ratio": ratio(
                d16_two["fused_proof_size_bytes"], d16["fused_proof_size_bytes"]
            ),
            "vs_d16_single_head_source_plus_sidecar_ratio": ratio(
                d16_two["source_plus_sidecar_raw_proof_bytes"], d16["source_plus_sidecar_raw_proof_bytes"]
            ),
            "vs_d8_two_head_lookup_claim_ratio": ratio(d16_two["lookup_claims"], two["lookup_claims"]),
            "vs_d8_two_head_trace_row_ratio": ratio(d16_two["trace_rows"], two["trace_rows"]),
            "vs_d8_two_head_fused_proof_size_ratio": ratio(
                d16_two["fused_proof_size_bytes"], two["fused_proof_size_bytes"]
            ),
            "vs_d8_two_head_source_plus_sidecar_ratio": ratio(
                d16_two["source_plus_sidecar_raw_proof_bytes"], two["source_plus_sidecar_raw_proof_bytes"]
            ),
            "matched_comparator_status": d16_two["matched_source_sidecar_status"],
        },
        "combined_width_head_sequence_axis": {
            "held_constant": "bounded_softmax_table_kernel_with_width_head_and_sequence_axes_combined",
            "profile_id": d16_two_longseq["profile_id"],
            "key_width": d16_two_longseq["key_width"],
            "head_count": d16_two_longseq["head_count"],
            "steps_per_head": d16_two_longseq["steps_per_head"],
            "lookup_claims": d16_two_longseq["lookup_claims"],
            "trace_rows": d16_two_longseq["trace_rows"],
            "fused_proof_size_bytes": d16_two_longseq["fused_proof_size_bytes"],
            "source_plus_sidecar_raw_proof_bytes": d16_two_longseq["source_plus_sidecar_raw_proof_bytes"],
            "vs_d16_two_head_seq8_steps_ratio": ratio(d16_two_longseq["steps_per_head"], d16_two["steps_per_head"]),
            "vs_d16_two_head_seq8_lookup_claim_ratio": ratio(
                d16_two_longseq["lookup_claims"], d16_two["lookup_claims"]
            ),
            "vs_d16_two_head_seq8_trace_row_ratio": ratio(d16_two_longseq["trace_rows"], d16_two["trace_rows"]),
            "vs_d16_two_head_seq8_fused_proof_size_ratio": ratio(
                d16_two_longseq["fused_proof_size_bytes"], d16_two["fused_proof_size_bytes"]
            ),
            "vs_d8_two_head_seq16_key_width_ratio": ratio(d16_two_longseq["key_width"], longseq["key_width"]),
            "vs_d8_two_head_seq16_lookup_claim_ratio": ratio(
                d16_two_longseq["lookup_claims"], longseq["lookup_claims"]
            ),
            "vs_d8_two_head_seq16_trace_row_ratio": ratio(d16_two_longseq["trace_rows"], longseq["trace_rows"]),
            "vs_d8_two_head_seq16_fused_proof_size_ratio": ratio(
                d16_two_longseq["fused_proof_size_bytes"], longseq["fused_proof_size_bytes"]
            ),
            "fused_to_source_plus_sidecar_ratio": d16_two_longseq["fused_to_source_plus_sidecar_ratio"],
            "matched_comparator_status": d16_two_longseq["matched_source_sidecar_status"],
        },
    }


def build_base_result() -> dict[str, Any]:
    route_rows = [build_route_row(profile) for profile in PROFILES]
    matched_rows = [row for row in route_rows if row["source_plus_sidecar_raw_proof_bytes"] is not None]
    missing_rows = [row for row in route_rows if row["source_plus_sidecar_raw_proof_bytes"] is None]
    result = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "kernel_scope": KERNEL_SCOPE,
        "comparator_policy": COMPARATOR_POLICY,
        "timing_policy": TIMING_POLICY,
        "profile_ids": list(PROFILE_IDS),
        "profiles_checked": len(route_rows),
        "matched_comparator_profiles": len(matched_rows),
        "no_comparator_profiles": [row["profile_id"] for row in missing_rows],
        "route_rows": route_rows,
        "axis_summary": build_axis_summary(route_rows),
        "aggregate_metrics": {
            "total_lookup_claims": sum(row["lookup_claims"] for row in route_rows),
            "total_trace_rows": sum(row["trace_rows"] for row in route_rows),
            "total_fused_proof_size_bytes": sum(row["fused_proof_size_bytes"] for row in route_rows),
            "max_fused_proof_size_bytes": max(row["fused_proof_size_bytes"] for row in route_rows),
            "min_matched_fused_to_source_plus_sidecar_ratio": min(
                row["fused_to_source_plus_sidecar_ratio"] for row in matched_rows
            ),
            "max_matched_fused_to_source_plus_sidecar_ratio": max(
                row["fused_to_source_plus_sidecar_ratio"] for row in matched_rows
            ),
            "matched_fused_savings_bytes_total": sum(
                row["fused_saves_vs_source_plus_sidecar_bytes"] for row in matched_rows
            ),
            "matched_source_plus_sidecar_raw_proof_bytes_total": sum(
                row["source_plus_sidecar_raw_proof_bytes"] for row in matched_rows
            ),
            "matched_fused_proof_size_bytes_total": sum(row["fused_proof_size_bytes"] for row in matched_rows),
        },
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    validate_core(result)
    return result


def mutation_cases() -> tuple[tuple[str, Any], ...]:
    return (
        ("decision_relabeling", lambda v: v.__setitem__("decision", "GO_PUBLIC_BENCHMARK")),
        ("route_id_relabeling", lambda v: v.__setitem__("route_id", "different-route")),
        ("claim_boundary_real_softmax_overclaim", lambda v: v.__setitem__("claim_boundary", "GO_REAL_VALUED_SOFTMAX")),
        ("timing_policy_benchmark_overclaim", lambda v: v.__setitem__("timing_policy", "median_of_5_public_benchmark")),
        ("kernel_scope_overclaim", lambda v: v.__setitem__("kernel_scope", "exact_real_valued_transformer_softmax")),
        ("comparator_policy_relabeling", lambda v: v.__setitem__("comparator_policy", "all_rows_have_comparators")),
        ("row_count_metric_smuggling", lambda v: v.__setitem__("profiles_checked", v["profiles_checked"] + 1)),
        ("route_row_order_drift", lambda v: v.__setitem__("route_rows", list(reversed(v["route_rows"])))),
        (
            "route_row_label_relabeling",
            lambda v: row_by_id(v["route_rows"], "d8_single_head_seq8").__setitem__("label", "different label"),
        ),
        (
            "route_row_decision_relabeling",
            lambda v: row_by_id(v["route_rows"], "d8_single_head_seq8").__setitem__("decision", "GO_DIFFERENT_GATE"),
        ),
        (
            "route_row_evidence_path_relabeling",
            lambda v: row_by_id(v["route_rows"], "d8_single_head_seq8").__setitem__("evidence_json", "other.json"),
        ),
        (
            "d16_width_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d16_single_head_seq8").__setitem__("key_width", 8),
        ),
        (
            "two_head_head_count_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_two_head_seq8").__setitem__("head_count", 1),
        ),
        (
            "longseq_steps_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_two_head_seq16").__setitem__("steps_per_head", 8),
        ),
        (
            "seq32_steps_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_two_head_seq32").__setitem__("steps_per_head", 16),
        ),
        (
            "fused_proof_size_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_four_head_seq8").__setitem__("fused_proof_size_bytes", 1),
        ),
        (
            "matched_ratio_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_single_head_seq8").__setitem__(
                "fused_to_source_plus_sidecar_ratio", 1.0
            ),
        ),
        (
            "eight_head_comparator_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_eight_head_seq8").__setitem__(
                "source_plus_sidecar_raw_proof_bytes", 1
            ),
        ),
        (
            "sixteen_head_comparator_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d8_sixteen_head_seq8").__setitem__(
                "source_plus_sidecar_raw_proof_bytes", 1
            ),
        ),
        (
            "d16_two_head_combined_axis_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d16_two_head_seq8").__setitem__("head_count", 1),
        ),
        (
            "d16_two_head_longseq_combined_axis_metric_smuggling",
            lambda v: row_by_id(v["route_rows"], "d16_two_head_seq16").__setitem__("steps_per_head", 8),
        ),
        (
            "axis_summary_width_ratio_drift",
            lambda v: v["axis_summary"]["width_axis_d8_to_d16"].__setitem__("fused_proof_size_ratio", 1.0),
        ),
        (
            "axis_summary_head_axis_ratio_drift",
            lambda v: v["axis_summary"]["head_axis_d8_seq8"].__setitem__("fused_proof_ratio_1_to_16", 16.0),
        ),
        (
            "axis_summary_sequence_ratio_drift",
            lambda v: v["axis_summary"]["sequence_axis_two_head_d8"].__setitem__(
                "seq8_to_seq16_lookup_claim_ratio", 2.0
            ),
        ),
        (
            "axis_summary_sequence_seq32_ratio_drift",
            lambda v: v["axis_summary"]["sequence_axis_two_head_d8"].__setitem__(
                "seq16_to_seq32_lookup_claim_ratio", 2.0
            ),
        ),
        (
            "axis_summary_combined_axis_ratio_drift",
            lambda v: v["axis_summary"]["combined_width_head_axis_seq8"].__setitem__(
                "vs_d8_two_head_fused_proof_size_ratio", 1.0
            ),
        ),
        (
            "axis_summary_combined_longseq_axis_ratio_drift",
            lambda v: v["axis_summary"]["combined_width_head_sequence_axis"].__setitem__(
                "vs_d8_two_head_seq16_fused_proof_size_ratio", 1.0
            ),
        ),
        ("unknown_field_injection", lambda v: v.__setitem__("unexpected", "claim smuggling")),
    )


def build_result() -> dict[str, Any]:
    base = build_base_result()
    mutation_results = []
    for name, mutator in mutation_cases():
        mutated = copy.deepcopy(base)
        try:
            mutator(mutated)
        except Exception as err:  # noqa: BLE001 - a broken mutator invalidates the gate.
            raise FusedSoftmaxTableRouteMatrixGateError(f"mutation mutator failed: {name}: {err}") from err
        try:
            validate_core(mutated)
        except Exception as err:  # noqa: BLE001 - gate records exact rejection surface.
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    if tuple(item["name"] for item in mutation_results) != EXPECTED_MUTATION_NAMES:
        raise FusedSoftmaxTableRouteMatrixGateError("mutation name/order drift")
    result = copy.deepcopy(base)
    result["mutation_results"] = mutation_results
    result["mutations_checked"] = len(mutation_results)
    result["mutations_rejected"] = sum(1 for item in mutation_results if item["rejected"] is True)
    validate_result(result)
    return result


def validate_route_rows(rows: Any) -> None:
    if not isinstance(rows, list) or len(rows) != len(PROFILES):
        raise FusedSoftmaxTableRouteMatrixGateError("route row count drift")
    if [row.get("profile_id") for row in rows] != list(PROFILE_IDS):
        raise FusedSoftmaxTableRouteMatrixGateError("route row order/profile drift")
    for row, profile in zip(rows, PROFILES, strict=True):
        required = {
            "profile_id",
            "axis_role",
            "label",
            "source_issue",
            "sidecar_issue",
            "fused_issue",
            "route_id",
            "decision",
            "key_width",
            "value_width",
            "head_count",
            "steps_per_head",
            "lookup_claims",
            "score_rows",
            "trace_rows",
            "table_rows",
            "source_proof_size_bytes",
            "source_envelope_size_bytes",
            "sidecar_proof_size_bytes",
            "source_plus_sidecar_raw_proof_bytes",
            "fused_proof_size_bytes",
            "fused_envelope_size_bytes",
            "fused_over_source_proof_bytes",
            "fused_saves_vs_source_plus_sidecar_bytes",
            "fused_to_source_plus_sidecar_ratio",
            "matched_source_sidecar_status",
            "mutations_checked",
            "mutations_rejected",
            "evidence_json",
            "source_input_json",
        }
        if set(row) != required:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} route row schema drift")
        if row["profile_id"] != profile.profile_id or row["axis_role"] != profile.axis_role:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} identity drift")
        if row["label"] != profile.label:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} label drift")
        if row["route_id"] != profile.gate_module.ROUTE_ID:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} route id drift")
        if row["decision"] != profile.gate_module.DECISION:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} decision drift")
        if row["evidence_json"] != str(profile.gate_json.relative_to(ROOT)):
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} evidence path drift")
        if row["source_input_json"] != str(profile.source_input_json.relative_to(ROOT)):
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} source input path drift")
        if row["key_width"] != profile.expected_key_width:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} key width drift")
        if row["value_width"] != profile.expected_value_width:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} value width drift")
        if row["head_count"] != profile.expected_head_count:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} head count drift")
        if row["steps_per_head"] != profile.expected_steps_per_head:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} steps per head drift")
        if row["lookup_claims"] != row["score_rows"]:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} lookup/score row drift")
        if row["table_rows"] != 9:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} table row drift")
        if row["mutations_checked"] != row["mutations_rejected"]:
            raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} mutation rejection drift")
        if profile.comparator_required:
            if row["matched_source_sidecar_status"] != MATCHED_COMPARATOR_STATUS:
                raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} matched comparator status drift")
            source_plus = row["source_plus_sidecar_raw_proof_bytes"]
            if source_plus != row["source_proof_size_bytes"] + row["sidecar_proof_size_bytes"]:
                raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} source-plus-sidecar sum drift")
            expected_ratio = ratio(row["fused_proof_size_bytes"], source_plus)
            if row["fused_to_source_plus_sidecar_ratio"] != expected_ratio:
                raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} fused ratio drift")
            if row["fused_saves_vs_source_plus_sidecar_bytes"] != source_plus - row["fused_proof_size_bytes"]:
                raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} fused savings drift")
        else:
            if row["matched_source_sidecar_status"] != NO_COMPARATOR_STATUS:
                raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} no-comparator status drift")
            forbidden = (
                row["sidecar_proof_size_bytes"],
                row["source_plus_sidecar_raw_proof_bytes"],
                row["fused_saves_vs_source_plus_sidecar_bytes"],
                row["fused_to_source_plus_sidecar_ratio"],
            )
            if any(item is not None for item in forbidden):
                raise FusedSoftmaxTableRouteMatrixGateError(f"{profile.profile_id} comparator overclaim")


def validate_axis_summary(summary: Any, rows: list[dict[str, Any]]) -> None:
    if not isinstance(summary, dict):
        raise FusedSoftmaxTableRouteMatrixGateError("axis summary must be an object")
    expected = build_axis_summary(rows)
    if summary != expected:
        raise FusedSoftmaxTableRouteMatrixGateError("axis summary drift")


def validate_aggregate_metrics(metrics: Any, rows: list[dict[str, Any]]) -> None:
    if not isinstance(metrics, dict):
        raise FusedSoftmaxTableRouteMatrixGateError("aggregate metrics must be an object")
    matched = [row for row in rows if row["source_plus_sidecar_raw_proof_bytes"] is not None]
    expected = {
        "total_lookup_claims": sum(row["lookup_claims"] for row in rows),
        "total_trace_rows": sum(row["trace_rows"] for row in rows),
        "total_fused_proof_size_bytes": sum(row["fused_proof_size_bytes"] for row in rows),
        "max_fused_proof_size_bytes": max(row["fused_proof_size_bytes"] for row in rows),
        "min_matched_fused_to_source_plus_sidecar_ratio": min(row["fused_to_source_plus_sidecar_ratio"] for row in matched),
        "max_matched_fused_to_source_plus_sidecar_ratio": max(row["fused_to_source_plus_sidecar_ratio"] for row in matched),
        "matched_fused_savings_bytes_total": sum(row["fused_saves_vs_source_plus_sidecar_bytes"] for row in matched),
        "matched_source_plus_sidecar_raw_proof_bytes_total": sum(
            row["source_plus_sidecar_raw_proof_bytes"] for row in matched
        ),
        "matched_fused_proof_size_bytes_total": sum(row["fused_proof_size_bytes"] for row in matched),
    }
    if metrics != expected:
        raise FusedSoftmaxTableRouteMatrixGateError("aggregate metrics drift")


def validate_core(result: Any) -> None:
    if not isinstance(result, dict):
        raise FusedSoftmaxTableRouteMatrixGateError("result must be an object")
    expected_keys = {
        "schema",
        "issue",
        "decision",
        "route_id",
        "claim_boundary",
        "kernel_scope",
        "comparator_policy",
        "timing_policy",
        "profile_ids",
        "profiles_checked",
        "matched_comparator_profiles",
        "no_comparator_profiles",
        "route_rows",
        "axis_summary",
        "aggregate_metrics",
        "validation_commands",
    }
    extra = set(result) - expected_keys
    if extra:
        raise FusedSoftmaxTableRouteMatrixGateError(f"unknown result keys: {sorted(extra)}")
    missing = expected_keys - set(result)
    if missing:
        raise FusedSoftmaxTableRouteMatrixGateError(f"missing result keys: {sorted(missing)}")
    exact = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "kernel_scope": KERNEL_SCOPE,
        "comparator_policy": COMPARATOR_POLICY,
        "timing_policy": TIMING_POLICY,
        "profile_ids": list(PROFILE_IDS),
        "profiles_checked": len(PROFILES),
        "matched_comparator_profiles": len(PROFILES),
        "no_comparator_profiles": [],
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, expected in exact.items():
        if result.get(key) != expected:
            raise FusedSoftmaxTableRouteMatrixGateError(f"result drift for {key}")
    if "GO_REAL_VALUED" in result["claim_boundary"] or "PUBLIC_BENCHMARK" not in result["claim_boundary"]:
        raise FusedSoftmaxTableRouteMatrixGateError("claim boundary drift")
    if "proof_existence" not in result["timing_policy"]:
        raise FusedSoftmaxTableRouteMatrixGateError("timing policy drift")
    rows = result["route_rows"]
    validate_route_rows(rows)
    validate_axis_summary(result["axis_summary"], rows)
    validate_aggregate_metrics(result["aggregate_metrics"], rows)


def validate_result(result: Any) -> None:
    if not isinstance(result, dict):
        raise FusedSoftmaxTableRouteMatrixGateError("result must be an object")
    core = copy.deepcopy(result)
    mutation_results = core.pop("mutation_results", None)
    mutations_checked = core.pop("mutations_checked", None)
    mutations_rejected = core.pop("mutations_rejected", None)
    validate_core(core)
    if not isinstance(mutation_results, list) or len(mutation_results) != len(EXPECTED_MUTATION_NAMES):
        raise FusedSoftmaxTableRouteMatrixGateError("mutation result shape drift")
    if tuple(item.get("name") for item in mutation_results if isinstance(item, dict)) != EXPECTED_MUTATION_NAMES:
        raise FusedSoftmaxTableRouteMatrixGateError("mutation result name drift")
    for item in mutation_results:
        if set(item) != {"name", "rejected", "error"}:
            raise FusedSoftmaxTableRouteMatrixGateError("mutation result schema drift")
        if item["rejected"] is not True or not isinstance(item["error"], str) or not item["error"]:
            raise FusedSoftmaxTableRouteMatrixGateError("mutation result rejection drift")
    if mutations_checked != len(EXPECTED_MUTATION_NAMES):
        raise FusedSoftmaxTableRouteMatrixGateError("mutations_checked drift")
    if mutations_rejected != len(EXPECTED_MUTATION_NAMES):
        raise FusedSoftmaxTableRouteMatrixGateError("mutations_rejected drift")


def tsv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        tmp_path = pathlib.Path(handle.name)
        handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    try:
        validate_result(json.loads(tmp_path.read_text(encoding="utf-8")))
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def write_tsv(path: pathlib.Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    rows = [{column: tsv_value(row[column]) for column in TSV_COLUMNS} for row in result["route_rows"]]
    expected_rows = [{column: str(value) for column, value in row.items()} for row in rows]
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        tmp_path = pathlib.Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    try:
        with tmp_path.open("r", encoding="utf-8", newline="") as handle:
            loaded_rows = list(csv.DictReader(handle, delimiter="\t"))
        if loaded_rows != expected_rows:
            raise FusedSoftmaxTableRouteMatrixGateError("TSV round-trip drift")
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    result = build_result()
    if args.write_json:
        write_json(args.write_json, result)
    if args.write_tsv:
        write_tsv(args.write_tsv, result)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
