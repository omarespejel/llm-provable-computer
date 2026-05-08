#!/usr/bin/env python3
"""Checked multi-head implementation-exact quantized Softmax-table receipt gate.

This gate answers issue #494 by promoting the existing fused native Stwo
Softmax-table proofs from "bounded table-like Softmax" evidence into a precise
integer-kernel receipt across multiple head counts. The receipt is exact for the
literal quantized table/floor-division kernel and remains explicitly not a
real-valued exp/div Softmax or full-inference claim.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import pathlib
import sys
import tempfile
from fractions import Fraction
from typing import Any, Callable, NamedTuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_four_head_fused_softmax_table_native_gate as four_head_fused_gate  # noqa: E402
from scripts import zkai_attention_kv_quantized_softmax_receipt_gate as single_receipt_gate  # noqa: E402
from scripts import zkai_attention_kv_two_head_fused_softmax_table_native_gate as two_head_fused_gate  # noqa: E402

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv"

SCHEMA = "zkai-attention-kv-multihead-quantized-softmax-receipt-gate-v1"
ISSUE = 494
SOURCE_ISSUES = (489, 491)
SOURCE_ARITHMETIC_ISSUES = (471, 482)
DECISION = "GO_MULTIHEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
ROUTE_ID = "local_stwo_attention_kv_multihead_quantized_softmax_table_kernel_receipt"
CLAIM_BOUNDARY = (
    "TWO_AND_FOUR_HEAD_NATIVE_STWO_FUSED_ATTENTION_RECEIPTS_FOR_A_FIXED_INTEGER_SOFTMAX_TABLE_KERNEL_"
    "NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_LONG_CONTEXT_NOT_RECURSION_OR_PCD_"
    "NOT_ON_CHAIN_OR_VERIFIER_EVIDENCE_NOT_PUBLIC_BENCHMARK"
)
KERNEL_NAME = single_receipt_gate.KERNEL_NAME
KERNEL_STATUS = "GO_EXACT_FOR_THIS_INTEGER_TABLE_FLOOR_DIVISION_KERNEL_ACROSS_TWO_AND_FOUR_HEAD_FIXTURES"
REAL_SOFTMAX_STATUS = single_receipt_gate.REAL_SOFTMAX_STATUS
PROOF_BINDING_STATUS = (
    "GO_NATIVE_STWO_FUSED_ATTENTION_ARITHMETIC_AND_LOGUP_TABLE_MEMBERSHIP_PROOFS_BACK_MULTIHEAD_RECEIPT"
)
TIMING_POLICY = "proof_existence_and_byte_accounting_only_not_public_benchmark"

SCORE_DOMAIN = "signed_i64_query_key_dot_products_over_d8_public_multihead_fixture_rows"
SCORE_SCALE = single_receipt_gate.SCORE_SCALE
MAX_SUBTRACTION_POLICY = single_receipt_gate.MAX_SUBTRACTION_POLICY
CLIP_POLICY = single_receipt_gate.CLIP_POLICY
SCORE_GAP_CLIP = single_receipt_gate.SCORE_GAP_CLIP
TABLE_GENERATION_RULE = single_receipt_gate.TABLE_GENERATION_RULE
WEIGHT_POLICY = single_receipt_gate.WEIGHT_POLICY
NUMERATOR_POLICY = single_receipt_gate.NUMERATOR_POLICY
DENOMINATOR_POLICY = single_receipt_gate.DENOMINATOR_POLICY
DENOMINATOR_NONZERO_BOUND = "1 <= denominator < 2^9 * per_head_step_score_row_count"
DIVISION_RULE = single_receipt_gate.DIVISION_RULE
ROUNDING_RULE = single_receipt_gate.ROUNDING_RULE
OUTPUT_SCALE = single_receipt_gate.OUTPUT_SCALE
OUTPUT_SCALE_POLICY = single_receipt_gate.OUTPUT_SCALE_POLICY
DIVISION_ERROR_BOUND = single_receipt_gate.DIVISION_ERROR_BOUND
TABLE_ERROR_BOUND_POLICY = single_receipt_gate.TABLE_ERROR_BOUND_POLICY
MODEL_BINDING_STATUS = single_receipt_gate.MODEL_BINDING_STATUS
HEAD_BINDING_POLICY = "each score row binds head_index; outputs are keyed by (head_index, local_step_index)"
STEP_BINDING_POLICY = "each score row binds per-head local step_index derived from the statement input_steps order"
OUTPUT_ORDER_POLICY = "attention_outputs index is derived from statement input_steps order, not from a hard-coded head layout"
CAUSAL_MASK_POLICY = "causal_prefix_position_lte_query_token checked on every emitted score row"
EXPECTED_WEIGHT_TABLE = single_receipt_gate.EXPECTED_WEIGHT_TABLE


class Profile(NamedTuple):
    profile_id: str
    label: str
    source_issue: int
    source_arithmetic_issue: int
    fused_gate: Any
    evidence: str
    fused_artifact: str


PROFILES = (
    Profile(
        profile_id="two_head",
        label="two-head d8 causal-prefix fused Softmax-table proof",
        source_issue=489,
        source_arithmetic_issue=471,
        fused_gate=two_head_fused_gate,
        evidence="docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05.json",
        fused_artifact=(
            "docs/engineering/evidence/"
            "zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json"
        ),
    ),
    Profile(
        profile_id="four_head",
        label="four-head d8 causal-prefix fused Softmax-table proof",
        source_issue=491,
        source_arithmetic_issue=482,
        fused_gate=four_head_fused_gate,
        evidence="docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json",
        fused_artifact=(
            "docs/engineering/evidence/"
            "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json"
        ),
    ),
)
PROFILE_BY_ID = {profile.profile_id: profile for profile in PROFILES}

EXPECTED_MUTATION_NAMES = (
    "kernel_status_relabeling",
    "kernel_name_relabeling",
    "claim_boundary_real_softmax_overclaim",
    "real_softmax_status_overclaim",
    "profile_count_metric_smuggling",
    "profile_head_count_metric_smuggling",
    "score_scale_relabeling",
    "max_subtraction_policy_relabeling",
    "clip_policy_relabeling",
    "score_gap_clip_relabeling",
    "weight_policy_relabeling",
    "weight_table_commitment_relabeling",
    "weight_table_value_drift",
    "denominator_policy_relabeling",
    "denominator_nonzero_bound_removed",
    "division_rule_relabeling",
    "rounding_rule_relabeling",
    "output_order_policy_relabeling",
    "causal_mask_policy_relabeling",
    "head_binding_policy_relabeling",
    "output_scale_relabeling",
    "division_error_bound_relabeling",
    "table_error_bound_policy_overclaim",
    "model_binding_status_overclaim",
    "source_input_two_head_head_count_drift",
    "source_input_two_head_head_index_relabeling",
    "source_input_two_head_step_index_relabeling",
    "source_input_two_head_token_position_drift",
    "source_input_two_head_mask_allowed_false",
    "source_input_two_head_denominator_zero",
    "source_input_two_head_selected_score_gap_coherent_drift",
    "source_input_two_head_output_vector_truncation",
    "source_input_two_head_remainder_drift",
    "source_input_two_head_attention_output_split_brain",
    "source_input_four_head_head_count_drift",
    "source_input_four_head_head_index_relabeling",
    "source_input_four_head_step_index_relabeling",
    "source_input_four_head_token_position_drift",
    "source_input_four_head_mask_allowed_false",
    "source_input_four_head_denominator_zero",
    "source_input_four_head_selected_score_gap_coherent_drift",
    "source_input_four_head_output_vector_truncation",
    "source_input_four_head_remainder_drift",
    "source_input_four_head_output_order_swap",
    "fused_two_head_verifier_domain_relabeling",
    "fused_two_head_statement_version_relabeling",
    "fused_two_head_proof_byte_tamper",
    "fused_four_head_verifier_domain_relabeling",
    "fused_four_head_statement_version_relabeling",
    "fused_four_head_proof_byte_tamper",
    "unknown_receipt_key_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_multihead_quantized_softmax_receipt_gate",
    "cargo +nightly-2025-07-14 test --locked attention_kv_two_head_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test --locked attention_kv_four_head_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json",
    "just lib",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "decision",
    "route_id",
    "kernel_name",
    "profiles_checked",
    "head_counts_checked",
    "fused_proof_size_bytes_sum",
    "max_fused_proof_size_bytes",
    "lookup_claims_total",
    "table_rows",
    "score_gap_clip",
    "division_error_bound",
    "real_softmax_status",
    "mutations_checked",
    "mutations_rejected",
    "profile_statement_commitments",
    "profile_weight_table_commitments",
)


class MultiheadQuantizedSoftmaxReceiptGateError(ValueError):
    pass


def profile_ids() -> tuple[str, ...]:
    return tuple(profile.profile_id for profile in PROFILES)


def read_profile_json(profile: Profile, path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    value = profile.fused_gate.read_bounded_json(path, max_bytes, f"{profile.profile_id} {label}")
    if not isinstance(value, dict):
        raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} {label} must be an object")
    return value


def source_input(profile: Profile) -> dict[str, Any]:
    value = read_profile_json(
        profile,
        profile.fused_gate.SOURCE_INPUT_JSON,
        profile.fused_gate.MAX_SOURCE_INPUT_JSON_BYTES,
        "source input",
    )
    validate_source_profile(profile, value)
    return value


def fused_envelope(profile: Profile) -> dict[str, Any]:
    return read_profile_json(
        profile,
        profile.fused_gate.FUSED_ENVELOPE_JSON,
        profile.fused_gate.MAX_FUSED_ENVELOPE_JSON_BYTES,
        "fused envelope",
    )


def load_sources() -> dict[str, dict[str, Any]]:
    return {profile.profile_id: source_input(profile) for profile in PROFILES}


def load_envelopes() -> dict[str, dict[str, Any]]:
    return {profile.profile_id: fused_envelope(profile) for profile in PROFILES}


def validate_source_profile(profile: Profile, source: dict[str, Any]) -> None:
    try:
        profile.fused_gate.SOURCE_INPUT_MODULE.validate_payload(source)
        profile.fused_gate.validate_source_input_contract(source)
    except Exception as err:  # noqa: BLE001 - preserve upstream validator detail.
        raise MultiheadQuantizedSoftmaxReceiptGateError(
            f"{profile.profile_id} source input validation drift: {err}"
        ) from err
    expected = {
        "semantics": "bounded_table_softmax_approx_attention",
        "weight_policy": WEIGHT_POLICY,
        "score_scale": SCORE_SCALE,
        "score_gap_clip": SCORE_GAP_CLIP,
        "weight_table_commitment": profile.fused_gate.SOURCE_WEIGHT_TABLE_COMMITMENT,
        "statement_commitment": profile.fused_gate.SOURCE_STATEMENT_COMMITMENT,
        "head_count": profile.fused_gate.SOURCE_HEAD_COUNT,
        "score_row_count": profile.fused_gate.SOURCE_SCORE_ROWS,
        "trace_row_count": profile.fused_gate.SOURCE_TRACE_ROWS,
        "verifier_domain": profile.fused_gate.SOURCE_VERIFIER_DOMAIN,
        "statement_version": profile.fused_gate.SOURCE_STATEMENT_VERSION,
        "semantic_scope": profile.fused_gate.SOURCE_SEMANTIC_SCOPE,
        "masking_policy": "causal_prefix_position_lte_query_token",
    }
    for key, expected_value in expected.items():
        if source.get(key) != expected_value:
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} source {key} drift")
    if source.get("weight_table") != list(EXPECTED_WEIGHT_TABLE):
        raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} statement-bound weight table drift")


def table_by_gap(source: dict[str, Any]) -> dict[int, int]:
    table = source.get("weight_table")
    if table != list(EXPECTED_WEIGHT_TABLE):
        raise MultiheadQuantizedSoftmaxReceiptGateError("statement-bound weight table drift")
    return {entry["gap"]: entry["weight"] for entry in table}


def output_index_by_head_step(source: dict[str, Any]) -> dict[tuple[int, int], int]:
    input_steps = source.get("input_steps")
    outputs = source.get("attention_outputs")
    head_count = source.get("head_count")
    if not isinstance(input_steps, list) or not isinstance(outputs, list):
        raise MultiheadQuantizedSoftmaxReceiptGateError("input_steps/attention_outputs must be lists")
    if len(input_steps) != len(outputs):
        raise MultiheadQuantizedSoftmaxReceiptGateError("input_steps/attention_outputs length drift")
    if not isinstance(head_count, int) or head_count <= 0:
        raise MultiheadQuantizedSoftmaxReceiptGateError("head_count malformed")
    local_counts: dict[int, int] = {}
    mapping: dict[tuple[int, int], int] = {}
    for output_index, step in enumerate(input_steps):
        if not isinstance(step, dict):
            raise MultiheadQuantizedSoftmaxReceiptGateError("input step must be an object")
        head_index = step.get("head_index")
        if not isinstance(head_index, int) or not (0 <= head_index < head_count):
            raise MultiheadQuantizedSoftmaxReceiptGateError("input step head_index drift")
        local_step_index = local_counts.get(head_index, 0)
        key = (head_index, local_step_index)
        if key in mapping:
            raise MultiheadQuantizedSoftmaxReceiptGateError("duplicate head/step output mapping")
        mapping[key] = output_index
        local_counts[head_index] = local_step_index + 1
    expected_sequence_length = source.get("sequence_length")
    if any(count != expected_sequence_length for count in local_counts.values()):
        raise MultiheadQuantizedSoftmaxReceiptGateError("per-head sequence length drift")
    if sorted(local_counts) != list(range(head_count)):
        raise MultiheadQuantizedSoftmaxReceiptGateError("missing head in input step order")
    return mapping


def rows_by_head_step(rows: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["head_index"], row["step_index"]), []).append(row)
    return grouped


def validate_quantized_kernel_for_profile(profile: Profile, source: dict[str, Any]) -> dict[str, Any]:
    validate_source_profile(profile, source)
    table = table_by_gap(source)
    rows = source.get("score_rows")
    outputs = source.get("attention_outputs")
    if not isinstance(rows, list) or not isinstance(outputs, list):
        raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} source rows/outputs must be lists")
    if len(rows) != profile.fused_gate.SOURCE_SCORE_ROWS:
        raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} score-row count drift")
    output_map = output_index_by_head_step(source)
    grouped = rows_by_head_step(rows)
    if set(grouped) != set(output_map):
        raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} head/step grouping drift")

    max_fraction = Fraction(0, 1)
    per_head_step_denominators: list[dict[str, int]] = []
    per_head_step_row_counts: list[dict[str, int]] = []
    max_rows_per_head_step = 0
    denominator_sum = 0
    for head_step in sorted(grouped):
        head_index, step_index = head_step
        step_rows = grouped[head_step]
        if not step_rows:
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} empty head/step rows")
        output_index = output_map[head_step]
        expected_input_step = source["input_steps"][output_index]
        expected_token_position = expected_input_step["token_position"]
        selected_scores = {row["selected_score"] for row in step_rows}
        max_score = max(row["score"] for row in step_rows)
        if selected_scores != {max_score}:
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} selected score drift")
        recomputed_denominator = 0
        token_positions = {row["token_position"] for row in step_rows}
        if len(token_positions) != 1:
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} token-position drift")
        query_token_position = next(iter(token_positions))
        if query_token_position != expected_token_position:
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} token-position/input-step drift")
        for row in step_rows:
            expected_mask_allowed = row["candidate_position"] <= query_token_position
            if row.get("mask_allowed") != expected_mask_allowed:
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} causal mask flag drift")
            if not expected_mask_allowed:
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} causal mask drift")
            if row["score_gap"] != max_score - row["score"]:
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} score-gap recomputation drift")
            clipped_gap = min(row["score_gap"], SCORE_GAP_CLIP)
            if clipped_gap < 0:
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} negative clipped gap")
            if row["attention_weight"] != table[clipped_gap]:
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} table-weight recomputation drift")
            recomputed_denominator += row["attention_weight"]
        if not (1 <= recomputed_denominator < (1 << 9) * len(step_rows)):
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} denominator outside statement bound")
        denominator_sum += recomputed_denominator
        max_rows_per_head_step = max(max_rows_per_head_step, len(step_rows))
        per_head_step_denominators.append(
            {"head_index": head_index, "step_index": step_index, "denominator": recomputed_denominator}
        )
        per_head_step_row_counts.append({"head_index": head_index, "step_index": step_index, "rows": len(step_rows)})
        for row in step_rows:
            if row["weight_denominator"] != recomputed_denominator:
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} weight denominator drift")
            expected_output = outputs[output_index]
            output_vectors = (row["attention_output"], row["output_remainder"], row["weighted_numerator"])
            if any(len(vector) != len(expected_output) for vector in output_vectors):
                raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} output vector length drift")
            for dim, (output, remainder, numerator) in enumerate(
                zip(*output_vectors, strict=True)
            ):
                if output != expected_output[dim]:
                    raise MultiheadQuantizedSoftmaxReceiptGateError(
                        f"{profile.profile_id} output row/list split-brain drift"
                    )
                if numerator != output * recomputed_denominator + remainder:
                    raise MultiheadQuantizedSoftmaxReceiptGateError(
                        f"{profile.profile_id} quotient/remainder relation drift"
                    )
                if not (0 <= remainder < recomputed_denominator):
                    raise MultiheadQuantizedSoftmaxReceiptGateError(
                        f"{profile.profile_id} remainder outside denominator bound"
                    )
                fraction = Fraction(remainder, recomputed_denominator)
                if fraction >= 1:
                    raise MultiheadQuantizedSoftmaxReceiptGateError(f"{profile.profile_id} division error bound drift")
                max_fraction = max(max_fraction, fraction)

    return {
        "profile_id": profile.profile_id,
        "label": profile.label,
        "source_issue": profile.source_issue,
        "source_arithmetic_issue": profile.source_arithmetic_issue,
        "head_count": source["head_count"],
        "sequence_length_per_head": source["sequence_length"],
        "input_steps": len(source["input_steps"]),
        "outputs": len(outputs),
        "score_rows": len(rows),
        "trace_rows": source["trace_row_count"],
        "lookup_claims": profile.fused_gate.SOURCE_SCORE_ROWS,
        "table_rows": profile.fused_gate.SOURCE_TABLE_ROWS,
        "max_rows_per_head_step": max_rows_per_head_step,
        "denominator_sum": denominator_sum,
        "per_head_step_denominators": per_head_step_denominators,
        "per_head_step_row_counts": per_head_step_row_counts,
        "output_index_policy": OUTPUT_ORDER_POLICY,
        "max_observed_division_error_fraction": f"{max_fraction.numerator}/{max_fraction.denominator}",
        "max_observed_division_error_decimal": float(max_fraction),
        "source_statement_commitment": source["statement_commitment"],
        "source_public_instance_commitment": source["public_instance_commitment"],
        "source_score_row_commitment": source["score_row_commitment"],
        "source_outputs_commitment": source["outputs_commitment"],
        "source_final_kv_cache_commitment": source["final_kv_cache_commitment"],
        "source_weight_table_commitment": source["weight_table_commitment"],
        "fused_proof_size_bytes": profile.fused_gate.FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": profile.fused_gate.FUSED_ENVELOPE_SIZE_BYTES,
        "fused_proof_backend_version": profile.fused_gate.FUSED_BACKEND_VERSION,
        "fused_proof_schema_version": profile.fused_gate.FUSED_PROOF_SCHEMA_VERSION,
        "fused_statement_version": profile.fused_gate.FUSED_STATEMENT_VERSION,
        "fused_target_id": profile.fused_gate.FUSED_TARGET_ID,
        "fused_verifier_domain": profile.fused_gate.FUSED_VERIFIER_DOMAIN,
        "evidence": profile.evidence,
        "fused_artifact": profile.fused_artifact,
    }


def profile_metrics(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [validate_quantized_kernel_for_profile(profile, sources[profile.profile_id]) for profile in PROFILES]


def aggregate_metrics(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    max_fraction = Fraction(0, 1)
    for profile in profiles:
        numerator, denominator = profile["max_observed_division_error_fraction"].split("/", maxsplit=1)
        max_fraction = max(max_fraction, Fraction(int(numerator), int(denominator)))
    return {
        "profiles_checked": len(profiles),
        "head_counts_checked": [profile["head_count"] for profile in profiles],
        "total_heads_checked": sum(profile["head_count"] for profile in profiles),
        "total_input_steps": sum(profile["input_steps"] for profile in profiles),
        "total_outputs": sum(profile["outputs"] for profile in profiles),
        "total_score_rows": sum(profile["score_rows"] for profile in profiles),
        "total_trace_rows": sum(profile["trace_rows"] for profile in profiles),
        "total_lookup_claims": sum(profile["lookup_claims"] for profile in profiles),
        "table_rows": len(EXPECTED_WEIGHT_TABLE),
        "fused_proof_size_bytes_sum": sum(profile["fused_proof_size_bytes"] for profile in profiles),
        "max_fused_proof_size_bytes": max(profile["fused_proof_size_bytes"] for profile in profiles),
        "max_observed_division_error_fraction": f"{max_fraction.numerator}/{max_fraction.denominator}",
        "max_observed_division_error_decimal": float(max_fraction),
    }


def kernel_contract(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    profiles = profile_metrics(sources)
    return {
        "kernel_name": KERNEL_NAME,
        "kernel_status": KERNEL_STATUS,
        "real_softmax_status": REAL_SOFTMAX_STATUS,
        "score_domain": SCORE_DOMAIN,
        "score_scale": SCORE_SCALE,
        "max_subtraction_policy": MAX_SUBTRACTION_POLICY,
        "clip_policy": CLIP_POLICY,
        "score_gap_clip": SCORE_GAP_CLIP,
        "table_generation_rule": TABLE_GENERATION_RULE,
        "weight_policy": WEIGHT_POLICY,
        "weight_table": list(EXPECTED_WEIGHT_TABLE),
        "numerator_policy": NUMERATOR_POLICY,
        "denominator_policy": DENOMINATOR_POLICY,
        "denominator_nonzero_bound": DENOMINATOR_NONZERO_BOUND,
        "division_rule": DIVISION_RULE,
        "rounding_rule": ROUNDING_RULE,
        "output_scale": OUTPUT_SCALE,
        "output_scale_policy": OUTPUT_SCALE_POLICY,
        "division_error_bound": DIVISION_ERROR_BOUND,
        "table_error_bound_policy": TABLE_ERROR_BOUND_POLICY,
        "model_binding_status": MODEL_BINDING_STATUS,
        "head_binding_policy": HEAD_BINDING_POLICY,
        "step_binding_policy": STEP_BINDING_POLICY,
        "output_order_policy": OUTPUT_ORDER_POLICY,
        "causal_mask_policy": CAUSAL_MASK_POLICY,
        "proof_binding_status": PROOF_BINDING_STATUS,
        "profiles": profiles,
        "aggregate_metrics": aggregate_metrics(profiles),
    }


def validate_kernel_contract(contract: dict[str, Any], sources: dict[str, dict[str, Any]]) -> None:
    if contract != kernel_contract(sources):
        raise MultiheadQuantizedSoftmaxReceiptGateError("kernel contract drift")


def validate_profile_envelopes(
    sources: dict[str, dict[str, Any]],
    envelopes: dict[str, dict[str, Any]],
    *,
    native_profile_ids: set[str],
) -> None:
    for profile in PROFILES:
        try:
            profile.fused_gate.validate_fused_envelope(
                envelopes[profile.profile_id],
                sources[profile.profile_id],
                run_native=profile.profile_id in native_profile_ids,
            )
        except Exception as err:  # noqa: BLE001 - normalize upstream gate failures.
            raise MultiheadQuantizedSoftmaxReceiptGateError(
                f"{profile.profile_id} fused proof receipt drift: {err}"
            ) from err


def build_base_receipt(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    contract = kernel_contract(sources)
    metrics = contract["aggregate_metrics"]
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issues": list(SOURCE_ISSUES),
        "source_arithmetic_issues": list(SOURCE_ARITHMETIC_ISSUES),
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "kernel_contract": contract,
        "fused_gate_decisions": {profile.profile_id: profile.fused_gate.DECISION for profile in PROFILES},
        "profiles_checked": metrics["profiles_checked"],
        "head_counts_checked": metrics["head_counts_checked"],
        "lookup_claims_total": metrics["total_lookup_claims"],
        "score_rows_total": metrics["total_score_rows"],
        "trace_rows_total": metrics["total_trace_rows"],
        "table_rows": metrics["table_rows"],
        "fused_proof_size_bytes_sum": metrics["fused_proof_size_bytes_sum"],
        "max_fused_proof_size_bytes": metrics["max_fused_proof_size_bytes"],
        "timing_policy": TIMING_POLICY,
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_results": [],
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }


def validate_receipt(
    receipt: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    envelopes: dict[str, dict[str, Any]],
    *,
    native_profile_ids: set[str] | None = None,
) -> None:
    if native_profile_ids is None:
        native_profile_ids = set()
    allowed_keys = {
        "schema",
        "issue",
        "source_issues",
        "source_arithmetic_issues",
        "decision",
        "route_id",
        "claim_boundary",
        "kernel_contract",
        "fused_gate_decisions",
        "profiles_checked",
        "head_counts_checked",
        "lookup_claims_total",
        "score_rows_total",
        "trace_rows_total",
        "table_rows",
        "fused_proof_size_bytes_sum",
        "max_fused_proof_size_bytes",
        "timing_policy",
        "validation_commands",
        "mutation_results",
        "mutations_checked",
        "mutations_rejected",
    }
    extra = set(receipt) - allowed_keys
    if extra:
        raise MultiheadQuantizedSoftmaxReceiptGateError(f"unknown receipt field(s): {sorted(extra)}")
    expected = build_base_receipt(sources)
    for key, expected_value in expected.items():
        if key == "mutation_results":
            continue
        if receipt.get(key) != expected_value:
            raise MultiheadQuantizedSoftmaxReceiptGateError(f"receipt drift for {key}")
    validate_kernel_contract(receipt.get("kernel_contract"), sources)
    validate_profile_envelopes(sources, envelopes, native_profile_ids=native_profile_ids)
    validate_mutation_results(receipt.get("mutation_results"))


def mutate_same_size_fused_proof(profile: Profile, envelope: dict[str, Any]) -> None:
    profile.fused_gate.mutate_same_size_stark_proof_commitment(envelope)


def mutation_cases(
    receipt: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    envelopes: dict[str, dict[str, Any]],
) -> list[tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]]:
    cases: list[tuple[str, dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]] = []

    def add(
        name: str,
        mutator: Callable[[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]], None],
        *,
        native_profile_ids: set[str] | None = None,
    ) -> None:
        receipt_copy = copy.deepcopy(receipt)
        sources_copy = copy.deepcopy(sources)
        envelopes_copy = copy.deepcopy(envelopes)
        mutator(receipt_copy, sources_copy, envelopes_copy)
        cases.append((name, receipt_copy, sources_copy, envelopes_copy, native_profile_ids or set()))

    def coherently_shift_selected_score_and_gap(source: dict[str, Any]) -> None:
        first = source["score_rows"][0]
        head_step = (first["head_index"], first["step_index"])
        for row in source["score_rows"]:
            if (row["head_index"], row["step_index"]) == head_step:
                row["selected_score"] += 1
                row["score_gap"] += 1

    def shift_step_token_position(source: dict[str, Any]) -> None:
        first = source["score_rows"][0]
        head_step = (first["head_index"], first["step_index"])
        for row in source["score_rows"]:
            if (row["head_index"], row["step_index"]) == head_step:
                row["token_position"] += 1

    def truncate_output_vectors(source: dict[str, Any]) -> None:
        first = source["score_rows"][0]
        first["attention_output"] = first["attention_output"][:-1]
        first["output_remainder"] = first["output_remainder"][:-1]
        first["weighted_numerator"] = first["weighted_numerator"][:-1]

    add("kernel_status_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("kernel_status", "GO_REAL_SOFTMAX"))
    add("kernel_name_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("kernel_name", "real_softmax"))
    add("claim_boundary_real_softmax_overclaim", lambda r, _s, _e: r.__setitem__("claim_boundary", "GO_REAL_VALUED_SOFTMAX"))
    add("real_softmax_status_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("real_softmax_status", "GO_REAL_SOFTMAX_ERROR_BOUND"))
    add("profile_count_metric_smuggling", lambda r, _s, _e: r.__setitem__("profiles_checked", 1))
    add("profile_head_count_metric_smuggling", lambda r, _s, _e: r["head_counts_checked"].__setitem__(1, 8))
    add("score_scale_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("score_scale", 2))
    add("max_subtraction_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("max_subtraction_policy", "none"))
    add("clip_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("clip_policy", "unclipped"))
    add("score_gap_clip_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("score_gap_clip", 7))
    add("weight_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("weight_policy", "float-exp"))
    add(
        "weight_table_commitment_relabeling",
        lambda r, _s, _e: r["kernel_contract"]["profiles"][0].__setitem__("source_weight_table_commitment", "blake2b-256:" + "55" * 32),
    )
    add("weight_table_value_drift", lambda r, _s, _e: r["kernel_contract"]["weight_table"][1].__setitem__("weight", 182))
    add("denominator_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("denominator_policy", "external denominator"))
    add("denominator_nonzero_bound_removed", lambda r, _s, _e: r["kernel_contract"].__setitem__("denominator_nonzero_bound", "not checked"))
    add("division_rule_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("division_rule", "round-to-nearest"))
    add("rounding_rule_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("rounding_rule", "truncate_toward_zero"))
    add("output_order_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("output_order_policy", "step_index_times_head_count_plus_head"))
    add("causal_mask_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("causal_mask_policy", "not checked"))
    add("head_binding_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("head_binding_policy", "metadata only"))
    add("output_scale_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("output_scale", 256))
    add("division_error_bound_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("division_error_bound", "0"))
    add("table_error_bound_policy_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("table_error_bound_policy", "bounded error to real Softmax"))
    add("model_binding_status_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("model_binding_status", "trainable model weights bound"))
    add("source_input_two_head_head_count_drift", lambda _r, s, e: (s["two_head"].__setitem__("head_count", 3), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_head_index_relabeling", lambda _r, s, e: (s["two_head"]["score_rows"][0].__setitem__("head_index", 2), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_step_index_relabeling", lambda _r, s, e: (s["two_head"]["score_rows"][0].__setitem__("step_index", 99), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_token_position_drift", lambda _r, s, e: (shift_step_token_position(s["two_head"]), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_mask_allowed_false", lambda _r, s, e: (s["two_head"]["score_rows"][0].__setitem__("mask_allowed", False), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_denominator_zero", lambda _r, s, e: (s["two_head"]["score_rows"][0].__setitem__("weight_denominator", 0), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_selected_score_gap_coherent_drift", lambda _r, s, e: (coherently_shift_selected_score_and_gap(s["two_head"]), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_output_vector_truncation", lambda _r, s, e: (truncate_output_vectors(s["two_head"]), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_remainder_drift", lambda _r, s, e: (s["two_head"]["score_rows"][0]["output_remainder"].__setitem__(0, 999), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_two_head_attention_output_split_brain", lambda _r, s, e: (s["two_head"]["score_rows"][0]["attention_output"].__setitem__(0, 999), e["two_head"].__setitem__("source_input", s["two_head"])))
    add("source_input_four_head_head_count_drift", lambda _r, s, e: (s["four_head"].__setitem__("head_count", 5), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_head_index_relabeling", lambda _r, s, e: (s["four_head"]["score_rows"][0].__setitem__("head_index", 4), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_step_index_relabeling", lambda _r, s, e: (s["four_head"]["score_rows"][0].__setitem__("step_index", 99), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_token_position_drift", lambda _r, s, e: (shift_step_token_position(s["four_head"]), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_mask_allowed_false", lambda _r, s, e: (s["four_head"]["score_rows"][0].__setitem__("mask_allowed", False), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_denominator_zero", lambda _r, s, e: (s["four_head"]["score_rows"][0].__setitem__("weight_denominator", 0), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_selected_score_gap_coherent_drift", lambda _r, s, e: (coherently_shift_selected_score_and_gap(s["four_head"]), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_output_vector_truncation", lambda _r, s, e: (truncate_output_vectors(s["four_head"]), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_remainder_drift", lambda _r, s, e: (s["four_head"]["score_rows"][0]["output_remainder"].__setitem__(0, 999), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("source_input_four_head_output_order_swap", lambda _r, s, e: (s["four_head"]["attention_outputs"].__setitem__(0, s["four_head"]["attention_outputs"][1]), e["four_head"].__setitem__("source_input", s["four_head"])))
    add("fused_two_head_verifier_domain_relabeling", lambda _r, _s, e: e["two_head"].__setitem__("verifier_domain", "different-domain"))
    add("fused_two_head_statement_version_relabeling", lambda _r, _s, e: e["two_head"].__setitem__("statement_version", "different-statement"))
    add(
        "fused_two_head_proof_byte_tamper",
        lambda _r, _s, e: mutate_same_size_fused_proof(PROFILE_BY_ID["two_head"], e["two_head"]),
        native_profile_ids={"two_head"},
    )
    add("fused_four_head_verifier_domain_relabeling", lambda _r, _s, e: e["four_head"].__setitem__("verifier_domain", "different-domain"))
    add("fused_four_head_statement_version_relabeling", lambda _r, _s, e: e["four_head"].__setitem__("statement_version", "different-statement"))
    add(
        "fused_four_head_proof_byte_tamper",
        lambda _r, _s, e: mutate_same_size_fused_proof(PROFILE_BY_ID["four_head"], e["four_head"]),
        native_profile_ids={"four_head"},
    )
    add("unknown_receipt_key_injection", lambda r, _s, _e: r.__setitem__("unexpected", "claim smuggling"))
    return cases


def validate_mutation_results(mutation_results: Any) -> None:
    if not isinstance(mutation_results, list) or len(mutation_results) != EXPECTED_MUTATION_COUNT:
        raise MultiheadQuantizedSoftmaxReceiptGateError("mutation result shape drift")
    if tuple(item.get("name") for item in mutation_results if isinstance(item, dict)) != EXPECTED_MUTATION_NAMES:
        raise MultiheadQuantizedSoftmaxReceiptGateError("mutation result name drift")
    for item in mutation_results:
        if not isinstance(item, dict) or set(item) != {"name", "rejected", "error"}:
            raise MultiheadQuantizedSoftmaxReceiptGateError("mutation result schema drift")
        if item["rejected"] is not True or not isinstance(item["error"], str) or not item["error"]:
            raise MultiheadQuantizedSoftmaxReceiptGateError("mutation result rejection drift")


def run_gate() -> dict[str, Any]:
    sources = load_sources()
    envelopes = load_envelopes()
    # Validate the backing fused proof artifacts, including their native CLI proof verifiers.
    for profile in PROFILES:
        profile.fused_gate.run_gate()

    receipt = build_base_receipt(sources)
    mutation_results = []
    for name, mutated_receipt, mutated_sources, mutated_envelopes, native_profile_ids in mutation_cases(
        receipt, sources, envelopes
    ):
        try:
            validate_receipt(
                mutated_receipt,
                mutated_sources,
                mutated_envelopes,
                native_profile_ids=native_profile_ids,
            )
        except Exception as err:  # noqa: BLE001 - gate records exact rejection surface.
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    receipt["mutation_results"] = mutation_results
    rejected = sum(1 for item in mutation_results if item["rejected"])
    receipt["mutations_rejected"] = rejected
    validate_receipt(receipt, sources, envelopes)
    return receipt


def validate_result(result: dict[str, Any], *, native_profile_ids: set[str] | None = None) -> None:
    if native_profile_ids is None:
        native_profile_ids = set(profile_ids())
    validate_receipt(result, load_sources(), load_envelopes(), native_profile_ids=native_profile_ids)


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_result(result)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
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
    contract = result["kernel_contract"]
    profiles = contract["profiles"]
    row = {
        "decision": result["decision"],
        "route_id": result["route_id"],
        "kernel_name": contract["kernel_name"],
        "profiles_checked": result["profiles_checked"],
        "head_counts_checked": ",".join(str(value) for value in result["head_counts_checked"]),
        "fused_proof_size_bytes_sum": result["fused_proof_size_bytes_sum"],
        "max_fused_proof_size_bytes": result["max_fused_proof_size_bytes"],
        "lookup_claims_total": result["lookup_claims_total"],
        "table_rows": result["table_rows"],
        "score_gap_clip": contract["score_gap_clip"],
        "division_error_bound": contract["division_error_bound"],
        "real_softmax_status": contract["real_softmax_status"],
        "mutations_checked": result["mutations_checked"],
        "mutations_rejected": result["mutations_rejected"],
        "profile_statement_commitments": ",".join(profile["source_statement_commitment"] for profile in profiles),
        "profile_weight_table_commitments": ",".join(profile["source_weight_table_commitment"] for profile in profiles),
    }
    expected_row = {column: str(row[column]) for column in TSV_COLUMNS}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    try:
        with tmp_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        if rows != [expected_row]:
            raise MultiheadQuantizedSoftmaxReceiptGateError("TSV round-trip drift")
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    result = run_gate()
    write_json(args.write_json, result)
    write_tsv(args.write_tsv, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
