#!/usr/bin/env python3
"""Build the attention-derived d128 residual-add boundary gate."""

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
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
SOURCE_INPUT_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-input-2026-05.json"
SOURCE_DOWN_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-down-projection-2026-05.json"
CURRENT_RESIDUAL_JSON = EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-residual-add-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-residual-add-2026-05.tsv"

DERIVED_INPUT_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_input_gate.py"
DERIVED_DOWN_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_down_projection_gate.py"
RESIDUAL_ADD_PATH = ROOT / "scripts" / "zkai_d128_residual_add_proof_input.py"
THIS_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_residual_add_gate.py"

SCHEMA = "zkai-attention-derived-d128-residual-add-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_RESIDUAL_ADD_INPUT"
RESULT = "GO_VALUE_CONNECTED_RESIDUAL_ADD_INPUT_NO_GO_SINGLE_BLOCK_PROOF"
CLAIM_BOUNDARY = (
    "CHECKED_ATTENTION_DERIVED_D128_INPUT_PLUS_DERIVED_RESIDUAL_DELTA_EMITS_DERIVED_OUTPUT_"
    "NOT_EXISTING_BLOCK_RECEIPT_NOT_SINGLE_COMPOSED_PROOF_NOT_PROOF_SIZE_EVIDENCE"
)
RESIDUAL_ADD_INPUT_SCHEMA = "zkai-attention-derived-d128-residual-add-input-v1"
SOURCE_INPUT_SCHEMA = "zkai-attention-derived-d128-input-gate-v1"
SOURCE_DOWN_PROJECTION_SCHEMA = "zkai-attention-derived-d128-down-projection-gate-v1"
SOURCE_DOWN_PROJECTION_PROOF_VERSION = "zkai-attention-derived-d128-down-projection-gate-v1"
VERIFIER_DOMAIN = "ptvm:zkai:attention-derived-d128-residual-add:v1"
PUBLIC_INSTANCE_DOMAIN = "ptvm:zkai:attention-derived-d128-residual-add-public-instance:v1"
PROOF_NATIVE_PARAMETER_DOMAIN = "ptvm:zkai:attention-derived-d128-residual-add-parameters:v1"
MAX_SOURCE_MODULE_BYTES = 8 * 1024 * 1024

NON_CLAIMS = [
    "not one composed d128 transformer-block proof",
    "not evidence that the existing d128 residual-add receipt consumed the derived path",
    "not recursive composition",
    "not proof-size or timing evidence",
    "not model-scale transformer inference",
    "not production-ready",
    "residual-add rows are verifier-recomputed from checked public input and residual-delta rows",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_residual_add_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-residual-add-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-residual-add-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_residual_add_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_residual_add_gate.py scripts/tests/test_zkai_attention_derived_d128_residual_add_gate.py",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "decision",
    "result",
    "source_input_activation_commitment",
    "source_residual_delta_commitment",
    "derived_output_activation_commitment",
    "derived_residual_add_statement_commitment",
    "residual_add_rows",
    "input_mismatch_count",
    "residual_delta_mismatch_count",
    "output_mismatch_count",
    "mutations_rejected",
)

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "claim_boundary",
    "source_artifacts",
    "source_summary",
    "residual_add_payload",
    "comparison_summary",
    "summary",
    "non_claims",
    "validation_commands",
    "payload_commitment",
}
MUTATION_KEYS = {"mutation_inventory", "cases", "case_count", "all_mutations_rejected"}
FINAL_KEYS = CORE_KEYS | MUTATION_KEYS


class AttentionDerivedD128ResidualAddError(ValueError):
    pass


