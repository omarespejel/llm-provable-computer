#!/usr/bin/env python3
"""Checked d16 implementation-exact quantized Softmax-table receipt gate for issue #506.

This gate does not introduce a new real-valued Softmax claim. It wraps the
existing fused native Stwo d16 bounded Softmax-table proof and pins the exact
integer kernel that the verifier/model path is allowed to mean: score max
subtraction, clipped table lookup, positive denominator, Euclidean floor
division, output remainders, and a statement-bound policy/table/domain/version.
"""

from __future__ import annotations

import argparse
import copy
import csv
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

from scripts import zkai_attention_kv_d16_fused_softmax_table_native_gate as fused_gate  # noqa: E402

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_INPUT_JSON = fused_gate.SOURCE_INPUT_JSON
FUSED_ENVELOPE_JSON = fused_gate.FUSED_ENVELOPE_JSON
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv"

SCHEMA = "zkai-attention-kv-d16-quantized-softmax-receipt-gate-v1"
ISSUE = 506
SOURCE_ISSUE = 501
SOURCE_ARITHMETIC_ISSUE = 501
DECISION = "GO_D16_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT"
ROUTE_ID = "local_stwo_attention_kv_d16_quantized_softmax_table_kernel_receipt"
CLAIM_BOUNDARY = (
    "ONE_NATIVE_STWO_FUSED_D16_ATTENTION_RECEIPT_FOR_A_FIXED_INTEGER_SOFTMAX_TABLE_KERNEL_"
    "NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_PUBLIC_BENCHMARK"
)
KERNEL_NAME = "bounded_fixed_point_softmax_table_attention_v1"
KERNEL_STATUS = "GO_EXACT_FOR_THIS_INTEGER_TABLE_FLOOR_DIVISION_KERNEL"
REAL_SOFTMAX_STATUS = "NO_REAL_VALUED_EXP_DIV_SOFTMAX_ERROR_BOUND_CLAIMED"
PROOF_BINDING_STATUS = "GO_NATIVE_STWO_FUSED_ARITHMETIC_AND_LOGUP_TABLE_MEMBERSHIP_PROOF_BACKS_RECEIPT"
TIMING_POLICY = fused_gate.TIMING_POLICY

SCORE_DOMAIN = "signed_i64_query_key_dot_products_over_d16_public_fixture_rows"
SCORE_SCALE = 1
KEY_WIDTH = 16
VALUE_WIDTH = 16
SEQUENCE_LENGTH = 8
MAX_SUBTRACTION_POLICY = "per_step_max_allowed_score_subtracted_before_table_lookup"
CLIP_POLICY = "clipped_gap = min(max_score - score, 8)"
SCORE_GAP_CLIP = 8
TABLE_GENERATION_RULE = "literal table: round(256 * 2^(-gap/2)) for gaps 0..8, committed as statement data"
WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
NUMERATOR_POLICY = "per_output_dim_sum_over_allowed_candidates(weight * value_dim)"
DENOMINATOR_POLICY = "sum_positive_statement_bound_table_weights_per_step"
DENOMINATOR_NONZERO_BOUND = "1 <= denominator < 2^9 * score_row_count"
DIVISION_RULE = "output = numerator.div_euclid(denominator); remainder = numerator.rem_euclid(denominator)"
ROUNDING_RULE = "floor_toward_negative_infinity_via_euclidean_division_positive_denominator"
OUTPUT_SCALE = 1
OUTPUT_SCALE_POLICY = "same_integer_units_as_value_vectors"
DIVISION_ERROR_BOUND = "0 <= weighted_rational - output < 1 output unit for every emitted output coordinate"
TABLE_ERROR_BOUND_POLICY = "no real-valued Softmax approximation error bound is claimed; the literal integer table is the kernel"
MODEL_BINDING_STATUS = "no separate trainable model weights in this fixture; public query/key/value/KV rows are statement-bound"

