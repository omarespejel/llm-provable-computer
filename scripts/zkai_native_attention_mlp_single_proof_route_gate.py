#!/usr/bin/env python3
"""Gate the native attention-plus-MLP single-proof route budget."""

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

from scripts import zkai_attention_derived_d128_mlp_fusion_attribution_gate as attribution_gate  # noqa: E402
from scripts import zkai_attention_derived_d128_native_mlp_proof_route_gate as mlp_route_gate  # noqa: E402
from scripts import zkai_d128_attention_mlp_boundary_frontier_gate as boundary_frontier_gate  # noqa: E402


EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
MAX_SOURCE_BYTES = 16 * 1024 * 1024

BOUNDARY_FRONTIER_PATH = EVIDENCE_DIR / "zkai-d128-attention-mlp-boundary-frontier-2026-05.json"
MLP_ROUTE_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json"
MLP_ATTRIBUTION_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-mlp-fusion-attribution-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-route-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-route-2026-05.tsv"

SCHEMA = "zkai-native-attention-mlp-single-proof-route-gate-v1"
DECISION = "GO_ROUTE_BUDGET_FOR_NATIVE_ATTENTION_MLP_SINGLE_PROOF_OBJECT"
RESULT = "NARROW_CLAIM_IMPLEMENTATION_TARGET_PINNED_NO_NATIVE_PROOF_OBJECT_YET"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/603"
CLAIM_BOUNDARY = (
    "PINS_THE_NEXT_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_TARGET_WITHOUT_CLAIMING_"
    "THE_OBJECT_EXISTS_OR_THAT_THE_ROUTE_IS_NANOZK_COMPARABLE"
)
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-single-proof-route:v1"
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900

EXPECTED_FRONTIER = {
    "attention_fused_typed_bytes": 18_124,
    "derived_mlp_fused_typed_bytes": 22_576,
    "two_proof_frontier_typed_bytes": 40_700,
    "two_proof_frontier_json_proof_bytes": 116_258,
    "six_separate_mlp_plus_attention_fused_typed_bytes": 77_468,
    "typed_saving_vs_six_separate_mlp_plus_attention_fused_bytes": 36_768,
    "typed_ratio_vs_six_separate_mlp_plus_attention_fused": 0.525378,
    "typed_gap_to_nanozk_reported_bytes": 33_800,
    "typed_reduction_needed_to_nanozk_reported_share": 0.830467,
    "single_native_attention_mlp_status": "NO_GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_MISSING",
}

EXPECTED_MLP_ROUTE = {
    "value_connected_chain_rows": 199_553,
    "current_mlp_fused_rows": 197_504,
    "row_ratio": 1.010374,
    "derived_fused_typed_bytes": 22_576,
    "derived_fused_proof_bytes": 68_560,
    "typed_saving_vs_available_separate_bytes": 36_768,
    "json_saving_vs_available_separate_bytes": 130_377,
    "go_result": "GO for a value-connected attention-derived d128 statement chain",
    "proof_result": "GO for a regenerated attention-derived native RMSNorm-MLP fused proof",
    "remaining_no_go_result": "NO-GO for attention plus MLP in one native proof object or matched external benchmark",
}

EXPECTED_ATTRIBUTION = {
    "opening_plumbing_saved_bytes": 33_280,
    "opening_plumbing_share": 0.905135,
    "largest_saved_group": "fri_decommitments",
    "largest_saved_group_bytes": 20_512,
    "compression_probe_result": "NO_GO_DROP_FRI_DECOMMITMENTS_WOULD_DROP_VERIFIER_OPENING_WITNESS",
}

NON_CLAIMS = (
    "not a native attention plus MLP proof object",
    "not proof that one native boundary will be 22,576 typed bytes",
    "not a full transformer block proof",
    "not a NANOZK proof-size win",
    "not a matched NANOZK workload or benchmark",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_native_attention_mlp_single_proof_route_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-single-proof-route-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_attention_mlp_single_proof_route_gate.py scripts/tests/test_zkai_native_attention_mlp_single_proof_route_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_single_proof_route_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
)

SOURCE_ARTIFACTS = (
    ("attention_mlp_boundary_frontier", BOUNDARY_FRONTIER_PATH),
    ("attention_derived_native_mlp_route", MLP_ROUTE_PATH),
    ("attention_derived_mlp_fusion_attribution", MLP_ATTRIBUTION_PATH),
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
    "current_two_proof_typed_bytes",
    "attention_proof_typed_bytes_available_to_remove",
    "mlp_surface_floor_typed_bytes",
    "mlp_surface_floor_ratio_vs_two_proof",
    "value_connected_chain_to_mlp_row_ratio",
    "native_proof_success_threshold_typed_bytes",
    "nanozk_gap_after_mlp_surface_floor_bytes",
    "one_native_proof_exists",
)


