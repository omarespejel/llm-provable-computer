#!/usr/bin/env python3
"""Statement-bound attention/KV-cache transition receipt probe.

This is a receipt-contract probe, not a new proof backend. It records the
minimal state-transition fields a future transformer/agent proof must bind:
prior KV state, input/query state, attention output, next KV state, model
configuration, verifier domain, and proof status.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-transition-receipt-2026-05.json"
TSV_OUT = ROOT / "docs" / "engineering" / "evidence" / "zkai-attention-kv-transition-receipt-2026-05.tsv"

SCHEMA = "zkai-attention-kv-transition-receipt-probe-v1"
RECEIPT_SCHEMA = "zkai-statement-receipt-v1"
DECISION = "GO_KV_TRANSITION_RECEIPT_CONTRACT_NOT_PROOF"
SOURCE_DATE_EPOCH_DEFAULT = 0
EXPECTED_MUTATION_NAMES = (
    "prior_kv_cache_relabeling",
    "input_query_relabeling",
    "attention_output_relabeling",
    "next_kv_cache_relabeling",
    "model_config_relabeling",
    "proof_status_overclaim",
    "verifier_domain_relabeling",
    "statement_commitment_relabeling",
)
TSV_COLUMNS = (
    "case_id",
    "decision",
    "proof_status",
    "prior_kv_items",
    "next_kv_items",
    "selected_position",
    "mutations_checked",
    "mutations_rejected",
    "statement_commitment",
)


class AttentionKvReceiptError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _generated_at() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(SOURCE_DATE_EPOCH_DEFAULT))
    try:
        timestamp = int(raw)
    except ValueError as err:
        raise AttentionKvReceiptError("SOURCE_DATE_EPOCH must be an integer") from err
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_transition_fixture() -> dict[str, Any]:
    return {
        "case_id": "tiny_single_head_argmax_kv_transition_v1",
        "model_config": {
            "attention_mode": "integer_argmax_attention",
            "head_count": 1,
            "key_width": 2,
            "value_width": 2,
            "tie_break": "lowest_position",
        },
        "prior_kv_cache": [
            {"position": 0, "key": [1, 0], "value": [2, 1]},
            {"position": 1, "key": [0, 1], "value": [-1, 3]},
        ],
        "input_step": {
            "token_position": 2,
            "query": [1, 1],
            "new_key": [1, -1],
            "new_value": [4, 2],
        },
    }


def dot(lhs: list[int], rhs: list[int]) -> int:
    if len(lhs) != len(rhs):
        raise AttentionKvReceiptError("dot-product width mismatch")
    return sum(left * right for left, right in zip(lhs, rhs, strict=True))


def evaluate_transition(fixture: dict[str, Any]) -> dict[str, Any]:
    prior = fixture["prior_kv_cache"]
    input_step = fixture["input_step"]
    next_item = {
        "position": input_step["token_position"],
        "key": input_step["new_key"],
        "value": input_step["new_value"],
    }
    candidates = prior + [next_item]
    scored = [
        {"position": item["position"], "score": dot(input_step["query"], item["key"]), "value": item["value"]}
        for item in candidates
    ]
    selected = max(scored, key=lambda item: (item["score"], -item["position"]))
    return {
        "scores": scored,
        "selected_position": selected["position"],
        "attention_output": selected["value"],
        "next_kv_cache": candidates,
    }


def build_receipt(fixture: dict[str, Any] | None = None) -> dict[str, Any]:
    fixture = canonical_transition_fixture() if fixture is None else fixture
    transition = evaluate_transition(fixture)
    statement = {
        "receipt_version": RECEIPT_SCHEMA,
        "verifier_domain": "ptvm:zkai:attention-kv-transition:v1",
        "proof_system": "source-backed-transition-receipt",
        "proof_system_version": "attention-kv-transition-reference-v1",
        "statement_kind": "attention-kv-cache-transition",
        "model_id": "tiny-single-head-argmax-attention-kv-v1",
        "model_config_commitment": blake2b_commitment(
            fixture["model_config"], "ptvm:zkai:attention-kv-model-config:v1"
        ),
        "prior_kv_cache_commitment": blake2b_commitment(
            fixture["prior_kv_cache"], "ptvm:zkai:attention-prior-kv-cache:v1"
        ),
        "input_commitment": blake2b_commitment(fixture["input_step"], "ptvm:zkai:attention-input-step:v1"),
        "attention_output_commitment": blake2b_commitment(
            transition["attention_output"], "ptvm:zkai:attention-output:v1"
        ),
        "next_kv_cache_commitment": blake2b_commitment(
            transition["next_kv_cache"], "ptvm:zkai:attention-next-kv-cache:v1"
        ),
        "public_instance_commitment": blake2b_commitment(
            {
                "prior_kv_cache_commitment": blake2b_commitment(
                    fixture["prior_kv_cache"], "ptvm:zkai:attention-prior-kv-cache:v1"
                ),
                "input_commitment": blake2b_commitment(fixture["input_step"], "ptvm:zkai:attention-input-step:v1"),
                "attention_output_commitment": blake2b_commitment(
                    transition["attention_output"], "ptvm:zkai:attention-output:v1"
                ),
                "next_kv_cache_commitment": blake2b_commitment(
                    transition["next_kv_cache"], "ptvm:zkai:attention-next-kv-cache:v1"
                ),
            },
            "ptvm:zkai:attention-kv-public-instance:v1",
        ),
        "proof_commitment": "not-applicable:source-backed-kv-transition-receipt",
        "proof_status": "SOURCE_BACKED_RECEIPT_NOT_PROVEN",
        "selected_position": transition["selected_position"],
        "score_trace_commitment": blake2b_commitment(transition["scores"], "ptvm:zkai:attention-score-trace:v1"),
        "non_claims": [
            "not a Stwo proof",
            "not a Softmax proof",
            "not full transformer inference",
            "not recursive or on-chain verification",
            "not agent correctness",
        ],
    }
    statement["statement_commitment"] = blake2b_commitment(
        {key: value for key, value in statement.items() if key != "statement_commitment"},
        "ptvm:zkai:attention-kv-statement:v1",
    )
    return statement


def verify_receipt(receipt: dict[str, Any], fixture: dict[str, Any] | None = None) -> bool:
    expected = build_receipt(canonical_transition_fixture() if fixture is None else fixture)
    if set(receipt) != set(expected):
        raise AttentionKvReceiptError("receipt field set mismatch")
    if receipt != expected:
        for field in sorted(expected):
            if receipt.get(field) != expected[field]:
                raise AttentionKvReceiptError(f"receipt field drift: {field}")
        raise AttentionKvReceiptError("receipt drift")
    return True


def mutate_path(value: dict[str, Any], path: tuple[str, ...], replacement: Any) -> dict[str, Any]:
    out = copy.deepcopy(value)
    cursor: Any = out
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    return out


def mutation_cases(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wrong_commitment = "blake2b-256:" + "66" * 32
    cases = {
        "prior_kv_cache_relabeling": mutate_path(receipt, ("prior_kv_cache_commitment",), wrong_commitment),
        "input_query_relabeling": mutate_path(receipt, ("input_commitment",), wrong_commitment),
        "attention_output_relabeling": mutate_path(receipt, ("attention_output_commitment",), wrong_commitment),
        "next_kv_cache_relabeling": mutate_path(receipt, ("next_kv_cache_commitment",), wrong_commitment),
        "model_config_relabeling": mutate_path(receipt, ("model_config_commitment",), wrong_commitment),
        "proof_status_overclaim": mutate_path(receipt, ("proof_status",), "PROVEN_BY_STWO"),
        "verifier_domain_relabeling": mutate_path(receipt, ("verifier_domain",), "ptvm:zkai:other-domain"),
        "statement_commitment_relabeling": mutate_path(receipt, ("statement_commitment",), wrong_commitment),
    }
    if tuple(sorted(cases)) != tuple(sorted(EXPECTED_MUTATION_NAMES)):
        raise AttentionKvReceiptError("mutation corpus drift")
    return cases


def run_probe() -> dict[str, Any]:
    fixture = canonical_transition_fixture()
    transition = evaluate_transition(fixture)
    receipt = build_receipt(fixture)
    baseline_accepted = verify_receipt(receipt, fixture)
    mutations = []
    for name, mutated in mutation_cases(receipt).items():
        try:
            verify_receipt(mutated, fixture)
        except AttentionKvReceiptError as err:
            mutations.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            mutations.append({"name": name, "rejected": False, "reason": "accepted"})
    rejected = sum(1 for item in mutations if item["rejected"])
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "generated_at": _generated_at(),
        "git_commit": os.environ.get("ZKAI_ATTENTION_KV_GIT_COMMIT", _git_commit()),
        "question": "Can a tiny attention/KV state transition receipt bind prior state, next state, and output fail-closed?",
        "fixture": fixture,
        "transition": transition,
        "receipt": receipt,
        "baseline_accepted": baseline_accepted,
        "mutations_checked": len(mutations),
        "mutations_rejected": rejected,
        "all_mutations_rejected": rejected == len(mutations),
        "mutation_cases": mutations,
        "summary": {
            "prior_kv_items": len(fixture["prior_kv_cache"]),
            "next_kv_items": len(transition["next_kv_cache"]),
            "selected_position": transition["selected_position"],
            "proof_status": receipt["proof_status"],
            "interpretation": (
                "A verifiable-intelligence receipt must bind state transition semantics, not only "
                "a model output label. Prior KV, input, output, and next KV are separate relabeling surfaces."
            ),
        },
        "next_backend_step": (
            "replace the source-backed transition receipt with a Stwo proof or source-backed proof receipt "
            "that consumes the same public-instance fields"
        ),
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise AttentionKvReceiptError("payload must be an object")
    if payload.get("schema") != SCHEMA:
        raise AttentionKvReceiptError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionKvReceiptError("decision drift")
    if payload.get("baseline_accepted") is not True:
        raise AttentionKvReceiptError("baseline receipt must be accepted")
    fixture = payload.get("fixture")
    if not isinstance(fixture, dict):
        raise AttentionKvReceiptError("fixture must be an object")
    transition = evaluate_transition(fixture)
    if payload.get("transition") != transition:
        raise AttentionKvReceiptError("transition drift")
    payload_mutation_cases = payload.get("mutation_cases")
    if not isinstance(payload_mutation_cases, list):
        raise AttentionKvReceiptError("mutation cases must be a list")
    if any(not isinstance(item, dict) for item in payload_mutation_cases):
        raise AttentionKvReceiptError("mutation case entries must be objects")
    expected_receipt = build_receipt(fixture)
    expected_mutations = []
    for name, mutated in mutation_cases(expected_receipt).items():
        try:
            verify_receipt(mutated, fixture)
        except AttentionKvReceiptError as err:
            expected_mutations.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            expected_mutations.append({"name": name, "rejected": False, "reason": "accepted"})
    if tuple(item.get("name") for item in payload_mutation_cases) != EXPECTED_MUTATION_NAMES:
        raise AttentionKvReceiptError("mutation case names drift")
    if any(item.get("rejected") is not True for item in payload_mutation_cases):
        raise AttentionKvReceiptError("mutation case rejection drift")
    if payload_mutation_cases != expected_mutations:
        raise AttentionKvReceiptError("mutation case details drift")
    mutation_count = len(payload_mutation_cases)
    mutation_rejections = sum(1 for item in payload_mutation_cases if item.get("rejected") is True)
    if payload.get("mutations_checked") != mutation_count:
        raise AttentionKvReceiptError("mutation count drift")
    if payload.get("mutations_rejected") != mutation_rejections:
        raise AttentionKvReceiptError("mutation rejection drift")
    if payload.get("all_mutations_rejected") is not True:
        raise AttentionKvReceiptError("fail-closed summary drift")
    expected_summary = {
        "prior_kv_items": len(fixture["prior_kv_cache"]),
        "next_kv_items": len(transition["next_kv_cache"]),
        "selected_position": transition["selected_position"],
        "proof_status": expected_receipt["proof_status"],
        "interpretation": (
            "A verifiable-intelligence receipt must bind state transition semantics, not only "
            "a model output label. Prior KV, input, output, and next KV are separate relabeling surfaces."
        ),
    }
    if payload.get("summary") != expected_summary:
        raise AttentionKvReceiptError("summary drift")
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        raise AttentionKvReceiptError("receipt must be an object")
    verify_receipt(receipt, payload.get("fixture"))


def to_tsv(payload: dict[str, Any]) -> str:
    rows: list[str] = []
    writer = csv.DictWriter(_ListWriter(rows), fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "case_id": payload["fixture"]["case_id"],
            "decision": payload["decision"],
            "proof_status": payload["receipt"]["proof_status"],
            "prior_kv_items": payload["summary"]["prior_kv_items"],
            "next_kv_items": payload["summary"]["next_kv_items"],
            "selected_position": payload["summary"]["selected_position"],
            "mutations_checked": payload["mutations_checked"],
            "mutations_rejected": payload["mutations_rejected"],
            "statement_commitment": payload["receipt"]["statement_commitment"],
        }
    )
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
    payload = run_probe()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    if not args.no_write:
        write_outputs(payload, args.write_json, args.write_tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
