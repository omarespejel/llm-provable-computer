#!/usr/bin/env python3
"""Checked native Stwo two-head gate for attention/KV.

This gate answers issue #455 narrowly: the native Stwo attention/KV AIR now
binds two explicit d=8 heads over an eight-step causal-prefix integer-argmax
sequence. It records multi-head statement binding and proof existence, not
Softmax, full inference, long-context evidence, recursion, PCD, or benchmark
timing.
"""

from __future__ import annotations

import argparse
import copy
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
TWO_HEAD_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json"
TWO_HEAD_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json"
D8_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_masked_sequence_proof_input.py"
TWO_HEAD_INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-gate-2026-05.tsv"
MAX_INPUT_JSON_BYTES = 1_048_576
MAX_ENVELOPE_JSON_BYTES = 1_048_576

NATIVE_INPUT_SCHEMA = "zkai-attention-kv-stwo-native-masked-sequence-air-proof-input-v1"
NATIVE_INPUT_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
NATIVE_ENVELOPE_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
TIMING_POLICY = "single_local_dev_profile_engineering_only_not_public_benchmark"

SCHEMA = "zkai-attention-kv-stwo-native-two-head-gate-v1"
ISSUE = 455
SOURCE_ISSUE = 453
DECISION = "GO_NATIVE_STWO_ATTENTION_KV_TWO_HEAD_D8_MASKED_SEQUENCE"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_TWO_HEAD_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_PROOF_"
    "NOT_SOFTMAX_NOT_LONG_CONTEXT_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
FIRST_BLOCKER = "NO_SOFTMAX_OR_LONG_CONTEXT_NATIVE_ATTENTION_PROOF_YET"
D8_ROUTE_ID = "local_stwo_attention_kv_d8_masked_sequence_proof"
TWO_HEAD_ROUTE_ID = "local_stwo_attention_kv_d8_two_head_masked_sequence_proof"

D8_TARGET_ID = "attention-kv-d8-causal-mask-sequence-v1"
D8_PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-sequence-air-proof-v1"
D8_REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-sequence-v1"
D8_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-statement-v1"
D8_SEMANTIC_SCOPE = "d8_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt"
D8_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-masked-sequence:v1"
D8_SELECTED_POSITIONS = (0, 2, 3, 3, 5, 5, 7, 9)
D8_COMMITMENTS = {
    "statement_commitment": "blake2b-256:dcb688e7e2d7076b2f2fe35c6aa3a12af57d676101c300b48cbda66797e4f232",
    "public_instance_commitment": "blake2b-256:3c5a7c1aaf6b7ececf3d729935b0548b0b947ce3c649f0370dd44fc687227631",
    "score_row_commitment": "blake2b-256:8348dc0d9c052050c77bc56a4c08896c283ca710ab2caca30f1bab60d8451337",
    "final_kv_cache_commitment": "blake2b-256:74038853585ec88f7211e615910923d194d5731af74197c370daaf906d0be1e2",
    "outputs_commitment": "blake2b-256:a39a6d6e90b4fa06d443807d4fe9110c0986a67c930d9ceff4e0bc4bbce9c083",
}

TWO_HEAD_TARGET_ID = "attention-kv-d8-causal-mask-two-head-v1"
TWO_HEAD_PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-air-proof-v1"
TWO_HEAD_REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-v1"
TWO_HEAD_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-two-head-statement-v1"
TWO_HEAD_SEMANTIC_SCOPE = "two_head_d8_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt"
TWO_HEAD_VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-masked-sequence-two-head:v1"
TWO_HEAD_SELECTED_POSITIONS = (1, 1, 1, 1, 0, 2, 2, 4, 0, 0, 7, 2, 2, 5, 6, 2)
TWO_HEAD_PROOF_SIZE_BYTES = 25453
TWO_HEAD_ENVELOPE_SIZE_BYTES = 343719
TWO_HEAD_COMMITMENTS = {
    "statement_commitment": "blake2b-256:718f31a22d372cf1a334791b116a535317a230503350b616d42bdd7dc3fe4aab",
    "public_instance_commitment": "blake2b-256:9e037276f313dd05838b2d64f9c04a8ebc096bb171213cf439423f39e0e6d91f",
    "score_row_commitment": "blake2b-256:ce21110487f94644359707df3dac02bc1cf40c9a748d29dd8f45581904683167",
    "final_kv_cache_commitment": "blake2b-256:1b4289832e620201afaf25aba2a816e4f34cadf352accf163fe40a6431ca6bc5",
    "outputs_commitment": "blake2b-256:03f3b934ae0148d5db3de1313ad6d93604fc7509df30e386d20e1e91d59421fd",
}

