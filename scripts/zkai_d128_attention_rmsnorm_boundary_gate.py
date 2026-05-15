#!/usr/bin/env python3
"""Gate the current attention-to-d128 RMSNorm/MLP fusion boundary."""

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
from scripts import zkai_d128_rmsnorm_mlp_fused_gate as mlp_gate  # noqa: E402

EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

MLP_GATE_PATH = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json"
MLP_INPUT_PATH = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json"
VALUE_ADAPTER_PATH = EVIDENCE_DIR / "zkai-attention-d128-value-adapter-2026-05.json"
BLOCK_CHAIN_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-block-statement-chain-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.tsv"

SCHEMA = "zkai-d128-attention-rmsnorm-mlp-boundary-gate-v1"
DECISION = "NO_GO_CURRENT_ATTENTION_RMSNORM_MLP_SINGLE_PROOF"
RESULT = "NARROW_CLAIM_MLP_FUSION_GO_ATTENTION_VALUE_HANDOFF_NO_GO"
CLAIM_BOUNDARY = (
    "CURRENT_D128_RMSNORM_MLP_NATIVE_FUSION_IS_PROOF_SIZE_POSITIVE_BUT_CURRENT_ATTENTION_OUTPUTS_"
    "DO_NOT_VALUE_FEED_THE_D128_RMSNORM_INPUT_SO_ATTENTION_PLUS_MLP_SINGLE_PROOF_REMAINS_NO_GO"
)
PAYLOAD_DOMAIN = "ptvm:zkai:d128-attention-rmsnorm-mlp-boundary:v1"

EXPECTED_MLP = {
    "fused_total_row_count": 197_504,
    "fused_local_typed_bytes": 24_832,
    "separate_local_typed_bytes": 56_976,
    "typed_saving_vs_separate_bytes": 32_144,
    "typed_ratio_vs_separate": 0.435833,
    "typed_saving_ratio_vs_separate": 0.564167,
}
EXPECTED_ADAPTER = {
    "attention_cells": 64,
    "target_width": 128,
    "best_candidate_id": "best_global_affine_over_tiled_attention",
    "best_candidate_mismatches": 124,
    "best_candidate_mean_abs_error": 47.734375,
    "target_matches_synthetic_pattern": True,
}
EXPECTED_CHAIN = {
    "accounted_relation_rows": 199_553,
    "activation_lookup_rows": 2_049,
    "slice_count": 6,
    "edge_count": 11,
    "all_edges_match": True,
}

