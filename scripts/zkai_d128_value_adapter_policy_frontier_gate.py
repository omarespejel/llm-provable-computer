#!/usr/bin/env python3
"""Gate the d128 attention-to-RMSNorm value-adapter policy frontier."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import pathlib
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_attention_d128_value_adapter_gate as adapter_gate  # noqa: E402
from scripts import zkai_d128_attention_rmsnorm_boundary_gate as boundary_gate  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-value-adapter-policy-frontier-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-value-adapter-policy-frontier-2026-05.tsv"

SCHEMA = "zkai-d128-value-adapter-policy-frontier-gate-v1"
DECISION = "NO_GO_CURRENT_FIXTURE_VALUE_DERIVED_ADAPTER"
RESULT = "NO_GO_CURRENT_D128_TARGET_IS_INDEX_SYNTHETIC_NOT_ATTENTION_DERIVED"
CLAIM_BOUNDARY = (
    "CURRENT_ATTENTION_OUTPUTS_DO_NOT_VALUE_DERIVE_CURRENT_D128_RMSNORM_INPUT_UNDER_CHECKED_"
    "NON_ARBITRARY_POLICIES_INDEX_ONLY_EXACT_MATCH_IS_FORBIDDEN"
)
PAYLOAD_DOMAIN = "ptvm:zkai:d128-value-adapter-policy-frontier:v1"

EXPECTED_SUMMARY = {
    "attention_cells": 64,
    "target_width": 128,
    "best_admissible_policy_id": "channelwise_affine_over_tiled_attention",
    "best_admissible_mismatches": 106,
    "best_admissible_mean_abs_error": 49.796875,
    "existing_adapter_best_policy_id": "best_global_affine_over_tiled_attention",
    "existing_adapter_best_mismatches": 124,
    "index_only_exact_mismatches": 0,
    "per_source_cell_lower_bound_mismatches": 64,
    "boundary_status": "NO_GO_CURRENT_VALUE_HANDOFF",
}

NON_CLAIMS = [
    "not a value-derived adapter for the current d128 target",
    "not attention plus MLP in one proof object",
    "not a full transformer block proof",
    "not a NANOZK benchmark win",
    "not timing evidence",
    "not production-ready zkML",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_value_adapter_policy_frontier_gate.py --write-json docs/engineering/evidence/zkai-d128-value-adapter-policy-frontier-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-value-adapter-policy-frontier-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_d128_value_adapter_policy_frontier_gate.py scripts/tests/test_zkai_d128_value_adapter_policy_frontier_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_d128_value_adapter_policy_frontier_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

SOURCE_ARTIFACTS = (
    ("attention_d8_bounded_softmax_table", adapter_gate.ATTENTION_FIXTURE),
    ("d128_rmsnorm_input", adapter_gate.D128_RMSNORM_INPUT),
    ("attention_d128_value_adapter_gate", adapter_gate.JSON_OUT),
    ("attention_rmsnorm_mlp_boundary_gate", boundary_gate.JSON_OUT),
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "policy_frontier",
    "policy_frontier_commitment",
    "summary",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = [
    "decision",
    "result",
    "best_admissible_policy_id",
    "best_admissible_mismatches",
    "best_admissible_mean_abs_error",
    "existing_adapter_best_mismatches",
    "per_source_cell_lower_bound_mismatches",
    "index_only_exact_mismatches",
    "boundary_status",
]


class ValueAdapterPolicyFrontierError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise ValueAdapterPolicyFrontierError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as err:
        raise ValueAdapterPolicyFrontierError(f"invalid JSON value: {err}") from err


def commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueAdapterPolicyFrontierError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueAdapterPolicyFrontierError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueAdapterPolicyFrontierError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueAdapterPolicyFrontierError(f"{label} must be integer")
    return value


def _number(value: Any, label: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueAdapterPolicyFrontierError(f"{label} must be number")
    return value


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        return adapter_gate.load_json(path)
    except Exception as err:  # noqa: BLE001 - normalize imported gate errors.
        raise ValueAdapterPolicyFrontierError(f"failed loading {path}: {err}") from err


def source_artifact(artifact_id: str, path: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, raw = load_json(path)
    return (
        payload,
        {
            "id": artifact_id,
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        },
    )


def score_policy(policy_id: str, description: str, values: list[int], target: list[int], admissible: bool) -> dict[str, Any]:
    if len(values) != len(target):
        raise ValueAdapterPolicyFrontierError(f"policy width drift: {policy_id}")
    mismatches = [
        {"index": index, "candidate": candidate, "target": target_value}
        for index, (candidate, target_value) in enumerate(zip(values, target, strict=True))
        if candidate != target_value
    ]
    total_abs_error = sum(abs(candidate - target_value) for candidate, target_value in zip(values, target, strict=True))
    return {
        "id": policy_id,
        "description": description,
        "admissible_as_value_adapter": admissible,
        "output_width": len(values),
        "mismatch_count": len(mismatches),
        "mismatch_share": len(mismatches) / len(target),
        "total_abs_error": total_abs_error,
        "mean_abs_error": total_abs_error / len(target),
        "first_mismatches": mismatches[:8],
    }


def best_global_affine(base: list[int], target: list[int]) -> list[int]:
    best: tuple[int, int, int, int, list[int]] | None = None
    for scale in range(-64, 65):
        for bias in range(-256, 257):
            values = [scale * value + bias for value in base]
            mismatches = sum(candidate != target_value for candidate, target_value in zip(values, target, strict=True))
            total_abs_error = sum(abs(candidate - target_value) for candidate, target_value in zip(values, target, strict=True))
            item = (mismatches, total_abs_error, scale, bias, values)
            if best is None or item[:4] < best[:4]:
                best = item
    if best is None:
        raise ValueAdapterPolicyFrontierError("failed global affine search")
    return best[4]


def best_channelwise_affine(base: list[int], target: list[int], width: int) -> tuple[list[int], list[dict[str, int]]]:
    values = [0] * len(target)
    params = []
    for channel in range(width):
        indices = [index for index in range(len(target)) if index % width == channel]
        xs = [base[index] for index in indices]
        ys = [target[index] for index in indices]
        best: tuple[int, int, int, int, list[int]] | None = None
        for scale in range(-64, 65):
            for bias in range(-256, 257):
                candidate = [scale * value + bias for value in xs]
                mismatches = sum(left != right for left, right in zip(candidate, ys, strict=True))
                total_abs_error = sum(abs(left - right) for left, right in zip(candidate, ys, strict=True))
                item = (mismatches, total_abs_error, scale, bias, candidate)
                if best is None or item[:4] < best[:4]:
                    best = item
        if best is None:
            raise ValueAdapterPolicyFrontierError("failed channelwise affine search")
        mismatches, total_abs_error, scale, bias, candidate = best
        params.append(
            {
                "channel": channel,
                "scale": scale,
                "bias": bias,
                "mismatches": mismatches,
                "total_abs_error": total_abs_error,
            }
        )
        for index, candidate_value in zip(indices, candidate, strict=True):
            values[index] = candidate_value
    return values, params


def per_source_cell_repeated_lower_bound(flat: list[int], target: list[int]) -> list[int]:
    if len(target) != 2 * len(flat):
        raise ValueAdapterPolicyFrontierError("per-source-cell lower bound expects tiled target width")
    values = [0] * len(target)
    for index, _source_value in enumerate(flat):
        left = target[index]
        right = target[index + len(flat)]
        candidate = left if abs(left - right) <= abs(right - left) else right
        values[index] = candidate
        values[index + len(flat)] = candidate
    return values


def index_only_target_pattern(width: int) -> list[int]:
    return [((13 * index + 7) % 193) - 96 for index in range(width)]


def build_policy_frontier(
    attention_payload: dict[str, Any],
    d128_payload: dict[str, Any],
    adapter_payload: dict[str, Any],
    boundary_payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        adapter_gate.validate_payload(adapter_payload)
        boundary_gate.validate_payload(boundary_payload)
    except Exception as err:  # noqa: BLE001 - normalize dependent gate failures.
        raise ValueAdapterPolicyFrontierError(f"dependent gate validation failed: {err}") from err

    attention_outputs = adapter_gate._extract_attention_outputs(attention_payload)
    flat = [cell for row in attention_outputs for cell in row]
    target = adapter_gate._extract_d128_input(d128_payload)
    tiled = (flat * ((len(target) + len(flat) - 1) // len(flat)))[: len(target)]
    channelwise_values, channelwise_params = best_channelwise_affine(tiled, target, width=8)
    policies = [
        score_policy("tile_flat_attention_twice", "flatten attention and tile to d128 width", tiled, target, True),
        score_policy(
            "global_affine_over_tiled_attention",
            "best single integer y = scale*x + bias over tiled attention",
            best_global_affine(tiled, target),
            target,
            True,
        ),
        score_policy(
            "channelwise_affine_over_tiled_attention",
            "best per-channel integer affine map over tiled attention; still low-parameter but not exact",
            channelwise_values,
            target,
            True,
        ),
        score_policy(
            "per_source_cell_repeated_lower_bound",
            "generous lower bound if each repeated source cell may choose one output value for both repeats",
            per_source_cell_repeated_lower_bound(flat, target),
            target,
            False,
        ),
        score_policy(
            "index_only_synthetic_target_pattern",
            "the known d128 fixture pattern; exact but forbidden because it ignores attention values",
            index_only_target_pattern(len(target)),
            target,
            False,
        ),
    ]
    best_admissible = min(
        (policy for policy in policies if policy["admissible_as_value_adapter"]),
        key=lambda policy: (policy["mismatch_count"], policy["total_abs_error"], policy["id"]),
    )
    exact_policies = [policy for policy in policies if policy["mismatch_count"] == 0]
    boundary_summary = _dict(boundary_payload.get("summary"), "boundary summary")
    adapter_summary = _dict(adapter_payload.get("summary"), "adapter summary")
    return {
        "analysis_kind": "d128-value-adapter-policy-frontier",
        "attention": {
            "outputs_commitment": _str(attention_payload.get("outputs_commitment"), "attention outputs commitment"),
            "statement_commitment": _str(attention_payload.get("statement_commitment"), "attention statement"),
            "shape": [len(attention_outputs), len(attention_outputs[0])],
            "flattened_cells": len(flat),
            "min_q8": min(flat),
            "max_q8": max(flat),
            "sum_q8": sum(flat),
        },
        "target": {
            "input_activation_commitment": _str(
                d128_payload.get("input_activation_commitment"), "target input activation"
            ),
            "width": len(target),
            "min_q8": min(target),
            "max_q8": max(target),
            "sum_q8": sum(target),
            "index_only_pattern_exact": index_only_target_pattern(len(target)) == target,
        },
        "policies": policies,
        "channelwise_affine_params": channelwise_params,
        "best_admissible_policy": {
            "id": best_admissible["id"],
            "mismatch_count": best_admissible["mismatch_count"],
            "mean_abs_error": best_admissible["mean_abs_error"],
        },
        "exact_policy_count": len(exact_policies),
        "exact_policy_ids": [policy["id"] for policy in exact_policies],
        "existing_adapter_gate": {
            "best_candidate_id": _str(adapter_summary.get("best_candidate_id"), "adapter best id"),
            "best_candidate_mismatches": _int(adapter_summary.get("best_candidate_mismatches"), "adapter mismatches"),
            "best_candidate_mean_abs_error": _number(
                adapter_summary.get("best_candidate_mean_abs_error"), "adapter mean abs error"
            ),
        },
        "boundary_gate": {
            "status": _str(boundary_summary.get("attention_to_mlp_value_status"), "boundary status"),
            "attention_chain_to_mlp_row_ratio": _number(
                boundary_summary.get("attention_chain_to_mlp_row_ratio"), "boundary row ratio"
            ),
        },
        "decision": {
            "current_fixture_adapter": "NO_GO",
            "reason": "only the index-only synthetic target pattern is exact; checked attention-derived policies miss",
            "next_smallest_experiment": "regenerate a d128 RMSNorm input fixture from attention values, then rerun the RMSNorm-MLP fused proof and boundary gate",
        },
    }


def build_context() -> dict[str, Any]:
    source_payloads: dict[str, dict[str, Any]] = {}
    source_artifacts = []
    for artifact_id, path in SOURCE_ARTIFACTS:
        payload, artifact = source_artifact(artifact_id, path)
        source_payloads[artifact_id] = payload
        source_artifacts.append(artifact)
    frontier = build_policy_frontier(
        source_payloads["attention_d8_bounded_softmax_table"],
        source_payloads["d128_rmsnorm_input"],
        source_payloads["attention_d128_value_adapter_gate"],
        source_payloads["attention_rmsnorm_mlp_boundary_gate"],
    )
    frontier_commitment = commitment(frontier, PAYLOAD_DOMAIN)
    best = _dict(frontier.get("best_admissible_policy"), "best admissible")
    existing = _dict(frontier.get("existing_adapter_gate"), "existing adapter")
    boundary = _dict(frontier.get("boundary_gate"), "boundary")
    policies = {policy["id"]: policy for policy in _list(frontier.get("policies"), "policies")}
    summary = {
        "decision": DECISION,
        "attention_cells": _int(_dict(frontier.get("attention"), "attention").get("flattened_cells"), "attention cells"),
        "target_width": _int(_dict(frontier.get("target"), "target").get("width"), "target width"),
        "best_admissible_policy_id": _str(best.get("id"), "best policy id"),
        "best_admissible_mismatches": _int(best.get("mismatch_count"), "best mismatches"),
        "best_admissible_mean_abs_error": _number(best.get("mean_abs_error"), "best mean abs error"),
        "existing_adapter_best_policy_id": _str(existing.get("best_candidate_id"), "existing policy id"),
        "existing_adapter_best_mismatches": _int(existing.get("best_candidate_mismatches"), "existing mismatches"),
        "index_only_exact_mismatches": _int(
            policies["index_only_synthetic_target_pattern"].get("mismatch_count"), "index-only mismatches"
        ),
        "per_source_cell_lower_bound_mismatches": _int(
            policies["per_source_cell_repeated_lower_bound"].get("mismatch_count"), "lower-bound mismatches"
        ),
        "boundary_status": _str(boundary.get("status"), "boundary status"),
        "policy_frontier_commitment": frontier_commitment,
    }
    return {
        "source_artifacts": source_artifacts,
        "policy_frontier": frontier,
        "policy_frontier_commitment": frontier_commitment,
        "summary": summary,
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    data = context if context is not None else build_context()
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(data["source_artifacts"]),
        "policy_frontier": copy.deepcopy(data["policy_frontier"]),
        "policy_frontier_commitment": data["policy_frontier_commitment"],
        "summary": copy.deepcopy(data["summary"]),
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def _comparable(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "payload_commitment"}


def validate_payload(payload: Any, *, expected: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    key_set = set(data)
    if key_set not in (CORE_KEYS, FINAL_KEYS):
        raise ValueAdapterPolicyFrontierError(f"unexpected payload keys: {sorted(key_set ^ FINAL_KEYS)}")
    for key, expected_value in (
        ("schema", SCHEMA),
        ("decision", DECISION),
        ("result", RESULT),
        ("claim_boundary", CLAIM_BOUNDARY),
    ):
        if data.get(key) != expected_value:
            raise ValueAdapterPolicyFrontierError(f"{key} drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise ValueAdapterPolicyFrontierError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise ValueAdapterPolicyFrontierError("validation command drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise ValueAdapterPolicyFrontierError("payload commitment drift")

    expected_context = context if context is not None else build_context()
    if data.get("source_artifacts") != expected_context["source_artifacts"]:
        raise ValueAdapterPolicyFrontierError("source artifact drift")
    if data.get("policy_frontier") != expected_context["policy_frontier"]:
        raise ValueAdapterPolicyFrontierError("policy frontier drift")
    if data.get("policy_frontier_commitment") != expected_context["policy_frontier_commitment"]:
        raise ValueAdapterPolicyFrontierError("policy frontier commitment drift")
    if data.get("summary") != expected_context["summary"]:
        raise ValueAdapterPolicyFrontierError("summary drift")
    if expected is not None and _comparable(data) != _comparable(expected):
        raise ValueAdapterPolicyFrontierError("payload content drift")

    summary = _dict(data.get("summary"), "summary")
    for key, expected_value in EXPECTED_SUMMARY.items():
        if summary.get(key) != expected_value:
            raise ValueAdapterPolicyFrontierError(f"summary drift: {key}")
    frontier = _dict(data.get("policy_frontier"), "policy frontier")
    if frontier.get("exact_policy_ids") != ["index_only_synthetic_target_pattern"]:
        raise ValueAdapterPolicyFrontierError("exact policy set drift")
    if _dict(frontier.get("decision"), "decision").get("current_fixture_adapter") != "NO_GO":
        raise ValueAdapterPolicyFrontierError("adapter decision overclaim")
    policies = _list(frontier.get("policies"), "policies")
    if len(policies) != 5:
        raise ValueAdapterPolicyFrontierError("policy count drift")
    for policy in policies:
        item = _dict(policy, "policy")
        _str(item.get("id"), "policy id")
        if _int(item.get("mismatch_count"), "policy mismatches") == 0 and item.get("admissible_as_value_adapter") is not False:
            raise ValueAdapterPolicyFrontierError("exact policy admitted as value adapter")
        _number(item.get("mean_abs_error"), "policy mean abs error")
        _list(item.get("first_mismatches"), "policy first mismatches")

    if key_set == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise ValueAdapterPolicyFrontierError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise ValueAdapterPolicyFrontierError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise ValueAdapterPolicyFrontierError("not all mutations rejected")
        names = []
        for index, case_value in enumerate(cases):
            case = _dict(case_value, f"cases[{index}]")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise ValueAdapterPolicyFrontierError("malformed mutation case")
            name = _str(case.get("name"), "case name")
            if name not in EXPECTED_MUTATIONS:
                raise ValueAdapterPolicyFrontierError("unknown mutation case")
            if case.get("accepted") is not False or case.get("rejected") is not True:
                raise ValueAdapterPolicyFrontierError(f"mutation accepted: {name}")
            _str(case.get("error"), "case error")
            names.append(name)
        if names != list(EXPECTED_MUTATIONS):
            raise ValueAdapterPolicyFrontierError("mutation order drift")


MutationFn = Callable[[dict[str, Any]], None]


def refresh_frontier_commitment(payload: dict[str, Any]) -> None:
    payload["policy_frontier_commitment"] = commitment(payload["policy_frontier"], PAYLOAD_DOMAIN)
    payload["summary"]["policy_frontier_commitment"] = payload["policy_frontier_commitment"]
    refresh_payload_commitment(payload)


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted", lambda p: p.__setitem__("decision", "GO_VALUE_DERIVED_ADAPTER"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "VALUE_DERIVED_ADAPTER_EXISTS"), True),
    (
        "best_admissible_mismatch_zeroed",
        lambda p: p["summary"].__setitem__("best_admissible_mismatches", 0),
        True,
    ),
    (
        "index_only_admitted",
        lambda p: p["policy_frontier"]["policies"][4].__setitem__("admissible_as_value_adapter", True),
        True,
    ),
    (
        "exact_policy_removed",
        lambda p: p["policy_frontier"].__setitem__("exact_policy_ids", []),
        True,
    ),
    (
        "adapter_decision_promoted",
        lambda p: p["policy_frontier"]["decision"].__setitem__("current_fixture_adapter", "GO"),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "11" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", lambda p: p.__setitem__("payload_commitment", "sha256:" + "22" * 32), False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutation_cases(core: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core)
        mutator(mutated)
        if refresh:
            if "policy_frontier" in mutated:
                refresh_frontier_commitment(mutated)
            else:
                refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, expected=core, context=context)
        except ValueAdapterPolicyFrontierError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result(context: dict[str, Any] | None = None) -> dict[str, Any]:
    expected_context = context if context is not None else build_context()
    core = build_core_payload(expected_context)
    cases = run_mutation_cases(core, expected_context)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(EXPECTED_MUTATIONS)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final, context=expected_context)
    return final


def to_tsv(payload: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    expected_context = context if context is not None else build_context()
    validate_payload(payload, context=expected_context)
    summary = _dict(payload.get("summary"), "summary")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow({key: summary[key] if key in summary else payload[key] for key in TSV_COLUMNS})
    return output.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = build_context()
    payload = build_gate_result(context)
    outputs = []
    json_path = adapter_gate.require_output_path(args.write_json, ".json")
    tsv_path = adapter_gate.require_output_path(args.write_tsv, ".tsv")
    if json_path is not None:
        outputs.append((json_path, pretty_json(payload), "policy frontier JSON"))
    if tsv_path is not None:
        outputs.append((tsv_path, to_tsv(payload, context), "policy frontier TSV"))
    adapter_gate.write_texts_no_follow(outputs)
    summary = payload["summary"]
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    print(f"mutations_rejected={sum(case['rejected'] for case in payload['cases'])}/{payload['case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
