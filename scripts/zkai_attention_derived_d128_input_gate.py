#!/usr/bin/env python3
"""Build a checked d128 input vector derived from the current attention output."""

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
ATTENTION_FIXTURE = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json"
CURRENT_D128_RMSNORM = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
VALUE_ADAPTER_GATE = EVIDENCE_DIR / "zkai-attention-d128-value-adapter-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.tsv"

VALUE_GATE_PATH = ROOT / "scripts" / "zkai_attention_d128_value_adapter_gate.py"
RMSNORM_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"

SCHEMA = "zkai-attention-derived-d128-input-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_INPUT_FIXTURE"
RESULT = "GO_VALUE_CONNECTED_INPUT_ARTIFACT_NO_GO_CURRENT_D128_BLOCK"
CLAIM_BOUNDARY = (
    "CHECKED_PUBLIC_PROJECTION_POLICY_DERIVES_A_NEW_D128_INPUT_FROM_D8_ATTENTION_OUTPUTS_"
    "NOT_MODEL_WEIGHTS_NOT_CURRENT_D128_BLOCK_INPUT"
)
PAYLOAD_DOMAIN = "ptvm:zkai:attention-derived-d128-input:v1"
ADAPTER_POLICY_ID = "fixed_public_two_source_q8_projection_v1"
ADAPTER_POLICY_COMMITMENT_DOMAIN = "ptvm:zkai:attention-derived-d128-input:policy:v1"
DERIVED_INPUT_DOMAIN = "ptvm:zkai:d128-input-activation:v1"
WIDTH = 128
ATTENTION_ROWS = 8
ATTENTION_WIDTH = 8
FLAT_CELLS = ATTENTION_ROWS * ATTENTION_WIDTH
PRIMARY_COEFF = 9
MIX_COEFF = 5
DENOMINATOR = 8

EXPECTED_ATTENTION = {
    "schema": "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-air-proof-input-v1",
    "decision": "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_D8_BOUNDED_SOFTMAX_TABLE_AIR_PROOF",
    "value_width": ATTENTION_WIDTH,
    "sequence_length": ATTENTION_ROWS,
    "outputs_commitment": "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
}

EXPECTED_CURRENT_D128 = {
    "schema": "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
    "decision": "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
    "width": WIDTH,
    "input_activation_commitment": "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78",
}

EXPECTED_VALUE_ADAPTER = {
    "schema": "zkai-attention-d128-value-adapter-gate-v1",
    "decision": "NO_GO_CURRENT_ATTENTION_TO_D128_VALUE_ADAPTER",
    "result": "NO_GO_MODEL_FAITHFUL_VALUE_ADAPTER_MISSING",
}

EXPECTED_SOURCE_ARTIFACTS = (
    ("attention_d8_bounded_softmax_table", ATTENTION_FIXTURE.relative_to(ROOT).as_posix()),
    ("current_d128_rmsnorm_input", CURRENT_D128_RMSNORM.relative_to(ROOT).as_posix()),
    ("attention_d128_value_adapter_gate", VALUE_ADAPTER_GATE.relative_to(ROOT).as_posix()),
)

NON_CLAIMS = [
    "not a learned model projection",
    "not evidence that the existing d128 RMSNorm proof consumed this derived vector",
    "not a full transformer block proof",
    "not a matched NANOZK/Jolt/DeepProve benchmark",
    "not proof-size savings",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_input_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_input_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_input_gate.py scripts/tests/test_zkai_attention_derived_d128_input_gate.py",
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
    "adapter_policy",
    "derived_input",
    "current_d128_comparison",
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
    "adapter_policy_id",
    "source_attention_outputs_commitment",
    "derived_input_activation_commitment",
    "current_d128_input_activation_commitment",
    "matches_current_d128_input",
    "derived_width",
    "derived_min_q8",
    "derived_max_q8",
    "derived_sum_q8",
)


class AttentionDerivedD128InputError(ValueError):
    pass