NON_CLAIMS = [
    "not attention plus MLP in one native proof object",
    "not a full transformer block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not proof that current attention outputs equal the d128 RMSNorm input",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_attention_rmsnorm_boundary_gate.py --write-json docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_d128_attention_rmsnorm_boundary_gate.py scripts/tests/test_zkai_d128_attention_rmsnorm_boundary_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_d128_attention_rmsnorm_boundary_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

SOURCE_ARTIFACTS = (
    ("d128_rmsnorm_mlp_fused_gate", MLP_GATE_PATH),
    ("d128_rmsnorm_mlp_fused_input", MLP_INPUT_PATH),
    ("attention_d128_value_adapter_gate", VALUE_ADAPTER_PATH),
    ("attention_derived_d128_block_statement_chain", BLOCK_CHAIN_PATH),
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "summary",
    "boundary_analysis",
    "boundary_analysis_commitment",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS

TSV_COLUMNS = [
    "decision",
    "result",
    "mlp_fused_local_typed_bytes",
    "mlp_separate_local_typed_bytes",
    "mlp_typed_saving_vs_separate_bytes",
    "mlp_typed_saving_ratio_vs_separate",
    "attention_chain_rows",
    "mlp_fused_rows",
    "attention_chain_to_mlp_row_ratio",
    "attention_to_mlp_value_status",
    "adapter_best_candidate_mismatches",
    "adapter_best_candidate_mean_abs_error",
]


class AttentionRmsnormBoundaryError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionRmsnormBoundaryError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as err:
        raise AttentionRmsnormBoundaryError(f"invalid JSON value: {err}") from err


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
        raise AttentionRmsnormBoundaryError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionRmsnormBoundaryError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AttentionRmsnormBoundaryError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionRmsnormBoundaryError(f"{label} must be integer")
    return value


def _number(value: Any, label: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise AttentionRmsnormBoundaryError(f"{label} must be number")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionRmsnormBoundaryError(f"{label} must be boolean")
    return value


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        return adapter_gate.load_json(path)
    except Exception as err:  # noqa: BLE001 - normalize imported gate errors for this gate.
        raise AttentionRmsnormBoundaryError(f"failed loading {path}: {err}") from err


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


def build_context() -> dict[str, Any]:
    source_payloads: dict[str, dict[str, Any]] = {}
    source_artifacts: list[dict[str, Any]] = []
    for artifact_id, path in SOURCE_ARTIFACTS:
        payload, artifact = source_artifact(artifact_id, path)
        source_payloads[artifact_id] = payload
        source_artifacts.append(artifact)

    mlp_payload = source_payloads["d128_rmsnorm_mlp_fused_gate"]
    try:
        mlp_gate.validate_payload(mlp_payload)
    except Exception as err:  # noqa: BLE001 - normalize dependent gate failures.
        raise AttentionRmsnormBoundaryError(f"MLP fused gate validation failed: {err}") from err

    try:
        adapter_context = adapter_gate.build_expected_context()
    except Exception as err:  # noqa: BLE001 - normalize dependent gate failures.
        raise AttentionRmsnormBoundaryError(f"adapter expected-context build failed: {err}") from err
    adapter_payload = source_payloads["attention_d128_value_adapter_gate"]
    try:
        adapter_gate.validate_payload(adapter_payload, expected_context=adapter_context)
    except Exception as err:  # noqa: BLE001 - normalize dependent gate failures.
        raise AttentionRmsnormBoundaryError(f"adapter gate validation failed: {err}") from err

    mlp_input = source_payloads["d128_rmsnorm_mlp_fused_input"]
    block_chain = source_payloads["attention_derived_d128_block_statement_chain"]

    mlp_aggregate = _dict(mlp_payload.get("aggregate"), "MLP aggregate")
    for key, expected in EXPECTED_MLP.items():
        if mlp_aggregate.get(key) != expected:
            raise AttentionRmsnormBoundaryError(f"MLP aggregate drift: {key}")

    adapter_summary = _dict(adapter_payload.get("summary"), "adapter summary")
    for key, expected in EXPECTED_ADAPTER.items():
        if adapter_summary.get(key) != expected:
            raise AttentionRmsnormBoundaryError(f"adapter summary drift: {key}")

    chain_summary = _dict(block_chain.get("summary"), "block chain summary")
    for key, expected in EXPECTED_CHAIN.items():
        if chain_summary.get(key) != expected:
            raise AttentionRmsnormBoundaryError(f"block chain summary drift: {key}")

    attention_outputs = _str(adapter_summary.get("attention_outputs_commitment"), "adapter attention output")
    d128_input_activation = _str(adapter_summary.get("d128_input_activation_commitment"), "adapter d128 input")
    mlp_input_activation = _str(mlp_input.get("input_activation_commitment"), "MLP input activation")
    chain_attention_outputs = _str(chain_summary.get("source_attention_outputs_commitment"), "chain attention output")
    chain_derived_input = _str(chain_summary.get("derived_input_activation_commitment"), "chain derived input")

    if chain_attention_outputs != attention_outputs:
        raise AttentionRmsnormBoundaryError("attention output commitment drift between chain and adapter")
    if mlp_input_activation != d128_input_activation:
        raise AttentionRmsnormBoundaryError("MLP input commitment drift against adapter d128 target")
    if attention_outputs == mlp_input_activation:
        raise AttentionRmsnormBoundaryError("current boundary unexpectedly has direct value equality")
    if chain_derived_input == mlp_input_activation:
        raise AttentionRmsnormBoundaryError("attention-derived d128 chain unexpectedly matches MLP fused input")

    mlp_rows = _int(mlp_aggregate.get("fused_total_row_count"), "MLP fused rows")
    chain_rows = _int(chain_summary.get("accounted_relation_rows"), "attention chain rows")
    adapter_mismatches = _int(adapter_summary.get("best_candidate_mismatches"), "adapter mismatches")
    analysis = {
        "analysis_kind": "d128-attention-to-rmsnorm-mlp-fusion-boundary",
        "mlp_fused_native_result": {
            "status": "GO_MLP_SIDE_NATIVE_FUSION_PROOF_SIZE_SAVING",
            "fused_rows": mlp_rows,
            "fused_local_typed_bytes": _int(mlp_aggregate.get("fused_local_typed_bytes"), "MLP fused typed"),
            "separate_local_typed_bytes": _int(mlp_aggregate.get("separate_local_typed_bytes"), "MLP separate typed"),
            "typed_saving_vs_separate_bytes": _int(
                mlp_aggregate.get("typed_saving_vs_separate_bytes"), "MLP typed saving"
            ),
            "typed_saving_ratio_vs_separate": _number(
                mlp_aggregate.get("typed_saving_ratio_vs_separate"), "MLP saving ratio"
            ),
            "typed_ratio_vs_separate": _number(mlp_aggregate.get("typed_ratio_vs_separate"), "MLP typed ratio"),
            "statement_commitment": _str(mlp_payload.get("statement_commitment"), "MLP statement commitment"),
            "public_instance_commitment": _str(
                mlp_payload.get("public_instance_commitment"), "MLP public instance commitment"
            ),
            "input_activation_commitment": mlp_input_activation,
        },
        "attention_side_statement_chain": {
            "status": "GO_STATEMENT_CHAIN_BUT_NOT_VALUE_CONNECTED_TO_CURRENT_MLP_INPUT",
            "accounted_relation_rows": chain_rows,
            "activation_lookup_rows": _int(chain_summary.get("activation_lookup_rows"), "activation lookup rows"),
            "slice_count": _int(chain_summary.get("slice_count"), "chain slice count"),
            "edge_count": _int(chain_summary.get("edge_count"), "chain edge count"),
            "all_edges_match": _bool(chain_summary.get("all_edges_match"), "chain edges match"),
            "source_attention_outputs_commitment": chain_attention_outputs,
            "derived_input_activation_commitment": chain_derived_input,
            "block_statement_commitment": _str(chain_summary.get("block_statement_commitment"), "block statement"),
        },
        "attention_to_mlp_value_adapter": {
            "status": "NO_GO_CURRENT_VALUE_HANDOFF",
            "attention_outputs_commitment": attention_outputs,
            "d128_input_activation_commitment": d128_input_activation,
            "best_candidate_id": _str(adapter_summary.get("best_candidate_id"), "best candidate id"),
            "best_candidate_mismatches": adapter_mismatches,
            "best_candidate_mean_abs_error": _number(
                adapter_summary.get("best_candidate_mean_abs_error"), "best candidate mean abs error"
            ),
            "mismatch_share": adapter_mismatches / _int(adapter_summary.get("target_width"), "adapter target width"),
            "target_matches_synthetic_pattern": _bool(
                adapter_summary.get("target_matches_synthetic_pattern"), "synthetic target pattern"
            ),
        },
        "boundary_decision": {
            "single_native_attention_plus_mlp_proof": "NO_GO_UNTIL_VALUE_HANDOFF_IS_SOLVED",
            "typed_handoff": "OPEN_RESEARCH_ROUTE",
            "next_smallest_experiment": (
                "build a checked adapter whose emitted d128 activation vector is value-derived from the "
                "attention output and then re-run the fusion boundary gate"
            ),
        },
    }
    analysis_commitment = commitment(analysis, PAYLOAD_DOMAIN)
    summary = {
        "decision": DECISION,
        "mlp_fused_local_typed_bytes": analysis["mlp_fused_native_result"]["fused_local_typed_bytes"],
        "mlp_separate_local_typed_bytes": analysis["mlp_fused_native_result"]["separate_local_typed_bytes"],
        "mlp_typed_saving_vs_separate_bytes": analysis["mlp_fused_native_result"][
            "typed_saving_vs_separate_bytes"
        ],
        "mlp_typed_saving_ratio_vs_separate": analysis["mlp_fused_native_result"][
            "typed_saving_ratio_vs_separate"
        ],
        "attention_chain_rows": chain_rows,
        "mlp_fused_rows": mlp_rows,
        "attention_chain_to_mlp_row_ratio": round(chain_rows / mlp_rows, 6),
        "attention_chain_extra_rows": chain_rows - mlp_rows,
        "attention_to_mlp_value_status": "NO_GO_CURRENT_VALUE_HANDOFF",
        "adapter_best_candidate_mismatches": adapter_mismatches,
        "adapter_best_candidate_mean_abs_error": analysis["attention_to_mlp_value_adapter"][
            "best_candidate_mean_abs_error"
        ],
        "boundary_analysis_commitment": analysis_commitment,
    }
    return {
        "source_artifacts": source_artifacts,
        "boundary_analysis": analysis,
        "boundary_analysis_commitment": analysis_commitment,
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
        "summary": copy.deepcopy(data["summary"]),
        "boundary_analysis": copy.deepcopy(data["boundary_analysis"]),
        "boundary_analysis_commitment": data["boundary_analysis_commitment"],
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def _comparable(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "payload_commitment"}


def validate_payload(
    payload: Any,
    *,
    expected: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    data = _dict(payload, "payload")
    key_set = set(data)
    if key_set not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionRmsnormBoundaryError(f"unexpected payload keys: {sorted(key_set ^ FINAL_KEYS)}")
    if data.get("schema") != SCHEMA:
        raise AttentionRmsnormBoundaryError("schema drift")
    if data.get("decision") != DECISION:
        raise AttentionRmsnormBoundaryError("decision drift")
    if data.get("result") != RESULT:
        raise AttentionRmsnormBoundaryError("result drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionRmsnormBoundaryError("claim boundary drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise AttentionRmsnormBoundaryError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionRmsnormBoundaryError("validation command drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AttentionRmsnormBoundaryError("payload commitment drift")

    expected_context = context if context is not None else build_context()
    if data.get("source_artifacts") != expected_context["source_artifacts"]:
        raise AttentionRmsnormBoundaryError("source artifact drift")
    if data.get("boundary_analysis") != expected_context["boundary_analysis"]:
        raise AttentionRmsnormBoundaryError("boundary analysis drift")
    if data.get("boundary_analysis_commitment") != expected_context["boundary_analysis_commitment"]:
        raise AttentionRmsnormBoundaryError("boundary analysis commitment drift")
    if data.get("summary") != expected_context["summary"]:
        raise AttentionRmsnormBoundaryError("summary drift")
    if expected is not None and _comparable(data) != _comparable(expected):
        raise AttentionRmsnormBoundaryError("payload content drift")

    summary = _dict(data.get("summary"), "summary")
    if _str(summary.get("attention_to_mlp_value_status"), "attention value status") != "NO_GO_CURRENT_VALUE_HANDOFF":
        raise AttentionRmsnormBoundaryError("attention value status drift")
    if _int(summary.get("adapter_best_candidate_mismatches"), "adapter best mismatches") <= 0:
        raise AttentionRmsnormBoundaryError("adapter mismatch overclaim")
    if _number(summary.get("adapter_best_candidate_mean_abs_error"), "adapter mean abs error") <= 0:
        raise AttentionRmsnormBoundaryError("adapter error overclaim")
    if _int(summary.get("mlp_typed_saving_vs_separate_bytes"), "MLP typed saving") != 32_144:
        raise AttentionRmsnormBoundaryError("MLP typed saving drift")
    if _int(summary.get("attention_chain_extra_rows"), "attention chain extra rows") != 2_049:
        raise AttentionRmsnormBoundaryError("attention chain row delta drift")

    analysis = _dict(data.get("boundary_analysis"), "boundary analysis")
    decision = _dict(analysis.get("boundary_decision"), "boundary decision")
    if decision.get("single_native_attention_plus_mlp_proof") != "NO_GO_UNTIL_VALUE_HANDOFF_IS_SOLVED":
        raise AttentionRmsnormBoundaryError("single-proof overclaim")
    adapter = _dict(analysis.get("attention_to_mlp_value_adapter"), "value adapter")
    mlp = _dict(analysis.get("mlp_fused_native_result"), "MLP result")
    attention = _dict(analysis.get("attention_side_statement_chain"), "attention result")
    if adapter.get("attention_outputs_commitment") != attention.get("source_attention_outputs_commitment"):
        raise AttentionRmsnormBoundaryError("attention output commitment drift")
    if adapter.get("d128_input_activation_commitment") != mlp.get("input_activation_commitment"):
        raise AttentionRmsnormBoundaryError("MLP input commitment drift")
    if adapter.get("attention_outputs_commitment") == mlp.get("input_activation_commitment"):
        raise AttentionRmsnormBoundaryError("value equality overclaim")

    if key_set == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionRmsnormBoundaryError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionRmsnormBoundaryError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionRmsnormBoundaryError("not all mutations rejected")
        case_names: list[str] = []
        for index, value in enumerate(cases):
            case = _dict(value, f"cases[{index}]")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionRmsnormBoundaryError("malformed mutation case")
            name = _str(case.get("name"), f"cases[{index}] name")
            if name not in EXPECTED_MUTATIONS:
                raise AttentionRmsnormBoundaryError("unknown mutation case")
            if _bool(case.get("accepted"), f"cases[{index}] accepted") is not False:
                raise AttentionRmsnormBoundaryError(f"mutation accepted: {name}")
            if _bool(case.get("rejected"), f"cases[{index}] rejected") is not True:
                raise AttentionRmsnormBoundaryError(f"mutation not rejected: {name}")
            _str(case.get("error"), f"cases[{index}] error")
            case_names.append(name)
        if case_names != list(EXPECTED_MUTATIONS):
            raise AttentionRmsnormBoundaryError("mutation case order drift")


MutationFn = Callable[[dict[str, Any]], None]


def _refresh_analysis(payload: dict[str, Any]) -> None:
    payload["boundary_analysis_commitment"] = commitment(payload["boundary_analysis"], PAYLOAD_DOMAIN)
    payload["summary"]["boundary_analysis_commitment"] = payload["boundary_analysis_commitment"]
    refresh_payload_commitment(payload)


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted", lambda p: p.__setitem__("decision", "GO_ATTENTION_RMSNORM_MLP_SINGLE_PROOF"), True),
    (
        "claim_boundary_overclaim",
        lambda p: p.__setitem__("claim_boundary", "ATTENTION_AND_MLP_ARE_ONE_PROVEN_BLOCK"),
        True,
    ),
    (
        "single_proof_status_promoted",
        lambda p: p["boundary_analysis"]["boundary_decision"].__setitem__(
            "single_native_attention_plus_mlp_proof", "GO_NATIVE_SINGLE_PROOF"
        ),
        True,
    ),
    (
        "adapter_mismatch_zeroed",
        lambda p: p["summary"].__setitem__("adapter_best_candidate_mismatches", 0),
        True,
    ),
    (
        "adapter_mean_abs_error_zeroed",
        lambda p: p["summary"].__setitem__("adapter_best_candidate_mean_abs_error", 0),
        True,
    ),
    (
        "mlp_typed_saving_zeroed",
        lambda p: p["summary"].__setitem__("mlp_typed_saving_vs_separate_bytes", 0),
        True,
    ),
    (
        "attention_commitment_relabelled",
        lambda p: p["boundary_analysis"]["attention_side_statement_chain"].__setitem__(
            "source_attention_outputs_commitment", "blake2b-256:" + "11" * 32
        ),
        True,
    ),
    (
        "mlp_input_relabelled",
        lambda p: p["boundary_analysis"]["mlp_fused_native_result"].__setitem__(
            "input_activation_commitment", "blake2b-256:" + "22" * 32
        ),
        True,
    ),
    (
        "source_artifact_hash_drift",
        lambda p: p["source_artifacts"][0].__setitem__("sha256", "33" * 32),
        True,
    ),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", lambda p: p.__setitem__("payload_commitment", "sha256:" + "44" * 32), False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutation_cases(core: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core)
        mutator(mutated)
        if refresh:
            if "boundary_analysis" in mutated:
                _refresh_analysis(mutated)
            else:
                refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, expected=core, context=context)
        except AttentionRmsnormBoundaryError as err:
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
        outputs.append((json_path, pretty_json(payload), "boundary JSON"))
    if tsv_path is not None:
        outputs.append((tsv_path, to_tsv(payload, context), "boundary TSV"))
    adapter_gate.write_texts_no_follow(outputs)
    summary = payload["summary"]
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    print(f"mutations_rejected={sum(case['rejected'] for case in payload['cases'])}/{payload['case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