class NativeAttentionMlpSingleProofRouteError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise NativeAttentionMlpSingleProofRouteError(f"invalid JSON value: {err}") from err


def ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        raise NativeAttentionMlpSingleProofRouteError("ratio denominator is zero")
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
        raise NativeAttentionMlpSingleProofRouteError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeAttentionMlpSingleProofRouteError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeAttentionMlpSingleProofRouteError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NativeAttentionMlpSingleProofRouteError(f"{label} must be integer")
    return value


def _number(value: Any, label: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise NativeAttentionMlpSingleProofRouteError(f"{label} must be number")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise NativeAttentionMlpSingleProofRouteError(f"{label} must be boolean")
    return value


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        return boundary_frontier_gate.load_json(path, label)
    except Exception as err:  # noqa: BLE001 - normalize imported gate errors.
        raise NativeAttentionMlpSingleProofRouteError(f"failed loading {label}: {err}") from err


def source_artifact(artifact_id: str, path: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = load_json(path, artifact_id)
    raw = path.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise NativeAttentionMlpSingleProofRouteError(f"{artifact_id} too large: {len(raw)} bytes")
    return (
        payload,
        {
            "id": artifact_id,
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        },
    )


def validate_sources(payloads: dict[str, Any]) -> None:
    frontier = _dict(payloads["attention_mlp_boundary_frontier"], "frontier payload")
    mlp_route = _dict(payloads["attention_derived_native_mlp_route"], "MLP route payload")
    attribution = _dict(payloads["attention_derived_mlp_fusion_attribution"], "MLP attribution payload")
    try:
        boundary_frontier_gate.validate_payload(frontier)
        mlp_route_gate.validate_payload(mlp_route)
        attribution_gate.validate_payload(attribution)
    except Exception as err:  # noqa: BLE001 - normalize dependent gate errors.
        raise NativeAttentionMlpSingleProofRouteError(f"dependent gate validation failed: {err}") from err

    frontier_summary = _dict(frontier.get("summary"), "frontier summary")
    for key, expected in EXPECTED_FRONTIER.items():
        if frontier_summary.get(key) != expected:
            raise NativeAttentionMlpSingleProofRouteError(f"frontier summary drift: {key}")
    mlp_summary = _dict(mlp_route.get("summary"), "MLP route summary")
    for key, expected in EXPECTED_MLP_ROUTE.items():
        if mlp_summary.get(key) != expected:
            raise NativeAttentionMlpSingleProofRouteError(f"MLP route summary drift: {key}")
    attribution_summary = _dict(attribution.get("summary"), "attribution summary")
    for key, expected in EXPECTED_ATTRIBUTION.items():
        if attribution_summary.get(key) != expected:
            raise NativeAttentionMlpSingleProofRouteError(f"attribution summary drift: {key}")


def build_context() -> dict[str, Any]:
    payloads: dict[str, dict[str, Any]] = {}
    artifacts = []
    for artifact_id, path in SOURCE_ARTIFACTS:
        payload, artifact = source_artifact(artifact_id, path)
        payloads[artifact_id] = payload
        artifacts.append(artifact)
    validate_sources(payloads)
    return {"payloads": payloads, "source_artifacts": artifacts}


def build_routes(context: dict[str, Any]) -> dict[str, Any]:
    payloads = context["payloads"]
    frontier_summary = _dict(payloads["attention_mlp_boundary_frontier"].get("summary"), "frontier summary")
    mlp_summary = _dict(payloads["attention_derived_native_mlp_route"].get("summary"), "MLP route summary")
    attribution_summary = _dict(payloads["attention_derived_mlp_fusion_attribution"].get("summary"), "attribution")

    two_proof_typed = _int(frontier_summary["two_proof_frontier_typed_bytes"], "two-proof typed bytes")
    attention_typed = _int(frontier_summary["attention_fused_typed_bytes"], "attention typed bytes")
    mlp_typed = _int(frontier_summary["derived_mlp_fused_typed_bytes"], "MLP typed bytes")
    nano_gap_after_mlp_floor = mlp_typed - NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES
    if nano_gap_after_mlp_floor <= 0:
        raise NativeAttentionMlpSingleProofRouteError("unexpected NANOZK floor gap non-positive")
    if two_proof_typed != attention_typed + mlp_typed:
        raise NativeAttentionMlpSingleProofRouteError("two-proof typed arithmetic drift")

    return {
        "current_two_proof_frontier": {
            "status": "BASELINE_CURRENT_VALUE_CONNECTED_TWO_PROOF_TARGET",
            "current_two_proof_typed_bytes": two_proof_typed,
            "attention_fused_typed_bytes": attention_typed,
            "derived_mlp_fused_typed_bytes": mlp_typed,
            "current_two_proof_json_proof_bytes": _int(
                frontier_summary["two_proof_frontier_json_proof_bytes"], "two-proof JSON bytes"
            ),
            "single_native_status": _str(
                frontier_summary["single_native_attention_mlp_status"], "single native status"
            ),
        },
        "native_single_proof_route_budget": {
            "status": "GO_BUILD_ROUTE_BUT_NO_PROOF_OBJECT_EXISTS_YET",
            "success_threshold": "native proof verifies locally and typed bytes are below the current two-proof target",
            "native_proof_success_threshold_typed_bytes": two_proof_typed,
            "attention_proof_typed_bytes_available_to_remove": attention_typed,
            "mlp_surface_floor_typed_bytes": mlp_typed,
            "mlp_surface_floor_ratio_vs_two_proof": ratio(mlp_typed, two_proof_typed),
            "typed_saving_if_mlp_surface_floor_holds_bytes": attention_typed,
            "typed_saving_if_mlp_surface_floor_holds_share": ratio(attention_typed, two_proof_typed),
            "value_connected_chain_rows": _int(mlp_summary["value_connected_chain_rows"], "chain rows"),
            "mlp_fused_rows": _int(mlp_summary["current_mlp_fused_rows"], "MLP rows"),
            "value_connected_chain_extra_rows": _int(mlp_summary["value_connected_chain_rows"], "chain rows")
            - _int(mlp_summary["current_mlp_fused_rows"], "MLP rows"),
            "value_connected_chain_to_mlp_row_ratio": _number(mlp_summary["row_ratio"], "row ratio"),
            "one_native_proof_exists": False,
        },
        "nanozk_comparison_boundary": {
            "status": "NO_GO_NOT_MATCHED_NANOZK_COMPARISON",
            "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
            "two_proof_gap_to_nanozk_reported_bytes": _int(
                frontier_summary["typed_gap_to_nanozk_reported_bytes"], "two-proof NANOZK gap"
            ),
            "nanozk_gap_after_mlp_surface_floor_bytes": nano_gap_after_mlp_floor,
            "nanozk_reduction_needed_after_mlp_surface_floor_share": ratio(nano_gap_after_mlp_floor, mlp_typed),
            "matched_workload_or_object_class": False,
        },
        "mechanism_prior": {
            "status": "EVIDENCE_POINTS_TO_SHARED_OPENING_PLUMBING_NOT_DROPPED_VERIFIER_WITNESS",
            "mlp_fusion_typed_saving_bytes": _int(
                mlp_summary["typed_saving_vs_available_separate_bytes"], "MLP saving"
            ),
            "opening_plumbing_saved_bytes": _int(
                attribution_summary["opening_plumbing_saved_bytes"], "opening plumbing saving"
            ),
            "opening_plumbing_saved_share": _number(
                attribution_summary["opening_plumbing_share"], "opening plumbing share"
            ),
            "compression_probe_result": _str(
                attribution_summary["compression_probe_result"], "compression probe"
            ),
        },
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    data = context if context is not None else build_context()
    routes = build_routes(data)
    budget = routes["native_single_proof_route_budget"]
    nanozk = routes["nanozk_comparison_boundary"]
    summary = {
        "current_two_proof_typed_bytes": routes["current_two_proof_frontier"]["current_two_proof_typed_bytes"],
        "attention_proof_typed_bytes_available_to_remove": budget["attention_proof_typed_bytes_available_to_remove"],
        "mlp_surface_floor_typed_bytes": budget["mlp_surface_floor_typed_bytes"],
        "mlp_surface_floor_ratio_vs_two_proof": budget["mlp_surface_floor_ratio_vs_two_proof"],
        "typed_saving_if_mlp_surface_floor_holds_bytes": budget["typed_saving_if_mlp_surface_floor_holds_bytes"],
        "typed_saving_if_mlp_surface_floor_holds_share": budget["typed_saving_if_mlp_surface_floor_holds_share"],
        "value_connected_chain_extra_rows": budget["value_connected_chain_extra_rows"],
        "value_connected_chain_to_mlp_row_ratio": budget["value_connected_chain_to_mlp_row_ratio"],
        "native_proof_success_threshold_typed_bytes": budget["native_proof_success_threshold_typed_bytes"],
        "nanozk_gap_after_mlp_surface_floor_bytes": nanozk["nanozk_gap_after_mlp_surface_floor_bytes"],
        "nanozk_reduction_needed_after_mlp_surface_floor_share": nanozk[
            "nanozk_reduction_needed_after_mlp_surface_floor_share"
        ],
        "one_native_proof_exists": False,
    }
    mechanism = {
        "why_this_is_next": (
            "the value-connected derived MLP route already verifies, but the attention proof and MLP proof are still "
            "two proof objects"
        ),
        "first_success_gate": "one native proof object verifies locally and beats 40,700 typed bytes",
        "hard_external_comparison_gate": (
            "after a native proof object exists, compare matched workload/object class against external systems"
        ),
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(data["source_artifacts"]),
        "routes": routes,
        "summary": summary,
        "mechanism": mechanism,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
        "route_commitment": route_commitment(routes),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any, *, expected: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    key_set = set(data)
    if key_set not in (CORE_KEYS, FINAL_KEYS):
        raise NativeAttentionMlpSingleProofRouteError(f"unexpected payload keys: {sorted(key_set ^ FINAL_KEYS)}")
    for key, expected_value in (
        ("schema", SCHEMA),
        ("decision", DECISION),
        ("result", RESULT),
        ("issue", ISSUE),
        ("claim_boundary", CLAIM_BOUNDARY),
    ):
        if data.get(key) != expected_value:
            raise NativeAttentionMlpSingleProofRouteError(f"{key} drift")
    if data.get("non_claims") != list(NON_CLAIMS):
        raise NativeAttentionMlpSingleProofRouteError("non-claims drift")
    if data.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise NativeAttentionMlpSingleProofRouteError("validation command drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise NativeAttentionMlpSingleProofRouteError("payload commitment drift")

    expected_context = context if context is not None else build_context()
    expected_core = expected if expected is not None else build_core_payload(expected_context)
    if data.get("source_artifacts") != expected_context["source_artifacts"]:
        raise NativeAttentionMlpSingleProofRouteError("source artifact drift")
    if data.get("routes") != expected_core["routes"]:
        raise NativeAttentionMlpSingleProofRouteError("route drift")
    if data.get("summary") != expected_core["summary"]:
        raise NativeAttentionMlpSingleProofRouteError("summary drift")
    if data.get("mechanism") != expected_core["mechanism"]:
        raise NativeAttentionMlpSingleProofRouteError("mechanism drift")
    if data.get("route_commitment") != route_commitment(_dict(data.get("routes"), "routes")):
        raise NativeAttentionMlpSingleProofRouteError("route commitment drift")

    summary = _dict(data.get("summary"), "summary")
    if _int(summary.get("current_two_proof_typed_bytes"), "two-proof typed") != 40_700:
        raise NativeAttentionMlpSingleProofRouteError("two-proof target drift")
    if _int(summary.get("native_proof_success_threshold_typed_bytes"), "success threshold") != 40_700:
        raise NativeAttentionMlpSingleProofRouteError("success threshold drift")
    if _bool(summary.get("one_native_proof_exists"), "one native exists") is not False:
        raise NativeAttentionMlpSingleProofRouteError("native proof existence overclaim")
    if _int(summary.get("nanozk_gap_after_mlp_surface_floor_bytes"), "NANOZK floor gap") <= 0:
        raise NativeAttentionMlpSingleProofRouteError("NANOZK floor overclaim")

    routes = _dict(data.get("routes"), "routes")
    budget = _dict(routes.get("native_single_proof_route_budget"), "native budget route")
    if budget.get("one_native_proof_exists") is not False:
        raise NativeAttentionMlpSingleProofRouteError("route native proof existence overclaim")
    nanozk = _dict(routes.get("nanozk_comparison_boundary"), "NANOZK route")
    if nanozk.get("status") != "NO_GO_NOT_MATCHED_NANOZK_COMPARISON":
        raise NativeAttentionMlpSingleProofRouteError("NANOZK route overclaim")
    if nanozk.get("matched_workload_or_object_class") is not False:
        raise NativeAttentionMlpSingleProofRouteError("NANOZK matched-object overclaim")

    if key_set == FINAL_KEYS:
        mutation_result = _dict(data.get("mutation_result"), "mutation result")
        inventory = _dict(data.get("mutation_inventory"), "mutation inventory")
        cases = _list(mutation_result.get("cases"), "mutation cases")
        if inventory.get("cases") != list(MUTATION_NAMES):
            raise NativeAttentionMlpSingleProofRouteError("mutation inventory drift")
        if inventory.get("case_count") != len(MUTATION_NAMES):
            raise NativeAttentionMlpSingleProofRouteError("mutation count drift")
        if inventory.get("all_mutations_rejected") is not True:
            raise NativeAttentionMlpSingleProofRouteError("mutation inventory not all rejected")
        if mutation_result.get("all_mutations_rejected") is not True:
            raise NativeAttentionMlpSingleProofRouteError("not all mutations rejected")
        names = []
        for index, value in enumerate(cases):
            case = _dict(value, f"mutation case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise NativeAttentionMlpSingleProofRouteError("malformed mutation case")
            name = _str(case.get("name"), f"mutation case {index} name")
            names.append(name)
            if _bool(case.get("accepted"), f"{name} accepted") is not False:
                raise NativeAttentionMlpSingleProofRouteError(f"mutation accepted: {name}")
            if _bool(case.get("rejected"), f"{name} rejected") is not True:
                raise NativeAttentionMlpSingleProofRouteError(f"mutation not rejected: {name}")
            _str(case.get("error"), f"{name} error")
        if names != list(MUTATION_NAMES):
            raise NativeAttentionMlpSingleProofRouteError("mutation order drift")


MutationFn = Callable[[dict[str, Any]], None]


MUTATIONS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted", lambda p: p.__setitem__("decision", "GO_NATIVE_ATTENTION_MLP_PROOF_EXISTS"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "MATCHED_NANOZK_NATIVE_PROOF_WIN"), True),
    (
        "native_proof_existence_promoted",
        lambda p: p["summary"].__setitem__("one_native_proof_exists", True),
        True,
    ),
    (
        "route_native_proof_existence_promoted",
        lambda p: p["routes"]["native_single_proof_route_budget"].__setitem__("one_native_proof_exists", True),
        True,
    ),
    (
        "two_proof_target_reduced",
        lambda p: p["summary"].__setitem__("current_two_proof_typed_bytes", 6_900),
        True,
    ),
    (
        "nanozk_win_promoted",
        lambda p: p["routes"]["nanozk_comparison_boundary"].__setitem__("status", "GO_MATCHED_NANOZK_WIN"),
        True,
    ),
    (
        "nanozk_object_class_promoted",
        lambda p: p["routes"]["nanozk_comparison_boundary"].__setitem__("matched_workload_or_object_class", True),
        True,
    ),
    (
        "row_ratio_drift",
        lambda p: p["summary"].__setitem__("value_connected_chain_to_mlp_row_ratio", 1.0),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("payload_sha256", "0" * 64), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", lambda p: p.__setitem__("payload_commitment", "sha256:" + "1" * 64), False),
)
MUTATION_NAMES = tuple(name for name, _, _ in MUTATIONS)


def run_mutations(core: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for name, mutator, refresh in MUTATIONS:
        mutated = copy.deepcopy(core)
        mutator(mutated)
        if refresh:
            refresh_routes_and_payload(mutated)
        try:
            validate_payload(mutated, expected=core, context=context)
        except NativeAttentionMlpSingleProofRouteError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return {"cases": cases, "all_mutations_rejected": all(case["rejected"] for case in cases)}


def build_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    expected_context = context if context is not None else build_context()
    core = build_core_payload(expected_context)
    mutation_result = run_mutations(core, expected_context)
    payload = copy.deepcopy(core)
    payload["mutation_result"] = mutation_result
    payload["mutation_inventory"] = {
        "case_count": len(MUTATION_NAMES),
        "all_mutations_rejected": mutation_result["all_mutations_rejected"],
        "cases": list(MUTATION_NAMES),
    }
    refresh_payload_commitment(payload)
    validate_payload(payload, context=expected_context)
    return payload


def to_tsv(payload: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    expected_context = context if context is not None else build_context()
    validate_payload(payload, context=expected_context)
    row = {column: payload["summary"].get(column, payload.get(column)) for column in TSV_COLUMNS}
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
    return handle.getvalue()


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    attribution_gate.write_bytes_atomic(path, data, "native attention MLP route JSON")


def write_tsv(path: pathlib.Path, payload: dict[str, Any], context: dict[str, Any]) -> None:
    attribution_gate.write_bytes_atomic(path, to_tsv(payload, context).encode("utf-8"), "native attention MLP route TSV")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args()

    context = build_context()
    payload = build_payload(context)
    if args.write_json:
        write_json(args.write_json, payload)
    if args.write_tsv:
        write_tsv(args.write_tsv, payload, context)
    if not args.write_json and not args.write_tsv:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
