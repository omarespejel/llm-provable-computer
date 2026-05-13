#!/usr/bin/env python3
"""Build the attention-derived d128 down-projection boundary gate."""

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
import secrets
import stat as stat_module
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_ACTIVATION_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-activation-swiglu-2026-05.json"
CURRENT_DOWN_JSON = EVIDENCE_DIR / "zkai-d128-down-projection-proof-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-down-projection-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-down-projection-2026-05.tsv"

DERIVED_ACTIVATION_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_activation_swiglu_gate.py"
DOWN_PROJECTION_PATH = ROOT / "scripts" / "zkai_d128_down_projection_proof_input.py"
THIS_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_down_projection_gate.py"

SCHEMA = "zkai-attention-derived-d128-down-projection-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_DOWN_PROJECTION_INPUT"
RESULT = "GO_VALUE_CONNECTED_DOWN_PROJECTION_INPUT_NO_GO_FULL_BLOCK"
CLAIM_BOUNDARY = (
    "CHECKED_ATTENTION_DERIVED_D128_HIDDEN_ACTIVATION_FEEDS_D128_DOWN_PROJECTION_"
    "AND_EMITS_DERIVED_RESIDUAL_DELTA_NOT_EXISTING_BLOCK_RECEIPT_NOT_FULL_LAYER_PROOF"
)
DOWN_PROJECTION_INPUT_SCHEMA = "zkai-attention-derived-d128-down-projection-input-v1"
SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION = "zkai-attention-derived-d128-activation-swiglu-gate-v1"
VERIFIER_DOMAIN = "ptvm:zkai:attention-derived-d128-down-projection:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:attention-derived-d128-down-projection-public-instance:v1"
MAX_SOURCE_JSON_BYTES = 8 * 1024 * 1024
MAX_SOURCE_ARTIFACT_BYTES = 8 * 1024 * 1024