EXPECTED_WEIGHT_TABLE = (
    {"gap": 0, "weight": 256},
    {"gap": 1, "weight": 181},
    {"gap": 2, "weight": 128},
    {"gap": 3, "weight": 91},
    {"gap": 4, "weight": 64},
    {"gap": 5, "weight": 45},
    {"gap": 6, "weight": 32},
    {"gap": 7, "weight": 23},
    {"gap": 8, "weight": 16},
)

EXPECTED_MUTATION_NAMES = (
    "kernel_status_relabeling",
    "kernel_name_relabeling",
    "claim_boundary_exact_softmax_overclaim",
    "real_softmax_status_overclaim",
    "score_scale_relabeling",
    "key_width_relabeling",
    "value_width_relabeling",
    "sequence_length_relabeling",
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
    "output_scale_relabeling",
    "division_error_bound_relabeling",
    "table_error_bound_policy_overclaim",
    "model_binding_status_overclaim",
    "source_input_score_scale_drift",
    "source_input_key_width_drift",
    "source_input_value_width_drift",
    "source_input_sequence_length_drift",
    "source_input_clip_drift",
    "source_input_weight_policy_drift",
    "source_input_denominator_zero",
    "source_input_weighted_value_drift",
    "source_input_weighted_numerator_drift",
    "source_input_remainder_drift",
    "fused_verifier_domain_relabeling",
    "fused_statement_version_relabeling",
    "fused_proof_byte_tamper",
    "unknown_receipt_key_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_quantized_softmax_receipt_gate",
    "cargo +nightly-2025-07-14 test --locked attention_kv_native_d16_fused_softmax_table --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json",
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
    "sequence_length",
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


class QuantizedSoftmaxReceiptGateError(ValueError):
    pass


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    value = fused_gate.read_bounded_json(path, max_bytes, label)
    if not isinstance(value, dict):
        raise QuantizedSoftmaxReceiptGateError(f"{label} must be an object")
    return value


def source_input() -> dict[str, Any]:
    value = read_json(SOURCE_INPUT_JSON, fused_gate.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
    try:
        fused_gate.SOURCE_INPUT_MODULE.validate_payload(value)
    except Exception as err:  # noqa: BLE001 - preserve validator detail.
        raise QuantizedSoftmaxReceiptGateError(f"source input validation drift: {err}") from err
    return value


def fused_envelope() -> dict[str, Any]:
    return read_json(FUSED_ENVELOPE_JSON, fused_gate.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")


def table_by_gap(source: dict[str, Any]) -> dict[int, int]:
    table = source.get("weight_table")
    if table != list(EXPECTED_WEIGHT_TABLE):
        raise QuantizedSoftmaxReceiptGateError("statement-bound weight table drift")
    return {entry["gap"]: entry["weight"] for entry in table}


def rows_by_step(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["step_index"], []).append(row)
    return grouped


def validate_quantized_kernel(source: dict[str, Any]) -> dict[str, Any]:
    table = table_by_gap(source)
    expected_scalars = {
        "semantics": "bounded_table_softmax_approx_attention",
        "weight_policy": WEIGHT_POLICY,
        "score_scale": SCORE_SCALE,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "sequence_length": SEQUENCE_LENGTH,
        "score_row_count": fused_gate.SOURCE_SCORE_ROWS,
        "trace_row_count": fused_gate.SOURCE_TRACE_ROWS,
        "score_gap_clip": SCORE_GAP_CLIP,
        "weight_table_commitment": fused_gate.SOURCE_WEIGHT_TABLE_COMMITMENT,
        "statement_commitment": fused_gate.SOURCE_STATEMENT_COMMITMENT,
        "verifier_domain": "ptvm:zkai:attention-kv-stwo-native-d16-bounded-softmax-table:v1",
    }
    for key, expected in expected_scalars.items():
        if source.get(key) != expected:
            raise QuantizedSoftmaxReceiptGateError(f"source {key} drift")

    rows = source.get("score_rows")
    outputs = source.get("attention_outputs")
    if not isinstance(rows, list) or not isinstance(outputs, list):
        raise QuantizedSoftmaxReceiptGateError("source rows/outputs must be lists")
    if len(rows) != fused_gate.SOURCE_SCORE_ROWS:
        raise QuantizedSoftmaxReceiptGateError("score-row count drift")
    if len(outputs) != SEQUENCE_LENGTH:
        raise QuantizedSoftmaxReceiptGateError("attention output step count drift")
    if any(not isinstance(output, list) or len(output) != VALUE_WIDTH for output in outputs):
        raise QuantizedSoftmaxReceiptGateError("attention output width drift")

    max_fraction = Fraction(0, 1)
    per_step_denominators: list[int] = []
    grouped = rows_by_step(rows)
    if sorted(grouped) != list(range(len(outputs))):
        raise QuantizedSoftmaxReceiptGateError("step grouping drift")

    for step_index in sorted(grouped):
        step_rows = grouped[step_index]
        if not step_rows:
            raise QuantizedSoftmaxReceiptGateError("empty step rows")
        selected_scores = {row["selected_score"] for row in step_rows}
        if len(selected_scores) != 1:
            raise QuantizedSoftmaxReceiptGateError("per-step selected score drift")
        max_score = next(iter(selected_scores))
        if max_score != max(row["score"] for row in step_rows):
            raise QuantizedSoftmaxReceiptGateError("max-score recomputation drift")
        recomputed_denominator = 0
        for row in step_rows:
            if len(row["query"]) != KEY_WIDTH or len(row["key"]) != KEY_WIDTH:
                raise QuantizedSoftmaxReceiptGateError("query/key width drift")
            for vector_name in (
                "value",
                "attention_output",
                "output_remainder",
                "weighted_numerator",
                "weighted_value",
                "products",
            ):
                if len(row[vector_name]) != VALUE_WIDTH:
                    raise QuantizedSoftmaxReceiptGateError(f"{vector_name} width drift")
            if row["score_gap"] != max_score - row["score"]:
                raise QuantizedSoftmaxReceiptGateError("score-gap recomputation drift")
            clipped_gap = min(row["score_gap"], SCORE_GAP_CLIP)
            if clipped_gap < 0:
                raise QuantizedSoftmaxReceiptGateError("negative clipped gap")
            if row["attention_weight"] != table[clipped_gap]:
                raise QuantizedSoftmaxReceiptGateError("table-weight recomputation drift")
            expected_weighted_value = [row["attention_weight"] * value for value in row["value"]]
            if row["weighted_value"] != expected_weighted_value:
                raise QuantizedSoftmaxReceiptGateError("weighted-value recomputation drift")
            recomputed_denominator += row["attention_weight"]
        if not (1 <= recomputed_denominator < (1 << 9) * fused_gate.SOURCE_SCORE_ROWS):
            raise QuantizedSoftmaxReceiptGateError("denominator outside statement bound")
        per_step_denominators.append(recomputed_denominator)
        recomputed_numerator = [0] * VALUE_WIDTH
        for row in step_rows:
            for dim, value in enumerate(row["weighted_value"]):
                recomputed_numerator[dim] += value
        for row in step_rows:
            if row["weight_denominator"] != recomputed_denominator:
                raise QuantizedSoftmaxReceiptGateError("weight denominator drift")
            if row["weighted_numerator"] != recomputed_numerator:
                raise QuantizedSoftmaxReceiptGateError("weighted-numerator recomputation drift")
            for dim, (output, remainder, numerator) in enumerate(
                zip(row["attention_output"], row["output_remainder"], row["weighted_numerator"], strict=True)
            ):
                if output != outputs[step_index][dim]:
                    raise QuantizedSoftmaxReceiptGateError("output row/list split-brain drift")
                if numerator != output * recomputed_denominator + remainder:
                    raise QuantizedSoftmaxReceiptGateError("quotient/remainder relation drift")
                if not (0 <= remainder < recomputed_denominator):
                    raise QuantizedSoftmaxReceiptGateError("remainder outside denominator bound")
                fraction = Fraction(remainder, recomputed_denominator)
                if fraction >= 1:
                    raise QuantizedSoftmaxReceiptGateError("division error bound drift")
                max_fraction = max(max_fraction, fraction)

    return {
        "score_rows": len(rows),
        "steps": len(outputs),
        "per_step_denominators": per_step_denominators,
        "max_observed_division_error_fraction": f"{max_fraction.numerator}/{max_fraction.denominator}",
        "max_observed_division_error_decimal": float(max_fraction),
    }


def kernel_contract(source: dict[str, Any]) -> dict[str, Any]:
    kernel_metrics = validate_quantized_kernel(source)
    return {
        "kernel_name": KERNEL_NAME,
        "kernel_status": KERNEL_STATUS,
        "real_softmax_status": REAL_SOFTMAX_STATUS,
        "score_domain": SCORE_DOMAIN,
        "score_scale": SCORE_SCALE,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "sequence_length": SEQUENCE_LENGTH,
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


def validate_kernel_contract(contract: dict[str, Any], source: dict[str, Any]) -> None:
    if contract != kernel_contract(source):
        raise QuantizedSoftmaxReceiptGateError("kernel contract drift")


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
        raise QuantizedSoftmaxReceiptGateError(f"unknown receipt field(s): {sorted(extra)}")
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
            raise QuantizedSoftmaxReceiptGateError(f"receipt drift for {key}")
    validate_kernel_contract(receipt.get("kernel_contract"), source)
    try:
        fused_gate.validate_fused_envelope(envelope, source, run_native=run_native)
    except Exception as err:  # noqa: BLE001 - normalize upstream gate errors for callers.
        raise QuantizedSoftmaxReceiptGateError(f"fused proof receipt drift: {err}") from err
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

    add("kernel_status_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("kernel_status", "GO_REAL_SOFTMAX"))
    add("kernel_name_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("kernel_name", "real_softmax"))
    add("claim_boundary_exact_softmax_overclaim", lambda r, _s, _e: r.__setitem__("claim_boundary", "GO_EXACT_REAL_VALUED_SOFTMAX"))
    add("real_softmax_status_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("real_softmax_status", "GO_REAL_SOFTMAX_ERROR_BOUND"))
    add("score_scale_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("score_scale", 2))
    add("key_width_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("key_width", 8))
    add("value_width_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("value_width", 8))
    add("sequence_length_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("sequence_length", 4))
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
    add("output_scale_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("output_scale", 256))
    add("division_error_bound_relabeling", lambda r, _s, _e: r["kernel_contract"].__setitem__("division_error_bound", "0"))
    add("table_error_bound_policy_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("table_error_bound_policy", "bounded error to real Softmax"))
    add("model_binding_status_overclaim", lambda r, _s, _e: r["kernel_contract"].__setitem__("model_binding_status", "trainable model weights bound"))
    add("source_input_score_scale_drift", lambda _r, s, e: (s.__setitem__("score_scale", 2), e.__setitem__("source_input", s)))
    add("source_input_key_width_drift", lambda _r, s, e: (s.__setitem__("key_width", 8), e.__setitem__("source_input", s)))
    add("source_input_value_width_drift", lambda _r, s, e: (s.__setitem__("value_width", 8), e.__setitem__("source_input", s)))
    add("source_input_sequence_length_drift", lambda _r, s, e: (s.__setitem__("sequence_length", 4), e.__setitem__("source_input", s)))
    add("source_input_clip_drift", lambda _r, s, e: (s.__setitem__("score_gap_clip", 7), e.__setitem__("source_input", s)))
    add("source_input_weight_policy_drift", lambda _r, s, e: (s.__setitem__("weight_policy", "float-exp"), e.__setitem__("source_input", s)))
    add("source_input_denominator_zero", lambda _r, s, e: (s["score_rows"][0].__setitem__("weight_denominator", 0), e.__setitem__("source_input", s)))
    add("source_input_weighted_value_drift", lambda _r, s, e: (s["score_rows"][0]["weighted_value"].__setitem__(0, 81), e.__setitem__("source_input", s)))
    add("source_input_weighted_numerator_drift", lambda _r, s, e: (s["score_rows"][0]["weighted_numerator"].__setitem__(0, 561), e.__setitem__("source_input", s)))
    add("source_input_remainder_drift", lambda _r, s, e: (s["score_rows"][0]["output_remainder"].__setitem__(0, 999), e.__setitem__("source_input", s)))
    add("fused_verifier_domain_relabeling", lambda _r, _s, e: e.__setitem__("verifier_domain", "different-domain"))
    add("fused_statement_version_relabeling", lambda _r, _s, e: e.__setitem__("statement_version", "different-statement"))
    add("fused_proof_byte_tamper", lambda _r, _s, e: mutate_same_size_fused_proof(e), run_native=True)
    add("unknown_receipt_key_injection", lambda r, _s, _e: r.__setitem__("unexpected", "claim smuggling"))
    return cases


def validate_mutation_results(mutation_results: Any) -> None:
    if not isinstance(mutation_results, list) or len(mutation_results) != EXPECTED_MUTATION_COUNT:
        raise QuantizedSoftmaxReceiptGateError("mutation result shape drift")
    if tuple(item.get("name") for item in mutation_results if isinstance(item, dict)) != EXPECTED_MUTATION_NAMES:
        raise QuantizedSoftmaxReceiptGateError("mutation result name drift")
    for item in mutation_results:
        if not isinstance(item, dict) or set(item) != {"name", "rejected", "error"}:
            raise QuantizedSoftmaxReceiptGateError("mutation result schema drift")
        if item["rejected"] is not True or not isinstance(item["error"], str) or not item["error"]:
            raise QuantizedSoftmaxReceiptGateError("mutation result rejection drift")


def stable_mutation_error(error: str) -> str:
    native_rejection_prefix = "fused proof receipt drift: native fused verifier rejected in-memory fused envelope"
    if error.startswith(native_rejection_prefix):
        return native_rejection_prefix
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
        except QuantizedSoftmaxReceiptGateError as err:
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    return mutation_results


def validate_recomputed_mutation_results(result: dict[str, Any], recomputed: list[dict[str, Any]]) -> None:
    validate_mutation_results(recomputed)
    serialized = result.get("mutation_results")
    validate_mutation_results(serialized)
    serialized_details = tuple((item["name"], item["rejected"], stable_mutation_error(item["error"])) for item in serialized)
    recomputed_details = tuple((item["name"], item["rejected"], stable_mutation_error(item["error"])) for item in recomputed)
    if serialized_details != recomputed_details:
        raise QuantizedSoftmaxReceiptGateError("recomputed mutation result detail drift")
    if result.get("mutations_rejected") != sum(1 for item in recomputed if item["rejected"]):
        raise QuantizedSoftmaxReceiptGateError("recomputed mutation rejection count drift")


def build_base_receipt(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "source_arithmetic_issue": SOURCE_ARITHMETIC_ISSUE,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "kernel_contract": kernel_contract(source),
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
    # This validates the previous fused proof artifact, including the native CLI proof verifier.
    fused_gate.run_gate()

    receipt = build_base_receipt(source)
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
    row = {
        "decision": result["decision"],
        "route_id": result["route_id"],
        "kernel_name": result["kernel_contract"]["kernel_name"],
        "fused_proof_size_bytes": result["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": result["fused_envelope_size_bytes"],
        "key_width": result["kernel_contract"]["key_width"],
        "value_width": result["kernel_contract"]["value_width"],
        "sequence_length": result["kernel_contract"]["sequence_length"],
        "lookup_claims": result["lookup_claims"],
        "table_rows": result["table_rows"],
        "score_gap_clip": result["kernel_contract"]["score_gap_clip"],
        "division_error_bound": result["kernel_contract"]["division_error_bound"],
        "real_softmax_status": result["kernel_contract"]["real_softmax_status"],
        "mutations_checked": result["mutations_checked"],
        "mutations_rejected": result["mutations_rejected"],
        "source_statement_commitment": result["kernel_contract"]["source_statement_commitment"],
        "source_weight_table_commitment": result["kernel_contract"]["weight_table_commitment"],
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
            raise QuantizedSoftmaxReceiptGateError("TSV round-trip drift")
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
