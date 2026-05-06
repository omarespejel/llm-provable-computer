#!/usr/bin/env python3
"""Checked scale gate for the native Stwo attention/KV seq16 proof.

This gate answers issue #450 narrowly: the native Stwo attention/KV AIR now has
a second proof artifact that scales sequence length from eight carried steps to
sixteen carried steps while keeping d=8 width, integer-argmax semantics,
causal-prefix masking, lowest-position tie-break, and explicit statement
binding.  It does not claim Softmax, multi-head attention, long-context
inference, recursion, PCD, or benchmark-grade timing.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
D8_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json"
D8_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json"
SEQ16_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json"
SEQ16_ENVELOPE_JSON = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.tsv"
MAX_INPUT_JSON_BYTES = 1_048_576
MAX_ENVELOPE_JSON_BYTES = 1_048_576

SCHEMA = "zkai-attention-kv-stwo-native-seq16-scale-gate-v1"
ISSUE = 450
SOURCE_ISSUE = 448
DECISION = "GO_NATIVE_STWO_ATTENTION_KV_SEQ16_SEQUENCE_LENGTH_SCALE"
CLAIM_BOUNDARY = (
    "NATIVE_STWO_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_LENGTH_16_PROOF_"
    "NOT_SOFTMAX_NOT_MULTIHEAD_NOT_LONG_CONTEXT_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD"
)
FIRST_BLOCKER = "NO_SOFTMAX_MULTIHEAD_OR_LONG_CONTEXT_NATIVE_ATTENTION_PROOF_YET"
SEQ16_ROUTE_ID = "local_stwo_attention_kv_d8_seq16_masked_sequence_proof"
D8_ROUTE_ID = "local_stwo_attention_kv_d8_masked_sequence_proof"
D8_TARGET_ID = "attention-kv-d8-causal-mask-sequence-v1"
D8_PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-sequence-air-proof-v1"
D8_REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-sequence-v1"
D8_SELECTED_POSITIONS = (0, 2, 3, 3, 5, 5, 7, 9)
SEQ16_TARGET_ID = "attention-kv-d8-causal-mask-seq16-v1"
SEQ16_PROOF_VERSION = "stwo-attention-kv-d8-causal-mask-seq16-air-proof-v1"
SEQ16_REQUIRED_BACKEND_VERSION = "stwo-attention-kv-d8-causal-mask-seq16-v1"
SEQ16_SELECTED_POSITIONS = (0, 2, 3, 3, 5, 5, 7, 9, 7, 3, 7, 3, 7, 5, 7, 16)
EXPECTED_MUTATION_NAMES = (
    "seq16_statement_commitment_relabeling",
    "seq16_public_instance_commitment_relabeling",
    "seq16_sequence_length_relabeling",
    "seq16_score_row_count_relabeling",
    "seq16_trace_row_count_relabeling",
    "seq16_selected_position_relabeling",
    "seq16_final_kv_relabeling",
    "seq16_envelope_input_split_brain",
    "seq16_envelope_backend_relabeling",
    "seq16_proof_size_metric_smuggling",
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
    "python3 scripts/zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_seq16_native_scale_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_seq16_native_scale_gate",
    "just lib",
    "just gate-fast",
    "just gate",
)
TSV_COLUMNS = (
    "decision",
    "baseline_sequence_length",
    "scaled_sequence_length",
    "baseline_score_rows",
    "scaled_score_rows",
    "baseline_proof_size_bytes",
    "scaled_proof_size_bytes",
    "mutations_checked",
    "mutations_rejected",
    "scaled_statement_commitment",
)


class AttentionKvSeq16NativeScaleGateError(ValueError):
    pass


def read_bounded_json(path: pathlib.Path, max_bytes: int, label: str) -> Any:
    if not path.is_file():
        raise AttentionKvSeq16NativeScaleGateError(f"missing {label}: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise AttentionKvSeq16NativeScaleGateError(f"{label} exceeds max size: got {size}, max {max_bytes}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionKvSeq16NativeScaleGateError(f"failed to read {label}: {err}") from err


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def validate_pair(input_payload: Any, envelope: Any, *, sequence_length: int, score_rows: int, trace_rows: int) -> None:
    if not isinstance(input_payload, dict) or not isinstance(envelope, dict):
        raise AttentionKvSeq16NativeScaleGateError("input/envelope must be objects")
    if envelope.get("input") != input_payload:
        raise AttentionKvSeq16NativeScaleGateError("proof envelope/input split-brain drift")
    if envelope.get("proof_backend") != "stwo":
        raise AttentionKvSeq16NativeScaleGateError("proof backend drift")
    if envelope.get("proof_backend_version") != input_payload.get("required_backend_version"):
        raise AttentionKvSeq16NativeScaleGateError("proof backend version drift")
    if envelope.get("statement_version") != input_payload.get("statement_version"):
        raise AttentionKvSeq16NativeScaleGateError("statement version drift")
    if envelope.get("semantic_scope") != input_payload.get("semantic_scope"):
        raise AttentionKvSeq16NativeScaleGateError("semantic scope drift")
    if input_payload.get("sequence_length") != sequence_length:
        raise AttentionKvSeq16NativeScaleGateError("sequence length drift")
    if input_payload.get("score_row_count") != score_rows:
        raise AttentionKvSeq16NativeScaleGateError("score row count drift")
    if input_payload.get("trace_row_count") != trace_rows:
        raise AttentionKvSeq16NativeScaleGateError("trace row count drift")
    if len(input_payload.get("selected_positions", [])) != sequence_length:
        raise AttentionKvSeq16NativeScaleGateError("selected positions length drift")
    proof = envelope.get("proof")
    if not isinstance(proof, list) or not proof:
        raise AttentionKvSeq16NativeScaleGateError("proof bytes missing")
    if any(not isinstance(byte, int) or byte < 0 or byte > 255 for byte in proof):
        raise AttentionKvSeq16NativeScaleGateError("proof bytes malformed")
    for key in (
        "statement_commitment",
        "public_instance_commitment",
        "score_row_commitment",
        "final_kv_cache_commitment",
        "outputs_commitment",
    ):
        value = input_payload.get(key)
        if not isinstance(value, str) or not value.startswith("blake2b-256:"):
            raise AttentionKvSeq16NativeScaleGateError(f"{key} commitment drift")


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
        "timing_policy": "single_local_dev_profile_engineering_only",
    }


def build_payload() -> dict[str, Any]:
    d8_input = read_bounded_json(D8_INPUT_JSON, MAX_INPUT_JSON_BYTES, "d8 input")
    d8_envelope = read_bounded_json(D8_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "d8 envelope")
    seq16_input = read_bounded_json(SEQ16_INPUT_JSON, MAX_INPUT_JSON_BYTES, "seq16 input")
    seq16_envelope = read_bounded_json(SEQ16_ENVELOPE_JSON, MAX_ENVELOPE_JSON_BYTES, "seq16 envelope")
    validate_pair(d8_input, d8_envelope, sequence_length=8, score_rows=52, trace_rows=64)
    validate_pair(seq16_input, seq16_envelope, sequence_length=16, score_rows=168, trace_rows=256)
    baseline = receipt_summary(D8_ROUTE_ID, d8_input, d8_envelope, D8_ENVELOPE_JSON)
    scaled = receipt_summary(SEQ16_ROUTE_ID, seq16_input, seq16_envelope, SEQ16_ENVELOPE_JSON)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_issue": SOURCE_ISSUE,
        "decision": DECISION,
        "claim_boundary": CLAIM_BOUNDARY,
        "first_blocker": FIRST_BLOCKER,
        "result": "GO",
        "baseline_receipt": baseline,
        "scaled_receipt": scaled,
        "scale_axis": "sequence_length_8_to_16_same_d8_width_same_integer_argmax_causal_mask",
        "score_row_scale": scaled["score_row_count"] / baseline["score_row_count"],
        "trace_row_scale": scaled["trace_row_count"] / baseline["trace_row_count"],
        "proof_size_scale": scaled["proof_size_bytes"] / baseline["proof_size_bytes"],
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    payload["scale_gate_commitment"] = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "baseline_receipt": payload["baseline_receipt"],
            "scaled_receipt": payload["scaled_receipt"],
            "scale_axis": payload["scale_axis"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-stwo-native-seq16-scale-gate:v1",
    )
    mutation_cases = run_mutations(payload)
    payload["mutation_cases"] = mutation_cases
    payload["mutations_checked"] = len(mutation_cases)
    payload["mutations_rejected"] = sum(1 for case in mutation_cases if case["rejected"] is True)
    payload["all_mutations_rejected"] = payload["mutations_rejected"] == len(EXPECTED_MUTATION_NAMES)
    validate_payload(payload)
    return payload


def mutate_payload(payload: dict[str, Any], name: str) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    out.pop("mutation_cases", None)
    out.pop("mutations_checked", None)
    out.pop("mutations_rejected", None)
    out.pop("all_mutations_rejected", None)
    if name == "seq16_statement_commitment_relabeling":
        out["scaled_receipt"]["statement_commitment"] = "blake2b-256:" + "00" * 32
    elif name == "seq16_public_instance_commitment_relabeling":
        out["scaled_receipt"]["public_instance_commitment"] = "blake2b-256:" + "11" * 32
    elif name == "seq16_sequence_length_relabeling":
        out["scaled_receipt"]["sequence_length"] = 8
    elif name == "seq16_score_row_count_relabeling":
        out["scaled_receipt"]["score_row_count"] = 52
    elif name == "seq16_trace_row_count_relabeling":
        out["scaled_receipt"]["trace_row_count"] = 64
    elif name == "seq16_selected_position_relabeling":
        out["scaled_receipt"]["selected_positions"][-1] += 1
    elif name == "seq16_final_kv_relabeling":
        out["scaled_receipt"]["final_kv_cache_commitment"] = "blake2b-256:" + "22" * 32
    elif name == "seq16_envelope_input_split_brain":
        out["scaled_receipt"]["target_id"] = D8_ROUTE_ID
    elif name == "seq16_envelope_backend_relabeling":
        out["scaled_receipt"]["required_backend_version"] = "tampered"
    elif name == "seq16_proof_size_metric_smuggling":
        out["scaled_receipt"]["proof_size_bytes"] = 1
    elif name == "d8_baseline_statement_relabeling":
        out["baseline_receipt"]["statement_commitment"] = "blake2b-256:" + "33" * 32
    elif name == "route_removed":
        out["scaled_receipt"]["route_id"] = "removed"
    elif name == "claim_boundary_softmax_overclaim":
        out["claim_boundary"] = out["claim_boundary"].replace("NOT_SOFTMAX_", "SOFTMAX_")
    elif name == "first_blocker_removed":
        out["first_blocker"] = None
    elif name == "non_claim_removed":
        out["non_claims"] = out["non_claims"][:-1]
    elif name == "unknown_field_injection":
        out["unexpected"] = True
    else:
        raise AttentionKvSeq16NativeScaleGateError(f"unknown mutation: {name}")
    return out


def run_mutations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name in EXPECTED_MUTATION_NAMES:
        mutated = mutate_payload(payload, name)
        try:
            validate_payload(mutated, allow_missing_mutation_summary=True)
        except AttentionKvSeq16NativeScaleGateError as err:
            cases.append({"name": name, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "error": "accepted"})
    return cases


def validate_receipt_summary(
    summary: Any,
    *,
    route_id: str,
    target_id: str,
    proof_version: str,
    required_backend_version: str,
    sequence_length: int,
    score_rows: int,
    trace_rows: int,
    final_kv_items: int,
    selected_positions: tuple[int, ...],
) -> None:
    if not isinstance(summary, dict):
        raise AttentionKvSeq16NativeScaleGateError("receipt summary must be an object")
    expected_keys = {
        "route_id", "target_id", "proof_version", "required_backend_version", "sequence_length",
        "key_width", "value_width", "score_row_count", "trace_row_count", "final_kv_items",
        "selected_positions", "proof_size_bytes", "envelope_size_bytes", "statement_commitment",
        "public_instance_commitment", "score_row_commitment", "final_kv_cache_commitment", "outputs_commitment",
        "timing_policy",
    }
    if set(summary) != expected_keys:
        raise AttentionKvSeq16NativeScaleGateError("receipt summary field drift")
    if summary["route_id"] != route_id:
        raise AttentionKvSeq16NativeScaleGateError("route id drift")
    if summary["target_id"] != target_id:
        raise AttentionKvSeq16NativeScaleGateError("target id drift")
    if summary["proof_version"] != proof_version:
        raise AttentionKvSeq16NativeScaleGateError("proof version drift")
    if summary["required_backend_version"] != required_backend_version:
        raise AttentionKvSeq16NativeScaleGateError("required backend version drift")
    if summary["sequence_length"] != sequence_length:
        raise AttentionKvSeq16NativeScaleGateError("sequence length drift")
    if summary["score_row_count"] != score_rows:
        raise AttentionKvSeq16NativeScaleGateError("score row count drift")
    if summary["trace_row_count"] != trace_rows:
        raise AttentionKvSeq16NativeScaleGateError("trace row count drift")
    if summary["key_width"] != 8 or summary["value_width"] != 8:
        raise AttentionKvSeq16NativeScaleGateError("width drift")
    if summary["final_kv_items"] != final_kv_items:
        raise AttentionKvSeq16NativeScaleGateError("final KV item count drift")
    if not isinstance(summary["selected_positions"], list) or any(
        not isinstance(item, int) or isinstance(item, bool)
        for item in summary["selected_positions"]
    ):
        raise AttentionKvSeq16NativeScaleGateError("selected positions malformed")
    if tuple(summary["selected_positions"]) != selected_positions:
        raise AttentionKvSeq16NativeScaleGateError("selected positions drift")
    if summary["proof_size_bytes"] <= 0 or summary["envelope_size_bytes"] <= summary["proof_size_bytes"]:
        raise AttentionKvSeq16NativeScaleGateError("proof/envelope metric drift")
    if summary["timing_policy"] != "single_local_dev_profile_engineering_only":
        raise AttentionKvSeq16NativeScaleGateError("timing policy drift")
    for key in (
        "statement_commitment", "public_instance_commitment", "score_row_commitment",
        "final_kv_cache_commitment", "outputs_commitment",
    ):
        if not isinstance(summary[key], str) or not summary[key].startswith("blake2b-256:"):
            raise AttentionKvSeq16NativeScaleGateError(f"{key} drift")


def validate_payload(payload: Any, *, allow_missing_mutation_summary: bool = False) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvSeq16NativeScaleGateError("payload must be an object")
    expected_keys = {
        "schema", "issue", "source_issue", "decision", "claim_boundary", "first_blocker", "result",
        "baseline_receipt", "scaled_receipt", "scale_axis", "score_row_scale", "trace_row_scale",
        "proof_size_scale", "non_claims", "validation_commands", "scale_gate_commitment",
    }
    if not allow_missing_mutation_summary:
        expected_keys |= {"mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"}
    if set(payload) != expected_keys:
        raise AttentionKvSeq16NativeScaleGateError("payload field drift")
    if payload["schema"] != SCHEMA:
        raise AttentionKvSeq16NativeScaleGateError("schema drift")
    if payload["issue"] != ISSUE or payload["source_issue"] != SOURCE_ISSUE:
        raise AttentionKvSeq16NativeScaleGateError("issue drift")
    if payload["decision"] != DECISION or payload["result"] != "GO":
        raise AttentionKvSeq16NativeScaleGateError("decision drift")
    if payload["claim_boundary"] != CLAIM_BOUNDARY:
        raise AttentionKvSeq16NativeScaleGateError("claim boundary drift")
    if payload["first_blocker"] != FIRST_BLOCKER:
        raise AttentionKvSeq16NativeScaleGateError("first blocker drift")
    if payload["scale_axis"] != "sequence_length_8_to_16_same_d8_width_same_integer_argmax_causal_mask":
        raise AttentionKvSeq16NativeScaleGateError("scale axis drift")
    if tuple(payload["non_claims"]) != NON_CLAIMS:
        raise AttentionKvSeq16NativeScaleGateError("non-claim drift")
    if tuple(payload["validation_commands"]) != VALIDATION_COMMANDS:
        raise AttentionKvSeq16NativeScaleGateError("validation command drift")
    validate_receipt_summary(
        payload["baseline_receipt"],
        route_id=D8_ROUTE_ID,
        target_id=D8_TARGET_ID,
        proof_version=D8_PROOF_VERSION,
        required_backend_version=D8_REQUIRED_BACKEND_VERSION,
        sequence_length=8,
        score_rows=52,
        trace_rows=64,
        final_kv_items=10,
        selected_positions=D8_SELECTED_POSITIONS,
    )
    validate_receipt_summary(
        payload["scaled_receipt"],
        route_id=SEQ16_ROUTE_ID,
        target_id=SEQ16_TARGET_ID,
        proof_version=SEQ16_PROOF_VERSION,
        required_backend_version=SEQ16_REQUIRED_BACKEND_VERSION,
        sequence_length=16,
        score_rows=168,
        trace_rows=256,
        final_kv_items=18,
        selected_positions=SEQ16_SELECTED_POSITIONS,
    )
    if payload["score_row_scale"] != payload["scaled_receipt"]["score_row_count"] / payload["baseline_receipt"]["score_row_count"]:
        raise AttentionKvSeq16NativeScaleGateError("score-row scale drift")
    if payload["trace_row_scale"] != payload["scaled_receipt"]["trace_row_count"] / payload["baseline_receipt"]["trace_row_count"]:
        raise AttentionKvSeq16NativeScaleGateError("trace-row scale drift")
    if payload["proof_size_scale"] != payload["scaled_receipt"]["proof_size_bytes"] / payload["baseline_receipt"]["proof_size_bytes"]:
        raise AttentionKvSeq16NativeScaleGateError("proof-size scale drift")
    expected_commitment = blake2b_commitment(
        {
            "schema": payload["schema"],
            "decision": payload["decision"],
            "claim_boundary": payload["claim_boundary"],
            "first_blocker": payload["first_blocker"],
            "baseline_receipt": payload["baseline_receipt"],
            "scaled_receipt": payload["scaled_receipt"],
            "scale_axis": payload["scale_axis"],
            "non_claims": payload["non_claims"],
        },
        "ptvm:zkai:attention-kv-stwo-native-seq16-scale-gate:v1",
    )
    if payload["scale_gate_commitment"] != expected_commitment:
        raise AttentionKvSeq16NativeScaleGateError("scale gate commitment drift")
    if allow_missing_mutation_summary:
        return
    mutation_cases = payload.get("mutation_cases")
    if not isinstance(mutation_cases, list):
        raise AttentionKvSeq16NativeScaleGateError("mutation cases must be a list")
    if tuple(case.get("name") for case in mutation_cases) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvSeq16NativeScaleGateError("mutation case inventory drift")
    if any(case.get("rejected") is not True for case in mutation_cases):
        raise AttentionKvSeq16NativeScaleGateError("mutation rejection drift")
    if payload["mutations_checked"] != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvSeq16NativeScaleGateError("mutation count drift")
    if payload["mutations_rejected"] != len(EXPECTED_MUTATION_NAMES):
        raise AttentionKvSeq16NativeScaleGateError("mutation rejection count drift")
    if payload["all_mutations_rejected"] is not True:
        raise AttentionKvSeq16NativeScaleGateError("fail-closed summary drift")


def to_tsv(payload: dict[str, Any]) -> str:
    rows: list[str] = []
    writer = csv.DictWriter(_ListWriter(rows), fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow({
        "decision": payload["decision"],
        "baseline_sequence_length": payload["baseline_receipt"]["sequence_length"],
        "scaled_sequence_length": payload["scaled_receipt"]["sequence_length"],
        "baseline_score_rows": payload["baseline_receipt"]["score_row_count"],
        "scaled_score_rows": payload["scaled_receipt"]["score_row_count"],
        "baseline_proof_size_bytes": payload["baseline_receipt"]["proof_size_bytes"],
        "scaled_proof_size_bytes": payload["scaled_receipt"]["proof_size_bytes"],
        "mutations_checked": payload["mutations_checked"],
        "mutations_rejected": payload["mutations_rejected"],
        "scaled_statement_commitment": payload["scaled_receipt"]["statement_commitment"],
    })
    return "".join(rows)


class _ListWriter:
    def __init__(self, rows: list[str]) -> None:
        self.rows = rows

    def write(self, value: str) -> int:
        self.rows.append(value)
        return len(value)


def write_outputs(payload: dict[str, Any], json_out: pathlib.Path, tsv_out: pathlib.Path) -> None:
    validate_payload(payload)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    tsv_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tsv_out.write_text(to_tsv(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    parser.add_argument("--write-json", type=pathlib.Path, default=JSON_OUT)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=TSV_OUT)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json, args.write_tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
