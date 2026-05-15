#!/usr/bin/env python3
"""Classify the attention-derived d128 native RMSNorm-MLP proof route."""

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
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

DERIVED_RMSNORM = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
DERIVED_PROJECTION = EVIDENCE_DIR / "zkai-attention-derived-d128-projection-boundary-2026-05.json"
DERIVED_ACTIVATION = EVIDENCE_DIR / "zkai-attention-derived-d128-activation-swiglu-2026-05.json"
DERIVED_DOWN = EVIDENCE_DIR / "zkai-attention-derived-d128-down-projection-2026-05.json"
DERIVED_RESIDUAL = EVIDENCE_DIR / "zkai-attention-derived-d128-residual-add-2026-05.json"
DERIVED_CHAIN = EVIDENCE_DIR / "zkai-attention-derived-d128-block-statement-chain-2026-05.json"
CURRENT_MLP_FUSED_GATE = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json"
CURRENT_MLP_FUSED_INPUT = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json"
CURRENT_MLP_FUSED_ENVELOPE = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-native-mlp-proof-route-gate-v1"
DECISION = "NO_GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_NOT_REGENERATED"
RESULT = "BOUNDED_NO_GO_NATIVE_COMPONENT_INPUTS_NOT_PARAMETERIZED"
VALUE_CHAIN_STATUS = "GO_ATTENTION_DERIVED_D128_VALUE_CONNECTED_STATEMENT_CHAIN"
NATIVE_ROUTE_STATUS = "NO_GO_DERIVED_DOWNSTREAM_PAYLOADS_NOT_NATIVE_COMPONENT_PROOF_INPUTS"
FIRST_BLOCKER = (
    "the attention-derived downstream slice artifacts are checked statement-chain payloads, "
    "not native component proof inputs accepted by the current Stwo RMSNorm-MLP fused proof builder"
)
PAYLOAD_DOMAIN = "ptvm:zkai:attention-derived-d128:native-mlp-proof-route:v1"
EXPECTED_DERIVED_INPUT_COMMITMENT = (
    "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35"
)
EXPECTED_CURRENT_INPUT_COMMITMENT = (
    "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78"
)

REQUIRED_NATIVE_PROOF_ARTIFACTS = (
    "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json",
    "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json",
)

