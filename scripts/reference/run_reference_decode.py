#!/usr/bin/env python3
"""Tiny reference decode harness for fixture-driven differential checks.

This is intentionally small and model-agnostic. It demonstrates the
reference-vs-candidate pattern on a toy decoder shape; it does not claim full
transformer equivalence.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(data: Dict[str, Any], path: Path | None) -> None:
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if path is None:
        sys.stdout.write(payload)
        return
    path.write_text(payload, encoding="utf-8")


def require_list(name: str, value: Any) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    return value


def require_number_list(name: str, value: Any) -> List[float]:
    items = require_list(name, value)
    result: List[float] = []
    for index, item in enumerate(items):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{name}[{index}] must be numeric")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{name}[{index}] must be finite")
        result.append(number)
    return result


def require_int_list(name: str, value: Any) -> List[int]:
    items = require_list(name, value)
    result: List[int] = []
    for index, item in enumerate(items):
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError(f"{name}[{index}] must be an integer")
        result.append(int(item))
    return result


def require_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def require_positive_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def softmax(logits: Sequence[float]) -> List[float]:
    if not logits:
        raise ValueError("logits must not be empty")
    max_logit = max(logits)
    exps = [math.exp(logit - max_logit) for logit in logits]
    total = sum(exps)
    return [value / total for value in exps]


def top_indices(logits: Sequence[float], k: int) -> List[int]:
    ranked = sorted(
        enumerate(logits),
        key=lambda pair: (-pair[1], pair[0]),
    )
    return [index for index, _ in ranked[:k]]


def reference_logits(case: Dict[str, Any]) -> Dict[str, Any]:
    decode = case.get("reference_decode")
    if not isinstance(decode, dict):
        raise ValueError("fixture must contain reference_decode object")

    context_tokens = require_int_list("reference_decode.context_tokens", decode.get("context_tokens"))
    logit_bias = require_number_list("reference_decode.logit_bias", decode.get("logit_bias"))
    context_scale = require_number(
        "reference_decode.context_scale", decode.get("context_scale")
    )
    position_slope = require_number(
        "reference_decode.position_slope", decode.get("position_slope")
    )
    top_k = require_positive_int("reference_decode.top_k", decode.get("top_k"))
    if len(logit_bias) == 0:
        raise ValueError("reference_decode.logit_bias must not be empty")

    context_score = sum(context_tokens)
    logits = [
        round(context_scale * context_score + bias + position_slope * index, 12)
        for index, bias in enumerate(logit_bias)
    ]
    ranked = top_indices(logits, min(top_k, len(logits)))
    return {
        "context_score": context_score,
        "logits": logits,
        "top1": ranked[0],
        "topk": ranked,
    }


def compare_logits(
    reference: Sequence[float],
    candidate: Sequence[float],
    top_k: int,
) -> Dict[str, Any]:
    if len(reference) != len(candidate):
        raise ValueError(
            f"reference and candidate logits length mismatch: {len(reference)} != {len(candidate)}"
        )
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    absolute_errors = [abs(ref - cand) for ref, cand in zip(reference, candidate)]
    reference_probs = softmax(reference)
    candidate_probs = softmax(candidate)
    kl_divergence = sum(
        ref_prob * math.log(ref_prob / cand_prob)
        for ref_prob, cand_prob in zip(reference_probs, candidate_probs)
    )

    reference_top1 = top_indices(reference, 1)[0]
    candidate_top1 = top_indices(candidate, 1)[0]
    bounded_top_k = min(top_k, len(reference))
    reference_topk = top_indices(reference, bounded_top_k)
    candidate_topk = top_indices(candidate, bounded_top_k)
    topk_overlap = len(set(reference_topk).intersection(candidate_topk))

    return {
        "max_logit_error": max(absolute_errors),
        "mean_logit_error": sum(absolute_errors) / len(absolute_errors),
        "kl_divergence": kl_divergence,
        "top1_match": reference_top1 == candidate_top1,
        "topk_overlap": topk_overlap,
        "token_flips": 0 if reference_top1 == candidate_top1 else 1,
        "reference_top1": reference_top1,
        "candidate_top1": candidate_top1,
        "reference_topk": reference_topk,
        "candidate_topk": candidate_topk,
    }


def build_report(case: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("fixture must contain a non-empty case_id string")

    candidate = case.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("fixture must contain candidate object")
    candidate_logits = require_number_list("candidate.logits", candidate.get("logits"))

    reference = reference_logits(case)
    metrics = compare_logits(
        reference["logits"], candidate_logits, top_k=len(reference["topk"])
    )

    return {
        "case_id": case_id,
        "reference": reference,
        "candidate": {
            "logits": candidate_logits,
            "top1": metrics["candidate_top1"],
            "topk": metrics["candidate_topk"],
        },
        "metrics": {
            "max_logit_error": metrics["max_logit_error"],
            "mean_logit_error": metrics["mean_logit_error"],
            "kl_divergence": metrics["kl_divergence"],
            "top1_match": metrics["top1_match"],
            "topk_overlap": metrics["topk_overlap"],
            "token_flips": metrics["token_flips"],
        },
        "status": "pass" if metrics["top1_match"] and metrics["max_logit_error"] == 0 else "needs-review",
    }


def check_report(fixture: Dict[str, Any], report: Dict[str, Any]) -> None:
    expected = fixture.get("expected_comparison")
    if not isinstance(expected, dict):
        raise ValueError("fixture must contain expected_comparison object for check mode")
    if report != expected:
        raise ValueError(
            "comparison report did not match expected_comparison in fixture"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    emit = subparsers.add_parser("emit", help="emit a comparison JSON report")
    emit.add_argument("--fixture", required=True, type=Path)
    emit.add_argument("--output", type=Path)

    check = subparsers.add_parser("check", help="validate a comparison JSON report")
    check.add_argument("--fixture", required=True, type=Path)
    check.add_argument("--output", type=Path)

    args = parser.parse_args()
    fixture = load_json(args.fixture)
    report = build_report(fixture)

    if args.command == "emit":
        dump_json(report, args.output)
        return 0

    if args.command == "check":
        check_report(fixture, report)
        dump_json(report, args.output)
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
