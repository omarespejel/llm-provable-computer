#!/usr/bin/env python3
"""Check whether the current attention output can feed the d128 block input."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
import pathlib
import secrets
import stat as stat_module
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
ATTENTION_FIXTURE = EVIDENCE_DIR / "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json"
D128_RMSNORM_INPUT = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
STATEMENT_BRIDGE = EVIDENCE_DIR / "zkai-attention-block-statement-bridge-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-d128-value-adapter-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-d128-value-adapter-2026-05.tsv"

SCHEMA = "zkai-attention-d128-value-adapter-gate-v1"
DECISION = "NO_GO_CURRENT_ATTENTION_TO_D128_VALUE_ADAPTER"
RESULT = "NO_GO_MODEL_FAITHFUL_VALUE_ADAPTER_MISSING"
CLAIM_BOUNDARY = (
    "CURRENT_D8_ATTENTION_AND_D128_BLOCK_FIXTURES_ARE_STATEMENT_BOUND_BUT_NOT_VALUE_CONNECTED_"
    "NO_ARBITRARY_LEARNED_PROJECTION_NO_MODEL_FAITHFUL_ADAPTER_YET"
)
PAYLOAD_DOMAIN = "ptvm:zkai:attention-output-to-d128-block-input:value-adapter-feasibility:v1"
MAX_SOURCE_BYTES = 16 * 1024 * 1024

EXPECTED_SOURCE_ARTIFACTS = (
    ("attention_d8_bounded_softmax_table", ATTENTION_FIXTURE.relative_to(ROOT).as_posix()),
    ("d128_rmsnorm_input", D128_RMSNORM_INPUT.relative_to(ROOT).as_posix()),
    ("attention_block_statement_bridge", STATEMENT_BRIDGE.relative_to(ROOT).as_posix()),
)

EXPECTED_ATTENTION = {
    "schema": "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-air-proof-input-v1",
    "decision": "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_D8_BOUNDED_SOFTMAX_TABLE_AIR_PROOF",
    "value_width": 8,
    "sequence_length": 8,
    "outputs_commitment": "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638",
}

EXPECTED_D128 = {
    "schema": "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
    "decision": "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
    "width": 128,
    "input_activation_commitment": "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78",
}

EXPECTED_BRIDGE = {
    "schema": "zkai-attention-block-statement-bridge-v1",
    "decision": "GO_STATEMENT_BRIDGE_NO_GO_ATTENTION_TO_BLOCK_VALUE_EQUALITY",
    "result": "GO_STATEMENT_COMMITMENT_BINDING_WITH_NO_GO_VALUE_EQUALITY",
    "bridge_statement_commitment": "blake2b-256:f180e809c0b0329bc340b34864d8067d6dfa9c4335471ba6adec94e203ec4d2e",
}

NON_CLAIMS = [
    "not proof that attention output equals the d128 block input",
    "not a learned projection or model-faithful adapter",
    "not evidence that the current d128 block consumes attention values",
    "not a recursive or compressed proof object",
    "not a matched NANOZK/Jolt/DeepProve benchmark",
    "not full transformer inference",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_d128_value_adapter_gate.py --write-json docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_d128_value_adapter_gate",
    "python3 -m py_compile scripts/zkai_attention_d128_value_adapter_gate.py scripts/tests/test_zkai_attention_d128_value_adapter_gate.py",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "adapter_analysis",
    "adapter_analysis_commitment",
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
    "attention_outputs_commitment",
    "d128_input_activation_commitment",
    "attention_cells",
    "target_width",
    "best_candidate_id",
    "best_candidate_mismatches",
    "best_candidate_mean_abs_error",
    "target_matches_synthetic_pattern",
)


class AttentionD128ValueAdapterError(ValueError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise AttentionD128ValueAdapterError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise AttentionD128ValueAdapterError(f"invalid JSON value: {err}") from err


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
        raise AttentionD128ValueAdapterError(f"source path must stay inside repository: {path}") from err

    current = root
    pre_stat = None
    try:
        for part in relative.parts:
            current = current / part
            part_stat = current.lstat()
            if stat_module.S_ISLNK(part_stat.st_mode):
                raise AttentionD128ValueAdapterError(f"source path must not traverse symlinks: {path}")
            pre_stat = part_stat
        if pre_stat is None or not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionD128ValueAdapterError(f"source path must be a repo file: {path}")
        if pre_stat.st_size > MAX_SOURCE_BYTES:
            raise AttentionD128ValueAdapterError(f"source path exceeds size limit: {path}")
        fd = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if (pre_stat.st_dev, pre_stat.st_ino, pre_stat.st_size) != (
                post_stat.st_dev,
                post_stat.st_ino,
                post_stat.st_size,
            ):
                raise AttentionD128ValueAdapterError(f"source path changed while reading: {path}")
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionD128ValueAdapterError(f"source path must remain a regular file: {path}")
            raw = os.read(fd, MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise AttentionD128ValueAdapterError(f"source path exceeds size limit after open: {path}")
            return raw
        finally:
            os.close(fd)
    except OSError as err:
        raise AttentionD128ValueAdapterError(f"failed reading source path {path}: {err}") from err


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = read_source_bytes(path)
    try:
        parsed = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise AttentionD128ValueAdapterError(f"failed parsing JSON source {path}: {err}") from err
    if not isinstance(parsed, dict):
        raise AttentionD128ValueAdapterError(f"JSON source must be an object: {path}")
    return parsed, raw


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionD128ValueAdapterError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionD128ValueAdapterError(f"{label} must be list")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AttentionD128ValueAdapterError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionD128ValueAdapterError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionD128ValueAdapterError(f"{label} must be boolean")
    return value


def _number(value: Any, label: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise AttentionD128ValueAdapterError(f"{label} must be a finite number")
    return value


def _hex_digest(value: Any, label: str) -> str:
    text = _string(value, label)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise AttentionD128ValueAdapterError(f"{label} must use a 32-byte lowercase hex digest")
    return text


def _commitment(value: Any, label: str) -> str:
    text = _string(value, label)
    for prefix in ("blake2b-256:", "sha256:"):
        if text.startswith(prefix):
            _hex_digest(text.removeprefix(prefix), label)
            return text
    raise AttentionD128ValueAdapterError(f"{label} must be a typed commitment")


def _source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def _validate_source_artifacts(value: Any, *, expected_artifacts: list[dict[str, Any]]) -> None:
    artifacts = _list(value, "source_artifacts")
    if len(artifacts) != len(EXPECTED_SOURCE_ARTIFACTS):
        raise AttentionD128ValueAdapterError("source_artifacts count drift")
    if len(expected_artifacts) != len(EXPECTED_SOURCE_ARTIFACTS):
        raise AttentionD128ValueAdapterError("expected source_artifacts count drift")
    for index, ((expected_id, expected_path), artifact_value, expected_artifact) in enumerate(
        zip(EXPECTED_SOURCE_ARTIFACTS, artifacts, expected_artifacts, strict=True)
    ):
        label = f"source_artifacts[{index}]"
        artifact = _dict(artifact_value, label)
        if set(artifact) != {"id", "path", "sha256", "payload_sha256"}:
            raise AttentionD128ValueAdapterError(f"{label} keys drift")
        if artifact.get("id") != expected_id:
            raise AttentionD128ValueAdapterError(f"{label} id drift")
        path = _string(artifact.get("path"), f"{label} path")
        parsed_path = pathlib.PurePosixPath(path)
        if parsed_path.is_absolute() or ".." in parsed_path.parts:
            raise AttentionD128ValueAdapterError(f"{label} path must be repo-relative")
        if path != expected_path:
            raise AttentionD128ValueAdapterError(f"{label} path drift")
        if not path.startswith("docs/engineering/evidence/") or not path.endswith(".json"):
            raise AttentionD128ValueAdapterError(f"{label} path must be evidence JSON")
        _hex_digest(artifact.get("sha256"), f"{label} sha256")
        _hex_digest(artifact.get("payload_sha256"), f"{label} payload_sha256")
        if artifact != expected_artifact:
            raise AttentionD128ValueAdapterError(f"{label} hash drift")


def _validate_expected(payload: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AttentionD128ValueAdapterError(f"{label} drift: {key}")


def _load_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    attention, attention_raw = load_json(ATTENTION_FIXTURE)
    d128_input, d128_raw = load_json(D128_RMSNORM_INPUT)
    bridge, bridge_raw = load_json(STATEMENT_BRIDGE)
    return (
        attention,
        d128_input,
        bridge,
        [
            _source_artifact("attention_d8_bounded_softmax_table", ATTENTION_FIXTURE, attention, attention_raw),
            _source_artifact("d128_rmsnorm_input", D128_RMSNORM_INPUT, d128_input, d128_raw),
            _source_artifact("attention_block_statement_bridge", STATEMENT_BRIDGE, bridge, bridge_raw),
        ],
    )


def _extract_attention_outputs(attention: dict[str, Any]) -> list[list[int]]:
    outputs = _list(attention.get("attention_outputs"), "attention outputs")
    if len(outputs) != EXPECTED_ATTENTION["sequence_length"]:
        raise AttentionD128ValueAdapterError("attention output step count drift")
    parsed: list[list[int]] = []
    for row_index, row_value in enumerate(outputs):
        row = _list(row_value, f"attention output row {row_index}")
        if len(row) != EXPECTED_ATTENTION["value_width"]:
            raise AttentionD128ValueAdapterError(f"attention output row width drift: {row_index}")
        parsed.append([_int(cell, f"attention output row {row_index} cell") for cell in row])
    return parsed


def _extract_d128_input(d128_input: dict[str, Any]) -> list[int]:
    rows = _list(d128_input.get("rows"), "d128 rows")
    if len(rows) != EXPECTED_D128["width"]:
        raise AttentionD128ValueAdapterError("d128 input row count drift")
    values: list[int] = []
    for index, row_value in enumerate(rows):
        row = _dict(row_value, f"d128 row {index}")
        if _int(row.get("index"), f"d128 row {index} index") != index:
            raise AttentionD128ValueAdapterError(f"d128 row index drift: {index}")
        values.append(_int(row.get("input_q8"), f"d128 row {index} input_q8"))
    return values


def _score_candidate(candidate_id: str, description: str, values: list[int], target: list[int]) -> dict[str, Any]:
    if len(values) != len(target):
        raise AttentionD128ValueAdapterError(f"candidate width drift: {candidate_id}")
    mismatches = [
        {"index": index, "candidate": candidate, "target": target_value}
        for index, (candidate, target_value) in enumerate(zip(values, target, strict=True))
        if candidate != target_value
    ]
    total_abs_error = sum(abs(candidate - target_value) for candidate, target_value in zip(values, target, strict=True))
    return {
        "id": candidate_id,
        "description": description,
        "output_width": len(values),
        "exact_match": len(mismatches) == 0,
        "mismatch_count": len(mismatches),
        "mismatch_share": len(mismatches) / len(target),
        "total_abs_error": total_abs_error,
        "mean_abs_error": total_abs_error / len(target),
        "first_mismatches": mismatches[:8],
    }


def _best_global_affine_tiled(flat: list[int], target: list[int]) -> tuple[list[int], dict[str, int]]:
    base = (flat * ((len(target) + len(flat) - 1) // len(flat)))[: len(target)]
    best: tuple[int, int, int, int, list[int]] | None = None
    for scale in range(-64, 65):
        for bias in range(-256, 257):
            values = [scale * value + bias for value in base]
            total_abs_error = sum(abs(candidate - target_value) for candidate, target_value in zip(values, target, strict=True))
            mismatches = sum(candidate != target_value for candidate, target_value in zip(values, target, strict=True))
            item = (mismatches, total_abs_error, scale, bias, values)
            if best is None or item[:4] < best[:4]:
                best = item
    if best is None:
        raise AttentionD128ValueAdapterError("failed finding affine adapter candidate")
    mismatches, total_abs_error, scale, bias, values = best
    return values, {"scale": scale, "bias": bias, "mismatches": mismatches, "total_abs_error": total_abs_error}


def _target_pattern(values: list[int]) -> dict[str, Any]:
    generated = [((13 * index + 7) % 193) - 96 for index in range(len(values))]
    matches = generated == values
    return {
        "pattern": "target_q8[i] = ((13 * i + 7) % 193) - 96",
        "matches": matches,
        "modulus": 193,
        "step": 13,
        "offset": 7,
        "center": 96,
        "interpretation": (
            "the current d128 input activation is an independent deterministic fixture pattern, "
            "not a value-derived expansion of the checked d8 attention output"
        ),
    }


def build_adapter_analysis(
    attention: dict[str, Any],
    d128_input: dict[str, Any],
    bridge: dict[str, Any],
) -> dict[str, Any]:
    _validate_expected(attention, EXPECTED_ATTENTION, "attention fixture")
    _validate_expected(d128_input, EXPECTED_D128, "d128 input")
    _validate_expected(bridge, EXPECTED_BRIDGE, "statement bridge")

    bridge_summary = _dict(bridge.get("summary"), "bridge summary")
    if bridge_summary.get("current_commitments_equal") is not False:
        raise AttentionD128ValueAdapterError("statement bridge equality status drift")
    if bridge_summary.get("attention_outputs_commitment") != attention.get("outputs_commitment"):
        raise AttentionD128ValueAdapterError("bridge attention commitment drift")
    if bridge_summary.get("block_input_activation_commitment") != d128_input.get("input_activation_commitment"):
        raise AttentionD128ValueAdapterError("bridge d128 commitment drift")

    attention_outputs = _extract_attention_outputs(attention)
    flat = [cell for row in attention_outputs for cell in row]
    target = _extract_d128_input(d128_input)
    if len(flat) != 64:
        raise AttentionD128ValueAdapterError("attention flattened cell count drift")
    if len(target) != 128:
        raise AttentionD128ValueAdapterError("d128 target width drift")

    affine_values, affine_params = _best_global_affine_tiled(flat, target)
    candidates = [
        _score_candidate(
            "tile_flat_attention_twice",
            "flatten the 8x8 attention outputs and tile once to 128 cells",
            (flat * 2)[:128],
            target,
        ),
        _score_candidate(
            "pad_flat_attention_with_zeroes",
            "flatten the 8x8 attention outputs and pad the remaining 64 cells with zero",
            flat + [0] * 64,
            target,
        ),
        _score_candidate(
            "repeat_each_attention_cell",
            "duplicate each flattened attention output cell once",
            [cell for cell in flat for _ in (0, 1)][:128],
            target,
        ),
        _score_candidate(
            "first_step_repeat_16",
            "repeat the first attention output row sixteen times",
            (attention_outputs[0] * 16)[:128],
            target,
        ),
        _score_candidate(
            "last_step_repeat_16",
            "repeat the last attention output row sixteen times",
            (attention_outputs[-1] * 16)[:128],
            target,
        ),
        _score_candidate(
            "best_global_affine_over_tiled_attention",
            f"best integer y = scale*x + bias over tiled attention in scale/bias search window: {affine_params}",
            affine_values,
            target,
        ),
    ]
    best = min(candidates, key=lambda candidate: (candidate["mismatch_count"], candidate["total_abs_error"]))
    return {
        "analysis_kind": "attention-output-to-d128-input-value-adapter-feasibility",
        "attention": {
            "outputs_commitment": _commitment(attention.get("outputs_commitment"), "attention outputs commitment"),
            "statement_commitment": _commitment(attention.get("statement_commitment"), "attention statement commitment"),
            "shape": [len(attention_outputs), len(attention_outputs[0])],
            "flattened_cells": len(flat),
            "min_q8": min(flat),
            "max_q8": max(flat),
            "sum_q8": sum(flat),
        },
        "d128_input": {
            "input_activation_commitment": _commitment(
                d128_input.get("input_activation_commitment"), "d128 input activation commitment"
            ),
            "statement_commitment": _commitment(d128_input.get("statement_commitment"), "d128 statement commitment"),
            "width": len(target),
            "min_q8": min(target),
            "max_q8": max(target),
            "sum_q8": sum(target),
            "target_pattern": _target_pattern(target),
        },
        "statement_bridge": {
            "bridge_statement_commitment": _commitment(
                bridge.get("bridge_statement_commitment"), "bridge statement commitment"
            ),
            "payload_commitment": _commitment(bridge.get("payload_commitment"), "bridge payload commitment"),
            "current_commitments_equal": _bool(bridge_summary.get("current_commitments_equal"), "bridge current equality"),
            "feed_equality_status": _string(bridge_summary.get("feed_equality_status"), "bridge feed equality status"),
        },
        "candidate_policies": candidates,
        "best_candidate": {
            "id": best["id"],
            "mismatch_count": best["mismatch_count"],
            "mismatch_share": best["mismatch_share"],
            "mean_abs_error": best["mean_abs_error"],
        },
        "go_gate": (
            "GO only after a non-arbitrary checked adapter consumes the exact attention output values and emits the "
            "exact d128 input activation vector with zero mismatches under a model-facing policy"
        ),
        "no_go_gate": "current checked fixtures fail every conservative adapter candidate; value equality remains NO-GO",
    }


def summary_from_analysis(analysis: dict[str, Any], analysis_commitment: str) -> dict[str, Any]:
    attention = _dict(analysis.get("attention"), "analysis attention")
    d128_input = _dict(analysis.get("d128_input"), "analysis d128 input")
    best = _dict(analysis.get("best_candidate"), "analysis best candidate")
    target_pattern = _dict(d128_input.get("target_pattern"), "analysis target pattern")
    best_mismatches = _int(best.get("mismatch_count"), "best mismatch count")
    return {
        "go_result": "NO-GO for current value adapter; statement binding exists but values are not connected",
        "attention_outputs_commitment": _commitment(
            attention.get("outputs_commitment"), "summary attention outputs commitment"
        ),
        "d128_input_activation_commitment": _commitment(
            d128_input.get("input_activation_commitment"), "summary d128 input activation commitment"
        ),
        "attention_cells": _int(attention.get("flattened_cells"), "summary attention cells"),
        "target_width": _int(d128_input.get("width"), "summary target width"),
        "best_candidate_id": _string(best.get("id"), "summary best candidate id"),
        "best_candidate_mismatches": best_mismatches,
        "best_candidate_mean_abs_error": _number(best.get("mean_abs_error"), "summary best mean abs error"),
        "target_matches_synthetic_pattern": _bool(target_pattern.get("matches"), "summary target pattern match"),
        "adapter_analysis_commitment": _commitment(analysis_commitment, "summary adapter analysis commitment"),
    }


def build_core_payload() -> dict[str, Any]:
    attention, d128_input, bridge, source_artifacts = _load_sources()
    analysis = build_adapter_analysis(attention, d128_input, bridge)
    analysis_commitment = blake2b_commitment(analysis, PAYLOAD_DOMAIN)
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "adapter_analysis": analysis,
        "adapter_analysis_commitment": analysis_commitment,
        "source_artifacts": source_artifacts,
        "summary": summary_from_analysis(analysis, analysis_commitment),
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
        raise AttentionD128ValueAdapterError(f"unexpected payload keys: {sorted(key_set ^ FINAL_KEYS)}")
    if data.get("schema") != SCHEMA:
        raise AttentionD128ValueAdapterError("schema drift")
    if data.get("decision") != DECISION:
        raise AttentionD128ValueAdapterError("decision drift")
    if data.get("result") != RESULT:
        raise AttentionD128ValueAdapterError("result drift")
    if data.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionD128ValueAdapterError("claim boundary drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise AttentionD128ValueAdapterError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionD128ValueAdapterError("validation command drift")
    attention, d128_input_source, bridge, expected_source_artifacts = _load_sources()
    _validate_source_artifacts(data.get("source_artifacts"), expected_artifacts=expected_source_artifacts)

    analysis = _dict(data.get("adapter_analysis"), "adapter analysis")
    expected_analysis = build_adapter_analysis(attention, d128_input_source, bridge)
    if canonical_json_bytes(analysis) != canonical_json_bytes(expected_analysis):
        raise AttentionD128ValueAdapterError("adapter analysis content drift")
    expected_analysis_commitment = blake2b_commitment(expected_analysis, PAYLOAD_DOMAIN)
    if data.get("adapter_analysis_commitment") != expected_analysis_commitment:
        raise AttentionD128ValueAdapterError("adapter analysis commitment drift")
    if _dict(data.get("summary"), "summary") != summary_from_analysis(expected_analysis, expected_analysis_commitment):
        raise AttentionD128ValueAdapterError("summary drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise AttentionD128ValueAdapterError("payload commitment drift")

    candidates = _list(analysis.get("candidate_policies"), "candidate policies")
    if len(candidates) != 6:
        raise AttentionD128ValueAdapterError("candidate policy count drift")
    for candidate_value in candidates:
        candidate = _dict(candidate_value, "candidate")
        _string(candidate.get("id"), "candidate id")
        _string(candidate.get("description"), "candidate description")
        if _int(candidate.get("output_width"), f"{candidate.get('id')} output_width") != 128:
            raise AttentionD128ValueAdapterError("candidate output width drift")
        if _bool(candidate.get("exact_match"), f"{candidate.get('id')} exact_match") is True:
            raise AttentionD128ValueAdapterError("adapter equality overclaim")
        if _int(candidate.get("mismatch_count"), f"{candidate.get('id')} mismatch_count") <= 0:
            raise AttentionD128ValueAdapterError("adapter mismatch floor drift")
        _number(candidate.get("mismatch_share"), f"{candidate.get('id')} mismatch_share")
        if _int(candidate.get("total_abs_error"), f"{candidate.get('id')} total_abs_error") <= 0:
            raise AttentionD128ValueAdapterError("candidate total abs error drift")
        _number(candidate.get("mean_abs_error"), f"{candidate.get('id')} mean_abs_error")
        _list(candidate.get("first_mismatches"), f"{candidate.get('id')} first_mismatches")
    best = _dict(analysis.get("best_candidate"), "best candidate")
    if _int(best.get("mismatch_count"), "best mismatch count") <= 0:
        raise AttentionD128ValueAdapterError("best candidate overclaim")
    _number(best.get("mismatch_share"), "best mismatch share")
    _number(best.get("mean_abs_error"), "best mean abs error")
    d128_input = _dict(analysis.get("d128_input"), "analysis d128 input")
    target_pattern = _dict(d128_input.get("target_pattern"), "analysis target pattern")
    if _bool(target_pattern.get("matches"), "target pattern match") is not True:
        raise AttentionD128ValueAdapterError("target pattern evidence drift")
    if expected is not None and _comparable(data) != _comparable(expected):
        raise AttentionD128ValueAdapterError("payload content drift")

    if key_set == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionD128ValueAdapterError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionD128ValueAdapterError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionD128ValueAdapterError("not all mutations rejected")
        if [case.get("name") for case in cases] != list(EXPECTED_MUTATIONS):
            raise AttentionD128ValueAdapterError("mutation case order drift")
        for case in cases:
            if case.get("rejected") is not True or case.get("accepted") is not False:
                raise AttentionD128ValueAdapterError(f"mutation was not rejected: {case.get('name')}")


def _set_payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


def _forge_best_candidate_positive(payload: dict[str, Any]) -> None:
    payload["adapter_analysis"]["best_candidate"]["mismatch_count"] = 1
    payload["adapter_analysis"]["best_candidate"]["mismatch_share"] = 1 / 128
    payload["adapter_analysis_commitment"] = blake2b_commitment(payload["adapter_analysis"], PAYLOAD_DOMAIN)
    payload["summary"] = summary_from_analysis(payload["adapter_analysis"], payload["adapter_analysis_commitment"])
    refresh_payload_commitment(payload)


MutationFn = Callable[[dict[str, Any]], None]


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_promoted", lambda p: p.__setitem__("decision", "GO_VALUE_ADAPTER"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "MODEL_FAITHFUL_VALUE_ADAPTER"), True),
    (
        "attention_commitment_drift",
        lambda p: p["adapter_analysis"]["attention"].__setitem__("outputs_commitment", "blake2b-256:" + "22" * 32),
        True,
    ),
    (
        "d128_input_commitment_drift",
        lambda p: p["adapter_analysis"]["d128_input"].__setitem__(
            "input_activation_commitment", "blake2b-256:" + "33" * 32
        ),
        True,
    ),
    (
        "candidate_exact_match_overclaim",
        lambda p: p["adapter_analysis"]["candidate_policies"][0].__setitem__("exact_match", True),
        True,
    ),
    (
        "candidate_mismatch_zeroed",
        lambda p: p["adapter_analysis"]["candidate_policies"][0].__setitem__("mismatch_count", 0),
        True,
    ),
    (
        "best_candidate_zeroed",
        lambda p: p["adapter_analysis"]["best_candidate"].__setitem__("mismatch_count", 0),
        True,
    ),
    ("self_consistent_forged_best_candidate_positive", _forge_best_candidate_positive, False),
    (
        "target_pattern_relabelled",
        lambda p: p["adapter_analysis"]["d128_input"]["target_pattern"].__setitem__(
            "interpretation", "target is attention-derived"
        ),
        True,
    ),
    ("source_artifact_sha_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "44" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
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
        except AttentionD128ValueAdapterError as err:
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
    data = _dict(payload, "payload")
    validate_payload(data)
    analysis = _dict(data.get("adapter_analysis"), "adapter analysis")
    analysis_commitment = blake2b_commitment(analysis, PAYLOAD_DOMAIN)
    summary = summary_from_analysis(analysis, analysis_commitment)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": _string(data.get("decision"), "decision"),
            "result": _string(data.get("result"), "result"),
            "attention_outputs_commitment": summary["attention_outputs_commitment"],
            "d128_input_activation_commitment": summary["d128_input_activation_commitment"],
            "attention_cells": summary["attention_cells"],
            "target_width": summary["target_width"],
            "best_candidate_id": summary["best_candidate_id"],
            "best_candidate_mismatches": summary["best_candidate_mismatches"],
            "best_candidate_mean_abs_error": summary["best_candidate_mean_abs_error"],
            "target_matches_synthetic_pattern": str(summary["target_matches_synthetic_pattern"]).lower(),
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    candidate = pathlib.Path(os.path.abspath(path if path.is_absolute() else ROOT / path))
    evidence_root = EVIDENCE_DIR.resolve(strict=True)
    try:
        candidate.relative_to(EVIDENCE_DIR)
    except ValueError as err:
        raise AttentionD128ValueAdapterError(f"output path must stay in docs/engineering/evidence: {path}") from err
    try:
        parent_real = candidate.parent.resolve(strict=True)
        parent_real.relative_to(evidence_root)
    except (FileNotFoundError, ValueError) as err:
        raise AttentionD128ValueAdapterError(
            f"output parent must stay in real docs/engineering/evidence tree: {path}"
        ) from err
    if candidate.suffix != suffix:
        raise AttentionD128ValueAdapterError(f"output path must end with {suffix}: {path}")
    if candidate.exists() and candidate.is_symlink():
        raise AttentionD128ValueAdapterError(f"output path must not be symlink: {path}")
    return candidate


def write_text_no_follow(path: pathlib.Path, contents: str, label: str) -> None:
    data = contents.encode("utf-8")
    parent_fd: int | None = None
    file_fd: int | None = None
    temp_name: str | None = None
    try:
        parent = path.parent.resolve(strict=True)
        parent.relative_to(EVIDENCE_DIR.resolve(strict=True))
        parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        parent_fd = os.open(parent, parent_flags)
        parent_stat = os.fstat(parent_fd)
        if not stat_module.S_ISDIR(parent_stat.st_mode):
            raise AttentionD128ValueAdapterError(f"{label} parent must be a real directory")
        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        for _ in range(100):
            candidate = f".{path.name}.{secrets.token_hex(8)}.tmp"
            try:
                file_fd = os.open(candidate, create_flags, 0o600, dir_fd=parent_fd)
                temp_name = candidate
                break
            except FileExistsError:
                continue
        if file_fd is None or temp_name is None:
            raise AttentionD128ValueAdapterError(f"failed creating temporary {label}")
        with os.fdopen(file_fd, "wb") as handle:
            file_fd = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise AttentionD128ValueAdapterError(f"{label} path must not become a symlink")
        os.replace(temp_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temp_name = None
        os.fsync(parent_fd)
    except OSError as err:
        raise AttentionD128ValueAdapterError(f"failed writing {label}: {err}") from err
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if parent_fd is not None:
            try:
                if temp_name is not None:
                    try:
                        os.unlink(temp_name, dir_fd=parent_fd)
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass
            finally:
                os.close(parent_fd)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    json_target = require_output_path(json_path, ".json")
    tsv_target = require_output_path(tsv_path, ".tsv")
    if json_target is not None:
        write_text_no_follow(json_target, pretty_json(payload) + "\n", "json output")
    if tsv_target is not None:
        write_text_no_follow(tsv_target, to_tsv(payload), "tsv output")


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
    except AttentionD128ValueAdapterError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
