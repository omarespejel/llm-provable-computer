#!/usr/bin/env python3
"""Checked d16 two-head implementation-exact quantized Softmax-table receipt gate.

This gate answers issue #524. It does not introduce a real-valued Softmax
claim. It wraps the checked native Stwo d16 two-head fused bounded
Softmax-table proof and pins the exact integer kernel contract: per-head score
max subtraction, clipped table lookup, positive denominator construction,
Euclidean floor division, quotient/remainder discipline, causal-prefix masking,
output ordering across heads, and statement-bound proof/table/domain/version
fields.
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
from collections.abc import Callable
from fractions import Fraction
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_d16_two_head_fused_softmax_table_native_gate as fused_gate  # noqa: E402
from scripts import zkai_attention_kv_quantized_softmax_receipt_gate as d8_receipt_gate  # noqa: E402

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_INPUT_JSON = fused_gate.SOURCE_INPUT_JSON
FUSED_ENVELOPE_JSON = fused_gate.FUSED_ENVELOPE_JSON
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.tsv"

SCHEMA = "zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-v1"
ISSUE = 524
SOURCE_ISSUE = 521
SOURCE_ARITHMETIC_ISSUE = 521
DECISION = "GO_D16_TWO_HEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
ROUTE_ID = "local_stwo_attention_kv_d16_two_head_quantized_softmax_table_kernel_receipt"
CLAIM_BOUNDARY = (
    "ONE_NATIVE_STWO_FUSED_D16_TWO_HEAD_ATTENTION_RECEIPT_FOR_A_FIXED_INTEGER_SOFTMAX_TABLE_KERNEL_"
    "NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_LONG_CONTEXT_NOT_RECURSION_OR_PCD_NOT_PUBLIC_BENCHMARK"
)
KERNEL_NAME = d8_receipt_gate.KERNEL_NAME
KERNEL_STATUS = "GO_EXACT_FOR_THIS_INTEGER_TABLE_FLOOR_DIVISION_KERNEL_ON_D16_TWO_HEAD_FIXTURE"
REAL_SOFTMAX_STATUS = d8_receipt_gate.REAL_SOFTMAX_STATUS
PROOF_BINDING_STATUS = (
    "GO_NATIVE_STWO_FUSED_D16_TWO_HEAD_ATTENTION_ARITHMETIC_AND_LOGUP_TABLE_MEMBERSHIP_PROOF_BACKS_RECEIPT"
)
TIMING_POLICY = fused_gate.TIMING_POLICY

SCORE_DOMAIN = "signed_i64_query_key_dot_products_over_d16_public_two_head_fixture_rows"
SCORE_SCALE = d8_receipt_gate.SCORE_SCALE
KEY_WIDTH = 16
VALUE_WIDTH = 16
HEAD_COUNT = 2
SEQUENCE_LENGTH_PER_HEAD = 8
MAX_SUBTRACTION_POLICY = d8_receipt_gate.MAX_SUBTRACTION_POLICY
CLIP_POLICY = d8_receipt_gate.CLIP_POLICY
SCORE_GAP_CLIP = d8_receipt_gate.SCORE_GAP_CLIP
TABLE_GENERATION_RULE = d8_receipt_gate.TABLE_GENERATION_RULE
WEIGHT_POLICY = d8_receipt_gate.WEIGHT_POLICY
NUMERATOR_POLICY = d8_receipt_gate.NUMERATOR_POLICY
DENOMINATOR_POLICY = "sum_positive_statement_bound_table_weights_per_head_step"
DENOMINATOR_NONZERO_BOUND = "1 <= denominator < 2^9 * per_head_step_score_row_count"
DIVISION_RULE = d8_receipt_gate.DIVISION_RULE
ROUNDING_RULE = d8_receipt_gate.ROUNDING_RULE
OUTPUT_SCALE = d8_receipt_gate.OUTPUT_SCALE
OUTPUT_SCALE_POLICY = d8_receipt_gate.OUTPUT_SCALE_POLICY
DIVISION_ERROR_BOUND = d8_receipt_gate.DIVISION_ERROR_BOUND
TABLE_ERROR_BOUND_POLICY = d8_receipt_gate.TABLE_ERROR_BOUND_POLICY
MODEL_BINDING_STATUS = d8_receipt_gate.MODEL_BINDING_STATUS
HEAD_BINDING_POLICY = "each score row binds head_index; outputs are keyed by (head_index, local_step_index)"
STEP_BINDING_POLICY = "each score row binds per-head local step_index derived from statement input_steps order"
OUTPUT_ORDER_POLICY = "attention_outputs index is derived from statement input_steps order, not from a hard-coded head layout"
CAUSAL_MASK_POLICY = "causal_prefix_position_lte_query_token checked on every emitted score row"
EXPECTED_WEIGHT_TABLE = d8_receipt_gate.EXPECTED_WEIGHT_TABLE

EXPECTED_MUTATION_NAMES = (
    "kernel_status_relabeling",
    "kernel_name_relabeling",
    "claim_boundary_real_softmax_overclaim",
    "real_softmax_status_overclaim",
    "head_count_metric_smuggling",
    "key_width_relabeling",
    "value_width_relabeling",
    "sequence_length_relabeling",
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
    "source_input_head_count_drift",
    "source_input_key_width_drift",
    "source_input_value_width_drift",
    "source_input_head_index_relabeling",
    "source_input_step_index_relabeling",
    "source_input_token_position_drift",
    "source_input_mask_allowed_false",
    "source_input_denominator_zero",
    "source_input_selected_score_gap_coherent_drift",
    "source_input_output_vector_truncation",
    "source_input_remainder_drift",
    "source_input_attention_output_split_brain",
    "source_input_output_order_swap",
    "fused_verifier_domain_relabeling",
    "fused_statement_version_relabeling",
    "fused_proof_byte_tamper",
    "unknown_receipt_key_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)
NATIVE_FUSED_PROOF_TAMPER_ERROR = (
    "fused proof receipt drift: native fused verifier rejected in-memory fused envelope"
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate",
    "cargo +nightly-2025-07-14 test --locked attention_kv_native_d16_two_head_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d16_two_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json",
    "just lib",
    "just gate-fast",
    "just gate",
)

TSV_COLUMNS = (
    "decision",
    "route_id",
    "kernel_name",
    "fused_proof_size_bytes",
    "fused_envelope_size_bytes",
    "key_width",
    "value_width",
    "head_count",
    "sequence_length_per_head",
    "input_steps",
    "lookup_claims",
    "table_rows",
    "score_gap_clip",
    "division_error_bound",
    "real_softmax_status",
    "mutations_checked",
    "mutations_rejected",
    "source_statement_commitment",
    "source_weight_table_commitment",
)


class D16TwoHeadQuantizedSoftmaxReceiptGateError(ValueError):
    pass


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    value = fused_gate.read_bounded_json(path, max_bytes, label)
    if not isinstance(value, dict):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"{label} must be an object")
    return value


def source_input() -> dict[str, Any]:
    value = read_json(SOURCE_INPUT_JSON, fused_gate.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    validate_source_contract(value)
    return value


def fused_envelope() -> dict[str, Any]:
    return read_json(FUSED_ENVELOPE_JSON, fused_gate.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")


def validate_source_contract(source: dict[str, Any]) -> None:
    try:
        fused_gate.SOURCE_INPUT_MODULE.validate_payload(source)
        fused_gate.validate_source_input_contract(source)
    except Exception as err:  # noqa: BLE001 - preserve upstream validator detail.
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"source input validation drift: {err}") from err
    expected = {
        "semantics": "bounded_table_softmax_approx_attention",
        "weight_policy": WEIGHT_POLICY,
        "score_scale": SCORE_SCALE,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "head_count": HEAD_COUNT,
        "sequence_length": SEQUENCE_LENGTH_PER_HEAD,
        "score_row_count": fused_gate.SOURCE_SCORE_ROWS,
        "trace_row_count": fused_gate.SOURCE_TRACE_ROWS,
        "score_gap_clip": SCORE_GAP_CLIP,
        "weight_table_commitment": fused_gate.SOURCE_WEIGHT_TABLE_COMMITMENT,
        "statement_commitment": fused_gate.SOURCE_STATEMENT_COMMITMENT,
        "verifier_domain": fused_gate.SOURCE_VERIFIER_DOMAIN,
        "statement_version": fused_gate.SOURCE_STATEMENT_VERSION,
        "semantic_scope": fused_gate.SOURCE_SEMANTIC_SCOPE,
        "masking_policy": "causal_prefix_position_lte_query_token",
    }
    for key, expected_value in expected.items():
        if source.get(key) != expected_value:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"source {key} drift")
    if source.get("weight_table") != list(EXPECTED_WEIGHT_TABLE):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("statement-bound weight table drift")


def table_by_gap(source: dict[str, Any]) -> dict[int, int]:
    table = source.get("weight_table")
    if table != list(EXPECTED_WEIGHT_TABLE):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("statement-bound weight table drift")
    return {entry["gap"]: entry["weight"] for entry in table}


def output_index_by_head_step(source: dict[str, Any]) -> dict[tuple[int, int], int]:
    input_steps = source.get("input_steps")
    outputs = source.get("attention_outputs")
    if not isinstance(input_steps, list) or not isinstance(outputs, list):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("input_steps/attention_outputs must be lists")
    if len(input_steps) != len(outputs):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("input_steps/attention_outputs length drift")
    local_counts: dict[int, int] = {}
    mapping: dict[tuple[int, int], int] = {}
    for output_index, step in enumerate(input_steps):
        if not isinstance(step, dict):
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("input step must be an object")
        head_index = step.get("head_index")
        if not isinstance(head_index, int) or not (0 <= head_index < HEAD_COUNT):
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("input step head_index drift")
        local_step_index = local_counts.get(head_index, 0)
        key = (head_index, local_step_index)
        if key in mapping:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("duplicate head/step output mapping")
        mapping[key] = output_index
        local_counts[head_index] = local_step_index + 1
    if sorted(local_counts) != list(range(HEAD_COUNT)):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("missing head in input step order")
    if any(count != SEQUENCE_LENGTH_PER_HEAD for count in local_counts.values()):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("per-head sequence length drift")
    return mapping


def rows_by_head_step(rows: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["head_index"], row["step_index"]), []).append(row)
    return grouped


def blake2b256(data: bytes) -> str:
    return "blake2b-256:" + hashlib.blake2b(data, digest_size=32).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def proof_bytes(envelope: dict[str, Any]) -> bytes:
    proof = envelope.get("proof")
    if not isinstance(proof, list):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("fused envelope proof must be a byte list")
    if any(not isinstance(byte, int) or isinstance(byte, bool) or byte < 0 or byte > 255 for byte in proof):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("fused envelope proof byte out of range")
    return bytes(proof)


def validate_quantized_kernel(source: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    validate_source_contract(source)
    table = table_by_gap(source)
    rows = source.get("score_rows")
    outputs = source.get("attention_outputs")
    if not isinstance(rows, list) or not isinstance(outputs, list):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("source rows/outputs must be lists")
    if len(rows) != fused_gate.SOURCE_SCORE_ROWS:
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("score-row count drift")
    if len(outputs) != HEAD_COUNT * SEQUENCE_LENGTH_PER_HEAD:
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("attention output count drift")
    if any(not isinstance(output, list) or len(output) != VALUE_WIDTH for output in outputs):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("attention output width drift")

    output_map = output_index_by_head_step(source)
    grouped = rows_by_head_step(rows)
    if set(grouped) != set(output_map):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("head/step grouping drift")

    max_fraction = Fraction(0, 1)
    per_head_step_denominators: list[dict[str, int]] = []
    per_head_step_row_counts: list[dict[str, int]] = []
    max_rows_per_head_step = 0
    denominator_sum = 0
    for head_step in sorted(grouped):
        head_index, step_index = head_step
        step_rows = grouped[head_step]
        output_index = output_map[head_step]
        expected_input_step = source["input_steps"][output_index]
        expected_token_position = expected_input_step["token_position"]
        token_positions = {row["token_position"] for row in step_rows}
        if len(token_positions) != 1:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("token-position drift")
        query_token_position = next(iter(token_positions))
        if query_token_position != expected_token_position:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("token-position/input-step drift")
        selected_scores = {row["selected_score"] for row in step_rows}
        max_score = max(row["score"] for row in step_rows)
        if selected_scores != {max_score}:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("selected score drift")
        recomputed_denominator = 0
        for row in step_rows:
            if row["head_index"] != head_index or row["step_index"] != step_index:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("head/step row drift")
            if len(row["query"]) != KEY_WIDTH or len(row["key"]) != KEY_WIDTH:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("query/key width drift")
            for vector_name in (
                "value",
                "attention_output",
                "output_remainder",
                "weighted_numerator",
                "weighted_value",
                "products",
            ):
                if len(row[vector_name]) != VALUE_WIDTH:
                    raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"{vector_name} width drift")
            expected_mask_allowed = row["candidate_position"] <= query_token_position
            if bool(row.get("mask_allowed")) != expected_mask_allowed:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("causal mask flag drift")
            if not expected_mask_allowed:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("causal mask drift")
            if row["score_gap"] != max_score - row["score"]:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("score-gap recomputation drift")
            clipped_gap = min(row["score_gap"], SCORE_GAP_CLIP)
            if clipped_gap < 0:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("negative clipped gap")
            if row["attention_weight"] != table[clipped_gap]:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("table-weight recomputation drift")
            expected_weighted_value = [row["attention_weight"] * value for value in row["value"]]
            if row["weighted_value"] != expected_weighted_value:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("weighted-value recomputation drift")
            recomputed_denominator += row["attention_weight"]
        if not (1 <= recomputed_denominator < (1 << 9) * len(step_rows)):
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("denominator outside statement bound")
        denominator_sum += recomputed_denominator
        max_rows_per_head_step = max(max_rows_per_head_step, len(step_rows))
        per_head_step_denominators.append(
            {"head_index": head_index, "step_index": step_index, "denominator": recomputed_denominator}
        )
        per_head_step_row_counts.append({"head_index": head_index, "step_index": step_index, "rows": len(step_rows)})
        recomputed_numerator = [0] * VALUE_WIDTH
        for row in step_rows:
            for dim, value in enumerate(row["weighted_value"]):
                recomputed_numerator[dim] += value
        expected_output = outputs[output_index]
        for row in step_rows:
            if row["weight_denominator"] != recomputed_denominator:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("weight denominator drift")
            if row["weighted_numerator"] != recomputed_numerator:
                raise D16TwoHeadQuantizedSoftmaxReceiptGateError("weighted-numerator recomputation drift")
            for dim, (output, remainder, numerator) in enumerate(
                zip(row["attention_output"], row["output_remainder"], row["weighted_numerator"], strict=True)
            ):
                if output != expected_output[dim]:
                    raise D16TwoHeadQuantizedSoftmaxReceiptGateError("output row/list split-brain drift")
                if numerator != output * recomputed_denominator + remainder:
                    raise D16TwoHeadQuantizedSoftmaxReceiptGateError("quotient/remainder relation drift")
                if not (0 <= remainder < recomputed_denominator):
                    raise D16TwoHeadQuantizedSoftmaxReceiptGateError("remainder outside denominator bound")
                fraction = Fraction(remainder, recomputed_denominator)
                if fraction >= 1:
                    raise D16TwoHeadQuantizedSoftmaxReceiptGateError("division error bound drift")
                max_fraction = max(max_fraction, fraction)

    return {
        "head_count": HEAD_COUNT,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "sequence_length_per_head": SEQUENCE_LENGTH_PER_HEAD,
        "input_steps": len(source["input_steps"]),
        "outputs": len(outputs),
        "score_rows": len(rows),
        "trace_rows": source["trace_row_count"],
        "lookup_claims": fused_gate.SOURCE_SCORE_ROWS,
        "table_rows": fused_gate.SOURCE_TABLE_ROWS,
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
        "fused_proof_size_bytes": fused_gate.FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": fused_gate.FUSED_ENVELOPE_SIZE_BYTES,
        "fused_proof_backend_version": fused_gate.FUSED_BACKEND_VERSION,
        "fused_proof_schema_version": fused_gate.FUSED_PROOF_SCHEMA_VERSION,
        "fused_statement_version": fused_gate.FUSED_STATEMENT_VERSION,
        "fused_target_id": fused_gate.FUSED_TARGET_ID,
        "fused_verifier_domain": fused_gate.FUSED_VERIFIER_DOMAIN,
        "fused_envelope_commitment": blake2b256(canonical_json_bytes(envelope)),
        "fused_proof_commitment": blake2b256(proof_bytes(envelope)),
    }


def kernel_contract(source: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    kernel_metrics = validate_quantized_kernel(source, envelope)
    return {
        "kernel_name": KERNEL_NAME,
        "kernel_status": KERNEL_STATUS,
        "real_softmax_status": REAL_SOFTMAX_STATUS,
        "score_domain": SCORE_DOMAIN,
        "score_scale": SCORE_SCALE,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "head_count": HEAD_COUNT,
        "sequence_length_per_head": SEQUENCE_LENGTH_PER_HEAD,
        "max_subtraction_policy": MAX_SUBTRACTION_POLICY,
        "clip_policy": CLIP_POLICY,
        "score_gap_clip": SCORE_GAP_CLIP,
        "table_generation_rule": TABLE_GENERATION_RULE,
        "weight_policy": WEIGHT_POLICY,
        "weight_table": list(EXPECTED_WEIGHT_TABLE),
        "weight_table_commitment": source["weight_table_commitment"],
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
        "source_statement_commitment": source["statement_commitment"],
        "source_public_instance_commitment": source["public_instance_commitment"],
        "source_score_row_commitment": source["score_row_commitment"],
        "source_outputs_commitment": source["outputs_commitment"],
        "source_final_kv_cache_commitment": source["final_kv_cache_commitment"],
        "source_proof_native_parameter_commitment": source["proof_native_parameter_commitment"],
        "fused_proof_backend_version": fused_gate.FUSED_BACKEND_VERSION,
        "fused_proof_schema_version": fused_gate.FUSED_PROOF_SCHEMA_VERSION,
        "fused_statement_version": fused_gate.FUSED_STATEMENT_VERSION,
        "fused_target_id": fused_gate.FUSED_TARGET_ID,
        "fused_verifier_domain": fused_gate.FUSED_VERIFIER_DOMAIN,
        "proof_binding_status": PROOF_BINDING_STATUS,
        "kernel_metrics": kernel_metrics,
    }


def validate_kernel_contract(contract: dict[str, Any], source: dict[str, Any], envelope: dict[str, Any]) -> None:
    if contract != kernel_contract(source, envelope):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("kernel contract drift")


def validate_receipt(receipt: dict[str, Any], source: dict[str, Any], envelope: dict[str, Any], *, run_native: bool) -> None:
    allowed_keys = {
        "schema",
        "issue",
        "source_issue",
        "source_arithmetic_issue",
        "decision",
        "route_id",
        "claim_boundary",
        "kernel_contract",
        "fused_gate_decision",
        "fused_proof_size_bytes",
        "fused_envelope_size_bytes",
        "lookup_claims",
        "table_rows",
        "timing_policy",
        "validation_commands",
        "mutation_results",
        "mutations_checked",
        "mutations_rejected",
    }
    extra = set(receipt) - allowed_keys
    if extra:
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"unknown receipt field(s): {sorted(extra)}")
    expected_scalars = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "source_arithmetic_issue": SOURCE_ARITHMETIC_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "fused_gate_decision": fused_gate.DECISION,
        "fused_proof_size_bytes": fused_gate.FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": fused_gate.FUSED_ENVELOPE_SIZE_BYTES,
        "lookup_claims": fused_gate.SOURCE_SCORE_ROWS,
        "table_rows": fused_gate.SOURCE_TABLE_ROWS,
        "timing_policy": TIMING_POLICY,
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }
    for key, expected in expected_scalars.items():
        if receipt.get(key) != expected:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"receipt drift for {key}")
    validate_kernel_contract(receipt.get("kernel_contract"), source, envelope)
    try:
        fused_gate.validate_fused_envelope(envelope, source, run_native=run_native)
    except Exception as err:  # noqa: BLE001 - normalize upstream gate failures.
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError(f"fused proof receipt drift: {err}") from err
    validate_mutation_results(receipt.get("mutation_results"))


def mutate_same_size_fused_proof(envelope: dict[str, Any]) -> None:
    fused_gate.mutate_same_size_stark_proof_commitment(envelope)


def mutation_cases(receipt: dict[str, Any], source: dict[str, Any], envelope: dict[str, Any]) -> list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], bool]]:
    cases: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], bool]] = []

    def add(
        name: str,
        mutator: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None],
        *,
        run_native: bool = False,
    ) -> None:
        receipt_copy = copy.deepcopy(receipt)
        source_copy = copy.deepcopy(source)
        envelope_copy = copy.deepcopy(envelope)
        mutator(receipt_copy, source_copy, envelope_copy)
        cases.append((name, receipt_copy, source_copy, envelope_copy, run_native))

    def mirror_source(mutator: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None]:
        def apply(_receipt: dict[str, Any], source_payload: dict[str, Any], envelope_payload: dict[str, Any]) -> None:
            mutator(source_payload)
            envelope_payload["source_input"] = source_payload

        return apply

    def coherently_shift_selected_score_and_gap(source_payload: dict[str, Any]) -> None:
        first = source_payload["score_rows"][0]
        head_step = (first["head_index"], first["step_index"])
        for row in source_payload["score_rows"]:
            if (row["head_index"], row["step_index"]) == head_step:
                row["selected_score"] += 1
                row["score_gap"] += 1

    def shift_step_token_position(source_payload: dict[str, Any]) -> None:
        first = source_payload["score_rows"][0]
        head_step = (first["head_index"], first["step_index"])
        for row in source_payload["score_rows"]:
            if (row["head_index"], row["step_index"]) == head_step:
                row["token_position"] += 1

    def truncate_output_vectors(source_payload: dict[str, Any]) -> None:
        first = source_payload["score_rows"][0]
        first["attention_output"] = first["attention_output"][:-1]
        first["output_remainder"] = first["output_remainder"][:-1]
        first["weighted_numerator"] = first["weighted_numerator"][:-1]

    def swap_attention_outputs(source_payload: dict[str, Any]) -> None:
        outputs = source_payload["attention_outputs"]
        outputs[0], outputs[1] = outputs[1], outputs[0]

    add("kernel_status_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("kernel_status", "GO_REAL_SOFTMAX"))
    add("kernel_name_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("kernel_name", "real_softmax"))
    add("claim_boundary_real_softmax_overclaim", lambda r, _s, _e: r.__setitem__("claim_boundary", "GO_REAL_VALUED_SOFTMAX"))
    add("real_softmax_status_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("real_softmax_status", "GO_REAL_SOFTMAX_ERROR_BOUND"))
    add("head_count_metric_smuggling", lambda r, _s, _e: r["kernel_contract"].__setitem__("head_count", 1))
    add("key_width_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("key_width", 8))
    add("value_width_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("value_width", 8))
    add("sequence_length_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("sequence_length_per_head", 4))
    add("score_scale_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("score_scale", 2))
    add("max_subtraction_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("max_subtraction_policy", "none"))
    add("clip_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("clip_policy", "unclipped"))
    add("score_gap_clip_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("score_gap_clip", 7))
    add("weight_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("weight_policy", "float-exp"))
    add("weight_table_commitment_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("weight_table_commitment", "blake2b-256:" + "55" * 32))
    add("weight_table_value_drift", lambda r, _s, _e: r["kernel_contract"]["weight_table"][1].__setitem__("weight", 182))
    add("denominator_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("denominator_policy", "external denominator"))
    add("denominator_nonzero_bound_removed", lambda r, _s, _e: r["kernel_contract"].__setitem__("denominator_nonzero_bound", "not checked"))
    add("division_rule_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("division_rule", "round-to-nearest"))
    add("rounding_rule_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("rounding_rule", "truncate_toward_zero"))
    add("output_order_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("output_order_policy", "head_index_times_sequence_length_plus_step"))
    add("causal_mask_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("causal_mask_policy", "not checked"))
    add("head_binding_policy_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("head_binding_policy", "metadata only"))
    add("output_scale_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("output_scale", 256))
    add("division_error_bound_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("division_error_bound", "0"))
    add("table_error_bound_policy_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("table_error_bound_policy", "bounded error to real Softmax"))
    add("model_binding_status_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("model_binding_status", "trainable model weights bound"))
    add("source_input_head_count_drift", mirror_source(lambda s: s.__setitem__("head_count", 1)))
    add("source_input_key_width_drift", mirror_source(lambda s: s.__setitem__("key_width", 8)))
    add("source_input_value_width_drift", mirror_source(lambda s: s.__setitem__("value_width", 8)))
    add("source_input_head_index_relabeling", mirror_source(lambda s: s["score_rows"][0].__setitem__("head_index", 2)))
    add("source_input_step_index_relabeling", mirror_source(lambda s: s["score_rows"][0].__setitem__("step_index", 99)))
    add("source_input_token_position_drift", mirror_source(shift_step_token_position))
    add("source_input_mask_allowed_false", mirror_source(lambda s: s["score_rows"][0].__setitem__("mask_allowed", False)))
    add("source_input_denominator_zero", mirror_source(lambda s: s["score_rows"][0].__setitem__("weight_denominator", 0)))
    add("source_input_selected_score_gap_coherent_drift", mirror_source(coherently_shift_selected_score_and_gap))
    add("source_input_output_vector_truncation", mirror_source(truncate_output_vectors))
    add("source_input_remainder_drift", mirror_source(lambda s: s["score_rows"][0]["output_remainder"].__setitem__(0, 999)))
    add("source_input_attention_output_split_brain", mirror_source(lambda s: s["score_rows"][0]["attention_output"].__setitem__(0, 999)))
    add("source_input_output_order_swap", mirror_source(swap_attention_outputs))
    add("fused_verifier_domain_relabeling", lambda _r, _s, e: e.__setitem__("verifier_domain", "different-domain"))
    add("fused_statement_version_relabeling", lambda _r, _s, e: e.__setitem__("statement_version", "different-statement"))
    add("fused_proof_byte_tamper", lambda _r, _s, e: mutate_same_size_fused_proof(e))
    add("unknown_receipt_key_injection", lambda r, _s, _e: r.__setitem__("unexpected", "claim smuggling"))
    return cases


def validate_mutation_results(mutation_results: Any) -> None:
    if not isinstance(mutation_results, list) or len(mutation_results) != EXPECTED_MUTATION_COUNT:
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("mutation result shape drift")
    if tuple(item.get("name") for item in mutation_results if isinstance(item, dict)) != EXPECTED_MUTATION_NAMES:
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("mutation result name drift")
    for item in mutation_results:
        if not isinstance(item, dict) or set(item) != {"name", "rejected", "error"}:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("mutation result schema drift")
        if item["rejected"] is not True or not isinstance(item["error"], str) or not item["error"]:
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("mutation result rejection drift")


def canonical_mutation_error(name: str, error: str) -> str:
    if name == "fused_proof_byte_tamper" and error.startswith(NATIVE_FUSED_PROOF_TAMPER_ERROR):
        return NATIVE_FUSED_PROOF_TAMPER_ERROR
    return error


def recompute_mutation_results(
    receipt: dict[str, Any],
    source: dict[str, Any],
    envelope: dict[str, Any],
) -> list[dict[str, Any]]:
    mutation_results = []
    for name, mutated_receipt, mutated_source, mutated_envelope, run_native in mutation_cases(receipt, source, envelope):
        try:
            validate_receipt(mutated_receipt, mutated_source, mutated_envelope, run_native=run_native)
        except D16TwoHeadQuantizedSoftmaxReceiptGateError as err:
            mutation_results.append({"name": name, "rejected": True, "error": canonical_mutation_error(name, str(err))})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    return mutation_results


def validate_recomputed_mutation_results(result: dict[str, Any], recomputed: list[dict[str, Any]]) -> None:
    validate_mutation_results(recomputed)
    serialized = result.get("mutation_results")
    validate_mutation_results(serialized)
    serialized_details = tuple((item["name"], item["rejected"], item["error"]) for item in serialized)
    recomputed_details = tuple((item["name"], item["rejected"], item["error"]) for item in recomputed)
    if serialized_details != recomputed_details:
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("recomputed mutation result detail drift")
    if result.get("mutations_rejected") != sum(1 for item in recomputed if item["rejected"]):
        raise D16TwoHeadQuantizedSoftmaxReceiptGateError("recomputed mutation rejection count drift")


def build_base_receipt(source: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "source_arithmetic_issue": SOURCE_ARITHMETIC_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "kernel_contract": kernel_contract(source, envelope),
        "fused_gate_decision": fused_gate.DECISION,
        "fused_proof_size_bytes": fused_gate.FUSED_PROOF_SIZE_BYTES,
        "fused_envelope_size_bytes": fused_gate.FUSED_ENVELOPE_SIZE_BYTES,
        "lookup_claims": fused_gate.SOURCE_SCORE_ROWS,
        "table_rows": fused_gate.SOURCE_TABLE_ROWS,
        "timing_policy": TIMING_POLICY,
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_results": [],
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }


def run_gate() -> dict[str, Any]:
    source = source_input()
    envelope = fused_envelope()
    # Validate the previous fused proof artifact, including the native CLI proof verifier.
    fused_gate.run_gate()

    receipt = build_base_receipt(source, envelope)
    mutation_results = recompute_mutation_results(receipt, source, envelope)
    receipt["mutation_results"] = mutation_results
    rejected = sum(1 for item in mutation_results if item["rejected"])
    receipt["mutations_rejected"] = rejected
    validate_receipt(receipt, source, envelope, run_native=False)
    return receipt


def validate_result(result: dict[str, Any], *, run_native: bool = False) -> None:
    source = source_input()
    envelope = fused_envelope()
    validate_receipt(result, source, envelope, run_native=run_native)
    validate_recomputed_mutation_results(result, recompute_mutation_results(result, source, envelope))


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
    metrics = contract["kernel_metrics"]
    row = {
        "decision": result["decision"],
        "route_id": result["route_id"],
        "kernel_name": contract["kernel_name"],
        "fused_proof_size_bytes": result["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": result["fused_envelope_size_bytes"],
        "key_width": contract["key_width"],
        "value_width": contract["value_width"],
        "head_count": contract["head_count"],
        "sequence_length_per_head": contract["sequence_length_per_head"],
        "input_steps": metrics["input_steps"],
        "lookup_claims": result["lookup_claims"],
        "table_rows": result["table_rows"],
        "score_gap_clip": contract["score_gap_clip"],
        "division_error_bound": contract["division_error_bound"],
        "real_softmax_status": contract["real_softmax_status"],
        "mutations_checked": result["mutations_checked"],
        "mutations_rejected": result["mutations_rejected"],
        "source_statement_commitment": contract["source_statement_commitment"],
        "source_weight_table_commitment": contract["weight_table_commitment"],
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
            raise D16TwoHeadQuantizedSoftmaxReceiptGateError("TSV round-trip drift")
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
