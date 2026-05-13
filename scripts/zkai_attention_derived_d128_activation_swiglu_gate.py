#!/usr/bin/env python3
"""Build the attention-derived d128 activation/SwiGLU boundary gate."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import stat as stat_module
import tempfile
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_PROJECTION_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-projection-boundary-2026-05.json"
CURRENT_ACTIVATION_JSON = EVIDENCE_DIR / "zkai-d128-activation-swiglu-proof-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-activation-swiglu-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-activation-swiglu-2026-05.tsv"

PROJECTION_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_projection_boundary_gate.py"
ACTIVATION_GATE_PATH = ROOT / "scripts" / "zkai_d128_activation_swiglu_proof_input.py"
THIS_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_activation_swiglu_gate.py"

SCHEMA = "zkai-attention-derived-d128-activation-swiglu-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_ACTIVATION_SWIGLU_INPUT"
RESULT = "GO_VALUE_CONNECTED_ACTIVATION_SWIGLU_INPUT_NO_GO_FULL_BLOCK"
CLAIM_BOUNDARY = (
    "CHECKED_ATTENTION_DERIVED_D128_GATE_VALUE_OUTPUT_FEEDS_ACTIVATION_SWIGLU_"
    "NOT_EXISTING_BLOCK_RECEIPT_NOT_FULL_LAYER_PROOF"
)
ACTIVATION_INPUT_SCHEMA = "zkai-attention-derived-d128-activation-swiglu-input-v1"
SOURCE_PROJECTION_BOUNDARY_VERSION = "zkai-attention-derived-d128-projection-boundary-gate-v1"
SOURCE_GATE_VALUE_PROOF_VERSION = "zkai-attention-derived-d128-gate-value-projection-input-v1"
VERIFIER_DOMAIN = "ptvm:zkai:attention-derived-d128-activation-swiglu:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:attention-derived-d128-activation-swiglu-public-instance:v1"
MAX_SOURCE_JSON_BYTES = 8 * 1024 * 1024
MAX_SOURCE_ARTIFACT_BYTES = 8 * 1024 * 1024

NON_CLAIMS = [
    "not full d128 block proof",
    "not down projection proof",
    "not residual proof",
    "not recursive composition",
    "not binding the full d128 output_activation_commitment",
    "not learned/model projection weights",
    "not matched to the existing canonical d128 activation/SwiGLU fixture",
    "not proof-size or timing evidence",
    "activation lookup and SwiGLU rows are verifier-recomputed from checked public rows",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_activation_swiglu_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-activation-swiglu-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-activation-swiglu-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_activation_swiglu_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_activation_swiglu_gate.py scripts/tests/test_zkai_attention_derived_d128_activation_swiglu_gate.py",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "decision",
    "result",
    "source_projection_boundary_payload_commitment",
    "source_gate_value_projection_output_commitment",
    "derived_activation_output_commitment",
    "derived_hidden_activation_commitment",
    "activation_lookup_rows",
    "swiglu_mix_rows",
    "activation_output_mismatch_count",
    "hidden_activation_mismatch_count",
    "mutations_rejected",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "source_summary",
    "activation_swiglu_payload",
    "comparison_summary",
    "summary",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS


class AttentionDerivedD128ActivationSwiGluError(ValueError):
    pass


def _load_module(path: pathlib.Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AttentionDerivedD128ActivationSwiGluError(f"failed to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROJECTION = _load_module(PROJECTION_GATE_PATH, "zkai_attention_derived_d128_projection_boundary_gate")
ACTIVATION = _load_module(ACTIVATION_GATE_PATH, "zkai_d128_activation_swiglu_proof_input")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    return ACTIVATION.blake2b_commitment(value, domain)


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + sha256_hex(material)


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    try:
        return PROJECTION._commitment(value, label)
    except Exception as err:
        raise AttentionDerivedD128ActivationSwiGluError(str(err)) from err


def read_source_bytes(path: pathlib.Path, *, max_bytes: int, label: str) -> bytes:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionDerivedD128ActivationSwiGluError(f"{label} is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionDerivedD128ActivationSwiGluError(f"{label} is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise AttentionDerivedD128ActivationSwiGluError(f"{label} changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(max_bytes + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise AttentionDerivedD128ActivationSwiGluError(f"failed to read {label}: {path}: {err}") from err
    if len(raw) > max_bytes:
        raise AttentionDerivedD128ActivationSwiGluError(
            f"{label} exceeds max size: got at least {len(raw)} bytes, limit {max_bytes} bytes"
        )
    return raw


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = read_source_bytes(path, max_bytes=MAX_SOURCE_JSON_BYTES, label="JSON source")
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionDerivedD128ActivationSwiGluError(f"failed to load JSON: {path}: {err}") from err
    return _dict(payload, f"JSON payload {path}"), raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: Any | None = None) -> dict[str, Any]:
    try:
        raw = read_source_bytes(path, max_bytes=MAX_SOURCE_ARTIFACT_BYTES, label="source artifact")
    except AttentionDerivedD128ActivationSwiGluError as err:
        raise AttentionDerivedD128ActivationSwiGluError(f"failed to read source artifact: {path}: {err}") from err
    artifact = {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if payload is not None:
        artifact["payload_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return artifact


def sequence_mismatch_count(left: list[int], right: list[int], label: str) -> int:
    if len(left) != len(right):
        raise AttentionDerivedD128ActivationSwiGluError(f"{label} length mismatch")
    return sum(1 for left_value, right_value in zip(left, right, strict=True) if left_value != right_value)


def validate_source_projection(payload: Any, *, full: bool = False) -> None:
    data = _dict(payload, "source projection boundary payload")
    constants = {
        "schema": SOURCE_PROJECTION_BOUNDARY_VERSION,
        "decision": PROJECTION.DECISION,
        "result": PROJECTION.RESULT,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ActivationSwiGluError(f"source projection boundary field mismatch: {field}")
    if data.get("payload_commitment") != PROJECTION.payload_commitment(data):
        raise AttentionDerivedD128ActivationSwiGluError("source projection boundary payload commitment drift")
    if full:
        try:
            PROJECTION.validate_payload(data)
        except Exception as err:
            raise AttentionDerivedD128ActivationSwiGluError(f"source projection boundary invalid: {err}") from err


def validate_source_gate_value(source: Any, *, projection_payload: dict[str, Any] | None = None) -> None:
    data = _dict(source, "source derived gate/value payload")
    constants = {
        "schema": SOURCE_GATE_VALUE_PROOF_VERSION,
        "decision": "GO_ATTENTION_DERIVED_D128_GATE_VALUE_PROJECTION_INPUT",
        "operation": "gate_value_projection",
        "target_id": ACTIVATION.TARGET_ID,
        "required_backend_version": ACTIVATION.REQUIRED_BACKEND_VERSION,
        "verifier_domain": ACTIVATION.VERIFIER_DOMAIN,
        "width": ACTIVATION.WIDTH,
        "ff_dim": ACTIVATION.FF_DIM,
        "row_count": 2 * ACTIVATION.FF_DIM * ACTIVATION.WIDTH,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ActivationSwiGluError(f"source gate/value field mismatch: {field}")
    if projection_payload is not None:
        validate_source_projection(projection_payload)
        bridge_payload = _dict(projection_payload.get("bridge_payload"), "source bridge payload")
        try:
            PROJECTION.validate_gate_value_projection_payload(data, bridge_payload=bridge_payload)
        except Exception as err:
            raise AttentionDerivedD128ActivationSwiGluError(f"source gate/value invalid: {err}") from err
        if projection_payload["summary"]["derived_gate_value_projection_output_commitment"] != data["gate_value_projection_output_commitment"]:
            raise AttentionDerivedD128ActivationSwiGluError("source gate/value does not match projection boundary summary")
    gate = [_int(value, f"source gate projection {index}") for index, value in enumerate(_list(data.get("gate_projection_q8"), "source gate projection"))]
    value = [_int(item, f"source value projection {index}") for index, item in enumerate(_list(data.get("value_projection_q8"), "source value projection"))]
    if len(gate) != ACTIVATION.FF_DIM or len(value) != ACTIVATION.FF_DIM:
        raise AttentionDerivedD128ActivationSwiGluError("source projection vector width mismatch")
    if ACTIVATION.sequence_commitment(gate, ACTIVATION.GATE_VALUE.GATE_PROJECTION_OUTPUT_DOMAIN, [ACTIVATION.FF_DIM]) != data["gate_projection_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("source gate projection commitment drift")
    if ACTIVATION.sequence_commitment(value, ACTIVATION.GATE_VALUE.VALUE_PROJECTION_OUTPUT_DOMAIN, [ACTIVATION.FF_DIM]) != data["value_projection_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("source value projection commitment drift")
    if ACTIVATION.GATE_VALUE.output_commitment(gate, value) != data["gate_value_projection_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("source gate/value output commitment drift")


def source_gate_value_vectors(source: dict[str, Any]) -> tuple[list[int], list[int]]:
    validate_source_gate_value(source)
    return list(source["gate_projection_q8"]), list(source["value_projection_q8"])


def statement_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "activation_lookup_commitment": payload["activation_lookup_commitment"],
            "activation_output_commitment": payload["activation_output_commitment"],
            "activation_swiglu_row_commitment": payload["activation_swiglu_row_commitment"],
            "ff_dim": payload["ff_dim"],
            "hidden_activation_commitment": payload["hidden_activation_commitment"],
            "operation": "attention_derived_activation_swiglu",
            "proof_native_parameter_commitment": payload["proof_native_parameter_commitment"],
            "required_backend_version": payload["required_backend_version"],
            "row_count": payload["row_count"],
            "scale_q8": payload["scale_q8"],
            "source_gate_projection_output_commitment": payload["source_gate_projection_output_commitment"],
            "source_gate_value_projection_output_commitment": payload["source_gate_value_projection_output_commitment"],
            "source_gate_value_projection_proof_version": payload["source_gate_value_projection_proof_version"],
            "source_gate_value_projection_public_instance_commitment": payload["source_gate_value_projection_public_instance_commitment"],
            "source_gate_value_projection_statement_commitment": payload["source_gate_value_projection_statement_commitment"],
            "source_projection_boundary_payload_commitment": payload["source_projection_boundary_payload_commitment"],
            "source_projection_boundary_proof_version": payload["source_projection_boundary_proof_version"],
            "source_value_projection_output_commitment": payload["source_value_projection_output_commitment"],
            "target_id": payload["target_id"],
            "verifier_domain": payload["verifier_domain"],
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return blake2b_commitment(
        {
            "ff_dim": ACTIVATION.FF_DIM,
            "operation": "attention_derived_activation_swiglu",
            "target_commitment": statement,
            "width": ACTIVATION.WIDTH,
        },
        PUBLIC_INSTANCE_DOMAIN,
    )


def build_activation_payload(source_gate_value: dict[str, Any], source_projection: dict[str, Any]) -> dict[str, Any]:
    validate_source_gate_value(source_gate_value, projection_payload=source_projection)
    gate, value = source_gate_value_vectors(source_gate_value)
    rows, activated, hidden = ACTIVATION.build_rows(gate, value)
    lookup_commitment = ACTIVATION.activation_lookup_commitment()
    native_parameter = ACTIVATION.proof_native_parameter_commitment(lookup_commitment)
    payload = {
        "schema": ACTIVATION_INPUT_SCHEMA,
        "decision": DECISION,
        "operation": "activation_swiglu",
        "target_id": ACTIVATION.TARGET_ID,
        "required_backend_version": ACTIVATION.REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": ACTIVATION.WIDTH,
        "ff_dim": ACTIVATION.FF_DIM,
        "row_count": len(rows),
        "activation_lookup_rows": ACTIVATION.ACTIVATION_TABLE_ROWS,
        "swiglu_mix_rows": ACTIVATION.FF_DIM,
        "scale_q8": ACTIVATION.SCALE_Q8,
        "activation_clamp_q8": ACTIVATION.ACTIVATION_CLAMP_Q8,
        "source_projection_boundary_proof_version": SOURCE_PROJECTION_BOUNDARY_VERSION,
        "source_projection_boundary_payload_commitment": source_projection["payload_commitment"],
        "source_gate_value_projection_proof_version": SOURCE_GATE_VALUE_PROOF_VERSION,
        "source_gate_value_projection_statement_commitment": source_gate_value["statement_commitment"],
        "source_gate_value_projection_public_instance_commitment": source_gate_value["public_instance_commitment"],
        "source_gate_projection_output_commitment": source_gate_value["gate_projection_output_commitment"],
        "source_value_projection_output_commitment": source_gate_value["value_projection_output_commitment"],
        "source_gate_value_projection_output_commitment": source_gate_value["gate_value_projection_output_commitment"],
        "activation_lookup_commitment": lookup_commitment,
        "proof_native_parameter_commitment": native_parameter,
        "activation_output_commitment": ACTIVATION.sequence_commitment(activated, ACTIVATION.ACTIVATION_OUTPUT_DOMAIN, [ACTIVATION.FF_DIM]),
        "hidden_activation_commitment": ACTIVATION.sequence_commitment(hidden, ACTIVATION.HIDDEN_ACTIVATION_DOMAIN, [ACTIVATION.FF_DIM]),
        "activation_swiglu_row_commitment": ACTIVATION.rows_commitment(rows),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "gate_projection_q8": gate,
        "value_projection_q8": value,
        "activated_gate_q8": activated,
        "hidden_q8": hidden,
        "non_claims": list(NON_CLAIMS),
        "next_backend_step": "connect derived hidden activation to down-projection boundary input",
    }
    statement = statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    validate_activation_payload(payload, source_gate_value=source_gate_value, source_projection=source_projection)
    return payload


def validate_activation_payload(
    payload: Any,
    *,
    source_gate_value: dict[str, Any] | None = None,
    source_projection: dict[str, Any] | None = None,
) -> None:
    data = _dict(payload, "activation/SwiGLU payload")
    expected_fields = {
        "schema",
        "decision",
        "operation",
        "target_id",
        "required_backend_version",
        "verifier_domain",
        "width",
        "ff_dim",
        "row_count",
        "activation_lookup_rows",
        "swiglu_mix_rows",
        "scale_q8",
        "activation_clamp_q8",
        "source_projection_boundary_proof_version",
        "source_projection_boundary_payload_commitment",
        "source_gate_value_projection_proof_version",
        "source_gate_value_projection_statement_commitment",
        "source_gate_value_projection_public_instance_commitment",
        "source_gate_projection_output_commitment",
        "source_value_projection_output_commitment",
        "source_gate_value_projection_output_commitment",
        "activation_lookup_commitment",
        "proof_native_parameter_commitment",
        "activation_output_commitment",
        "hidden_activation_commitment",
        "activation_swiglu_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "gate_projection_q8",
        "value_projection_q8",
        "activated_gate_q8",
        "hidden_q8",
        "non_claims",
        "next_backend_step",
    }
    if set(data) != expected_fields:
        raise AttentionDerivedD128ActivationSwiGluError("activation/SwiGLU field set drift")
    constants = {
        "schema": ACTIVATION_INPUT_SCHEMA,
        "decision": DECISION,
        "operation": "activation_swiglu",
        "target_id": ACTIVATION.TARGET_ID,
        "required_backend_version": ACTIVATION.REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": ACTIVATION.WIDTH,
        "ff_dim": ACTIVATION.FF_DIM,
        "row_count": ACTIVATION.FF_DIM,
        "activation_lookup_rows": ACTIVATION.ACTIVATION_TABLE_ROWS,
        "swiglu_mix_rows": ACTIVATION.FF_DIM,
        "scale_q8": ACTIVATION.SCALE_Q8,
        "activation_clamp_q8": ACTIVATION.ACTIVATION_CLAMP_Q8,
        "source_projection_boundary_proof_version": SOURCE_PROJECTION_BOUNDARY_VERSION,
        "source_gate_value_projection_proof_version": SOURCE_GATE_VALUE_PROOF_VERSION,
        "activation_lookup_commitment": ACTIVATION.ACTIVATION_LOOKUP_COMMITMENT,
        "proof_native_parameter_commitment": ACTIVATION.PROOF_NATIVE_PARAMETER_COMMITMENT,
        "non_claims": NON_CLAIMS,
        "next_backend_step": "connect derived hidden activation to down-projection boundary input",
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ActivationSwiGluError(f"activation/SwiGLU field mismatch: {field}")
    for field in (
        "source_projection_boundary_payload_commitment",
        "source_gate_value_projection_statement_commitment",
        "source_gate_value_projection_public_instance_commitment",
        "source_gate_projection_output_commitment",
        "source_value_projection_output_commitment",
        "source_gate_value_projection_output_commitment",
        "activation_lookup_commitment",
        "proof_native_parameter_commitment",
        "activation_output_commitment",
        "hidden_activation_commitment",
        "activation_swiglu_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
    ):
        _commitment(data[field], f"activation/SwiGLU {field}")
    if data["hidden_activation_commitment"] == ACTIVATION.OUTPUT_ACTIVATION_COMMITMENT:
        raise AttentionDerivedD128ActivationSwiGluError("hidden activation relabeled as full output")
    gate = [_int(value, f"gate projection {index}") for index, value in enumerate(_list(data.get("gate_projection_q8"), "gate projection"))]
    value = [_int(item, f"value projection {index}") for index, item in enumerate(_list(data.get("value_projection_q8"), "value projection"))]
    activated = [_int(item, f"activation output {index}") for index, item in enumerate(_list(data.get("activated_gate_q8"), "activation output"))]
    hidden = [_int(item, f"hidden activation {index}") for index, item in enumerate(_list(data.get("hidden_q8"), "hidden activation"))]
    if len(gate) != ACTIVATION.FF_DIM or len(value) != ACTIVATION.FF_DIM:
        raise AttentionDerivedD128ActivationSwiGluError("source projection vector width mismatch")
    if len(activated) != ACTIVATION.FF_DIM or len(hidden) != ACTIVATION.FF_DIM:
        raise AttentionDerivedD128ActivationSwiGluError("activation output vector width mismatch")
    for label, values in (
        ("gate projection", gate),
        ("value projection", value),
        ("activation output", activated),
        ("hidden activation", hidden),
    ):
        for index, item in enumerate(values):
            ACTIVATION.require_signed_m31(item, f"{label} {index}")
    if ACTIVATION.sequence_commitment(gate, ACTIVATION.GATE_VALUE.GATE_PROJECTION_OUTPUT_DOMAIN, [ACTIVATION.FF_DIM]) != data["source_gate_projection_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("source gate projection commitment drift")
    if ACTIVATION.sequence_commitment(value, ACTIVATION.GATE_VALUE.VALUE_PROJECTION_OUTPUT_DOMAIN, [ACTIVATION.FF_DIM]) != data["source_value_projection_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("source value projection commitment drift")
    if ACTIVATION.GATE_VALUE.output_commitment(gate, value) != data["source_gate_value_projection_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("source gate/value output commitment drift")
    rows, recomputed_activated, recomputed_hidden = ACTIVATION.build_rows(gate, value)
    if recomputed_activated != activated:
        raise AttentionDerivedD128ActivationSwiGluError("activation output drift")
    if recomputed_hidden != hidden:
        raise AttentionDerivedD128ActivationSwiGluError("hidden activation output drift")
    if ACTIVATION.activation_lookup_commitment() != data["activation_lookup_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("activation lookup commitment drift")
    if ACTIVATION.proof_native_parameter_commitment(data["activation_lookup_commitment"]) != data["proof_native_parameter_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("proof-native parameter commitment drift")
    if ACTIVATION.sequence_commitment(activated, ACTIVATION.ACTIVATION_OUTPUT_DOMAIN, [ACTIVATION.FF_DIM]) != data["activation_output_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("activation output commitment drift")
    if ACTIVATION.sequence_commitment(hidden, ACTIVATION.HIDDEN_ACTIVATION_DOMAIN, [ACTIVATION.FF_DIM]) != data["hidden_activation_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("hidden activation commitment drift")
    if ACTIVATION.rows_commitment(rows) != data["activation_swiglu_row_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("activation/SwiGLU row commitment drift")
    if source_projection is not None:
        validate_source_projection(source_projection)
        if data["source_projection_boundary_payload_commitment"] != source_projection["payload_commitment"]:
            raise AttentionDerivedD128ActivationSwiGluError("source projection boundary payload commitment drift")
    if source_gate_value is not None:
        validate_source_gate_value(source_gate_value, projection_payload=source_projection)
        if data["source_gate_value_projection_statement_commitment"] != source_gate_value["statement_commitment"]:
            raise AttentionDerivedD128ActivationSwiGluError("source gate/value statement drift")
        if data["source_gate_value_projection_public_instance_commitment"] != source_gate_value["public_instance_commitment"]:
            raise AttentionDerivedD128ActivationSwiGluError("source gate/value public instance drift")
        if data["source_gate_value_projection_output_commitment"] != source_gate_value["gate_value_projection_output_commitment"]:
            raise AttentionDerivedD128ActivationSwiGluError("source gate/value output drift")
    if statement_commitment(data) != data["statement_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("statement commitment drift")
    if public_instance_commitment(data["statement_commitment"]) != data["public_instance_commitment"]:
        raise AttentionDerivedD128ActivationSwiGluError("public instance commitment drift")


def build_context() -> dict[str, Any]:
    source_projection, source_projection_raw = load_json(SOURCE_PROJECTION_JSON)
    current_activation, current_activation_raw = load_json(CURRENT_ACTIVATION_JSON)
    validate_source_projection(source_projection, full=True)
    try:
        ACTIVATION.validate_payload(current_activation)
    except Exception as err:
        raise AttentionDerivedD128ActivationSwiGluError(f"current activation fixture invalid: {err}") from err
    source_gate_value = _dict(source_projection.get("gate_value_projection_payload"), "source gate/value payload")
    activation_payload = build_activation_payload(source_gate_value, source_projection)
    current_activated = [
        _int(item, f"current activation output {index}")
        for index, item in enumerate(_list(current_activation.get("activated_gate_q8"), "current activation output"))
    ]
    current_hidden = [
        _int(item, f"current hidden activation {index}")
        for index, item in enumerate(_list(current_activation.get("hidden_q8"), "current hidden activation"))
    ]
    comparison = {
        "current_activation_statement_commitment": current_activation["statement_commitment"],
        "current_activation_output_commitment": current_activation["activation_output_commitment"],
        "current_hidden_activation_commitment": current_activation["hidden_activation_commitment"],
        "current_activation_swiglu_row_commitment": current_activation["activation_swiglu_row_commitment"],
        "activation_output_mismatch_count": sequence_mismatch_count(
            activation_payload["activated_gate_q8"], current_activated, "activation output"
        ),
        "hidden_activation_mismatch_count": sequence_mismatch_count(
            activation_payload["hidden_q8"], current_hidden, "hidden activation"
        ),
        "matches_existing_d128_activation_swiglu": False,
    }
    return {
        "source_artifacts": [
            source_artifact("attention_derived_projection_boundary", SOURCE_PROJECTION_JSON, source_projection),
            {
                "id": "current_d128_activation_swiglu_input",
                "path": CURRENT_ACTIVATION_JSON.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(current_activation_raw).hexdigest(),
                "payload_sha256": hashlib.sha256(canonical_json_bytes(current_activation)).hexdigest(),
            },
            source_artifact("attention_derived_projection_boundary_generator", PROJECTION_GATE_PATH),
            source_artifact("d128_activation_swiglu_generator", ACTIVATION_GATE_PATH),
            source_artifact("attention_derived_activation_swiglu_gate", THIS_GATE_PATH),
        ],
        "source_summary": {
            "source_attention_outputs_commitment": source_projection["summary"]["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": source_projection["summary"]["derived_input_activation_commitment"],
            "derived_rmsnorm_output_row_commitment": source_projection["summary"]["derived_rmsnorm_output_row_commitment"],
            "derived_gate_value_statement_commitment": source_gate_value["statement_commitment"],
            "derived_gate_value_projection_output_commitment": source_gate_value["gate_value_projection_output_commitment"],
            "source_projection_boundary_payload_sha256": hashlib.sha256(source_projection_raw).hexdigest(),
            "source_projection_boundary_payload_commitment": source_projection["payload_commitment"],
        },
        "source_projection": source_projection,
        "source_gate_value": source_gate_value,
        "activation_swiglu_payload": activation_payload,
        "comparison_summary": comparison,
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    activation_payload = context["activation_swiglu_payload"]
    comparison = context["comparison_summary"]
    source_summary = context["source_summary"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "source_summary": copy.deepcopy(source_summary),
        "activation_swiglu_payload": copy.deepcopy(activation_payload),
        "comparison_summary": copy.deepcopy(comparison),
        "summary": {
            "go_result": (
                "GO for attention-derived d128 gate/value output feeding activation/SwiGLU "
                "and producing a derived hidden activation"
            ),
            "no_go_result": (
                "NO-GO for claiming the existing d128 block receipt consumed this path or for claiming a full layer proof"
            ),
            "source_attention_outputs_commitment": source_summary["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": source_summary["derived_input_activation_commitment"],
            "derived_rmsnorm_output_row_commitment": source_summary["derived_rmsnorm_output_row_commitment"],
            "source_projection_boundary_payload_commitment": source_summary["source_projection_boundary_payload_commitment"],
            "derived_gate_value_statement_commitment": source_summary["derived_gate_value_statement_commitment"],
            "derived_gate_value_projection_output_commitment": source_summary["derived_gate_value_projection_output_commitment"],
            "derived_activation_statement_commitment": activation_payload["statement_commitment"],
            "derived_activation_output_commitment": activation_payload["activation_output_commitment"],
            "derived_hidden_activation_commitment": activation_payload["hidden_activation_commitment"],
            "derived_activation_swiglu_row_commitment": activation_payload["activation_swiglu_row_commitment"],
            "activation_lookup_rows": activation_payload["activation_lookup_rows"],
            "swiglu_mix_rows": activation_payload["swiglu_mix_rows"],
            "matches_existing_d128_activation_swiglu": False,
            "activation_output_mismatch_count": comparison["activation_output_mismatch_count"],
            "hidden_activation_mismatch_count": comparison["hidden_activation_mismatch_count"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_core_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    if set(payload) not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128ActivationSwiGluError("payload key set drift")
    if payload.get("schema") != SCHEMA:
        raise AttentionDerivedD128ActivationSwiGluError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionDerivedD128ActivationSwiGluError("decision drift")
    if payload.get("result") != RESULT:
        raise AttentionDerivedD128ActivationSwiGluError("result drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128ActivationSwiGluError("claim boundary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128ActivationSwiGluError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128ActivationSwiGluError("validation commands drift")
    context = build_context() if context is None else context
    expected_core = build_core_payload(context)
    comparable = {key: value for key, value in payload.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected = {key: value for key, value in expected_core.items() if key != "payload_commitment"}
    if comparable != expected:
        raise AttentionDerivedD128ActivationSwiGluError("derived activation payload drift")
    activation_payload = _dict(payload.get("activation_swiglu_payload"), "activation/SwiGLU payload")
    validate_activation_payload(
        activation_payload,
        source_gate_value=_dict(context.get("source_gate_value"), "context source gate/value"),
        source_projection=_dict(context.get("source_projection"), "context source projection"),
    )
    comparison = _dict(payload.get("comparison_summary"), "comparison summary")
    summary = _dict(payload.get("summary"), "summary")
    if summary.get("matches_existing_d128_activation_swiglu") is not False:
        raise AttentionDerivedD128ActivationSwiGluError("existing activation consumption overclaim")
    if comparison.get("matches_existing_d128_activation_swiglu") is not False:
        raise AttentionDerivedD128ActivationSwiGluError("comparison overclaim")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128ActivationSwiGluError("payload commitment drift")


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    context = build_context() if context is None else context
    validate_core_payload(data, context=context)
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ActivationSwiGluError("mutation case count drift")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ActivationSwiGluError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ActivationSwiGluError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionDerivedD128ActivationSwiGluError("not all mutations rejected")
        expected_cases = run_mutation_cases(build_core_payload(context), context)
        for index, (expected_name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionDerivedD128ActivationSwiGluError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AttentionDerivedD128ActivationSwiGluError("mutation case order drift")
            if _bool(case.get("accepted"), "mutation accepted") is not False:
                raise AttentionDerivedD128ActivationSwiGluError("mutation accepted")
            if _bool(case.get("rejected"), "mutation rejected") is not True:
                raise AttentionDerivedD128ActivationSwiGluError("mutation not rejected")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise AttentionDerivedD128ActivationSwiGluError("mutation error field drift")
            if case != expected_cases[index]:
                raise AttentionDerivedD128ActivationSwiGluError("mutation case drift")


MutationFn = Callable[[dict[str, Any]], None]


def _set_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_TRANSFORMER_BLOCK"), True),
    ("result_overclaim", lambda p: p.__setitem__("result", "GO_FULL_LAYER_PROOF"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_RECURSIVE_LAYER_PROOF"), True),
    (
        "source_projection_boundary_commitment_drift",
        lambda p: p["activation_swiglu_payload"].__setitem__("source_projection_boundary_payload_commitment", "blake2b-256:" + "22" * 32),
        True,
    ),
    (
        "source_gate_value_output_commitment_drift",
        lambda p: p["activation_swiglu_payload"].__setitem__("source_gate_value_projection_output_commitment", "blake2b-256:" + "33" * 32),
        True,
    ),
    (
        "gate_projection_output_drift",
        lambda p: p["activation_swiglu_payload"]["gate_projection_q8"].__setitem__(0, 12345),
        True,
    ),
    (
        "value_projection_output_drift",
        lambda p: p["activation_swiglu_payload"]["value_projection_q8"].__setitem__(0, -12345),
        True,
    ),
    (
        "activation_output_drift",
        lambda p: p["activation_swiglu_payload"]["activated_gate_q8"].__setitem__(0, 99),
        True,
    ),
    (
        "hidden_activation_output_drift",
        lambda p: p["activation_swiglu_payload"]["hidden_q8"].__setitem__(0, 99),
        True,
    ),
    (
        "activation_lookup_commitment_drift",
        lambda p: p["activation_swiglu_payload"].__setitem__("activation_lookup_commitment", "blake2b-256:" + "44" * 32),
        True,
    ),
    (
        "hidden_relabels_full_output",
        lambda p: p["activation_swiglu_payload"].__setitem__("hidden_activation_commitment", ACTIVATION.OUTPUT_ACTIVATION_COMMITMENT),
        True,
    ),
    (
        "current_activation_consumption_overclaim",
        lambda p: p["summary"].__setitem__("matches_existing_d128_activation_swiglu", True),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "55" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", _set_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)
EXPECTED_MUTATION_ERRORS = {
    "decision_overclaim": "decision drift",
    "result_overclaim": "result drift",
    "claim_boundary_overclaim": "claim boundary drift",
    "source_projection_boundary_commitment_drift": "derived activation payload drift",
    "source_gate_value_output_commitment_drift": "derived activation payload drift",
    "gate_projection_output_drift": "derived activation payload drift",
    "value_projection_output_drift": "derived activation payload drift",
    "activation_output_drift": "derived activation payload drift",
    "hidden_activation_output_drift": "derived activation payload drift",
    "activation_lookup_commitment_drift": "derived activation payload drift",
    "hidden_relabels_full_output": "derived activation payload drift",
    "current_activation_consumption_overclaim": "derived activation payload drift",
    "source_artifact_hash_drift": "derived activation payload drift",
    "non_claim_removed": "non-claims drift",
    "payload_commitment_drift": "payload commitment drift",
}


def run_mutation_cases(core_payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core_payload)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, context=context)
        except AttentionDerivedD128ActivationSwiGluError as err:
            expected_error = EXPECTED_MUTATION_ERRORS.get(name)
            if expected_error is None:
                raise AttentionDerivedD128ActivationSwiGluError(f"mutation error marker missing: {name}") from err
            actual_error = str(err)
            error = expected_error if expected_error in actual_error else actual_error
            cases.append({"name": name, "accepted": False, "rejected": True, "error": error})
        else:
            cases.append({"name": name, "accepted": True, "rejected": False, "error": ""})
    return cases


def build_gate_result(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    core = build_core_payload(context)
    cases = run_mutation_cases(core, context)
    final = copy.deepcopy(core)
    final["mutation_inventory"] = list(EXPECTED_MUTATIONS)
    final["cases"] = cases
    final["case_count"] = len(cases)
    final["all_mutations_rejected"] = all(case["rejected"] and not case["accepted"] for case in cases)
    refresh_payload_commitment(final)
    validate_payload(final, context=context)
    return final


def to_tsv(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> str:
    validate_payload(payload, context=context)
    if set(payload) != FINAL_KEYS:
        raise AttentionDerivedD128ActivationSwiGluError("TSV requires finalized payload")
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        "source_projection_boundary_payload_commitment": payload["summary"]["source_projection_boundary_payload_commitment"],
        "source_gate_value_projection_output_commitment": payload["summary"]["derived_gate_value_projection_output_commitment"],
        "derived_activation_output_commitment": payload["summary"]["derived_activation_output_commitment"],
        "derived_hidden_activation_commitment": payload["summary"]["derived_hidden_activation_commitment"],
        "activation_lookup_rows": payload["summary"]["activation_lookup_rows"],
        "swiglu_mix_rows": payload["summary"]["swiglu_mix_rows"],
        "activation_output_mismatch_count": payload["summary"]["activation_output_mismatch_count"],
        "hidden_activation_mismatch_count": payload["summary"]["hidden_activation_mismatch_count"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return handle.getvalue()


def require_output_path(path: pathlib.Path, *, suffix: str | None = None) -> pathlib.Path:
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve(strict=False)
    evidence_root = EVIDENCE_DIR.resolve()
    try:
        resolved.relative_to(evidence_root)
    except ValueError as err:
        raise AttentionDerivedD128ActivationSwiGluError(f"output path must stay under docs/engineering/evidence: {path}") from err
    if suffix is not None and resolved.suffix != suffix:
        raise AttentionDerivedD128ActivationSwiGluError(f"output path must end with {suffix}: {path}")
    if candidate.is_symlink() or resolved.is_symlink():
        raise AttentionDerivedD128ActivationSwiGluError(f"output path must not be a symlink: {path}")
    if resolved.exists() and resolved.is_dir():
        raise AttentionDerivedD128ActivationSwiGluError(f"output path must not be a directory: {path}")
    return resolved


def atomic_write_text(path: pathlib.Path, text: str, *, suffix: str | None = None) -> None:
    resolved = require_output_path(path, suffix=suffix)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent)
    tmp_path = pathlib.Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, resolved)
        dir_fd = os.open(resolved.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise


def write_outputs(
    payload: dict[str, Any],
    json_path: pathlib.Path | None,
    tsv_path: pathlib.Path | None,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    context = build_context() if context is None else context
    validate_payload(payload, context=context)
    if json_path is not None:
        atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n", suffix=".json")
    if tsv_path is not None:
        atomic_write_text(tsv_path, to_tsv(payload, context=context), suffix=".tsv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = build_context()
    payload = build_gate_result(context)
    if args.write_json is not None or args.write_tsv is not None:
        write_outputs(payload, args.write_json, args.write_tsv, context=context)
    summary = {
        "decision": payload["decision"],
        "result": payload["result"],
        "source_gate_value_projection_output_commitment": payload["summary"]["derived_gate_value_projection_output_commitment"],
        "derived_activation_output_commitment": payload["summary"]["derived_activation_output_commitment"],
        "derived_hidden_activation_commitment": payload["summary"]["derived_hidden_activation_commitment"],
        "swiglu_mix_rows": payload["summary"]["swiglu_mix_rows"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
