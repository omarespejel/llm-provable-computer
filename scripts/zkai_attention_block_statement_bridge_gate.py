#!/usr/bin/env python3
"""Bind the checked attention output and d128 block input under one statement."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import stat as stat_module
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
ATTENTION_BRIDGE = EVIDENCE_DIR / "zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json"
D128_ACCUMULATOR = EVIDENCE_DIR / "zkai-d128-full-block-accumulator-backend-2026-05.json"
ONE_BLOCK_SURFACE = EVIDENCE_DIR / "zkai-one-transformer-block-surface-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-block-statement-bridge-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-block-statement-bridge-2026-05.tsv"

SCHEMA = "zkai-attention-block-statement-bridge-v1"
DECISION = "GO_STATEMENT_BRIDGE_NO_GO_ATTENTION_TO_BLOCK_VALUE_EQUALITY"
RESULT = "GO_STATEMENT_COMMITMENT_BINDING_WITH_NO_GO_VALUE_EQUALITY"
CLAIM_BOUNDARY = (
    "ONE_STATEMENT_COMMITMENT_BINDS_ATTENTION_OUTPUT_AND_D128_BLOCK_INPUT_"
    "NOT_VALUE_EQUALITY_NOT_RECURSIVE_PROOF_NOT_FULL_INFERENCE"
)
BRIDGE_DOMAIN = "ptvm:zkai:attention-output-to-d128-block-input:statement-bridge:v1"
MAX_SOURCE_BYTES = 16 * 1024 * 1024

EXPECTED_ATTENTION = {
    "schema": "zkai-attention-kv-model-faithful-quantized-attention-bridge-gate-v1",
    "decision": "GO_MODEL_FAITHFUL_QUANTIZED_ATTENTION_BRIDGE_FOR_CHECKED_D8_FIXTURE",
    "route_id": "local_model_faithful_quantized_attention_bridge_d8_bounded_softmax_table",
    "claim_boundary": (
        "CHECKED_EQUIVALENCE_BETWEEN_A_MODEL_FACING_INTEGER_ATTENTION_POLICY_AND_THE_EXISTING_"
        "D8_BOUNDED_SOFTMAX_TABLE_FIXTURE_TRACE_NOT_REAL_VALUED_SOFTMAX_NOT_FULL_INFERENCE_NOT_PRODUCTION"
    ),
    "mutations_checked": 20,
    "mutations_rejected": 20,
}

EXPECTED_ACCUMULATOR = {
    "schema": "zkai-d128-full-block-accumulator-backend-v1",
    "decision": "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_BACKEND",
    "result": "GO",
    "accumulator_result": "GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR",
    "recursive_or_pcd_result": "NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING",
    "claim_boundary": "NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF",
    "case_count": 52,
}

EXPECTED_SURFACE = {
    "schema": "zkai-one-transformer-block-surface-v1",
    "decision": "GO_ONE_TRANSFORMER_BLOCK_SURFACE_NO_GO_MATCHED_LAYER_PROOF",
}

NON_CLAIMS = [
    "not proof that the current attention output equals the d128 block input activation",
    "not an adapter from the d8 attention fixture into the d128 block input vector",
    "not one recursive or compressed proof object",
    "not exact real-valued Softmax, LayerNorm, or GELU",
    "not a matched NANOZK/Jolt/DeepProve benchmark",
    "not full autoregressive inference",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_block_statement_bridge_gate.py --write-json docs/engineering/evidence/zkai-attention-block-statement-bridge-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-block-statement-bridge-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_block_statement_bridge_gate",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "bridge_statement",
    "bridge_statement_commitment",
    "source_artifacts",
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
    "bridge_statement_commitment",
    "attention_outputs_commitment",
    "block_input_activation_commitment",
    "current_commitments_equal",
    "feed_equality_status",
    "attention_value_width",
    "block_width",
    "attention_mutations_rejected",
    "block_mutations_rejected",
)


class AttentionBlockStatementBridgeError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionBlockStatementBridgeError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise AttentionBlockStatementBridgeError(f"invalid JSON value: {err}") from err


def blake2b_commitment(value: Any, domain: str) -> str:
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


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def read_source_bytes(path: pathlib.Path) -> bytes:
    root = ROOT.resolve()
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as err:
        raise AttentionBlockStatementBridgeError(f"source path must stay inside repository: {path}") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise AttentionBlockStatementBridgeError(f"source path must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionBlockStatementBridgeError(f"source path must be a repo file: {path}")
        if pre_stat.st_size > MAX_SOURCE_BYTES:
            raise AttentionBlockStatementBridgeError(f"source path exceeds size limit: {path}")
        fd = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if (pre_stat.st_dev, pre_stat.st_ino, pre_stat.st_size) != (
                post_stat.st_dev,
                post_stat.st_ino,
                post_stat.st_size,
            ):
                raise AttentionBlockStatementBridgeError(f"source path changed while reading: {path}")
            return os.read(fd, MAX_SOURCE_BYTES + 1)
        finally:
            os.close(fd)
    except OSError as err:
        raise AttentionBlockStatementBridgeError(f"failed reading source path {path}: {err}") from err


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = read_source_bytes(path)
    try:
        parsed = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise AttentionBlockStatementBridgeError(f"failed parsing JSON source {path}: {err}") from err
    if not isinstance(parsed, dict):
        raise AttentionBlockStatementBridgeError(f"JSON source must be an object: {path}")
    return parsed, raw


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionBlockStatementBridgeError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionBlockStatementBridgeError(f"{label} must be list")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AttentionBlockStatementBridgeError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionBlockStatementBridgeError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionBlockStatementBridgeError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    text = _string(value, label)
    if not (text.startswith("blake2b-256:") or text.startswith("sha256:")):
        raise AttentionBlockStatementBridgeError(f"{label} must be a typed commitment")
    return text


def _source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def _validate_expected(payload: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AttentionBlockStatementBridgeError(f"{label} drift: {key}")


def _load_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    attention, attention_raw = load_json(ATTENTION_BRIDGE)
    accumulator, accumulator_raw = load_json(D128_ACCUMULATOR)
    surface, surface_raw = load_json(ONE_BLOCK_SURFACE)
    source_artifacts = [
        _source_artifact("model_faithful_attention_bridge", ATTENTION_BRIDGE, attention, attention_raw),
        _source_artifact("d128_full_block_accumulator", D128_ACCUMULATOR, accumulator, accumulator_raw),
        _source_artifact("one_transformer_block_surface", ONE_BLOCK_SURFACE, surface, surface_raw),
    ]
    return attention, accumulator, surface, source_artifacts


def build_bridge_statement(attention: dict[str, Any], accumulator: dict[str, Any], surface: dict[str, Any]) -> dict[str, Any]:
    _validate_expected(attention, EXPECTED_ATTENTION, "attention bridge")
    _validate_expected(accumulator, EXPECTED_ACCUMULATOR, "d128 accumulator")
    _validate_expected(surface, EXPECTED_SURFACE, "one-block surface")
    if accumulator.get("all_mutations_rejected") is not True:
        raise AttentionBlockStatementBridgeError("d128 accumulator mutations are not all rejected")
    if "make attention output feed the block receipt input under one statement commitment" not in _list(
        surface.get("next_required_work"), "one-block next_required_work"
    ):
        raise AttentionBlockStatementBridgeError("one-block surface no longer names the bridge follow-up")

    bridge_contract = _dict(attention.get("bridge_contract"), "attention bridge_contract")
    metrics = _dict(bridge_contract.get("metrics"), "attention metrics")
    comparisons = _dict(metrics.get("comparisons"), "attention comparisons")
    if any(value is not True for value in comparisons.values()):
        raise AttentionBlockStatementBridgeError("attention bridge comparisons are not all true")
    attention_outputs = _commitment(metrics.get("fixture_outputs_commitment"), "attention fixture outputs commitment")
    attention_statement = _commitment(metrics.get("fixture_statement_commitment"), "attention statement commitment")
    policy_commitment = _commitment(bridge_contract.get("policy_commitment"), "attention policy commitment")
    attention_width = _int(metrics.get("value_width"), "attention value_width")
    attention_steps = _int(metrics.get("steps"), "attention steps")

    artifact = _dict(accumulator.get("accumulator_artifact"), "accumulator artifact")
    preimage = _dict(artifact.get("preimage"), "accumulator preimage")
    public_inputs = _dict(preimage.get("public_inputs"), "accumulator public inputs")
    transcript = _list(preimage.get("verifier_transcript"), "accumulator verifier transcript")
    if len(transcript) != 6:
        raise AttentionBlockStatementBridgeError("d128 accumulator transcript must contain six slices")
    first_slice = _dict(transcript[0], "d128 first slice")
    if first_slice.get("slice_id") != "rmsnorm_public_rows":
        raise AttentionBlockStatementBridgeError("d128 first slice drift")
    block_input = _commitment(
        _dict(first_slice.get("source_commitments"), "d128 first slice source commitments").get(
            "input_activation_commitment"
        ),
        "d128 input activation commitment",
    )
    block_width = _int(accumulator["summary"].get("slice_count"), "d128 summary slice_count")
    if block_width != 6:
        raise AttentionBlockStatementBridgeError("d128 slice_count drift")
    d128_width = 128
    current_equal = attention_outputs == block_input
    if current_equal:
        raise AttentionBlockStatementBridgeError("attention output unexpectedly equals d128 block input; promote gate")

    statement = {
        "statement_kind": "attention-output-to-d128-block-input-statement-bridge",
        "statement_version": "v1",
        "attention_output": {
            "route_id": attention["route_id"],
            "policy_commitment": policy_commitment,
            "source_statement_commitment": attention_statement,
            "outputs_commitment": attention_outputs,
            "value_width": attention_width,
            "steps": attention_steps,
            "score_rows": _int(metrics.get("score_rows"), "attention score_rows"),
            "fused_proof_size_bytes": _int(metrics.get("fused_proof_size_bytes"), "attention proof bytes"),
            "fused_envelope_size_bytes": _int(metrics.get("fused_envelope_size_bytes"), "attention envelope bytes"),
            "mutations_rejected": attention["mutations_rejected"],
        },
        "d128_block_input": {
            "accumulator_commitment": _commitment(
                accumulator["summary"].get("accumulator_commitment"), "d128 accumulator commitment"
            ),
            "block_receipt_commitment": _commitment(
                public_inputs.get("block_receipt_commitment"), "d128 block receipt commitment"
            ),
            "statement_commitment": _commitment(public_inputs.get("statement_commitment"), "d128 statement commitment"),
            "input_activation_commitment": block_input,
            "width": d128_width,
            "slice_count": len(transcript),
            "total_checked_rows": _int(accumulator["summary"].get("total_checked_rows"), "d128 checked rows"),
            "mutations_rejected": accumulator["case_count"],
        },
        "feed_edge": {
            "from_commitment": attention_outputs,
            "to_commitment": block_input,
            "current_commitments_equal": current_equal,
            "width_adapter_required": attention_width != d128_width,
            "feed_equality_status": "NO_GO_CURRENT_FIXTURES_DO_NOT_BIND_VALUE_EQUALITY",
            "adapter_requirement": (
                "add a checked adapter that consumes the attention output commitment and emits the exact "
                "d128 input_activation_commitment before claiming feed equality"
            ),
        },
        "comparison_context": {
            "one_block_surface_payload_commitment": _commitment(
                surface.get("payload_commitment"), "one-block surface payload commitment"
            ),
            "one_block_surface_decision": surface["decision"],
            "surface_attention_fusion_saving_bytes": _int(
                surface["summary"].get("attention_fusion_saving_bytes"), "surface attention saving"
            ),
            "surface_d128_checked_rows": _int(surface["summary"].get("d128_checked_rows"), "surface d128 rows"),
        },
    }
    return statement


def build_core_payload() -> dict[str, Any]:
    attention, accumulator, surface, source_artifacts = _load_sources()
    statement = build_bridge_statement(attention, accumulator, surface)
    statement_commitment = blake2b_commitment(statement, BRIDGE_DOMAIN)
    summary = {
        "go_result": "GO for one verifier-facing statement commitment binding attention output and d128 block input handles",
        "no_go_result": "NO-GO for value equality, adapter proof, recursion, matched benchmark, or full inference",
        "attention_outputs_commitment": statement["attention_output"]["outputs_commitment"],
        "block_input_activation_commitment": statement["d128_block_input"]["input_activation_commitment"],
        "current_commitments_equal": statement["feed_edge"]["current_commitments_equal"],
        "feed_equality_status": statement["feed_edge"]["feed_equality_status"],
        "adapter_required": statement["feed_edge"]["width_adapter_required"],
        "attention_value_width": statement["attention_output"]["value_width"],
        "block_width": statement["d128_block_input"]["width"],
        "attention_mutations_rejected": statement["attention_output"]["mutations_rejected"],
        "block_mutations_rejected": statement["d128_block_input"]["mutations_rejected"],
        "combined_source_mutation_floor": statement["attention_output"]["mutations_rejected"]
        + statement["d128_block_input"]["mutations_rejected"],
        "bridge_statement_commitment": statement_commitment,
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": source_artifacts,
        "bridge_statement": statement,
        "bridge_statement_commitment": statement_commitment,
        "summary": summary,
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    refresh_payload_commitment(payload)
    return payload


def _comparable(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "payload_commitment"}


def validate_payload(payload: Any, *, expected: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    key_set = set(data)
    if key_set not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionBlockStatementBridgeError(f"unexpected payload keys: {sorted(key_set ^ FINAL_KEYS)}")
    if data.get("schema") != SCHEMA:
        raise AttentionBlockStatementBridgeError("schema drift")
    if data.get("decision") != DECISION:
        raise AttentionBlockStatementBridgeError("decision drift")
    if data.get("result") != RESULT:
        raise AttentionBlockStatementBridgeError("result drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionBlockStatementBridgeError("claim boundary drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise AttentionBlockStatementBridgeError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionBlockStatementBridgeError("validation command drift")
    statement = _dict(data.get("bridge_statement"), "bridge statement")
    expected_statement_commitment = blake2b_commitment(statement, BRIDGE_DOMAIN)
    if data.get("bridge_statement_commitment") != expected_statement_commitment:
        raise AttentionBlockStatementBridgeError("bridge statement commitment drift")
    if _dict(data.get("summary"), "summary").get("bridge_statement_commitment") != expected_statement_commitment:
        raise AttentionBlockStatementBridgeError("summary bridge commitment drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AttentionBlockStatementBridgeError("payload commitment drift")

    feed_edge = _dict(statement.get("feed_edge"), "feed edge")
    if feed_edge.get("current_commitments_equal") is not False:
        raise AttentionBlockStatementBridgeError("feed equality overclaim")
    if feed_edge.get("feed_equality_status") != "NO_GO_CURRENT_FIXTURES_DO_NOT_BIND_VALUE_EQUALITY":
        raise AttentionBlockStatementBridgeError("feed equality status drift")
    if feed_edge.get("width_adapter_required") is not True:
        raise AttentionBlockStatementBridgeError("adapter requirement drift")
    if feed_edge.get("from_commitment") != statement["attention_output"]["outputs_commitment"]:
        raise AttentionBlockStatementBridgeError("attention feed commitment drift")
    if feed_edge.get("to_commitment") != statement["d128_block_input"]["input_activation_commitment"]:
        raise AttentionBlockStatementBridgeError("block input feed commitment drift")

    if expected is not None and _comparable(data) != _comparable(expected):
        raise AttentionBlockStatementBridgeError("payload content drift")

    if key_set == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionBlockStatementBridgeError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionBlockStatementBridgeError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionBlockStatementBridgeError("not all mutations rejected")
        if [case.get("name") for case in cases] != list(EXPECTED_MUTATIONS):
            raise AttentionBlockStatementBridgeError("mutation case order drift")
        for case in cases:
            if case.get("rejected") is not True or case.get("accepted") is not False:
                raise AttentionBlockStatementBridgeError(f"mutation was not rejected: {case.get('name')}")


def _set_payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MutationFn = Callable[[dict[str, Any]], None]


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_drift", lambda p: p.__setitem__("decision", "GO_OVERCLAIM"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_TRANSFORMER_BLOCK_PROOF"), True),
    (
        "attention_output_commitment_drift",
        lambda p: p["bridge_statement"]["attention_output"].__setitem__("outputs_commitment", "blake2b-256:" + "22" * 32),
        True,
    ),
    (
        "block_input_activation_commitment_drift",
        lambda p: p["bridge_statement"]["d128_block_input"].__setitem__(
            "input_activation_commitment", "blake2b-256:" + "33" * 32
        ),
        True,
    ),
    (
        "feed_from_commitment_drift",
        lambda p: p["bridge_statement"]["feed_edge"].__setitem__("from_commitment", "blake2b-256:" + "44" * 32),
        True,
    ),
    (
        "feed_to_commitment_drift",
        lambda p: p["bridge_statement"]["feed_edge"].__setitem__("to_commitment", "blake2b-256:" + "55" * 32),
        True,
    ),
    (
        "feed_equality_overclaim",
        lambda p: p["bridge_statement"]["feed_edge"].__setitem__("current_commitments_equal", True),
        True,
    ),
    (
        "adapter_requirement_removed",
        lambda p: p["bridge_statement"]["feed_edge"].__setitem__("width_adapter_required", False),
        True,
    ),
    (
        "feed_status_promoted",
        lambda p: p["bridge_statement"]["feed_edge"].__setitem__("feed_equality_status", "GO_VALUE_EQUALITY"),
        True,
    ),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("validation_command_removed", lambda p: p.__setitem__("validation_commands", p["validation_commands"][:-1]), True),
    ("source_artifact_sha_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "66" * 32), True),
    ("payload_commitment_drift", _set_payload_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutation_cases(core_payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core_payload)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, expected=core_payload)
        except AttentionBlockStatementBridgeError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result() -> dict[str, Any]:
    core = build_core_payload()
    cases = run_mutation_cases(core)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(EXPECTED_MUTATIONS)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final)
    return final


def to_tsv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    summary = payload["summary"]
    writer.writerow(
        {
            "decision": payload["decision"],
            "result": payload["result"],
            "bridge_statement_commitment": payload["bridge_statement_commitment"],
            "attention_outputs_commitment": summary["attention_outputs_commitment"],
            "block_input_activation_commitment": summary["block_input_activation_commitment"],
            "current_commitments_equal": str(summary["current_commitments_equal"]).lower(),
            "feed_equality_status": summary["feed_equality_status"],
            "attention_value_width": summary["attention_value_width"],
            "block_width": summary["block_width"],
            "attention_mutations_rejected": summary["attention_mutations_rejected"],
            "block_mutations_rejected": summary["block_mutations_rejected"],
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    try:
        candidate.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise AttentionBlockStatementBridgeError(f"output path must stay in docs/engineering/evidence: {path}") from err
    if candidate.suffix != suffix:
        raise AttentionBlockStatementBridgeError(f"output path must end with {suffix}: {path}")
    if candidate.exists() and candidate.is_symlink():
        raise AttentionBlockStatementBridgeError(f"output path must not be symlink: {path}")
    return candidate


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    json_target = require_output_path(json_path, ".json")
    tsv_target = require_output_path(tsv_path, ".tsv")
    if json_target is not None:
        json_target.write_text(pretty_json(payload) + "\n", encoding="utf-8")
    if tsv_target is not None:
        tsv_target.write_text(to_tsv(payload), encoding="utf-8")


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
    except AttentionBlockStatementBridgeError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
