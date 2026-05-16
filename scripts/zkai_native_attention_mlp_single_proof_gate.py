#!/usr/bin/env python3
"""Gate the native attention-plus-MLP single-proof object probe."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import copy
import csv
import hashlib
import io
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import zkai_native_attention_mlp_single_proof_route_gate as route_gate  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

ENVELOPE_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.envelope.json"
ACCOUNTING_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json"
ROUTE_BUDGET_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-route-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.tsv"

SCHEMA = "zkai-native-attention-mlp-single-proof-object-gate-v1"
DECISION = "GO_NATIVE_ATTENTION_MLP_SINGLE_STWO_PROOF_OBJECT_VERIFIES"
RESULT = "NARROW_CLAIM_SINGLE_PROOF_OBJECT_BARELY_BEATS_TWO_PROOF_FRONTIER"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/603"
CLAIM_BOUNDARY = (
    "ONE_NATIVE_STWO_PROOF_OBJECT_FOR_STATEMENT_BOUND_D8_ATTENTION_AND_ATTENTION_DERIVED_"
    "D128_RMSNORM_MLP_SURFACES_WITHOUT_NATIVE_ADAPTER_AIR_OR_NANOZK_COMPARABILITY"
)
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-single-proof-object:v1"

EXPECTED = {
    "proof_backend_version": "stwo-native-attention-mlp-single-proof-object-probe-v1",
    "proof_schema_version": "stwo-native-attention-mlp-single-proof-object-payload-v1",
    "statement_version": "zkai-native-attention-mlp-single-proof-object-statement-v1",
    "target_id": "attention-kv-d8-fused-softmax-table-plus-attention-derived-d128-rmsnorm-mlp-v1",
    "verifier_domain": "ptvm:zkai:native-attention-mlp-single-proof-object:v1",
    "adapter_status": "STATEMENT_BOUND_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER_NOT_NATIVE_AIR",
    "pcs_lifting_log_size": 19,
    "single_proof_json_bytes": 115_924,
    "single_proof_typed_bytes": 40_668,
    "single_envelope_bytes": 1_222_508,
    "two_proof_frontier_json_bytes": 116_258,
    "two_proof_frontier_typed_bytes": 40_700,
    "attention_fused_typed_bytes": 18_124,
    "derived_mlp_fused_typed_bytes": 22_576,
    "nanozk_reported_d128_block_proof_bytes": 6_900,
}

NON_CLAIMS = (
    "not a native AIR proof of the attention-output-to-d128-input adapter",
    "not a full transformer block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not exact real-valued Softmax",
    "not full autoregressive inference",
    "not recursion or proof-carrying data",
    "not timing evidence",
    "not production-ready zkML",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "claim_boundary",
    "source_artifacts",
    "routes",
    "summary",
    "mechanism",
    "non_claims",
    "validation_commands",
    "route_commitment",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_result", "mutation_inventory"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "decision",
    "result",
    "single_proof_typed_bytes",
    "two_proof_frontier_typed_bytes",
    "typed_saving_vs_two_proof_bytes",
    "typed_ratio_vs_two_proof",
    "single_proof_json_bytes",
    "two_proof_frontier_json_bytes",
    "json_saving_vs_two_proof_bytes",
    "json_ratio_vs_two_proof",
    "pcs_lifting_log_size",
    "native_adapter_air_proven",
    "typed_gap_to_nanozk_reported_bytes",
    "typed_reduction_needed_to_nanozk_reported_share",
)

MUTATION_NAMES = (
    "single_typed_bytes_drift",
    "two_proof_frontier_drift",
    "proof_json_bytes_drift",
    "adapter_promoted_to_native_air",
    "pcs_lifting_log_size_drift",
    "nanozk_win_promoted",
    "route_commitment_drift",
    "payload_commitment_drift",
    "missing_non_claim",
)

EXPECTED_MUTATION_REASONS = {
    "single_typed_bytes_drift": "summary drift",
    "two_proof_frontier_drift": "summary drift",
    "proof_json_bytes_drift": "summary drift",
    "adapter_promoted_to_native_air": "routes drift",
    "pcs_lifting_log_size_drift": "summary drift",
    "nanozk_win_promoted": "routes drift",
    "route_commitment_drift": "route commitment drift",
    "payload_commitment_drift": "payload commitment drift",
    "missing_non_claim": "non-claims drift",
}


class NativeAttentionMlpSingleProofGateError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise NativeAttentionMlpSingleProofGateError(f"invalid JSON value: {err}") from err


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise NativeAttentionMlpSingleProofGateError("ratio denominator must be positive")
    return round(numerator / denominator, 6)


def route_commitment(routes: dict[str, Any]) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(PAYLOAD_DOMAIN.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(routes))
    return "blake2b-256:" + digest.hexdigest()


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def refresh_routes_and_payload(payload: dict[str, Any]) -> None:
    payload["route_commitment"] = route_commitment(payload["routes"])
    refresh_payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeAttentionMlpSingleProofGateError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeAttentionMlpSingleProofGateError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeAttentionMlpSingleProofGateError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NativeAttentionMlpSingleProofGateError(f"{label} must be integer")
    return value


def _bytes(value: Any, label: str) -> bytes:
    if not isinstance(value, bytes):
        raise NativeAttentionMlpSingleProofGateError(f"{label} must be bytes")
    return value


def _str_list(value: Any, label: str) -> list[str]:
    items = _list(value, label)
    result = []
    for index, item in enumerate(items):
        result.append(_str(item, f"{label}[{index}]"))
    return result


def read_json(path: pathlib.Path, label: str) -> Any:
    try:
        payload, _raw = route_gate.read_json_and_raw_bytes(path, label)
        return payload
    except route_gate.NativeAttentionMlpSingleProofRouteError as err:
        raise NativeAttentionMlpSingleProofGateError(str(err)) from err


def build_context() -> dict[str, Any]:
    try:
        envelope, envelope_raw = route_gate.read_json_and_raw_bytes(ENVELOPE_PATH, "single proof envelope")
        accounting, _accounting_raw = route_gate.read_json_and_raw_bytes(ACCOUNTING_PATH, "single proof accounting")
        route_budget, _route_budget_raw = route_gate.read_json_and_raw_bytes(ROUTE_BUDGET_PATH, "route budget")
    except route_gate.NativeAttentionMlpSingleProofRouteError as err:
        raise NativeAttentionMlpSingleProofGateError(str(err)) from err
    return {
        "envelope": _dict(envelope, "single proof envelope"),
        "envelope_raw_bytes": envelope_raw,
        "accounting": _dict(accounting, "single proof accounting"),
        "route_budget": _dict(route_budget, "route budget"),
    }


def accounting_row(accounting: dict[str, Any]) -> dict[str, Any]:
    rows = _list(accounting.get("rows"), "accounting rows")
    if len(rows) != 1:
        raise NativeAttentionMlpSingleProofGateError(f"expected one accounting row, got {len(rows)}")
    return _dict(rows[0], "single accounting row")


def build_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    payload = build_payload_no_mutations(context)
    payload["mutation_result"] = mutation_result_placeholder()
    payload["mutation_inventory"] = {"cases": list(MUTATION_NAMES)}
    refresh_routes_and_payload(payload)
    validate_payload(payload, context=context)
    payload["mutation_result"] = mutation_result(payload, context)
    refresh_routes_and_payload(payload)
    validate_payload(payload, context=context)
    return payload


def source_artifacts() -> list[dict[str, Any]]:
    artifacts = []
    for artifact_id, path in (
        ("single_proof_envelope", ENVELOPE_PATH),
        ("single_proof_binary_accounting", ACCOUNTING_PATH),
        ("single_proof_route_budget", ROUTE_BUDGET_PATH),
    ):
        _payload, raw = route_gate.read_json_and_raw_bytes(path, artifact_id)
        artifacts.append(
            {
                "id": artifact_id,
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return artifacts


def validate_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    context = build_context() if context is None else context
    if set(payload) != FINAL_KEYS:
        raise NativeAttentionMlpSingleProofGateError("top-level key drift")
    for key, expected in (
        ("schema", SCHEMA),
        ("decision", DECISION),
        ("result", RESULT),
        ("issue", ISSUE),
        ("claim_boundary", CLAIM_BOUNDARY),
    ):
        if payload.get(key) != expected:
            raise NativeAttentionMlpSingleProofGateError(f"{key} drift")
    if payload.get("non_claims") != list(NON_CLAIMS):
        raise NativeAttentionMlpSingleProofGateError("non-claims drift")
    expected_payload = build_payload_without_mutations(context)
    for key in ("source_artifacts", "routes", "summary", "mechanism", "validation_commands"):
        if payload.get(key) != expected_payload[key]:
            raise NativeAttentionMlpSingleProofGateError(f"{key} drift")
    if payload.get("route_commitment") != route_commitment(payload["routes"]):
        raise NativeAttentionMlpSingleProofGateError("route commitment drift")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise NativeAttentionMlpSingleProofGateError("payload commitment drift")
    mutation = _dict(payload.get("mutation_result"), "mutation result")
    cases = _list(mutation.get("cases"), "mutation cases")
    if [case.get("name") for case in cases] != list(MUTATION_NAMES):
        raise NativeAttentionMlpSingleProofGateError("mutation inventory drift")
    if not all(case.get("rejected") is True for case in cases):
        raise NativeAttentionMlpSingleProofGateError("mutation rejection drift")
    for case in cases:
        name = _str(case.get("name"), "mutation name")
        reason = _str(case.get("reason"), "mutation rejection reason")
        if reason != EXPECTED_MUTATION_REASONS.get(name):
            raise NativeAttentionMlpSingleProofGateError(
                f"mutation reason drift for {name}: got {reason!r}, expected {EXPECTED_MUTATION_REASONS.get(name)!r}"
            )
    if payload.get("mutation_inventory") != {"cases": list(MUTATION_NAMES)}:
        raise NativeAttentionMlpSingleProofGateError("mutation inventory drift")


def build_payload_without_mutations(context: dict[str, Any]) -> dict[str, Any]:
    payload = build_payload_no_mutations(context)
    payload["mutation_result"] = {"cases": []}
    payload["mutation_inventory"] = {"cases": list(MUTATION_NAMES)}
    refresh_routes_and_payload(payload)
    return payload


def build_payload_no_mutations(context: dict[str, Any]) -> dict[str, Any]:
    envelope = _dict(context["envelope"], "envelope")
    input_payload = _dict(envelope.get("input"), "envelope input")
    row = accounting_row(_dict(context["accounting"], "accounting"))
    route_budget = _dict(context["route_budget"], "route budget")
    route_budget_routes = _dict(route_budget.get("routes"), "route budget routes")
    current_two_proof_frontier = _dict(
        route_budget_routes.get("current_two_proof_frontier"),
        "route budget current two-proof frontier",
    )
    local = _dict(row.get("local_binary_accounting"), "local binary accounting")
    metadata = _dict(row.get("envelope_metadata"), "envelope metadata")
    validation_commands = _str_list(input_payload.get("validation_commands"), "input validation commands")
    envelope_bytes = len(_bytes(context.get("envelope_raw_bytes"), "single envelope raw bytes"))
    single_typed = _int(local.get("typed_size_estimate_bytes"), "single typed bytes")
    single_json = _int(row.get("proof_json_size_bytes"), "single JSON proof bytes")
    two_typed = _int(input_payload.get("current_two_proof_frontier_typed_bytes"), "two proof typed bytes")
    two_json = _int(
        current_two_proof_frontier.get("current_two_proof_json_proof_bytes"),
        "two proof frontier JSON bytes",
    )
    nanozk = _int(input_payload.get("nanozk_reported_d128_block_proof_bytes"), "NANOZK reported bytes")
    typed_gap_to_nanozk = single_typed - nanozk
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": source_artifacts(),
        "routes": {
            "native_single_proof_object": {
                "status": "GO_VERIFIED_SINGLE_NATIVE_STWO_PROOF_OBJECT",
                "proof_backend_version": metadata["proof_backend_version"],
                "proof_schema_version": metadata["proof_schema_version"],
                "statement_version": metadata["statement_version"],
                "proof_json_size_bytes": single_json,
                "typed_size_estimate_bytes": single_typed,
                "pcs_lifting_log_size": input_payload["pcs_lifting_log_size"],
            },
            "two_proof_frontier_comparison": {
                "status": "BARELY_GO_BEATS_CURRENT_TWO_PROOF_TYPED_TARGET",
                "two_proof_frontier_typed_bytes": two_typed,
                "typed_saving_bytes": two_typed - single_typed,
                "typed_ratio": ratio(single_typed, two_typed),
                "two_proof_frontier_json_bytes": two_json,
                "json_saving_bytes": two_json - single_json,
                "json_ratio": ratio(single_json, two_json),
            },
            "adapter_boundary": {
                "status": "NO_GO_NATIVE_ADAPTER_AIR_NOT_PROVEN",
                "adapter_status": input_payload["adapter_status"],
                "native_adapter_air_proven": False,
            },
            "nanozk_comparison_boundary": {
                "status": "NO_GO_NOT_NANOZK_COMPARABLE",
                "nanozk_reported_d128_block_proof_bytes": nanozk,
                "typed_gap_to_nanozk_reported_bytes": typed_gap_to_nanozk,
                "matched_workload_or_object_class": False,
                "proof_size_win_claimed": False,
            },
        },
        "summary": {
            "single_proof_typed_bytes": single_typed,
            "two_proof_frontier_typed_bytes": two_typed,
            "typed_saving_vs_two_proof_bytes": two_typed - single_typed,
            "typed_ratio_vs_two_proof": ratio(single_typed, two_typed),
            "single_proof_json_bytes": single_json,
            "two_proof_frontier_json_bytes": two_json,
            "json_saving_vs_two_proof_bytes": two_json - single_json,
            "json_ratio_vs_two_proof": ratio(single_json, two_json),
            "single_envelope_bytes": envelope_bytes,
            "pcs_lifting_log_size": input_payload["pcs_lifting_log_size"],
            "attention_fused_typed_bytes": input_payload["current_attention_fused_typed_bytes"],
            "derived_mlp_fused_typed_bytes": input_payload["current_derived_mlp_fused_typed_bytes"],
            "adapter_status": input_payload["adapter_status"],
            "native_adapter_air_proven": False,
            "nanozk_reported_d128_block_proof_bytes": nanozk,
            "typed_gap_to_nanozk_reported_bytes": typed_gap_to_nanozk,
            "typed_reduction_needed_to_nanozk_reported_share": ratio(typed_gap_to_nanozk, single_typed),
        },
        "mechanism": {
            "single_proof_object_mechanism": (
                "attention LogUp interaction trace and six d128 RMSNorm-MLP components are proved "
                "under one Stwo proof object with shared PCS/Fri plumbing"
            ),
            "explicit_lifting_reason": (
                "the attention interaction tree is much smaller than the MLP base tree, so the route "
                "pins an explicit PCS lifting log size instead of relying on publication-v1 None"
            ),
            "research_signal": "the first verified one-proof object saves 32 typed bytes versus the two-proof frontier",
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": validation_commands,
        "route_commitment": "",
        "payload_commitment": "",
    }
    refresh_routes_and_payload(payload)
    return payload


def validate_context(context: dict[str, Any]) -> None:
    envelope = _dict(context["envelope"], "envelope")
    input_payload = _dict(envelope.get("input"), "envelope input")
    row = accounting_row(_dict(context["accounting"], "accounting"))
    route_budget = _dict(context["route_budget"], "route budget")
    route_budget_routes = _dict(route_budget.get("routes"), "route budget routes")
    current_two_proof_frontier = _dict(
        route_budget_routes.get("current_two_proof_frontier"),
        "route budget current two-proof frontier",
    )
    local = _dict(row.get("local_binary_accounting"), "local binary accounting")
    metadata = _dict(row.get("envelope_metadata"), "envelope metadata")
    _str_list(input_payload.get("validation_commands"), "input validation commands")
    checks = {
        "proof_backend_version": envelope.get("proof_backend_version"),
        "proof_schema_version": envelope.get("proof_schema_version"),
        "statement_version": envelope.get("statement_version"),
        "target_id": envelope.get("target_id"),
        "verifier_domain": envelope.get("verifier_domain"),
        "adapter_status": input_payload.get("adapter_status"),
        "pcs_lifting_log_size": input_payload.get("pcs_lifting_log_size"),
        "single_proof_json_bytes": len(_list(envelope.get("proof"), "proof byte array")),
        "single_envelope_bytes": len(_bytes(context.get("envelope_raw_bytes"), "single envelope raw bytes")),
        "single_proof_typed_bytes": local.get("typed_size_estimate_bytes"),
        "attention_fused_typed_bytes": input_payload.get("current_attention_fused_typed_bytes"),
        "derived_mlp_fused_typed_bytes": input_payload.get("current_derived_mlp_fused_typed_bytes"),
        "two_proof_frontier_typed_bytes": input_payload.get("current_two_proof_frontier_typed_bytes"),
        "two_proof_frontier_json_bytes": current_two_proof_frontier.get("current_two_proof_json_proof_bytes"),
        "nanozk_reported_d128_block_proof_bytes": input_payload.get("nanozk_reported_d128_block_proof_bytes"),
    }
    for key, expected in EXPECTED.items():
        if checks.get(key) != expected:
            raise NativeAttentionMlpSingleProofGateError(
                f"context {key} drift: got {checks.get(key)!r}, expected {expected!r}"
            )
    if metadata.get("proof_backend_version") != EXPECTED["proof_backend_version"]:
        raise NativeAttentionMlpSingleProofGateError("accounting metadata proof backend drift")
    if row.get("proof_json_size_bytes") != EXPECTED["single_proof_json_bytes"]:
        raise NativeAttentionMlpSingleProofGateError("accounting proof JSON bytes drift")
    if local.get("component_sum_bytes") != local.get("typed_size_estimate_bytes"):
        raise NativeAttentionMlpSingleProofGateError("typed accounting component sum drift")
    if EXPECTED["two_proof_frontier_typed_bytes"] - EXPECTED["single_proof_typed_bytes"] != 32:
        raise NativeAttentionMlpSingleProofGateError("expected 32-byte typed saving drift")


def mutation_result_placeholder() -> dict[str, Any]:
    return {
        "cases": [
            {
                "name": name,
                "rejected": True,
                "reason": EXPECTED_MUTATION_REASONS[name],
            }
            for name in MUTATION_NAMES
        ]
    }


def mutation_result(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for name, mutator in mutation_cases():
        candidate = copy.deepcopy(payload)
        mutator(candidate)
        try:
            validate_payload(candidate, context=context)
        except NativeAttentionMlpSingleProofGateError as err:
            cases.append({"name": name, "rejected": True, "reason": str(err)})
        else:
            cases.append({"name": name, "rejected": False, "reason": "mutation accepted"})
    return {"cases": cases}


def mutation_cases() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    return [
        ("single_typed_bytes_drift", lambda p: p["summary"].__setitem__("single_proof_typed_bytes", 40_701)),
        ("two_proof_frontier_drift", lambda p: p["summary"].__setitem__("two_proof_frontier_typed_bytes", 40_699)),
        ("proof_json_bytes_drift", lambda p: p["summary"].__setitem__("single_proof_json_bytes", 116_258)),
        ("adapter_promoted_to_native_air", lambda p: p["routes"]["adapter_boundary"].__setitem__("native_adapter_air_proven", True)),
        ("pcs_lifting_log_size_drift", lambda p: p["summary"].__setitem__("pcs_lifting_log_size", 0)),
        ("nanozk_win_promoted", lambda p: p["routes"]["nanozk_comparison_boundary"].__setitem__("proof_size_win_claimed", True)),
        ("route_commitment_drift", lambda p: p.__setitem__("route_commitment", "blake2b-256:" + "0" * 64)),
        ("payload_commitment_drift", lambda p: p.__setitem__("payload_commitment", "sha256:" + "1" * 64)),
        ("missing_non_claim", lambda p: p["non_claims"].pop()),
    ]


def to_tsv(payload: dict[str, Any], context: dict[str, Any]) -> str:
    validate_payload(payload, context=context)
    summary = payload["summary"]
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        **{key: summary[key] for key in TSV_COLUMNS if key in summary},
    }
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, extrasaction="ignore", delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_tsv(path: pathlib.Path, payload: dict[str, Any], context: dict[str, Any]) -> None:
    path.write_text(to_tsv(payload, context), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args()
    context = build_context()
    validate_context(context)
    payload = build_payload(context)
    validate_payload(payload, context=context)
    if args.write_json:
        output = route_gate.attribution_gate.resolve_evidence_output_path(args.write_json, "single proof JSON")
        write_json(output, payload)
    if args.write_tsv:
        output = route_gate.attribution_gate.resolve_evidence_output_path(args.write_tsv, "single proof TSV")
        write_tsv(output, payload, context)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