EXPECTED_MUTATION_NAMES = (
    "two_head_statement_commitment_relabeling",
    "two_head_public_instance_commitment_relabeling",
    "two_head_head_count_relabeling",
    "two_head_input_step_head_relabeling",
    "two_head_score_row_head_relabeling",
    "two_head_selected_position_relabeling",
    "two_head_final_kv_head_relabeling",
    "two_head_output_relabeling",
    "two_head_target_id_relabeling",
    "two_head_backend_version_relabeling",
    "two_head_proof_size_metric_smuggling",
    "two_head_envelope_size_metric_smuggling",
    "d8_baseline_statement_relabeling",
    "route_removed",
    "claim_boundary_softmax_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "unknown_field_injection",
)
MUTATION_CASE_KEYS = {"name", "rejected", "error"}
NON_CLAIMS = (
    "not a Softmax proof",
    "not full autoregressive inference",
    "not recursive verification or PCD",
    "not a long-context benchmark",
    "not a public performance benchmark row",
    "not a Starknet deployment result",
    "not proof aggregation across heads",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_two_head_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "decision",
    "baseline_head_count",
    "scaled_head_count",
    "baseline_score_rows",
    "scaled_score_rows",
    "baseline_trace_rows",
    "scaled_trace_rows",
    "baseline_proof_size_bytes",
    "scaled_proof_size_bytes",
    "mutations_checked",
    "mutations_rejected",
    "scaled_statement_commitment",
)


class AttentionKvTwoHeadNativeGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvTwoHeadNativeGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