def _read_repo_regular_file_bytes(path: pathlib.Path, *, label: str) -> tuple[bytes, pathlib.Path]:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise AttentionDerivedD128ResidualAddError(f"{label} must not be a symlink: {path}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise AttentionDerivedD128ResidualAddError(f"{label} escapes repository: {path}") from err
    try:
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise AttentionDerivedD128ResidualAddError(f"{label} is not a regular file: {path}")
        fd: int | None = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise AttentionDerivedD128ResidualAddError(f"{label} is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise AttentionDerivedD128ResidualAddError(f"{label} changed while reading: {path}")
            with os.fdopen(fd, "rb") as handle:
                fd = None
                raw = handle.read(MAX_SOURCE_MODULE_BYTES + 1)
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise AttentionDerivedD128ResidualAddError(f"failed to read {label}: {path}: {err}") from err
    if len(raw) > MAX_SOURCE_MODULE_BYTES:
        raise AttentionDerivedD128ResidualAddError(
            f"{label} exceeds max size: got at least {len(raw)} bytes, limit {MAX_SOURCE_MODULE_BYTES} bytes"
        )
    return raw, resolved


def _load_module(path: pathlib.Path, name: str) -> Any:
    source, resolved = _read_repo_regular_file_bytes(path, label="module source")
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(resolved))
    if spec is None:
        raise AttentionDerivedD128ResidualAddError(f"failed to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(resolved)
    exec(compile(source, str(resolved), "exec"), module.__dict__)
    return module


DERIVED_INPUT = _load_module(DERIVED_INPUT_GATE_PATH, "zkai_attention_derived_d128_input_gate")
DERIVED_DOWN = _load_module(DERIVED_DOWN_GATE_PATH, "zkai_attention_derived_d128_down_projection_gate")
RESIDUAL = _load_module(RESIDUAL_ADD_PATH, "zkai_d128_residual_add_proof_input")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def blake2b_commitment(value: Any, domain: str) -> str:
    return RESIDUAL.blake2b_commitment(value, domain)


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + sha256_hex(material)


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AttentionDerivedD128ResidualAddError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128ResidualAddError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128ResidualAddError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128ResidualAddError(f"{label} must be boolean")
    return value


def _digest(value: Any, label: str, *, prefix: str = "blake2b-256") -> str:
    if not isinstance(value, str) or not value.startswith(f"{prefix}:"):
        raise AttentionDerivedD128ResidualAddError(f"{label} must be a {prefix} commitment")
    digest = value.removeprefix(f"{prefix}:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise AttentionDerivedD128ResidualAddError(f"{label} must be a 32-byte lowercase hex digest")
    return value


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = DERIVED_DOWN.read_source_bytes(path, max_bytes=DERIVED_DOWN.MAX_SOURCE_JSON_BYTES, label="JSON source")
        payload = json.loads(raw.decode("utf-8"))
    except Exception as err:
        raise AttentionDerivedD128ResidualAddError(f"failed to load JSON: {path}: {err}") from err
    return _dict(payload, f"JSON payload {path}"), raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: Any | None = None) -> dict[str, Any]:
    try:
        raw = DERIVED_DOWN.read_source_bytes(path, max_bytes=DERIVED_DOWN.MAX_SOURCE_ARTIFACT_BYTES, label="source artifact")
    except Exception as err:
        raise AttentionDerivedD128ResidualAddError(f"failed to read source artifact: {path}: {err}") from err
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
        raise AttentionDerivedD128ResidualAddError(f"{label} length mismatch")
    return sum(1 for left_value, right_value in zip(left, right, strict=True) if left_value != right_value)


def validate_source_input(payload: Any, *, full: bool = False) -> None:
    data = _dict(payload, "source derived input payload")
    constants = {
        "schema": SOURCE_INPUT_SCHEMA,
        "decision": DERIVED_INPUT.DECISION,
        "result": DERIVED_INPUT.RESULT,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ResidualAddError(f"source input field mismatch: {field}")
    if data.get("payload_commitment") != DERIVED_INPUT.payload_commitment(data):
        raise AttentionDerivedD128ResidualAddError("source input payload commitment drift")
    derived = _dict(data.get("derived_input"), "source derived input")
    summary = _dict(data.get("summary"), "source input summary")
    if derived.get("input_activation_commitment") != summary.get("derived_input_activation_commitment"):
        raise AttentionDerivedD128ResidualAddError("source input commitment summary drift")
    if full:
        try:
            DERIVED_INPUT.validate_payload(data)
        except Exception as err:
            raise AttentionDerivedD128ResidualAddError(f"source input invalid: {err}") from err


def validate_source_down(payload: Any, *, full: bool = False) -> None:
    data = _dict(payload, "source derived down-projection payload")
    constants = {
        "schema": SOURCE_DOWN_PROJECTION_SCHEMA,
        "decision": DERIVED_DOWN.DECISION,
        "result": DERIVED_DOWN.RESULT,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ResidualAddError(f"source down-projection field mismatch: {field}")
    if data.get("payload_commitment") != DERIVED_DOWN.payload_commitment(data):
        raise AttentionDerivedD128ResidualAddError("source down-projection payload commitment drift")
    down = _dict(data.get("down_projection_payload"), "source down-projection nested payload")
    summary = _dict(data.get("summary"), "source down-projection summary")
    if down.get("residual_delta_commitment") != summary.get("derived_residual_delta_commitment"):
        raise AttentionDerivedD128ResidualAddError("source residual delta summary drift")
    if full:
        try:
            DERIVED_DOWN.validate_payload(data)
        except Exception as err:
            raise AttentionDerivedD128ResidualAddError(f"source down-projection invalid: {err}") from err


def source_input_vector(source: dict[str, Any]) -> list[int]:
    validate_source_input(source)
    derived = _dict(source.get("derived_input"), "source derived input")
    values = [_int(item, f"source input {index}") for index, item in enumerate(_list(derived.get("values_q8"), "source input"))]
    if len(values) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("source input width mismatch")
    for index, value in enumerate(values):
        RESIDUAL.require_signed_q8(value, f"source input {index}")
    if RESIDUAL.sequence_commitment(values, RESIDUAL.INPUT_ACTIVATION_DOMAIN, [RESIDUAL.WIDTH]) != derived["input_activation_commitment"]:
        raise AttentionDerivedD128ResidualAddError("source input activation commitment drift")
    return values


def source_residual_delta(source: dict[str, Any]) -> tuple[list[int], list[int], int]:
    validate_source_down(source)
    down = _dict(source.get("down_projection_payload"), "source down-projection nested payload")
    residual_delta = [
        _int(item, f"source residual delta {index}")
        for index, item in enumerate(_list(down.get("residual_delta_q8"), "source residual delta"))
    ]
    remainders = [
        _int(item, f"source residual delta remainder {index}")
        for index, item in enumerate(_list(down.get("residual_delta_remainder_q8"), "source residual delta remainder"))
    ]
    if len(residual_delta) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("source residual delta width mismatch")
    if len(remainders) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("source residual delta remainder width mismatch")
    divisor = _int(down.get("residual_delta_scale_divisor"), "source residual delta divisor")
    for index, value in enumerate(residual_delta):
        RESIDUAL.require_signed_m31(value, f"source residual delta {index}")
    for index, value in enumerate(remainders):
        if value < 0 or value >= divisor:
            raise AttentionDerivedD128ResidualAddError(f"source residual delta remainder {index} outside divisor range")
    if DERIVED_DOWN.DOWN.residual_delta_commitment(residual_delta, remainders, divisor) != down["residual_delta_commitment"]:
        raise AttentionDerivedD128ResidualAddError("source residual delta commitment drift")
    return residual_delta, remainders, divisor


def statement_commitment(payload: dict[str, Any]) -> str:
    return blake2b_commitment(
        {
            "input_activation_commitment": payload["input_activation_commitment"],
            "operation": "attention_derived_residual_add",
            "output_activation_commitment": payload["output_activation_commitment"],
            "range_policy": payload["range_policy"],
            "residual_add_row_commitment": payload["residual_add_row_commitment"],
            "residual_delta_commitment": payload["residual_delta_commitment"],
            "residual_delta_remainder_sha256": payload["residual_delta_remainder_sha256"],
            "residual_delta_scale_divisor": payload["residual_delta_scale_divisor"],
            "row_count": payload["row_count"],
            "source_down_projection_payload_commitment": payload["source_down_projection_payload_commitment"],
            "source_down_projection_proof_version": payload["source_down_projection_proof_version"],
            "source_down_projection_public_instance_commitment": payload["source_down_projection_public_instance_commitment"],
            "source_down_projection_statement_commitment": payload["source_down_projection_statement_commitment"],
            "source_input_payload_commitment": payload["source_input_payload_commitment"],
            "target_id": payload["target_id"],
            "verifier_domain": payload["verifier_domain"],
            "width": payload["width"],
        },
        VERIFIER_DOMAIN,
    )


def public_instance_commitment(statement: str) -> str:
    return blake2b_commitment(
        {
            "operation": "attention_derived_residual_add",
            "target_commitment": statement,
            "width": RESIDUAL.WIDTH,
        },
        PUBLIC_INSTANCE_DOMAIN,
    )


def proof_native_parameter_commitment(source_down_statement: str) -> str:
    return blake2b_commitment(
        {
            "kind": "attention-derived-d128-residual-add-parameters-v1",
            "source_down_projection_statement_commitment": source_down_statement,
            "width": RESIDUAL.WIDTH,
        },
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )


def build_residual_add_payload(source_input: dict[str, Any], source_down: dict[str, Any]) -> dict[str, Any]:
    validate_source_input(source_input)
    validate_source_down(source_down)
    input_q8 = source_input_vector(source_input)
    residual_delta_q8, residual_delta_remainder_q8, residual_delta_scale_divisor = source_residual_delta(source_down)
    rows = RESIDUAL.build_rows(input_q8, residual_delta_q8)
    output_q8 = [row["output_q8"] for row in rows]
    down = _dict(source_down.get("down_projection_payload"), "source down-projection nested payload")
    source_input_summary = _dict(source_input.get("summary"), "source input summary")
    payload = {
        "schema": RESIDUAL_ADD_INPUT_SCHEMA,
        "decision": DECISION,
        "operation": "attention_derived_residual_add",
        "target_id": RESIDUAL.TARGET_ID,
        "required_backend_version": RESIDUAL.REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": RESIDUAL.WIDTH,
        "row_count": RESIDUAL.WIDTH,
        "source_input_schema": SOURCE_INPUT_SCHEMA,
        "source_input_payload_commitment": source_input["payload_commitment"],
        "source_attention_outputs_commitment": source_input_summary["source_attention_outputs_commitment"],
        "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
        "source_down_projection_payload_commitment": source_down["payload_commitment"],
        "source_down_projection_statement_commitment": down["statement_commitment"],
        "source_down_projection_public_instance_commitment": down["public_instance_commitment"],
        "range_policy": "attention_derived_input_q8_semantic_bound_1024; residual_delta_and_output_signed_m31",
        "input_activation_commitment": source_input_summary["derived_input_activation_commitment"],
        "residual_delta_commitment": down["residual_delta_commitment"],
        "residual_delta_scale_divisor": residual_delta_scale_divisor,
        "residual_delta_remainder_sha256": "sha256:" + sha256_hex(residual_delta_remainder_q8),
        "output_activation_commitment": RESIDUAL.sequence_commitment(
            output_q8, RESIDUAL.OUTPUT_ACTIVATION_DOMAIN, [RESIDUAL.WIDTH]
        ),
        "residual_add_row_commitment": RESIDUAL.rows_commitment(rows),
        "proof_native_parameter_commitment": proof_native_parameter_commitment(down["statement_commitment"]),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "input_q8": input_q8,
        "residual_delta_q8": residual_delta_q8,
        "residual_delta_remainder_q8": residual_delta_remainder_q8,
        "output_q8": output_q8,
        "rows": rows,
        "non_claims": list(NON_CLAIMS),
        "next_backend_step": "compose the derived slice statements into a single checked block statement boundary",
    }
    statement = statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = public_instance_commitment(statement)
    validate_residual_add_payload(payload, source_input=source_input, source_down=source_down)
    return payload


def validate_residual_add_payload(
    payload: Any,
    *,
    source_input: dict[str, Any] | None = None,
    source_down: dict[str, Any] | None = None,
) -> None:
    data = _dict(payload, "residual-add payload")
    expected_fields = {
        "schema",
        "decision",
        "operation",
        "target_id",
        "required_backend_version",
        "verifier_domain",
        "width",
        "row_count",
        "source_input_schema",
        "source_input_payload_commitment",
        "source_attention_outputs_commitment",
        "source_down_projection_proof_version",
        "source_down_projection_payload_commitment",
        "source_down_projection_statement_commitment",
        "source_down_projection_public_instance_commitment",
        "range_policy",
        "input_activation_commitment",
        "residual_delta_commitment",
        "residual_delta_scale_divisor",
        "residual_delta_remainder_sha256",
        "output_activation_commitment",
        "residual_add_row_commitment",
        "proof_native_parameter_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "input_q8",
        "residual_delta_q8",
        "residual_delta_remainder_q8",
        "output_q8",
        "rows",
        "non_claims",
        "next_backend_step",
    }
    if set(data) != expected_fields:
        raise AttentionDerivedD128ResidualAddError("residual-add field set drift")
    constants = {
        "schema": RESIDUAL_ADD_INPUT_SCHEMA,
        "decision": DECISION,
        "operation": "attention_derived_residual_add",
        "target_id": RESIDUAL.TARGET_ID,
        "required_backend_version": RESIDUAL.REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": RESIDUAL.WIDTH,
        "row_count": RESIDUAL.WIDTH,
        "source_input_schema": SOURCE_INPUT_SCHEMA,
        "source_down_projection_proof_version": SOURCE_DOWN_PROJECTION_PROOF_VERSION,
        "residual_delta_scale_divisor": DERIVED_DOWN.DOWN.FF_DIM,
        "non_claims": NON_CLAIMS,
        "next_backend_step": "compose the derived slice statements into a single checked block statement boundary",
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ResidualAddError(f"residual-add field mismatch: {field}")
    if data["residual_delta_commitment"] == data["output_activation_commitment"]:
        raise AttentionDerivedD128ResidualAddError("residual delta commitment relabeled as full output commitment")
    if data["input_activation_commitment"] == data["output_activation_commitment"]:
        raise AttentionDerivedD128ResidualAddError("input activation commitment relabeled as output activation commitment")
    _digest(data["source_input_payload_commitment"], "source input payload commitment", prefix="sha256")
    _digest(data["source_down_projection_payload_commitment"], "source down-projection payload commitment", prefix="sha256")
    _digest(data["residual_delta_remainder_sha256"], "residual delta remainder SHA-256", prefix="sha256")
    for field in (
        "source_attention_outputs_commitment",
        "source_down_projection_statement_commitment",
        "source_down_projection_public_instance_commitment",
        "input_activation_commitment",
        "residual_delta_commitment",
        "output_activation_commitment",
        "residual_add_row_commitment",
        "proof_native_parameter_commitment",
        "public_instance_commitment",
        "statement_commitment",
    ):
        _digest(data[field], f"residual-add {field}")
    input_q8 = [_int(item, f"input {index}") for index, item in enumerate(_list(data.get("input_q8"), "input"))]
    residual_delta_q8 = [
        _int(item, f"residual delta {index}") for index, item in enumerate(_list(data.get("residual_delta_q8"), "residual delta"))
    ]
    residual_delta_remainder_q8 = [
        _int(item, f"residual delta remainder {index}")
        for index, item in enumerate(_list(data.get("residual_delta_remainder_q8"), "residual delta remainder"))
    ]
    output_q8 = [_int(item, f"output {index}") for index, item in enumerate(_list(data.get("output_q8"), "output"))]
    if len(input_q8) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("input vector mismatch")
    if len(residual_delta_q8) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("residual delta vector mismatch")
    if len(residual_delta_remainder_q8) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("residual delta remainder vector mismatch")
    if len(output_q8) != RESIDUAL.WIDTH:
        raise AttentionDerivedD128ResidualAddError("output vector mismatch")
    for index, value in enumerate(input_q8):
        RESIDUAL.require_signed_q8(value, f"input {index}")
    for label, values in (("residual delta", residual_delta_q8), ("output", output_q8)):
        for index, value in enumerate(values):
            RESIDUAL.require_signed_m31(value, f"{label} {index}")
    for index, value in enumerate(residual_delta_remainder_q8):
        if value < 0 or value >= data["residual_delta_scale_divisor"]:
            raise AttentionDerivedD128ResidualAddError(f"residual delta remainder {index} outside divisor range")
    if sha256_hex(residual_delta_remainder_q8) != data["residual_delta_remainder_sha256"].removeprefix("sha256:"):
        raise AttentionDerivedD128ResidualAddError("residual delta remainder hash drift")
    if DERIVED_DOWN.DOWN.residual_delta_commitment(
        residual_delta_q8,
        residual_delta_remainder_q8,
        data["residual_delta_scale_divisor"],
    ) != data["residual_delta_commitment"]:
        raise AttentionDerivedD128ResidualAddError("residual delta commitment drift")
    if RESIDUAL.sequence_commitment(input_q8, RESIDUAL.INPUT_ACTIVATION_DOMAIN, [RESIDUAL.WIDTH]) != data["input_activation_commitment"]:
        raise AttentionDerivedD128ResidualAddError("input activation commitment drift")
    if RESIDUAL.sequence_commitment(output_q8, RESIDUAL.OUTPUT_ACTIVATION_DOMAIN, [RESIDUAL.WIDTH]) != data["output_activation_commitment"]:
        raise AttentionDerivedD128ResidualAddError("output activation commitment drift")
    rows = _list(data.get("rows"), "rows")
    recomputed_rows = RESIDUAL.build_rows(input_q8, residual_delta_q8)
    if rows != recomputed_rows:
        raise AttentionDerivedD128ResidualAddError("residual-add row relation drift")
    if [row["output_q8"] for row in rows] != output_q8:
        raise AttentionDerivedD128ResidualAddError("output activation row drift")
    if RESIDUAL.rows_commitment(rows) != data["residual_add_row_commitment"]:
        raise AttentionDerivedD128ResidualAddError("residual-add row commitment drift")
    if proof_native_parameter_commitment(data["source_down_projection_statement_commitment"]) != data["proof_native_parameter_commitment"]:
        raise AttentionDerivedD128ResidualAddError("proof-native parameter commitment drift")
    if source_input is not None:
        validate_source_input(source_input)
        source_summary = _dict(source_input.get("summary"), "source input summary")
        if data["source_input_payload_commitment"] != source_input["payload_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source input payload commitment drift")
        if data["source_attention_outputs_commitment"] != source_summary["source_attention_outputs_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source attention output commitment drift")
        if data["input_activation_commitment"] != source_summary["derived_input_activation_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source input activation drift")
    if source_down is not None:
        validate_source_down(source_down)
        down = _dict(source_down.get("down_projection_payload"), "source down-projection nested payload")
        if data["source_down_projection_payload_commitment"] != source_down["payload_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source down-projection payload commitment drift")
        if data["source_down_projection_statement_commitment"] != down["statement_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source down-projection statement drift")
        if data["source_down_projection_public_instance_commitment"] != down["public_instance_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source down-projection public instance drift")
        if data["residual_delta_commitment"] != down["residual_delta_commitment"]:
            raise AttentionDerivedD128ResidualAddError("source residual delta drift")
    if statement_commitment(data) != data["statement_commitment"]:
        raise AttentionDerivedD128ResidualAddError("statement commitment drift")
    if public_instance_commitment(data["statement_commitment"]) != data["public_instance_commitment"]:
        raise AttentionDerivedD128ResidualAddError("public instance commitment drift")


def build_context() -> dict[str, Any]:
    source_input, source_input_raw = load_json(SOURCE_INPUT_JSON)
    source_down, source_down_raw = load_json(SOURCE_DOWN_JSON)
    current_residual, current_residual_raw = load_json(CURRENT_RESIDUAL_JSON)
    validate_source_input(source_input, full=True)
    validate_source_down(source_down, full=True)
    try:
        RESIDUAL.validate_payload(current_residual)
    except Exception as err:
        raise AttentionDerivedD128ResidualAddError(f"current residual-add fixture invalid: {err}") from err
    residual_payload = build_residual_add_payload(source_input, source_down)
    current_input = [
        _int(item, f"current residual input {index}")
        for index, item in enumerate(_list(current_residual.get("input_q8"), "current residual input"))
    ]
    current_residual_delta = [
        _int(item, f"current residual delta {index}")
        for index, item in enumerate(_list(current_residual.get("residual_delta_q8"), "current residual delta"))
    ]
    current_output = [
        _int(item, f"current residual output {index}")
        for index, item in enumerate(_list(current_residual.get("output_q8"), "current residual output"))
    ]
    comparison = {
        "current_residual_add_statement_commitment": current_residual["statement_commitment"],
        "current_residual_add_public_instance_commitment": current_residual["public_instance_commitment"],
        "current_input_activation_commitment": current_residual["input_activation_commitment"],
        "current_residual_delta_commitment": current_residual["residual_delta_commitment"],
        "current_output_activation_commitment": current_residual["output_activation_commitment"],
        "current_residual_add_row_commitment": current_residual["residual_add_row_commitment"],
        "input_mismatch_count": sequence_mismatch_count(residual_payload["input_q8"], current_input, "input"),
        "residual_delta_mismatch_count": sequence_mismatch_count(
            residual_payload["residual_delta_q8"], current_residual_delta, "residual delta"
        ),
        "output_mismatch_count": sequence_mismatch_count(residual_payload["output_q8"], current_output, "output"),
        "matches_existing_d128_residual_add": False,
    }
    source_input_summary = _dict(source_input.get("summary"), "source input summary")
    source_down_summary = _dict(source_down.get("summary"), "source down-projection summary")
    return {
        "source_artifacts": [
            source_artifact("attention_derived_d128_input", SOURCE_INPUT_JSON, source_input),
            source_artifact("attention_derived_d128_down_projection", SOURCE_DOWN_JSON, source_down),
            {
                "id": "current_d128_residual_add_input",
                "path": CURRENT_RESIDUAL_JSON.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(current_residual_raw).hexdigest(),
                "payload_sha256": hashlib.sha256(canonical_json_bytes(current_residual)).hexdigest(),
            },
            source_artifact("attention_derived_input_gate", DERIVED_INPUT_GATE_PATH),
            source_artifact("attention_derived_down_projection_gate", DERIVED_DOWN_GATE_PATH),
            source_artifact("d128_residual_add_generator", RESIDUAL_ADD_PATH),
            source_artifact("attention_derived_residual_add_gate", THIS_GATE_PATH),
        ],
        "source_summary": {
            "source_input_payload_sha256": hashlib.sha256(source_input_raw).hexdigest(),
            "source_input_payload_commitment": source_input["payload_commitment"],
            "source_attention_outputs_commitment": source_input_summary["source_attention_outputs_commitment"],
            "source_input_activation_commitment": source_input_summary["derived_input_activation_commitment"],
            "source_down_projection_payload_sha256": hashlib.sha256(source_down_raw).hexdigest(),
            "source_down_projection_payload_commitment": source_down["payload_commitment"],
            "source_down_projection_statement_commitment": source_down_summary["derived_down_projection_statement_commitment"],
            "source_residual_delta_commitment": source_down_summary["derived_residual_delta_commitment"],
        },
        "source_input": source_input,
        "source_down": source_down,
        "residual_add_payload": residual_payload,
        "comparison_summary": comparison,
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    residual_payload = context["residual_add_payload"]
    source_summary = context["source_summary"]
    comparison = context["comparison_summary"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "source_summary": copy.deepcopy(source_summary),
        "residual_add_payload": copy.deepcopy(residual_payload),
        "comparison_summary": copy.deepcopy(comparison),
        "summary": {
            "go_result": (
                "GO for attention-derived d128 input plus derived residual delta producing a derived output activation"
            ),
            "no_go_result": "NO-GO for claiming one composed d128 block proof or existing d128 residual receipt consumption",
            "source_input_activation_commitment": source_summary["source_input_activation_commitment"],
            "source_residual_delta_commitment": source_summary["source_residual_delta_commitment"],
            "derived_output_activation_commitment": residual_payload["output_activation_commitment"],
            "derived_residual_add_statement_commitment": residual_payload["statement_commitment"],
            "derived_residual_add_public_instance_commitment": residual_payload["public_instance_commitment"],
            "derived_residual_add_row_commitment": residual_payload["residual_add_row_commitment"],
            "residual_add_rows": residual_payload["row_count"],
            "matches_existing_d128_residual_add": False,
            "input_mismatch_count": comparison["input_mismatch_count"],
            "residual_delta_mismatch_count": comparison["residual_delta_mismatch_count"],
            "output_mismatch_count": comparison["output_mismatch_count"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_core_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    if set(payload) not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128ResidualAddError("payload key set drift")
    if payload.get("schema") != SCHEMA:
        raise AttentionDerivedD128ResidualAddError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionDerivedD128ResidualAddError("decision drift")
    if payload.get("result") != RESULT:
        raise AttentionDerivedD128ResidualAddError("result drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128ResidualAddError("claim boundary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128ResidualAddError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128ResidualAddError("validation commands drift")
    context = build_context() if context is None else context
    expected_core = build_core_payload(context)
    comparable = {key: value for key, value in payload.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected = {key: value for key, value in expected_core.items() if key != "payload_commitment"}
    if comparable != expected:
        raise AttentionDerivedD128ResidualAddError("derived residual-add payload drift")
    validate_residual_add_payload(
        _dict(payload.get("residual_add_payload"), "residual-add payload"),
        source_input=_dict(context.get("source_input"), "context source input"),
        source_down=_dict(context.get("source_down"), "context source down-projection"),
    )
    comparison = _dict(payload.get("comparison_summary"), "comparison summary")
    summary = _dict(payload.get("summary"), "summary")
    if summary.get("matches_existing_d128_residual_add") is not False:
        raise AttentionDerivedD128ResidualAddError("existing residual-add consumption overclaim")
    if comparison.get("matches_existing_d128_residual_add") is not False:
        raise AttentionDerivedD128ResidualAddError("comparison overclaim")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128ResidualAddError("payload commitment drift")


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    context = build_context() if context is None else context
    validate_core_payload(data, context=context)
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ResidualAddError("mutation case count drift")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ResidualAddError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ResidualAddError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionDerivedD128ResidualAddError("not all mutations rejected")
        expected_cases = run_mutation_cases(build_core_payload(context), context)
        for index, (expected_name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionDerivedD128ResidualAddError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AttentionDerivedD128ResidualAddError("mutation case order drift")
            if _bool(case.get("accepted"), "mutation accepted") is not False:
                raise AttentionDerivedD128ResidualAddError("mutation accepted")
            if _bool(case.get("rejected"), "mutation rejected") is not True:
                raise AttentionDerivedD128ResidualAddError("mutation not rejected")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise AttentionDerivedD128ResidualAddError("mutation error field drift")
            if case != expected_cases[index]:
                raise AttentionDerivedD128ResidualAddError("mutation case drift")


MutationFn = Callable[[dict[str, Any]], None]


def _set_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_TRANSFORMER_BLOCK"), True),
    ("result_overclaim", lambda p: p.__setitem__("result", "GO_SINGLE_COMPOSED_BLOCK_PROOF"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_RECURSIVE_LAYER_PROOF"), True),
    (
        "source_input_payload_commitment_drift",
        lambda p: p["residual_add_payload"].__setitem__("source_input_payload_commitment", "sha256:" + "22" * 32),
        True,
    ),
    (
        "source_down_payload_commitment_drift",
        lambda p: p["residual_add_payload"].__setitem__("source_down_projection_payload_commitment", "sha256:" + "33" * 32),
        True,
    ),
    (
        "input_vector_drift",
        lambda p: p["residual_add_payload"]["input_q8"].__setitem__(0, p["residual_add_payload"]["input_q8"][0] + 1),
        True,
    ),
    (
        "residual_delta_vector_drift",
        lambda p: p["residual_add_payload"]["residual_delta_q8"].__setitem__(
            0, p["residual_add_payload"]["residual_delta_q8"][0] + 1
        ),
        True,
    ),
    (
        "residual_delta_remainder_drift",
        lambda p: p["residual_add_payload"]["residual_delta_remainder_q8"].__setitem__(
            0, (p["residual_add_payload"]["residual_delta_remainder_q8"][0] + 1) % DERIVED_DOWN.DOWN.FF_DIM
        ),
        True,
    ),
    (
        "output_vector_drift",
        lambda p: p["residual_add_payload"]["output_q8"].__setitem__(0, p["residual_add_payload"]["output_q8"][0] + 1),
        True,
    ),
    (
        "row_relation_drift",
        lambda p: p["residual_add_payload"]["rows"][0].__setitem__("output_q8", p["residual_add_payload"]["rows"][0]["output_q8"] + 1),
        True,
    ),
    (
        "row_commitment_drift",
        lambda p: p["residual_add_payload"].__setitem__("residual_add_row_commitment", "blake2b-256:" + "44" * 32),
        True,
    ),
    (
        "output_relabels_input",
        lambda p: p["residual_add_payload"].__setitem__(
            "output_activation_commitment", p["residual_add_payload"]["input_activation_commitment"]
        ),
        True,
    ),
    (
        "output_relabels_residual_delta",
        lambda p: p["residual_add_payload"].__setitem__(
            "output_activation_commitment", p["residual_add_payload"]["residual_delta_commitment"]
        ),
        True,
    ),
    (
        "current_residual_consumption_overclaim",
        lambda p: p["summary"].__setitem__("matches_existing_d128_residual_add", True),
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
    "source_input_payload_commitment_drift": "derived residual-add payload drift",
    "source_down_payload_commitment_drift": "derived residual-add payload drift",
    "input_vector_drift": "derived residual-add payload drift",
    "residual_delta_vector_drift": "derived residual-add payload drift",
    "residual_delta_remainder_drift": "derived residual-add payload drift",
    "output_vector_drift": "derived residual-add payload drift",
    "row_relation_drift": "derived residual-add payload drift",
    "row_commitment_drift": "derived residual-add payload drift",
    "output_relabels_input": "derived residual-add payload drift",
    "output_relabels_residual_delta": "derived residual-add payload drift",
    "current_residual_consumption_overclaim": "derived residual-add payload drift",
    "source_artifact_hash_drift": "derived residual-add payload drift",
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
        except AttentionDerivedD128ResidualAddError as err:
            expected_error = EXPECTED_MUTATION_ERRORS.get(name)
            if expected_error is None:
                raise AttentionDerivedD128ResidualAddError(f"mutation error marker missing: {name}") from err
            actual_error = str(err)
            if expected_error not in actual_error:
                raise AttentionDerivedD128ResidualAddError(
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
        raise AttentionDerivedD128ResidualAddError("TSV requires finalized payload")
    row = {
        "decision": payload["decision"],
        "result": payload["result"],
        "source_input_activation_commitment": payload["summary"]["source_input_activation_commitment"],
        "source_residual_delta_commitment": payload["summary"]["source_residual_delta_commitment"],
        "derived_output_activation_commitment": payload["summary"]["derived_output_activation_commitment"],
        "derived_residual_add_statement_commitment": payload["summary"]["derived_residual_add_statement_commitment"],
        "residual_add_rows": payload["summary"]["residual_add_rows"],
        "input_mismatch_count": payload["summary"]["input_mismatch_count"],
        "residual_delta_mismatch_count": payload["summary"]["residual_delta_mismatch_count"],
        "output_mismatch_count": payload["summary"]["output_mismatch_count"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return handle.getvalue()


def write_outputs(
    payload: dict[str, Any],
    json_path: pathlib.Path | None = None,
    tsv_path: pathlib.Path | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    validate_payload(payload, context=context)
    if json_path is not None:
        try:
            DERIVED_DOWN.atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n", suffix=".json")
        except Exception as err:
            raise AttentionDerivedD128ResidualAddError(str(err)) from err
    if tsv_path is not None:
        try:
            DERIVED_DOWN.atomic_write_text(tsv_path, to_tsv(payload, context=context), suffix=".tsv")
        except Exception as err:
            raise AttentionDerivedD128ResidualAddError(str(err)) from err


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
        "source_input_activation_commitment": payload["summary"]["source_input_activation_commitment"],
        "source_residual_delta_commitment": payload["summary"]["source_residual_delta_commitment"],
        "derived_output_activation_commitment": payload["summary"]["derived_output_activation_commitment"],
        "residual_add_rows": payload["summary"]["residual_add_rows"],
        "mutations_rejected": sum(1 for case in payload["cases"] if case["rejected"]),
    }
    print(json.dumps(payload if args.json else summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
