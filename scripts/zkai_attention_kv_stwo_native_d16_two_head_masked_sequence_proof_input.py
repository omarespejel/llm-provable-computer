#!/usr/bin/env python3
"""Build the native Stwo attention/KV d16-two-head masked-sequence proof input.

This supports issue #521 by building the source d16 two-head
integer-argmax attention/KV fixture: causal-prefix mask, eight carried steps per
head, and public-row binding discipline, with both width and head count present
in the same source surface.

It is intentionally scoped: not Softmax, not full inference, not long-context
inference, and not recursive/PCD.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-native-masked-sequence-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
ISSUE = 521
SOURCE_ISSUE = 521
TARGET_ID = "attention-kv-d16-two-head-causal-mask-v1"
REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d16-two-head-causal-mask-v1"
PROOF_VERSION = "stwo-attention-kv-d16-two-head-causal-mask-air-proof-v1"
STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-d16-two-head-statement-v1"
SEMANTIC_SCOPE = "d16_two_head_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt"
VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-masked-sequence-d16-two-head:v1"
SEMANTICS = "integer_argmax_attention"
MASKING_POLICY = "causal_prefix_position_lte_query_token"
TIE_BREAK = "lowest_position"
KEY_WIDTH = 16
VALUE_WIDTH = 16
HEAD_COUNT = 2
SEQUENCE_LENGTH = 8
INITIAL_KV_ITEMS_PER_HEAD = 2
FINAL_KV_ITEMS_PER_HEAD = INITIAL_KV_ITEMS_PER_HEAD + SEQUENCE_LENGTH
INITIAL_KV_ITEMS = HEAD_COUNT * INITIAL_KV_ITEMS_PER_HEAD
FINAL_KV_ITEMS = HEAD_COUNT * FINAL_KV_ITEMS_PER_HEAD
TRACE_ROW_COUNT = 128
SCORE_ROW_COUNT = HEAD_COUNT * sum(INITIAL_KV_ITEMS_PER_HEAD + step + 1 for step in range(SEQUENCE_LENGTH))
SCORE_GAP_BITS = 16
CAUSAL_GAP_BITS = 16
TIE_GAP_BITS = 16
MAX_ABS_VALUE = 1_000_000

ROW_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-score-rows:v1"
INITIAL_KV_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-initial-kv:v1"
INPUT_STEPS_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-input-steps:v1"
FINAL_KV_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-final-kv:v1"
OUTPUTS_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-outputs:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-public-instance:v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-proof-parameters:v1"

NON_CLAIMS = [
    "not Softmax attention",
    "not full transformer inference",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not long-context benchmark evidence",
    "not on-chain verification evidence",
    "argmax and sequence carry are verifier-recomputed from public rows before proof verification",
]

PROOF_VERIFIER_HARDENING = [
    "native Stwo AIR proves query-key dot-product rows for every checked candidate",
    "native Stwo AIR proves selected-score dominance gaps are nonnegative via bit decomposition",
    "native Stwo AIR proves causal-prefix mask gaps are nonnegative via bit decomposition",
    "native Stwo AIR binds selected candidate values to the emitted attention output row",
    "verifier recomputes append-only KV carry and lowest-position tie-break before proof verification",
    "score-row, initial-KV, input-step, final-KV, output, public-instance, and statement commitments are recomputed before proof verification",
    "fixed publication-v1 PCS verifier profile before commitment-root recomputation",
    "bounded envelope JSON before deserialization and bounded proof bytes before proof parsing",
    "commitment-vector length check before commitment indexing",
]

NEXT_BACKEND_STEP = "scale the native Stwo attention/KV proof surface to bounded Softmax-like approximation or a larger per-head frontier only after preserving the same multi-head, width, carry, mask, and selected-output rejection surface"

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_kv_stwo_native_d16_two_head_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_d16_two_head_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_d16_two_head_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_two_head_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "issue",
    "decision",
    "proof_version",
    "key_width",
    "value_width",
    "head_count",
    "sequence_length",
    "score_row_count",
    "trace_row_count",
    "selected_positions",
    "score_row_commitment",
    "final_kv_cache_commitment",
    "outputs_commitment",
    "statement_commitment",
    "non_claims",
)


class AttentionKvStwoNativeD16TwoHeadInputError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def commitment_from_parts(parts: list[tuple[str, Any]], domain: str) -> str:
    encoded = b"".join(
        str(label).encode("utf-8") + b"=" + canonical_json_bytes(value) + b"\n"
        for label, value in parts
    )
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(encoded)
    return f"blake2b-256:{digest.hexdigest()}"


def require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionKvStwoNativeD16TwoHeadInputError(f"{label} must be an integer")
    if not -MAX_ABS_VALUE <= value <= MAX_ABS_VALUE:
        raise AttentionKvStwoNativeD16TwoHeadInputError(f"{label} outside bounded fixture range")
    return value


def dot(lhs: list[int], rhs: list[int]) -> int:
    if len(lhs) != KEY_WIDTH or len(rhs) != KEY_WIDTH:
        raise AttentionKvStwoNativeD16TwoHeadInputError("dot-product width mismatch")
    return sum(require_int(left, "query") * require_int(right, "key") for left, right in zip(lhs, rhs, strict=True))


def vector_material_kv(cache: list[dict[str, Any]]) -> list[list[int]]:
    return [[item["head_index"], item["position"], *item["key"], *item["value"]] for item in cache]


def input_steps_material(steps: list[dict[str, Any]]) -> list[list[int]]:
    return [[step["head_index"], step["token_position"], *step["query"], *step["new_key"], *step["new_value"]] for step in steps]


def score_rows_material(rows: list[dict[str, Any]]) -> list[list[int]]:
    material: list[list[int]] = []
    for row in rows:
        material.append([
            row["row_index"], row["head_index"], row["step_index"], row["candidate_index"], row["token_position"],
            row["candidate_position"], row["mask_allowed"], row["selected_flag"], row["selected_position"],
            row["selected_score"], row["score"], row["score_gap"], row["score_tied"],
            row["tie_break_gap"], row["causal_gap"], *row["query"], *row["key"], *row["value"],
            *row["products"], *row["attention_output"],
        ])
    return material


def score_row_material_width() -> int:
    return 15 + 3 * KEY_WIDTH + 2 * VALUE_WIDTH


def rows_commitment(rows: list[dict[str, Any]]) -> str:
    return commitment_from_parts(
        [("encoding", "attention_kv_stwo_native_score_rows_with_head_v1"), ("shape", [len(rows), score_row_material_width()]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(score_rows_material(rows))))],
        ROW_DOMAIN,
    )


def kv_commitment(cache: list[dict[str, Any]], domain: str) -> str:
    return commitment_from_parts(
        [("encoding", "attention_kv_cache_with_head_v1"), ("shape", [len(cache), 2 + KEY_WIDTH + VALUE_WIDTH]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(vector_material_kv(cache))))],
        domain,
    )


def input_steps_commitment(steps: list[dict[str, Any]]) -> str:
    return commitment_from_parts(
        [("encoding", "attention_input_steps_with_head_v1"), ("shape", [len(steps), 2 + 2 * KEY_WIDTH + VALUE_WIDTH]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(input_steps_material(steps))))],
        INPUT_STEPS_DOMAIN,
    )


def outputs_material(steps: list[dict[str, Any]], outputs: list[list[int]]) -> list[list[int]]:
    return [[step["head_index"], *output] for step, output in zip(steps, outputs, strict=True)]


def outputs_commitment(steps: list[dict[str, Any]], outputs: list[list[int]]) -> str:
    return commitment_from_parts(
        [("encoding", "attention_outputs_with_head_v1"), ("shape", [len(outputs), 1 + VALUE_WIDTH]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(outputs_material(steps, outputs))))],
        OUTPUTS_DOMAIN,
    )


def proof_native_parameter_commitment() -> str:
    return commitment_from_parts(
        [
            ("key_width", KEY_WIDTH),
            ("head_count", HEAD_COUNT),
            ("masking_policy", MASKING_POLICY),
            ("semantics", SEMANTICS),
            ("sequence_length", SEQUENCE_LENGTH),
            ("tie_break", TIE_BREAK),
            ("value_width", VALUE_WIDTH),
        ],
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def statement_commitment(payload: dict[str, Any]) -> str:
    return commitment_from_parts(
        [
            ("final_kv_cache_commitment", payload["final_kv_cache_commitment"]),
            ("initial_kv_cache_commitment", payload["initial_kv_cache_commitment"]),
            ("input_steps_commitment", payload["input_steps_commitment"]),
            ("key_width", payload["key_width"]),
            ("head_count", payload["head_count"]),
            ("masking_policy", payload["masking_policy"]),
            ("outputs_commitment", payload["outputs_commitment"]),
            ("proof_native_parameter_commitment", payload["proof_native_parameter_commitment"]),
            ("required_backend_version", payload["required_backend_version"]),
            ("score_row_commitment", payload["score_row_commitment"]),
            ("semantics", payload["semantics"]),
            ("sequence_length", payload["sequence_length"]),
            ("target_id", payload["target_id"]),
            ("tie_break", payload["tie_break"]),
            ("value_width", payload["value_width"]),
            ("verifier_domain", payload["verifier_domain"]),
        ],
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(payload: dict[str, Any]) -> str:
    return commitment_from_parts(
        [("statement_commitment", payload["statement_commitment"]), ("target_id", TARGET_ID), ("proof_version", PROOF_VERSION)],
        PUBLIC_INSTANCE_DOMAIN,
    )


def initial_kv_cache() -> list[dict[str, Any]]:
    cache = []
    for head_index in range(HEAD_COUNT):
        cache.extend([
            {
                "head_index": head_index,
                "position": 0,
                "key": [((head_index + 3) * (index + 1)) % 9 - 4 for index in range(KEY_WIDTH)],
                "value": [((head_index + 5) * (index + 2)) % 11 - 5 for index in range(VALUE_WIDTH)],
            },
            {
                "head_index": head_index,
                "position": 1,
                "key": [((head_index + 5) * (index + 2) + index) % 9 - 4 for index in range(KEY_WIDTH)],
                "value": [((head_index + 7) * (index + 1) - 2 * index) % 11 - 5 for index in range(VALUE_WIDTH)],
            },
        ])
    return cache


def input_step(head_index: int, step_index: int) -> dict[str, Any]:
    token_position = INITIAL_KV_ITEMS_PER_HEAD + step_index
    return {
        "head_index": head_index,
        "token_position": token_position,
        "query": [((head_index + 2) * (step_index + 2) * (index + 3) + step_index) % 9 - 4 for index in range(KEY_WIDTH)],
        "new_key": [((head_index + 3) * (step_index + 5) * (index + 1) + index) % 7 - 3 for index in range(KEY_WIDTH)],
        "new_value": [((head_index + 5) * (step_index + 7) * (index + 2) - index) % 11 - 5 for index in range(VALUE_WIDTH)],
    }


def fixture() -> dict[str, Any]:
    return {
        "initial_kv_cache": initial_kv_cache(),
        "input_steps": [
            input_step(head_index, step_index)
            for step_index in range(SEQUENCE_LENGTH)
            for head_index in range(HEAD_COUNT)
        ],
    }


def clone_cache_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "head_index": item["head_index"],
        "position": item["position"],
        "key": list(item["key"]),
        "value": list(item["value"]),
    }


def clone_input_step_item(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "head_index": step["head_index"],
        "token_position": step["token_position"],
        "query": list(step["query"]),
        "new_key": list(step["new_key"]),
        "new_value": list(step["new_value"]),
    }


def expected_journal() -> dict[str, Any]:
    data = fixture()
    initial_cache = [clone_cache_item(item) for item in data["initial_kv_cache"]]
    input_steps = [clone_input_step_item(step) for step in data["input_steps"]]
    current = [clone_cache_item(item) for item in initial_cache]
    transitions: list[dict[str, Any]] = []
    local_step_counts = [0] * HEAD_COUNT
    for global_step_index, step in enumerate(input_steps):
        head_index = step["head_index"]
        step_index = local_step_counts[head_index]
        local_step_counts[head_index] += 1
        next_item = {
            "head_index": head_index,
            "position": step["token_position"],
            "key": list(step["new_key"]),
            "value": list(step["new_value"]),
        }
        next_cache = [clone_cache_item(item) for item in current] + [clone_cache_item(next_item)]
        next_head_cache = [clone_cache_item(item) for item in next_cache if item["head_index"] == head_index]
        scores = []
        for candidate in next_head_cache:
            if candidate["position"] <= step["token_position"]:
                scores.append({"position": candidate["position"], "score": dot(step["query"], candidate["key"])})
        selected = max(scores, key=lambda item: (item["score"], -item["position"]))
        selected_position = selected["position"]
        attention_output = list(next(item["value"] for item in next_head_cache if item["position"] == selected_position))
        transitions.append({
            "global_step_index": global_step_index,
            "head_index": head_index,
            "step_index": step_index,
            "input_step": clone_input_step_item(step),
            "prior_kv_cache": [clone_cache_item(item) for item in current if item["head_index"] == head_index],
            "next_kv_cache": next_head_cache,
            "scores": scores,
            "selected_position": selected_position,
            "attention_output": attention_output,
        })
        current = next_cache
    return {
        "initial_kv_cache": initial_cache,
        "input_steps": input_steps,
        "transitions": transitions,
        "final_kv_cache": current,
    }


def build_score_rows(journal: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    row_index = 0
    for transition in journal["transitions"]:
        input_step = transition["input_step"]
        selected_score = max(score["score"] for score in transition["scores"])
        selected_position = transition["selected_position"]
        for candidate_index, candidate in enumerate(transition["next_kv_cache"]):
            if candidate["position"] > input_step["token_position"]:
                continue
            products = [left * right for left, right in zip(input_step["query"], candidate["key"], strict=True)]
            score = sum(products)
            score_gap = selected_score - score
            score_tied = int(score_gap == 0)
            rows.append({
                "row_index": row_index,
                "head_index": transition["head_index"],
                "step_index": transition["step_index"],
                "candidate_index": candidate_index,
                "token_position": input_step["token_position"],
                "candidate_position": candidate["position"],
                "mask_allowed": 1,
                "selected_flag": int(candidate["position"] == selected_position),
                "selected_position": selected_position,
                "selected_score": selected_score,
                "score": score,
                "score_gap": score_gap,
                "score_tied": score_tied,
                "tie_break_gap": candidate["position"] - selected_position if score_tied else 0,
                "causal_gap": input_step["token_position"] - candidate["position"],
                "query": list(input_step["query"]),
                "key": list(candidate["key"]),
                "value": list(candidate["value"]),
                "products": products,
                "attention_output": list(transition["attention_output"]),
            })
            row_index += 1
    return rows


def build_payload() -> dict[str, Any]:
    journal = expected_journal()
    rows = build_score_rows(journal)
    outputs = [list(row["attention_output"]) for row in journal["transitions"]]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": DECISION,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "proof_version": PROOF_VERSION,
        "statement_version": STATEMENT_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "verifier_domain": VERIFIER_DOMAIN,
        "semantics": SEMANTICS,
        "masking_policy": MASKING_POLICY,
        "tie_break": TIE_BREAK,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "head_count": HEAD_COUNT,
        "sequence_length": SEQUENCE_LENGTH,
        "initial_kv_items": INITIAL_KV_ITEMS,
        "final_kv_items": FINAL_KV_ITEMS,
        "score_row_count": SCORE_ROW_COUNT,
        "trace_row_count": TRACE_ROW_COUNT,
        "score_gap_bits": SCORE_GAP_BITS,
        "causal_gap_bits": CAUSAL_GAP_BITS,
        "tie_gap_bits": TIE_GAP_BITS,
        "selected_positions": [row["selected_position"] for row in journal["transitions"]],
        "initial_kv_cache": journal["initial_kv_cache"],
        "input_steps": journal["input_steps"],
        "final_kv_cache": journal["final_kv_cache"],
        "attention_outputs": outputs,
        "score_rows": rows,
        "initial_kv_cache_commitment": kv_commitment(journal["initial_kv_cache"], INITIAL_KV_DOMAIN),
        "input_steps_commitment": input_steps_commitment(journal["input_steps"]),
        "score_row_commitment": rows_commitment(rows),
        "final_kv_cache_commitment": kv_commitment(journal["final_kv_cache"], FINAL_KV_DOMAIN),
        "outputs_commitment": outputs_commitment(journal["input_steps"], outputs),
        "proof_native_parameter_commitment": proof_native_parameter_commitment(),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "non_claims": list(NON_CLAIMS),
        "proof_verifier_hardening": list(PROOF_VERIFIER_HARDENING),
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["statement_commitment"] = statement_commitment(payload)
    payload["public_instance_commitment"] = public_instance_commitment(payload)
    validate_payload(payload)
    return payload


def validate_vector(vector: Any, width: int, label: str) -> None:
    if not isinstance(vector, list) or len(vector) != width:
        raise AttentionKvStwoNativeD16TwoHeadInputError(f"{label} width mismatch")
    for index, value in enumerate(vector):
        require_int(value, f"{label}[{index}]")


def validate_score_row(row: Any, expected_index: int) -> None:
    if not isinstance(row, dict):
        raise AttentionKvStwoNativeD16TwoHeadInputError("score row must be an object")
    expected_fields = {
        "row_index", "head_index", "step_index", "candidate_index", "token_position", "candidate_position", "mask_allowed",
        "selected_flag", "selected_position", "selected_score", "score", "score_gap", "score_tied",
        "tie_break_gap", "causal_gap", "query", "key", "value", "products", "attention_output",
    }
    if set(row) != expected_fields:
        raise AttentionKvStwoNativeD16TwoHeadInputError("score row field set mismatch")
    if row["row_index"] != expected_index:
        raise AttentionKvStwoNativeD16TwoHeadInputError("score row index drift")
    for scalar in ("head_index", "step_index", "candidate_index", "token_position", "candidate_position", "mask_allowed", "selected_flag", "selected_position", "selected_score", "score", "score_gap", "score_tied", "tie_break_gap", "causal_gap"):
        require_int(row[scalar], scalar)
    if row["head_index"] not in range(HEAD_COUNT):
        raise AttentionKvStwoNativeD16TwoHeadInputError("head index drift")
    for vector_field, width in (("query", KEY_WIDTH), ("key", KEY_WIDTH), ("value", VALUE_WIDTH), ("products", KEY_WIDTH), ("attention_output", VALUE_WIDTH)):
        validate_vector(row[vector_field], width, vector_field)
    expected_products = [left * right for left, right in zip(row["query"], row["key"], strict=True)]
    if row["products"] != expected_products:
        raise AttentionKvStwoNativeD16TwoHeadInputError("score product row drift")
    if row["score"] != sum(expected_products):
        raise AttentionKvStwoNativeD16TwoHeadInputError("score sum drift")
    if row["score_gap"] != row["selected_score"] - row["score"] or row["score_gap"] < 0:
        raise AttentionKvStwoNativeD16TwoHeadInputError("selected-score dominance gap drift")
    if row["score_gap"] >= (1 << SCORE_GAP_BITS):
        raise AttentionKvStwoNativeD16TwoHeadInputError("score_gap overflow")
    if row["causal_gap"] != row["token_position"] - row["candidate_position"] or row["causal_gap"] < 0:
        raise AttentionKvStwoNativeD16TwoHeadInputError("causal-prefix mask gap drift")
    if row["causal_gap"] >= (1 << CAUSAL_GAP_BITS):
        raise AttentionKvStwoNativeD16TwoHeadInputError("causal_gap overflow")
    if row["score_tied"] != int(row["score_gap"] == 0):
        raise AttentionKvStwoNativeD16TwoHeadInputError("score-tie witness drift")
    if row["tie_break_gap"] != (row["candidate_position"] - row["selected_position"] if row["score_tied"] else 0):
        raise AttentionKvStwoNativeD16TwoHeadInputError("tie-break gap drift")
    if row["tie_break_gap"] < 0 or row["tie_break_gap"] >= (1 << TIE_GAP_BITS):
        raise AttentionKvStwoNativeD16TwoHeadInputError("tie-break gap outside range")
    if row["selected_flag"] not in (0, 1):
        raise AttentionKvStwoNativeD16TwoHeadInputError("selected flag must be boolean")
    if row["selected_flag"] == 1 and row["value"] != row["attention_output"]:
        raise AttentionKvStwoNativeD16TwoHeadInputError("selected value/output drift")


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvStwoNativeD16TwoHeadInputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "issue", "source_issue", "target_id", "required_backend_version", "proof_version",
        "statement_version", "semantic_scope", "verifier_domain", "semantics", "masking_policy", "tie_break",
        "key_width", "value_width", "head_count", "sequence_length", "initial_kv_items", "final_kv_items", "score_row_count",
        "trace_row_count", "score_gap_bits", "causal_gap_bits", "tie_gap_bits", "selected_positions",
        "initial_kv_cache", "input_steps", "final_kv_cache", "attention_outputs", "score_rows",
        "initial_kv_cache_commitment", "input_steps_commitment", "score_row_commitment", "final_kv_cache_commitment",
        "outputs_commitment", "proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment",
        "non_claims", "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise AttentionKvStwoNativeD16TwoHeadInputError("payload field set mismatch")
    constants = {
        "schema": SCHEMA,
        "decision": DECISION,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "proof_version": PROOF_VERSION,
        "statement_version": STATEMENT_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "verifier_domain": VERIFIER_DOMAIN,
        "semantics": SEMANTICS,
        "masking_policy": MASKING_POLICY,
        "tie_break": TIE_BREAK,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "head_count": HEAD_COUNT,
        "sequence_length": SEQUENCE_LENGTH,
        "initial_kv_items": INITIAL_KV_ITEMS,
        "final_kv_items": FINAL_KV_ITEMS,
        "score_row_count": SCORE_ROW_COUNT,
        "trace_row_count": TRACE_ROW_COUNT,
        "score_gap_bits": SCORE_GAP_BITS,
        "causal_gap_bits": CAUSAL_GAP_BITS,
        "tie_gap_bits": TIE_GAP_BITS,
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    for field, expected in constants.items():
        if payload.get(field) != expected:
            raise AttentionKvStwoNativeD16TwoHeadInputError(f"payload field mismatch: {field}")
    journal = expected_journal()
    rows = build_score_rows(journal)
    outputs = [row["attention_output"] for row in journal["transitions"]]
    if payload["initial_kv_cache"] != journal["initial_kv_cache"]:
        raise AttentionKvStwoNativeD16TwoHeadInputError("initial KV cache drift")
    if payload["input_steps"] != journal["input_steps"]:
        raise AttentionKvStwoNativeD16TwoHeadInputError("input steps drift")
    if payload["final_kv_cache"] != journal["final_kv_cache"]:
        raise AttentionKvStwoNativeD16TwoHeadInputError("final KV cache drift")
    if payload["attention_outputs"] != outputs:
        raise AttentionKvStwoNativeD16TwoHeadInputError("attention outputs drift")
    if payload["score_rows"] != rows:
        raise AttentionKvStwoNativeD16TwoHeadInputError("score rows drift")
    if payload["selected_positions"] != [row["selected_position"] for row in journal["transitions"]]:
        raise AttentionKvStwoNativeD16TwoHeadInputError("selected positions drift")
    if len(payload["score_rows"]) != SCORE_ROW_COUNT:
        raise AttentionKvStwoNativeD16TwoHeadInputError("score row count drift")
    for index, row in enumerate(payload["score_rows"]):
        validate_score_row(row, index)
    if payload["initial_kv_cache_commitment"] != kv_commitment(payload["initial_kv_cache"], INITIAL_KV_DOMAIN):
        raise AttentionKvStwoNativeD16TwoHeadInputError("initial KV commitment drift")
    if payload["input_steps_commitment"] != input_steps_commitment(payload["input_steps"]):
        raise AttentionKvStwoNativeD16TwoHeadInputError("input steps commitment drift")
    if payload["score_row_commitment"] != rows_commitment(payload["score_rows"]):
        raise AttentionKvStwoNativeD16TwoHeadInputError("score row commitment drift")
    if payload["final_kv_cache_commitment"] != kv_commitment(payload["final_kv_cache"], FINAL_KV_DOMAIN):
        raise AttentionKvStwoNativeD16TwoHeadInputError("final KV commitment drift")
    if payload["outputs_commitment"] != outputs_commitment(payload["input_steps"], payload["attention_outputs"]):
        raise AttentionKvStwoNativeD16TwoHeadInputError("outputs commitment drift")
    if payload["proof_native_parameter_commitment"] != proof_native_parameter_commitment():
        raise AttentionKvStwoNativeD16TwoHeadInputError("proof-native parameter commitment drift")
    if payload["statement_commitment"] != statement_commitment(payload):
        raise AttentionKvStwoNativeD16TwoHeadInputError("statement commitment drift")
    if payload["public_instance_commitment"] != public_instance_commitment(payload):
        raise AttentionKvStwoNativeD16TwoHeadInputError("public instance commitment drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_payload(payload)
    return [{
        "issue": payload["issue"],
        "decision": payload["decision"],
        "proof_version": payload["proof_version"],
        "key_width": payload["key_width"],
        "value_width": payload["value_width"],
        "head_count": payload["head_count"],
        "sequence_length": payload["sequence_length"],
        "score_row_count": payload["score_row_count"],
        "trace_row_count": payload["trace_row_count"],
        "selected_positions": json.dumps(payload["selected_positions"], separators=(",", ":")),
        "score_row_commitment": payload["score_row_commitment"],
        "final_kv_cache_commitment": payload["final_kv_cache_commitment"],
        "outputs_commitment": payload["outputs_commitment"],
        "statement_commitment": payload["statement_commitment"],
        "non_claims": json.dumps(payload["non_claims"], separators=(",", ":"), sort_keys=True),
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
