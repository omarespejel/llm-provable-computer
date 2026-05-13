#!/usr/bin/env python3
"""Build a d128 RMSNorm public-row slice over the attention-derived input."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
DERIVED_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.json"
CURRENT_D128_RMSNORM_JSON = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
TARGET_JSON = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.tsv"

DERIVED_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_input_gate.py"
RMSNORM_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
THIS_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_rmsnorm_public_row_gate.py"

SCHEMA = "zkai-attention-derived-d128-rmsnorm-public-row-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_RMSNORM_PUBLIC_ROW_INPUT"
RESULT = "GO_VALUE_CONNECTED_RMSNORM_SLICE_INPUT_NO_GO_FULL_BLOCK"
CLAIM_BOUNDARY = (
    "CHECKED_D128_RMSNORM_PUBLIC_ROW_INPUT_CONSUMES_ATTENTION_DERIVED_D128_VECTOR_"
    "NOT_EXISTING_BLOCK_RECEIPT_NOT_FULL_LAYER_PROOF_NOT_RECURSION"
)

NON_CLAIMS = [
    "not evidence that the existing d128 block receipt consumed the derived vector",
    "not a learned model projection",
    "not a full transformer block proof",
    "not one recursive or compressed proof object",
    "not a matched NANOZK/Jolt/DeepProve benchmark",
    "not proof-size or timing evidence",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_rmsnorm_public_row_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_rmsnorm_public_row_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_rmsnorm_public_row_gate.py scripts/tests/test_zkai_attention_derived_d128_rmsnorm_public_row_gate.py",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "source_summary",
    "rmsnorm_public_row_payload",
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
    "source_attention_outputs_commitment",
    "input_activation_commitment",
    "rmsnorm_statement_commitment",
    "rmsnorm_output_row_commitment",
    "row_count",
    "rms_q8",
    "sum_squares",
    "average_square_floor",
    "matches_current_d128_block_input",
    "current_d128_mismatch_count",
    "mutations_rejected",
)


class AttentionDerivedD128RmsnormPublicRowError(ValueError):
    pass


def _load_module(path: pathlib.Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AttentionDerivedD128RmsnormPublicRowError(f"failed to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DERIVED = _load_module(DERIVED_GATE_PATH, "zkai_attention_derived_d128_input_gate")
RMSNORM = _load_module(RMSNORM_PATH, "zkai_d128_rmsnorm_public_row_proof_input")
VALUE_GATE = DERIVED.VALUE_GATE


def canonical_json_bytes(value: Any) -> bytes:
    return VALUE_GATE.canonical_json_bytes(value)


def pretty_json(value: Any) -> str:
    return VALUE_GATE.pretty_json(value)


def payload_commitment(payload: dict[str, Any]) -> str:
    return VALUE_GATE.payload_commitment(payload)


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128RmsnormPublicRowError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128RmsnormPublicRowError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128RmsnormPublicRowError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128RmsnormPublicRowError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    try:
        return DERIVED._commitment(value, label)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        return VALUE_GATE.load_json(path)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err


def source_artifact(artifact_id: str, path: pathlib.Path, payload: Any | None = None) -> dict[str, Any]:
    try:
        raw = VALUE_GATE.read_source_bytes(path)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err
    artifact = {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if payload is not None:
        artifact["payload_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return artifact


def build_rmsnorm_payload_for_input(derived_values: list[int]) -> dict[str, Any]:
    if len(derived_values) != RMSNORM.WIDTH:
        raise AttentionDerivedD128RmsnormPublicRowError("derived input width mismatch")
    target = RMSNORM.load_target(TARGET_JSON)
    target_commitment = target["summary"]["target_commitment"]
    _canonical_input_q8, rms_scale_q8 = RMSNORM.build_vectors()
    rows, sum_squares, average_square_floor, rms_q8 = RMSNORM.build_rows(derived_values, rms_scale_q8)
    normed_q8 = [row["normed_q8"] for row in rows]
    scale_commitment = RMSNORM.sequence_commitment(rms_scale_q8, RMSNORM.RMS_SCALE_DOMAIN)
    input_activation = RMSNORM.sequence_commitment(derived_values, RMSNORM.INPUT_ACTIVATION_DOMAIN)
    rmsnorm_output = RMSNORM.sequence_commitment(normed_q8, RMSNORM.RMSNORM_OUTPUT_ROW_DOMAIN)
    normalization_config = RMSNORM.normalization_config_commitment(rms_q8, scale_commitment)
    scale_tree_root = RMSNORM.rms_scale_tree_root(rms_scale_q8)
    payload = {
        "schema": RMSNORM.SCHEMA,
        "decision": RMSNORM.DECISION,
        "operation": RMSNORM.OPERATION,
        "target_id": RMSNORM.TARGET_ID,
        "required_backend_version": RMSNORM.REQUIRED_BACKEND_VERSION,
        "verifier_domain": RMSNORM.VERIFIER_DOMAIN,
        "width": RMSNORM.WIDTH,
        "row_count": RMSNORM.WIDTH,
        "source_proof_backend_version": RMSNORM.SOURCE_PROOF_BACKEND_VERSION,
        "input_activation_domain": RMSNORM.INPUT_ACTIVATION_DOMAIN,
        "rms_scale_domain": RMSNORM.RMS_SCALE_DOMAIN,
        "rmsnorm_output_row_domain": RMSNORM.RMSNORM_OUTPUT_ROW_DOMAIN,
        "normalization_config_domain": RMSNORM.NORMALIZATION_CONFIG_DOMAIN,
        "rms_scale_leaf_domain": RMSNORM.RMS_SCALE_LEAF_DOMAIN,
        "rms_scale_tree_domain": RMSNORM.RMS_SCALE_TREE_DOMAIN,
        "scale_q8": RMSNORM.Q8_SCALE,
        "rms_q8": rms_q8,
        "sum_squares": sum_squares,
        "average_square_floor": average_square_floor,
        "proof_native_parameter_commitment": "",
        "normalization_config_commitment": normalization_config,
        "input_activation_commitment": input_activation,
        "rmsnorm_output_row_commitment": rmsnorm_output,
        "public_instance_commitment": "",
        "statement_commitment": "",
        "rms_scale_tree_root": scale_tree_root,
        "rows": rows,
        "non_claims": list(RMSNORM.NON_CLAIMS),
        "proof_verifier_hardening": list(RMSNORM.PROOF_VERIFIER_HARDENING),
        "next_backend_step": RMSNORM.NEXT_BACKEND_STEP,
        "validation_commands": list(RMSNORM.VALIDATION_COMMANDS),
    }
    statement = RMSNORM.statement_commitment(payload, target_commitment)
    payload["statement_commitment"] = statement
    payload["proof_native_parameter_commitment"] = RMSNORM.proof_native_parameter_commitment(statement)
    payload["public_instance_commitment"] = RMSNORM.public_instance_commitment(statement, RMSNORM.WIDTH)
    try:
        RMSNORM.validate_payload(payload)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(f"derived RMSNorm payload invalid: {err}") from err
    return payload


def build_context() -> dict[str, Any]:
    derived_input, derived_raw = load_json(DERIVED_INPUT_JSON)
    current_rmsnorm, current_raw = load_json(CURRENT_D128_RMSNORM_JSON)
    try:
        DERIVED.validate_payload(derived_input)
        RMSNORM.validate_payload(current_rmsnorm)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err
    derived = _dict(derived_input.get("derived_input"), "derived input")
    derived_values = [_int(value, f"derived value {index}") for index, value in enumerate(_list(derived.get("values_q8"), "derived values"))]
    rmsnorm_payload = build_rmsnorm_payload_for_input(derived_values)
    derived_commitment = _commitment(derived.get("input_activation_commitment"), "derived input commitment")
    if rmsnorm_payload["input_activation_commitment"] != derived_commitment:
        raise AttentionDerivedD128RmsnormPublicRowError("derived RMSNorm input commitment mismatch")
    current_comparison = _dict(derived_input.get("current_d128_comparison"), "current comparison")
    return {
        "source_artifacts": [
            source_artifact("attention_derived_d128_input_gate", DERIVED_INPUT_JSON, derived_input),
            {
                "id": "current_d128_rmsnorm_public_row_input",
                "path": CURRENT_D128_RMSNORM_JSON.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(current_raw).hexdigest(),
                "payload_sha256": hashlib.sha256(canonical_json_bytes(current_rmsnorm)).hexdigest(),
            },
            source_artifact("d128_layerwise_comparator_target", TARGET_JSON, RMSNORM.load_target(TARGET_JSON)),
            source_artifact("rmsnorm_public_row_generator", RMSNORM_PATH),
            source_artifact("attention_derived_input_generator", DERIVED_GATE_PATH),
            source_artifact("attention_derived_rmsnorm_public_row_gate", THIS_GATE_PATH),
        ],
        "source_summary": {
            "source_attention_outputs_commitment": _commitment(
                derived.get("source_attention_outputs_commitment"), "source attention outputs commitment"
            ),
            "derived_input_activation_commitment": derived_commitment,
            "current_d128_input_activation_commitment": _commitment(
                current_comparison.get("current_input_activation_commitment"),
                "current d128 input activation commitment",
            ),
            "current_d128_mismatch_count": _int(
                current_comparison.get("mismatch_count_against_current"), "current d128 mismatch count"
            ),
            "derived_matches_current_d128_input": _bool(
                current_comparison.get("derived_matches_current_input_values"),
                "derived matches current d128 input",
            ),
        },
        "rmsnorm_public_row_payload": rmsnorm_payload,
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    rmsnorm_payload = context["rmsnorm_public_row_payload"]
    source_summary = context["source_summary"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "source_summary": copy.deepcopy(source_summary),
        "rmsnorm_public_row_payload": copy.deepcopy(rmsnorm_payload),
        "summary": {
            "go_result": "GO for a d128 RMSNorm public-row input whose input commitment is derived from checked attention outputs",
            "no_go_result": "NO-GO for claiming the existing d128 block receipt consumed this vector or for claiming a full layer proof",
            "source_attention_outputs_commitment": source_summary["source_attention_outputs_commitment"],
            "input_activation_commitment": rmsnorm_payload["input_activation_commitment"],
            "rmsnorm_statement_commitment": rmsnorm_payload["statement_commitment"],
            "rmsnorm_output_row_commitment": rmsnorm_payload["rmsnorm_output_row_commitment"],
            "row_count": rmsnorm_payload["row_count"],
            "rms_q8": rmsnorm_payload["rms_q8"],
            "sum_squares": rmsnorm_payload["sum_squares"],
            "average_square_floor": rmsnorm_payload["average_square_floor"],
            "matches_current_d128_block_input": False,
            "current_d128_mismatch_count": source_summary["current_d128_mismatch_count"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_core_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    if set(payload) not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128RmsnormPublicRowError("payload key set drift")
    if payload.get("schema") != SCHEMA:
        raise AttentionDerivedD128RmsnormPublicRowError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionDerivedD128RmsnormPublicRowError("decision drift")
    if payload.get("result") != RESULT:
        raise AttentionDerivedD128RmsnormPublicRowError("result drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128RmsnormPublicRowError("claim boundary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128RmsnormPublicRowError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128RmsnormPublicRowError("validation commands drift")
    context = build_context() if context is None else context
    expected_core = build_core_payload(context)
    comparable = {key: value for key, value in payload.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected = {key: value for key, value in expected_core.items() if key != "payload_commitment"}
    if comparable != expected:
        raise AttentionDerivedD128RmsnormPublicRowError("derived RMSNorm payload drift")
    rmsnorm_payload = _dict(payload.get("rmsnorm_public_row_payload"), "rmsnorm public row payload")
    try:
        RMSNORM.validate_payload(rmsnorm_payload)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err
    summary = _dict(payload.get("summary"), "summary")
    source_summary = _dict(payload.get("source_summary"), "source summary")
    if rmsnorm_payload["input_activation_commitment"] != source_summary["derived_input_activation_commitment"]:
        raise AttentionDerivedD128RmsnormPublicRowError("RMSNorm input does not consume derived commitment")
    if summary.get("matches_current_d128_block_input") is not False:
        raise AttentionDerivedD128RmsnormPublicRowError("current block consumption overclaim")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128RmsnormPublicRowError("payload commitment drift")


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    context = build_context() if context is None else context
    validate_core_payload(data, context=context)
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128RmsnormPublicRowError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128RmsnormPublicRowError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionDerivedD128RmsnormPublicRowError("not all mutations rejected")
        expected_cases = run_mutation_cases(build_core_payload(context), context)
        expected_outcomes = [(case["name"], case["accepted"], case["rejected"]) for case in expected_cases]
        outcomes = []
        for index, (expected_name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionDerivedD128RmsnormPublicRowError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AttentionDerivedD128RmsnormPublicRowError("mutation case order drift")
            if _bool(case.get("accepted"), "mutation accepted") is not False:
                raise AttentionDerivedD128RmsnormPublicRowError("mutation accepted")
            if _bool(case.get("rejected"), "mutation rejected") is not True:
                raise AttentionDerivedD128RmsnormPublicRowError("mutation not rejected")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise AttentionDerivedD128RmsnormPublicRowError("mutation error field drift")
            outcomes.append((case["name"], case["accepted"], case["rejected"]))
        if outcomes != expected_outcomes:
            raise AttentionDerivedD128RmsnormPublicRowError("mutation outcome drift")


MutationFn = Callable[[dict[str, Any]], None]


def _set_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_TRANSFORMER_BLOCK"), True),
    ("result_overclaim", lambda p: p.__setitem__("result", "GO_FULL_LAYER_PROOF"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_RECURSIVE_LAYER_PROOF"), True),
    (
        "source_attention_commitment_drift",
        lambda p: p["source_summary"].__setitem__("source_attention_outputs_commitment", "blake2b-256:" + "22" * 32),
        True,
    ),
    (
        "rmsnorm_input_commitment_drift",
        lambda p: p["rmsnorm_public_row_payload"].__setitem__("input_activation_commitment", "blake2b-256:" + "33" * 32),
        True,
    ),
    (
        "rmsnorm_row_input_drift",
        lambda p: p["rmsnorm_public_row_payload"]["rows"][0].__setitem__("input_q8", 99),
        True,
    ),
    (
        "rmsnorm_statement_commitment_drift",
        lambda p: p["rmsnorm_public_row_payload"].__setitem__("statement_commitment", "blake2b-256:" + "44" * 32),
        True,
    ),
    (
        "current_block_consumption_overclaim",
        lambda p: p["summary"].__setitem__("matches_current_d128_block_input", True),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "55" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", _set_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutation_cases(core_payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core_payload)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, context=context)
        except AttentionDerivedD128RmsnormPublicRowError as err:
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


def to_tsv(payload: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    validate_payload(payload, context=context)
    summary = _dict(payload.get("summary"), "summary")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": payload["decision"],
            "result": payload["result"],
            "source_attention_outputs_commitment": summary["source_attention_outputs_commitment"],
            "input_activation_commitment": summary["input_activation_commitment"],
            "rmsnorm_statement_commitment": summary["rmsnorm_statement_commitment"],
            "rmsnorm_output_row_commitment": summary["rmsnorm_output_row_commitment"],
            "row_count": summary["row_count"],
            "rms_q8": summary["rms_q8"],
            "sum_squares": summary["sum_squares"],
            "average_square_floor": summary["average_square_floor"],
            "matches_current_d128_block_input": str(summary["matches_current_d128_block_input"]).lower(),
            "current_d128_mismatch_count": summary["current_d128_mismatch_count"],
            "mutations_rejected": payload["case_count"],
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    try:
        return VALUE_GATE.require_output_path(path, suffix)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    context = build_context()
    validate_payload(payload, context=context)
    outputs: list[tuple[pathlib.Path, str, str]] = []
    json_target = require_output_path(json_path, ".json")
    tsv_target = require_output_path(tsv_path, ".tsv")
    if json_target is not None:
        outputs.append((json_target, pretty_json(payload) + "\n", "json output"))
    if tsv_target is not None:
        outputs.append((tsv_target, to_tsv(payload, context=context), "tsv output"))
    try:
        VALUE_GATE.write_texts_no_follow(outputs)
    except Exception as err:
        raise AttentionDerivedD128RmsnormPublicRowError(str(err)) from err


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
    except AttentionDerivedD128RmsnormPublicRowError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