NON_CLAIMS = [
    "not full d128 block proof",
    "not residual proof",
    "not recursive composition",
    "not binding the full d128 output_activation_commitment",
    "not matched to the existing canonical d128 down-projection fixture",
    "not proof-size or timing evidence",
    "down projection rows are verifier-recomputed from checked public hidden activation rows",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_down_projection_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-down-projection-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-down-projection-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_down_projection_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_down_projection_gate.py scripts/tests/test_zkai_attention_derived_d128_down_projection_gate.py",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "decision",
    "result",
    "source_activation_swiglu_payload_commitment",
    "source_hidden_activation_commitment",
    "derived_residual_delta_commitment",
    "derived_down_projection_statement_commitment",
    "down_projection_mul_rows",
    "residual_delta_rows",
    "hidden_mismatch_count",
    "residual_delta_mismatch_count",
    "residual_remainder_mismatch_count",
    "mutations_rejected",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "source_summary",
    "down_projection_payload",
    "comparison_summary",
    "summary",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS


class AttentionDerivedD128DownProjectionError(ValueError):
    pass


def _read_repo_regular_file_bytes(path: pathlib.Path, *, label: str) -> tuple[bytes, pathlib.Path]:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise AttentionDerivedD128DownProjectionError(f"{label} must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise AttentionDerivedD128DownProjectionError(f"{label} escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionDerivedD128DownProjectionError(f"{label} is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionDerivedD128DownProjectionError(f"{label} is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise AttentionDerivedD128DownProjectionError(f"{label} changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(MAX_SOURCE_ARTIFACT_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise AttentionDerivedD128DownProjectionError(f"failed to read {label}: {path}: {err}") from err
    if len(raw) > MAX_SOURCE_ARTIFACT_BYTES:
        raise AttentionDerivedD128DownProjectionError(
            f"{label} exceeds max size: got at least {len(raw)} bytes, limit {MAX_SOURCE_ARTIFACT_BYTES} bytes"
        )
    return raw, resolved


def _load_module(path: pathlib.Path, name: str) -> Any:
    source, resolved = _read_repo_regular_file_bytes(path, label="module source")
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(resolved))
    if spec is None:
        raise AttentionDerivedD128DownProjectionError(f"failed to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(resolved)
    exec(compile(source, str(resolved), "exec"), module.__dict__)
    return module


DERIVED_ACTIVATION = _load_module(DERIVED_ACTIVATION_GATE_PATH, "zkai_attention_derived_d128_activation_swiglu_gate")
DOWN = _load_module(DOWN_PROJECTION_PATH, "zkai_d128_down_projection_proof_input")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    return DOWN.blake2b_commitment(value, domain)


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + sha256_hex(material)


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128DownProjectionError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128DownProjectionError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128DownProjectionError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128DownProjectionError(f"{label} must be boolean")
    return value


def _digest(value: Any, label: str, *, prefix: str = "blake2b-256") -> str:
    if not isinstance(value, str) or not value.startswith(f"{prefix}:"):
        raise AttentionDerivedD128DownProjectionError(f"{label} must be a {prefix} commitment")
    digest = value.removeprefix(f"{prefix}:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise AttentionDerivedD128DownProjectionError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def read_source_bytes(path: pathlib.Path, *, max_bytes: int, label: str) -> bytes:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise AttentionDerivedD128DownProjectionError(f"{label} must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise AttentionDerivedD128DownProjectionError(f"{label} escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionDerivedD128DownProjectionError(f"{label} is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionDerivedD128DownProjectionError(f"{label} is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise AttentionDerivedD128DownProjectionError(f"{label} changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(max_bytes + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise AttentionDerivedD128DownProjectionError(f"failed to read {label}: {path}: {err}") from err
    if len(raw) > max_bytes:
        raise AttentionDerivedD128DownProjectionError(
            f"{label} exceeds max size: got at least {len(raw)} bytes, limit {max_bytes} bytes"
        )
    return raw


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = read_source_bytes(path, max_bytes=MAX_SOURCE_JSON_BYTES, label="JSON source")
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise AttentionDerivedD128DownProjectionError(f"failed to load JSON: {path}: {err}") from err
    return _dict(payload, f"JSON payload {path}"), raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: Any | None = None) -> dict[str, Any]:
    try:
        raw = read_source_bytes(path, max_bytes=MAX_SOURCE_ARTIFACT_BYTES, label="source artifact")
    except AttentionDerivedD128DownProjectionError as err:
        raise AttentionDerivedD128DownProjectionError(f"failed to read source artifact: {path}: {err}") from err
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
        raise AttentionDerivedD128DownProjectionError(f"{label} length mismatch")
    return sum(1 for left_value, right_value in zip(left, right, strict=True) if left_value != right_value)


def validate_source_activation(payload: Any, *, full: bool = False) -> None:
    data = _dict(payload, "source derived activation/SwiGLU payload")
    constants = {
        "schema": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "decision": DERIVED_ACTIVATION.DECISION,
        "result": DERIVED_ACTIVATION.RESULT,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128DownProjectionError(f"source activation/SwiGLU field mismatch: {field}")
    if data.get("payload_commitment") != DERIVED_ACTIVATION.payload_commitment(data):
        raise AttentionDerivedD128DownProjectionError("source activation/SwiGLU payload commitment drift")
    activation = _dict(data.get("activation_swiglu_payload"), "source activation/SwiGLU nested payload")
    summary = _dict(data.get("summary"), "source activation/SwiGLU summary")
    if activation.get("hidden_activation_commitment") != summary.get("derived_hidden_activation_commitment"):
        raise AttentionDerivedD128DownProjectionError("source hidden activation summary drift")
    if activation.get("statement_commitment") != summary.get("derived_activation_statement_commitment"):
        raise AttentionDerivedD128DownProjectionError("source activation statement summary drift")
    if full:
        try:
            DERIVED_ACTIVATION.validate_payload(data)
        except Exception as err:
            raise AttentionDerivedD128DownProjectionError(f"source activation/SwiGLU invalid: {err}") from err


def source_hidden_vector(source: dict[str, Any]) -> list[int]:
    validate_source_activation(source)
    activation = _dict(source.get("activation_swiglu_payload"), "source activation/SwiGLU nested payload")
    hidden = [_int(item, f"source hidden activation {index}") for index, item in enumerate(_list(activation.get("hidden_q8"), "source hidden activation"))]
    if len(hidden) != DOWN.FF_DIM:
        raise AttentionDerivedD128DownProjectionError("source hidden activation vector mismatch")
    for index, item in enumerate(hidden):
        DOWN.require_signed_m31(item, f"source hidden activation {index}")
    if DOWN.sequence_commitment(hidden, DOWN.HIDDEN_ACTIVATION_DOMAIN, [DOWN.FF_DIM]) != activation["hidden_activation_commitment"]:
        raise AttentionDerivedD128DownProjectionError("source hidden activation commitment drift")
    return hidden


def statement_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "down_matrix_root": payload["down_matrix_root"],
            "down_projection_mul_row_commitment": payload["down_projection_mul_row_commitment"],
            "ff_dim": payload["ff_dim"],
            "operation": "attention_derived_down_projection",
            "proof_native_parameter_commitment": payload["proof_native_parameter_commitment"],
            "required_backend_version": payload["required_backend_version"],
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "residual_delta_scale_divisor": payload["residual_delta_scale_divisor"],
            "row_count": payload["row_count"],
            "source_activation_swiglu_payload_commitment": payload["source_activation_swiglu_payload_commitment"],
            "source_activation_swiglu_proof_version": payload["source_activation_swiglu_proof_version"],
            "source_activation_swiglu_public_instance_commitment": payload["source_activation_swiglu_public_instance_commitment"],
            "source_activation_swiglu_statement_commitment": payload["source_activation_swiglu_statement_commitment"],
            "source_hidden_activation_commitment": payload["source_hidden_activation_commitment"],
            "target_id": payload["target_id"],
            "verifier_domain": payload["verifier_domain"],
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return blake2b_commitment(
        {
            "ff_dim": DOWN.FF_DIM,
            "operation": "attention_derived_down_projection",
            "target_commitment": statement,
            "width": DOWN.WIDTH,
        },
        PUBLIC_INSTANCE_DOMAIN,
    )


def build_down_projection_payload(source_activation: dict[str, Any]) -> dict[str, Any]:
    validate_source_activation(source_activation)
    activation = _dict(source_activation.get("activation_swiglu_payload"), "source activation/SwiGLU nested payload")
    hidden = source_hidden_vector(source_activation)
    rows, residual_delta, residual_remainder = DOWN.build_rows(hidden)
    down_root = DOWN.matrix_root(rows)
    native_parameter = DOWN.proof_native_parameter_commitment(down_root)
    payload = {
        "schema": DOWN_PROJECTION_INPUT_SCHEMA,
        "decision": DECISION,
        "operation": "down_projection",
        "target_id": DOWN.TARGET_ID,
        "required_backend_version": DOWN.REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": DOWN.WIDTH,
        "ff_dim": DOWN.FF_DIM,
        "row_count": len(rows),
        "down_projection_mul_rows": DOWN.WIDTH * DOWN.FF_DIM,
        "residual_delta_rows": DOWN.WIDTH,
        "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source_activation_swiglu_payload_commitment": source_activation["payload_commitment"],
        "source_activation_swiglu_statement_commitment": activation["statement_commitment"],
        "source_activation_swiglu_public_instance_commitment": activation["public_instance_commitment"],
        "source_hidden_activation_commitment": activation["hidden_activation_commitment"],
        "down_matrix_root": down_root,
        "proof_native_parameter_commitment": native_parameter,
        "residual_delta_scale_divisor": DOWN.FF_DIM,
        "residual_delta_commitment": DOWN.residual_delta_commitment(residual_delta, residual_remainder, DOWN.FF_DIM),
        "down_projection_mul_row_commitment": DOWN.rows_commitment(rows),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "hidden_q8": hidden,
        "residual_delta_q8": residual_delta,
        "residual_delta_remainder_q8": residual_remainder,
        "non_claims": list(NON_CLAIMS),
        "next_backend_step": "connect derived residual delta to source-bound residual-add boundary",
    }
    statement = statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    validate_down_projection_payload(payload, source_activation=source_activation)
    return payload


def validate_down_projection_payload(payload: Any, *, source_activation: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "down-projection payload")
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
        "down_projection_mul_rows",
        "residual_delta_rows",
        "source_activation_swiglu_proof_version",
        "source_activation_swiglu_payload_commitment",
        "source_activation_swiglu_statement_commitment",
        "source_activation_swiglu_public_instance_commitment",
        "source_hidden_activation_commitment",
        "down_matrix_root",
        "proof_native_parameter_commitment",
        "residual_delta_scale_divisor",
        "residual_delta_commitment",
        "down_projection_mul_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "hidden_q8",
        "residual_delta_q8",
        "residual_delta_remainder_q8",
        "non_claims",
        "next_backend_step",
    }
    if set(data) != expected_fields:
        raise AttentionDerivedD128DownProjectionError("down-projection field set drift")
    constants = {
        "schema": DOWN_PROJECTION_INPUT_SCHEMA,
        "decision": DECISION,
        "operation": "down_projection",
        "target_id": DOWN.TARGET_ID,
        "required_backend_version": DOWN.REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": DOWN.WIDTH,
        "ff_dim": DOWN.FF_DIM,
        "row_count": DOWN.WIDTH * DOWN.FF_DIM,
        "down_projection_mul_rows": DOWN.WIDTH * DOWN.FF_DIM,
        "residual_delta_rows": DOWN.WIDTH,
        "source_activation_swiglu_proof_version": SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "down_matrix_root": DOWN.DOWN_MATRIX_ROOT,
        "proof_native_parameter_commitment": DOWN.PROOF_NATIVE_PARAMETER_COMMITMENT,
        "residual_delta_scale_divisor": DOWN.FF_DIM,
        "non_claims": NON_CLAIMS,
        "next_backend_step": "connect derived residual delta to source-bound residual-add boundary",
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128DownProjectionError(f"down-projection field mismatch: {field}")
    if data["residual_delta_commitment"] == DOWN.OUTPUT_ACTIVATION_COMMITMENT:
        raise AttentionDerivedD128DownProjectionError("residual delta commitment relabeled as full output commitment")
    _digest(data["source_activation_swiglu_payload_commitment"], "source activation/SwiGLU payload commitment", prefix="sha256")
    for field in (
        "source_activation_swiglu_statement_commitment",
        "source_activation_swiglu_public_instance_commitment",
        "source_hidden_activation_commitment",
        "down_matrix_root",
        "proof_native_parameter_commitment",
        "residual_delta_commitment",
        "down_projection_mul_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
    ):
        _digest(data[field], f"down-projection {field}")
    hidden = [_int(item, f"hidden activation {index}") for index, item in enumerate(_list(data.get("hidden_q8"), "hidden activation"))]
    residual_delta = [_int(item, f"residual delta {index}") for index, item in enumerate(_list(data.get("residual_delta_q8"), "residual delta"))]
    residual_remainder = [
        _int(item, f"residual delta remainder {index}")
        for index, item in enumerate(_list(data.get("residual_delta_remainder_q8"), "residual delta remainder"))
    ]
    if len(hidden) != DOWN.FF_DIM:
        raise AttentionDerivedD128DownProjectionError("hidden activation vector mismatch")
    if len(residual_delta) != DOWN.WIDTH:
        raise AttentionDerivedD128DownProjectionError("residual delta vector mismatch")
    if len(residual_remainder) != DOWN.WIDTH:
        raise AttentionDerivedD128DownProjectionError("residual delta remainder vector mismatch")
    for index, item in enumerate(hidden):
        DOWN.require_signed_m31(item, f"hidden activation {index}")
    for index, item in enumerate(residual_delta):
        DOWN.require_signed_m31(item, f"residual delta {index}")
    for index, item in enumerate(residual_remainder):
        if item < 0 or item >= DOWN.FF_DIM:
            raise AttentionDerivedD128DownProjectionError(f"residual delta remainder {index} outside divisor range")
    if DOWN.sequence_commitment(hidden, DOWN.HIDDEN_ACTIVATION_DOMAIN, [DOWN.FF_DIM]) != data["source_hidden_activation_commitment"]:
        raise AttentionDerivedD128DownProjectionError("source hidden activation commitment drift")
    rows, recomputed_delta, recomputed_remainder = DOWN.build_rows(hidden)
    if recomputed_delta != residual_delta:
        raise AttentionDerivedD128DownProjectionError("residual delta output drift")
    if recomputed_remainder != residual_remainder:
        raise AttentionDerivedD128DownProjectionError("residual delta remainder drift")
    if DOWN.matrix_root(rows) != data["down_matrix_root"]:
        raise AttentionDerivedD128DownProjectionError("down matrix root drift")
    if DOWN.proof_native_parameter_commitment(data["down_matrix_root"]) != data["proof_native_parameter_commitment"]:
        raise AttentionDerivedD128DownProjectionError("proof-native parameter commitment drift")
    if DOWN.residual_delta_commitment(residual_delta, residual_remainder, data["residual_delta_scale_divisor"]) != data["residual_delta_commitment"]:
        raise AttentionDerivedD128DownProjectionError("residual delta commitment drift")
    if DOWN.rows_commitment(rows) != data["down_projection_mul_row_commitment"]:
        raise AttentionDerivedD128DownProjectionError("down-projection row commitment drift")
    if source_activation is not None:
        validate_source_activation(source_activation)
        activation = _dict(source_activation.get("activation_swiglu_payload"), "source activation/SwiGLU nested payload")
        if data["source_activation_swiglu_payload_commitment"] != source_activation["payload_commitment"]:
            raise AttentionDerivedD128DownProjectionError("source activation/SwiGLU payload commitment drift")
        if data["source_activation_swiglu_statement_commitment"] != activation["statement_commitment"]:
            raise AttentionDerivedD128DownProjectionError("source activation/SwiGLU statement drift")
        if data["source_activation_swiglu_public_instance_commitment"] != activation["public_instance_commitment"]:
            raise AttentionDerivedD128DownProjectionError("source activation/SwiGLU public instance drift")
        if data["source_hidden_activation_commitment"] != activation["hidden_activation_commitment"]:
            raise AttentionDerivedD128DownProjectionError("source hidden activation drift")
    if statement_commitment(data) != data["statement_commitment"]:
        raise AttentionDerivedD128DownProjectionError("statement commitment drift")
    if public_instance_commitment(data["statement_commitment"]) != data["public_instance_commitment"]:
        raise AttentionDerivedD128DownProjectionError("public instance commitment drift")


def build_context() -> dict[str, Any]:
    source_activation, source_activation_raw = load_json(SOURCE_ACTIVATION_JSON)
    current_down, current_down_raw = load_json(CURRENT_DOWN_JSON)
    validate_source_activation(source_activation, full=True)
    try:
        DOWN.validate_payload(current_down)
    except Exception as err:
        raise AttentionDerivedD128DownProjectionError(f"current down-projection fixture invalid: {err}") from err
    down_payload = build_down_projection_payload(source_activation)
    current_hidden = [
        _int(item, f"current hidden activation {index}")
        for index, item in enumerate(_list(current_down.get("hidden_q8"), "current hidden activation"))
    ]
    current_residual = [
        _int(item, f"current residual delta {index}")
        for index, item in enumerate(_list(current_down.get("residual_delta_q8"), "current residual delta"))
    ]
    current_remainder = [
        _int(item, f"current residual remainder {index}")
        for index, item in enumerate(_list(current_down.get("residual_delta_remainder_q8"), "current residual remainder"))
    ]
    comparison = {
        "current_down_projection_statement_commitment": current_down["statement_commitment"],
        "current_down_projection_public_instance_commitment": current_down["public_instance_commitment"],
        "current_residual_delta_commitment": current_down["residual_delta_commitment"],
        "current_down_projection_mul_row_commitment": current_down["down_projection_mul_row_commitment"],
        "hidden_mismatch_count": sequence_mismatch_count(down_payload["hidden_q8"], current_hidden, "hidden activation"),
        "residual_delta_mismatch_count": sequence_mismatch_count(
            down_payload["residual_delta_q8"], current_residual, "residual delta"
        ),
        "residual_remainder_mismatch_count": sequence_mismatch_count(
            down_payload["residual_delta_remainder_q8"], current_remainder, "residual remainder"
        ),
        "matches_existing_d128_down_projection": False,
    }
    source_summary = _dict(source_activation.get("summary"), "source activation/SwiGLU summary")
    return {
        "source_artifacts": [
            source_artifact("attention_derived_activation_swiglu", SOURCE_ACTIVATION_JSON, source_activation),
            {
                "id": "current_d128_down_projection_input",
                "path": CURRENT_DOWN_JSON.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(current_down_raw).hexdigest(),
                "payload_sha256": hashlib.sha256(canonical_json_bytes(current_down)).hexdigest(),
            },
            source_artifact("attention_derived_activation_swiglu_generator", DERIVED_ACTIVATION_GATE_PATH),
            source_artifact("d128_down_projection_generator", DOWN_PROJECTION_PATH),
            source_artifact("attention_derived_down_projection_gate", THIS_GATE_PATH),
        ],
        "source_summary": {
            "source_activation_swiglu_payload_sha256": hashlib.sha256(source_activation_raw).hexdigest(),
            "source_activation_swiglu_payload_commitment": source_activation["payload_commitment"],
            "source_gate_value_projection_output_commitment": source_summary["derived_gate_value_projection_output_commitment"],
            "source_activation_statement_commitment": source_summary["derived_activation_statement_commitment"],
            "source_activation_output_commitment": source_summary["derived_activation_output_commitment"],
            "source_hidden_activation_commitment": source_summary["derived_hidden_activation_commitment"],
        },
        "source_activation": source_activation,
        "down_projection_payload": down_payload,
        "comparison_summary": comparison,
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    down_payload = context["down_projection_payload"]
    comparison = context["comparison_summary"]
    source_summary = context["source_summary"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "source_summary": copy.deepcopy(source_summary),
        "down_projection_payload": copy.deepcopy(down_payload),
        "comparison_summary": copy.deepcopy(comparison),
        "summary": {
            "go_result": (
                "GO for attention-derived d128 hidden activation feeding down projection "
                "and producing a derived residual delta"
            ),
            "no_go_result": (
                "NO-GO for claiming the existing d128 block receipt consumed this path or for claiming a full layer proof"
            ),
            "source_activation_swiglu_payload_commitment": source_summary["source_activation_swiglu_payload_commitment"],
            "source_hidden_activation_commitment": source_summary["source_hidden_activation_commitment"],
            "derived_down_projection_statement_commitment": down_payload["statement_commitment"],
            "derived_down_projection_public_instance_commitment": down_payload["public_instance_commitment"],
            "derived_residual_delta_commitment": down_payload["residual_delta_commitment"],
            "derived_down_projection_mul_row_commitment": down_payload["down_projection_mul_row_commitment"],
            "down_projection_mul_rows": down_payload["down_projection_mul_rows"],
            "residual_delta_rows": down_payload["residual_delta_rows"],
            "residual_delta_scale_divisor": down_payload["residual_delta_scale_divisor"],
            "matches_existing_d128_down_projection": False,
            "hidden_mismatch_count": comparison["hidden_mismatch_count"],
            "residual_delta_mismatch_count": comparison["residual_delta_mismatch_count"],
            "residual_remainder_mismatch_count": comparison["residual_remainder_mismatch_count"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_core_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    if set(payload) not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128DownProjectionError("payload key set drift")
    if payload.get("schema") != SCHEMA:
        raise AttentionDerivedD128DownProjectionError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionDerivedD128DownProjectionError("decision drift")
    if payload.get("result") != RESULT:
        raise AttentionDerivedD128DownProjectionError("result drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128DownProjectionError("claim boundary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128DownProjectionError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128DownProjectionError("validation commands drift")
    context = build_context() if context is None else context
    expected_core = build_core_payload(context)
    comparable = {key: value for key, value in payload.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected = {key: value for key, value in expected_core.items() if key != "payload_commitment"}
    if comparable != expected:
        raise AttentionDerivedD128DownProjectionError("derived down-projection payload drift")
    validate_down_projection_payload(
        _dict(payload.get("down_projection_payload"), "down-projection payload"),
        source_activation=_dict(context.get("source_activation"), "context source activation/SwiGLU"),
    )
    comparison = _dict(payload.get("comparison_summary"), "comparison summary")
    summary = _dict(payload.get("summary"), "summary")
    if summary.get("matches_existing_d128_down_projection") is not False:
        raise AttentionDerivedD128DownProjectionError("existing down-projection consumption overclaim")
    if comparison.get("matches_existing_d128_down_projection") is not False:
        raise AttentionDerivedD128DownProjectionError("comparison overclaim")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128DownProjectionError("payload commitment drift")


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    context = build_context() if context is None else context
    validate_core_payload(data, context=context)
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128DownProjectionError("mutation case count drift")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128DownProjectionError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128DownProjectionError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionDerivedD128DownProjectionError("not all mutations rejected")
        expected_cases = run_mutation_cases(build_core_payload(context), context)
        for index, (expected_name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionDerivedD128DownProjectionError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AttentionDerivedD128DownProjectionError("mutation case order drift")
            if _bool(case.get("accepted"), "mutation accepted") is not False:
                raise AttentionDerivedD128DownProjectionError("mutation accepted")
            if _bool(case.get("rejected"), "mutation rejected") is not True:
                raise AttentionDerivedD128DownProjectionError("mutation not rejected")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise AttentionDerivedD128DownProjectionError("mutation error field drift")
            if case != expected_cases[index]:
                raise AttentionDerivedD128DownProjectionError("mutation case drift")


MutationFn = Callable[[dict[str, Any]], None]


def _set_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_TRANSFORMER_BLOCK"), True),
    ("result_overclaim", lambda p: p.__setitem__("result", "GO_FULL_LAYER_PROOF"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_RECURSIVE_LAYER_PROOF"), True),
    (
        "source_activation_payload_commitment_drift",
        lambda p: p["down_projection_payload"].__setitem__("source_activation_swiglu_payload_commitment", "sha256:" + "22" * 32),
        True,
    ),
    (
        "source_hidden_activation_commitment_drift",
        lambda p: p["down_projection_payload"].__setitem__("source_hidden_activation_commitment", "blake2b-256:" + "33" * 32),
        True,
    ),
    (
        "hidden_vector_drift",
        lambda p: p["down_projection_payload"]["hidden_q8"].__setitem__(0, p["down_projection_payload"]["hidden_q8"][0] + 1),
        True,
    ),
    (
        "residual_delta_output_drift",
        lambda p: p["down_projection_payload"]["residual_delta_q8"].__setitem__(0, p["down_projection_payload"]["residual_delta_q8"][0] + 1),
        True,
    ),
    (
        "residual_delta_remainder_drift",
        lambda p: p["down_projection_payload"]["residual_delta_remainder_q8"].__setitem__(
            0, (p["down_projection_payload"]["residual_delta_remainder_q8"][0] + 1) % DOWN.FF_DIM
        ),
        True,
    ),
    (
        "down_matrix_root_drift",
        lambda p: p["down_projection_payload"].__setitem__("down_matrix_root", "blake2b-256:" + "44" * 32),
        True,
    ),
    (
        "residual_delta_commitment_drift",
        lambda p: p["down_projection_payload"].__setitem__("residual_delta_commitment", "blake2b-256:" + "55" * 32),
        True,
    ),
    (
        "row_commitment_drift",
        lambda p: p["down_projection_payload"].__setitem__("down_projection_mul_row_commitment", "blake2b-256:" + "66" * 32),
        True,
    ),
    (
        "residual_delta_relabels_full_output",
        lambda p: p["down_projection_payload"].__setitem__("residual_delta_commitment", DOWN.OUTPUT_ACTIVATION_COMMITMENT),
        True,
    ),
    (
        "current_down_projection_consumption_overclaim",
        lambda p: p["summary"].__setitem__("matches_existing_d128_down_projection", True),
        True,
    ),
    ("source_artifact_hash_drift", lambda p: p["source_artifacts"][0].__setitem__("sha256", "77" * 32), True),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("payload_commitment_drift", _set_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)
EXPECTED_MUTATION_ERRORS = {
    "decision_overclaim": "decision drift",
    "result_overclaim": "result drift",
    "claim_boundary_overclaim": "claim boundary drift",
    "source_activation_payload_commitment_drift": "derived down-projection payload drift",
    "source_hidden_activation_commitment_drift": "derived down-projection payload drift",
    "hidden_vector_drift": "derived down-projection payload drift",
    "residual_delta_output_drift": "derived down-projection payload drift",
    "residual_delta_remainder_drift": "derived down-projection payload drift",
    "down_matrix_root_drift": "derived down-projection payload drift",
    "residual_delta_commitment_drift": "derived down-projection payload drift",
    "row_commitment_drift": "derived down-projection payload drift",
    "residual_delta_relabels_full_output": "derived down-projection payload drift",
    "current_down_projection_consumption_overclaim": "derived down-projection payload drift",
    "source_artifact_hash_drift": "derived down-projection payload drift",
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
        except AttentionDerivedD128DownProjectionError as err:
            expected_error = EXPECTED_MUTATION_ERRORS.get(name)
            if expected_error is None:
                raise AttentionDerivedD128DownProjectionError(f"mutation error marker missing: {name}") from err
            actual_error = str(err)
            if expected_error not in actual_error:
                raise AttentionDerivedD128DownProjectionError(
                    f"mutation produced unexpected error: {name}: {actual_error}"
                ) from err
            cases.append({"name": name, "accepted": False, "rejected": True, "error": expected_error})
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
        raise AttentionDerivedD128DownProjectionError("TSV requires finalized payload")
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        "source_activation_swiglu_payload_commitment": payload["summary"]["source_activation_swiglu_payload_commitment"],
        "source_hidden_activation_commitment": payload["summary"]["source_hidden_activation_commitment"],
        "derived_residual_delta_commitment": payload["summary"]["derived_residual_delta_commitment"],
        "derived_down_projection_statement_commitment": payload["summary"]["derived_down_projection_statement_commitment"],
        "down_projection_mul_rows": payload["summary"]["down_projection_mul_rows"],
        "residual_delta_rows": payload["summary"]["residual_delta_rows"],
        "hidden_mismatch_count": payload["summary"]["hidden_mismatch_count"],
        "residual_delta_mismatch_count": payload["summary"]["residual_delta_mismatch_count"],
        "residual_remainder_mismatch_count": payload["summary"]["residual_remainder_mismatch_count"],
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
    try:
        resolved.relative_to(EVIDENCE_DIR.resolve())
    except ValueError as err:
        raise AttentionDerivedD128DownProjectionError(f"output path must stay under docs/engineering/evidence: {path}") from err
    if suffix is not None and resolved.suffix != suffix:
        raise AttentionDerivedD128DownProjectionError(f"output path must end with {suffix}: {path}")
    if candidate.is_symlink() or resolved.is_symlink():
        raise AttentionDerivedD128DownProjectionError(f"output path must not be a symlink: {path}")
    if resolved.exists() and resolved.is_dir():
        raise AttentionDerivedD128DownProjectionError(f"output path must not be a directory: {path}")
    return resolved


def atomic_write_text(path: pathlib.Path, text: str, *, suffix: str | None = None) -> None:
    resolved = require_output_path(path, suffix=suffix)
    if not resolved.parent.exists():
        raise AttentionDerivedD128DownProjectionError(f"output parent must exist: {resolved.parent}")
    parent_stat = resolved.parent.lstat()
    if not stat_module.S_ISDIR(parent_stat.st_mode):
        raise AttentionDerivedD128DownProjectionError(f"output parent must be a directory: {resolved.parent}")
    dir_fd = os.open(resolved.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    tmp_name = f".{resolved.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    tmp_created = False
    try:
        open_parent_stat = os.fstat(dir_fd)
        if (open_parent_stat.st_dev, open_parent_stat.st_ino) != (parent_stat.st_dev, parent_stat.st_ino):
            raise AttentionDerivedD128DownProjectionError(f"output parent changed while opening: {resolved.parent}")
        fd = os.open(tmp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
        tmp_created = True
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(tmp_name, resolved.name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        tmp_created = False
        os.fsync(dir_fd)
    except Exception:
        if tmp_created:
            try:
                os.unlink(tmp_name, dir_fd=dir_fd)
            except FileNotFoundError:
                pass
        raise
    finally:
        os.close(dir_fd)


def write_outputs(
    payload: dict[str, Any],
    json_path: pathlib.Path | None = None,
    tsv_path: pathlib.Path | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> None:
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
    write_outputs(payload, args.write_json, args.write_tsv, context=context)
    summary = {
        "decision": payload["decision"],
        "result": payload["result"],
        "source_hidden_activation_commitment": payload["summary"]["source_hidden_activation_commitment"],
        "derived_residual_delta_commitment": payload["summary"]["derived_residual_delta_commitment"],
        "down_projection_mul_rows": payload["summary"]["down_projection_mul_rows"],
        "residual_delta_rows": payload["summary"]["residual_delta_rows"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
