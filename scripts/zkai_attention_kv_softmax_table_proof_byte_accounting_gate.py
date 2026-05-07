#!/usr/bin/env python3
"""Checked proof-byte accounting for native Stwo bounded Softmax-table receipts.

This gate answers issue #469 narrowly.  The checked proof byte buffers currently
contain UTF-8 JSON with one `stark_proof` object, so this script can account for
stable JSON subobjects below the top-level `stark_proof` sections.  It does not
pretend to account for true binary PCS/FRI internals; the missing typed/binary
serialization hook is recorded as an explicit blocker.
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
SINGLE_GATE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_d8_bounded_softmax_table_native_gate.py"
TWO_HEAD_GATE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-gate-v1"
ISSUE = 469
SOURCE_ISSUES = (463, 471)
DECISION = "GO_JSON_STARK_PROOF_SUBOBJECT_ACCOUNTING_NO_GO_BINARY_PCS_FRI_ACCOUNTING"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_BOUNDED_SOFTMAX_TABLE_PROOF_BYTE_ACCOUNTING_"
    "JSON_SUBOBJECTS_ONLY_NOT_BINARY_PCS_FRI_INTERNALS_NOT_SCALING_LAW_NOT_PUBLIC_BENCHMARK"
)
FIRST_BLOCKER = "NO_GO_BINARY_PCS_FRI_ACCOUNTING_STABLE_STWO_BINARY_SERIALIZATION_SCHEMA_NOT_EXPOSED"
TIMING_POLICY = "no_new_timing_proof_byte_accounting_only"
PROFILE_INTERPRETATION = (
    "doubling_heads_and_score_rows_adds_2412_raw_json_proof_bytes_while_checked_envelope_file_bytes_add_111655_"
    "raw_proof_growth_is_fri_and_query_material_dominated_but_true_binary_pcs_fri_accounting_is_not_available"
)
JSON_ACCOUNTING_STATUS = "GO_STABLE_JSON_STARK_PROOF_SUBOBJECT_ACCOUNTING"
BINARY_ACCOUNTING_STATUS = "NO_GO_TYPED_BINARY_STWO_PROOF_COMPONENT_SCHEMA_NOT_EXPOSED"
CONTROLLED_GRID_STATUS = "PARTIAL_ONE_TO_TWO_HEAD_SOFTMAX_TABLE_POINT_ONLY_CONTROLLED_GRID_MISSING"
PROOF_PAYLOAD_KIND = "utf8_json_object_with_single_stark_proof_field"
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
PROOF_SECTION_KEYS = (
    "config",
    "commitments",
    "sampled_values",
    "decommitments",
    "queried_values",
    "proof_of_work",
    "fri_proof",
)
FRI_LAYER_COMPONENT_KEYS = ("fri_witness", "decommitment", "commitment")

SINGLE_ROUTE_ID = "local_stwo_attention_kv_d8_bounded_softmax_table_masked_sequence_proof"
TWO_HEAD_ROUTE_ID = "local_stwo_attention_kv_two_head_bounded_softmax_table_masked_sequence_proof"
SEMANTICS = "bounded_table_softmax_approx_attention"
WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
PROOF_BACKEND = "stwo"
PROOF_SYSTEM = "Stwo"
WIDTH = 8
SEQUENCE_LENGTH_PER_HEAD = 8

EXPECTED_SINGLE_ACCOUNTING = {
    "raw_proof_size_bytes": 44692,
    "proof_payload_kind": PROOF_PAYLOAD_KIND,
    "json_accounting_status": JSON_ACCOUNTING_STATUS,
    "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
    "proof_config": PROOF_CONFIG,
    "proof_section_bytes": {
        "config": 136,
        "commitments": 340,
        "sampled_values": 19830,
        "decommitments": 5494,
        "queried_values": 12868,
        "proof_of_work": 3,
        "fri_proof": 5896,
    },
    "proof_section_payload_bytes_total": 44567,
    "proof_json_wrapper_bytes": 125,
    "commitment_bytes_by_lane": [113, 113, 110],
    "sampled_values": {
        "top_level_bytes": 19830,
        "lane_count": 3,
        "lane_lengths": [246, 246, 8],
        "lane_bytes": [9713, 9713, 400],
    },
    "decommitments": {
        "top_level_bytes": 5494,
        "lane_count": 3,
        "lane_bytes": [1829, 1829, 1832],
    },
    "queried_values": {
        "top_level_bytes": 12868,
        "lane_count": 3,
        "lane_lengths": [246, 246, 8],
        "lane_bytes": [6297, 6297, 270],
    },
    "fri_proof": {
        "top_level_bytes": 5896,
        "first_layer_bytes": 1780,
        "inner_layers_bytes": 3993,
        "inner_layer_count": 5,
        "last_layer_poly_bytes": 72,
        "component_group_bytes": {
            "commitments": 686,
            "decommitments": 4036,
            "witnesses": 769,
            "last_layer_poly": 72,
            "json_structure_overhead": 333,
        },
        "first_layer_component_bytes": {
            "commitment": 115,
            "decommitment": 1473,
            "fri_witness": 146,
        },
        "inner_layer_component_bytes": [
            {"layer": 0, "commitment": 116, "decommitment": 1147, "fri_witness": 148, "total": 1457},
            {"layer": 1, "commitment": 114, "decommitment": 812, "fri_witness": 141, "total": 1113},
            {"layer": 2, "commitment": 116, "decommitment": 463, "fri_witness": 141, "total": 766},
            {"layer": 3, "commitment": 115, "decommitment": 122, "fri_witness": 143, "total": 426},
            {"layer": 4, "commitment": 110, "decommitment": 19, "fri_witness": 50, "total": 225},
        ],
    },
}
EXPECTED_TWO_HEAD_ACCOUNTING = {
    "raw_proof_size_bytes": 47104,
    "proof_payload_kind": PROOF_PAYLOAD_KIND,
    "json_accounting_status": JSON_ACCOUNTING_STATUS,
    "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
    "proof_config": PROOF_CONFIG,
    "proof_section_bytes": {
        "config": 136,
        "commitments": 346,
        "sampled_values": 20368,
        "decommitments": 5798,
        "queried_values": 13214,
        "proof_of_work": 4,
        "fri_proof": 7113,
    },
    "proof_section_payload_bytes_total": 46979,
    "proof_json_wrapper_bytes": 125,
    "commitment_bytes_by_lane": [113, 113, 116],
    "sampled_values": {
        "top_level_bytes": 20368,
        "lane_count": 3,
        "lane_lengths": [247, 247, 8],
        "lane_bytes": [9979, 9979, 406],
    },
    "decommitments": {
        "top_level_bytes": 5798,
        "lane_count": 3,
        "lane_bytes": [1935, 1935, 1924],
    },
    "queried_values": {
        "top_level_bytes": 13214,
        "lane_count": 3,
        "lane_lengths": [247, 247, 8],
        "lane_bytes": [6469, 6469, 272],
    },
    "fri_proof": {
        "top_level_bytes": 7113,
        "first_layer_bytes": 1871,
        "inner_layers_bytes": 5121,
        "inner_layer_count": 6,
        "last_layer_poly_bytes": 70,
        "component_group_bytes": {
            "commitments": 788,
            "decommitments": 5054,
            "witnesses": 821,
            "last_layer_poly": 70,
            "json_structure_overhead": 380,
        },
        "first_layer_component_bytes": {
            "commitment": 107,
            "decommitment": 1575,
            "fri_witness": 143,
        },
        "inner_layer_component_bytes": [
            {"layer": 0, "commitment": 118, "decommitment": 1246, "fri_witness": 145, "total": 1555},
            {"layer": 1, "commitment": 112, "decommitment": 929, "fri_witness": 146, "total": 1233},
            {"layer": 2, "commitment": 119, "decommitment": 578, "fri_witness": 145, "total": 888},
            {"layer": 3, "commitment": 108, "decommitment": 463, "fri_witness": 47, "total": 664},
            {"layer": 4, "commitment": 107, "decommitment": 244, "fri_witness": 99, "total": 496},
            {"layer": 5, "commitment": 117, "decommitment": 19, "fri_witness": 96, "total": 278},
        ],
    },
}
EXPECTED_SINGLE = {
    "label": "single_head_d8_seq8_bounded_softmax_table",
    "source_issue": 463,
    "route_id": SINGLE_ROUTE_ID,
    "head_count": 1,
    "key_width": WIDTH,
    "value_width": WIDTH,
    "sequence_length_per_head": SEQUENCE_LENGTH_PER_HEAD,
    "score_rows": 52,
    "trace_rows": 64,
    "proof_size_bytes": 44692,
    "envelope_size_bytes": 451982,
    "canonical_input_bytes": 34893,
    "canonical_proof_byte_array_bytes": 134589,
    "canonical_envelope_metadata_bytes": 379,
    "statement_commitment": "blake2b-256:7d75ce774597ed9ac2a022b954647f685350aa82b70438cb37e57b915f16c79b",
    "gate_commitment": "blake2b-256:6fb160ca48a77e08097c4301f45bbbcd749112e451078d7d96135a449ea8b6ce",
    "proof_accounting": EXPECTED_SINGLE_ACCOUNTING,
}
EXPECTED_TWO_HEAD = {
    "label": "two_head_d8_seq8_bounded_softmax_table",
    "source_issue": 471,
    "route_id": TWO_HEAD_ROUTE_ID,
    "head_count": 2,
    "key_width": WIDTH,
    "value_width": WIDTH,
    "sequence_length_per_head": SEQUENCE_LENGTH_PER_HEAD,
    "score_rows": 104,
    "trace_rows": 128,
    "proof_size_bytes": 47104,
    "envelope_size_bytes": 563637,
    "canonical_input_bytes": 67945,
    "canonical_proof_byte_array_bytes": 141869,
    "canonical_envelope_metadata_bytes": 412,
    "statement_commitment": "blake2b-256:3430a919e3cede8302e11a7b182c3e85f1c0b894abe3a6c67f474fa83331fe2b",
    "gate_commitment": "blake2b-256:4480537073014d4fe68837c3b7750d34d1f1ef34157b21c39ff11ed998149a2e",
    "proof_accounting": EXPECTED_TWO_HEAD_ACCOUNTING,
}

EXPECTED_MUTATION_NAMES = (
    "single_proof_size_metric_smuggling",
    "two_head_proof_size_metric_smuggling",
    "single_envelope_size_metric_smuggling",
    "two_head_envelope_size_metric_smuggling",
    "top_level_fri_metric_smuggling",
    "fri_inner_layers_metric_smuggling",
    "fri_decommitment_group_metric_smuggling",
    "sampled_lane_length_metric_smuggling",
    "queried_lane_length_metric_smuggling",
    "dominant_delta_section_relabeling",
    "binary_accounting_overclaim",
    "claim_boundary_binary_overclaim",
    "first_blocker_removed",
    "envelope_ratio_metric_smuggling",
    "proof_ratio_metric_smuggling",
    "source_gate_commitment_relabeling",
    "statement_commitment_relabeling",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = 19
MUTATION_CASE_KEYS = {"name", "rejected", "error"}
NON_CLAIMS = (
    "not binary PCS/FRI internal accounting",
    "not a proof-size scaling law",
    "not a public performance benchmark row",
    "not a timing benchmark",
    "not exact Softmax attention",
    "not AIR-private lookup arguments",
    "not full autoregressive inference",
    "not proof aggregation or recursion",
    "not controlled-grid coverage",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_d8_bounded_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv",
    "python3 scripts/zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.tsv",
    "python3 scripts/zkai_attention_kv_softmax_table_proof_byte_accounting_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_softmax_table_proof_byte_accounting_gate",
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
    "baseline_raw_proof_bytes",
    "scaled_raw_proof_bytes",
    "raw_proof_delta_bytes",
    "raw_proof_ratio",
    "baseline_envelope_file_bytes",
    "scaled_envelope_file_bytes",
    "envelope_file_delta_bytes",
    "envelope_file_ratio",
    "fri_proof_delta_bytes",
    "fri_decommitment_group_delta_bytes",
    "fri_inner_layers_delta_bytes",
    "sampled_values_delta_bytes",
    "queried_values_delta_bytes",
    "binary_accounting_status",
    "mutations_checked",
    "mutations_rejected",
)


class AttentionKvSoftmaxTableProofByteAccountingGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(
            f"failed to import {module_name} from {path}: {err}"
        ) from err
    return module


SINGLE_GATE_MODULE = load_script_module(SINGLE_GATE_SCRIPT, "zkai_attention_kv_d8_bounded_softmax_table_native_gate")
TWO_HEAD_GATE_MODULE = load_script_module(
    TWO_HEAD_GATE_SCRIPT,
    "zkai_attention_kv_two_head_bounded_softmax_table_native_gate",
)


def require_exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{label} must be an integer")
    return value


def require_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, float):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{label} must be a float")
    return value


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("ratio denominator must be positive")
    return round(numerator / denominator, 12)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_json_size(value: Any) -> int:
    return len(canonical_json_bytes(value))


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def decode_proof_bytes(envelope: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    proof = envelope.get("proof")
    if not isinstance(proof, list):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("proof must be a byte list")
    proof_bytes = bytearray()
    for index, value in enumerate(proof):
        if isinstance(value, bool) or not isinstance(value, int):
            raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"proof byte[{index}] must be an integer")
        if value < 0 or value > 255:
            raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"proof byte[{index}] outside byte range")
        proof_bytes.append(value)
    try:
        proof_payload = json.loads(bytes(proof_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"proof payload is not JSON: {err}") from err
    if not isinstance(proof_payload, dict) or set(proof_payload) != {"stark_proof"}:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("proof payload must contain only stark_proof")
    stark_proof = proof_payload["stark_proof"]
    if not isinstance(stark_proof, dict) or set(stark_proof) != set(PROOF_SECTION_KEYS):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("stark_proof section set drift")
    if stark_proof["config"] != PROOF_CONFIG:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("proof config drift")
    return bytes(proof_bytes), stark_proof


def layer_component_bytes(layer: dict[str, Any]) -> dict[str, int]:
    if not isinstance(layer, dict) or set(layer) != set(FRI_LAYER_COMPONENT_KEYS):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("FRI layer field drift")
    return {
        "commitment": canonical_json_size(layer["commitment"]),
        "decommitment": canonical_json_size(layer["decommitment"]),
        "fri_witness": canonical_json_size(layer["fri_witness"]),
        "total": canonical_json_size(layer),
    }


def fri_accounting(fri_proof: Any) -> dict[str, Any]:
    if not isinstance(fri_proof, dict) or set(fri_proof) != {"first_layer", "inner_layers", "last_layer_poly"}:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("fri_proof field drift")
    first = fri_proof["first_layer"]
    inner_layers = fri_proof["inner_layers"]
    if not isinstance(first, dict) or not isinstance(inner_layers, list):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("FRI layer type drift")
    first_components = layer_component_bytes(first)
    inner_components = []
    for index, layer in enumerate(inner_layers):
        component = layer_component_bytes(layer)
        component["layer"] = index
        inner_components.append(component)
    commitment_bytes = first_components["commitment"] + sum(layer["commitment"] for layer in inner_components)
    decommitment_bytes = first_components["decommitment"] + sum(layer["decommitment"] for layer in inner_components)
    witness_bytes = first_components["fri_witness"] + sum(layer["fri_witness"] for layer in inner_components)
    last_layer_poly_bytes = canonical_json_size(fri_proof["last_layer_poly"])
    top_level_bytes = canonical_json_size(fri_proof)
    overhead = top_level_bytes - commitment_bytes - decommitment_bytes - witness_bytes - last_layer_poly_bytes
    if overhead <= 0:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("FRI JSON overhead accounting drift")
    return {
        "top_level_bytes": top_level_bytes,
        "first_layer_bytes": canonical_json_size(first),
        "inner_layers_bytes": canonical_json_size(inner_layers),
        "inner_layer_count": len(inner_layers),
        "last_layer_poly_bytes": last_layer_poly_bytes,
        "component_group_bytes": {
            "commitments": commitment_bytes,
            "decommitments": decommitment_bytes,
            "witnesses": witness_bytes,
            "last_layer_poly": last_layer_poly_bytes,
            "json_structure_overhead": overhead,
        },
        "first_layer_component_bytes": {
            "commitment": first_components["commitment"],
            "decommitment": first_components["decommitment"],
            "fri_witness": first_components["fri_witness"],
        },
        "inner_layer_component_bytes": inner_components,
    }


def proof_accounting(envelope: dict[str, Any]) -> dict[str, Any]:
    proof_bytes, stark_proof = decode_proof_bytes(envelope)
    section_bytes = {key: canonical_json_size(stark_proof[key]) for key in PROOF_SECTION_KEYS}
    section_total = sum(section_bytes.values())
    wrapper_bytes = len(proof_bytes) - section_total
    if wrapper_bytes <= 0:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("proof wrapper byte accounting drift")
    sampled_values = stark_proof["sampled_values"]
    decommitments = stark_proof["decommitments"]
    queried_values = stark_proof["queried_values"]
    commitments = stark_proof["commitments"]
    if not all(isinstance(value, list) for value in (sampled_values, decommitments, queried_values, commitments)):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("stark_proof list section drift")
    return {
        "raw_proof_size_bytes": len(proof_bytes),
        "proof_payload_kind": PROOF_PAYLOAD_KIND,
        "json_accounting_status": JSON_ACCOUNTING_STATUS,
        "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
        "proof_section_bytes": section_bytes,
        "proof_section_payload_bytes_total": section_total,
        "proof_json_wrapper_bytes": wrapper_bytes,
        "proof_config": stark_proof["config"],
        "commitment_bytes_by_lane": [canonical_json_size(value) for value in commitments],
        "sampled_values": {
            "top_level_bytes": section_bytes["sampled_values"],
            "lane_count": len(sampled_values),
            "lane_lengths": [len(value) for value in sampled_values],
            "lane_bytes": [canonical_json_size(value) for value in sampled_values],
        },
        "decommitments": {
            "top_level_bytes": section_bytes["decommitments"],
            "lane_count": len(decommitments),
            "lane_bytes": [canonical_json_size(value) for value in decommitments],
        },
        "queried_values": {
            "top_level_bytes": section_bytes["queried_values"],
            "lane_count": len(queried_values),
            "lane_lengths": [len(value) for value in queried_values],
            "lane_bytes": [canonical_json_size(value) for value in queried_values],
        },
        "fri_proof": fri_accounting(stark_proof["fri_proof"]),
    }


def envelope_component_sizes(envelope: dict[str, Any]) -> dict[str, int]:
    if not isinstance(envelope, dict):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("envelope must be object")
    if "input" not in envelope:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("envelope missing input")
    if "proof" not in envelope:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("envelope missing proof")
    if not isinstance(envelope["input"], dict):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("envelope input must be object")
    if not isinstance(envelope["proof"], list):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("envelope proof must be byte list")
    metadata = {key: value for key, value in envelope.items() if key not in {"input", "proof"}}
    return {
        "canonical_input_bytes": canonical_json_size(envelope["input"]),
        "canonical_proof_byte_array_bytes": canonical_json_size(envelope["proof"]),
        "canonical_envelope_metadata_bytes": canonical_json_size(metadata),
    }


def source_row_from_gate(gate_payload: dict[str, Any], *, expected: dict[str, Any], gate_module: ModuleType) -> dict[str, Any]:
    receipt = gate_payload.get("bounded_softmax_table_receipt")
    if not isinstance(receipt, dict):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("source gate missing bounded Softmax-table receipt")
    envelope = gate_module.read_bounded_json(
        gate_module.ENVELOPE_JSON,
        gate_module.MAX_ENVELOPE_JSON_BYTES,
        "proof-byte accounting envelope",
    )
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
        **envelope_component_sizes(envelope),
        "proof_accounting": proof_accounting(envelope),
    }
    validate_profile_row(row, expected=expected)
    return row


def validate_profile_row(row: Any, *, expected: dict[str, Any]) -> None:
    if not isinstance(row, dict):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("profile row must be object")
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
        "canonical_input_bytes",
        "canonical_proof_byte_array_bytes",
        "canonical_envelope_metadata_bytes",
        "statement_commitment",
        "gate_commitment",
        "proof_accounting",
    }
    if set(row) != expected_keys:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("profile row field drift")
    common_expected = {
        "proof_system": PROOF_SYSTEM,
        "proof_backend": PROOF_BACKEND,
        "semantics": SEMANTICS,
        "weight_policy": WEIGHT_POLICY,
    }
    for key, value in common_expected.items():
        if row.get(key) != value:
            raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"profile row {key} drift")
    for key, value in expected.items():
        if isinstance(value, dict):
            if row.get(key) != value:
                raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"profile row {key} drift")
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
                raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"profile row {key} drift")
        elif row.get(key) != value:
            raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"profile row {key} drift")
    accounting = row["proof_accounting"]
    if accounting.get("raw_proof_size_bytes") != row["proof_size_bytes"]:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("raw proof size/accounting split-brain drift")
    if accounting.get("proof_payload_kind") != PROOF_PAYLOAD_KIND:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("proof payload kind drift")
    if accounting.get("json_accounting_status") != JSON_ACCOUNTING_STATUS:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("json accounting status drift")
    if accounting.get("binary_pcs_fri_accounting_status") != BINARY_ACCOUNTING_STATUS:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("binary accounting status drift")
    if accounting.get("proof_config") != PROOF_CONFIG:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("proof config drift")


def build_scaling_diagnostics(single: dict[str, Any], two_head: dict[str, Any]) -> dict[str, Any]:
    single_acc = single["proof_accounting"]
    two_acc = two_head["proof_accounting"]
    top_delta = {
        key: two_acc["proof_section_bytes"][key] - single_acc["proof_section_bytes"][key]
        for key in PROOF_SECTION_KEYS
    }
    top_growth = {
        key: ratio(two_acc["proof_section_bytes"][key], single_acc["proof_section_bytes"][key])
        for key in PROOF_SECTION_KEYS
    }
    fri_delta = {
        "first_layer_bytes": two_acc["fri_proof"]["first_layer_bytes"] - single_acc["fri_proof"]["first_layer_bytes"],
        "inner_layers_bytes": two_acc["fri_proof"]["inner_layers_bytes"] - single_acc["fri_proof"]["inner_layers_bytes"],
        "last_layer_poly_bytes": two_acc["fri_proof"]["last_layer_poly_bytes"]
        - single_acc["fri_proof"]["last_layer_poly_bytes"],
        "inner_layer_count_delta": two_acc["fri_proof"]["inner_layer_count"] - single_acc["fri_proof"]["inner_layer_count"],
    }
    fri_group_delta = {
        key: two_acc["fri_proof"]["component_group_bytes"][key] - single_acc["fri_proof"]["component_group_bytes"][key]
        for key in ("commitments", "decommitments", "witnesses", "last_layer_poly", "json_structure_overhead")
    }
    raw_delta = two_head["proof_size_bytes"] - single["proof_size_bytes"]
    envelope_delta = two_head["envelope_size_bytes"] - single["envelope_size_bytes"]
    diagnostics = {
        "axes_compared": "head_count_1_to_2_same_d8_same_sequence_length_per_head_same_bounded_softmax_table_policy",
        "baseline_head_count": single["head_count"],
        "scaled_head_count": two_head["head_count"],
        "score_rows_ratio_fraction": {"numerator": two_head["score_rows"], "denominator": single["score_rows"]},
        "score_rows_ratio": ratio(two_head["score_rows"], single["score_rows"]),
        "trace_rows_ratio_fraction": {"numerator": two_head["trace_rows"], "denominator": single["trace_rows"]},
        "trace_rows_ratio": ratio(two_head["trace_rows"], single["trace_rows"]),
        "raw_proof_size_ratio_fraction": {
            "numerator": two_head["proof_size_bytes"],
            "denominator": single["proof_size_bytes"],
        },
        "raw_proof_size_ratio": ratio(two_head["proof_size_bytes"], single["proof_size_bytes"]),
        "raw_proof_size_delta_bytes": raw_delta,
        "envelope_file_size_ratio_fraction": {
            "numerator": two_head["envelope_size_bytes"],
            "denominator": single["envelope_size_bytes"],
        },
        "envelope_file_size_ratio": ratio(two_head["envelope_size_bytes"], single["envelope_size_bytes"]),
        "envelope_file_size_delta_bytes": envelope_delta,
        "raw_proof_growth_vs_score_growth": ratio(
            two_head["proof_size_bytes"] * single["score_rows"],
            single["proof_size_bytes"] * two_head["score_rows"],
        ),
        "envelope_file_growth_vs_score_growth": ratio(
            two_head["envelope_size_bytes"] * single["score_rows"],
            single["envelope_size_bytes"] * two_head["score_rows"],
        ),
        "envelope_delta_per_raw_proof_delta": ratio(envelope_delta, raw_delta),
        "top_level_section_delta_bytes": top_delta,
        "top_level_section_growth_ratios": top_growth,
        "dominant_top_level_delta_section": "fri_proof",
        "fri_proof_delta_share_of_raw_proof_delta": ratio(top_delta["fri_proof"], raw_delta),
        "fri_subcomponent_delta_bytes": fri_delta,
        "fri_component_group_delta_bytes": fri_group_delta,
        "sampled_values_lane_length_delta": [
            two_acc["sampled_values"]["lane_lengths"][index] - single_acc["sampled_values"]["lane_lengths"][index]
            for index in range(len(single_acc["sampled_values"]["lane_lengths"]))
        ],
        "queried_values_lane_length_delta": [
            two_acc["queried_values"]["lane_lengths"][index] - single_acc["queried_values"]["lane_lengths"][index]
            for index in range(len(single_acc["queried_values"]["lane_lengths"]))
        ],
        "canonical_envelope_component_delta_bytes": {
            "input": two_head["canonical_input_bytes"] - single["canonical_input_bytes"],
            "proof_byte_array": two_head["canonical_proof_byte_array_bytes"] - single["canonical_proof_byte_array_bytes"],
            "metadata": two_head["canonical_envelope_metadata_bytes"] - single["canonical_envelope_metadata_bytes"],
        },
        "json_accounting_status": JSON_ACCOUNTING_STATUS,
        "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
        "profile_interpretation": PROFILE_INTERPRETATION,
    }
    validate_scaling_diagnostics(diagnostics, single, two_head)
    return diagnostics


def validate_ratio_fraction(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{label} fraction field drift")
    require_exact_int(value.get("numerator"), f"{label} numerator")
    require_exact_int(value.get("denominator"), f"{label} denominator")


def validate_int_dict(value: Any, expected_keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{label} field drift")
    for key in expected_keys:
        require_exact_int(value.get(key), f"{label} {key}")


def validate_float_dict(value: Any, expected_keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{label} field drift")
    for key in expected_keys:
        require_float(value.get(key), f"{label} {key}")


def validate_scaling_diagnostic_types(axis: dict[str, Any]) -> None:
    for key in (
        "score_rows_ratio_fraction",
        "trace_rows_ratio_fraction",
        "raw_proof_size_ratio_fraction",
        "envelope_file_size_ratio_fraction",
    ):
        validate_ratio_fraction(axis.get(key), key)
    for key in (
        "baseline_head_count",
        "scaled_head_count",
        "raw_proof_size_delta_bytes",
        "envelope_file_size_delta_bytes",
    ):
        require_exact_int(axis.get(key), key)
    for key in (
        "score_rows_ratio",
        "trace_rows_ratio",
        "raw_proof_size_ratio",
        "envelope_file_size_ratio",
        "raw_proof_growth_vs_score_growth",
        "envelope_file_growth_vs_score_growth",
        "envelope_delta_per_raw_proof_delta",
        "fri_proof_delta_share_of_raw_proof_delta",
    ):
        require_float(axis.get(key), key)
    validate_int_dict(axis.get("top_level_section_delta_bytes"), set(PROOF_SECTION_KEYS), "top-level section delta")
    validate_float_dict(axis.get("top_level_section_growth_ratios"), set(PROOF_SECTION_KEYS), "top-level section growth")
    validate_int_dict(
        axis.get("fri_subcomponent_delta_bytes"),
        {"first_layer_bytes", "inner_layers_bytes", "last_layer_poly_bytes", "inner_layer_count_delta"},
        "FRI subcomponent delta",
    )
    validate_int_dict(
        axis.get("fri_component_group_delta_bytes"),
        {"commitments", "decommitments", "witnesses", "last_layer_poly", "json_structure_overhead"},
        "FRI component group delta",
    )
    validate_int_dict(
        axis.get("canonical_envelope_component_delta_bytes"),
        {"input", "proof_byte_array", "metadata"},
        "canonical envelope component delta",
    )
    for key in ("sampled_values_lane_length_delta", "queried_values_lane_length_delta"):
        value = axis.get(key)
        if not isinstance(value, list) or len(value) != 3:
            raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{key} drift")
        for index, item in enumerate(value):
            require_exact_int(item, f"{key}[{index}]")


def validate_scaling_diagnostics(axis: Any, single: dict[str, Any], two_head: dict[str, Any]) -> None:
    if not isinstance(axis, dict):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("scaling diagnostics must be object")
    expected_keys = {
        "axes_compared",
        "baseline_head_count",
        "scaled_head_count",
        "score_rows_ratio_fraction",
        "score_rows_ratio",
        "trace_rows_ratio_fraction",
        "trace_rows_ratio",
        "raw_proof_size_ratio_fraction",
        "raw_proof_size_ratio",
        "raw_proof_size_delta_bytes",
        "envelope_file_size_ratio_fraction",
        "envelope_file_size_ratio",
        "envelope_file_size_delta_bytes",
        "raw_proof_growth_vs_score_growth",
        "envelope_file_growth_vs_score_growth",
        "envelope_delta_per_raw_proof_delta",
        "top_level_section_delta_bytes",
        "top_level_section_growth_ratios",
        "dominant_top_level_delta_section",
        "fri_proof_delta_share_of_raw_proof_delta",
        "fri_subcomponent_delta_bytes",
        "fri_component_group_delta_bytes",
        "sampled_values_lane_length_delta",
        "queried_values_lane_length_delta",
        "canonical_envelope_component_delta_bytes",
        "json_accounting_status",
        "binary_pcs_fri_accounting_status",
        "profile_interpretation",
    }
    if set(axis) != expected_keys:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("scaling diagnostics field drift")
    validate_scaling_diagnostic_types(axis)
    if axis != build_expected_scaling_diagnostics(single, two_head):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("scaling diagnostics drift")


def build_expected_scaling_diagnostics(_single: dict[str, Any], _two_head: dict[str, Any]) -> dict[str, Any]:
    return {
        "axes_compared": "head_count_1_to_2_same_d8_same_sequence_length_per_head_same_bounded_softmax_table_policy",
        "baseline_head_count": 1,
        "scaled_head_count": 2,
        "score_rows_ratio_fraction": {"numerator": 104, "denominator": 52},
        "score_rows_ratio": 2.0,
        "trace_rows_ratio_fraction": {"numerator": 128, "denominator": 64},
        "trace_rows_ratio": 2.0,
        "raw_proof_size_ratio_fraction": {"numerator": 47104, "denominator": 44692},
        "raw_proof_size_ratio": 1.053969390495,
        "raw_proof_size_delta_bytes": 2412,
        "envelope_file_size_ratio_fraction": {"numerator": 563637, "denominator": 451982},
        "envelope_file_size_ratio": 1.247034173927,
        "envelope_file_size_delta_bytes": 111655,
        "raw_proof_growth_vs_score_growth": 0.526984695247,
        "envelope_file_growth_vs_score_growth": 0.623517086964,
        "envelope_delta_per_raw_proof_delta": 46.291459369818,
        "top_level_section_delta_bytes": {
            "config": 0,
            "commitments": 6,
            "sampled_values": 538,
            "decommitments": 304,
            "queried_values": 346,
            "proof_of_work": 1,
            "fri_proof": 1217,
        },
        "top_level_section_growth_ratios": {
            "config": 1.0,
            "commitments": 1.017647058824,
            "sampled_values": 1.027130610187,
            "decommitments": 1.055333090644,
            "queried_values": 1.026888405347,
            "proof_of_work": 1.333333333333,
            "fri_proof": 1.206411126187,
        },
        "dominant_top_level_delta_section": "fri_proof",
        "fri_proof_delta_share_of_raw_proof_delta": 0.50456053068,
        "fri_subcomponent_delta_bytes": {
            "first_layer_bytes": 91,
            "inner_layers_bytes": 1128,
            "last_layer_poly_bytes": -2,
            "inner_layer_count_delta": 1,
        },
        "fri_component_group_delta_bytes": {
            "commitments": 102,
            "decommitments": 1018,
            "witnesses": 52,
            "last_layer_poly": -2,
            "json_structure_overhead": 47,
        },
        "sampled_values_lane_length_delta": [1, 1, 0],
        "queried_values_lane_length_delta": [1, 1, 0],
        "canonical_envelope_component_delta_bytes": {"input": 33052, "proof_byte_array": 7280, "metadata": 33},
        "json_accounting_status": JSON_ACCOUNTING_STATUS,
        "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
        "profile_interpretation": PROFILE_INTERPRETATION,
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
        "json_accounting_status": JSON_ACCOUNTING_STATUS,
        "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
        "controlled_grid_status": CONTROLLED_GRID_STATUS,
        "profile_rows": [single, two_head],
        "scaling_diagnostics": diagnostics,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["accounting_gate_commitment"] = expected_commitment(payload)
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
        "accounting_gate_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    ):
        commitment_payload.pop(key, None)
    return blake2b_commitment(
        commitment_payload,
        "ptvm:zkai:attention-kv-softmax-table-proof-byte-accounting-gate:v1",
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
    elif name == "top_level_fri_metric_smuggling":
        mutated["profile_rows"][1]["proof_accounting"]["proof_section_bytes"]["fri_proof"] += 1
    elif name == "fri_inner_layers_metric_smuggling":
        mutated["profile_rows"][1]["proof_accounting"]["fri_proof"]["inner_layers_bytes"] += 1
    elif name == "fri_decommitment_group_metric_smuggling":
        mutated["profile_rows"][1]["proof_accounting"]["fri_proof"]["component_group_bytes"]["decommitments"] += 1
    elif name == "sampled_lane_length_metric_smuggling":
        mutated["profile_rows"][1]["proof_accounting"]["sampled_values"]["lane_lengths"][0] += 1
    elif name == "queried_lane_length_metric_smuggling":
        mutated["profile_rows"][1]["proof_accounting"]["queried_values"]["lane_lengths"][0] += 1
    elif name == "dominant_delta_section_relabeling":
        mutated["scaling_diagnostics"]["dominant_top_level_delta_section"] = "sampled_values"
    elif name == "binary_accounting_overclaim":
        mutated["binary_pcs_fri_accounting_status"] = "GO_BINARY_PCS_FRI_INTERNAL_ACCOUNTING"
    elif name == "claim_boundary_binary_overclaim":
        mutated["claim_boundary"] = "NATIVE_STWO_BINARY_PCS_FRI_INTERNAL_ACCOUNTING"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "envelope_ratio_metric_smuggling":
        mutated["scaling_diagnostics"]["envelope_file_size_ratio"] = 1.0
    elif name == "proof_ratio_metric_smuggling":
        mutated["scaling_diagnostics"]["raw_proof_size_ratio"] = 1.0
    elif name == "source_gate_commitment_relabeling":
        mutated["profile_rows"][1]["gate_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "statement_commitment_relabeling":
        mutated["profile_rows"][1]["statement_commitment"] = "blake2b-256:" + "66" * 32
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "unknown_field_injection":
        mutated["unexpected"] = "claim smuggling"
    else:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"unknown mutation: {name}")
    return mutated


def mutation_cases_for(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_mutation_spec()
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvSoftmaxTableProofByteAccountingGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "mutation unexpectedly accepted"})
    return cases


def validate_mutation_spec() -> None:
    if len(EXPECTED_MUTATION_NAMES) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation spec count drift")


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("payload must be object")
    expected_keys = {
        "schema",
        "issue",
        "source_issues",
        "decision",
        "claim_boundary",
        "first_blocker",
        "timing_policy",
        "json_accounting_status",
        "binary_pcs_fri_accounting_status",
        "controlled_grid_status",
        "profile_rows",
        "scaling_diagnostics",
        "non_claims",
        "validation_commands",
        "accounting_gate_commitment",
    }
    mutation_summary_keys = {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    has_mutation_summary = bool(mutation_summary_keys & set(payload))
    if not allow_missing_mutation_summary or has_mutation_summary:
        expected_keys |= mutation_summary_keys
    if set(payload) != expected_keys:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("payload field set drift")
    expected_top = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issues": list(SOURCE_ISSUES),
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "json_accounting_status": JSON_ACCOUNTING_STATUS,
        "binary_pcs_fri_accounting_status": BINARY_ACCOUNTING_STATUS,
        "controlled_grid_status": CONTROLLED_GRID_STATUS,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, expected in expected_top.items():
        if payload.get(key) != expected:
            raise AttentionKvSoftmaxTableProofByteAccountingGateError(f"{key} drift")
    rows = payload.get("profile_rows")
    if not isinstance(rows, list) or len(rows) != 2:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("profile row count drift")
    validate_profile_row(rows[0], expected=EXPECTED_SINGLE)
    validate_profile_row(rows[1], expected=EXPECTED_TWO_HEAD)
    validate_scaling_diagnostics(payload.get("scaling_diagnostics"), rows[0], rows[1])
    if payload.get("accounting_gate_commitment") != expected_commitment(payload):
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("accounting gate commitment drift")
    if not allow_missing_mutation_summary or has_mutation_summary:
        validate_mutation_summary(payload)


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    validate_mutation_spec()
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation case count drift")
    names = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != MUTATION_CASE_KEYS:
            raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation case schema drift")
        names.append(case.get("name"))
        if case.get("rejected") is not True or not isinstance(case.get("error"), str) or not case.get("error"):
            raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation rejection drift")
    if tuple(names) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation names drift")
    if require_exact_int(payload.get("mutations_checked"), "mutations_checked") != EXPECTED_MUTATION_COUNT:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation checked count drift")
    if require_exact_int(payload.get("mutations_rejected"), "mutations_rejected") != EXPECTED_MUTATION_COUNT:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("mutation rejected count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvSoftmaxTableProofByteAccountingGateError("all mutations rejected drift")


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
            "baseline_raw_proof_bytes": baseline["proof_size_bytes"],
            "scaled_raw_proof_bytes": scaled["proof_size_bytes"],
            "raw_proof_delta_bytes": diagnostics["raw_proof_size_delta_bytes"],
            "raw_proof_ratio": diagnostics["raw_proof_size_ratio"],
            "baseline_envelope_file_bytes": baseline["envelope_size_bytes"],
            "scaled_envelope_file_bytes": scaled["envelope_size_bytes"],
            "envelope_file_delta_bytes": diagnostics["envelope_file_size_delta_bytes"],
            "envelope_file_ratio": diagnostics["envelope_file_size_ratio"],
            "fri_proof_delta_bytes": diagnostics["top_level_section_delta_bytes"]["fri_proof"],
            "fri_decommitment_group_delta_bytes": diagnostics["fri_component_group_delta_bytes"]["decommitments"],
            "fri_inner_layers_delta_bytes": diagnostics["fri_subcomponent_delta_bytes"]["inner_layers_bytes"],
            "sampled_values_delta_bytes": diagnostics["top_level_section_delta_bytes"]["sampled_values"],
            "queried_values_delta_bytes": diagnostics["top_level_section_delta_bytes"]["queried_values"],
            "binary_accounting_status": payload["binary_pcs_fri_accounting_status"],
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
