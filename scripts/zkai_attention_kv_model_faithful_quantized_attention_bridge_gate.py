#!/usr/bin/env python3
"""Checked model-facing quantized attention bridge for the bounded Softmax-table fixture.

This gate does not wire a full model runtime. It proves the narrower bridge we
need first: the existing checked d8 bounded Softmax-table fixture trace is
exactly the trace produced by a model-facing integer attention policy with score
scale 1, per-step max subtraction, clipped gap cap 8, the literal table, positive
denominators, Euclidean floor division, and remainders below the denominator.
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
from fractions import Fraction
from typing import Any, Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_kv_quantized_softmax_receipt_gate as receipt_gate  # noqa: E402
from scripts import zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input as fixture_gate  # noqa: E402

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_FIXTURE_JSON = fixture_gate.JSON_OUT
QUANTIZED_RECEIPT_JSON = receipt_gate.JSON_OUT
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.tsv"

MAX_INPUT_JSON_BYTES = 1_048_576

SCHEMA = "zkai-attention-kv-model-faithful-quantized-attention-bridge-gate-v1"
DECISION = "GO_MODEL_FAITHFUL_QUANTIZED_ATTENTION_BRIDGE_FOR_CHECKED_D8_FIXTURE"
ROUTE_ID = "local_model_faithful_quantized_attention_bridge_d8_bounded_softmax_table"
SOURCE_FIXTURE_ISSUE = 463
FUSED_RECEIPT_ISSUE = 485
FUSED_PROOF_ISSUE = 478
CLAIM_BOUNDARY = (
    "CHECKED_EQUIVALENCE_BETWEEN_A_MODEL_FACING_INTEGER_ATTENTION_POLICY_AND_THE_EXISTING_D8_"
    "BOUNDED_SOFTMAX_TABLE_FIXTURE_TRACE_NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_PRODUCTION"
)

POLICY_NAME = "model_facing_bounded_quantized_attention_v1"
KERNEL_NAME = receipt_gate.KERNEL_NAME
SCORE_SCALE = receipt_gate.SCORE_SCALE
MAX_SUBTRACTION_POLICY = receipt_gate.MAX_SUBTRACTION_POLICY
SCORE_GAP_CLIP = receipt_gate.SCORE_GAP_CLIP
CLIP_POLICY = receipt_gate.CLIP_POLICY
DENOMINATOR_POLICY = receipt_gate.DENOMINATOR_POLICY
DIVISION_RULE = receipt_gate.DIVISION_RULE
REMAINDER_POLICY = "0 <= remainder < denominator for every output coordinate"
OUTPUT_SCALE_POLICY = receipt_gate.OUTPUT_SCALE_POLICY
MASKING_POLICY = fixture_gate.MASKING_POLICY
EXPECTED_WEIGHT_TABLE = [dict(entry) for entry in receipt_gate.EXPECTED_WEIGHT_TABLE]

NON_CLAIMS = [
    "not exact real-valued Softmax",
    "not full inference",
    "not public benchmark",
    "not production",
    "not accuracy or perplexity evidence",
    "not a tokenizer, model-weight, or runtime integration",
    "not an error bound against mathematical exp/div Softmax",
]

BLOCKERS = [
    "full transformer runtime is not wired to this policy yet",
    "no tokenizer/model-weight import path is bound to this fixture",
    "no accuracy or perplexity delta against a real quantized model is measured",
    "only the existing checked d8 fixture trace is bridged",
    "production verifier and Starknet deployment surfaces are out of scope",
]

VALIDATION_COMMANDS = [
    "just gate-fast",
    "python3 scripts/zkai_attention_kv_model_faithful_quantized_attention_bridge_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_model_faithful_quantized_attention_bridge_gate",
    "git diff --check",
    "just gate",
]

EXPECTED_MUTATION_NAMES = (
    "policy_name_relabeling",
    "claim_boundary_real_softmax_overclaim",
    "score_scale_drift",
    "max_subtraction_policy_drift",
    "clip_cap_drift",
    "weight_table_value_drift",
    "denominator_policy_drift",
    "division_rule_drift",
    "remainder_policy_removed",
    "non_claim_removed",
    "blocker_removed",
    "source_fixture_output_drift",
    "source_fixture_score_gap_drift",
    "source_fixture_denominator_zero",
    "source_fixture_remainder_drift",
    "source_fixture_statement_commitment_drift",
    "receipt_kernel_status_overclaim",
    "receipt_weight_table_drift",
    "receipt_source_commitment_drift",
    "unknown_bridge_field_injection",
)
EXPECTED_MUTATION_COUNT = len(EXPECTED_MUTATION_NAMES)

TSV_COLUMNS = (
    "decision",
    "route_id",
    "policy_name",
    "kernel_name",
    "fixture_statement_commitment",
    "fixture_score_row_commitment",
    "model_trace_commitment",
    "score_rows",
    "steps",
    "value_width",
    "score_scale",
    "score_gap_clip",
    "denominator_min",
    "denominator_max",
    "max_observed_division_error_fraction",
    "equivalence_mismatches",
    "mutations_checked",
    "mutations_rejected",
)


class ModelFaithfulQuantizedAttentionBridgeGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def commitment_from_parts(parts: list[tuple[str, Any]], domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    for label, value in parts:
        digest.update(str(label).encode("utf-8"))
        digest.update(b"=")
        digest.update(canonical_json_bytes(value))
        digest.update(b"\n")
    return f"blake2b-256:{digest.hexdigest()}"


def read_json(path: pathlib.Path, max_bytes: int, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"{label} must not be a symlink")
    size = path.stat().st_size
    if size > max_bytes:
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"{label} exceeds byte bound")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"{label} must be an object")
    return value


def prepare_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise ModelFaithfulQuantizedAttentionBridgeGateError("output path must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ModelFaithfulQuantizedAttentionBridgeGateError("output parent must not be a symlink")
    return path


def load_fixture_payload() -> dict[str, Any]:
    payload = read_json(SOURCE_FIXTURE_JSON, MAX_INPUT_JSON_BYTES, "bounded Softmax-table fixture")
    try:
        fixture_gate.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - preserve upstream validator detail.
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"source fixture validation drift: {err}") from err
    return payload


def load_quantized_receipt() -> dict[str, Any]:
    receipt = read_json(QUANTIZED_RECEIPT_JSON, MAX_INPUT_JSON_BYTES, "quantized Softmax receipt")
    try:
        receipt_gate.validate_result(receipt, run_native=False)
    except Exception as err:  # noqa: BLE001 - preserve upstream validator detail.
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"quantized receipt validation drift: {err}") from err
    return receipt


def require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"{label} must be an integer")
    return value


def require_vector(value: Any, *, width: int, label: str) -> list[int]:
    if not isinstance(value, list) or len(value) != width:
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"{label} width drift")
    return [require_int(item, f"{label}[{index}]") for index, item in enumerate(value)]


def weight_by_gap() -> dict[int, int]:
    return {entry["gap"]: entry["weight"] for entry in EXPECTED_WEIGHT_TABLE}


def dot(lhs: list[int], rhs: list[int]) -> int:
    if len(lhs) != len(rhs):
        raise ModelFaithfulQuantizedAttentionBridgeGateError("dot-product width mismatch")
    return sum(left * right for left, right in zip(lhs, rhs, strict=True))


def div_euclid_positive_denominator(numerator: int, denominator: int) -> tuple[int, int]:
    if denominator <= 0:
        raise ModelFaithfulQuantizedAttentionBridgeGateError("division denominator must be positive")
    quotient = numerator // denominator
    remainder = numerator - quotient * denominator
    if not (0 <= remainder < denominator):
        raise ModelFaithfulQuantizedAttentionBridgeGateError("Euclidean remainder bound failed")
    return quotient, remainder


def model_policy() -> dict[str, Any]:
    return {
        "policy_name": POLICY_NAME,
        "kernel_name": KERNEL_NAME,
        "score_scale": SCORE_SCALE,
        "score_rule": "score = dot(query, key) / score_scale with score_scale fixed to 1",
        "max_subtraction_policy": MAX_SUBTRACTION_POLICY,
        "clip_policy": CLIP_POLICY,
        "score_gap_clip": SCORE_GAP_CLIP,
        "weight_table": copy.deepcopy(EXPECTED_WEIGHT_TABLE),
        "denominator_policy": DENOMINATOR_POLICY,
        "division_rule": DIVISION_RULE,
        "remainder_policy": REMAINDER_POLICY,
        "output_scale_policy": OUTPUT_SCALE_POLICY,
        "masking_policy": MASKING_POLICY,
    }


def build_model_trace(payload: dict[str, Any]) -> dict[str, Any]:
    key_width = require_int(payload.get("key_width"), "key_width")
    value_width = require_int(payload.get("value_width"), "value_width")
    initial = payload.get("initial_kv_cache")
    steps = payload.get("input_steps")
    if not isinstance(initial, list) or not isinstance(steps, list):
        raise ModelFaithfulQuantizedAttentionBridgeGateError("fixture initial/input rows must be lists")

    current: list[dict[str, Any]] = []
    for index, item in enumerate(initial):
        if not isinstance(item, dict):
            raise ModelFaithfulQuantizedAttentionBridgeGateError("initial KV item must be an object")
        current.append({
            "position": require_int(item.get("position"), f"initial_kv[{index}].position"),
            "key": require_vector(item.get("key"), width=key_width, label=f"initial_kv[{index}].key"),
            "value": require_vector(item.get("value"), width=value_width, label=f"initial_kv[{index}].value"),
        })

    table = weight_by_gap()
    rows: list[dict[str, Any]] = []
    outputs: list[list[int]] = []
    per_step_denominators: list[int] = []
    max_fraction = Fraction(0, 1)

    for step_index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ModelFaithfulQuantizedAttentionBridgeGateError("input step must be an object")
        token_position = require_int(step.get("token_position"), f"input_steps[{step_index}].token_position")
        query = require_vector(step.get("query"), width=key_width, label=f"input_steps[{step_index}].query")
        next_item = {
            "position": token_position,
            "key": require_vector(step.get("new_key"), width=key_width, label=f"input_steps[{step_index}].new_key"),
            "value": require_vector(step.get("new_value"), width=value_width, label=f"input_steps[{step_index}].new_value"),
        }
        candidates = current + [next_item]
        allowed = [candidate for candidate in candidates if require_int(candidate["position"], "candidate.position") <= token_position]
        if not allowed:
            raise ModelFaithfulQuantizedAttentionBridgeGateError("model policy produced no allowed candidates")

        scored = [(candidate, dot(query, candidate["key"]) // SCORE_SCALE) for candidate in allowed]
        max_score = max(score for _candidate, score in scored)
        weights = [table[min(max_score - score, SCORE_GAP_CLIP)] for _candidate, score in scored]
        denominator = sum(weights)
        if denominator <= 0:
            raise ModelFaithfulQuantizedAttentionBridgeGateError("model policy produced nonpositive denominator")
        per_step_denominators.append(denominator)

        numerators = [0 for _ in range(value_width)]
        for (candidate, _score), weight in zip(scored, weights, strict=True):
            for dim, value in enumerate(candidate["value"]):
                numerators[dim] += weight * value

        output: list[int] = []
        remainders: list[int] = []
        for dim, numerator in enumerate(numerators):
            quotient, remainder = div_euclid_positive_denominator(numerator, denominator)
            output.append(quotient)
            remainders.append(remainder)
            max_fraction = max(max_fraction, Fraction(remainder, denominator))
        outputs.append(output)

        for candidate_index, ((candidate, score), weight) in enumerate(zip(scored, weights, strict=True)):
            score_gap = max_score - score
            if score_gap < 0:
                raise ModelFaithfulQuantizedAttentionBridgeGateError("negative score gap")
            products = [left * right for left, right in zip(query, candidate["key"], strict=True)]
            weighted_value = [weight * value for value in candidate["value"]]
            rows.append({
                "row_index": len(rows),
                "step_index": step_index,
                "candidate_index": candidate_index,
                "token_position": token_position,
                "candidate_position": candidate["position"],
                "mask_allowed": 1,
                "selected_score": max_score,
                "score": score,
                "score_gap": score_gap,
                "causal_gap": token_position - candidate["position"],
                "attention_weight": weight,
                "weight_denominator": denominator,
                "query": list(query),
                "key": list(candidate["key"]),
                "value": list(candidate["value"]),
                "products": products,
                "weighted_value": weighted_value,
                "weighted_numerator": list(numerators),
                "attention_output": list(output),
                "output_remainder": list(remainders),
            })
        current = candidates

    return {
        "score_rows": rows,
        "attention_outputs": outputs,
        "final_kv_cache": current,
        "per_step_denominators": per_step_denominators,
        "max_observed_division_error_fraction": f"{max_fraction.numerator}/{max_fraction.denominator}",
        "max_observed_division_error_decimal": float(max_fraction),
    }


def model_trace_commitment(trace: dict[str, Any]) -> str:
    return commitment_from_parts(
        [
            ("policy_name", POLICY_NAME),
            ("score_rows_sha256", sha256_hex(trace["score_rows"])),
            ("attention_outputs_sha256", sha256_hex(trace["attention_outputs"])),
            ("final_kv_cache_sha256", sha256_hex(trace["final_kv_cache"])),
        ],
        "ptvm:zkai:attention-kv-model-faithful-quantized-attention-bridge:v1",
    )


def policy_commitment() -> str:
    return commitment_from_parts(
        [
            ("policy", model_policy()),
            ("non_claims", NON_CLAIMS),
            ("blockers", BLOCKERS),
        ],
        "ptvm:zkai:attention-kv-model-facing-quantized-attention-policy:v1",
    )


def validate_fixture_equivalence(payload: dict[str, Any]) -> dict[str, Any]:
    trace = build_model_trace(payload)
    comparisons = {
        "score_rows_match": trace["score_rows"] == payload.get("score_rows"),
        "attention_outputs_match": trace["attention_outputs"] == payload.get("attention_outputs"),
        "final_kv_cache_match": trace["final_kv_cache"] == payload.get("final_kv_cache"),
        "weight_table_match": payload.get("weight_table") == EXPECTED_WEIGHT_TABLE,
        "score_scale_match": payload.get("score_scale") == SCORE_SCALE,
        "score_gap_clip_match": payload.get("score_gap_clip") == SCORE_GAP_CLIP,
        "denominators_positive": all(denominator > 0 for denominator in trace["per_step_denominators"]),
    }
    if not all(comparisons.values()):
        failed = [name for name, ok in comparisons.items() if not ok]
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"model/fixture equivalence drift: {failed}")
    return {
        "status": "GO_EQUIVALENT_FOR_EXISTING_CHECKED_FIXTURE_TRACE",
        "comparisons": comparisons,
        "equivalence_mismatches": 0,
        "model_trace_commitment": model_trace_commitment(trace),
        "model_trace_sha256": sha256_hex({
            "score_rows": trace["score_rows"],
            "attention_outputs": trace["attention_outputs"],
            "final_kv_cache": trace["final_kv_cache"],
        }),
        "per_step_denominators": trace["per_step_denominators"],
        "denominator_min": min(trace["per_step_denominators"]),
        "denominator_max": max(trace["per_step_denominators"]),
        "max_observed_division_error_fraction": trace["max_observed_division_error_fraction"],
        "max_observed_division_error_decimal": trace["max_observed_division_error_decimal"],
    }


def bridge_metrics(payload: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    equivalence = validate_fixture_equivalence(payload)
    receipt_metrics = receipt["kernel_contract"]["kernel_metrics"]
    if receipt_metrics["per_step_denominators"] != equivalence["per_step_denominators"]:
        raise ModelFaithfulQuantizedAttentionBridgeGateError("receipt denominator metrics drift")
    if receipt_metrics["max_observed_division_error_fraction"] != equivalence["max_observed_division_error_fraction"]:
        raise ModelFaithfulQuantizedAttentionBridgeGateError("receipt division-error metric drift")
    return {
        "source_fixture_json": str(SOURCE_FIXTURE_JSON.relative_to(ROOT)),
        "quantized_receipt_json": str(QUANTIZED_RECEIPT_JSON.relative_to(ROOT)),
        "fixture_statement_commitment": payload["statement_commitment"],
        "fixture_score_row_commitment": payload["score_row_commitment"],
        "fixture_outputs_commitment": payload["outputs_commitment"],
        "fixture_weight_table_commitment": payload["weight_table_commitment"],
        "receipt_route_id": receipt["route_id"],
        "receipt_mutations_rejected": receipt["mutations_rejected"],
        "fused_proof_size_bytes": receipt["fused_proof_size_bytes"],
        "fused_envelope_size_bytes": receipt["fused_envelope_size_bytes"],
        "score_rows": len(payload["score_rows"]),
        "steps": len(payload["attention_outputs"]),
        "key_width": payload["key_width"],
        "value_width": payload["value_width"],
        "trace_rows": payload["trace_row_count"],
        "table_rows": len(EXPECTED_WEIGHT_TABLE),
        **equivalence,
    }


def bridge_contract(payload: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy_commitment": policy_commitment(),
        "model_policy": model_policy(),
        "metrics": bridge_metrics(payload, receipt),
        "non_claims": list(NON_CLAIMS),
        "blockers": list(BLOCKERS),
    }


def build_base_result(payload: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "source_fixture_issue": SOURCE_FIXTURE_ISSUE,
        "fused_receipt_issue": FUSED_RECEIPT_ISSUE,
        "fused_proof_issue": FUSED_PROOF_ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "bridge_contract": bridge_contract(payload, receipt),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutation_results": [],
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }


def validate_mutation_results(value: Any) -> None:
    if not isinstance(value, list) or len(value) != EXPECTED_MUTATION_COUNT:
        raise ModelFaithfulQuantizedAttentionBridgeGateError("mutation result shape drift")
    if tuple(item.get("name") for item in value if isinstance(item, dict)) != EXPECTED_MUTATION_NAMES:
        raise ModelFaithfulQuantizedAttentionBridgeGateError("mutation result name drift")
    for item in value:
        if not isinstance(item, dict) or set(item) != {"name", "rejected", "error"}:
            raise ModelFaithfulQuantizedAttentionBridgeGateError("mutation result schema drift")
        if item["rejected"] is not True or not isinstance(item["error"], str) or not item["error"]:
            raise ModelFaithfulQuantizedAttentionBridgeGateError("mutation result rejection drift")


def validate_result(result: dict[str, Any], payload: dict[str, Any] | None = None, receipt: dict[str, Any] | None = None) -> None:
    payload = load_fixture_payload() if payload is None else payload
    receipt = load_quantized_receipt() if receipt is None else receipt
    try:
        fixture_gate.validate_payload(payload)
        receipt_gate.validate_result(receipt, run_native=False)
    except Exception as err:  # noqa: BLE001 - normalize upstream validation detail.
        raise ModelFaithfulQuantizedAttentionBridgeGateError(str(err)) from err

    allowed = {
        "schema",
        "decision",
        "route_id",
        "source_fixture_issue",
        "fused_receipt_issue",
        "fused_proof_issue",
        "claim_boundary",
        "bridge_contract",
        "validation_commands",
        "mutation_results",
        "mutations_checked",
        "mutations_rejected",
    }
    extra = set(result) - allowed
    if extra:
        raise ModelFaithfulQuantizedAttentionBridgeGateError(f"unknown bridge field(s): {sorted(extra)}")
    expected = {
        "schema": SCHEMA,
        "decision": DECISION,
        "route_id": ROUTE_ID,
        "source_fixture_issue": SOURCE_FIXTURE_ISSUE,
        "fused_receipt_issue": FUSED_RECEIPT_ISSUE,
        "fused_proof_issue": FUSED_PROOF_ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "bridge_contract": bridge_contract(payload, receipt),
        "validation_commands": list(VALIDATION_COMMANDS),
        "mutations_checked": EXPECTED_MUTATION_COUNT,
        "mutations_rejected": EXPECTED_MUTATION_COUNT,
    }
    for key, expected_value in expected.items():
        if result.get(key) != expected_value:
            raise ModelFaithfulQuantizedAttentionBridgeGateError(f"result {key} drift")
    validate_mutation_results(result.get("mutation_results"))


def mutation_cases(
    result: dict[str, Any],
    payload: dict[str, Any],
    receipt: dict[str, Any],
) -> list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]] = []

    def add(name: str, mutator: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None]) -> None:
        result_copy = copy.deepcopy(result)
        payload_copy = copy.deepcopy(payload)
        receipt_copy = copy.deepcopy(receipt)
        mutator(result_copy, payload_copy, receipt_copy)
        cases.append((name, result_copy, payload_copy, receipt_copy))

    add("policy_name_relabeling", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("policy_name", "float_attention"))
    add("claim_boundary_real_softmax_overclaim", lambda r, _p, _q: r.__setitem__("claim_boundary", "GO_EXACT_REAL_VALUED_SOFTMAX"))
    add("score_scale_drift", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("score_scale", 2))
    add("max_subtraction_policy_drift", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("max_subtraction_policy", "none"))
    add("clip_cap_drift", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("score_gap_clip", 7))
    add("weight_table_value_drift", lambda r, _p, _q: r["bridge_contract"]["model_policy"]["weight_table"][1].__setitem__("weight", 182))
    add("denominator_policy_drift", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("denominator_policy", "external"))
    add("division_rule_drift", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("division_rule", "round_to_nearest"))
    add("remainder_policy_removed", lambda r, _p, _q: r["bridge_contract"]["model_policy"].__setitem__("remainder_policy", "unchecked"))
    add("non_claim_removed", lambda r, _p, _q: r["bridge_contract"]["non_claims"].remove("not exact real-valued Softmax"))
    add("blocker_removed", lambda r, _p, _q: r["bridge_contract"]["blockers"].remove("full transformer runtime is not wired to this policy yet"))
    add("source_fixture_output_drift", lambda _r, p, _q: p["attention_outputs"][0].__setitem__(0, 999))
    add("source_fixture_score_gap_drift", lambda _r, p, _q: p["score_rows"][0].__setitem__("score_gap", 1))
    add("source_fixture_denominator_zero", lambda _r, p, _q: p["score_rows"][0].__setitem__("weight_denominator", 0))
    add("source_fixture_remainder_drift", lambda _r, p, _q: p["score_rows"][0]["output_remainder"].__setitem__(0, 999))
    add("source_fixture_statement_commitment_drift", lambda _r, p, _q: p.__setitem__("statement_commitment", "blake2b-256:" + "55" * 32))
    add("receipt_kernel_status_overclaim", lambda _r, _p, q: q["kernel_contract"].__setitem__("kernel_status", "GO_REAL_SOFTMAX"))
    add("receipt_weight_table_drift", lambda _r, _p, q: q["kernel_contract"]["weight_table"][1].__setitem__("weight", 182))
    add("receipt_source_commitment_drift", lambda _r, _p, q: q["kernel_contract"].__setitem__("source_statement_commitment", "blake2b-256:" + "55" * 32))
    add("unknown_bridge_field_injection", lambda r, _p, _q: r.__setitem__("unexpected", "claim smuggling"))
    return cases


def run_gate() -> dict[str, Any]:
    payload = load_fixture_payload()
    receipt = load_quantized_receipt()
    result = build_base_result(payload, receipt)
    mutation_results = []
    for name, mutated_result, mutated_payload, mutated_receipt in mutation_cases(result, payload, receipt):
        try:
            validate_result(mutated_result, mutated_payload, mutated_receipt)
        except Exception as err:  # noqa: BLE001 - gate records exact rejection surface.
            mutation_results.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_results.append({"name": name, "rejected": False, "error": "mutation accepted"})
    result["mutation_results"] = mutation_results
    result["mutations_rejected"] = sum(1 for item in mutation_results if item["rejected"])
    validate_result(result, payload, receipt)
    return result


def write_json(path: pathlib.Path, result: dict[str, Any]) -> None:
    validate_result(result)
    path = prepare_output_path(path)
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
    validate_result(result)
    path = prepare_output_path(path)
    metrics = result["bridge_contract"]["metrics"]
    row = {
        "decision": result["decision"],
        "route_id": result["route_id"],
        "policy_name": result["bridge_contract"]["model_policy"]["policy_name"],
        "kernel_name": result["bridge_contract"]["model_policy"]["kernel_name"],
        "fixture_statement_commitment": metrics["fixture_statement_commitment"],
        "fixture_score_row_commitment": metrics["fixture_score_row_commitment"],
        "model_trace_commitment": metrics["model_trace_commitment"],
        "score_rows": metrics["score_rows"],
        "steps": metrics["steps"],
        "value_width": metrics["value_width"],
        "score_scale": result["bridge_contract"]["model_policy"]["score_scale"],
        "score_gap_clip": result["bridge_contract"]["model_policy"]["score_gap_clip"],
        "denominator_min": metrics["denominator_min"],
        "denominator_max": metrics["denominator_max"],
        "max_observed_division_error_fraction": metrics["max_observed_division_error_fraction"],
        "equivalence_mismatches": metrics["equivalence_mismatches"],
        "mutations_checked": result["mutations_checked"],
        "mutations_rejected": result["mutations_rejected"],
    }
    expected = {column: str(row[column]) for column in TSV_COLUMNS}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        tmp_path = pathlib.Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    try:
        with tmp_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        if rows != [expected]:
            raise ModelFaithfulQuantizedAttentionBridgeGateError("TSV round-trip drift")
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
