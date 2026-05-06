#!/usr/bin/env python3
"""Build the native Stwo d=8 two-head bounded weighted attention/KV proof input.

This answers issue #461 narrowly. It combines the issue #460 bounded weighted
attention/KV policy with the issue #455 two-head carried-state fixture:

    weight = 2 ** (4 - min(max_score - score, 4))

The resulting output is the integer floor of the weighted value average. This is
Softmax-like in shape because all allowed candidates contribute with a monotone
score-derived weight, but it is not exact Softmax and does not claim exp/div
semantics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
from collections.abc import Sequence
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.tsv"

SOURCE_SCHEMA = "zkai-attention-kv-stwo-native-masked-sequence-air-proof-input-v1"
SOURCE_DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
SOURCE_TARGET_ID = "attention-kv-d8-causal-mask-two-head-v1"
SOURCE_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-v1"
SOURCE_PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-air-proof-v1"
SOURCE_STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-two-head-statement-v1"
SOURCE_PAYLOAD_SHA256 = "0ab175f3b9df547c6f200bc47fecb43d7850c06e6a74ac3febf91d835466ceaf"

SCHEMA = "zkai-attention-kv-stwo-native-two-head-bounded-weighted-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_TWO_HEAD_BOUNDED_WEIGHTED_AIR_PROOF"
ISSUE = 461
SOURCE_ISSUE = 460
TARGET_ID = "attention-kv-d8-causal-mask-two-head-bounded-weighted-v1"
REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-bounded-weighted-v1"
PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-two-head-bounded-weighted-air-proof-v1"
STATEMENT_VERSION = "zkai-attention-kv-stwo-native-two-head-bounded-weighted-statement-v1"
SEMANTIC_SCOPE = "two_head_d8_bounded_power2_weighted_attention_kv_causal_mask_rows_bound_to_statement_receipt"
VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted:v1"
SEMANTICS = "bounded_power2_weighted_attention"
WEIGHT_POLICY = "power2_gap_clipped_4_floor_division"
MASKING_POLICY = "causal_prefix_position_lte_query_token"
KEY_WIDTH = 8
VALUE_WIDTH = 8
HEAD_COUNT = 2
SEQUENCE_LENGTH = 8
INITIAL_KV_ITEMS_PER_HEAD = 2
INITIAL_KV_ITEMS = HEAD_COUNT * INITIAL_KV_ITEMS_PER_HEAD
FINAL_KV_ITEMS_PER_HEAD = INITIAL_KV_ITEMS_PER_HEAD + SEQUENCE_LENGTH
FINAL_KV_ITEMS = HEAD_COUNT * FINAL_KV_ITEMS_PER_HEAD
TRACE_ROW_COUNT = 128
SCORE_ROW_COUNT = HEAD_COUNT * sum(INITIAL_KV_ITEMS_PER_HEAD + step + 1 for step in range(SEQUENCE_LENGTH))
SCORE_GAP_BITS = 16
CAUSAL_GAP_BITS = 16
WEIGHT_BITS = 5
OUTPUT_REMAINDER_BITS = 8
MAX_ABS_VALUE = 1_000_000

ROW_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-score-rows:v1"
INITIAL_KV_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-initial-kv:v1"
INPUT_STEPS_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-input-steps:v1"
FINAL_KV_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-final-kv:v1"
OUTPUTS_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-outputs:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-public-instance:v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-two-head-bounded-weighted-proof-parameters:v1"

NON_CLAIMS = [
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full transformer inference",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not long-context benchmark evidence",
    "not on-chain verification evidence",
    "bounded score-to-weight policy, per-head KV carry, and weighted averages are verifier-recomputed from public rows before proof verification",
]

PROOF_VERIFIER_HARDENING = [
    "native Stwo AIR proves query-key dot-product rows for every checked candidate",
    "native Stwo AIR proves selected-score dominance gaps are nonnegative via bit decomposition",
    "native Stwo AIR proves causal-prefix mask gaps are nonnegative via bit decomposition",
    "native Stwo AIR proves weight times value products for every checked candidate and dimension",
    "native Stwo AIR proves output quotient/remainder rows against the verifier-recomputed weighted numerator and denominator",
    "verifier recomputes per-head append-only KV carry, max score, bounded weights, weighted numerators, denominators, and outputs before proof verification",
    "score-row, initial-KV, input-step, final-KV, output, public-instance, and statement commitments are recomputed before proof verification",
    "fixed publication-v1 PCS verifier profile before commitment-root recomputation",
    "bounded envelope JSON before deserialization and bounded proof bytes before proof parsing",
    "commitment-vector length check before commitment indexing",
]

NEXT_BACKEND_STEP = "combine bounded weighted attention with two-head state binding only after preserving weighted-product, quotient/remainder, carry, mask, and relabeling rejection surfaces"

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_two_head_bounded_weighted_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_two_head_bounded_weighted_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_bounded_weighted_native_gate",
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
    "weight_policy",
    "attention_outputs",
    "score_row_commitment",
    "final_kv_cache_commitment",
    "outputs_commitment",
    "statement_commitment",
    "non_claims",
)


class AttentionKvTwoHeadBoundedWeightedInputError(ValueError):
    pass


def _load_source_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"failed to load source script: {SOURCE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE = _load_source_module()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def commitment_from_parts(parts: list[tuple[str, Any]], domain: str) -> str:
    encoded = b"".join(
        str(label).encode("utf-8") + b"=" + canonical_json_bytes(value) + b"\n" for label, value in parts
    )
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(encoded)
    return f"blake2b-256:{digest.hexdigest()}"


def require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} must be an integer")
    if abs(value) > MAX_ABS_VALUE:
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} outside bounded fixture range")
    return value


def require_nonnegative_bit_bound(value: int, *, bits: int, label: str) -> int:
    checked = require_int(value, label)
    if checked < 0 or checked >= (1 << bits):
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} outside {bits}-bit range")
    return checked


def next_power_of_two(value: int) -> int:
    if value <= 0:
        raise AttentionKvTwoHeadBoundedWeightedInputError("trace row count input must be positive")
    return 1 << (value - 1).bit_length()


def require_vector(value: Any, *, width: int, label: str) -> list[int]:
    if not isinstance(value, list):
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} must be a list")
    if len(value) != width:
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} width drift")
    return [require_int(item, f"{label}[{index}]") for index, item in enumerate(value)]


def require_head_index(value: Any, label: str) -> int:
    head_index = require_int(value, label)
    if head_index < 0 or head_index >= HEAD_COUNT:
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} outside head range")
    return head_index


def require_kv_item(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} must be an object")
    return {
        "head_index": require_head_index(value.get("head_index"), f"{label}.head_index"),
        "position": require_int(value.get("position"), f"{label}.position"),
        "key": require_vector(value.get("key"), width=KEY_WIDTH, label=f"{label}.key"),
        "value": require_vector(value.get("value"), width=VALUE_WIDTH, label=f"{label}.value"),
    }


def require_input_step(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} must be an object")
    return {
        "head_index": require_head_index(value.get("head_index"), f"{label}.head_index"),
        "token_position": require_int(value.get("token_position"), f"{label}.token_position"),
        "query": require_vector(value.get("query"), width=KEY_WIDTH, label=f"{label}.query"),
        "new_key": require_vector(value.get("new_key"), width=KEY_WIDTH, label=f"{label}.new_key"),
        "new_value": require_vector(value.get("new_value"), width=VALUE_WIDTH, label=f"{label}.new_value"),
    }


def require_sequence(value: Any, *, label: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise AttentionKvTwoHeadBoundedWeightedInputError(f"{label} must be a list")
    return value


def source_payload() -> dict[str, Any]:
    payload = SOURCE.build_payload()
    if not isinstance(payload, dict):
        raise AttentionKvTwoHeadBoundedWeightedInputError("source payload must be an object")
    expected_scalars = {
        "schema": SOURCE_SCHEMA,
        "decision": SOURCE_DECISION,
        "target_id": SOURCE_TARGET_ID,
        "required_backend_version": SOURCE_BACKEND_VERSION,
        "proof_version": SOURCE_PROOF_VERSION,
        "statement_version": SOURCE_STATEMENT_VERSION,
        "key_width": KEY_WIDTH,
        "value_width": VALUE_WIDTH,
        "sequence_length": SEQUENCE_LENGTH,
        "head_count": HEAD_COUNT,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"source payload {key} drift")
    observed = sha256_hex_bytes(canonical_json_bytes(payload))
    if observed != SOURCE_PAYLOAD_SHA256:
        raise AttentionKvTwoHeadBoundedWeightedInputError("source payload commitment drift")
    return payload


def dot(lhs: list[int], rhs: list[int]) -> int:
    if len(lhs) != KEY_WIDTH or len(rhs) != KEY_WIDTH:
        raise AttentionKvTwoHeadBoundedWeightedInputError("dot-product width mismatch")
    return sum(require_int(left, "query") * require_int(right, "key") for left, right in zip(lhs, rhs, strict=True))


def weight_from_gap(score_gap: int) -> int:
    if score_gap < 0:
        raise AttentionKvTwoHeadBoundedWeightedInputError("negative score gap")
    clipped = min(score_gap, 4)
    return 1 << (4 - clipped)


def vector_material_kv(cache: list[dict[str, Any]]) -> list[list[int]]:
    return [[item["head_index"], item["position"], *item["key"], *item["value"]] for item in cache]


def input_steps_material(steps: list[dict[str, Any]]) -> list[list[int]]:
    return [[step["head_index"], step["token_position"], *step["query"], *step["new_key"], *step["new_value"]] for step in steps]


def score_rows_material(rows: list[dict[str, Any]]) -> list[list[int]]:
    material: list[list[int]] = []
    for row in rows:
        material.append([
            row["row_index"], row["head_index"], row["step_index"], row["candidate_index"], row["token_position"],
            row["candidate_position"], row["mask_allowed"], row["selected_score"], row["score"],
            row["score_gap"], row["causal_gap"], row["attention_weight"], row["weight_denominator"],
            *row["query"], *row["key"], *row["value"], *row["products"], *row["weighted_value"],
            *row["weighted_numerator"], *row["attention_output"], *row["output_remainder"],
        ])
    return material


def score_row_material_width() -> int:
    return 13 + 3 * KEY_WIDTH + 5 * VALUE_WIDTH


def rows_commitment(rows: list[dict[str, Any]]) -> str:
    return commitment_from_parts(
        [
            ("encoding", "attention_kv_stwo_native_two_head_bounded_weighted_score_rows_v1"),
            ("shape", [len(rows), score_row_material_width()]),
            ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(score_rows_material(rows)))),
        ],
        ROW_DOMAIN,
    )


def kv_commitment(cache: list[dict[str, Any]], domain: str) -> str:
    return commitment_from_parts(
        [
            ("encoding", "attention_kv_cache_with_head_v1"),
            ("shape", [len(cache), 2 + KEY_WIDTH + VALUE_WIDTH]),
            ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(vector_material_kv(cache)))),
        ],
        domain,
    )


def input_steps_commitment(steps: list[dict[str, Any]]) -> str:
    return commitment_from_parts(
        [
            ("encoding", "attention_input_steps_with_head_v1"),
            ("shape", [len(steps), 2 + 2 * KEY_WIDTH + VALUE_WIDTH]),
            ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(input_steps_material(steps)))),
        ],
        INPUT_STEPS_DOMAIN,
    )


def outputs_commitment(steps: list[dict[str, Any]], outputs: list[list[int]]) -> str:
    return commitment_from_parts(
        [
            ("encoding", "bounded_weighted_attention_outputs_with_head_v1"),
            ("shape", [len(outputs), 1 + VALUE_WIDTH]),
            ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(outputs_material(steps, outputs)))),
        ],
        OUTPUTS_DOMAIN,
    )


def proof_native_parameter_commitment() -> str:
    return commitment_from_parts(
        [
            ("head_count", HEAD_COUNT),
            ("key_width", KEY_WIDTH),
            ("masking_policy", MASKING_POLICY),
            ("semantics", SEMANTICS),
            ("sequence_length", SEQUENCE_LENGTH),
            ("value_width", VALUE_WIDTH),
            ("weight_policy", WEIGHT_POLICY),
        ],
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def outputs_material(steps: list[dict[str, Any]], outputs: list[list[int]]) -> list[list[int]]:
    if len(steps) != len(outputs):
        raise AttentionKvTwoHeadBoundedWeightedInputError("output/input step length mismatch")
    return [[step["head_index"], *output] for step, output in zip(steps, outputs, strict=True)]


def statement_commitment(payload: dict[str, Any]) -> str:
    return commitment_from_parts(
        [
            ("final_kv_cache_commitment", payload["final_kv_cache_commitment"]),
            ("head_count", payload["head_count"]),
            ("initial_kv_cache_commitment", payload["initial_kv_cache_commitment"]),
            ("input_steps_commitment", payload["input_steps_commitment"]),
            ("key_width", payload["key_width"]),
            ("masking_policy", payload["masking_policy"]),
            ("outputs_commitment", payload["outputs_commitment"]),
            ("proof_native_parameter_commitment", payload["proof_native_parameter_commitment"]),
            ("required_backend_version", payload["required_backend_version"]),
            ("score_row_commitment", payload["score_row_commitment"]),
            ("semantics", payload["semantics"]),
            ("sequence_length", payload["sequence_length"]),
            ("target_id", payload["target_id"]),
            ("value_width", payload["value_width"]),
            ("verifier_domain", payload["verifier_domain"]),
            ("weight_policy", payload["weight_policy"]),
        ],
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return commitment_from_parts(
        [("statement_commitment", statement), ("target_id", TARGET_ID), ("proof_version", PROOF_VERSION)],
        PUBLIC_INSTANCE_DOMAIN,
    )


def fixture_initial_kv() -> list[dict[str, Any]]:
    initial = source_payload().get("initial_kv_cache")
    items = [
        require_kv_item(item, label=f"initial_kv[{index}]")
        for index, item in enumerate(require_sequence(initial, label="initial_kv_cache"))
    ]
    if len(items) != INITIAL_KV_ITEMS:
        raise AttentionKvTwoHeadBoundedWeightedInputError("source initial KV length drift")
    return items


def fixture_input_steps() -> list[dict[str, Any]]:
    steps = source_payload().get("input_steps")
    items = [
        require_input_step(item, label=f"input_steps[{index}]")
        for index, item in enumerate(require_sequence(steps, label="input_steps"))
    ]
    if len(items) != HEAD_COUNT * SEQUENCE_LENGTH:
        raise AttentionKvTwoHeadBoundedWeightedInputError("source input step length drift")
    return items


def clone_kv_item(item: dict[str, Any]) -> dict[str, Any]:
    checked = require_kv_item(item, label="kv_item")
    return {
        "head_index": checked["head_index"],
        "position": checked["position"],
        "key": list(checked["key"]),
        "value": list(checked["value"]),
    }


def build_score_rows(initial_kv: list[dict[str, Any]], input_steps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[list[int]]]:
    current = [
        require_kv_item(item, label=f"initial_kv[{index}]")
        for index, item in enumerate(require_sequence(initial_kv, label="initial_kv"))
    ]
    steps = [
        require_input_step(step, label=f"input_steps[{index}]")
        for index, step in enumerate(require_sequence(input_steps, label="input_steps"))
    ]
    rows: list[dict[str, Any]] = []
    outputs: list[list[int]] = []
    local_step_counts = [0 for _ in range(HEAD_COUNT)]
    for global_step_index, step in enumerate(steps):
        head_index = step["head_index"]
        step_index = local_step_counts[head_index]
        local_step_counts[head_index] += 1
        if step_index >= SEQUENCE_LENGTH:
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"input_steps[{global_step_index}] exceeds per-head sequence length")
        next_item = {
            "head_index": head_index,
            "position": step["token_position"],
            "key": list(step["new_key"]),
            "value": list(step["new_value"]),
        }
        candidates = [clone_kv_item(item) for item in current] + [clone_kv_item(next_item)]
        head_candidates = [candidate for candidate in candidates if candidate["head_index"] == head_index]
        allowed = [
            require_kv_item(candidate, label=f"step[{global_step_index}].candidate[{candidate_index}]")
            for candidate_index, candidate in enumerate(head_candidates)
            if candidate["position"] <= step["token_position"]
        ]
        if not allowed:
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"input_steps[{global_step_index}] has no allowed candidates")
        scored = [(candidate, dot(step["query"], candidate["key"])) for candidate in allowed]
        selected_score = max(score for _, score in scored)
        score_gaps = [
            require_nonnegative_bit_bound(
                selected_score - score,
                bits=SCORE_GAP_BITS,
                label=f"input_steps[{global_step_index}].score_gap[{candidate_index}]",
            )
            for candidate_index, (_, score) in enumerate(scored)
        ]
        causal_gaps = [
            require_nonnegative_bit_bound(
                step["token_position"] - candidate["position"],
                bits=CAUSAL_GAP_BITS,
                label=f"input_steps[{global_step_index}].causal_gap[{candidate_index}]",
            )
            for candidate_index, (candidate, _) in enumerate(scored)
        ]
        weights = [
            require_nonnegative_bit_bound(
                weight_from_gap(score_gap),
                bits=WEIGHT_BITS,
                label=f"input_steps[{global_step_index}].attention_weight[{candidate_index}]",
            )
            for candidate_index, score_gap in enumerate(score_gaps)
        ]
        if any(weight <= 0 for weight in weights):
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"input_steps[{global_step_index}] has zero weight")
        denominator = sum(weights)
        if denominator <= 0:
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"input_steps[{global_step_index}] has invalid weight denominator")
        numerators = [0 for _ in range(VALUE_WIDTH)]
        for (candidate, _), weight in zip(scored, weights, strict=True):
            for dim, value in enumerate(candidate["value"]):
                numerators[dim] += weight * value
        output = [
            require_int(numerator // denominator, f"input_steps[{global_step_index}].attention_output[{dim}]")
            for dim, numerator in enumerate(numerators)
        ]
        remainders = [numerator - out * denominator for numerator, out in zip(numerators, output, strict=True)]
        for dim, remainder in enumerate(remainders):
            require_nonnegative_bit_bound(
                remainder,
                bits=OUTPUT_REMAINDER_BITS,
                label=f"input_steps[{global_step_index}].output_remainder[{dim}]",
            )
            if remainder >= denominator:
                raise AttentionKvTwoHeadBoundedWeightedInputError(
                    f"input_steps[{global_step_index}].output_remainder[{dim}] outside denominator range"
                )
        outputs.append(list(output))
        for candidate_index, ((candidate, score), weight, score_gap, causal_gap) in enumerate(
            zip(scored, weights, score_gaps, causal_gaps, strict=True)
        ):
            products = [left * right for left, right in zip(step["query"], candidate["key"], strict=True)]
            weighted_value = [weight * value for value in candidate["value"]]
            rows.append({
                "row_index": len(rows),
                "head_index": head_index,
                "step_index": step_index,
                "candidate_index": candidate_index,
                "token_position": step["token_position"],
                "candidate_position": candidate["position"],
                "mask_allowed": 1,
                "selected_score": selected_score,
                "score": score,
                "score_gap": score_gap,
                "causal_gap": causal_gap,
                "attention_weight": weight,
                "weight_denominator": denominator,
                "query": list(step["query"]),
                "key": list(candidate["key"]),
                "value": list(candidate["value"]),
                "products": list(products),
                "weighted_value": list(weighted_value),
                "weighted_numerator": list(numerators),
                "attention_output": list(output),
                "output_remainder": list(remainders),
            })
        current = candidates
    if local_step_counts != [SEQUENCE_LENGTH for _ in range(HEAD_COUNT)]:
        raise AttentionKvTwoHeadBoundedWeightedInputError("per-head input step count drift")
    return rows, current, outputs


def validate_payload(payload: dict[str, Any]) -> None:
    expected_scalars = {
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
        "weight_policy": WEIGHT_POLICY,
        "masking_policy": MASKING_POLICY,
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
        "weight_bits": WEIGHT_BITS,
        "output_remainder_bits": OUTPUT_REMAINDER_BITS,
        "next_backend_step": NEXT_BACKEND_STEP,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"{key} drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionKvTwoHeadBoundedWeightedInputError("non claims drift")
    if payload.get("proof_verifier_hardening") != PROOF_VERIFIER_HARDENING:
        raise AttentionKvTwoHeadBoundedWeightedInputError("proof verifier hardening drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionKvTwoHeadBoundedWeightedInputError("validation commands drift")
    initial = fixture_initial_kv()
    steps = fixture_input_steps()
    rows, final_cache, outputs = build_score_rows(initial, steps)
    if len(initial) != payload.get("initial_kv_items"):
        raise AttentionKvTwoHeadBoundedWeightedInputError("derived initial KV count drift")
    if len(final_cache) != payload.get("final_kv_items"):
        raise AttentionKvTwoHeadBoundedWeightedInputError("derived final KV count drift")
    if len(rows) != payload.get("score_row_count"):
        raise AttentionKvTwoHeadBoundedWeightedInputError("derived score row count drift")
    if next_power_of_two(len(rows)) != payload.get("trace_row_count"):
        raise AttentionKvTwoHeadBoundedWeightedInputError("derived trace row count drift")
    if payload.get("initial_kv_cache") != initial:
        raise AttentionKvTwoHeadBoundedWeightedInputError("initial KV drift")
    if payload.get("input_steps") != steps:
        raise AttentionKvTwoHeadBoundedWeightedInputError("input steps drift")
    if payload.get("score_rows") != rows:
        raise AttentionKvTwoHeadBoundedWeightedInputError("score rows drift")
    if payload.get("final_kv_cache") != final_cache:
        raise AttentionKvTwoHeadBoundedWeightedInputError("final KV drift")
    if payload.get("attention_outputs") != outputs:
        raise AttentionKvTwoHeadBoundedWeightedInputError("attention outputs drift")
    expected_commitments = {
        "initial_kv_cache_commitment": kv_commitment(initial, INITIAL_KV_DOMAIN),
        "input_steps_commitment": input_steps_commitment(steps),
        "score_row_commitment": rows_commitment(rows),
        "final_kv_cache_commitment": kv_commitment(final_cache, FINAL_KV_DOMAIN),
        "outputs_commitment": outputs_commitment(steps, outputs),
        "proof_native_parameter_commitment": proof_native_parameter_commitment(),
    }
    for key, expected in expected_commitments.items():
        if payload.get(key) != expected:
            raise AttentionKvTwoHeadBoundedWeightedInputError(f"{key} drift")
    statement = statement_commitment(payload)
    if payload.get("statement_commitment") != statement:
        raise AttentionKvTwoHeadBoundedWeightedInputError("statement commitment drift")
    if payload.get("public_instance_commitment") != public_instance_commitment(statement):
        raise AttentionKvTwoHeadBoundedWeightedInputError("public instance commitment drift")


def build_payload() -> dict[str, Any]:
    initial = fixture_initial_kv()
    steps = fixture_input_steps()
    rows, final_cache, outputs = build_score_rows(initial, steps)
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
        "weight_policy": WEIGHT_POLICY,
        "masking_policy": MASKING_POLICY,
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
        "weight_bits": WEIGHT_BITS,
        "output_remainder_bits": OUTPUT_REMAINDER_BITS,
        "initial_kv_cache": initial,
        "input_steps": steps,
        "final_kv_cache": final_cache,
        "attention_outputs": outputs,
        "score_rows": rows,
        "initial_kv_cache_commitment": kv_commitment(initial, INITIAL_KV_DOMAIN),
        "input_steps_commitment": input_steps_commitment(steps),
        "score_row_commitment": rows_commitment(rows),
        "final_kv_cache_commitment": kv_commitment(final_cache, FINAL_KV_DOMAIN),
        "outputs_commitment": outputs_commitment(steps, outputs),
        "proof_native_parameter_commitment": proof_native_parameter_commitment(),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "non_claims": NON_CLAIMS,
        "proof_verifier_hardening": PROOF_VERIFIER_HARDENING,
        "next_backend_step": NEXT_BACKEND_STEP,
        "validation_commands": VALIDATION_COMMANDS,
    }
    payload["statement_commitment"] = statement_commitment(payload)
    payload["public_instance_commitment"] = public_instance_commitment(payload["statement_commitment"])
    validate_payload(payload)
    return payload


def write_json(payload: dict[str, Any], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_tsv(payload: dict[str, Any]) -> str:
    row = {
        "issue": payload["issue"],
        "decision": payload["decision"],
        "proof_version": payload["proof_version"],
        "key_width": payload["key_width"],
        "value_width": payload["value_width"],
        "head_count": payload["head_count"],
        "sequence_length": payload["sequence_length"],
        "score_row_count": payload["score_row_count"],
        "trace_row_count": payload["trace_row_count"],
        "weight_policy": payload["weight_policy"],
        "attention_outputs": json.dumps(payload["attention_outputs"], separators=(",", ":")),
        "score_row_commitment": payload["score_row_commitment"],
        "final_kv_cache_commitment": payload["final_kv_cache_commitment"],
        "outputs_commitment": payload["outputs_commitment"],
        "statement_commitment": payload["statement_commitment"],
        "non_claims": ";".join(payload["non_claims"]),
    }
    out_lines: list[str] = []
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    out_lines.append(buf.getvalue())
    return "".join(out_lines)


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