D8_INPUT_MODULE = load_script_module(D8_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_masked_sequence_proof_input")
TWO_HEAD_INPUT_MODULE = load_script_module(TWO_HEAD_INPUT_SCRIPT, "zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input")


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    bounded_file_size(path, max_bytes, label)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvTwoHeadNativeGateError(f"failed to read {label}: {err}") from err


def bounded_file_size(path: pathlib.Path, max_bytes: int, label: str) -> int:
    if not path.is_file():
        raise AttentionKvTwoHeadNativeGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvTwoHeadNativeGateError(f"{label} size drift: got {size}, max {max_bytes}")
    return size


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def require_exact_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionKvTwoHeadNativeGateError(f"{label} malformed")
    return value


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
    head_count: int,
    key_width: int,
    value_width: int,
    sequence_length: int,
    input_steps: int,
    score_rows: int,
    trace_rows: int,
    initial_kv_items: int,
    final_kv_items: int,
    selected_positions: tuple[int, ...],
    commitments: dict[str, str],
) -> None:
    if not isinstance(input_payload, dict) or not isinstance(envelope, dict):
        raise AttentionKvTwoHeadNativeGateError("input/envelope must be objects")
    if input_payload.get("schema") != NATIVE_INPUT_SCHEMA:
        raise AttentionKvTwoHeadNativeGateError("input schema drift")
    if input_payload.get("decision") != NATIVE_INPUT_DECISION:
        raise AttentionKvTwoHeadNativeGateError("input decision drift")
    try:
        input_validator(input_payload)
    except Exception as err:
        raise AttentionKvTwoHeadNativeGateError(f"{input_label} source input validation drift: {err}") from err
    if envelope.get("input") != input_payload:
        raise AttentionKvTwoHeadNativeGateError("proof envelope/input split-brain drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvTwoHeadNativeGateError("proof backend drift")
    if envelope.get("proof_backend_version") != required_backend_version:
        raise AttentionKvTwoHeadNativeGateError("proof backend version drift")
    if envelope.get("statement_version") != statement_version:
        raise AttentionKvTwoHeadNativeGateError("statement version drift")
    if envelope.get("semantic_scope") != semantic_scope:
        raise AttentionKvTwoHeadNativeGateError("semantic scope drift")
    if envelope.get("decision") != NATIVE_ENVELOPE_DECISION:
        raise AttentionKvTwoHeadNativeGateError("proof envelope decision drift")
    for key, expected in (
        ("target_id", target_id),
        ("proof_version", proof_version),
        ("required_backend_version", required_backend_version),
        ("statement_version", statement_version),
        ("semantic_scope", semantic_scope),
        ("verifier_domain", verifier_domain),
    ):
        if input_payload.get(key) != expected:
            raise AttentionKvTwoHeadNativeGateError(f"{key} drift")
    if input_payload.get("head_count", 1) != head_count:
        raise AttentionKvTwoHeadNativeGateError("head count drift")
    if input_payload.get("key_width") != key_width or input_payload.get("value_width") != value_width:
        raise AttentionKvTwoHeadNativeGateError("width drift")
    if input_payload.get("sequence_length") != sequence_length:
        raise AttentionKvTwoHeadNativeGateError("sequence length drift")
    if len(input_payload.get("input_steps", [])) != input_steps:
        raise AttentionKvTwoHeadNativeGateError("input step count drift")
    if input_payload.get("score_row_count") != score_rows or len(input_payload.get("score_rows", [])) != score_rows:
        raise AttentionKvTwoHeadNativeGateError("score row count drift")
    if input_payload.get("trace_row_count") != trace_rows:
        raise AttentionKvTwoHeadNativeGateError("trace row count drift")
    if input_payload.get("initial_kv_items") != initial_kv_items:
        raise AttentionKvTwoHeadNativeGateError("initial KV item count drift")
    if input_payload.get("final_kv_items") != final_kv_items:
        raise AttentionKvTwoHeadNativeGateError("final KV item count drift")
    input_positions = input_payload.get("selected_positions")
    if not isinstance(input_positions, list) or any(not isinstance(item, int) or isinstance(item, bool) for item in input_positions):
        raise AttentionKvTwoHeadNativeGateError("selected positions malformed")
    if tuple(input_positions) != selected_positions:
        raise AttentionKvTwoHeadNativeGateError("selected positions drift")
    for key, expected in commitments.items():
        if input_payload.get(key) != expected:
            raise AttentionKvTwoHeadNativeGateError(f"{key} drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not proof:
        raise AttentionKvTwoHeadNativeGateError("proof bytes malformed")
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 or item > 255 for item in proof):
        raise AttentionKvTwoHeadNativeGateError("proof byte malformed")


def receipt_from_pair(
    route_id: str,
    input_payload: dict[str, Any],
    envelope: dict[str, Any],
    envelope_path: pathlib.Path,
) -> dict[str, Any]:
    proof_size = len(envelope["proof"])
    return {
        "route_id": route_id,
        "target_id": input_payload["target_id"],
        "proof_version": input_payload["proof_version"],
        "required_backend_version": input_payload["required_backend_version"],
        "statement_version": input_payload["statement_version"],
        "semantic_scope": input_payload["semantic_scope"],
        "verifier_domain": input_payload["verifier_domain"],
        "head_count": input_payload.get("head_count", 1),
        "key_width": input_payload["key_width"],
        "value_width": input_payload["value_width"],
        "sequence_length": input_payload["sequence_length"],
        "input_steps": len(input_payload["input_steps"]),
        "score_rows": input_payload["score_row_count"],
        "trace_rows": input_payload["trace_row_count"],
        "initial_kv_items": input_payload["initial_kv_items"],
        "final_kv_items": input_payload["final_kv_items"],
        "selected_positions": input_payload["selected_positions"],
        "proof_size_bytes": proof_size,
        "envelope_size_bytes": envelope_path.stat().st_size,
        "timing_policy": TIMING_POLICY,
        "statement_commitment": input_payload["statement_commitment"],
        "public_instance_commitment": input_payload["public_instance_commitment"],
        "score_row_commitment": input_payload["score_row_commitment"],
        "final_kv_cache_commitment": input_payload["final_kv_cache_commitment"],
        "outputs_commitment": input_payload["outputs_commitment"],
    }


def build_payload() -> dict[str, Any]:
    d8_input = read_bounded_json(D8_INPUT_JSON, MAX_INPUT_JSON_BYTES, "d8 input")
    d8_envelope = read_bounded_json(D8_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "d8 envelope")
    two_input = read_bounded_json(TWO_HEAD_INPUT_JSON, MAX_INPUT_JSON_BYTES, "two-head input")
    two_envelope = read_bounded_json(TWO_HEAD_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "two-head envelope")
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
        head_count=1,
        key_width=8,
        value_width=8,
        sequence_length=8,
        input_steps=8,
        score_rows=52,
        trace_rows=64,
        initial_kv_items=2,
        final_kv_items=10,
        selected_positions=D8_SELECTED_POSITIONS,
        commitments=D8_COMMITMENTS,
    )
    validate_pair(
        two_input,
        two_envelope,
        input_validator=TWO_HEAD_INPUT_MODULE.validate_payload,
        input_label="two-head",
        target_id=TWO_HEAD_TARGET_ID,
        proof_version=TWO_HEAD_PROOF_VERSION,
        required_backend_version=TWO_HEAD_REQUIRED_BACKEND_VERSION,
        statement_version=TWO_HEAD_STATEMENT_VERSION,
        semantic_scope=TWO_HEAD_SEMANTIC_SCOPE,
        verifier_domain=TWO_HEAD_VERIFIER_DOMAIN,
        head_count=2,
        key_width=8,
        value_width=8,
        sequence_length=8,
        input_steps=16,
        score_rows=104,
        trace_rows=128,
        initial_kv_items=4,
        final_kv_items=20,
        selected_positions=TWO_HEAD_SELECTED_POSITIONS,
        commitments=TWO_HEAD_COMMITMENTS,
    )
    d8_receipt = receipt_from_pair(D8_ROUTE_ID, d8_input, d8_envelope, D8_ENVELOPE_JSON)
    two_receipt = receipt_from_pair(TWO_HEAD_ROUTE_ID, two_input, two_envelope, TWO_HEAD_ENVELOPE_JSON)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "baseline_receipt": d8_receipt,
        "two_head_receipt": two_receipt,
        "multi_head_axis_result": {
            "baseline_head_count": 1,
            "scaled_head_count": 2,
            "same_key_width": True,
            "same_value_width": True,
            "same_sequence_length_per_head": True,
            "input_steps_doubled": two_receipt["input_steps"] == 2 * d8_receipt["input_steps"],
            "score_rows_doubled": two_receipt["score_rows"] == 2 * d8_receipt["score_rows"],
            "trace_rows_doubled": two_receipt["trace_rows"] == 2 * d8_receipt["trace_rows"],
            "proof_size_ratio_vs_d8": round(two_receipt["proof_size_bytes"] / d8_receipt["proof_size_bytes"], 6),
            "envelope_size_ratio_vs_d8": round(two_receipt["envelope_size_bytes"] / d8_receipt["envelope_size_bytes"], 6),
            "selected_positions_changed": two_receipt["selected_positions"] != d8_receipt["selected_positions"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["two_head_gate_commitment"] = _expected_commitment(payload)
    mutation_cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvTwoHeadNativeGateError as err:
            mutation_cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            mutation_cases.append({"name": name, "rejected": False, "error": "mutation unexpectedly accepted"})
    payload["mutation_cases"] = mutation_cases
    payload["mutations_checked"] = len(mutation_cases)
    payload["mutations_rejected"] = sum(1 for case in mutation_cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def _expected_commitment(payload: dict[str, Any]) -> str:
    commitment_payload = {key: value for key, value in payload.items() if key != "two_head_gate_commitment"}
    for transient in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        commitment_payload.pop(transient, None)
    return blake2b_commitment(commitment_payload, "ptvm:zkai:attention-kv:stwo-native-two-head-gate:v1")


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for transient in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        mutated.pop(transient, None)
    if name == "two_head_statement_commitment_relabeling":
        mutated["two_head_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "two_head_public_instance_commitment_relabeling":
        mutated["two_head_receipt"]["public_instance_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "two_head_head_count_relabeling":
        mutated["two_head_receipt"]["head_count"] = 1
    elif name == "two_head_input_step_head_relabeling":
        mutated["two_head_receipt"]["input_steps"] = 15
    elif name == "two_head_score_row_head_relabeling":
        mutated["two_head_receipt"]["score_row_commitment"] = mutated["baseline_receipt"]["score_row_commitment"]
    elif name == "two_head_selected_position_relabeling":
        mutated["two_head_receipt"]["selected_positions"][-1] += 1
    elif name == "two_head_final_kv_head_relabeling":
        mutated["two_head_receipt"]["final_kv_cache_commitment"] = mutated["baseline_receipt"]["final_kv_cache_commitment"]
    elif name == "two_head_output_relabeling":
        mutated["two_head_receipt"]["outputs_commitment"] = mutated["baseline_receipt"]["outputs_commitment"]
    elif name == "two_head_target_id_relabeling":
        mutated["two_head_receipt"]["target_id"] = D8_TARGET_ID
    elif name == "two_head_backend_version_relabeling":
        mutated["two_head_receipt"]["required_backend_version"] = D8_REQUIRED_BACKEND_VERSION
    elif name == "two_head_proof_size_metric_smuggling":
        mutated["two_head_receipt"]["proof_size_bytes"] += 1
    elif name == "two_head_envelope_size_metric_smuggling":
        mutated["two_head_receipt"]["envelope_size_bytes"] += 1
    elif name == "d8_baseline_statement_relabeling":
        mutated["baseline_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "route_removed":
        mutated.pop("two_head_receipt")
    elif name == "claim_boundary_softmax_overclaim":
        mutated["claim_boundary"] = "NATIVE_STWO_SOFTMAX_MULTIHEAD_FULL_ATTENTION_PROOF"
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "non_claim_removed":
        mutated["non_claims"] = mutated["non_claims"][:-1]
    elif name == "unknown_field_injection":
        mutated["unknown"] = True
    else:
        raise AttentionKvTwoHeadNativeGateError(f"unknown mutation name: {name}")
    if name not in {"unknown_field_injection", "route_removed"}:
        mutated["two_head_gate_commitment"] = _expected_commitment(mutated)
    return mutated


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvTwoHeadNativeGateError("payload must be object")
    expected_fields = {
        "schema",
        "issue",
        "source_issue",
        "decision",
        "claim_boundary",
        "first_blocker",
        "baseline_receipt",
        "two_head_receipt",
        "multi_head_axis_result",
        "non_claims",
        "validation_commands",
        "two_head_gate_commitment",
    }
    if not allow_missing_mutation_summary:
        expected_fields |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    elif {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"} & set(payload):
        expected_fields |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if set(payload) != expected_fields:
        raise AttentionKvTwoHeadNativeGateError("payload field set mismatch")
    for key, expected in (
        ("schema", SCHEMA),
        ("issue", ISSUE),
        ("source_issue", SOURCE_ISSUE),
        ("decision", DECISION),
        ("claim_boundary", CLAIM_BOUNDARY),
        ("first_blocker", FIRST_BLOCKER),
    ):
        if payload.get(key) != expected:
            raise AttentionKvTwoHeadNativeGateError(f"{key} drift")
    if tuple(payload.get("non_claims", ())) != NON_CLAIMS:
        raise AttentionKvTwoHeadNativeGateError("non-claim drift")
    if tuple(payload.get("validation_commands", ())) != VALIDATION_COMMANDS:
        raise AttentionKvTwoHeadNativeGateError("validation command drift")
    validate_receipt_summary(payload["baseline_receipt"], baseline=True)
    validate_receipt_summary(payload["two_head_receipt"], baseline=False)
    validate_axis_result(payload["multi_head_axis_result"], payload["baseline_receipt"], payload["two_head_receipt"])
    if payload["two_head_gate_commitment"] != _expected_commitment(payload):
        raise AttentionKvTwoHeadNativeGateError("two-head gate commitment drift")
    if not allow_missing_mutation_summary:
        validate_mutation_summary(payload)


def validate_receipt_summary(receipt: Any, *, baseline: bool) -> None:
    if not isinstance(receipt, dict):
        raise AttentionKvTwoHeadNativeGateError("receipt summary must be object")
    expected_keys = {
        "route_id",
        "target_id",
        "proof_version",
        "required_backend_version",
        "statement_version",
        "semantic_scope",
        "verifier_domain",
        "head_count",
        "key_width",
        "value_width",
        "sequence_length",
        "input_steps",
        "score_rows",
        "trace_rows",
        "initial_kv_items",
        "final_kv_items",
        "selected_positions",
        "proof_size_bytes",
        "envelope_size_bytes",
        "timing_policy",
        "statement_commitment",
        "public_instance_commitment",
        "score_row_commitment",
        "final_kv_cache_commitment",
        "outputs_commitment",
    }
    if set(receipt) != expected_keys:
        raise AttentionKvTwoHeadNativeGateError("receipt field set mismatch")
    if baseline:
        expected = {
            "route_id": D8_ROUTE_ID,
            "target_id": D8_TARGET_ID,
            "proof_version": D8_PROOF_VERSION,
            "required_backend_version": D8_REQUIRED_BACKEND_VERSION,
            "statement_version": D8_STATEMENT_VERSION,
            "semantic_scope": D8_SEMANTIC_SCOPE,
            "verifier_domain": D8_VERIFIER_DOMAIN,
            "head_count": 1,
            "key_width": 8,
            "value_width": 8,
            "sequence_length": 8,
            "input_steps": 8,
            "score_rows": 52,
            "trace_rows": 64,
            "initial_kv_items": 2,
            "final_kv_items": 10,
            "selected_positions": list(D8_SELECTED_POSITIONS),
            "statement_commitment": D8_COMMITMENTS["statement_commitment"],
            "public_instance_commitment": D8_COMMITMENTS["public_instance_commitment"],
            "score_row_commitment": D8_COMMITMENTS["score_row_commitment"],
            "final_kv_cache_commitment": D8_COMMITMENTS["final_kv_cache_commitment"],
            "outputs_commitment": D8_COMMITMENTS["outputs_commitment"],
        }
    else:
        expected = {
            "route_id": TWO_HEAD_ROUTE_ID,
            "target_id": TWO_HEAD_TARGET_ID,
            "proof_version": TWO_HEAD_PROOF_VERSION,
            "required_backend_version": TWO_HEAD_REQUIRED_BACKEND_VERSION,
            "statement_version": TWO_HEAD_STATEMENT_VERSION,
            "semantic_scope": TWO_HEAD_SEMANTIC_SCOPE,
            "verifier_domain": TWO_HEAD_VERIFIER_DOMAIN,
            "head_count": 2,
            "key_width": 8,
            "value_width": 8,
            "sequence_length": 8,
            "input_steps": 16,
            "score_rows": 104,
            "trace_rows": 128,
            "initial_kv_items": 4,
            "final_kv_items": 20,
            "selected_positions": list(TWO_HEAD_SELECTED_POSITIONS),
            "statement_commitment": TWO_HEAD_COMMITMENTS["statement_commitment"],
            "public_instance_commitment": TWO_HEAD_COMMITMENTS["public_instance_commitment"],
            "score_row_commitment": TWO_HEAD_COMMITMENTS["score_row_commitment"],
            "final_kv_cache_commitment": TWO_HEAD_COMMITMENTS["final_kv_cache_commitment"],
            "outputs_commitment": TWO_HEAD_COMMITMENTS["outputs_commitment"],
        }
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            raise AttentionKvTwoHeadNativeGateError(f"{key} drift")
    for key in ("proof_size_bytes", "envelope_size_bytes"):
        require_exact_int(receipt.get(key), key)
    if not baseline and receipt["proof_size_bytes"] != TWO_HEAD_PROOF_SIZE_BYTES:
        raise AttentionKvTwoHeadNativeGateError("proof-size scale drift")
    if not baseline and receipt["envelope_size_bytes"] != TWO_HEAD_ENVELOPE_SIZE_BYTES:
        raise AttentionKvTwoHeadNativeGateError("envelope-size scale drift")
    if receipt["timing_policy"] != TIMING_POLICY:
        raise AttentionKvTwoHeadNativeGateError("timing policy drift")


def validate_axis_result(axis: Any, baseline: dict[str, Any], scaled: dict[str, Any]) -> None:
    if not isinstance(axis, dict):
        raise AttentionKvTwoHeadNativeGateError("axis result must be object")
    expected_keys = {
        "baseline_head_count",
        "scaled_head_count",
        "same_key_width",
        "same_value_width",
        "same_sequence_length_per_head",
        "input_steps_doubled",
        "score_rows_doubled",
        "trace_rows_doubled",
        "proof_size_ratio_vs_d8",
        "envelope_size_ratio_vs_d8",
        "selected_positions_changed",
    }
    if set(axis) != expected_keys:
        raise AttentionKvTwoHeadNativeGateError("axis result field set mismatch")
    expected = {
        "baseline_head_count": 1,
        "scaled_head_count": 2,
        "same_key_width": True,
        "same_value_width": True,
        "same_sequence_length_per_head": True,
        "input_steps_doubled": True,
        "score_rows_doubled": True,
        "trace_rows_doubled": True,
        "proof_size_ratio_vs_d8": round(scaled["proof_size_bytes"] / baseline["proof_size_bytes"], 6),
        "envelope_size_ratio_vs_d8": round(scaled["envelope_size_bytes"] / baseline["envelope_size_bytes"], 6),
        "selected_positions_changed": True,
    }
    if axis != expected:
        raise AttentionKvTwoHeadNativeGateError("axis result drift")


def validate_mutation_summary(payload: dict[str, Any]) -> None:
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvTwoHeadNativeGateError("mutation case drift")
    names = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != MUTATION_CASE_KEYS:
            raise AttentionKvTwoHeadNativeGateError("mutation case drift")
        names.append(case["name"])
        if case["name"] not in EXPECTED_MUTATION_NAMES:
            raise AttentionKvTwoHeadNativeGateError("mutation name drift")
        if case["rejected"] is not True or not isinstance(case["error"], str) or not case["error"]:
            raise AttentionKvTwoHeadNativeGateError("mutation rejection drift")
    if tuple(names) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvTwoHeadNativeGateError("mutation order drift")
    if payload.get("mutations_checked") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvTwoHeadNativeGateError("mutation count drift")
    if payload.get("mutations_rejected") != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvTwoHeadNativeGateError("mutation rejection count drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvTwoHeadNativeGateError("mutation rejection drift")


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    row = {
        "decision": payload["decision"],
        "baseline_head_count": payload["baseline_receipt"]["head_count"],
        "scaled_head_count": payload["two_head_receipt"]["head_count"],
        "baseline_score_rows": payload["baseline_receipt"]["score_rows"],
        "scaled_score_rows": payload["two_head_receipt"]["score_rows"],
        "baseline_trace_rows": payload["baseline_receipt"]["trace_rows"],
        "scaled_trace_rows": payload["two_head_receipt"]["trace_rows"],
        "baseline_proof_size_bytes": payload["baseline_receipt"]["proof_size_bytes"],
        "scaled_proof_size_bytes": payload["two_head_receipt"]["proof_size_bytes"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "scaled_statement_commitment": payload["two_head_receipt"]["statement_commitment"],
    }
    out = []
    out.append("\t".join(TSV_COLUMNS))
    out.append("\t".join(str(row[column]) for column in TSV_COLUMNS))
    return "\n".join(out) + "\n"


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_tsv(payload), encoding="utf-8")


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
