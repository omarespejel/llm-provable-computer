#!/usr/bin/env python3
"""Build the native Stwo attention/KV seq16 masked-sequence proof input.

This extends the checked native Stwo d=8 eight-step surface along one axis:
sequence length.  The fixture keeps the same single-head integer-argmax,
causal-prefix mask, d=8 key/value width, and public-row binding discipline, but
runs sixteen carried KV-cache transitions instead of eight.

It is intentionally scoped: not Softmax, not multi-head, not full inference, and
not recursive/PCD.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
BASE_SCRIPT = ROOT / "scripts" / "zkai_attention_kv_stwo_native_masked_sequence_proof_input.py"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.tsv"

SCHEMA = "zkai-attention-kv-stwo-native-masked-sequence-air-proof-input-v1"
DECISION = "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF"
ISSUE = 450
SOURCE_ISSUE = 448
TARGET_ID = "attention-kv-d8-causal-mask-seq16-v1"
REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-seq16-v1"
PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-seq16-air-proof-v1"
STATEMENT_VERSION = "zkai-attention-kv-stwo-native-masked-sequence-seq16-statement-v1"
SEMANTIC_SCOPE = "d8_integer_argmax_attention_kv_causal_mask_seq16_rows_bound_to_statement_receipt"
VERIFIER_DOMAIN = "ptvm:zkai:attention-kv-stwo-native-masked-sequence-seq16:v1"
SEMANTICS = "integer_argmax_attention"
MASKING_POLICY = "causal_prefix_position_lte_query_token"
TIE_BREAK = "lowest_position"
KEY_WIDTH = 8
VALUE_WIDTH = 8
SEQUENCE_LENGTH = 16
INITIAL_KV_ITEMS = 2
FINAL_KV_ITEMS = 18
TRACE_ROW_COUNT = 256
SCORE_ROW_COUNT = sum(INITIAL_KV_ITEMS + step + 1 for step in range(SEQUENCE_LENGTH))
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

NEXT_BACKEND_STEP = "scale the native Stwo attention/KV proof surface to multi-head or bounded Softmax-like approximation only after preserving the same carry, mask, selected-output, and sequence-length rejection surface"

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_seq16_native_scale_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_seq16_native_scale_gate",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "issue",
    "decision",
    "proof_version",
    "key_width",
    "value_width",
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


class AttentionKvStwoNativeSeq16InputError(ValueError):
    pass


def _load_base_module() -> Any:
    spec = importlib.util.spec_from_file_location("zkai_attention_kv_stwo_native_masked_sequence_proof_input", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AttentionKvStwoNativeSeq16InputError(f"failed to load base script: {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base_module()


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
        raise AttentionKvStwoNativeSeq16InputError(f"{label} must be an integer")
    if not -MAX_ABS_VALUE <= value <= MAX_ABS_VALUE:
        raise AttentionKvStwoNativeSeq16InputError(f"{label} outside bounded fixture range")
    return value


def dot(lhs: list[int], rhs: list[int]) -> int:
    if len(lhs) != KEY_WIDTH or len(rhs) != KEY_WIDTH:
        raise AttentionKvStwoNativeSeq16InputError("dot-product width mismatch")
    return sum(require_int(left, "query") * require_int(right, "key") for left, right in zip(lhs, rhs, strict=True))


def vector_material_kv(cache: list[dict[str, Any]]) -> list[list[int]]:
    return [[item["position"], *item["key"], *item["value"]] for item in cache]


def input_steps_material(steps: list[dict[str, Any]]) -> list[list[int]]:
    return [[step["token_position"], *step["query"], *step["new_key"], *step["new_value"]] for step in steps]


def score_rows_material(rows: list[dict[str, Any]]) -> list[list[int]]:
    material: list[list[int]] = []
    for row in rows:
        material.append([
            row["row_index"], row["step_index"], row["candidate_index"], row["token_position"],
            row["candidate_position"], row["mask_allowed"], row["selected_flag"], row["selected_position"],
            row["selected_score"], row["score"], row["score_gap"], row["score_tied"],
            row["tie_break_gap"], row["causal_gap"], *row["query"], *row["key"], *row["value"],
            *row["products"], *row["attention_output"],
        ])
    return material


def rows_commitment(rows: list[dict[str, Any]]) -> str:
    return commitment_from_parts(
        [("encoding", "attention_kv_stwo_native_score_rows_v1"), ("shape", [len(rows), 54]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(score_rows_material(rows))))],
        ROW_DOMAIN,
    )


def kv_commitment(cache: list[dict[str, Any]], domain: str) -> str:
    return commitment_from_parts(
        [("encoding", "attention_kv_cache_v1"), ("shape", [len(cache), 1 + KEY_WIDTH + VALUE_WIDTH]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(vector_material_kv(cache))))],
        domain,
    )


def input_steps_commitment(steps: list[dict[str, Any]]) -> str:
    return commitment_from_parts(
        [("encoding", "attention_input_steps_v1"), ("shape", [len(steps), 1 + 2 * KEY_WIDTH + VALUE_WIDTH]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(input_steps_material(steps))))],
        INPUT_STEPS_DOMAIN,
    )


def outputs_commitment(outputs: list[list[int]]) -> str:
    return commitment_from_parts(
        [("encoding", "attention_outputs_v1"), ("shape", [len(outputs), VALUE_WIDTH]), ("rows_sha256", sha256_hex_bytes(canonical_json_bytes(outputs)))],
        OUTPUTS_DOMAIN,
    )


def proof_native_parameter_commitment() -> str:
    return commitment_from_parts(
        [
            ("key_width", KEY_WIDTH),
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


def extra_step(step_index: int) -> dict[str, Any]:
    token_position = INITIAL_KV_ITEMS + step_index
    return {
        "token_position": token_position,
        "query": [((step_index + 2) * (index + 3)) % 9 - 4 for index in range(KEY_WIDTH)],
        "new_key": [((step_index + 5) * (index + 1) + index) % 7 - 3 for index in range(KEY_WIDTH)],
        "new_value": [((step_index + 7) * (index + 2) - index) % 11 - 5 for index in range(VALUE_WIDTH)],
    }


def seq16_fixture() -> dict[str, Any]:
    base = BASE.build_payload()
    input_steps = list(base["input_steps"])
    for step_index in range(len(input_steps), SEQUENCE_LENGTH):
        input_steps.append(extra_step(step_index))
    return {
        "initial_kv_cache": base["initial_kv_cache"],
        "input_steps": input_steps,
    }


def expected_journal() -> dict[str, Any]:
    fixture = seq16_fixture()
    current = list(fixture["initial_kv_cache"])
    transitions: list[dict[str, Any]] = []
    for step_index, input_step in enumerate(fixture["input_steps"]):
        next_item = {
            "position": input_step["token_position"],
            "key": list(input_step["new_key"]),
            "value": list(input_step["new_value"]),
        }
        next_cache = [dict(item) for item in current] + [next_item]
        scores = []
        for candidate in next_cache:
            if candidate["position"] <= input_step["token_position"]:
                scores.append({"position": candidate["position"], "score": dot(input_step["query"], candidate["key"])})
        selected = max(scores, key=lambda item: (item["score"], -item["position"]))
        selected_position = selected["position"]
        attention_output = next(item["value"] for item in next_cache if item["position"] == selected_position)
        transitions.append({
            "step_index": step_index,
            "input_step": input_step,
            "prior_kv_cache": current,
            "next_kv_cache": next_cache,
            "scores": scores,
            "selected_position": selected_position,
            "attention_output": attention_output,
        })
        current = next_cache
    return {
        "initial_kv_cache": fixture["initial_kv_cache"],
        "input_steps": fixture["input_steps"],
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
    outputs = [row["attention_output"] for row in journal["transitions"]]
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
        "outputs_commitment": outputs_commitment(outputs),
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


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvStwoNativeSeq16InputError("payload must be an object")
    expected_fields = {
        "schema", "decision", "issue", "source_issue", "target_id", "required_backend_version", "proof_version",
        "statement_version", "semantic_scope", "verifier_domain", "semantics", "masking_policy", "tie_break",
        "key_width", "value_width", "sequence_length", "initial_kv_items", "final_kv_items", "score_row_count",
        "trace_row_count", "score_gap_bits", "causal_gap_bits", "tie_gap_bits", "selected_positions",
        "initial_kv_cache", "input_steps", "final_kv_cache", "attention_outputs", "score_rows",
        "initial_kv_cache_commitment", "input_steps_commitment", "score_row_commitment", "final_kv_cache_commitment",
        "outputs_commitment", "proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment",
        "non_claims", "proof_verifier_hardening", "next_backend_step", "validation_commands",
    }
    if set(payload) != expected_fields:
        raise AttentionKvStwoNativeSeq16InputError("payload field set mismatch")
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
            raise AttentionKvStwoNativeSeq16InputError(f"payload field mismatch: {field}")
    journal = expected_journal()
    rows = build_score_rows(journal)
    outputs = [row["attention_output"] for row in journal["transitions"]]
    if payload["initial_kv_cache"] != journal["initial_kv_cache"]:
        raise AttentionKvStwoNativeSeq16InputError("initial KV cache drift")
    if payload["input_steps"] != journal["input_steps"]:
        raise AttentionKvStwoNativeSeq16InputError("input steps drift")
    if payload["final_kv_cache"] != journal["final_kv_cache"]:
        raise AttentionKvStwoNativeSeq16InputError("final KV cache drift")
    if payload["attention_outputs"] != outputs:
        raise AttentionKvStwoNativeSeq16InputError("attention outputs drift")
    if payload["score_rows"] != rows:
        raise AttentionKvStwoNativeSeq16InputError("score rows drift")
    if payload["selected_positions"] != [row["selected_position"] for row in journal["transitions"]]:
        raise AttentionKvStwoNativeSeq16InputError("selected positions drift")
    if len(payload["score_rows"]) != SCORE_ROW_COUNT:
        raise AttentionKvStwoNativeSeq16InputError("score row count drift")
    if payload["initial_kv_cache_commitment"] != kv_commitment(payload["initial_kv_cache"], INITIAL_KV_DOMAIN):
        raise AttentionKvStwoNativeSeq16InputError("initial KV commitment drift")
    if payload["input_steps_commitment"] != input_steps_commitment(payload["input_steps"]):
        raise AttentionKvStwoNativeSeq16InputError("input steps commitment drift")
    if payload["score_row_commitment"] != rows_commitment(payload["score_rows"]):
        raise AttentionKvStwoNativeSeq16InputError("score row commitment drift")
    if payload["final_kv_cache_commitment"] != kv_commitment(payload["final_kv_cache"], FINAL_KV_DOMAIN):
        raise AttentionKvStwoNativeSeq16InputError("final KV commitment drift")
    if payload["outputs_commitment"] != outputs_commitment(payload["attention_outputs"]):
        raise AttentionKvStwoNativeSeq16InputError("outputs commitment drift")
    if payload["proof_native_parameter_commitment"] != proof_native_parameter_commitment():
        raise AttentionKvStwoNativeSeq16InputError("proof-native parameter commitment drift")
    if payload["statement_commitment"] != statement_commitment(payload):
        raise AttentionKvStwoNativeSeq16InputError("statement commitment drift")
    if payload["public_instance_commitment"] != public_instance_commitment(payload):
        raise AttentionKvStwoNativeSeq16InputError("public instance commitment drift")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_payload(payload)
    return [{
        "issue": payload["issue"],
        "decision": payload["decision"],
        "proof_version": payload["proof_version"],
        "key_width": payload["key_width"],
        "value_width": payload["value_width"],
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
