#!/usr/bin/env python3
"""Checked native Stwo d8 bounded Softmax-table-attention gate for issue #463.

The gate records a native d8 attention/KV proof whose score-derived weights come
from a statement-bound exp-like lookup table. It is deliberately scoped: table
membership is verifier-recomputed over public rows, not an AIR-private lookup
argument, and this is not exact Softmax.
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
INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json"
ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json"
INPUT_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv"
MAX_INPUT_JSON_BYTES = 1_048_576
MAX_ENVELOPE_JSON_BYTES = 1_048_576

NATIVE_INPUT_SCHEMA = "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-air-proof-input-v1"
NATIVE_INPUT_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_D8_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
NATIVE_ENVELOPE_DECISION = "GO_STWO_NATIVE_ATTENTION_KV_BOUNDED_SOFTMAX_TABLE_AIR_PROOF"
TIMING_POLICY = "single_local_dev_profile_engineering_only_not_public_benchmark"

SCHEMA = "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-v1"
ISSUE = 463
SOURCE_ISSUE = 460
DECISION = "GO_NATIVE_STWO_ATTENTION_KV_BOUNDED_SOFTMAX_TABLE_D8_MASKED_SEQUENCE"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_D8_CAUSAL_MASKED_BOUNDED_SOFTMAX_TABLE_ATTENTION_KV_PROOF_"
    "NOT_EXACT_SOFTMAX_NOT_LONG_CONTEXT_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
FIRST_BLOCKER = "NO_AIR_PRIVATE_LOOKUP_ARGUMENT_OR_EXACT_SOFTMAX_EXP_DIV_AIR_YET"
ROUTE_ID = "local_stwo_attention_kv_d8_bounded_softmax_table_masked_sequence_proof"

TARGET_ID = "attention-kv-d8-causal-mask-bounded-softmax-table-v1"
PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-bounded-softmax-table-air-proof-v1"
REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-bounded-softmax-table-v1"
STATEMENT_VERSION = "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-statement-v1"
SEMANTIC_SCOPE = "d8_bounded_table_softmax_approx_attention_kv_causal_mask_rows_bound_to_statement_receipt"
VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-d8-bounded-softmax-table:v1"
SEMANTICS = "bounded_table_softmax_approx_attention"
WEIGHT_POLICY = "exp2_half_gap_table_clipped_8_floor_division"
SCORE_SCALE = 1
SCORE_GAP_CLIP = 8
WEIGHT_TABLE = (
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
PROOF_SIZE_BYTES = 44692
ENVELOPE_SIZE_BYTES = 451982
COMMITMENTS = {
    "statement_commitment": "blake2b-256:ce2f67e8009f647cef6282bc687e0346e52a27101d814b9626cd02163b417398",
    "public_instance_commitment": "blake2b-256:384bff181005ababda4e2227b3184382edf8069f4a112b436735886c2b567d31",
    "score_row_commitment": "blake2b-256:1279d23d93288d6ddce174aaae45b895f8c0ba690754c0a3035a84a556efb5ec",
    "final_kv_cache_commitment": "blake2b-256:593789678d4a171b53a2a91698d0cba11798c5b9273b9242a1d2e4d694e26873",
    "outputs_commitment": "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
    "weight_table_commitment": "blake2b-256:8c45ca7eec1032a0ffa5d5a1e842bebd5f6268d75f82d696b29ec7cf9a420e13",
}
EXPECTED_ATTENTION_OUTPUTS = (
    [1, 1, 0, -1, 1, -1, 2, 1],
    [3, 1, 1, 0, -1, 1, 2, 0],
    [3, -1, 0, 1, 1, 0, -1, 1],
    [2, 1, 0, 1, 1, 0, 1, 1],
    [3, 2, 0, -1, 1, 1, -1, 1],
    [5, 1, 1, -2, 0, 3, -2, 1],
    [4, 4, -2, 0, 1, 1, 2, -1],
    [-3, 3, 0, -2, 3, 1, -1, 0],
)
EXPECTED_MUTATION_NAMES = (
    "table_statement_commitment_relabeling",
    "table_public_instance_commitment_relabeling",
    "table_weight_policy_relabeling",
    "table_weight_table_commitment_relabeling",
    "table_score_scale_relabeling",
    "table_score_gap_clip_relabeling",
    "bounded_softmax_table_attention_outputs_relabeling",
    "table_outputs_commitment_relabeling",
    "table_score_row_count_relabeling",
    "table_final_kv_relabeling",
    "table_target_id_relabeling",
    "table_backend_version_relabeling",
    "proof_size_metric_smuggling",
    "envelope_size_metric_smuggling",
    "claim_boundary_exact_softmax_overclaim",
    "first_blocker_removed",
    "non_claim_removed",
    "unknown_field_injection",
)
EXPECTED_MUTATION_COUNT = 18
MUTATION_CASE_KEYS = {"name", "rejected", "error"}
NON_CLAIMS = (
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full autoregressive inference",
    "not recursive verification or PCD",
    "not a long-context benchmark",
    "not a public performance benchmark row",
    "not a Starknet deployment result",
    "not AIR-private lookup arguments",
)
VALIDATION_COMMANDS = (
    "python3 scripts/zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_d8_bounded_softmax_table_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d8_bounded_softmax_table_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d8_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_d8_bounded_softmax_table_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d8_bounded_softmax_table_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "decision",
    "route_id",
    "semantics",
    "weight_policy",
    "score_gap_clip",
    "weight_table_commitment",
    "key_width",
    "value_width",
    "sequence_length",
    "score_rows",
    "trace_rows",
    "proof_size_bytes",
    "envelope_size_bytes",
    "mutations_checked",
    "mutations_rejected",
    "statement_commitment",
)


class AttentionKvBoundedSoftmaxTableNativeGateError(ValueError):
    pass


def load_script_module(path: pathlib.Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"failed to load {module_name}: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise ImportError(f"failed to import {module_name} from {path}: {err}") from err
    return module


INPUT_MODULE = load_script_module(INPUT_SCRIPT, "zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input")


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    bounded_file_size(path, max_bytes, label)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"failed to read {label}: {err}") from err


def bounded_file_size(path: pathlib.Path, max_bytes: int, label: str) -> int:
    if not path.is_file():
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"{label} size drift: got {size}, max {max_bytes}")
    return size


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def validate_source_pair(input_payload: Any, envelope: Any) -> None:
    if not isinstance(input_payload, dict) or not isinstance(envelope, dict):
        raise AttentionKvBoundedSoftmaxTableNativeGateError("input/envelope must be objects")
    if input_payload.get("schema") != NATIVE_INPUT_SCHEMA:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("input schema drift")
    if input_payload.get("decision") != NATIVE_INPUT_DECISION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("input decision drift")
    try:
        INPUT_MODULE.validate_payload(input_payload)
    except Exception as err:
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"source input validation drift: {err}") from err
    if envelope.get("input") != input_payload:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("proof envelope/input split-brain drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvBoundedSoftmaxTableNativeGateError("proof backend drift")
    if envelope.get("proof_backend_version") != REQUIRED_BACKEND_VERSION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("proof backend version drift")
    if envelope.get("statement_version") != STATEMENT_VERSION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("statement version drift")
    if envelope.get("semantic_scope") != SEMANTIC_SCOPE:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("semantic scope drift")
    if envelope.get("decision") != NATIVE_ENVELOPE_DECISION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("proof envelope decision drift")
    if len(envelope.get("proof", [])) != PROOF_SIZE_BYTES:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("proof byte length drift")
    if input_payload.get("target_id") != TARGET_ID:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("target_id drift")
    if input_payload.get("proof_version") != PROOF_VERSION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("proof_version drift")
    if input_payload.get("required_backend_version") != REQUIRED_BACKEND_VERSION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("required_backend_version drift")
    if input_payload.get("statement_version") != STATEMENT_VERSION:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("statement_version drift")
    if input_payload.get("semantic_scope") != SEMANTIC_SCOPE:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("semantic_scope drift")
    if input_payload.get("verifier_domain") != VERIFIER_DOMAIN:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("verifier_domain drift")
    if input_payload.get("semantics") != SEMANTICS:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("semantics drift")
    if input_payload.get("weight_policy") != WEIGHT_POLICY:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("weight_policy drift")
    if input_payload.get("score_scale") != SCORE_SCALE:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("score_scale drift")
    if input_payload.get("score_gap_clip") != SCORE_GAP_CLIP:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("score_gap_clip drift")
    if input_payload.get("weight_table") != list(WEIGHT_TABLE):
        raise AttentionKvBoundedSoftmaxTableNativeGateError("weight_table drift")
    if tuple(input_payload.get("attention_outputs", [])) != EXPECTED_ATTENTION_OUTPUTS:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("attention_outputs drift")
    for key, expected in COMMITMENTS.items():
        if input_payload.get(key) != expected:
            raise AttentionKvBoundedSoftmaxTableNativeGateError(f"{key} drift")


def receipt_summary(input_payload: dict[str, Any], envelope: dict[str, Any], envelope_size_bytes: int) -> dict[str, Any]:
    validate_source_pair(input_payload, envelope)
    return {
        "route_id": ROUTE_ID,
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "decision": DECISION,
        "target_id": TARGET_ID,
        "proof_version": PROOF_VERSION,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "statement_version": STATEMENT_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "verifier_domain": VERIFIER_DOMAIN,
        "semantics": SEMANTICS,
        "weight_policy": WEIGHT_POLICY,
        "score_scale": input_payload["score_scale"],
        "score_gap_clip": input_payload["score_gap_clip"],
        "weight_table": input_payload["weight_table"],
        "key_width": input_payload["key_width"],
        "value_width": input_payload["value_width"],
        "sequence_length": input_payload["sequence_length"],
        "initial_kv_items": input_payload["initial_kv_items"],
        "final_kv_items": input_payload["final_kv_items"],
        "score_rows": input_payload["score_row_count"],
        "trace_rows": input_payload["trace_row_count"],
        "attention_outputs": input_payload["attention_outputs"],
        "proof_size_bytes": len(envelope["proof"]),
        "envelope_size_bytes": envelope_size_bytes,
        "statement_commitment": input_payload["statement_commitment"],
        "public_instance_commitment": input_payload["public_instance_commitment"],
        "score_row_commitment": input_payload["score_row_commitment"],
        "final_kv_cache_commitment": input_payload["final_kv_cache_commitment"],
        "outputs_commitment": input_payload["outputs_commitment"],
        "weight_table_commitment": input_payload["weight_table_commitment"],
    }


def mutation_cases_for(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if len(EXPECTED_MUTATION_NAMES) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("internal mutation spec count drift")
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvBoundedSoftmaxTableNativeGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "accepted mutation"})
    return cases


def build_payload() -> dict[str, Any]:
    input_payload = read_bounded_json(INPUT_JSON, MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
    envelope_size_bytes = bounded_file_size(ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
    envelope = read_bounded_json(ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
    receipt = receipt_summary(input_payload, envelope, envelope_size_bytes)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "bounded_softmax_table_receipt": receipt,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["gate_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "receipt_statement_commitment": receipt["statement_commitment"],
            "first_blocker": payload["first_blocker"],
        },
        "ptvm:zkai:attention-kv-d8-bounded-softmax-table-native-gate:v1",
    )
    cases = mutation_cases_for(payload)
    payload["mutation_cases"] = cases
    payload["mutations_checked"] = len(cases)
    payload["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    payload["all_mutations_rejected"] = payload["mutations_checked"] == payload["mutations_rejected"]
    validate_payload(payload)
    return payload


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
        mutated.pop(key, None)
    receipt = mutated["bounded_softmax_table_receipt"]
    if name == "table_statement_commitment_relabeling":
        receipt["statement_commitment"] = "blake2b-256:" + "55" * 32
    elif name == "table_public_instance_commitment_relabeling":
        receipt["public_instance_commitment"] = "blake2b-256:" + "66" * 32
    elif name == "table_weight_policy_relabeling":
        receipt["weight_policy"] = "exact_softmax"
    elif name == "table_weight_table_commitment_relabeling":
        receipt["weight_table_commitment"] = "blake2b-256:" + "99" * 32
    elif name == "table_score_scale_relabeling":
        receipt["score_scale"] = 2
    elif name == "table_score_gap_clip_relabeling":
        receipt["score_gap_clip"] = 4
    elif name == "bounded_softmax_table_attention_outputs_relabeling":
        receipt["attention_outputs"][0][0] += 1
    elif name == "table_outputs_commitment_relabeling":
        receipt["outputs_commitment"] = "blake2b-256:" + "77" * 32
    elif name == "table_score_row_count_relabeling":
        receipt["score_rows"] += 1
    elif name == "table_final_kv_relabeling":
        receipt["final_kv_cache_commitment"] = "blake2b-256:" + "88" * 32
    elif name == "table_target_id_relabeling":
        receipt["target_id"] = "attention-kv-d8-causal-mask-exact-softmax-v1"
    elif name == "table_backend_version_relabeling":
        receipt["required_backend_version"] = "fake-backend"
    elif name == "proof_size_metric_smuggling":
        receipt["proof_size_bytes"] += 1
    elif name == "envelope_size_metric_smuggling":
        receipt["envelope_size_bytes"] += 1
    elif name == "claim_boundary_exact_softmax_overclaim":
        mutated["claim_boundary"] = mutated["claim_boundary"].replace("NOT_EXACT_SOFTMAX_", "")
    elif name == "first_blocker_removed":
        mutated["first_blocker"] = ""
    elif name == "non_claim_removed":
        mutated["non_claims"].pop(0)
    elif name == "unknown_field_injection":
        mutated["unexpected"] = "claim smuggling"
    else:
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"unknown mutation: {name}")
    return mutated


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvBoundedSoftmaxTableNativeGateError("payload must be object")
    allowed_keys = {
        "schema",
        "issue",
        "source_issue",
        "decision",
        "claim_boundary",
        "first_blocker",
        "timing_policy",
        "bounded_softmax_table_receipt",
        "non_claims",
        "validation_commands",
        "gate_commitment",
        "mutation_cases",
        "mutations_checked",
        "mutations_rejected",
        "all_mutations_rejected",
    }
    extra = set(payload) - allowed_keys
    if extra:
        raise AttentionKvBoundedSoftmaxTableNativeGateError(f"unknown field(s): {sorted(extra)}")
    expected = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "timing_policy": TIMING_POLICY,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AttentionKvBoundedSoftmaxTableNativeGateError(f"{key} drift")
    receipt = payload.get("bounded_softmax_table_receipt")
    if not isinstance(receipt, dict):
        raise AttentionKvBoundedSoftmaxTableNativeGateError("missing bounded Softmax-table receipt")
    expected_receipt = {
        "route_id": ROUTE_ID,
        "proof_system": "Stwo",
        "proof_backend": "stwo",
        "decision": DECISION,
        "target_id": TARGET_ID,
        "proof_version": PROOF_VERSION,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "statement_version": STATEMENT_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "verifier_domain": VERIFIER_DOMAIN,
        "semantics": SEMANTICS,
        "weight_policy": WEIGHT_POLICY,
        "score_scale": SCORE_SCALE,
        "score_gap_clip": SCORE_GAP_CLIP,
        "weight_table": list(WEIGHT_TABLE),
        "key_width": 8,
        "value_width": 8,
        "sequence_length": 8,
        "initial_kv_items": 2,
        "final_kv_items": 10,
        "score_rows": 52,
        "trace_rows": 64,
        "attention_outputs": [list(row) for row in EXPECTED_ATTENTION_OUTPUTS],
        "proof_size_bytes": PROOF_SIZE_BYTES,
        "envelope_size_bytes": ENVELOPE_SIZE_BYTES,
    }
    for key, expected_value in expected_receipt.items():
        if receipt.get(key) != expected_value:
            raise AttentionKvBoundedSoftmaxTableNativeGateError(f"bounded Softmax-table receipt {key} drift")
    for key, expected_value in COMMITMENTS.items():
        if receipt.get(key) != expected_value:
            raise AttentionKvBoundedSoftmaxTableNativeGateError(f"bounded Softmax-table receipt {key} drift")
    expected_gate_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "receipt_statement_commitment": receipt["statement_commitment"],
            "first_blocker": payload["first_blocker"],
        },
        "ptvm:zkai:attention-kv-d8-bounded-softmax-table-native-gate:v1",
    )
    if payload.get("gate_commitment") != expected_gate_commitment:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("gate commitment drift")
    if allow_missing_mutation_summary and "mutation_cases" not in payload:
        return
    cases = payload.get("mutation_cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_MUTATION_COUNT:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("mutation case count drift")
    names = tuple(case.get("name") for case in cases if isinstance(case, dict))
    if names != EXPECTED_MUTATION_NAMES:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("mutation names drift")
    for case in cases:
        if not isinstance(case, dict) or set(case) != MUTATION_CASE_KEYS:
            raise AttentionKvBoundedSoftmaxTableNativeGateError("mutation case schema drift")
        if case["rejected"] is not True:
            raise AttentionKvBoundedSoftmaxTableNativeGateError("mutation rejection drift")
    if payload.get("mutations_checked") != EXPECTED_MUTATION_COUNT:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("mutations checked drift")
    if payload.get("mutations_rejected") != EXPECTED_MUTATION_COUNT:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("mutations rejected drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvBoundedSoftmaxTableNativeGateError("all mutations rejected drift")


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    receipt = payload["bounded_softmax_table_receipt"]
    row = {
        "decision": payload["decision"],
        "route_id": receipt["route_id"],
        "semantics": receipt["semantics"],
        "weight_policy": receipt["weight_policy"],
        "score_gap_clip": receipt["score_gap_clip"],
        "weight_table_commitment": receipt["weight_table_commitment"],
        "key_width": receipt["key_width"],
        "value_width": receipt["value_width"],
        "sequence_length": receipt["sequence_length"],
        "score_rows": receipt["score_rows"],
        "trace_rows": receipt["trace_rows"],
        "proof_size_bytes": receipt["proof_size_bytes"],
        "envelope_size_bytes": receipt["envelope_size_bytes"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "statement_commitment": receipt["statement_commitment"],
    }
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return buf.getvalue()


def write_json(payload: dict[str, Any], path: pathlib.Path) -> None:
    validate_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(payload: dict[str, Any], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_tsv(payload), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    args = parser.parse_args()
    payload = build_payload()
    write_json(payload, args.write_json)
    write_tsv(payload, args.write_tsv)


if __name__ == "__main__":
    main()
