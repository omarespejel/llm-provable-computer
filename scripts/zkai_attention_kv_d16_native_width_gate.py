#!/usr/bin/env python3
"""Checked width gate for the native Stwo attention/KV d16 proof.

This gate answers issue #453 narrowly: the native Stwo attention/KV AIR now has
a second width point that doubles key/value width from d=8 to d=16 while keeping
eight carried steps, integer-argmax semantics, causal-prefix masking,
lowest-position tie-break, and explicit statement binding. It does not claim
Softmax, multi-head attention, long-context inference, recursion, PCD, or
benchmark-grade timing.
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
from typing import Any, Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
D8_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json"
D8_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json"
D16_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json"
D16_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json"
D8_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_masked_sequence_proof_input.py"
D16_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-width-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-width-gate-2026-05.tsv"
MAX_INPUT_JSON_BYTES = 1_048_576
MAX_ENVELOPE_JSON_BYTES = 1_048_576

NATIVE_INPUT_SCHEMA = "zkai-attention-kv-stwo-native-masked-sequence-air-proof-input-v1"
NATIVE_INPUT_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
NATIVE_ENVELOPE_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
TIMING_POLICY = "single_local_dev_profile_engineering_only"

SCHEMA = "zkai-attention-kv-stwo-native-d16-width-gate-v1"
ISSUE = 453
SOURCE_ISSUE = 450
DECISION = "GO_NATIVE_STWO_ATTENTION_KV_D16_WIDTH_SCALE"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_D16_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_WIDTH_SCALE_PROOF_"
    "NOT_SOFTMAX_NOT_MULTIHEAD_NOT_LONG_CONTEXT_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
FIRST_BLOCKER = "NO_MULTIHEAD_SOFTMAX_OR_LONG_CONTEXT_NATIVE_ATTENTION_PROOF_YET"
D8_ROUTE_ID = "local_stwo_attention_kv_d8_masked_sequence_proof"
D16_ROUTE_ID = "local_stwo_attention_kv_d16_masked_sequence_proof"

D8_TARGET_ID = "attention-kv-d8-causal-mask-sequence-v1"
D8_PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-sequence-air-proof-v1"
D8_REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-sequence-v1"
D8_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-statement-v1"
D8_SEMANTIC_SCOPE = "d8_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt"
D8_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-masked-sequence:v1"
D8_SELECTED_POSITIONS = (0, 2, 3, 3, 5, 5, 7, 9)
D8_PROOF_SIZE_BYTES = 24394
D8_COMMITMENTS = {
    "statement_commitment": "blake2b-256:dcb688e7e2d7076b2f2fe35c6aa3a12af57d676101c300b48cbda66797e4f232",
    "public_instance_commitment": "blake2b-256:3c5a7c1aaf6b7ececf3d729935b0548b0b947ce3c649f0370dd44fc687227631",
    "score_row_commitment": "blake2b-256:8348dc0d9c052050c77bc56a4c08896c283ca710ab2caca30f1bab60d8451337",
    "final_kv_cache_commitment": "blake2b-256:74038853585ec88f7211e615910923d194d5731af74197c370daaf906d0be1e2",
    "outputs_commitment": "blake2b-256:a39a6d6e90b4fa06d443807d4fe9110c0986a67c930d9ceff4e0bc4bbce9c083",
}

D16_TARGET_ID = "attention-kv-d16-causal-mask-sequence-v1"
D16_PROOF_VERSION = "stwo-attention-kv-d16-causal-mask-sequence-air-proof-v1"
D16_REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d16-causal-mask-sequence-v1"
D16_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-d16-statement-v1"
D16_SEMANTIC_SCOPE = "d16_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt"
D16_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-masked-sequence-d16:v1"
D16_SELECTED_POSITIONS = (1, 1, 3, 1, 5, 3, 1, 3)
D16_PROOF_SIZE_BYTES = 31621
D16_COMMITMENTS = {
    "statement_commitment": "blake2b-256:9ca216aefb582e0877d46deacf4af936bf61aa3f6c7865b22675d7698ffc3cd6",
    "public_instance_commitment": "blake2b-256:bd7415e074c0699ced0c774f987b6eceae9ca5607cc6df0e0714723db3aa8551",
    "score_row_commitment": "blake2b-256:8973b8fdcbf26b031b38491ff405cf93f40aee9eeaa2fc0b6bdbe31b960ac855",
    "final_kv_cache_commitment": "blake2b-256:90b89f3256f1c080b60e06abfeb81ba4a68bfee6cd9ef49ed604cb4898ec774d",
    "outputs_commitment": "blake2b-256:c62aac346e84ef24b5bd1618e6e17a5cf86bf8f4185fc01e6f393da0ff085e47",
}

EXPECTED_MUTATION_NAMES = (
    "d16_statement_commitment_relabeling",
    "d16_public_instance_commitment_relabeling",
    "d16_key_width_relabeling",
    "d16_value_width_relabeling",
    "d16_score_row_count_relabeling",
    "d16_selected_position_relabeling",
    "d16_final_kv_relabeling",
    "d16_target_id_relabeling",
    "d16_backend_version_relabeling",
    "d16_proof_size_metric_smuggling",
    "d8_baseline_statement_relabeling",
    "route_removed",
    "claim_boundary_softmax_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "unknown_field_injection",
)
NON_CLAIMS = (
    "not a Softmax proof",
    "not a multi-head attention proof",
    "not full autoregressive inference",
    "not recursive verification or PCD",
    "not a long-context benchmark",
    "not a public performance benchmark row",
    "not a Starknet deployment result",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_d16_native_width_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_native_width_gate",
    "just lib",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "decision",
    "baseline_key_width",
    "scaled_key_width",
    "baseline_score_rows",
    "scaled_score_rows",
    "baseline_proof_size_bytes",
    "scaled_proof_size_bytes",
    "mutations_checked",
    "mutations_rejected",
    "scaled_statement_commitment",
)


class AttentionKvD16NativeWidthGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvD16NativeWidthGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


D8_INPUT_MODULE = load_script_module(D8_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_masked_sequence_proof_input")
D16_INPUT_MODULE = load_script_module(D16_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input")


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    bounded_file_size(path, max_bytes, label)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvD16NativeWidthGateError(f"failed to read {label}: {err}") from err


def bounded_file_size(path: pathlib.Path, max_bytes: int, label: str) -> int:
    if not path.is_file():
        raise AttentionKvD16NativeWidthGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvD16NativeWidthGateError(f"{label} size drift: got {size}, max {max_bytes}")
    return size


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def validate_pair(
    input_payload: Any,
    envelope: Any,
    *,
    input_validator: Callable[[dict[str, Any]], None],
    input_label: str,
    target_id: str,
    proof_version: str,
    required_backend_version: str,
    statement_version: str,
    semantic_scope: str,
    verifier_domain: str,
    key_width: int,
    value_width: int,
    sequence_length: int,
    score_rows: int,
    trace_rows: int,
    final_kv_items: int,
    selected_positions: tuple[int, ...],
    commitments: dict[str, str],
) -> None:
    if not isinstance(input_payload, dict) or not isinstance(envelope, dict):
        raise AttentionKvD16NativeWidthGateError("input/envelope must be objects")
    if input_payload.get("schema") != NATIVE_INPUT_SCHEMA:
        raise AttentionKvD16NativeWidthGateError("input schema drift")
    if input_payload.get("decision") != NATIVE_INPUT_DECISION:
        raise AttentionKvD16NativeWidthGateError("input decision drift")
    try:
        input_validator(input_payload)
    except Exception as err:
        raise AttentionKvD16NativeWidthGateError(f"{input_label} source input validation drift: {err}") from err
    if envelope.get("input") != input_payload:
        raise AttentionKvD16NativeWidthGateError("proof envelope/input split-brain drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvD16NativeWidthGateError("proof backend drift")
    if envelope.get("proof_backend_version") != required_backend_version:
        raise AttentionKvD16NativeWidthGateError("proof backend version drift")
    if envelope.get("statement_version") != statement_version:
        raise AttentionKvD16NativeWidthGateError("statement version drift")
    if envelope.get("semantic_scope") != semantic_scope:
        raise AttentionKvD16NativeWidthGateError("semantic scope drift")
    if envelope.get("decision") != NATIVE_ENVELOPE_DECISION:
        raise AttentionKvD16NativeWidthGateError("proof envelope decision drift")
    for key, expected in (
        ("target_id", target_id),
        ("proof_version", proof_version),
        ("required_backend_version", required_backend_version),
        ("statement_version", statement_version),
        ("semantic_scope", semantic_scope),
        ("verifier_domain", verifier_domain),
    ):
        if input_payload.get(key) != expected:
            raise AttentionKvD16NativeWidthGateError(f"{key} drift")
    if input_payload.get("key_width") != key_width or input_payload.get("value_width") != value_width:
        raise AttentionKvD16NativeWidthGateError("width drift")
    if input_payload.get("sequence_length") != sequence_length:
        raise AttentionKvD16NativeWidthGateError("sequence length drift")
    if input_payload.get("score_row_count") != score_rows:
        raise AttentionKvD16NativeWidthGateError("score row count drift")
    if input_payload.get("trace_row_count") != trace_rows:
        raise AttentionKvD16NativeWidthGateError("trace row count drift")
    if input_payload.get("final_kv_items") != final_kv_items:
        raise AttentionKvD16NativeWidthGateError("final KV item count drift")
    input_positions = input_payload.get("selected_positions")
    if not isinstance(input_positions, list) or any(not isinstance(item, int) or isinstance(item, bool) for item in input_positions):
        raise AttentionKvD16NativeWidthGateError("selected positions malformed")
    if tuple(input_positions) != selected_positions:
        raise AttentionKvD16NativeWidthGateError("selected positions drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not proof:
        raise AttentionKvD16NativeWidthGateError("proof bytes missing")
    if any(not isinstance(byte, int) or byte < 0 or byte > 255 for byte in proof):
        raise AttentionKvD16NativeWidthGateError("proof bytes malformed")
    for key, expected in commitments.items():
        if input_payload.get(key) != expected:
            raise AttentionKvD16NativeWidthGateError(f"{key} commitment drift")


def receipt_summary(route_id: str, input_payload: dict[str, Any], envelope: dict[str, Any], envelope_path: pathlib.Path) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "target_id": input_payload["target_id"],
        "proof_version": input_payload["proof_version"],
        "required_backend_version": input_payload["required_backend_version"],
        "sequence_length": input_payload["sequence_length"],
        "key_width": input_payload["key_width"],
        "value_width": input_payload["value_width"],
        "score_row_count": input_payload["score_row_count"],
        "trace_row_count": input_payload["trace_row_count"],
        "final_kv_items": input_payload["final_kv_items"],
        "selected_positions": input_payload["selected_positions"],
        "proof_size_bytes": len(envelope["proof"]),
        "envelope_size_bytes": envelope_path.stat().st_size,
        "statement_commitment": input_payload["statement_commitment"],
        "public_instance_commitment": input_payload["public_instance_commitment"],
        "score_row_commitment": input_payload["score_row_commitment"],
        "final_kv_cache_commitment": input_payload["final_kv_cache_commitment"],
        "outputs_commitment": input_payload["outputs_commitment"],
        "timing_policy": TIMING_POLICY,
    }


def _validate_source_pairs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    d8_input = read_bounded_json(D8_INPUT_JSON, MAX_INPUT_JSON_BYTES, "d8 input")
    d8_envelope = read_bounded_json(D8_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "d8 envelope")
    d16_input = read_bounded_json(D16_INPUT_JSON, MAX_INPUT_JSON_BYTES, "d16 input")
    d16_envelope = read_bounded_json(D16_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "d16 envelope")
    validate_pair(
        d8_input,
        d8_envelope,
        input_validator=D8_INPUT_MODULE.validate_payload,
        input_label="d8",
        target_id=D8_TARGET_ID,
        proof_version=D8_PROOF_VERSION,
        required_backend_version=D8_REQUIRED_BACKEND_VERSION,
        statement_version=D8_STATEMENT_VERSION,
        semantic_scope=D8_SEMANTIC_SCOPE,
        verifier_domain=D8_VERIFIER_DOMAIN,
        key_width=8,
        value_width=8,
        sequence_length=8,
        score_rows=52,
        trace_rows=64,
        final_kv_items=10,
        selected_positions=D8_SELECTED_POSITIONS,
        commitments=D8_COMMITMENTS,
    )
    validate_pair(
        d16_input,
        d16_envelope,
        input_validator=D16_INPUT_MODULE.validate_payload,
        input_label="d16",
        target_id=D16_TARGET_ID,
        proof_version=D16_PROOF_VERSION,
        required_backend_version=D16_REQUIRED_BACKEND_VERSION,
        statement_version=D16_STATEMENT_VERSION,
        semantic_scope=D16_SEMANTIC_SCOPE,
        verifier_domain=D16_VERIFIER_DOMAIN,
        key_width=16,
        value_width=16,
        sequence_length=8,
        score_rows=52,
        trace_rows=64,
        final_kv_items=10,
        selected_positions=D16_SELECTED_POSITIONS,
        commitments=D16_COMMITMENTS,
    )
    return d8_input, d8_envelope, d16_input, d16_envelope


def build_payload() -> dict[str, Any]:
    d8_input, d8_envelope, d16_input, d16_envelope = _validate_source_pairs()
    payload = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "baseline_receipt": receipt_summary(D8_ROUTE_ID, d8_input, d8_envelope, D8_ENVELOPE_JSON),
        "scaled_receipt": receipt_summary(D16_ROUTE_ID, d16_input, d16_envelope, D16_ENVELOPE_JSON),
        "width_axis_result": {
            "baseline_key_width": 8,
            "scaled_key_width": 16,
            "sequence_length_held_constant": 8,
            "score_rows_held_constant": 52,
            "trace_rows_held_constant": 64,
            "selected_positions_changed": True,
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["scale_gate_commitment"] = blake2b_commitment(
        {
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "baseline_receipt": payload["baseline_receipt"],
            "scaled_receipt": payload["scaled_receipt"],
            "width_axis_result": payload["width_axis_result"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-stwo-native-d16-width-gate:v1",
    )
    mutation_cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvD16NativeWidthGateError as error:
            mutation_cases.append({"name": name, "rejected": True, "error": str(error)})
        else:
            mutation_cases.append({"name": name, "rejected": False, "error": "mutation accepted"})
    payload["mutation_cases"] = mutation_cases
    payload["mutations_checked"] = len(mutation_cases)
    payload["mutations_rejected"] = sum(1 for case in mutation_cases if case["rejected"] is True)
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        mutated.pop(key, None)
    if name == "d16_statement_commitment_relabeling":
        mutated["scaled_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "d16_public_instance_commitment_relabeling":
        mutated["scaled_receipt"]["public_instance_commitment"] = "blake2b-256:" + "44" * 32
    elif name == "d16_key_width_relabeling":
        mutated["scaled_receipt"]["key_width"] = 8
    elif name == "d16_value_width_relabeling":
        mutated["scaled_receipt"]["value_width"] = 8
    elif name == "d16_score_row_count_relabeling":
        mutated["scaled_receipt"]["score_row_count"] += 1
    elif name == "d16_selected_position_relabeling":
        mutated["scaled_receipt"]["selected_positions"][-1] += 1
    elif name == "d16_final_kv_relabeling":
        mutated["scaled_receipt"]["final_kv_cache_commitment"] = "blake2b-256:" + "33" * 32
    elif name == "d16_target_id_relabeling":
        mutated["scaled_receipt"]["target_id"] = D8_TARGET_ID
    elif name == "d16_backend_version_relabeling":
        mutated["scaled_receipt"]["required_backend_version"] = D8_REQUIRED_BACKEND_VERSION
    elif name == "d16_proof_size_metric_smuggling":
        mutated["scaled_receipt"]["proof_size_bytes"] = 1
    elif name == "d8_baseline_statement_relabeling":
        mutated["baseline_receipt"]["statement_commitment"] = "blake2b-256:" + "22" * 32
    elif name == "route_removed":
        mutated["scaled_receipt"].pop("route_id")
    elif name == "claim_boundary_softmax_overclaim":
        mutated["claim_boundary"] = "GO_SOFTMAX_D16_ATTENTION"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = None
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "unknown_field_injection":
        mutated["unexpected"] = True
    else:
        raise AssertionError(f"unknown mutation: {name}")
    return mutated


def _expected_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "baseline_receipt": payload["baseline_receipt"],
            "scaled_receipt": payload["scaled_receipt"],
            "width_axis_result": payload["width_axis_result"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-stwo-native-d16-width-gate:v1",
    )


def validate_receipt_summary(
    summary: Any,
    *,
    route_id: str,
    target_id: str,
    proof_version: str,
    required_backend_version: str,
    key_width: int,
    value_width: int,
    selected_positions: tuple[int, ...],
    proof_size_bytes: int,
    envelope_size_bytes: int,
    commitments: dict[str, str],
) -> None:
    if not isinstance(summary, dict):
        raise AttentionKvD16NativeWidthGateError("receipt summary must be object")
    required = {
        "route_id", "target_id", "proof_version", "required_backend_version", "sequence_length", "key_width",
        "value_width", "score_row_count", "trace_row_count", "final_kv_items", "selected_positions",
        "proof_size_bytes", "envelope_size_bytes", "statement_commitment", "public_instance_commitment",
        "score_row_commitment", "final_kv_cache_commitment", "outputs_commitment", "timing_policy",
    }
    if set(summary) != required:
        raise AttentionKvD16NativeWidthGateError("receipt summary field drift")
    if summary["route_id"] != route_id:
        raise AttentionKvD16NativeWidthGateError("route id drift")
    if summary["target_id"] != target_id:
        raise AttentionKvD16NativeWidthGateError("target id drift")
    if summary["proof_version"] != proof_version:
        raise AttentionKvD16NativeWidthGateError("proof version drift")
    if summary["required_backend_version"] != required_backend_version:
        raise AttentionKvD16NativeWidthGateError("backend version drift")
    if summary["key_width"] != key_width or summary["value_width"] != value_width:
        raise AttentionKvD16NativeWidthGateError("width drift")
    if summary["sequence_length"] != 8:
        raise AttentionKvD16NativeWidthGateError("sequence length drift")
    if summary["score_row_count"] != 52 or summary["trace_row_count"] != 64:
        raise AttentionKvD16NativeWidthGateError("row count drift")
    if summary["final_kv_items"] != 10:
        raise AttentionKvD16NativeWidthGateError("final KV item count drift")
    positions = summary["selected_positions"]
    if (
        not isinstance(positions, list)
        or any(not isinstance(item, int) or isinstance(item, bool) for item in positions)
    ):
        raise AttentionKvD16NativeWidthGateError("selected positions malformed")
    if positions != list(selected_positions):
        raise AttentionKvD16NativeWidthGateError("selected positions drift")
    if summary["timing_policy"] != TIMING_POLICY:
        raise AttentionKvD16NativeWidthGateError("timing policy drift")
    if summary["proof_size_bytes"] != proof_size_bytes:
        raise AttentionKvD16NativeWidthGateError("proof-size scale drift")
    if summary["envelope_size_bytes"] != envelope_size_bytes:
        raise AttentionKvD16NativeWidthGateError("envelope-size scale drift")
    for key, expected in commitments.items():
        if summary[key] != expected:
            raise AttentionKvD16NativeWidthGateError("scale gate commitment drift")


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvD16NativeWidthGateError("payload must be object")
    required = {
        "schema", "issue", "source_issue", "decision", "claim_boundary", "first_blocker",
        "baseline_receipt", "scaled_receipt", "width_axis_result", "non_claims",
        "validation_commands", "scale_gate_commitment",
    }
    if not allow_missing_mutation_summary:
        required |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if set(payload) != required:
        raise AttentionKvD16NativeWidthGateError("payload field drift")
    if payload["schema"] != SCHEMA or payload["issue"] != ISSUE or payload["source_issue"] != SOURCE_ISSUE:
        raise AttentionKvD16NativeWidthGateError("metadata drift")
    if payload["decision"] != DECISION:
        raise AttentionKvD16NativeWidthGateError("decision drift")
    if payload["claim_boundary"] != CLAIM_BOUNDARY:
        raise AttentionKvD16NativeWidthGateError("claim boundary drift")
    if payload["first_blocker"] != FIRST_BLOCKER:
        raise AttentionKvD16NativeWidthGateError("first blocker drift")
    if payload["non_claims"] != list(NON_CLAIMS):
        raise AttentionKvD16NativeWidthGateError("non-claim drift")
    if payload["validation_commands"] != list(VALIDATION_COMMANDS):
        raise AttentionKvD16NativeWidthGateError("validation command drift")
    validate_receipt_summary(
        payload["baseline_receipt"],
        route_id=D8_ROUTE_ID,
        target_id=D8_TARGET_ID,
        proof_version=D8_PROOF_VERSION,
        required_backend_version=D8_REQUIRED_BACKEND_VERSION,
        key_width=8,
        value_width=8,
        selected_positions=D8_SELECTED_POSITIONS,
        proof_size_bytes=D8_PROOF_SIZE_BYTES,
        envelope_size_bytes=bounded_file_size(D8_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "d8 envelope"),
        commitments=D8_COMMITMENTS,
    )
    validate_receipt_summary(
        payload["scaled_receipt"],
        route_id=D16_ROUTE_ID,
        target_id=D16_TARGET_ID,
        proof_version=D16_PROOF_VERSION,
        required_backend_version=D16_REQUIRED_BACKEND_VERSION,
        key_width=16,
        value_width=16,
        selected_positions=D16_SELECTED_POSITIONS,
        proof_size_bytes=D16_PROOF_SIZE_BYTES,
        envelope_size_bytes=bounded_file_size(D16_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "d16 envelope"),
        commitments=D16_COMMITMENTS,
    )
    expected_axis = {
        "baseline_key_width": 8,
        "scaled_key_width": 16,
        "sequence_length_held_constant": 8,
        "score_rows_held_constant": 52,
        "trace_rows_held_constant": 64,
        "selected_positions_changed": True,
    }
    if payload["width_axis_result"] != expected_axis:
        raise AttentionKvD16NativeWidthGateError("width-axis result drift")
    if payload["scale_gate_commitment"] != _expected_commitment(payload):
        raise AttentionKvD16NativeWidthGateError("scale gate commitment drift")
    if not allow_missing_mutation_summary:
        cases = payload["mutation_cases"]
        if (
            not isinstance(cases, list)
            or any(not isinstance(case, dict) for case in cases)
            or [case.get("name") for case in cases] != list(EXPECTED_MUTATION_NAMES)
        ):
            raise AttentionKvD16NativeWidthGateError("mutation case drift")
        if any(case.get("rejected") is not True for case in cases):
            raise AttentionKvD16NativeWidthGateError("mutation rejection drift")
        if payload["mutations_checked"] != len(EXPECTED_MUTATION_NAMES):
            raise AttentionKvD16NativeWidthGateError("mutation count drift")
        if payload["mutations_rejected"] != len(EXPECTED_MUTATION_NAMES):
            raise AttentionKvD16NativeWidthGateError("mutation rejected count drift")
        if payload["all_mutations_rejected"] is not True:
            raise AttentionKvD16NativeWidthGateError("all mutations rejected drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_payload(payload)
    return [{
        "decision": payload["decision"],
        "baseline_key_width": payload["baseline_receipt"]["key_width"],
        "scaled_key_width": payload["scaled_receipt"]["key_width"],
        "baseline_score_rows": payload["baseline_receipt"]["score_row_count"],
        "scaled_score_rows": payload["scaled_receipt"]["score_row_count"],
        "baseline_proof_size_bytes": payload["baseline_receipt"]["proof_size_bytes"],
        "scaled_proof_size_bytes": payload["scaled_receipt"]["proof_size_bytes"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "scaled_statement_commitment": payload["scaled_receipt"]["statement_commitment"],
    }]


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_for_tsv(payload))


def to_tsv(payload: dict[str, Any]) -> str:
    import io

    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows_for_tsv(payload))
    return handle.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    payload = build_payload()
    write_json(args.write_json, payload)
    write_tsv(args.write_tsv, payload)


if __name__ == "__main__":
    main()
