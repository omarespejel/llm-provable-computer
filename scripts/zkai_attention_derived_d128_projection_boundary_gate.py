#!/usr/bin/env python3
"""Build the attention-derived d128 projection-boundary gate."""

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
DERIVED_RMSNORM_JSON = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
CURRENT_GATE_VALUE_JSON = EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.json"
TARGET_JSON = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-projection-boundary-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-projection-boundary-2026-05.tsv"

DERIVED_RMSNORM_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_rmsnorm_public_row_gate.py"
BRIDGE_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_to_projection_bridge_input.py"
GATE_VALUE_PATH = ROOT / "scripts" / "zkai_d128_gate_value_projection_proof_input.py"
THIS_GATE_PATH = ROOT / "scripts" / "zkai_attention_derived_d128_projection_boundary_gate.py"

SCHEMA = "zkai-attention-derived-d128-projection-boundary-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_PROJECTION_BOUNDARY_INPUT"
RESULT = "GO_VALUE_CONNECTED_GATE_VALUE_PROJECTION_INPUT_NO_GO_FULL_BLOCK"
CLAIM_BOUNDARY = (
    "CHECKED_ATTENTION_DERIVED_D128_RMSNORM_OUTPUT_FEEDS_D128_PROJECTION_BOUNDARY_"
    "AND_GATE_VALUE_PROJECTION_INPUT_NOT_EXISTING_BLOCK_RECEIPT_NOT_FULL_LAYER_PROOF"
)

NON_CLAIMS = [
    "not evidence that the existing d128 block receipt consumed the derived vector",
    "not a learned model projection",
    "not a full transformer block proof",
    "not a down-projection or residual proof",
    "not one recursive or compressed proof object",
    "not a matched NANOZK/Jolt/DeepProve benchmark",
    "not proof-size or timing evidence",
    "not production-ready",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_attention_derived_d128_projection_boundary_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-projection-boundary-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-projection-boundary-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_projection_boundary_gate",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_projection_boundary_gate.py scripts/tests/test_zkai_attention_derived_d128_projection_boundary_gate.py",
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
    "bridge_payload",
    "gate_value_projection_payload",
    "comparison_summary",
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
    "derived_input_activation_commitment",
    "derived_rmsnorm_output_row_commitment",
    "derived_projection_input_row_commitment",
    "derived_bridge_statement_commitment",
    "derived_gate_value_projection_output_commitment",
    "gate_value_mul_rows",
    "current_projection_input_mismatch_count",
    "current_gate_projection_mismatch_count",
    "current_value_projection_mismatch_count",
    "mutations_rejected",
)


class AttentionDerivedD128ProjectionBoundaryError(ValueError):
    pass


