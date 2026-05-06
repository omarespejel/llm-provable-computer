#!/usr/bin/env python3
"""Checked two-point proof-size profile for native Stwo attention/KV receipts.

This gate profiles the checked single-head and two-head d8 bounded weighted
attention/KV proof artifacts. It deliberately reports a two-point engineering
profile only: useful for spotting fixed-overhead behavior, not sufficient for a
paper scaling law or public benchmark row.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import pathlib
from types import ModuleType
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SINGLE_GATE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_d8_bounded_weighted_native_gate.py"
TWO_HEAD_GATE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_two_head_bounded_weighted_native_gate.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-native-proof-size-profile-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-native-proof-size-profile-2026-05.tsv"

SCHEMA = "zkai-attention-kv-native-proof-size-profile-gate-v1"
ISSUE = 467
SOURCE_ISSUES = (460, 461)
DECISION = "GO_TWO_POINT_NATIVE_STWO_ATTENTION_KV_PROOF_SIZE_PROFILE_ENGINEERING_ONLY"
CLAIM_BOUNDARY = (
    "TWO_POINT_NATIVE_STWO_D8_BOUNDED_WEIGHTED_ATTENTION_KV_PROOF_SIZE_PROFILE_"
    "NOT_SCALING_LAW_NOT_TIMING_BENCHMARK_NOT_EXACT_SOFTMAX_NOT_FULL_INFERENCE"
)
FIRST_BLOCKER = "CONTROLLED_HEAD_SEQUENCE_GRID_AND_BINARY_PROOF_COMPONENT_ACCOUNTING_MISSING"
TIMING_POLICY = "no_new_timing_two_point_engineering_profile_only"
PROFILE_INTERPRETATION = (
    "proof_bytes_sublinear_on_two_checked_points_likely_fixed_overhead_dominated_"
    "but_not_a_scaling_law"
)
PROOF_COMPONENT_BYTE_BREAKDOWN_STATUS = "TOP_LEVEL_STARK_PROOF_JSON_SECTION_BYTES_AVAILABLE_NOT_BINARY_PCS_FRI_INNER_ACCOUNTING"
STRUCTURAL_BREAKDOWN_STATUS = "ROW_COUNTS_AND_TOP_LEVEL_PROOF_SECTIONS_AVAILABLE_COLUMNS_NOT_EXPOSED_BY_CURRENT_GATE"
CONTROLLED_GRID_STATUS = "PARTIAL_SEQ8_ONLY_GRID_SEQ4_SEQ16_AND_4_HEAD_MISSING"
MISSING_TIMING_STATUS = "NOT_MEASURED_BY_THIS_PROFILE_TIMING_POLICY_REQUIRES_SEPARATE_MEDIAN_RUN"
MISSING_COLUMN_STATUS = "NOT_EXPOSED_BY_CURRENT_NATIVE_GATE"
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
STRUCTURAL_BREAKDOWN = {
    "preprocessed_columns": MISSING_COLUMN_STATUS,
    "base_trace_columns": MISSING_COLUMN_STATUS,
    "extension_columns": MISSING_COLUMN_STATUS,
    "pcs_fri_config": PROOF_CONFIG,
    "prover_time_ms": MISSING_TIMING_STATUS,
    "verifier_time_ms": MISSING_TIMING_STATUS,
}
CONTROLLED_GRID_COVERAGE = {
    "status": CONTROLLED_GRID_STATUS,
    "covered_points": [
        {"head_count": 1, "sequence_length_per_head": 8, "key_width": 8, "value_width": 8},
        {"head_count": 2, "sequence_length_per_head": 8, "key_width": 8, "value_width": 8},
    ],
    "missing_points": [
        {"head_count": 1, "sequence_length_per_head": 4, "key_width": 8, "value_width": 8},
        {"head_count": 1, "sequence_length_per_head": 16, "key_width": 8, "value_width": 8},
        {"head_count": 2, "sequence_length_per_head": 4, "key_width": 8, "value_width": 8},
        {"head_count": 2, "sequence_length_per_head": 16, "key_width": 8, "value_width": 8},
        {"head_count": 4, "sequence_length_per_head": 8, "key_width": 8, "value_width": 8},
    ],
}
PROOF_SECTION_KEYS = (
    "config",
    "commitments",
    "sampled_values",
    "decommitments",
    "queried_values",
    "proof_of_work",
    "fri_proof",
)

SINGLE_ROUTE_ID = "local_stwo_attention_kv_d8_bounded_weighted_masked_sequence_proof"
TWO_HEAD_ROUTE_ID = "local_stwo_attention_kv_two_head_bounded_weighted_masked_sequence_proof"
SEMANTICS = "bounded_power2_weighted_attention"
WEIGHT_POLICY = "power2_gap_clipped_4_floor_division"
PROOF_BACKEND = "stwo"
PROOF_SYSTEM = "Stwo"
WIDTH = 8
SEQUENCE_LENGTH_PER_HEAD = 8

EXPECTED_SINGLE = {
    "label": "single_head_d8_seq8_bounded_weighted",
    "source_issue": 460,
    "route_id": SINGLE_ROUTE_ID,
    "head_count": 1,
    "key_width": WIDTH,
    "value_width": WIDTH,
    "sequence_length_per_head": SEQUENCE_LENGTH_PER_HEAD,
    "score_rows": 52,
    "trace_rows": 64,
    "proof_size_bytes": 36769,
    "envelope_size_bytes": 386078,
    "statement_commitment": "blake2b-256:9f5d0a15b4a5f5a8481f39ffad44df58824b773375163f2f0908b847082e7b5a",
    "gate_commitment": "blake2b-256:35080c62c241d928b091226c09ca95696fffcb68162a77106771e0686c650659",
    "proof_section_bytes": {
        "config": 136,
        "commitments": 335,
        "sampled_values": 15066,
        "decommitments": 5408,
        "queried_values": 9801,
        "proof_of_work": 4,
        "fri_proof": 5894,
    },
    "proof_section_payload_bytes_total": 36644,
    "proof_json_wrapper_bytes": 125,
    "proof_config": PROOF_CONFIG,
    "structural_breakdown": STRUCTURAL_BREAKDOWN,
}
EXPECTED_TWO_HEAD = {
    "label": "two_head_d8_seq8_bounded_weighted",
    "source_issue": 461,
    "route_id": TWO_HEAD_ROUTE_ID,
    "head_count": 2,
    "key_width": WIDTH,
    "value_width": WIDTH,
    "sequence_length_per_head": SEQUENCE_LENGTH_PER_HEAD,
    "score_rows": 104,
    "trace_rows": 128,
    "proof_size_bytes": 41175,
    "envelope_size_bytes": 512060,
    "statement_commitment": "blake2b-256:57bbf22000a70ea241a43bcf3ecd79a723b497827ca5782d39577d8bb242810b",
    "gate_commitment": "blake2b-256:b4b46e78a9e6448bc99ae10f2998b01a30f108d1a59f98e1d5d14ec38e606117",
    "proof_section_bytes": {
        "config": 136,
        "commitments": 345,
        "sampled_values": 15701,
        "decommitments": 6504,
        "queried_values": 10329,
        "proof_of_work": 4,
        "fri_proof": 8031,
    },
    "proof_section_payload_bytes_total": 41050,
    "proof_json_wrapper_bytes": 125,
    "proof_config": PROOF_CONFIG,
    "structural_breakdown": STRUCTURAL_BREAKDOWN,
}

EXPECTED_MUTATION_NAMES = (
    "single_proof_size_metric_smuggling",
    "two_head_proof_size_metric_smuggling",
    "single_envelope_size_metric_smuggling",
    "two_head_envelope_size_metric_smuggling",
    "row_ratio_metric_smuggling",
    "proof_ratio_metric_smuggling",
    "fri_section_metric_smuggling",
    "grid_status_overclaim",
    "column_breakdown_overclaim",
    "source_gate_commitment_relabeling",
    "statement_commitment_relabeling",
    "claim_boundary_scaling_law_overclaim",
    "profile_interpretation_overclaim",
    "first_blocker_removed",
    "timing_policy_public_benchmark_overclaim",
    "proof_component_breakdown_overclaim",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = 18
MUTATION_CASE_KEYS = {"name", "rejected", "error"}
NON_CLAIMS = (
    "not a scaling law",
    "not a public performance benchmark row",
    "not a timing benchmark",
    "not exact Softmax attention",
    "not full autoregressive inference",
    "not long-context evidence",
    "not proof aggregation or recursion",
    "not a claim that binary PCS/FRI internals have been decomposed",
    "not full controlled-grid coverage",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_d8_bounded_weighted_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.tsv",
    "python3 scripts/zkai_attention_kv_two_head_bounded_weighted_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.tsv",
    "python3 scripts/zkai_attention_kv_proof_size_profile_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-native-proof-size-profile-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-native-proof-size-profile-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_proof_size_profile_gate",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "decision",
    "baseline_head_count",
    "scaled_head_count",
    "baseline_score_rows",
    "scaled_score_rows",
    "score_rows_ratio",
    "baseline_trace_rows",
    "scaled_trace_rows",
    "trace_rows_ratio",
    "baseline_proof_size_bytes",
    "scaled_proof_size_bytes",
    "proof_size_delta_bytes",
    "proof_size_ratio",
    "baseline_envelope_size_bytes",
    "scaled_envelope_size_bytes",
    "envelope_size_delta_bytes",
    "envelope_size_ratio",
    "proof_growth_vs_score_growth",
    "envelope_growth_vs_score_growth",
    "fri_proof_delta_bytes",
    "decommitments_delta_bytes",
    "proof_section_payload_delta_bytes",
    "proof_json_wrapper_delta_bytes",
    "proof_component_byte_breakdown_status",
    "mutations_checked",
    "mutations_rejected",
)


class AttentionKvProofSizeProfileGateError(ValueError):
    pass


def validate_mutation_spec() -> None:
    if len(EXPECTED_MUTATION_NAMES) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvProofSizeProfileGateError("mutation spec count drift")


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvProofSizeProfileGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


SINGLE_GATE_MODULE = load_script_module(SINGLE_GATE_SCRIPT, "zkai_attention_kv_d8_bounded_weighted_native_gate")
TWO_HEAD_GATE_MODULE = load_script_module(
    TWO_HEAD_GATE_SCRIPT,
    "zkai_attention_kv_two_head_bounded_weighted_native_gate",
)


def require_exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AttentionKvProofSizeProfileGateError(f"{label} must be an integer")
    return value


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise AttentionKvProofSizeProfileGateError("ratio denominator must be positive")
    return round(numerator / denominator, 12)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def proof_section_bytes_from_gate_module(gate_module: ModuleType) -> dict[str, Any]:
    envelope = gate_module.read_bounded_json(
        gate_module.ENVELOPE_JSON,
        gate_module.MAX_ENVELOPE_JSON_BYTES,
        "proof-size profile envelope",
    )
    proof = envelope.get("proof")
    if not isinstance(proof, list):
        raise AttentionKvProofSizeProfileGateError("proof must be a byte list")
    proof_bytes = bytearray()
    for index, value in enumerate(proof):
        if isinstance(value, bool) or not isinstance(value, int):
            raise AttentionKvProofSizeProfileGateError(f"proof byte[{index}] must be an integer")
        if value < 0 or value > 255:
            raise AttentionKvProofSizeProfileGateError(f"proof byte[{index}] outside byte range")
        proof_bytes.append(value)
    try:
        proof_payload = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvProofSizeProfileGateError(f"proof payload is not JSON: {err}") from err
    if not isinstance(proof_payload, dict) or set(proof_payload) != {"stark_proof"}:
        raise AttentionKvProofSizeProfileGateError("proof payload must contain only stark_proof")
    stark_proof = proof_payload["stark_proof"]
    if not isinstance(stark_proof, dict) or set(stark_proof) != set(PROOF_SECTION_KEYS):
        raise AttentionKvProofSizeProfileGateError("stark_proof section set drift")
    if stark_proof["config"] != PROOF_CONFIG:
        raise AttentionKvProofSizeProfileGateError("proof config drift")
    section_bytes = {key: len(canonical_json_bytes(stark_proof[key])) for key in PROOF_SECTION_KEYS}
    section_total = sum(section_bytes.values())
    wrapper_bytes = len(proof_bytes) - section_total
    if wrapper_bytes <= 0:
        raise AttentionKvProofSizeProfileGateError("proof wrapper byte accounting drift")
    return {
        "proof_section_bytes": section_bytes,
        "proof_section_payload_bytes_total": section_total,
        "proof_json_wrapper_bytes": wrapper_bytes,
        "proof_config": stark_proof["config"],
    }


def source_row_from_gate(gate_payload: dict[str, Any], *, expected: dict[str, Any], gate_module: ModuleType) -> dict[str, Any]:
    receipt = gate_payload.get("bounded_weighted_receipt")
    if not isinstance(receipt, dict):
        raise AttentionKvProofSizeProfileGateError("source gate missing bounded weighted receipt")
    section_accounting = proof_section_bytes_from_gate_module(gate_module)
    row = {
        "label": expected["label"],
        "source_issue": expected["source_issue"],
        "route_id": receipt.get("route_id"),
        "proof_system": receipt.get("proof_system"),
        "proof_backend": receipt.get("proof_backend"),
        "semantics": receipt.get("semantics"),
        "weight_policy": receipt.get("weight_policy"),
        "head_count": receipt.get("head_count", 1),
        "key_width": receipt.get("key_width"),
        "value_width": receipt.get("value_width"),
        "sequence_length_per_head": receipt.get("sequence_length"),
        "score_rows": receipt.get("score_rows"),
        "trace_rows": receipt.get("trace_rows"),
        "proof_size_bytes": receipt.get("proof_size_bytes"),
        "envelope_size_bytes": receipt.get("envelope_size_bytes"),
        "statement_commitment": receipt.get("statement_commitment"),
        "gate_commitment": gate_payload.get("gate_commitment"),
        "structural_breakdown": copy.deepcopy(STRUCTURAL_BREAKDOWN),
        **section_accounting,
    }
    validate_profile_row(row, expected=expected)
    return row


def validate_profile_row(row: Any, *, expected: dict[str, Any]) -> None:
    if not isinstance(row, dict):
        raise AttentionKvProofSizeProfileGateError("profile row must be object")
    expected_keys = {
        "label",
        "source_issue",
        "route_id",
        "proof_system",
        "proof_backend",
        "semantics",
        "weight_policy",
        "head_count",
        "key_width",
        "value_width",
        "sequence_length_per_head",
        "score_rows",
        "trace_rows",
        "proof_size_bytes",
        "envelope_size_bytes",
        "statement_commitment",
        "gate_commitment",
        "proof_section_bytes",
        "proof_section_payload_bytes_total",
        "proof_json_wrapper_bytes",
        "proof_config",
        "structural_breakdown",
    }
    if set(row) != expected_keys:
        raise AttentionKvProofSizeProfileGateError("profile row field drift")
    common_expected = {
        "proof_system": PROOF_SYSTEM,
        "proof_backend": PROOF_BACKEND,
        "semantics": SEMANTICS,
        "weight_policy": WEIGHT_POLICY,
    }
    for key, value in common_expected.items():
        if row.get(key) != value:
            raise AttentionKvProofSizeProfileGateError(f"profile row {key} drift")
    for key, value in expected.items():
        if isinstance(value, dict):
            if row.get(key) != value:
                raise AttentionKvProofSizeProfileGateError(f"profile row {key} drift")
        elif key.endswith("_bytes") or key in {
            "head_count",
            "key_width",
            "value_width",
            "sequence_length_per_head",
            "score_rows",
            "trace_rows",
            "source_issue",
        }:
            if require_exact_int(row.get(key), key) != value:
                raise AttentionKvProofSizeProfileGateError(f"profile row {key} drift")
        elif row.get(key) != value:
            raise AttentionKvProofSizeProfileGateError(f"profile row {key} drift")


def build_scaling_diagnostics(single: dict[str, Any], two_head: dict[str, Any]) -> dict[str, Any]:
    score_ratio = ratio(two_head["score_rows"], single["score_rows"])
    trace_ratio = ratio(two_head["trace_rows"], single["trace_rows"])
    proof_ratio = ratio(two_head["proof_size_bytes"], single["proof_size_bytes"])
    envelope_ratio = ratio(two_head["envelope_size_bytes"], single["envelope_size_bytes"])
    section_delta = {
        key: two_head["proof_section_bytes"][key] - single["proof_section_bytes"][key]
        for key in PROOF_SECTION_KEYS
    }
    section_growth = {
        key: ratio(two_head["proof_section_bytes"][key], single["proof_section_bytes"][key])
        for key in PROOF_SECTION_KEYS
    }
    diagnostics = {
        "axes_compared": "head_count_1_to_2_same_d8_same_sequence_length_per_head_same_bounded_weight_policy",
        "baseline_head_count": single["head_count"],
        "scaled_head_count": two_head["head_count"],
        "key_width_held_constant": True,
        "value_width_held_constant": True,
        "sequence_length_per_head_held_constant": True,
        "semantics_held_constant": True,
        "weight_policy_held_constant": True,
        "score_rows_ratio_fraction": {
            "numerator": two_head["score_rows"],
            "denominator": single["score_rows"],
        },
        "score_rows_ratio": score_ratio,
        "trace_rows_ratio_fraction": {
            "numerator": two_head["trace_rows"],
            "denominator": single["trace_rows"],
        },
        "trace_rows_ratio": trace_ratio,
        "proof_size_ratio_fraction": {
            "numerator": two_head["proof_size_bytes"],
            "denominator": single["proof_size_bytes"],
        },
        "proof_size_ratio": proof_ratio,
        "proof_size_delta_bytes": two_head["proof_size_bytes"] - single["proof_size_bytes"],
        "envelope_size_ratio_fraction": {
            "numerator": two_head["envelope_size_bytes"],
            "denominator": single["envelope_size_bytes"],
        },
        "envelope_size_ratio": envelope_ratio,
        "envelope_size_delta_bytes": two_head["envelope_size_bytes"] - single["envelope_size_bytes"],
        "proof_growth_vs_score_growth": ratio(two_head["proof_size_bytes"] * single["score_rows"], single["proof_size_bytes"] * two_head["score_rows"]),
        "envelope_growth_vs_score_growth": ratio(
            two_head["envelope_size_bytes"] * single["score_rows"],
            single["envelope_size_bytes"] * two_head["score_rows"],
        ),
        "proof_section_delta_bytes": section_delta,
        "proof_section_growth_ratios": section_growth,
        "proof_section_payload_delta_bytes": two_head["proof_section_payload_bytes_total"]
        - single["proof_section_payload_bytes_total"],
        "proof_json_wrapper_delta_bytes": two_head["proof_json_wrapper_bytes"] - single["proof_json_wrapper_bytes"],
        "largest_proof_section_delta": "fri_proof",
        "fri_proof_delta_bytes": section_delta["fri_proof"],
        "decommitments_delta_bytes": section_delta["decommitments"],
        "baseline_proof_bytes_per_score_row": ratio(single["proof_size_bytes"], single["score_rows"]),
        "scaled_proof_bytes_per_score_row": ratio(two_head["proof_size_bytes"], two_head["score_rows"]),
        "baseline_envelope_bytes_per_score_row": ratio(single["envelope_size_bytes"], single["score_rows"]),
        "scaled_envelope_bytes_per_score_row": ratio(two_head["envelope_size_bytes"], two_head["score_rows"]),
        "profile_interpretation": PROFILE_INTERPRETATION,
        "proof_component_byte_breakdown_status": PROOF_COMPONENT_BYTE_BREAKDOWN_STATUS,
    }
    validate_scaling_diagnostics(diagnostics, single, two_head)
    return diagnostics


def validate_scaling_diagnostics(axis: Any, single: dict[str, Any], two_head: dict[str, Any]) -> None:
    if not isinstance(axis, dict):
        raise AttentionKvProofSizeProfileGateError("scaling diagnostics must be object")
    expected_keys = {
        "axes_compared",
        "baseline_head_count",
        "scaled_head_count",
        "key_width_held_constant",
        "value_width_held_constant",
        "sequence_length_per_head_held_constant",
        "semantics_held_constant",
        "weight_policy_held_constant",
        "score_rows_ratio_fraction",
        "score_rows_ratio",
        "trace_rows_ratio_fraction",
        "trace_rows_ratio",
        "proof_size_ratio_fraction",
        "proof_size_ratio",
        "proof_size_delta_bytes",
        "envelope_size_ratio_fraction",
        "envelope_size_ratio",
        "envelope_size_delta_bytes",
        "proof_growth_vs_score_growth",
        "envelope_growth_vs_score_growth",
        "proof_section_delta_bytes",
        "proof_section_growth_ratios",
        "proof_section_payload_delta_bytes",
        "proof_json_wrapper_delta_bytes",
        "largest_proof_section_delta",
        "fri_proof_delta_bytes",
        "decommitments_delta_bytes",
        "baseline_proof_bytes_per_score_row",
        "scaled_proof_bytes_per_score_row",
        "baseline_envelope_bytes_per_score_row",
        "scaled_envelope_bytes_per_score_row",
        "profile_interpretation",
        "proof_component_byte_breakdown_status",
    }
    if set(axis) != expected_keys:
        raise AttentionKvProofSizeProfileGateError("scaling diagnostics field drift")
    validate_scaling_diagnostic_types(axis)
    expected = build_expected_scaling_diagnostics(single, two_head)
    if axis != expected:
        raise AttentionKvProofSizeProfileGateError("scaling diagnostics drift")


def validate_ratio_fraction(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise AttentionKvProofSizeProfileGateError(f"{label} fraction field drift")
    require_exact_int(value.get("numerator"), f"{label} numerator")
    require_exact_int(value.get("denominator"), f"{label} denominator")


def require_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, float):
        raise AttentionKvProofSizeProfileGateError(f"{label} must be a float")
    return value


def validate_scaling_diagnostic_types(axis: dict[str, Any]) -> None:
    for key in ("score_rows_ratio_fraction", "trace_rows_ratio_fraction", "proof_size_ratio_fraction", "envelope_size_ratio_fraction"):
        validate_ratio_fraction(axis.get(key), key)
    for key in (
        "baseline_head_count",
        "scaled_head_count",
        "proof_size_delta_bytes",
        "envelope_size_delta_bytes",
        "proof_section_payload_delta_bytes",
        "proof_json_wrapper_delta_bytes",
        "fri_proof_delta_bytes",
        "decommitments_delta_bytes",
    ):
        require_exact_int(axis.get(key), key)
    section_delta = axis.get("proof_section_delta_bytes")
    if not isinstance(section_delta, dict) or set(section_delta) != set(PROOF_SECTION_KEYS):
        raise AttentionKvProofSizeProfileGateError("proof section delta field drift")
    for key in PROOF_SECTION_KEYS:
        require_exact_int(section_delta.get(key), f"proof section delta {key}")
    section_growth = axis.get("proof_section_growth_ratios")
    if not isinstance(section_growth, dict) or set(section_growth) != set(PROOF_SECTION_KEYS):
        raise AttentionKvProofSizeProfileGateError("proof section growth field drift")
    for key in PROOF_SECTION_KEYS:
        require_float(section_growth.get(key), f"proof section growth {key}")
    for key in (
        "score_rows_ratio",
        "trace_rows_ratio",
        "proof_size_ratio",
        "envelope_size_ratio",
        "proof_growth_vs_score_growth",
        "envelope_growth_vs_score_growth",
        "baseline_proof_bytes_per_score_row",
        "scaled_proof_bytes_per_score_row",
        "baseline_envelope_bytes_per_score_row",
        "scaled_envelope_bytes_per_score_row",
    ):
        require_float(axis.get(key), key)
    for key in (
        "key_width_held_constant",
        "value_width_held_constant",
        "sequence_length_per_head_held_constant",
        "semantics_held_constant",
        "weight_policy_held_constant",
    ):
        if not isinstance(axis.get(key), bool):
            raise AttentionKvProofSizeProfileGateError(f"{key} must be bool")


def build_expected_scaling_diagnostics(_single: dict[str, Any], _two_head: dict[str, Any]) -> dict[str, Any]:
    return {
        "axes_compared": "head_count_1_to_2_same_d8_same_sequence_length_per_head_same_bounded_weight_policy",
        "baseline_head_count": 1,
        "scaled_head_count": 2,
        "key_width_held_constant": True,
        "value_width_held_constant": True,
        "sequence_length_per_head_held_constant": True,
        "semantics_held_constant": True,
        "weight_policy_held_constant": True,
        "score_rows_ratio_fraction": {"numerator": 104, "denominator": 52},
        "score_rows_ratio": 2.0,
        "trace_rows_ratio_fraction": {"numerator": 128, "denominator": 64},
        "trace_rows_ratio": 2.0,
        "proof_size_ratio_fraction": {"numerator": 41175, "denominator": 36769},
        "proof_size_ratio": 1.119829203949,
        "proof_size_delta_bytes": 4406,
        "envelope_size_ratio_fraction": {"numerator": 512060, "denominator": 386078},
        "envelope_size_ratio": 1.326312299587,
        "envelope_size_delta_bytes": 125982,
        "proof_growth_vs_score_growth": 0.559914601974,
        "envelope_growth_vs_score_growth": 0.663156149794,
        "proof_section_delta_bytes": {
            "config": 0,
            "commitments": 10,
            "sampled_values": 635,
            "decommitments": 1096,
            "queried_values": 528,
            "proof_of_work": 0,
            "fri_proof": 2137,
        },
        "proof_section_growth_ratios": {
            "config": 1.0,
            "commitments": 1.029850746269,
            "sampled_values": 1.04214788265,
            "decommitments": 1.202662721893,
            "queried_values": 1.053872053872,
            "proof_of_work": 1.0,
            "fri_proof": 1.362572107228,
        },
        "proof_section_payload_delta_bytes": 4406,
        "proof_json_wrapper_delta_bytes": 0,
        "largest_proof_section_delta": "fri_proof",
        "fri_proof_delta_bytes": 2137,
        "decommitments_delta_bytes": 1096,
        "baseline_proof_bytes_per_score_row": 707.096153846154,
        "scaled_proof_bytes_per_score_row": 395.913461538462,
        "baseline_envelope_bytes_per_score_row": 7424.576923076923,
        "scaled_envelope_bytes_per_score_row": 4923.653846153846,
        "profile_interpretation": PROFILE_INTERPRETATION,
        "proof_component_byte_breakdown_status": PROOF_COMPONENT_BYTE_BREAKDOWN_STATUS,
    }


def build_payload() -> dict[str, Any]:
    single_gate = SINGLE_GATE_MODULE.build_payload()
    two_head_gate = TWO_HEAD_GATE_MODULE.build_payload()
    SINGLE_GATE_MODULE.validate_payload(single_gate)
    TWO_HEAD_GATE_MODULE.validate_payload(two_head_gate)
    single = source_row_from_gate(single_gate, expected=EXPECTED_SINGLE, gate_module=SINGLE_GATE_MODULE)
    two_head = source_row_from_gate(two_head_gate, expected=EXPECTED_TWO_HEAD, gate_module=TWO_HEAD_GATE_MODULE)
    diagnostics = build_scaling_diagnostics(single, two_head)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issues": list(SOURCE_ISSUES),
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "profile_rows": [single, two_head],
        "scaling_diagnostics": diagnostics,
        "controlled_grid_coverage": copy.deepcopy(CONTROLLED_GRID_COVERAGE),
        "structural_breakdown_status": STRUCTURAL_BREAKDOWN_STATUS,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["profile_gate_commitment"] = expected_commitment(payload)
    cases = mutation_cases_for(payload)
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def expected_commitment(payload: dict[str, Any]) -> str:
    commitment_payload = copy.deepcopy(payload)
    for key in (
        "profile_gate_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    ):
        commitment_payload.pop(key, None)
    return blake2b_commitment(
        commitment_payload,
        "ptvm:zkai:attention-kv-native-proof-size-profile-gate:v1",
    )


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        mutated.pop(key, None)
    if name == "single_proof_size_metric_smuggling":
        mutated["profile_rows"][0]["proof_size_bytes"] += 1
    elif name == "two_head_proof_size_metric_smuggling":
        mutated["profile_rows"][1]["proof_size_bytes"] += 1
    elif name == "single_envelope_size_metric_smuggling":
        mutated["profile_rows"][0]["envelope_size_bytes"] += 1
    elif name == "two_head_envelope_size_metric_smuggling":
        mutated["profile_rows"][1]["envelope_size_bytes"] += 1
    elif name == "row_ratio_metric_smuggling":
        mutated["scaling_diagnostics"]["score_rows_ratio"] = 2.1
    elif name == "proof_ratio_metric_smuggling":
        mutated["scaling_diagnostics"]["proof_size_ratio"] = 1.0
    elif name == "fri_section_metric_smuggling":
        mutated["profile_rows"][1]["proof_section_bytes"]["fri_proof"] += 1
    elif name == "grid_status_overclaim":
        mutated["controlled_grid_coverage"]["status"] = "FULL_GRID_COVERED"
    elif name == "column_breakdown_overclaim":
        mutated["profile_rows"][1]["structural_breakdown"]["base_trace_columns"] = 12
    elif name == "source_gate_commitment_relabeling":
        mutated["profile_rows"][1]["gate_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "statement_commitment_relabeling":
        mutated["profile_rows"][1]["statement_commitment"] = "blake2b-256:" + "66" * 32
    elif name == "claim_boundary_scaling_law_overclaim":
        mutated["claim_boundary"] = "PROOF_SIZE_SCALING_LAW_FOR_NATIVE_STWO_ATTENTION_KV"
    elif name == "profile_interpretation_overclaim":
        mutated["scaling_diagnostics"]["profile_interpretation"] = "proves_sublinear_scaling_law"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "timing_policy_public_benchmark_overclaim":
        mutated["timing_policy"] = "public_benchmark"
    elif name == "proof_component_breakdown_overclaim":
        mutated["scaling_diagnostics"]["proof_component_byte_breakdown_status"] = "PCS_FRI_BYTES_DECOMPOSED"
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "unknown_field_injection":
        mutated["unexpected"] = "claim smuggling"
    else:
        raise AttentionKvProofSizeProfileGateError(f"unknown mutation: {name}")
    return mutated


def mutation_cases_for(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_mutation_spec()
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvProofSizeProfileGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "mutation unexpectedly accepted"})
    return cases


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvProofSizeProfileGateError("payload must be object")
    expected_keys = {
        "schema",
        "issue",
        "source_issues",
        "decision",
        "claim_boundary",
        "first_blocker",
        "timing_policy",
        "profile_rows",
        "scaling_diagnostics",
        "controlled_grid_coverage",
        "structural_breakdown_status",
        "non_claims",
        "validation_commands",
        "profile_gate_commitment",
    }
    if not allow_missing_mutation_summary:
        expected_keys |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    elif {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"} & set(payload):
        expected_keys |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if set(payload) != expected_keys:
        raise AttentionKvProofSizeProfileGateError("payload field set drift")
    expected_top = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issues": list(SOURCE_ISSUES),
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "controlled_grid_coverage": CONTROLLED_GRID_COVERAGE,
        "structural_breakdown_status": STRUCTURAL_BREAKDOWN_STATUS,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, expected in expected_top.items():
        if payload.get(key) != expected:
            raise AttentionKvProofSizeProfileGateError(f"{key} drift")
    rows = payload.get("profile_rows")
    if not isinstance(rows, list) or len(rows) != 2:
        raise AttentionKvProofSizeProfileGateError("profile row count drift")
    validate_profile_row(rows[0], expected=EXPECTED_SINGLE)
    validate_profile_row(rows[1], expected=EXPECTED_TWO_HEAD)
    validate_scaling_diagnostics(payload.get("scaling_diagnostics"), rows[0], rows[1])
    if payload.get("profile_gate_commitment") != expected_commitment(payload):
        raise AttentionKvProofSizeProfileGateError("profile gate commitment drift")
    if not allow_missing_mutation_summary:
        validate_mutation_summary(payload)


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    validate_mutation_spec()
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvProofSizeProfileGateError("mutation case count drift")
    names = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != MUTATION_CASE_KEYS:
            raise AttentionKvProofSizeProfileGateError("mutation case schema drift")
        names.append(case.get("name"))
        if case.get("rejected") is not True or not isinstance(case.get("error"), str) or not case.get("error"):
            raise AttentionKvProofSizeProfileGateError("mutation rejection drift")
    if tuple(names) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvProofSizeProfileGateError("mutation names drift")
    if require_exact_int(payload.get("mutations_checked"), "mutations_checked") != EXPECTED_MUTATION_COUNT:
        raise AttentionKvProofSizeProfileGateError("mutation checked count drift")
    if require_exact_int(payload.get("mutations_rejected"), "mutations_rejected") != EXPECTED_MUTATION_COUNT:
        raise AttentionKvProofSizeProfileGateError("mutation rejected count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvProofSizeProfileGateError("all mutations rejected drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_payload(payload)
    baseline = payload["profile_rows"][0]
    scaled = payload["profile_rows"][1]
    diagnostics = payload["scaling_diagnostics"]
    return [
        {
            "decision": payload["decision"],
            "baseline_head_count": baseline["head_count"],
            "scaled_head_count": scaled["head_count"],
            "baseline_score_rows": baseline["score_rows"],
            "scaled_score_rows": scaled["score_rows"],
            "score_rows_ratio": diagnostics["score_rows_ratio"],
            "baseline_trace_rows": baseline["trace_rows"],
            "scaled_trace_rows": scaled["trace_rows"],
            "trace_rows_ratio": diagnostics["trace_rows_ratio"],
            "baseline_proof_size_bytes": baseline["proof_size_bytes"],
            "scaled_proof_size_bytes": scaled["proof_size_bytes"],
            "proof_size_delta_bytes": diagnostics["proof_size_delta_bytes"],
            "proof_size_ratio": diagnostics["proof_size_ratio"],
            "baseline_envelope_size_bytes": baseline["envelope_size_bytes"],
            "scaled_envelope_size_bytes": scaled["envelope_size_bytes"],
            "envelope_size_delta_bytes": diagnostics["envelope_size_delta_bytes"],
            "envelope_size_ratio": diagnostics["envelope_size_ratio"],
            "proof_growth_vs_score_growth": diagnostics["proof_growth_vs_score_growth"],
            "envelope_growth_vs_score_growth": diagnostics["envelope_growth_vs_score_growth"],
            "fri_proof_delta_bytes": diagnostics["fri_proof_delta_bytes"],
            "decommitments_delta_bytes": diagnostics["decommitments_delta_bytes"],
            "proof_section_payload_delta_bytes": diagnostics["proof_section_payload_delta_bytes"],
            "proof_json_wrapper_delta_bytes": diagnostics["proof_json_wrapper_delta_bytes"],
            "proof_component_byte_breakdown_status": diagnostics["proof_component_byte_breakdown_status"],
            "mutations_checked": payload["mutations_checked"],
            "mutations_rejected": payload["mutations_rejected"],
        }
    ]


def to_tsv(payload: dict[str, Any]) -> str:
    import io

    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows_for_tsv(payload))
    return handle.getvalue()


def write_json(payload: dict[str, Any], path: pathlib.Path) -> None:
    validate_payload(payload)
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(payload: dict[str, Any], path: pathlib.Path) -> None:
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_tsv(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    payload = build_payload()
    write_json(payload, args.write_json)
    write_tsv(payload, args.write_tsv)


if __name__ == "__main__":
    main()