def _load_module(path: pathlib.Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AttentionDerivedD128InputError(f"failed to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALUE_GATE = _load_module(VALUE_GATE_PATH, "zkai_attention_d128_value_adapter_gate")
RMSNORM = _load_module(RMSNORM_PATH, "zkai_d128_rmsnorm_public_row_proof_input")


def canonical_json_bytes(value: Any) -> bytes:
    return VALUE_GATE.canonical_json_bytes(value)


def pretty_json(value: Any) -> str:
    return VALUE_GATE.pretty_json(value)


def blake2b_commitment(value: Any, domain: str) -> str:
    return VALUE_GATE.blake2b_commitment(value, domain)


def payload_commitment(payload: dict[str, Any]) -> str:
    return VALUE_GATE.payload_commitment(payload)


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128InputError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128InputError(f"{label} must be list")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AttentionDerivedD128InputError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128InputError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128InputError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    text = _string(value, label)
    for prefix in ("blake2b-256:", "sha256:"):
        if text.startswith(prefix):
            digest = text.removeprefix(prefix)
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise AttentionDerivedD128InputError(f"{label} must be a 32-byte lowercase hex digest")
            return text
    raise AttentionDerivedD128InputError(f"{label} must be a typed commitment")


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        return VALUE_GATE.load_json(path)
    except Exception as err:
        raise AttentionDerivedD128InputError(str(err)) from err


def source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def validate_expected(payload: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AttentionDerivedD128InputError(f"{label} drift: {key}")


def load_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    attention, attention_raw = load_json(ATTENTION_FIXTURE)
    current_d128, current_d128_raw = load_json(CURRENT_D128_RMSNORM)
    value_adapter, value_adapter_raw = load_json(VALUE_ADAPTER_GATE)
    return (
        attention,
        current_d128,
        value_adapter,
        [
            source_artifact("attention_d8_bounded_softmax_table", ATTENTION_FIXTURE, attention, attention_raw),
            source_artifact("current_d128_rmsnorm_input", CURRENT_D128_RMSNORM, current_d128, current_d128_raw),
            source_artifact("attention_d128_value_adapter_gate", VALUE_ADAPTER_GATE, value_adapter, value_adapter_raw),
        ],
    )


def validate_source_artifacts(value: Any, expected_artifacts: list[dict[str, Any]]) -> None:
    artifacts = _list(value, "source_artifacts")
    if len(artifacts) != len(EXPECTED_SOURCE_ARTIFACTS):
        raise AttentionDerivedD128InputError("source artifact count drift")
    for index, ((expected_id, expected_path), artifact_value, expected_artifact) in enumerate(
        zip(EXPECTED_SOURCE_ARTIFACTS, artifacts, expected_artifacts, strict=True)
    ):
        artifact = _dict(artifact_value, f"source_artifacts[{index}]")
        if set(artifact) != {"id", "path", "sha256", "payload_sha256"}:
            raise AttentionDerivedD128InputError("source artifact keys drift")
        if artifact.get("id") != expected_id or artifact.get("path") != expected_path:
            raise AttentionDerivedD128InputError("source artifact identity drift")
        if artifact != expected_artifact:
            raise AttentionDerivedD128InputError("source artifact hash drift")


def extract_attention_outputs(attention: dict[str, Any]) -> list[list[int]]:
    outputs = _list(attention.get("attention_outputs"), "attention_outputs")
    if len(outputs) != ATTENTION_ROWS:
        raise AttentionDerivedD128InputError("attention row count drift")
    parsed: list[list[int]] = []
    for row_index, row_value in enumerate(outputs):
        row = _list(row_value, f"attention row {row_index}")
        if len(row) != ATTENTION_WIDTH:
            raise AttentionDerivedD128InputError("attention width drift")
        parsed.append([_int(cell, f"attention row {row_index} cell") for cell in row])
    return parsed


def extract_current_d128_input(current_d128: dict[str, Any]) -> list[int]:
    rows = _list(current_d128.get("rows"), "current d128 rows")
    if len(rows) != WIDTH:
        raise AttentionDerivedD128InputError("current d128 row count drift")
    values: list[int] = []
    for index, row_value in enumerate(rows):
        row = _dict(row_value, f"current d128 row {index}")
        if _int(row.get("index"), f"current d128 row {index} index") != index:
            raise AttentionDerivedD128InputError("current d128 row index drift")
        values.append(_int(row.get("input_q8"), f"current d128 row {index} input_q8"))
    return values


def bias_for_index(index: int) -> int:
    return ((index * 7 + 3) % 9) - 4


def project_attention_to_d128(attention_outputs: list[list[int]]) -> tuple[list[int], list[dict[str, int]]]:
    flat = [cell for row in attention_outputs for cell in row]
    if len(flat) != FLAT_CELLS:
        raise AttentionDerivedD128InputError("attention flat cell count drift")
    outputs: list[int] = []
    rows: list[dict[str, int]] = []
    for index in range(WIDTH):
        primary_index = index % FLAT_CELLS
        mix_index = (index * 17 + 11) % FLAT_CELLS
        primary_value = flat[primary_index]
        mix_value = flat[mix_index]
        bias = bias_for_index(index)
        numerator = PRIMARY_COEFF * primary_value + MIX_COEFF * mix_value + bias
        output_q8 = numerator // DENOMINATOR
        floor_remainder_q8 = numerator - DENOMINATOR * output_q8
        rows.append(
            {
                "index": index,
                "primary_source_index": primary_index,
                "mix_source_index": mix_index,
                "primary_q8": primary_value,
                "mix_q8": mix_value,
                "primary_coeff": PRIMARY_COEFF,
                "mix_coeff": MIX_COEFF,
                "bias_q8": bias,
                "denominator": DENOMINATOR,
                "numerator_q8": numerator,
                "output_q8": output_q8,
                "floor_remainder_q8": floor_remainder_q8,
            }
        )
        outputs.append(output_q8)
    return outputs, rows


def adapter_policy_commitment() -> str:
    return blake2b_commitment(
        {
            "policy_id": ADAPTER_POLICY_ID,
            "input_shape": [ATTENTION_ROWS, ATTENTION_WIDTH],
            "output_width": WIDTH,
            "primary_source_index": "i mod 64",
            "mix_source_index": "(17*i + 11) mod 64",
            "bias_q8": "((7*i + 3) mod 9) - 4",
            "primary_coeff": PRIMARY_COEFF,
            "mix_coeff": MIX_COEFF,
            "denominator": DENOMINATOR,
            "division": "python_floor_integer_division",
        },
        ADAPTER_POLICY_COMMITMENT_DOMAIN,
    )


def sequence_commitment(values: list[int]) -> str:
    return RMSNORM.sequence_commitment(values, DERIVED_INPUT_DOMAIN, WIDTH)


def build_core_context() -> dict[str, Any]:
    attention, current_d128, value_adapter, source_artifacts = load_sources()
    validate_expected(attention, EXPECTED_ATTENTION, "attention fixture")
    validate_expected(current_d128, EXPECTED_CURRENT_D128, "current d128 RMSNorm input")
    validate_expected(value_adapter, EXPECTED_VALUE_ADAPTER, "value adapter gate")
    VALUE_GATE.validate_payload(value_adapter)

    attention_outputs = extract_attention_outputs(attention)
    flat = [cell for row in attention_outputs for cell in row]
    current_input = extract_current_d128_input(current_d128)
    derived_input, projection_rows = project_attention_to_d128(attention_outputs)
    derived_commitment = sequence_commitment(derived_input)
    current_commitment = _commitment(
        current_d128.get("input_activation_commitment"), "current d128 input activation commitment"
    )
    matches_current = derived_input == current_input
    mismatch_count = sum(a != b for a, b in zip(derived_input, current_input, strict=True))
    return {
        "source_artifacts": source_artifacts,
        "adapter_policy": {
            "policy_id": ADAPTER_POLICY_ID,
            "policy_commitment": adapter_policy_commitment(),
            "policy_commitment_domain": ADAPTER_POLICY_COMMITMENT_DOMAIN,
            "input_shape": [ATTENTION_ROWS, ATTENTION_WIDTH],
            "output_width": WIDTH,
            "primary_source_index": "i mod 64",
            "mix_source_index": "(17*i + 11) mod 64",
            "bias_q8": "((7*i + 3) mod 9) - 4",
            "primary_coeff": PRIMARY_COEFF,
            "mix_coeff": MIX_COEFF,
            "denominator": DENOMINATOR,
            "division": "python_floor_integer_division",
        },
        "derived_input": {
            "source_attention_outputs_commitment": _commitment(
                attention.get("outputs_commitment"), "attention outputs commitment"
            ),
            "source_attention_statement_commitment": _commitment(
                attention.get("statement_commitment"), "attention statement commitment"
            ),
            "input_activation_domain": DERIVED_INPUT_DOMAIN,
            "input_activation_commitment": derived_commitment,
            "width": WIDTH,
            "values_q8": derived_input,
            "projection_rows": projection_rows,
            "min_q8": min(derived_input),
            "max_q8": max(derived_input),
            "sum_q8": sum(derived_input),
            "source_min_q8": min(flat),
            "source_max_q8": max(flat),
            "source_sum_q8": sum(flat),
        },
        "current_d128_comparison": {
            "current_input_activation_commitment": current_commitment,
            "derived_matches_current_input_values": matches_current,
            "derived_matches_current_input_commitment": derived_commitment == current_commitment,
            "mismatch_count_against_current": mismatch_count,
            "first_mismatches": [
                {"index": index, "derived": derived, "current": current}
                for index, (derived, current) in enumerate(zip(derived_input, current_input, strict=True))
                if derived != current
            ][:8],
        },
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_core_context() if context is None else context
    summary = {
        "go_result": "GO for a new attention-derived d128 input artifact under a fixed public projection policy",
        "no_go_result": "NO-GO for current d128 block consumption, learned/model weights, proof-size savings, or full block proof",
        "adapter_policy_id": ADAPTER_POLICY_ID,
        "source_attention_outputs_commitment": context["derived_input"]["source_attention_outputs_commitment"],
        "derived_input_activation_commitment": context["derived_input"]["input_activation_commitment"],
        "current_d128_input_activation_commitment": context["current_d128_comparison"][
            "current_input_activation_commitment"
        ],
        "matches_current_d128_input": context["current_d128_comparison"]["derived_matches_current_input_values"],
        "mismatch_count_against_current": context["current_d128_comparison"]["mismatch_count_against_current"],
        "derived_width": WIDTH,
        "derived_min_q8": context["derived_input"]["min_q8"],
        "derived_max_q8": context["derived_input"]["max_q8"],
        "derived_sum_q8": context["derived_input"]["sum_q8"],
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "adapter_policy": copy.deepcopy(context["adapter_policy"]),
        "derived_input": copy.deepcopy(context["derived_input"]),
        "current_d128_comparison": copy.deepcopy(context["current_d128_comparison"]),
        "summary": summary,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_core_payload(
    data: dict[str, Any],
    *,
    expected: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    if set(data) not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128InputError("payload key set drift")
    if data.get("schema") != SCHEMA:
        raise AttentionDerivedD128InputError("schema drift")
    if data.get("decision") != DECISION:
        raise AttentionDerivedD128InputError("decision drift")
    if data.get("result") != RESULT:
        raise AttentionDerivedD128InputError("result drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128InputError("claim boundary drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128InputError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128InputError("validation commands drift")
    context = build_core_context() if context is None else context
    expected_core = build_core_payload(context)
    validate_source_artifacts(data.get("source_artifacts"), context["source_artifacts"])
    comparable = {key: value for key, value in data.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected_without_commitment = {key: value for key, value in expected_core.items() if key != "payload_commitment"}
    if comparable != expected_without_commitment:
        raise AttentionDerivedD128InputError("derived input payload drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AttentionDerivedD128InputError("payload commitment drift")
    if expected is not None:
        expected_comparable = {key: value for key, value in expected.items() if key != "payload_commitment"}
        data_comparable = {key: value for key, value in data.items() if key != "payload_commitment"}
        if data_comparable != expected_comparable:
            raise AttentionDerivedD128InputError("payload content drift")


def validate_payload(
    payload: Any,
    *,
    expected: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    data = _dict(payload, "payload")
    context = build_core_context() if context is None else context
    validate_core_payload(data, expected=expected, context=context)
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128InputError("mutation case count drift")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128InputError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128InputError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionDerivedD128InputError("not all mutations rejected")
        for index, (expected_name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionDerivedD128InputError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AttentionDerivedD128InputError("mutation case order drift")
            if _bool(case.get("accepted"), "mutation accepted") is not False:
                raise AttentionDerivedD128InputError("mutation accepted")
            if _bool(case.get("rejected"), "mutation rejected") is not True:
                raise AttentionDerivedD128InputError("mutation not rejected")
            if not isinstance(case.get("error"), str):
                raise AttentionDerivedD128InputError("mutation error field drift")
        expected_cases = run_mutation_cases(build_core_payload(context), context)
        outcomes = [(case["name"], case["accepted"], case["rejected"]) for case in cases]
        expected_outcomes = [(case["name"], case["accepted"], case["rejected"]) for case in expected_cases]
        if outcomes != expected_outcomes:
            raise AttentionDerivedD128InputError("mutation outcome drift")


def set_payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MutationFn = Callable[[dict[str, Any]], None]

MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted", lambda p: p.__setitem__("decision", "GO_FULL_D128_BLOCK"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "MODEL_FAITHFUL_LEARNED_ADAPTER"), True),
    (
        "source_attention_commitment_drift",
        lambda p: p["derived_input"].__setitem__("source_attention_outputs_commitment", "blake2b-256:" + "22" * 32),
        True,
    ),
    (
        "derived_input_commitment_drift",
        lambda p: p["derived_input"].__setitem__("input_activation_commitment", "blake2b-256:" + "33" * 32),
        True,
    ),
    ("projection_row_output_drift", lambda p: p["derived_input"]["projection_rows"][0].__setitem__("output_q8", 99), True),
    (
        "projection_row_source_index_drift",
        lambda p: p["derived_input"]["projection_rows"][0].__setitem__("primary_source_index", 7),
        True,
    ),
    ("adapter_policy_denominator_drift", lambda p: p["adapter_policy"].__setitem__("denominator", 7), True),
    (
        "current_d128_equality_overclaim",
        lambda p: p["current_d128_comparison"].__setitem__("derived_matches_current_input_values", True),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "44" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", set_payload_commitment_drift, False),
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
            validate_payload(mutated, expected=core_payload, context=context)
        except AttentionDerivedD128InputError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result() -> dict[str, Any]:
    context = build_core_context()
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
            "adapter_policy_id": summary["adapter_policy_id"],
            "source_attention_outputs_commitment": summary["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": summary["derived_input_activation_commitment"],
            "current_d128_input_activation_commitment": summary["current_d128_input_activation_commitment"],
            "matches_current_d128_input": str(summary["matches_current_d128_input"]).lower(),
            "derived_width": summary["derived_width"],
            "derived_min_q8": summary["derived_min_q8"],
            "derived_max_q8": summary["derived_max_q8"],
            "derived_sum_q8": summary["derived_sum_q8"],
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    try:
        return VALUE_GATE.require_output_path(path, suffix)
    except Exception as err:
        raise AttentionDerivedD128InputError(str(err)) from err


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    context = build_core_context()
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
        raise AttentionDerivedD128InputError(str(err)) from err


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
    except AttentionDerivedD128InputError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