def _load_module(path: pathlib.Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AttentionDerivedD128ProjectionBoundaryError(f"failed to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DERIVED_RMSNORM = _load_module(DERIVED_RMSNORM_GATE_PATH, "zkai_attention_derived_d128_rmsnorm_public_row_gate")
BRIDGE = _load_module(BRIDGE_PATH, "zkai_d128_rmsnorm_to_projection_bridge_input")
GATE_VALUE = _load_module(GATE_VALUE_PATH, "zkai_d128_gate_value_projection_proof_input")
VALUE_GATE = DERIVED_RMSNORM.VALUE_GATE


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
        raise AttentionDerivedD128ProjectionBoundaryError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AttentionDerivedD128ProjectionBoundaryError(f"{label} must be list")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AttentionDerivedD128ProjectionBoundaryError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AttentionDerivedD128ProjectionBoundaryError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    try:
        return DERIVED_RMSNORM._commitment(value, label)
    except Exception as err:
        raise AttentionDerivedD128ProjectionBoundaryError(str(err)) from err


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    try:
        return VALUE_GATE.load_json(path)
    except Exception as err:
        raise AttentionDerivedD128ProjectionBoundaryError(str(err)) from err


def source_artifact(artifact_id: str, path: pathlib.Path, payload: Any | None = None) -> dict[str, Any]:
    try:
        raw = VALUE_GATE.read_source_bytes(path)
    except Exception as err:
        raise AttentionDerivedD128ProjectionBoundaryError(str(err)) from err
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
        raise AttentionDerivedD128ProjectionBoundaryError(f"{label} length mismatch")
    return sum(1 for left_value, right_value in zip(left, right, strict=True) if left_value != right_value)


def rmsnorm_output_values(rmsnorm_payload: dict[str, Any]) -> list[int]:
    rows = _list(rmsnorm_payload.get("rows"), "RMSNorm rows")
    if len(rows) != BRIDGE.WIDTH:
        raise AttentionDerivedD128ProjectionBoundaryError("RMSNorm row width mismatch")
    values: list[int] = []
    for index, row_value in enumerate(rows):
        row = _dict(row_value, f"RMSNorm row {index}")
        if row.get("index") != index:
            raise AttentionDerivedD128ProjectionBoundaryError("RMSNorm row index drift")
        values.append(_int(row.get("normed_q8"), f"RMSNorm normed value {index}"))
    return values


def build_bridge_payload(rmsnorm_payload: dict[str, Any]) -> dict[str, Any]:
    validate_rmsnorm_source(rmsnorm_payload)
    target = BRIDGE.load_target(TARGET_JSON)
    target_commitment = BRIDGE.validate_target(target)
    values = rmsnorm_output_values(rmsnorm_payload)
    rows = [
        {
            "index": index,
            "rmsnorm_normed_q8": value,
            "projection_input_q8": value,
        }
        for index, value in enumerate(values)
    ]
    payload = {
        "schema": "zkai-attention-derived-d128-rmsnorm-to-projection-bridge-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_RMSNORM_TO_PROJECTION_BRIDGE_INPUT",
        "operation": "rmsnorm_to_projection_bridge",
        "target_id": BRIDGE.TARGET_ID,
        "required_backend_version": BRIDGE.REQUIRED_BACKEND_VERSION,
        "verifier_domain": BRIDGE.VERIFIER_DOMAIN,
        "width": BRIDGE.WIDTH,
        "row_count": BRIDGE.WIDTH,
        "source_rmsnorm_public_row_proof_version": BRIDGE.SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source_rmsnorm_statement_commitment": rmsnorm_payload["statement_commitment"],
        "source_rmsnorm_public_instance_commitment": rmsnorm_payload["public_instance_commitment"],
        "source_rmsnorm_output_row_domain": BRIDGE.SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN,
        "projection_input_row_domain": BRIDGE.PROJECTION_INPUT_ROW_DOMAIN,
        "source_rmsnorm_output_row_commitment": rmsnorm_payload["rmsnorm_output_row_commitment"],
        "projection_input_row_commitment": BRIDGE.sequence_commitment(values, BRIDGE.PROJECTION_INPUT_ROW_DOMAIN),
        "forbidden_output_activation_commitment": BRIDGE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT,
        "public_instance_commitment": "",
        "proof_native_parameter_commitment": "",
        "statement_commitment": "",
        "rows": rows,
        "non_claims": [
            "not full d128 block proof",
            "not gate, value, or down projection proof",
            "not activation, SwiGLU, or residual proof",
            "not binding the full d128 output_activation_commitment",
            "bridge proves only the domain-separated handoff from derived RMSNorm rows to projection-input rows",
        ],
        "proof_verifier_hardening": [
            "derived RMSNorm public-row payload validation before bridge construction",
            "derived RMSNorm output row commitment recomputation before bridge validation",
            "projection input row commitment recomputation before bridge validation",
            "statement/public-instance/native-parameter commitments recomputed before bridge validation",
            "full output_activation_commitment relabeling rejection",
        ],
        "next_backend_step": (
            "encode d128 gate/value projection rows that consume the derived projection_input_row_commitment"
        ),
    }
    statement = BRIDGE.statement_commitment(payload, target_commitment)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = BRIDGE.public_instance_commitment(statement)
    payload["proof_native_parameter_commitment"] = BRIDGE.proof_native_parameter_commitment(statement)
    validate_bridge_payload(payload, rmsnorm_payload=rmsnorm_payload)
    return payload


def gate_value_statement_commitment(payload: dict[str, Any]) -> str:
    return GATE_VALUE.blake2b_commitment(
        {
            "ff_dim": payload["ff_dim"],
            "gate_matrix_root": payload["gate_matrix_root"],
            "gate_projection_output_commitment": payload["gate_projection_output_commitment"],
            "gate_value_projection_mul_row_commitment": payload["gate_value_projection_mul_row_commitment"],
            "gate_value_projection_output_commitment": payload["gate_value_projection_output_commitment"],
            "operation": "gate_value_projection",
            "proof_native_parameter_commitment": payload["proof_native_parameter_commitment"],
            "required_backend_version": GATE_VALUE.REQUIRED_BACKEND_VERSION,
            "row_count": payload["row_count"],
            "source_bridge_proof_version": payload["source_bridge_proof_version"],
            "source_bridge_statement_commitment": payload["source_bridge_statement_commitment"],
            "source_projection_input_row_commitment": payload["source_projection_input_row_commitment"],
            "target_commitment": GATE_VALUE.TARGET_COMMITMENT,
            "target_id": GATE_VALUE.TARGET_ID,
            "value_matrix_root": payload["value_matrix_root"],
            "value_projection_output_commitment": payload["value_projection_output_commitment"],
            "verifier_domain": GATE_VALUE.VERIFIER_DOMAIN,
            "width": payload["width"],
        },
        GATE_VALUE.VERIFIER_DOMAIN,
    )


def build_gate_value_projection_payload(bridge_payload: dict[str, Any]) -> dict[str, Any]:
    validate_bridge_payload(bridge_payload)
    inputs = [_int(row["projection_input_q8"], f"projection input {index}") for index, row in enumerate(bridge_payload["rows"])]
    rows, gate, value = GATE_VALUE.build_rows(inputs)
    gate_root = GATE_VALUE.matrix_root(rows, "gate")
    value_root = GATE_VALUE.matrix_root(rows, "value")
    native_parameter = GATE_VALUE.proof_native_parameter_commitment(gate_root, value_root)
    payload = {
        "schema": "zkai-attention-derived-d128-gate-value-projection-input-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_GATE_VALUE_PROJECTION_INPUT",
        "operation": "gate_value_projection",
        "target_id": GATE_VALUE.TARGET_ID,
        "required_backend_version": GATE_VALUE.REQUIRED_BACKEND_VERSION,
        "verifier_domain": GATE_VALUE.VERIFIER_DOMAIN,
        "width": GATE_VALUE.WIDTH,
        "ff_dim": GATE_VALUE.FF_DIM,
        "row_count": 2 * GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH,
        "gate_projection_mul_rows": GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH,
        "value_projection_mul_rows": GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH,
        "source_bridge_proof_version": GATE_VALUE.SOURCE_BRIDGE_PROOF_VERSION,
        "source_bridge_statement_commitment": bridge_payload["statement_commitment"],
        "source_bridge_public_instance_commitment": bridge_payload["public_instance_commitment"],
        "source_projection_input_row_commitment": bridge_payload["projection_input_row_commitment"],
        "gate_matrix_root": gate_root,
        "value_matrix_root": value_root,
        "proof_native_parameter_commitment": native_parameter,
        "gate_projection_output_commitment": GATE_VALUE.sequence_commitment(
            gate, GATE_VALUE.GATE_PROJECTION_OUTPUT_DOMAIN, [GATE_VALUE.FF_DIM]
        ),
        "value_projection_output_commitment": GATE_VALUE.sequence_commitment(
            value, GATE_VALUE.VALUE_PROJECTION_OUTPUT_DOMAIN, [GATE_VALUE.FF_DIM]
        ),
        "gate_value_projection_output_commitment": GATE_VALUE.output_commitment(gate, value),
        "gate_value_projection_mul_row_commitment": GATE_VALUE.rows_commitment(rows),
        "public_instance_commitment": "",
        "statement_commitment": "",
        "projection_input_q8": inputs,
        "gate_projection_q8": gate,
        "value_projection_q8": value,
        "non_claims": [
            "not full d128 block proof",
            "not activation or SwiGLU proof",
            "not down projection proof",
            "not residual proof",
            "not recursive composition",
            "synthetic deterministic gate/value parameters only",
            "not binding the full d128 output_activation_commitment",
            "output aggregation is verifier-recomputed from checked public multiplication rows",
        ],
        "proof_verifier_hardening": [
            "derived RMSNorm-to-projection bridge validation before projection construction",
            "projection input row commitment recomputation before projection validation",
            "gate/value output commitment recomputation before projection validation",
            "gate/value multiplication row commitment recomputation before projection validation",
            "statement/public-instance/native-parameter commitments recomputed before projection validation",
            "full output_activation_commitment relabeling rejection",
        ],
        "next_backend_step": (
            "encode activation/SwiGLU rows that consume the derived gate_value_projection_output_commitment"
        ),
    }
    statement = gate_value_statement_commitment(payload)
    payload["statement_commitment"] = statement
    payload["public_instance_commitment"] = GATE_VALUE.public_instance_commitment(statement)
    validate_gate_value_projection_payload(payload, bridge_payload=bridge_payload)
    return payload


def validate_rmsnorm_source(payload: Any) -> None:
    data = _dict(payload, "RMSNorm payload")
    try:
        DERIVED_RMSNORM.RMSNORM.validate_payload(data)
    except Exception as err:
        raise AttentionDerivedD128ProjectionBoundaryError(f"derived RMSNorm source invalid: {err}") from err
    constants = {
        "schema": DERIVED_RMSNORM.RMSNORM.SCHEMA,
        "decision": DERIVED_RMSNORM.RMSNORM.DECISION,
        "operation": DERIVED_RMSNORM.RMSNORM.OPERATION,
        "target_id": BRIDGE.TARGET_ID,
        "required_backend_version": BRIDGE.REQUIRED_BACKEND_VERSION,
        "width": BRIDGE.WIDTH,
        "row_count": BRIDGE.WIDTH,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ProjectionBoundaryError(f"derived RMSNorm field mismatch: {field}")
    values = rmsnorm_output_values(data)
    if BRIDGE.sequence_commitment(values, BRIDGE.SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN) != data["rmsnorm_output_row_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("derived RMSNorm output commitment drift")


def validate_bridge_payload(payload: Any, *, rmsnorm_payload: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "bridge payload")
    expected_fields = {
        "schema",
        "decision",
        "operation",
        "target_id",
        "required_backend_version",
        "verifier_domain",
        "width",
        "row_count",
        "source_rmsnorm_public_row_proof_version",
        "source_rmsnorm_statement_commitment",
        "source_rmsnorm_public_instance_commitment",
        "source_rmsnorm_output_row_domain",
        "projection_input_row_domain",
        "source_rmsnorm_output_row_commitment",
        "projection_input_row_commitment",
        "forbidden_output_activation_commitment",
        "public_instance_commitment",
        "proof_native_parameter_commitment",
        "statement_commitment",
        "rows",
        "non_claims",
        "proof_verifier_hardening",
        "next_backend_step",
    }
    if set(data) != expected_fields:
        raise AttentionDerivedD128ProjectionBoundaryError("bridge field set drift")
    constants = {
        "schema": "zkai-attention-derived-d128-rmsnorm-to-projection-bridge-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_RMSNORM_TO_PROJECTION_BRIDGE_INPUT",
        "operation": "rmsnorm_to_projection_bridge",
        "target_id": BRIDGE.TARGET_ID,
        "required_backend_version": BRIDGE.REQUIRED_BACKEND_VERSION,
        "verifier_domain": BRIDGE.VERIFIER_DOMAIN,
        "width": BRIDGE.WIDTH,
        "row_count": BRIDGE.WIDTH,
        "source_rmsnorm_public_row_proof_version": BRIDGE.SOURCE_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source_rmsnorm_output_row_domain": BRIDGE.SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN,
        "projection_input_row_domain": BRIDGE.PROJECTION_INPUT_ROW_DOMAIN,
        "forbidden_output_activation_commitment": BRIDGE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ProjectionBoundaryError(f"bridge field mismatch: {field}")
    for field in (
        "source_rmsnorm_statement_commitment",
        "source_rmsnorm_public_instance_commitment",
        "source_rmsnorm_output_row_commitment",
        "projection_input_row_commitment",
        "public_instance_commitment",
        "proof_native_parameter_commitment",
        "statement_commitment",
    ):
        _commitment(data[field], f"bridge {field}")
    if data["projection_input_row_commitment"] == data["forbidden_output_activation_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("projection input relabeled as full output")
    rows = _list(data.get("rows"), "bridge rows")
    if len(rows) != BRIDGE.WIDTH:
        raise AttentionDerivedD128ProjectionBoundaryError("bridge row width mismatch")
    rms_values: list[int] = []
    projection_values: list[int] = []
    for index, row_value in enumerate(rows):
        row = _dict(row_value, f"bridge row {index}")
        if set(row) != {"index", "rmsnorm_normed_q8", "projection_input_q8"}:
            raise AttentionDerivedD128ProjectionBoundaryError("bridge row field set drift")
        if row["index"] != index:
            raise AttentionDerivedD128ProjectionBoundaryError("bridge row index drift")
        rms_value = _int(row["rmsnorm_normed_q8"], "bridge rmsnorm value")
        projection_value = _int(row["projection_input_q8"], "bridge projection value")
        if rms_value != projection_value:
            raise AttentionDerivedD128ProjectionBoundaryError("bridge equality drift")
        BRIDGE.require_signed_m31(rms_value, "bridge rmsnorm value")
        BRIDGE.require_signed_m31(projection_value, "bridge projection value")
        rms_values.append(rms_value)
        projection_values.append(projection_value)
    if BRIDGE.sequence_commitment(rms_values, BRIDGE.SOURCE_RMSNORM_OUTPUT_ROW_DOMAIN) != data["source_rmsnorm_output_row_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("source RMSNorm output commitment recomputation drift")
    if BRIDGE.sequence_commitment(projection_values, BRIDGE.PROJECTION_INPUT_ROW_DOMAIN) != data["projection_input_row_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("projection input commitment recomputation drift")
    if rmsnorm_payload is not None:
        validate_rmsnorm_source(rmsnorm_payload)
        if data["source_rmsnorm_statement_commitment"] != rmsnorm_payload["statement_commitment"]:
            raise AttentionDerivedD128ProjectionBoundaryError("bridge source statement does not bind derived RMSNorm")
        if data["source_rmsnorm_public_instance_commitment"] != rmsnorm_payload["public_instance_commitment"]:
            raise AttentionDerivedD128ProjectionBoundaryError("bridge source public instance does not bind derived RMSNorm")
        if data["source_rmsnorm_output_row_commitment"] != rmsnorm_payload["rmsnorm_output_row_commitment"]:
            raise AttentionDerivedD128ProjectionBoundaryError("bridge source output does not bind derived RMSNorm")
    target = BRIDGE.load_target(TARGET_JSON)
    target_commitment = BRIDGE.validate_target(target)
    statement = BRIDGE.statement_commitment(data, target_commitment)
    if data["statement_commitment"] != statement:
        raise AttentionDerivedD128ProjectionBoundaryError("bridge statement commitment drift")
    if data["public_instance_commitment"] != BRIDGE.public_instance_commitment(statement):
        raise AttentionDerivedD128ProjectionBoundaryError("bridge public instance commitment drift")
    if data["proof_native_parameter_commitment"] != BRIDGE.proof_native_parameter_commitment(statement):
        raise AttentionDerivedD128ProjectionBoundaryError("bridge proof-native parameter commitment drift")


def validate_gate_value_projection_payload(payload: Any, *, bridge_payload: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "gate/value payload")
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
        "gate_projection_mul_rows",
        "value_projection_mul_rows",
        "source_bridge_proof_version",
        "source_bridge_statement_commitment",
        "source_bridge_public_instance_commitment",
        "source_projection_input_row_commitment",
        "gate_matrix_root",
        "value_matrix_root",
        "proof_native_parameter_commitment",
        "gate_projection_output_commitment",
        "value_projection_output_commitment",
        "gate_value_projection_output_commitment",
        "gate_value_projection_mul_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
        "projection_input_q8",
        "gate_projection_q8",
        "value_projection_q8",
        "non_claims",
        "proof_verifier_hardening",
        "next_backend_step",
    }
    if set(data) != expected_fields:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value field set drift")
    constants = {
        "schema": "zkai-attention-derived-d128-gate-value-projection-input-v1",
        "decision": "GO_ATTENTION_DERIVED_D128_GATE_VALUE_PROJECTION_INPUT",
        "operation": "gate_value_projection",
        "target_id": GATE_VALUE.TARGET_ID,
        "required_backend_version": GATE_VALUE.REQUIRED_BACKEND_VERSION,
        "verifier_domain": GATE_VALUE.VERIFIER_DOMAIN,
        "width": GATE_VALUE.WIDTH,
        "ff_dim": GATE_VALUE.FF_DIM,
        "row_count": 2 * GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH,
        "gate_projection_mul_rows": GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH,
        "value_projection_mul_rows": GATE_VALUE.FF_DIM * GATE_VALUE.WIDTH,
        "source_bridge_proof_version": GATE_VALUE.SOURCE_BRIDGE_PROOF_VERSION,
        "gate_matrix_root": GATE_VALUE.GATE_MATRIX_ROOT,
        "value_matrix_root": GATE_VALUE.VALUE_MATRIX_ROOT,
    }
    for field, expected in constants.items():
        if data.get(field) != expected:
            raise AttentionDerivedD128ProjectionBoundaryError(f"gate/value field mismatch: {field}")
    for field in (
        "source_bridge_statement_commitment",
        "source_bridge_public_instance_commitment",
        "source_projection_input_row_commitment",
        "proof_native_parameter_commitment",
        "gate_projection_output_commitment",
        "value_projection_output_commitment",
        "gate_value_projection_output_commitment",
        "gate_value_projection_mul_row_commitment",
        "public_instance_commitment",
        "statement_commitment",
    ):
        _commitment(data[field], f"gate/value {field}")
    if data["gate_value_projection_output_commitment"] == GATE_VALUE.OUTPUT_ACTIVATION_COMMITMENT:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value output relabeled as full output")
    inputs = [_int(value, f"projection input {index}") for index, value in enumerate(_list(data["projection_input_q8"], "projection input"))]
    gate = [_int(value, f"gate output {index}") for index, value in enumerate(_list(data["gate_projection_q8"], "gate output"))]
    value = [_int(item, f"value output {index}") for index, item in enumerate(_list(data["value_projection_q8"], "value output"))]
    if len(inputs) != GATE_VALUE.WIDTH:
        raise AttentionDerivedD128ProjectionBoundaryError("projection input width mismatch")
    if len(gate) != GATE_VALUE.FF_DIM or len(value) != GATE_VALUE.FF_DIM:
        raise AttentionDerivedD128ProjectionBoundaryError("projection output width mismatch")
    rows, recomputed_gate, recomputed_value = GATE_VALUE.build_rows(inputs)
    if recomputed_gate != gate:
        raise AttentionDerivedD128ProjectionBoundaryError("gate projection output drift")
    if recomputed_value != value:
        raise AttentionDerivedD128ProjectionBoundaryError("value projection output drift")
    if GATE_VALUE.sequence_commitment(inputs, GATE_VALUE.PROJECTION_INPUT_ROW_DOMAIN, [GATE_VALUE.WIDTH]) != data["source_projection_input_row_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("projection input commitment recomputation drift")
    if GATE_VALUE.sequence_commitment(gate, GATE_VALUE.GATE_PROJECTION_OUTPUT_DOMAIN, [GATE_VALUE.FF_DIM]) != data["gate_projection_output_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("gate output commitment drift")
    if GATE_VALUE.sequence_commitment(value, GATE_VALUE.VALUE_PROJECTION_OUTPUT_DOMAIN, [GATE_VALUE.FF_DIM]) != data["value_projection_output_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("value output commitment drift")
    if GATE_VALUE.output_commitment(gate, value) != data["gate_value_projection_output_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value output commitment drift")
    if GATE_VALUE.rows_commitment(rows) != data["gate_value_projection_mul_row_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value row commitment drift")
    if GATE_VALUE.matrix_root(rows, "gate") != data["gate_matrix_root"]:
        raise AttentionDerivedD128ProjectionBoundaryError("gate matrix root drift")
    if GATE_VALUE.matrix_root(rows, "value") != data["value_matrix_root"]:
        raise AttentionDerivedD128ProjectionBoundaryError("value matrix root drift")
    if GATE_VALUE.proof_native_parameter_commitment(data["gate_matrix_root"], data["value_matrix_root"]) != data["proof_native_parameter_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value proof-native parameter drift")
    expected_bridge_public_instance = BRIDGE.public_instance_commitment(data["source_bridge_statement_commitment"])
    if data["source_bridge_public_instance_commitment"] != expected_bridge_public_instance:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value source bridge public instance commitment drift")
    if bridge_payload is not None:
        validate_bridge_payload(bridge_payload)
        if data["source_bridge_statement_commitment"] != bridge_payload["statement_commitment"]:
            raise AttentionDerivedD128ProjectionBoundaryError("gate/value source bridge statement drift")
        if data["source_bridge_public_instance_commitment"] != bridge_payload["public_instance_commitment"]:
            raise AttentionDerivedD128ProjectionBoundaryError("gate/value source bridge public instance drift")
        if data["source_projection_input_row_commitment"] != bridge_payload["projection_input_row_commitment"]:
            raise AttentionDerivedD128ProjectionBoundaryError("gate/value source projection input drift")
    statement = gate_value_statement_commitment(data)
    if data["statement_commitment"] != statement:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value statement commitment drift")
    if data["public_instance_commitment"] != GATE_VALUE.public_instance_commitment(statement):
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value public instance commitment drift")


def build_context() -> dict[str, Any]:
    derived_rmsnorm_gate, _derived_raw = load_json(DERIVED_RMSNORM_JSON)
    current_gate_value, current_raw = load_json(CURRENT_GATE_VALUE_JSON)
    try:
        DERIVED_RMSNORM.validate_payload(derived_rmsnorm_gate)
        GATE_VALUE.validate_payload(current_gate_value)
    except Exception as err:
        raise AttentionDerivedD128ProjectionBoundaryError(str(err)) from err
    rmsnorm_payload = _dict(derived_rmsnorm_gate.get("rmsnorm_public_row_payload"), "derived RMSNorm payload")
    validate_rmsnorm_source(rmsnorm_payload)
    bridge_payload = build_bridge_payload(rmsnorm_payload)
    gate_value_payload = build_gate_value_projection_payload(bridge_payload)
    current_projection_input = [_int(value, f"current projection input {index}") for index, value in enumerate(current_gate_value["projection_input_q8"])]
    current_gate = [_int(value, f"current gate output {index}") for index, value in enumerate(current_gate_value["gate_projection_q8"])]
    current_value = [_int(value, f"current value output {index}") for index, value in enumerate(current_gate_value["value_projection_q8"])]
    comparison = {
        "current_projection_input_commitment": current_gate_value["source_projection_input_row_commitment"],
        "current_gate_value_projection_output_commitment": current_gate_value["gate_value_projection_output_commitment"],
        "current_projection_input_mismatch_count": sequence_mismatch_count(
            gate_value_payload["projection_input_q8"], current_projection_input, "projection input"
        ),
        "current_gate_projection_mismatch_count": sequence_mismatch_count(
            gate_value_payload["gate_projection_q8"], current_gate, "gate projection"
        ),
        "current_value_projection_mismatch_count": sequence_mismatch_count(
            gate_value_payload["value_projection_q8"], current_value, "value projection"
        ),
        "matches_existing_d128_gate_value_projection": False,
    }
    return {
        "source_artifacts": [
            source_artifact("attention_derived_d128_rmsnorm_public_row_gate", DERIVED_RMSNORM_JSON, derived_rmsnorm_gate),
            {
                "id": "current_d128_gate_value_projection_input",
                "path": CURRENT_GATE_VALUE_JSON.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(current_raw).hexdigest(),
                "payload_sha256": hashlib.sha256(canonical_json_bytes(current_gate_value)).hexdigest(),
            },
            source_artifact("d128_layerwise_comparator_target", TARGET_JSON, BRIDGE.load_target(TARGET_JSON)),
            source_artifact("d128_rmsnorm_to_projection_bridge_generator", BRIDGE_PATH),
            source_artifact("d128_gate_value_projection_generator", GATE_VALUE_PATH),
            source_artifact("attention_derived_projection_boundary_gate", THIS_GATE_PATH),
        ],
        "source_summary": {
            "source_attention_outputs_commitment": derived_rmsnorm_gate["summary"]["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": derived_rmsnorm_gate["summary"]["input_activation_commitment"],
            "derived_rmsnorm_statement_commitment": rmsnorm_payload["statement_commitment"],
            "derived_rmsnorm_output_row_commitment": rmsnorm_payload["rmsnorm_output_row_commitment"],
        },
        "rmsnorm_public_row_payload": rmsnorm_payload,
        "bridge_payload": bridge_payload,
        "gate_value_projection_payload": gate_value_payload,
        "comparison_summary": comparison,
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    bridge_payload = context["bridge_payload"]
    gate_value_payload = context["gate_value_projection_payload"]
    source_summary = context["source_summary"]
    comparison = context["comparison_summary"]
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "source_summary": copy.deepcopy(source_summary),
        "bridge_payload": copy.deepcopy(bridge_payload),
        "gate_value_projection_payload": copy.deepcopy(gate_value_payload),
        "comparison_summary": copy.deepcopy(comparison),
        "summary": {
            "go_result": (
                "GO for attention-derived d128 RMSNorm output feeding a projection boundary and "
                "deterministic d128 gate/value projection input"
            ),
            "no_go_result": (
                "NO-GO for claiming the existing d128 block receipt consumed this path or for claiming a full layer proof"
            ),
            "source_attention_outputs_commitment": source_summary["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": source_summary["derived_input_activation_commitment"],
            "derived_rmsnorm_statement_commitment": source_summary["derived_rmsnorm_statement_commitment"],
            "derived_rmsnorm_output_row_commitment": source_summary["derived_rmsnorm_output_row_commitment"],
            "derived_projection_input_row_commitment": bridge_payload["projection_input_row_commitment"],
            "derived_bridge_statement_commitment": bridge_payload["statement_commitment"],
            "derived_gate_value_statement_commitment": gate_value_payload["statement_commitment"],
            "derived_gate_value_projection_output_commitment": gate_value_payload[
                "gate_value_projection_output_commitment"
            ],
            "gate_value_mul_rows": gate_value_payload["row_count"],
            "gate_projection_mul_rows": gate_value_payload["gate_projection_mul_rows"],
            "value_projection_mul_rows": gate_value_payload["value_projection_mul_rows"],
            "matches_existing_d128_gate_value_projection": False,
            "current_projection_input_mismatch_count": comparison["current_projection_input_mismatch_count"],
            "current_gate_projection_mismatch_count": comparison["current_gate_projection_mismatch_count"],
            "current_value_projection_mismatch_count": comparison["current_value_projection_mismatch_count"],
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_core_payload(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    if set(payload) not in (CORE_KEYS, FINAL_KEYS):
        raise AttentionDerivedD128ProjectionBoundaryError("payload key set drift")
    if payload.get("schema") != SCHEMA:
        raise AttentionDerivedD128ProjectionBoundaryError("schema drift")
    if payload.get("decision") != DECISION:
        raise AttentionDerivedD128ProjectionBoundaryError("decision drift")
    if payload.get("result") != RESULT:
        raise AttentionDerivedD128ProjectionBoundaryError("result drift")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        raise AttentionDerivedD128ProjectionBoundaryError("claim boundary drift")
    if payload.get("non_claims") != NON_CLAIMS:
        raise AttentionDerivedD128ProjectionBoundaryError("non-claims drift")
    if payload.get("validation_commands") != VALIDATION_COMMANDS:
        raise AttentionDerivedD128ProjectionBoundaryError("validation commands drift")
    context = build_context() if context is None else context
    expected_core = build_core_payload(context)
    comparable = {key: value for key, value in payload.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected = {key: value for key, value in expected_core.items() if key != "payload_commitment"}
    if comparable != expected:
        raise AttentionDerivedD128ProjectionBoundaryError("projection boundary payload drift")
    bridge_payload = _dict(payload.get("bridge_payload"), "bridge payload")
    gate_value_payload = _dict(payload.get("gate_value_projection_payload"), "gate/value payload")
    rmsnorm_payload = _dict(context.get("rmsnorm_public_row_payload"), "context RMSNorm payload")
    validate_bridge_payload(bridge_payload, rmsnorm_payload=rmsnorm_payload)
    validate_gate_value_projection_payload(gate_value_payload, bridge_payload=bridge_payload)
    summary = _dict(payload.get("summary"), "summary")
    comparison = _dict(payload.get("comparison_summary"), "comparison summary")
    if bridge_payload["projection_input_row_commitment"] != gate_value_payload["source_projection_input_row_commitment"]:
        raise AttentionDerivedD128ProjectionBoundaryError("gate/value input does not consume bridge output")
    if summary.get("matches_existing_d128_gate_value_projection") is not False:
        raise AttentionDerivedD128ProjectionBoundaryError("existing block consumption overclaim")
    if comparison.get("matches_existing_d128_gate_value_projection") is not False:
        raise AttentionDerivedD128ProjectionBoundaryError("comparison overclaim")
    if payload.get("payload_commitment") != payload_commitment(payload):
        raise AttentionDerivedD128ProjectionBoundaryError("payload commitment drift")


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    context = build_context() if context is None else context
    validate_core_payload(data, context=context)
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ProjectionBoundaryError("mutation case count drift")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ProjectionBoundaryError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise AttentionDerivedD128ProjectionBoundaryError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise AttentionDerivedD128ProjectionBoundaryError("not all mutations rejected")
        expected_cases = run_mutation_cases(build_core_payload(context), context)
        expected_outcomes = [(case["name"], case["accepted"], case["rejected"]) for case in expected_cases]
        outcomes = []
        for index, (expected_name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise AttentionDerivedD128ProjectionBoundaryError("mutation case field drift")
            if case.get("name") != expected_name:
                raise AttentionDerivedD128ProjectionBoundaryError("mutation case order drift")
            if _bool(case.get("accepted"), "mutation accepted") is not False:
                raise AttentionDerivedD128ProjectionBoundaryError("mutation accepted")
            if _bool(case.get("rejected"), "mutation rejected") is not True:
                raise AttentionDerivedD128ProjectionBoundaryError("mutation not rejected")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise AttentionDerivedD128ProjectionBoundaryError("mutation error field drift")
            outcomes.append((case["name"], case["accepted"], case["rejected"]))
        if outcomes != expected_outcomes:
            raise AttentionDerivedD128ProjectionBoundaryError("mutation outcome drift")


MutationFn = Callable[[dict[str, Any]], None]


def _set_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    ("decision_overclaim", lambda p: p.__setitem__("decision", "GO_FULL_TRANSFORMER_BLOCK"), True),
    ("result_overclaim", lambda p: p.__setitem__("result", "GO_FULL_LAYER_PROOF"), True),
    ("claim_boundary_overclaim", lambda p: p.__setitem__("claim_boundary", "FULL_RECURSIVE_LAYER_PROOF"), True),
    (
        "bridge_source_output_commitment_drift",
        lambda p: p["bridge_payload"].__setitem__("source_rmsnorm_output_row_commitment", "blake2b-256:" + "22" * 32),
        True,
    ),
    (
        "bridge_projection_value_drift",
        lambda p: p["bridge_payload"]["rows"][0].__setitem__("projection_input_q8", 99),
        True,
    ),
    (
        "gate_value_source_projection_commitment_drift",
        lambda p: p["gate_value_projection_payload"].__setitem__("source_projection_input_row_commitment", "blake2b-256:" + "33" * 32),
        True,
    ),
    (
        "gate_projection_output_drift",
        lambda p: p["gate_value_projection_payload"]["gate_projection_q8"].__setitem__(0, 12345),
        True,
    ),
    (
        "gate_value_statement_commitment_drift",
        lambda p: p["gate_value_projection_payload"].__setitem__("statement_commitment", "blake2b-256:" + "44" * 32),
        True,
    ),
    (
        "current_block_consumption_overclaim",
        lambda p: p["summary"].__setitem__("matches_existing_d128_gate_value_projection", True),
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
        except AttentionDerivedD128ProjectionBoundaryError as err:
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
    if set(payload) != FINAL_KEYS:
        raise AttentionDerivedD128ProjectionBoundaryError("to_tsv requires finalized payload")
    summary = _dict(payload.get("summary"), "summary")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": payload["decision"],
            "result": payload["result"],
            "source_attention_outputs_commitment": summary["source_attention_outputs_commitment"],
            "derived_input_activation_commitment": summary["derived_input_activation_commitment"],
            "derived_rmsnorm_output_row_commitment": summary["derived_rmsnorm_output_row_commitment"],
            "derived_projection_input_row_commitment": summary["derived_projection_input_row_commitment"],
            "derived_bridge_statement_commitment": summary["derived_bridge_statement_commitment"],
            "derived_gate_value_projection_output_commitment": summary[
                "derived_gate_value_projection_output_commitment"
            ],
            "gate_value_mul_rows": summary["gate_value_mul_rows"],
            "current_projection_input_mismatch_count": summary["current_projection_input_mismatch_count"],
            "current_gate_projection_mismatch_count": summary["current_gate_projection_mismatch_count"],
            "current_value_projection_mismatch_count": summary["current_value_projection_mismatch_count"],
            "mutations_rejected": payload["case_count"],
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    try:
        return VALUE_GATE.require_output_path(path, suffix)
    except Exception as err:
        raise AttentionDerivedD128ProjectionBoundaryError(str(err)) from err


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
        raise AttentionDerivedD128ProjectionBoundaryError(str(err)) from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build_gate_result()
        write_outputs(payload, args.write_json, args.write_tsv)
    except AttentionDerivedD128ProjectionBoundaryError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    if args.json:
        print(pretty_json(payload))
    else:
        print(
            json.dumps(
                {
                    "decision": payload["decision"],
                    "result": payload["result"],
                    "derived_projection_input_row_commitment": payload["summary"][
                        "derived_projection_input_row_commitment"
                    ],
                    "derived_gate_value_projection_output_commitment": payload["summary"][
                        "derived_gate_value_projection_output_commitment"
                    ],
                    "gate_value_mul_rows": payload["summary"]["gate_value_mul_rows"],
                    "mutations_rejected": payload["case_count"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
