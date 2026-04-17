#!/usr/bin/env python3
"""Check bounded approximation budgets from a JSON bundle.

The expected input is a JSON object with a non-empty ``cases`` array. Each case
must include a ``budget`` object and an ``evidence`` object. Missing evidence or
budget overruns exit non-zero.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def die(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def require_number(mapping: Dict[str, Any], key: str, case_id: str, section: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{case_id}: {section}.{key} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{case_id}: {section}.{key} must be finite")
    return number


def require_bool(mapping: Dict[str, Any], key: str, case_id: str, section: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{case_id}: {section}.{key} must be boolean")
    return bool(value)


def require_int(mapping: Dict[str, Any], key: str, case_id: str, section: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{case_id}: {section}.{key} must be an integer")
    return int(value)


def check_case(case: Dict[str, Any]) -> None:
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("each case must include a non-empty case_id")

    budget = case.get("budget")
    evidence = case.get("evidence")
    if not isinstance(budget, dict):
        raise ValueError(f"{case_id}: budget must be an object")
    if not isinstance(evidence, dict):
        raise ValueError(f"{case_id}: evidence must be an object")

    max_logit_error = require_number(budget, "max_logit_error", case_id, "budget")
    mean_logit_error = require_number(budget, "max_mean_logit_error", case_id, "budget")
    max_kl = require_number(budget, "max_kl", case_id, "budget")
    min_topk_overlap = require_int(budget, "min_topk_overlap", case_id, "budget")
    require_top1_match = require_bool(budget, "require_top1_match", case_id, "budget")

    if max_logit_error < 0 or mean_logit_error < 0 or max_kl < 0:
        raise ValueError(f"{case_id}: numeric budget maxima must be non-negative")
    if min_topk_overlap < 0:
        raise ValueError(f"{case_id}: budget.min_topk_overlap must be non-negative")

    token_flip_budget = budget.get("max_token_flips")
    if token_flip_budget is not None and (
        isinstance(token_flip_budget, bool) or not isinstance(token_flip_budget, int)
    ):
        raise ValueError(f"{case_id}: budget.max_token_flips must be an integer when provided")
    if isinstance(token_flip_budget, int) and token_flip_budget < 0:
        raise ValueError(f"{case_id}: budget.max_token_flips must be non-negative")

    evidence_max_logit_error = require_number(evidence, "max_logit_error", case_id, "evidence")
    evidence_mean_logit_error = require_number(evidence, "mean_logit_error", case_id, "evidence")
    evidence_kl = require_number(evidence, "kl_divergence", case_id, "evidence")
    top1_match = require_bool(evidence, "top1_match", case_id, "evidence")
    topk_overlap = require_int(evidence, "topk_overlap", case_id, "evidence")

    if evidence_max_logit_error > max_logit_error:
        raise ValueError(
            f"{case_id}: max_logit_error {evidence_max_logit_error} exceeds budget {max_logit_error}"
        )
    if evidence_mean_logit_error > mean_logit_error:
        raise ValueError(
            f"{case_id}: mean_logit_error {evidence_mean_logit_error} exceeds budget {mean_logit_error}"
        )
    if evidence_kl > max_kl:
        raise ValueError(f"{case_id}: kl_divergence {evidence_kl} exceeds budget {max_kl}")
    if require_top1_match and not top1_match:
        raise ValueError(f"{case_id}: top1_match is required but evidence reports false")
    if topk_overlap < min_topk_overlap:
        raise ValueError(
            f"{case_id}: topk_overlap {topk_overlap} is below budget {min_topk_overlap}"
        )

    if token_flip_budget is not None:
        token_flips = require_int(evidence, "token_flips", case_id, "evidence")
        if token_flips > token_flip_budget:
            raise ValueError(
                f"{case_id}: token_flips {token_flips} exceeds budget {token_flip_budget}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("budget_json", type=Path)
    args = parser.parse_args()

    try:
        payload = load_json(args.budget_json)
        if not isinstance(payload, dict):
            return die("budget JSON must be an object with a non-empty cases array")
        cases = payload.get("cases")
        if not isinstance(cases, list) or not cases:
            return die("budget JSON must contain a non-empty cases array")
        for case in cases:
            if not isinstance(case, dict):
                return die("each case must be a JSON object")
            check_case(case)
    except (OSError, json.JSONDecodeError) as err:
        return die(str(err))
    except ValueError as err:
        return die(str(err))

    print(f"checked {len(cases)} case(s) from {args.budget_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
