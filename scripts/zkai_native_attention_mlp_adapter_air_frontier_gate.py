#!/usr/bin/env python3
"""Gate the native adapter-AIR frontier for the attention-plus-MLP route."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import stat
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

DERIVED_INPUT_PATH = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.json"
SINGLE_PROOF_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-single-proof-2026-05.json"
LIFTING_ABLATION_PATH = EVIDENCE_DIR / "zkai-native-attention-mlp-lifting-ablation-2026-05.json"

JSON_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-adapter-air-frontier-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-native-attention-mlp-adapter-air-frontier-2026-05.tsv"

SCHEMA = "zkai-native-attention-mlp-adapter-air-frontier-gate-v1"
DECISION = "NARROW_CLAIM_NATIVE_ADAPTER_AIR_FRONTIER_PINNED"
RESULT = "GO_CONSTRAINT_SURFACE_READY_NO_GO_SIZE_BREAKTHROUGH"
ISSUE = "https://github.com/omarespejel/provable-transformer-vm/issues/603"
ROUTE_ID = "native_attention_mlp_adapter_air_frontier_v1"
CLAIM_BOUNDARY = (
    "PINS_THE_EXACT_NATIVE_AIR_CONSTRAINT_SURFACE_FOR_THE_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER_"
    "WITHOUT_REGENERATING_A_STWO_PROOF_OR_CLAIMING_PROOF_SIZE_IMPROVEMENT"
)
PAYLOAD_DOMAIN = "ptvm:zkai:native-attention-mlp-adapter-air-frontier:v1"
DERIVED_INPUT_DOMAIN = "ptvm:zkai:d128-input-activation:v1"

WIDTH = 128
ATTENTION_FLAT_CELLS = 64
ADAPTER_LOG_SIZE = 7
PRIMARY_COEFF = 9
MIX_COEFF = 5
DENOMINATOR = 8
REMAINDER_BITS = 3
NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES = 6_900
MAX_JSON_BYTES = 16 * 1024 * 1024

EXPECTED_DERIVED_INPUT = {
    "schema": "zkai-attention-derived-d128-input-gate-v1",
    "decision": "GO_ATTENTION_DERIVED_D128_INPUT_FIXTURE",
    "result": "GO_VALUE_CONNECTED_INPUT_ARTIFACT_NO_GO_CURRENT_D128_BLOCK",
    "adapter_policy_id": "fixed_public_two_source_q8_projection_v1",
    "source_attention_outputs_commitment": "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
    "derived_input_activation_commitment": "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35",
    "derived_width": WIDTH,
    "derived_min_q8": -4,
    "derived_max_q8": 5,
    "derived_sum_q8": 104,
}

EXPECTED_SINGLE = {
    "schema": "zkai-native-attention-mlp-single-proof-object-gate-v1",
    "decision": "GO_NATIVE_ATTENTION_MLP_SINGLE_STWO_PROOF_OBJECT_VERIFIES",
    "result": "NARROW_CLAIM_SINGLE_PROOF_OBJECT_BARELY_BEATS_TWO_PROOF_FRONTIER",
    "adapter_status": "STATEMENT_BOUND_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER_NOT_NATIVE_AIR",
    "single_proof_typed_bytes": 40_668,
    "two_proof_frontier_typed_bytes": 40_700,
    "typed_saving_vs_two_proof_bytes": 32,
    "typed_gap_to_nanozk_reported_bytes": 33_768,
}

EXPECTED_LIFTING = {
    "schema": "zkai-native-attention-mlp-lifting-ablation-gate-v1",
    "decision": "NO_GO_LIFTING_ONLY_BREAKTHROUGH_FOR_NATIVE_ATTENTION_MLP_SINGLE_PROOF",
    "result": "NARROW_CLAIM_FRI_DECOMMITMENT_OVERHANG_IS_REAL_BUT_TOO_SMALL",
    "projected_typed_bytes_without_fri_overhang": 40_028,
    "projected_gap_to_nanozk_reported_bytes": 33_128,
    "next_attack": "native_adapter_air_or_query_value_reduction_or_boundary_restructure",
}

ADAPTER_COLUMNS = (
    "row_index",
    "primary_source_index",
    "mix_source_index",
    "primary_q8",
    "mix_q8",
    "bias_q8",
    "numerator_q8",
    "output_q8",
    "floor_remainder_q8",
)

CONSTRAINTS = (
    "row_index_equals_public_column",
    "primary_source_index_equals_i_mod_64",
    "mix_source_index_equals_17i_plus_11_mod_64",
    "primary_q8_equals_selected_attention_output",
    "mix_q8_equals_selected_attention_output",
    "bias_q8_equals_7i_plus_3_mod_9_minus_4",
    "numerator_q8_equals_9_primary_plus_5_mix_plus_bias",
    "numerator_q8_equals_8_output_plus_floor_remainder",
    "floor_remainder_q8_decomposes_into_three_boolean_bits",
    "output_q8_commitment_equals_d128_rmsnorm_input_activation_commitment",
)

NON_CLAIMS = (
    "not a regenerated Stwo proof with the adapter component included",
    "not proof-size savings",
    "not a NANOZK proof-size win",
    "not a matched NANOZK workload or benchmark",
    "not exact real-valued Softmax",
    "not full transformer block inference",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
)

VALIDATION_COMMANDS = (
    "python3 scripts/zkai_native_attention_mlp_adapter_air_frontier_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-adapter-air-frontier-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-adapter-air-frontier-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_native_attention_mlp_adapter_air_frontier_gate.py scripts/tests/test_zkai_native_attention_mlp_adapter_air_frontier_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_adapter_air_frontier_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
)


def expected_bias_q8(index: int) -> int:
    return ((7 * index + 3) % 9) - 4


CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "issue",
    "route_id",
    "claim_boundary",
    "source_artifacts",
    "adapter_air_candidate",
    "budget",
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
    "native_adapter_air_status",
    "adapter_rows",
    "adapter_columns",
    "adapter_trace_cells",
    "constraint_count",
    "single_proof_typed_bytes",
    "two_proof_frontier_typed_bytes",
    "typed_slack_vs_two_proof_bytes",
    "max_adapter_overhead_for_size_win_bytes",
    "nanozk_reported_d128_block_proof_bytes",
    "current_gap_to_nanozk_reported_bytes",
    "correctness_next_step",
)


class AdapterAirFrontierError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AdapterAirFrontierError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    digest = hashlib.blake2b(digest_size=32)
    digest.update(PAYLOAD_DOMAIN.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(material))
    return "blake2b-256:" + digest.hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdapterAirFrontierError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AdapterAirFrontierError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AdapterAirFrontierError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AdapterAirFrontierError(f"{label} must be boolean")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdapterAirFrontierError(f"{label} must be non-empty string")
    return value


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def sequence_commitment(values: list[int]) -> str:
    values_json = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    values_sha256 = hashlib.sha256(values_json).hexdigest()
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": [WIDTH],
            "values_sha256": values_sha256,
        },
        DERIVED_INPUT_DOMAIN,
    )


def read_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if evidence_root not in resolved.parents and resolved != evidence_root:
        raise AdapterAirFrontierError(f"{label} path must stay under docs/engineering/evidence")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as err:
        raise AdapterAirFrontierError(f"failed to open {label} {path}: {err}") from err
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise AdapterAirFrontierError(f"{label} must be a regular file")
        if before.st_size > MAX_JSON_BYTES:
            raise AdapterAirFrontierError(f"{label} exceeds max size")
        chunks: list[bytes] = []
        remaining = MAX_JSON_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_JSON_BYTES:
            raise AdapterAirFrontierError(f"{label} exceeds max size")
        after = os.fstat(fd)
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise AdapterAirFrontierError(f"{label} changed while reading")
    finally:
        os.close(fd)
    try:
        payload = json.loads(
            raw,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                AdapterAirFrontierError(f"{label} contains non-finite JSON constant {constant}")
            ),
        )
    except json.JSONDecodeError as err:
        raise AdapterAirFrontierError(f"failed to parse {label}: {err}") from err
    return _dict(payload, label), raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def load_sources() -> dict[str, Any]:
    derived, derived_raw = read_json(DERIVED_INPUT_PATH, "derived input gate")
    single, single_raw = read_json(SINGLE_PROOF_PATH, "single proof gate")
    lifting, lifting_raw = read_json(LIFTING_ABLATION_PATH, "lifting ablation gate")
    return {
        "derived": derived,
        "single": single,
        "lifting": lifting,
        "source_artifacts": [
            source_artifact("attention_derived_d128_input_gate", DERIVED_INPUT_PATH, derived, derived_raw),
            source_artifact("native_attention_mlp_single_proof_gate", SINGLE_PROOF_PATH, single, single_raw),
            source_artifact("native_attention_mlp_lifting_ablation_gate", LIFTING_ABLATION_PATH, lifting, lifting_raw),
        ],
    }


def validate_expected_sources(sources: dict[str, Any]) -> None:
    derived_summary = _dict(sources["derived"].get("summary"), "derived input summary")
    for key, expected in EXPECTED_DERIVED_INPUT.items():
        actual = sources["derived"].get(key) if key in {"schema", "decision", "result"} else derived_summary.get(key)
        if actual != expected:
            raise AdapterAirFrontierError(f"derived input {key} drift")
    validate_derived_input_commitment(sources["derived"])
    single_summary = _dict(sources["single"].get("summary"), "single proof summary")
    for key, expected in EXPECTED_SINGLE.items():
        actual = sources["single"].get(key) if key in {"schema", "decision", "result"} else single_summary.get(key)
        if actual != expected:
            raise AdapterAirFrontierError(f"single proof {key} drift")
    lifting_summary = _dict(sources["lifting"].get("summary"), "lifting summary")
    for key, expected in EXPECTED_LIFTING.items():
        actual = sources["lifting"].get(key) if key in {"schema", "decision", "result"} else lifting_summary.get(key)
        if actual != expected:
            raise AdapterAirFrontierError(f"lifting {key} drift")


def validate_derived_input_commitment(derived: dict[str, Any]) -> None:
    derived_input = _dict(derived.get("derived_input"), "derived input")
    if _str(derived_input.get("input_activation_domain"), "derived input activation domain") != DERIVED_INPUT_DOMAIN:
        raise AdapterAirFrontierError("derived input activation domain drift")
    declared = _str(derived_input.get("input_activation_commitment"), "derived input activation commitment")
    if declared != EXPECTED_DERIVED_INPUT["derived_input_activation_commitment"]:
        raise AdapterAirFrontierError("derived input activation commitment drift")
    values = [_int(value, f"derived value {index}") for index, value in enumerate(_list(derived_input.get("values_q8"), "derived values"))]
    if len(values) != WIDTH:
        raise AdapterAirFrontierError("derived value count drift")
    if declared != sequence_commitment(values):
        raise AdapterAirFrontierError("derived input activation commitment mismatch")


def projection_rows(derived: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _list(_dict(derived.get("derived_input"), "derived input").get("projection_rows"), "projection rows")
    if len(rows) != WIDTH:
        raise AdapterAirFrontierError("adapter projection row count drift")
    return [_dict(row, f"projection row {index}") for index, row in enumerate(rows)]


def validate_projection_rows(derived: dict[str, Any]) -> dict[str, Any]:
    rows = projection_rows(derived)
    min_remainder: int | None = None
    max_remainder: int | None = None
    values: list[int] = []
    for index, row in enumerate(rows):
        if _int(row.get("index"), f"row {index} index") != index:
            raise AdapterAirFrontierError("projection row index drift")
        primary_source = _int(row.get("primary_source_index"), f"row {index} primary source")
        mix_source = _int(row.get("mix_source_index"), f"row {index} mix source")
        primary = _int(row.get("primary_q8"), f"row {index} primary")
        mix = _int(row.get("mix_q8"), f"row {index} mix")
        bias = _int(row.get("bias_q8"), f"row {index} bias")
        numerator = _int(row.get("numerator_q8"), f"row {index} numerator")
        output = _int(row.get("output_q8"), f"row {index} output")
        floor_remainder = _int(row.get("floor_remainder_q8"), f"row {index} floor remainder")
        denominator = _int(row.get("denominator"), f"row {index} denominator")
        if primary_source != index % ATTENTION_FLAT_CELLS:
            raise AdapterAirFrontierError("primary source policy drift")
        if mix_source != (17 * index + 11) % ATTENTION_FLAT_CELLS:
            raise AdapterAirFrontierError("mix source policy drift")
        if bias != expected_bias_q8(index):
            raise AdapterAirFrontierError("bias policy drift")
        if row.get("primary_coeff") != PRIMARY_COEFF or row.get("mix_coeff") != MIX_COEFF:
            raise AdapterAirFrontierError("adapter coefficient drift")
        if denominator != DENOMINATOR:
            raise AdapterAirFrontierError("adapter denominator drift")
        if numerator != PRIMARY_COEFF * primary + MIX_COEFF * mix + bias:
            raise AdapterAirFrontierError("adapter numerator relation drift")
        remainder = numerator - denominator * output
        if floor_remainder != remainder:
            raise AdapterAirFrontierError("adapter floor remainder drift")
        if not 0 <= remainder < denominator:
            raise AdapterAirFrontierError("adapter floor remainder outside denominator range")
        min_remainder = remainder if min_remainder is None else min(min_remainder, remainder)
        max_remainder = remainder if max_remainder is None else max(max_remainder, remainder)
        values.append(output)
    derived_values = _list(_dict(derived.get("derived_input"), "derived input").get("values_q8"), "derived values")
    if values != [_int(value, "derived value") for value in derived_values]:
        raise AdapterAirFrontierError("adapter output vector does not match derived d128 input")
    return {
        "row_count": len(rows),
        "min_floor_remainder_q8": min_remainder,
        "max_floor_remainder_q8": max_remainder,
        "remainder_bits": REMAINDER_BITS,
        "all_remainders_fit_three_bits": max_remainder is not None and max_remainder < 2**REMAINDER_BITS,
        "output_sum_q8": sum(values),
        "output_min_q8": min(values),
        "output_max_q8": max(values),
    }


def build_payload() -> dict[str, Any]:
    sources = load_sources()
    validate_expected_sources(sources)
    projection = validate_projection_rows(sources["derived"])
    single_summary = _dict(sources["single"]["summary"], "single proof summary")
    lifting_summary = _dict(sources["lifting"]["summary"], "lifting summary")
    typed_slack = single_summary["two_proof_frontier_typed_bytes"] - single_summary["single_proof_typed_bytes"]
    adapter_trace_cells = WIDTH * (len(ADAPTER_COLUMNS) + REMAINDER_BITS)
    candidate = {
        "status": "READY_FOR_NATIVE_AIR_IMPLEMENTATION",
        "native_adapter_air_proven_in_current_artifact": False,
        "policy_id": EXPECTED_DERIVED_INPUT["adapter_policy_id"],
        "source_attention_outputs_commitment": EXPECTED_DERIVED_INPUT["source_attention_outputs_commitment"],
        "output_d128_input_activation_commitment": EXPECTED_DERIVED_INPUT["derived_input_activation_commitment"],
        "log_size": ADAPTER_LOG_SIZE,
        "rows": projection["row_count"],
        "columns": list(ADAPTER_COLUMNS),
        "column_count": len(ADAPTER_COLUMNS),
        "remainder_bit_columns": REMAINDER_BITS,
        "trace_cells": adapter_trace_cells,
        "constraints": list(CONSTRAINTS),
        "constraint_count": len(CONSTRAINTS),
        "projection_row_summary": projection,
    }
    budget = {
        "single_proof_typed_bytes": single_summary["single_proof_typed_bytes"],
        "two_proof_frontier_typed_bytes": single_summary["two_proof_frontier_typed_bytes"],
        "typed_slack_vs_two_proof_bytes": typed_slack,
        "max_adapter_overhead_for_size_win_bytes": typed_slack,
        "native_adapter_air_size_breakthrough_gate": "NO_GO_UNTIL_REPROVEN_OVERHEAD_IS_AT_MOST_32_TYPED_BYTES",
        "correctness_next_step": "implement the adapter component in the one-proof Stwo object even if typed bytes increase",
        "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "current_gap_to_nanozk_reported_bytes": single_summary["typed_gap_to_nanozk_reported_bytes"],
        "projected_gap_after_lifting_only_bytes": lifting_summary["projected_gap_to_nanozk_reported_bytes"],
    }
    summary = {
        "native_adapter_air_status": candidate["status"],
        "native_adapter_air_proven_in_current_artifact": False,
        "adapter_rows": candidate["rows"],
        "adapter_columns": candidate["column_count"],
        "adapter_trace_cells": candidate["trace_cells"],
        "constraint_count": candidate["constraint_count"],
        "adapter_outputs_match_d128_input_commitment": True,
        "all_remainders_fit_three_bits": projection["all_remainders_fit_three_bits"],
        "single_proof_typed_bytes": budget["single_proof_typed_bytes"],
        "two_proof_frontier_typed_bytes": budget["two_proof_frontier_typed_bytes"],
        "typed_slack_vs_two_proof_bytes": typed_slack,
        "max_adapter_overhead_for_size_win_bytes": typed_slack,
        "nanozk_reported_d128_block_proof_bytes": NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "current_gap_to_nanozk_reported_bytes": budget["current_gap_to_nanozk_reported_bytes"],
        "native_adapter_air_size_breakthrough_status": "NO_GO",
        "next_attack": "implement_adapter_air_then_measure_real_typed_overhead",
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "route_id": ROUTE_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": sources["source_artifacts"],
        "adapter_air_candidate": candidate,
        "budget": budget,
        "summary": summary,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any) -> None:
    data = _dict(payload, "payload")
    if set(data) not in (CORE_KEYS, FINAL_KEYS):
        raise AdapterAirFrontierError("payload key set drift")
    if data.get("schema") != SCHEMA:
        raise AdapterAirFrontierError("schema drift")
    if data.get("decision") != DECISION:
        raise AdapterAirFrontierError("decision drift")
    if data.get("result") != RESULT:
        raise AdapterAirFrontierError("result drift")
    if data.get("issue") != ISSUE:
        raise AdapterAirFrontierError("issue drift")
    if data.get("route_id") != ROUTE_ID:
        raise AdapterAirFrontierError("route id drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AdapterAirFrontierError("claim boundary drift")
    if data.get("non_claims") != list(NON_CLAIMS):
        raise AdapterAirFrontierError("non-claims drift")
    if data.get("validation_commands") != list(VALIDATION_COMMANDS):
        raise AdapterAirFrontierError("validation commands drift")
    summary = _dict(data.get("summary"), "summary")
    if _bool(summary.get("native_adapter_air_proven_in_current_artifact"), "native adapter proven") is not False:
        raise AdapterAirFrontierError("native adapter AIR overclaim")
    if summary.get("native_adapter_air_size_breakthrough_status") != "NO_GO":
        raise AdapterAirFrontierError("native adapter size breakthrough overclaim")
    if _int(summary.get("max_adapter_overhead_for_size_win_bytes"), "adapter overhead budget") != 32:
        raise AdapterAirFrontierError("adapter overhead budget drift")
    expected = build_payload()
    for key in CORE_KEYS - {"payload_commitment"}:
        if data.get(key) != expected.get(key):
            raise AdapterAirFrontierError(f"{key} drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AdapterAirFrontierError("payload commitment drift")
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(MUTATION_NAMES):
            raise AdapterAirFrontierError("mutation inventory drift")
        if data.get("case_count") != len(MUTATION_NAMES) or len(cases) != len(MUTATION_NAMES):
            raise AdapterAirFrontierError("mutation case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AdapterAirFrontierError("not all mutations rejected")
        for expected_name, case_value in zip(MUTATION_NAMES, cases, strict=True):
            case = _dict(case_value, "mutation case")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AdapterAirFrontierError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AdapterAirFrontierError("mutation case order drift")
            if case.get("accepted") is not False:
                raise AdapterAirFrontierError("mutation accepted")
            if case.get("rejected") is not True:
                raise AdapterAirFrontierError("mutation not rejected")


MutationFn = Callable[[dict[str, Any]], None]


def _payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "blake2b-256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted_to_full_block", lambda p: p.__setitem__("decision", "GO_FULL_TRANSFORMER_BLOCK"), True),
    (
        "adapter_air_marked_proven",
        lambda p: p["summary"].__setitem__("native_adapter_air_proven_in_current_artifact", True),
        True,
    ),
    (
        "adapter_size_breakthrough_overclaim",
        lambda p: p["summary"].__setitem__("native_adapter_air_size_breakthrough_status", "GO"),
        True,
    ),
    (
        "adapter_slack_inflated",
        lambda p: p["budget"].__setitem__("max_adapter_overhead_for_size_win_bytes", 4096),
        True,
    ),
    (
        "source_attention_commitment_drift",
        lambda p: p["adapter_air_candidate"].__setitem__(
            "source_attention_outputs_commitment", "blake2b-256:" + "22" * 32
        ),
        True,
    ),
    (
        "output_commitment_drift",
        lambda p: p["adapter_air_candidate"].__setitem__(
            "output_d128_input_activation_commitment", "blake2b-256:" + "33" * 32
        ),
        True,
    ),
    (
        "constraint_removed",
        lambda p: p["adapter_air_candidate"].__setitem__("constraints", p["adapter_air_candidate"]["constraints"][1:]),
        True,
    ),
    (
        "remainder_bits_weakened",
        lambda p: p["adapter_air_candidate"].__setitem__("remainder_bit_columns", 0),
        True,
    ),
    ("nanozk_gap_erased", lambda p: p["summary"].__setitem__("current_gap_to_nanozk_reported_bytes", 0), True),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "44" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", _payload_commitment_drift, False),
)

MUTATION_NAMES = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutations(core: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated)
        except AdapterAirFrontierError as err:
            cases.append({"name": name, "accepted": False, "rejected": True, "error": str(err)})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result() -> dict[str, Any]:
    core = build_payload()
    cases = run_mutations(core)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(MUTATION_NAMES)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final)
    return final


def to_tsv(payload: dict[str, Any]) -> str:
    validate_payload(payload)
    summary = _dict(payload["summary"], "summary")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow({key: summary[key] for key in TSV_COLUMNS if key in summary} | {"decision": payload["decision"], "result": payload["result"], "correctness_next_step": payload["budget"]["correctness_next_step"]})
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    candidate = ROOT / path if not path.is_absolute() else path
    resolved_parent = candidate.parent.resolve()
    resolved = resolved_parent / candidate.name
    evidence_root = EVIDENCE_DIR.resolve()
    if evidence_root not in resolved.parents:
        raise AdapterAirFrontierError("output path must stay under docs/engineering/evidence")
    if resolved.suffix != suffix:
        raise AdapterAirFrontierError(f"output path must end with {suffix}")
    return resolved


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise AdapterAirFrontierError("refusing to write through symlink")
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_path = parent / f".{path.name}.tmp-{os.getpid()}"
    try:
        with open(temp_path, "x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    out_json = require_output_path(json_path, ".json")
    out_tsv = require_output_path(tsv_path, ".tsv")
    if out_json is not None:
        write_text_atomic(out_json, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    if out_tsv is not None:
        write_text_atomic(out_tsv, to_tsv(payload))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path)
    parser.add_argument("--write-tsv", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