COMPONENT_SPECS = (
    {
        "component_id": "rmsnorm_public_rows",
        "path": DERIVED_RMSNORM,
        "payload_key": "rmsnorm_public_row_payload",
        "required_native_schema": "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
        "required_native_decision": "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "rmsnorm_projection_bridge",
        "path": DERIVED_PROJECTION,
        "payload_key": "bridge_payload",
        "required_native_schema": "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "gate_value_projection",
        "path": DERIVED_PROJECTION,
        "payload_key": "gate_value_projection_payload",
        "required_native_schema": "zkai-d128-gate-value-projection-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_GATE_VALUE_PROJECTION_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "activation_swiglu",
        "path": DERIVED_ACTIVATION,
        "payload_key": "activation_swiglu_payload",
        "required_native_schema": "zkai-d128-activation-swiglu-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_ACTIVATION_SWIGLU_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "down_projection",
        "path": DERIVED_DOWN,
        "payload_key": "down_projection_payload",
        "required_native_schema": "zkai-d128-down-projection-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "residual_add",
        "path": DERIVED_RESIDUAL,
        "payload_key": "residual_add_payload",
        "required_native_schema": "zkai-d128-residual-add-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
)

NON_CLAIMS = [
    "not a regenerated attention-derived native RMSNorm-MLP fused proof",
    "not attention plus MLP in one native proof object",
    "not a full transformer block proof",
    "not a NANOZK benchmark win",
    "not proof-size evidence for the attention-derived route",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py scripts/tests/test_zkai_attention_derived_d128_native_mlp_proof_route_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "value_chain_status",
    "native_route_status",
    "first_blocker",
    "source_artifacts",
    "component_input_frontier",
    "missing_native_artifacts",
    "comparison",
    "summary",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = (
    "decision",
    "result",
    "value_chain_status",
    "native_route_status",
    "derived_input_activation_commitment",
    "current_mlp_input_activation_commitment",
    "value_connected_chain_rows",
    "current_mlp_fused_rows",
    "row_ratio",
    "current_mlp_fused_typed_bytes",
    "current_mlp_typed_saving_vs_separate_bytes",
    "native_compatible_components",
    "native_incompatible_components",
)


class NativeMlpProofRouteError(ValueError):
    pass


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise NativeMlpProofRouteError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise NativeMlpProofRouteError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeMlpProofRouteError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeMlpProofRouteError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeMlpProofRouteError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NativeMlpProofRouteError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise NativeMlpProofRouteError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    text = _str(value, label)
    for prefix in ("blake2b-256:", "sha256:"):
        digest = text.removeprefix(prefix)
        if digest != text and len(digest) == 64 and all(char in "0123456789abcdef" for char in digest):
            return text
    raise NativeMlpProofRouteError(f"{label} must be a typed 32-byte commitment")


def _load_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink():
        raise NativeMlpProofRouteError(f"{label} must not be a symlink: {path}")
    try:
        raw = path.read_bytes()
    except OSError as err:
        raise NativeMlpProofRouteError(f"failed reading {label}: {path}") from err
    if len(raw) > 16 * 1024 * 1024:
        raise NativeMlpProofRouteError(f"{label} exceeds max bytes: {len(raw)}")
    try:
        payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise NativeMlpProofRouteError(f"failed parsing {label}: {path}: {err}") from err
    if not isinstance(payload, dict):
        raise NativeMlpProofRouteError(f"{label} must be JSON object")
    return payload, raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def component_frontier_row(spec: dict[str, Any], source_payloads: dict[pathlib.Path, dict[str, Any]]) -> dict[str, Any]:
    payload = _dict(source_payloads[spec["path"]].get(spec["payload_key"]), f"{spec['component_id']} payload")
    missing = [field for field in spec["required_fields"] if field not in payload]
    schema = _str(payload.get("schema"), f"{spec['component_id']} schema")
    decision = _str(payload.get("decision"), f"{spec['component_id']} decision")
    schema_matches = schema == spec["required_native_schema"]
    decision_matches = decision == spec["required_native_decision"]
    compatible = schema_matches and decision_matches and not missing
    commitments = {
        key: value
        for key, value in payload.items()
        if key.endswith("_commitment") and isinstance(value, str) and value.startswith(("blake2b-256:", "sha256:"))
    }
    return {
        "component_id": spec["component_id"],
        "source_path": spec["path"].relative_to(ROOT).as_posix(),
        "payload_key": spec["payload_key"],
        "schema": schema,
        "required_native_schema": spec["required_native_schema"],
        "schema_matches_native": schema_matches,
        "decision": decision,
        "required_native_decision": spec["required_native_decision"],
        "decision_matches_native": decision_matches,
        "missing_required_native_fields": missing,
        "native_component_input_status": "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE" if compatible else "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT",
        "commitments": commitments,
    }


def build_context() -> dict[str, Any]:
    paths = {
        DERIVED_RMSNORM,
        DERIVED_PROJECTION,
        DERIVED_ACTIVATION,
        DERIVED_DOWN,
        DERIVED_RESIDUAL,
        DERIVED_CHAIN,
        CURRENT_MLP_FUSED_GATE,
        CURRENT_MLP_FUSED_INPUT,
        CURRENT_MLP_FUSED_ENVELOPE,
    }
    loaded: dict[pathlib.Path, dict[str, Any]] = {}
    artifacts = []
    for path in sorted(paths):
        payload, raw = _load_json(path, path.name)
        loaded[path] = payload
        artifacts.append(source_artifact(path.stem, path, payload, raw))

    chain_summary = _dict(loaded[DERIVED_CHAIN].get("summary"), "derived chain summary")
    current_aggregate = _dict(loaded[CURRENT_MLP_FUSED_GATE].get("aggregate"), "current MLP aggregate")
    current_input = loaded[CURRENT_MLP_FUSED_INPUT]
    current_envelope = loaded[CURRENT_MLP_FUSED_ENVELOPE]
    derived_input_commitment = _commitment(
        chain_summary.get("derived_input_activation_commitment"),
        "derived input activation commitment",
    )
    current_input_commitment = _commitment(
        current_input.get("input_activation_commitment"),
        "current MLP fused input activation commitment",
    )
    if derived_input_commitment != EXPECTED_DERIVED_INPUT_COMMITMENT:
        raise NativeMlpProofRouteError("derived input commitment drift")
    if current_input_commitment != EXPECTED_CURRENT_INPUT_COMMITMENT:
        raise NativeMlpProofRouteError("current MLP input commitment drift")
    rows = _int(chain_summary.get("accounted_relation_rows"), "attention-derived relation rows")
    mlp_rows = _int(current_aggregate.get("fused_total_row_count"), "current MLP fused rows")
    component_rows = [component_frontier_row(spec, loaded) for spec in COMPONENT_SPECS]
    missing_native_artifacts = [
        {
            "path": path,
            "exists": (ROOT / path).exists(),
            "required_for_go": True,
            "status": "MISSING_REQUIRED_NATIVE_ATTENTION_DERIVED_PROOF_ARTIFACT",
        }
        for path in REQUIRED_NATIVE_PROOF_ARTIFACTS
    ]
    return {
        "loaded": loaded,
        "source_artifacts": artifacts,
        "component_input_frontier": component_rows,
        "missing_native_artifacts": missing_native_artifacts,
        "comparison": {
            "derived_input_activation_commitment": derived_input_commitment,
            "current_mlp_input_activation_commitment": current_input_commitment,
            "current_mlp_fused_envelope_input_activation_commitment": _commitment(
                _dict(current_envelope.get("input"), "current envelope input").get("input_activation_commitment"),
                "current envelope input activation commitment",
            ),
            "current_mlp_proof_backend_version": _str(
                current_envelope.get("proof_backend_version"),
                "current MLP proof backend version",
            ),
            "value_connected_chain_rows": rows,
            "current_mlp_fused_rows": mlp_rows,
            "row_ratio": round(rows / mlp_rows, 6),
            "extra_rows_vs_current_mlp_fused": rows - mlp_rows,
            "current_mlp_fused_typed_bytes": _int(
                current_aggregate.get("fused_local_typed_bytes"),
                "current fused typed bytes",
            ),
            "current_mlp_separate_typed_bytes": _int(
                current_aggregate.get("separate_local_typed_bytes"),
                "current separate typed bytes",
            ),
            "current_mlp_typed_saving_vs_separate_bytes": _int(
                current_aggregate.get("typed_saving_vs_separate_bytes"),
                "current typed saving bytes",
            ),
            "current_mlp_typed_saving_ratio_vs_separate": current_aggregate.get(
                "typed_saving_ratio_vs_separate"
            ),
            "current_native_fused_proof_can_be_reused_for_derived_input": False,
        },
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    compatible_count = sum(
        1
        for row in context["component_input_frontier"]
        if row["native_component_input_status"] == "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE"
    )
    incompatible_count = len(context["component_input_frontier"]) - compatible_count
    comparison = context["comparison"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "value_chain_status": VALUE_CHAIN_STATUS,
        "native_route_status": NATIVE_ROUTE_STATUS,
        "first_blocker": FIRST_BLOCKER,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "component_input_frontier": copy.deepcopy(context["component_input_frontier"]),
        "missing_native_artifacts": copy.deepcopy(context["missing_native_artifacts"]),
        "comparison": copy.deepcopy(comparison),
        "summary": {
            "go_result": "GO for a value-connected attention-derived d128 statement chain",
            "no_go_result": "NO-GO for a regenerated attention-derived native RMSNorm-MLP fused proof today",
            "derived_input_activation_commitment": comparison["derived_input_activation_commitment"],
            "current_mlp_input_activation_commitment": comparison["current_mlp_input_activation_commitment"],
            "value_connected_chain_rows": comparison["value_connected_chain_rows"],
            "current_mlp_fused_rows": comparison["current_mlp_fused_rows"],
            "row_ratio": comparison["row_ratio"],
            "current_mlp_fused_typed_bytes": comparison["current_mlp_fused_typed_bytes"],
            "current_mlp_typed_saving_vs_separate_bytes": comparison[
                "current_mlp_typed_saving_vs_separate_bytes"
            ],
            "current_mlp_typed_saving_ratio_vs_separate": comparison[
                "current_mlp_typed_saving_ratio_vs_separate"
            ],
            "native_compatible_components": compatible_count,
            "native_incompatible_components": incompatible_count,
            "missing_native_artifacts": len(context["missing_native_artifacts"]),
            "route_commitment": blake2b_commitment(
                {
                    "derived_input": comparison["derived_input_activation_commitment"],
                    "current_mlp_input": comparison["current_mlp_input_activation_commitment"],
                    "component_frontier": context["component_input_frontier"],
                    "missing_native_artifacts": context["missing_native_artifacts"],
                },
                PAYLOAD_DOMAIN,
            ),
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    if set(data) not in (CORE_KEYS, FINAL_KEYS):
        raise NativeMlpProofRouteError("payload key set drift")
    if data.get("schema") != SCHEMA:
        raise NativeMlpProofRouteError("schema drift")
    if data.get("decision") != DECISION:
        raise NativeMlpProofRouteError("decision drift")
    if data.get("result") != RESULT:
        raise NativeMlpProofRouteError("result drift")
    if data.get("value_chain_status") != VALUE_CHAIN_STATUS:
        raise NativeMlpProofRouteError("value-chain status drift")
    if data.get("native_route_status") != NATIVE_ROUTE_STATUS:
        raise NativeMlpProofRouteError("native route status drift")
    if data.get("first_blocker") != FIRST_BLOCKER:
        raise NativeMlpProofRouteError("first blocker drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise NativeMlpProofRouteError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise NativeMlpProofRouteError("validation commands drift")
    context = build_context() if context is None else context
    expected = build_core_payload(context)
    comparable = {key: value for key, value in data.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected_comparable = {key: value for key, value in expected.items() if key != "payload_commitment"}
    if comparable != expected_comparable:
        raise NativeMlpProofRouteError("payload content drift")
    summary = _dict(data.get("summary"), "summary")
    if _int(summary.get("native_incompatible_components"), "native incompatible components") <= 0:
        raise NativeMlpProofRouteError("native route overclaim")
    if data["comparison"]["current_native_fused_proof_can_be_reused_for_derived_input"] is not False:
        raise NativeMlpProofRouteError("current proof reuse overclaim")
    for row in _list(data.get("missing_native_artifacts"), "missing native artifacts"):
        artifact = _dict(row, "missing native artifact")
        if _bool(artifact.get("exists"), "missing artifact exists") is not False:
            raise NativeMlpProofRouteError("missing native artifact relabeled as existing")
        if _bool(artifact.get("required_for_go"), "required for go") is not True:
            raise NativeMlpProofRouteError("required native artifact no longer required")
    if data.get("payload_commitment") != payload_commitment(data):
        raise NativeMlpProofRouteError("payload commitment drift")
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise NativeMlpProofRouteError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise NativeMlpProofRouteError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise NativeMlpProofRouteError("not all mutations rejected")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise NativeMlpProofRouteError("mutation cases length drift")
        for index, (name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise NativeMlpProofRouteError("mutation case field drift")
            if case.get("name") != name:
                raise NativeMlpProofRouteError("mutation case order drift")
            if case.get("accepted") is not False or case.get("rejected") is not True:
                raise NativeMlpProofRouteError("mutation accepted")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise NativeMlpProofRouteError("mutation error missing")


MutationFn = Callable[[dict[str, Any]], None]


def _set_payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted_to_go", lambda p: p.__setitem__("decision", "GO_ATTENTION_DERIVED_NATIVE_MLP_PROOF"), True),
    ("result_promoted_to_proof", lambda p: p.__setitem__("result", "GO_NATIVE_PROOF_REGENERATED"), True),
    ("native_route_status_promoted", lambda p: p.__setitem__("native_route_status", "GO_NATIVE_ROUTE"), True),
    ("first_blocker_removed", lambda p: p.__setitem__("first_blocker", ""), True),
    (
        "derived_input_relabels_current_mlp_input",
        lambda p: p["comparison"].__setitem__(
            "derived_input_activation_commitment", EXPECTED_CURRENT_INPUT_COMMITMENT
        ),
        True,
    ),
    (
        "current_proof_reuse_overclaim",
        lambda p: p["comparison"].__setitem__("current_native_fused_proof_can_be_reused_for_derived_input", True),
        True,
    ),
    (
        "incompatible_component_count_zeroed",
        lambda p: p["summary"].__setitem__("native_incompatible_components", 0),
        True,
    ),
    (
        "component_schema_relabels_native",
        lambda p: p["component_input_frontier"][1].__setitem__(
            "schema", p["component_input_frontier"][1]["required_native_schema"]
        ),
        True,
    ),
    (
        "missing_native_artifact_marked_existing",
        lambda p: p["missing_native_artifacts"][0].__setitem__("exists", True),
        True,
    ),
    (
        "missing_native_artifact_not_required",
        lambda p: p["missing_native_artifacts"][0].__setitem__("required_for_go", False),
        True,
    ),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("validation_command_removed", lambda p: p.__setitem__("validation_commands", p["validation_commands"][1:]), True),
    ("payload_commitment_drift", _set_payload_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutation_cases(core_payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core_payload)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, context=context)
        except NativeMlpProofRouteError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result() -> dict[str, Any]:
    context = build_context()
    core = build_core_payload(context)
    cases = run_mutation_cases(core, context)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(EXPECTED_MUTATIONS)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final, context=context)
    return final


def to_tsv(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> str:
    validate_payload(payload, context=context)
    summary = _dict(payload.get("summary"), "summary")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": payload["decision"],
            "result": payload["result"],
            "value_chain_status": payload["value_chain_status"],
            "native_route_status": payload["native_route_status"],
            "derived_input_activation_commitment": summary["derived_input_activation_commitment"],
            "current_mlp_input_activation_commitment": summary["current_mlp_input_activation_commitment"],
            "value_connected_chain_rows": summary["value_connected_chain_rows"],
            "current_mlp_fused_rows": summary["current_mlp_fused_rows"],
            "row_ratio": summary["row_ratio"],
            "current_mlp_fused_typed_bytes": summary["current_mlp_fused_typed_bytes"],
            "current_mlp_typed_saving_vs_separate_bytes": summary[
                "current_mlp_typed_saving_vs_separate_bytes"
            ],
            "native_compatible_components": summary["native_compatible_components"],
            "native_incompatible_components": summary["native_incompatible_components"],
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    resolved_root = ROOT.resolve()
    candidate = (ROOT / path if not path.is_absolute() else path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as err:
        raise NativeMlpProofRouteError(f"output path must stay inside repository: {path}") from err
    if candidate.suffix != suffix:
        raise NativeMlpProofRouteError(f"output path must end with {suffix}: {path}")
    if candidate.exists() and candidate.is_symlink():
        raise NativeMlpProofRouteError(f"output path must not be symlink: {path}")
    return candidate


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    context = build_context()
    validate_payload(payload, context=context)
    json_target = require_output_path(json_path, ".json")
    tsv_target = require_output_path(tsv_path, ".tsv")
    if json_target is not None:
        atomic_write(json_target, pretty_json(payload) + "\n")
    if tsv_target is not None:
        atomic_write(tsv_target, to_tsv(payload, context=context))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        payload = build_gate_result()
        write_outputs(payload, args.write_json, args.write_tsv)
        if args.write_json is None and args.write_tsv is None:
            print(pretty_json(payload))
    except NativeMlpProofRouteError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
