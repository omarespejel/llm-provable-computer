#!/usr/bin/env python3
"""Compose checked d128 proof-slice evidence into one statement-bound receipt.

This gate verifies that the six native d128 slice artifacts form one ordered
commitment chain and exposes one d128 block receipt commitment. It intentionally
does not claim recursive aggregation, a single compressed proof, or verifier-time
metrics for the whole block.
"""

from __future__ import annotations

import argparse
import copy
import csv
import dataclasses
import hashlib
import importlib.util
import json
import os
import pathlib
import stat as stat_module
import sys
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-block-receipt-composition-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-block-receipt-composition-gate-2026-05.tsv"

RMSNORM_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
BRIDGE_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_to_projection_bridge_input.py"
GATE_VALUE_PATH = ROOT / "scripts" / "zkai_d128_gate_value_projection_proof_input.py"
ACTIVATION_SWIGLU_PATH = ROOT / "scripts" / "zkai_d128_activation_swiglu_proof_input.py"
DOWN_PROJECTION_PATH = ROOT / "scripts" / "zkai_d128_down_projection_proof_input.py"
RESIDUAL_ADD_PATH = ROOT / "scripts" / "zkai_d128_residual_add_proof_input.py"

SCHEMA = "zkai-d128-block-receipt-composition-gate-v1"
DECISION = "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE"
RECEIPT_VERSION = "zkai-d128-block-receipt-v1"
STATEMENT_KIND = "d128-rmsnorm-swiglu-residual-block"
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
MODEL_ID = "urn:zkai:ptvm:rmsnorm-swiglu-residual-d128-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
VERIFIER_DOMAIN = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1"
WIDTH = 128
FF_DIM = 512
SCALE_Q8 = 256
ACTIVATION_CLAMP_Q8 = 1024
MAX_SOURCE_JSON_BYTES = 16 * 1024 * 1024

SLICE_CHAIN_DOMAIN = "ptvm:zkai:d128-block:slice-chain:v1"
EVIDENCE_MANIFEST_DOMAIN = "ptvm:zkai:d128-block:evidence-manifest:v1"
BLOCK_STATEMENT_DOMAIN = "ptvm:zkai:d128-block:statement:v1"
BLOCK_RECEIPT_DOMAIN = "ptvm:zkai:d128-block:receipt:v1"

NON_CLAIMS = [
    "not recursive aggregation of the six slice proofs",
    "not one compressed verifier object",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not verifier-time benchmark evidence",
    "not proof-size benchmark evidence for a full block",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_block_receipt_composition_gate.py --write-json docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_block_receipt_composition_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate-fast",
    "just gate",
]

TSV_COLUMNS = (
    "mutation",
    "surface",
    "baseline_accepted",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
)

EXPECTED_COMMITMENT_KEYS: dict[str, tuple[set[str], set[str]]] = {
    "rmsnorm_public_rows": (
        {"input_activation_commitment"},
        {"rmsnorm_output_row_commitment"},
    ),
    "rmsnorm_projection_bridge": (
        {
            "source_rmsnorm_statement_commitment",
            "source_rmsnorm_public_instance_commitment",
            "rmsnorm_output_row_commitment",
        },
        {"projection_input_row_commitment"},
    ),
    "gate_value_projection": (
        {
            "source_bridge_statement_commitment",
            "source_bridge_public_instance_commitment",
            "projection_input_row_commitment",
        },
        {
            "gate_projection_output_commitment",
            "value_projection_output_commitment",
            "gate_value_projection_output_commitment",
        },
    ),
    "activation_swiglu": (
        {
            "source_gate_value_projection_statement_commitment",
            "source_gate_value_projection_public_instance_commitment",
            "gate_projection_output_commitment",
            "value_projection_output_commitment",
            "gate_value_projection_output_commitment",
        },
        {"hidden_activation_commitment"},
    ),
    "down_projection": (
        {
            "source_activation_swiglu_statement_commitment",
            "source_activation_swiglu_public_instance_commitment",
            "hidden_activation_commitment",
        },
        {"residual_delta_commitment"},
    ),
    "residual_add": (
        {
            "source_rmsnorm_statement_commitment",
            "source_down_projection_statement_commitment",
            "source_down_projection_public_instance_commitment",
            "input_activation_commitment",
            "residual_delta_commitment",
        },
        {"output_activation_commitment"},
    ),
}


class D128BlockReceiptError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class SliceSpec:
    slice_id: str
    evidence_path: pathlib.Path
    schema: str
    decision: str
    proof_version: str
    validator: Callable[[Any], None]


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128BlockReceiptError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


RMSNORM = _load_module(RMSNORM_PATH, "zkai_d128_rmsnorm_for_block_receipt")
BRIDGE = _load_module(BRIDGE_PATH, "zkai_d128_bridge_for_block_receipt")
GATE_VALUE = _load_module(GATE_VALUE_PATH, "zkai_d128_gate_value_for_block_receipt")
ACTIVATION_SWIGLU = _load_module(ACTIVATION_SWIGLU_PATH, "zkai_d128_activation_for_block_receipt")
DOWN_PROJECTION = _load_module(DOWN_PROJECTION_PATH, "zkai_d128_down_for_block_receipt")
RESIDUAL_ADD = _load_module(RESIDUAL_ADD_PATH, "zkai_d128_residual_for_block_receipt")

INPUT_ACTIVATION_COMMITMENT = RESIDUAL_ADD.INPUT_ACTIVATION_COMMITMENT
OUTPUT_ACTIVATION_COMMITMENT = RESIDUAL_ADD.OUTPUT_ACTIVATION_COMMITMENT


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_hex_json(value: Any) -> str:
    return sha256_hex_bytes(canonical_json_bytes(value))


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return f"blake2b-256:{digest.hexdigest()}"


def _assert_repo_source_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128BlockReceiptError(f"source evidence must not be a symlink: {path}")
    resolved = path.resolve()
    root = ROOT.resolve()
    if not resolved.is_file():
        raise D128BlockReceiptError(f"source evidence is not a regular file: {path}")
    if resolved != root and root not in resolved.parents:
        raise D128BlockReceiptError(f"source evidence path escapes repository: {path}")
    return resolved


def _open_repo_regular_file(path: pathlib.Path | str) -> tuple[int, pathlib.Path]:
    candidate = pathlib.Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        if candidate.is_symlink():
            raise D128BlockReceiptError(f"source evidence must not be a symlink: {path}")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as err:
            raise D128BlockReceiptError(f"source evidence path escapes repository: {path}") from err
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128BlockReceiptError(f"source evidence is not a regular file: {path}")
        fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128BlockReceiptError(f"source evidence is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128BlockReceiptError(f"source evidence changed while reading: {path}")
            opened_fd = fd
            fd = None
            return opened_fd, resolved
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise D128BlockReceiptError(f"failed to read source evidence {path}: {err}") from err


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    fd, _resolved = _open_repo_regular_file(path)
    with os.fdopen(fd, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D128BlockReceiptError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D128BlockReceiptError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D128BlockReceiptError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D128BlockReceiptError(f"{field} must be an integer")
    return value


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D128BlockReceiptError(f"{field} mismatch")


def expect_key_set(value: dict[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise D128BlockReceiptError(f"{field} key set mismatch: missing={missing} extra={extra}")


def wrap_validator(name: str, validator: Callable[[Any], None]) -> Callable[[Any], None]:
    def _wrapped(payload: Any) -> None:
        try:
            validator(payload)
        except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
            raise D128BlockReceiptError(f"{name} validation failed: {err}") from err

    return _wrapped


SLICE_SPECS = [
    SliceSpec(
        "rmsnorm_public_rows",
        EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json",
        RMSNORM.SCHEMA,
        RMSNORM.DECISION,
        "stwo-d128-rmsnorm-public-row-air-proof-v3",
        wrap_validator("RMSNorm public rows", RMSNORM.validate_payload),
    ),
    SliceSpec(
        "rmsnorm_projection_bridge",
        EVIDENCE_DIR / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json",
        BRIDGE.SCHEMA,
        BRIDGE.DECISION,
        "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1",
        wrap_validator("RMSNorm projection bridge", BRIDGE.validate_payload),
    ),
    SliceSpec(
        "gate_value_projection",
        EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.json",
        GATE_VALUE.SCHEMA,
        GATE_VALUE.DECISION,
        "stwo-d128-gate-value-projection-air-proof-v1",
        wrap_validator("gate/value projection", GATE_VALUE.validate_payload),
    ),
    SliceSpec(
        "activation_swiglu",
        EVIDENCE_DIR / "zkai-d128-activation-swiglu-proof-2026-05.json",
        ACTIVATION_SWIGLU.SCHEMA,
        ACTIVATION_SWIGLU.DECISION,
        "stwo-d128-activation-swiglu-air-proof-v1",
        wrap_validator("activation/SwiGLU", ACTIVATION_SWIGLU.validate_payload),
    ),
    SliceSpec(
        "down_projection",
        EVIDENCE_DIR / "zkai-d128-down-projection-proof-2026-05.json",
        DOWN_PROJECTION.SCHEMA,
        DOWN_PROJECTION.DECISION,
        "stwo-d128-down-projection-air-proof-v1",
        wrap_validator("down projection", DOWN_PROJECTION.validate_payload),
    ),
    SliceSpec(
        "residual_add",
        EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.json",
        RESIDUAL_ADD.SCHEMA,
        RESIDUAL_ADD.DECISION,
        "stwo-d128-residual-add-air-proof-v1",
        wrap_validator("residual add", RESIDUAL_ADD.validate_payload),
    ),
]


def load_json(path: pathlib.Path) -> dict[str, Any]:
    fd, _resolved = _open_repo_regular_file(path)
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read(MAX_SOURCE_JSON_BYTES + 1)
    if len(raw) > MAX_SOURCE_JSON_BYTES:
        raise D128BlockReceiptError(f"source evidence exceeds max size: {path}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128BlockReceiptError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128BlockReceiptError(f"source evidence must be a JSON object: {path}")
    return payload


def source_payloads() -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for spec in SLICE_SPECS:
        payload = load_json(spec.evidence_path)
        spec.validator(payload)
        payloads[spec.slice_id] = payload
    return payloads


def source_manifest(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    manifest = []
    for index, spec in enumerate(SLICE_SPECS):
        payload = payloads[spec.slice_id]
        manifest.append(
            {
                "index": index,
                "slice_id": spec.slice_id,
                "path": relative_path(spec.evidence_path),
                "file_sha256": file_sha256(spec.evidence_path),
                "payload_sha256": sha256_hex_json(payload),
                "schema": payload["schema"],
                "decision": payload["decision"],
                "proof_backend_version": spec.proof_version,
            }
        )
    return manifest


def _slice_item(
    index: int,
    spec: SliceSpec,
    payload: dict[str, Any],
    source_commitments: dict[str, str],
    target_commitments: dict[str, str],
) -> dict[str, Any]:
    return {
        "index": index,
        "slice_id": spec.slice_id,
        "schema": payload["schema"],
        "decision": payload["decision"],
        "proof_backend_version": spec.proof_version,
        "proof_native_parameter_commitment": payload["proof_native_parameter_commitment"],
        "public_instance_commitment": payload["public_instance_commitment"],
        "statement_commitment": payload["statement_commitment"],
        "source_commitments": source_commitments,
        "target_commitments": target_commitments,
        "row_count": payload["row_count"],
    }


def slice_chain(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rmsnorm = payloads["rmsnorm_public_rows"]
    bridge = payloads["rmsnorm_projection_bridge"]
    gate = payloads["gate_value_projection"]
    activation = payloads["activation_swiglu"]
    down = payloads["down_projection"]
    residual = payloads["residual_add"]
    specs = {spec.slice_id: spec for spec in SLICE_SPECS}
    return [
        _slice_item(
            0,
            specs["rmsnorm_public_rows"],
            rmsnorm,
            {"input_activation_commitment": rmsnorm["input_activation_commitment"]},
            {"rmsnorm_output_row_commitment": rmsnorm["rmsnorm_output_row_commitment"]},
        ),
        _slice_item(
            1,
            specs["rmsnorm_projection_bridge"],
            bridge,
            {
                "source_rmsnorm_statement_commitment": bridge["source_rmsnorm_statement_commitment"],
                "source_rmsnorm_public_instance_commitment": bridge["source_rmsnorm_public_instance_commitment"],
                "rmsnorm_output_row_commitment": bridge["source_rmsnorm_output_row_commitment"],
            },
            {"projection_input_row_commitment": bridge["projection_input_row_commitment"]},
        ),
        _slice_item(
            2,
            specs["gate_value_projection"],
            gate,
            {
                "source_bridge_statement_commitment": GATE_VALUE.SOURCE_BRIDGE_STATEMENT_COMMITMENT,
                "source_bridge_public_instance_commitment": GATE_VALUE.SOURCE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
                "projection_input_row_commitment": gate["source_projection_input_row_commitment"],
            },
            {
                "gate_projection_output_commitment": gate["gate_projection_output_commitment"],
                "value_projection_output_commitment": gate["value_projection_output_commitment"],
                "gate_value_projection_output_commitment": gate["gate_value_projection_output_commitment"],
            },
        ),
        _slice_item(
            3,
            specs["activation_swiglu"],
            activation,
            {
                "source_gate_value_projection_statement_commitment": activation[
                    "source_gate_value_projection_statement_commitment"
                ],
                "source_gate_value_projection_public_instance_commitment": activation[
                    "source_gate_value_projection_public_instance_commitment"
                ],
                "gate_projection_output_commitment": activation["source_gate_projection_output_commitment"],
                "value_projection_output_commitment": activation["source_value_projection_output_commitment"],
                "gate_value_projection_output_commitment": activation[
                    "source_gate_value_projection_output_commitment"
                ],
            },
            {"hidden_activation_commitment": activation["hidden_activation_commitment"]},
        ),
        _slice_item(
            4,
            specs["down_projection"],
            down,
            {
                "source_activation_swiglu_statement_commitment": down[
                    "source_activation_swiglu_statement_commitment"
                ],
                "source_activation_swiglu_public_instance_commitment": down[
                    "source_activation_swiglu_public_instance_commitment"
                ],
                "hidden_activation_commitment": down["source_hidden_activation_commitment"],
            },
            {"residual_delta_commitment": down["residual_delta_commitment"]},
        ),
        _slice_item(
            5,
            specs["residual_add"],
            residual,
            {
                "source_rmsnorm_statement_commitment": residual["source_rmsnorm_statement_commitment"],
                "source_down_projection_statement_commitment": residual[
                    "source_down_projection_statement_commitment"
                ],
                "source_down_projection_public_instance_commitment": residual[
                    "source_down_projection_public_instance_commitment"
                ],
                "input_activation_commitment": residual["input_activation_commitment"],
                "residual_delta_commitment": residual["residual_delta_commitment"],
            },
            {"output_activation_commitment": residual["output_activation_commitment"]},
        ),
    ]


def model_config() -> dict[str, Any]:
    return {
        "model_id": MODEL_ID,
        "target_id": TARGET_ID,
        "statement_kind": STATEMENT_KIND,
        "width": WIDTH,
        "ff_dim": FF_DIM,
        "scale_q8": SCALE_Q8,
        "activation_clamp_q8": ACTIVATION_CLAMP_Q8,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
    }


def _statement_payload_for_commitment(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    payload["statement_commitment"] = None
    payload["block_receipt_commitment"] = None
    return payload


def _receipt_payload_for_commitment(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    payload["block_receipt_commitment"] = None
    return payload


def refresh_commitments(payload: dict[str, Any]) -> None:
    payload["slice_chain_commitment"] = blake2b_commitment(payload["slice_chain"], SLICE_CHAIN_DOMAIN)
    payload["evidence_manifest_commitment"] = blake2b_commitment(
        payload["source_evidence_manifest"],
        EVIDENCE_MANIFEST_DOMAIN,
    )
    receipt = payload["block_receipt"]
    receipt["slice_chain_commitment"] = payload["slice_chain_commitment"]
    receipt["evidence_manifest_commitment"] = payload["evidence_manifest_commitment"]
    receipt["statement_commitment"] = blake2b_commitment(
        _statement_payload_for_commitment(receipt),
        BLOCK_STATEMENT_DOMAIN,
    )
    receipt["block_receipt_commitment"] = blake2b_commitment(
        _receipt_payload_for_commitment(receipt),
        BLOCK_RECEIPT_DOMAIN,
    )


def build_payload(payloads: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    payloads = payloads or source_payloads()
    manifest = source_manifest(payloads)
    chain = slice_chain(payloads)
    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "statement_kind": STATEMENT_KIND,
        "target_id": TARGET_ID,
        "model_config": model_config(),
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
        "output_activation_commitment": OUTPUT_ACTIVATION_COMMITMENT,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "slice_versions": [
            {"slice_id": spec.slice_id, "proof_backend_version": spec.proof_version, "schema": spec.schema}
            for spec in SLICE_SPECS
        ],
        "slice_chain_commitment": None,
        "evidence_manifest_commitment": None,
        "statement_commitment": None,
        "block_receipt_commitment": None,
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": "GO",
        "block_receipt": receipt,
        "slice_chain": chain,
        "source_evidence_manifest": manifest,
        "slice_chain_commitment": None,
        "evidence_manifest_commitment": None,
        "summary": {
            "slice_count": len(SLICE_SPECS),
            "total_checked_rows": sum(int(item["row_count"]) for item in chain),
            "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
            "output_activation_commitment": OUTPUT_ACTIVATION_COMMITMENT,
            "non_claims": NON_CLAIMS,
            "next_backend_step": "recursive or proof-carrying aggregation of this receipt, if a future verifier proves the slice verifiers inside one object",
        },
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
    }
    refresh_commitments(payload)
    validate_payload(payload, require_mutations=False)
    return payload


def _manifest_by_slice(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = payload.get("source_evidence_manifest")
    if not isinstance(manifest, list):
        raise D128BlockReceiptError("source evidence manifest must be a list")
    by_slice: dict[str, dict[str, Any]] = {}
    expected_ids = [spec.slice_id for spec in SLICE_SPECS]
    actual_ids: list[str] = []
    for expected_index, item in enumerate(manifest):
        if not isinstance(item, dict):
            raise D128BlockReceiptError("source evidence manifest item must be an object")
        if item.get("index") != expected_index:
            raise D128BlockReceiptError("source evidence manifest index mismatch")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D128BlockReceiptError("source evidence manifest slice_id must be a string")
        if slice_id in by_slice:
            raise D128BlockReceiptError("duplicate source evidence manifest slice")
        actual_ids.append(slice_id)
        by_slice[slice_id] = item
    if actual_ids != expected_ids:
        raise D128BlockReceiptError("source evidence manifest order or membership mismatch")
    return by_slice


def _chain_by_slice(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    chain = payload.get("slice_chain")
    if not isinstance(chain, list):
        raise D128BlockReceiptError("slice chain must be a list")
    by_slice: dict[str, dict[str, Any]] = {}
    expected_ids = [spec.slice_id for spec in SLICE_SPECS]
    actual_ids: list[str] = []
    for expected_index, item in enumerate(chain):
        if not isinstance(item, dict):
            raise D128BlockReceiptError("slice chain item must be an object")
        if item.get("index") != expected_index:
            raise D128BlockReceiptError("slice chain index mismatch")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D128BlockReceiptError("slice chain slice_id must be a string")
        if slice_id in by_slice:
            raise D128BlockReceiptError("duplicate slice in slice chain")
        actual_ids.append(slice_id)
        by_slice[slice_id] = item
    if actual_ids != expected_ids:
        raise D128BlockReceiptError("slice chain order or membership mismatch")
    for spec in SLICE_SPECS:
        item = by_slice[spec.slice_id]
        expect_equal(item.get("schema"), spec.schema, f"{spec.slice_id} schema")
        expect_equal(item.get("decision"), spec.decision, f"{spec.slice_id} decision")
        expect_equal(item.get("proof_backend_version"), spec.proof_version, f"{spec.slice_id} proof version")
        for field in ("proof_native_parameter_commitment", "public_instance_commitment", "statement_commitment"):
            require_commitment(item.get(field), f"{spec.slice_id} {field}")
        row_count = require_int(item.get("row_count"), f"{spec.slice_id} row_count")
        if row_count <= 0:
            raise D128BlockReceiptError(f"{spec.slice_id} row_count must be positive")
        if not isinstance(item.get("source_commitments"), dict):
            raise D128BlockReceiptError(f"{spec.slice_id} source commitments must be an object")
        if not isinstance(item.get("target_commitments"), dict):
            raise D128BlockReceiptError(f"{spec.slice_id} target commitments must be an object")
        expected_source_keys, expected_target_keys = EXPECTED_COMMITMENT_KEYS[spec.slice_id]
        if set(item["source_commitments"]) != expected_source_keys:
            raise D128BlockReceiptError(f"{spec.slice_id} source commitment keys mismatch")
        if set(item["target_commitments"]) != expected_target_keys:
            raise D128BlockReceiptError(f"{spec.slice_id} target commitment keys mismatch")
        for field, value in [*item["source_commitments"].items(), *item["target_commitments"].items()]:
            require_commitment(value, f"{spec.slice_id} {field}")
    return by_slice


def _validate_source_hashes(payload: dict[str, Any]) -> None:
    by_slice = _manifest_by_slice(payload)
    for spec in SLICE_SPECS:
        item = by_slice.get(spec.slice_id)
        if item is None:
            raise D128BlockReceiptError("missing source evidence manifest slice")
        expect_equal(item.get("schema"), spec.schema, f"{spec.slice_id} manifest schema")
        expect_equal(item.get("decision"), spec.decision, f"{spec.slice_id} manifest decision")
        expect_equal(item.get("proof_backend_version"), spec.proof_version, f"{spec.slice_id} manifest proof version")
        path_value = item.get("path")
        if not isinstance(path_value, str):
            raise D128BlockReceiptError(f"{spec.slice_id} manifest path must be a string")
        expect_equal(path_value, relative_path(spec.evidence_path), f"{spec.slice_id} manifest canonical path")
        path = (ROOT / path_value).resolve()
        if path != spec.evidence_path.resolve():
            raise D128BlockReceiptError(f"{spec.slice_id} manifest path mismatch")
        source = load_json(path)
        spec.validator(source)
        expect_equal(item.get("file_sha256"), file_sha256(path), f"{spec.slice_id} source file hash")
        expect_equal(item.get("payload_sha256"), sha256_hex_json(source), f"{spec.slice_id} source payload hash")


def _validate_chain_edges(chain: dict[str, dict[str, Any]]) -> None:
    rmsnorm = chain["rmsnorm_public_rows"]
    bridge = chain["rmsnorm_projection_bridge"]
    gate = chain["gate_value_projection"]
    activation = chain["activation_swiglu"]
    down = chain["down_projection"]
    residual = chain["residual_add"]
    expect_equal(
        bridge["source_commitments"]["source_rmsnorm_statement_commitment"],
        rmsnorm["statement_commitment"],
        "RMSNorm-to-bridge statement edge",
    )
    expect_equal(
        bridge["source_commitments"]["source_rmsnorm_public_instance_commitment"],
        rmsnorm["public_instance_commitment"],
        "RMSNorm-to-bridge public-instance edge",
    )
    expect_equal(
        bridge["source_commitments"]["rmsnorm_output_row_commitment"],
        rmsnorm["target_commitments"]["rmsnorm_output_row_commitment"],
        "RMSNorm-to-bridge commitment edge",
    )
    expect_equal(
        gate["source_commitments"]["source_bridge_statement_commitment"],
        bridge["statement_commitment"],
        "bridge-to-projection statement edge",
    )
    expect_equal(
        gate["source_commitments"]["source_bridge_public_instance_commitment"],
        bridge["public_instance_commitment"],
        "bridge-to-projection public-instance edge",
    )
    expect_equal(
        gate["source_commitments"]["projection_input_row_commitment"],
        bridge["target_commitments"]["projection_input_row_commitment"],
        "bridge-to-projection commitment edge",
    )
    expect_equal(
        activation["source_commitments"]["source_gate_value_projection_statement_commitment"],
        gate["statement_commitment"],
        "gate-value-to-activation statement edge",
    )
    expect_equal(
        activation["source_commitments"]["source_gate_value_projection_public_instance_commitment"],
        gate["public_instance_commitment"],
        "gate-value-to-activation public-instance edge",
    )
    expect_equal(
        activation["source_commitments"]["gate_projection_output_commitment"],
        gate["target_commitments"]["gate_projection_output_commitment"],
        "gate-projection-to-activation commitment edge",
    )
    expect_equal(
        activation["source_commitments"]["value_projection_output_commitment"],
        gate["target_commitments"]["value_projection_output_commitment"],
        "value-projection-to-activation commitment edge",
    )
    expect_equal(
        activation["source_commitments"]["gate_value_projection_output_commitment"],
        gate["target_commitments"]["gate_value_projection_output_commitment"],
        "gate-value-to-activation commitment edge",
    )
    expect_equal(
        down["source_commitments"]["source_activation_swiglu_statement_commitment"],
        activation["statement_commitment"],
        "activation-to-down statement edge",
    )
    expect_equal(
        down["source_commitments"]["source_activation_swiglu_public_instance_commitment"],
        activation["public_instance_commitment"],
        "activation-to-down public-instance edge",
    )
    expect_equal(
        down["source_commitments"]["hidden_activation_commitment"],
        activation["target_commitments"]["hidden_activation_commitment"],
        "activation-to-down commitment edge",
    )
    expect_equal(
        residual["source_commitments"]["source_rmsnorm_statement_commitment"],
        rmsnorm["statement_commitment"],
        "RMSNorm-to-residual statement edge",
    )
    expect_equal(
        residual["source_commitments"]["source_down_projection_statement_commitment"],
        down["statement_commitment"],
        "down-to-residual statement edge",
    )
    expect_equal(
        residual["source_commitments"]["source_down_projection_public_instance_commitment"],
        down["public_instance_commitment"],
        "down-to-residual public-instance edge",
    )
    expect_equal(
        residual["source_commitments"]["residual_delta_commitment"],
        down["target_commitments"]["residual_delta_commitment"],
        "down-to-residual commitment edge",
    )
    expect_equal(
        residual["source_commitments"]["input_activation_commitment"],
        rmsnorm["source_commitments"]["input_activation_commitment"],
        "input-activation replay edge",
    )
    expect_equal(
        residual["target_commitments"]["output_activation_commitment"],
        OUTPUT_ACTIVATION_COMMITMENT,
        "final output activation commitment",
    )
    final_output = residual["target_commitments"]["output_activation_commitment"]
    for label, commitment in (
        ("input activation", residual["source_commitments"]["input_activation_commitment"]),
        ("RMSNorm output", rmsnorm["target_commitments"]["rmsnorm_output_row_commitment"]),
        ("projection input", bridge["target_commitments"]["projection_input_row_commitment"]),
        ("gate/value output", gate["target_commitments"]["gate_value_projection_output_commitment"]),
        ("hidden activation", activation["target_commitments"]["hidden_activation_commitment"]),
        ("residual delta", residual["source_commitments"]["residual_delta_commitment"]),
    ):
        if commitment == final_output:
            raise D128BlockReceiptError(f"{label} commitment relabeled as final output")


def _validate_receipt(payload: dict[str, Any]) -> None:
    receipt = payload.get("block_receipt")
    if not isinstance(receipt, dict):
        raise D128BlockReceiptError("block receipt must be an object")
    expect_key_set(
        receipt,
        {
            "receipt_version",
            "statement_kind",
            "target_id",
            "model_config",
            "input_activation_commitment",
            "output_activation_commitment",
            "required_backend_version",
            "verifier_domain",
            "slice_versions",
            "slice_chain_commitment",
            "evidence_manifest_commitment",
            "statement_commitment",
            "block_receipt_commitment",
        },
        "block receipt",
    )
    expected = {
        "receipt_version": RECEIPT_VERSION,
        "statement_kind": STATEMENT_KIND,
        "target_id": TARGET_ID,
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
        "output_activation_commitment": OUTPUT_ACTIVATION_COMMITMENT,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "slice_chain_commitment": payload.get("slice_chain_commitment"),
        "evidence_manifest_commitment": payload.get("evidence_manifest_commitment"),
    }
    for field, value in expected.items():
        expect_equal(receipt.get(field), value, f"block receipt {field}")
    expect_equal(receipt.get("model_config"), model_config(), "block receipt model_config")
    slice_versions = receipt.get("slice_versions")
    if not isinstance(slice_versions, list) or len(slice_versions) != len(SLICE_SPECS):
        raise D128BlockReceiptError("block receipt slice_versions mismatch")
    for version, spec in zip(slice_versions, SLICE_SPECS, strict=True):
        if not isinstance(version, dict):
            raise D128BlockReceiptError("block receipt slice version must be an object")
        expect_key_set(version, {"slice_id", "proof_backend_version", "schema"}, "block receipt slice version")
        expect_equal(version.get("slice_id"), spec.slice_id, "block receipt slice version id")
        expect_equal(version.get("schema"), spec.schema, "block receipt slice version schema")
        expect_equal(version.get("proof_backend_version"), spec.proof_version, "block receipt slice proof version")
    expect_equal(
        receipt.get("statement_commitment"),
        blake2b_commitment(_statement_payload_for_commitment(receipt), BLOCK_STATEMENT_DOMAIN),
        "block receipt statement commitment",
    )
    expect_equal(
        receipt.get("block_receipt_commitment"),
        blake2b_commitment(_receipt_payload_for_commitment(receipt), BLOCK_RECEIPT_DOMAIN),
        "block receipt commitment",
    )


def validate_payload(payload: Any, *, require_mutations: bool = True) -> None:
    if not isinstance(payload, dict):
        raise D128BlockReceiptError("block receipt composition payload must be an object")
    expected_top_level = {
        "schema",
        "decision",
        "result",
        "block_receipt",
        "slice_chain",
        "source_evidence_manifest",
        "slice_chain_commitment",
        "evidence_manifest_commitment",
        "summary",
        "non_claims",
        "validation_commands",
    }
    if require_mutations:
        expected_top_level |= {"case_count", "all_mutations_rejected", "cases"}
    expect_key_set(payload, expected_top_level, "block receipt composition payload")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), "GO", "result")
    chain = _chain_by_slice(payload)
    _validate_chain_edges(chain)
    expect_equal(
        payload.get("slice_chain_commitment"),
        blake2b_commitment(payload["slice_chain"], SLICE_CHAIN_DOMAIN),
        "slice chain commitment",
    )
    expect_equal(
        payload.get("evidence_manifest_commitment"),
        blake2b_commitment(payload["source_evidence_manifest"], EVIDENCE_MANIFEST_DOMAIN),
        "evidence manifest commitment",
    )
    _validate_source_hashes(payload)
    _validate_receipt(payload)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise D128BlockReceiptError("summary must be an object")
    expected_summary = {
        "slice_count",
        "total_checked_rows",
        "input_activation_commitment",
        "output_activation_commitment",
        "non_claims",
        "next_backend_step",
    }
    if require_mutations:
        expected_summary |= {"mutation_cases", "mutations_rejected"}
    expect_key_set(summary, expected_summary, "summary")
    expect_equal(summary.get("slice_count"), len(SLICE_SPECS), "summary slice count")
    total_checked_rows = sum(
        require_int(item.get("row_count"), f"{item.get('slice_id', 'unknown')} row_count")
        for item in chain.values()
    )
    expect_equal(summary.get("total_checked_rows"), total_checked_rows, "summary row count")
    expect_equal(summary.get("input_activation_commitment"), INPUT_ACTIVATION_COMMITMENT, "summary input commitment")
    expect_equal(summary.get("output_activation_commitment"), OUTPUT_ACTIVATION_COMMITMENT, "summary output commitment")
    expect_equal(payload.get("non_claims"), NON_CLAIMS, "non_claims")
    expect_equal(summary.get("non_claims"), NON_CLAIMS, "summary non_claims")
    expect_equal(payload.get("validation_commands"), VALIDATION_COMMANDS, "validation commands")
    if require_mutations:
        cases = payload.get("cases")
        if not isinstance(cases, list):
            raise D128BlockReceiptError("mutation cases must be a list")
        expected = expected_mutation_inventory()
        expect_equal(payload.get("case_count"), len(cases), "case count length")
        expect_equal(payload.get("case_count"), len(expected), "case count inventory")
        expect_equal(summary.get("mutation_cases"), len(cases), "summary mutation count")
        rejected_count = 0
        for index, (case, expected_case) in enumerate(zip(cases, expected, strict=True)):
            if not isinstance(case, dict):
                raise D128BlockReceiptError("mutation case must be an object")
            expect_key_set(
                case,
                {
                    "mutation",
                    "surface",
                    "baseline_accepted",
                    "mutated_accepted",
                    "rejected",
                    "rejection_layer",
                    "error",
                },
                f"mutation case {index}",
            )
            expect_equal(case.get("mutation"), expected_case["mutation"], f"mutation case {index} name")
            expect_equal(case.get("surface"), expected_case["surface"], f"mutation case {index} surface")
            expect_equal(case.get("baseline_accepted"), True, f"mutation case {index} baseline")
            if not isinstance(case.get("mutated_accepted"), bool):
                raise D128BlockReceiptError(f"mutation case {index} accepted flag must be boolean")
            if not isinstance(case.get("rejected"), bool):
                raise D128BlockReceiptError(f"mutation case {index} rejected flag must be boolean")
            expect_equal(
                case["mutated_accepted"],
                not case["rejected"],
                f"mutation case {index} accepted/rejected relation",
            )
            if case["rejected"]:
                rejected_count += 1
                expect_equal(
                    case.get("rejection_layer"),
                    expected_case["rejection_layer"],
                    f"mutation case {index} rejection layer",
                )
                if not case.get("error"):
                    raise D128BlockReceiptError(f"mutation case {index} error must be non-empty")
        expect_equal(summary.get("mutations_rejected"), rejected_count, "summary mutations rejected")
        expect_equal(rejected_count, len(cases), "all mutation cases rejected")
        expect_equal(payload.get("all_mutations_rejected"), True, "all mutations rejected")


def classify_error(error: Exception) -> str:
    text = str(error).lower()
    if "source" in text or "manifest" in text or "hash" in text:
        return "source_evidence_manifest"
    if "order" in text or "duplicate" in text or "missing" in text or "membership" in text or "index" in text:
        return "slice_chain_shape"
    if text.startswith("block receipt") or " receipt " in f" {text} ":
        return "block_receipt"
    if "edge" in text or "relabel" in text or "commitment" in text:
        return "commitment_chain"
    return "parser_or_schema"


def _mutated_cases(baseline: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Callable[[dict[str, Any]], None], refresh: bool = True) -> None:
        mutated = copy.deepcopy(baseline)
        mutator(mutated)
        if refresh:
            refresh_commitments(mutated)
        cases.append((name, surface, mutated))

    def swap_bridge_and_projection(payload: dict[str, Any]) -> None:
        payload["slice_chain"][1], payload["slice_chain"][2] = payload["slice_chain"][2], payload["slice_chain"][1]

    add("missing_bridge_slice", "slice_chain_shape", lambda p: p["slice_chain"].pop(1))
    add("reordered_bridge_and_projection", "slice_chain_shape", swap_bridge_and_projection)
    add("duplicated_final_slice_missing_down", "slice_chain_shape", lambda p: p["slice_chain"].__setitem__(4, copy.deepcopy(p["slice_chain"][5])))
    add(
        "stale_projection_input_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][1]["target_commitments"].__setitem__("projection_input_row_commitment", "blake2b-256:" + "10" * 32),
    )
    add(
        "stale_gate_value_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][2]["target_commitments"].__setitem__("gate_value_projection_output_commitment", "blake2b-256:" + "11" * 32),
    )
    add(
        "stale_hidden_activation_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][3]["target_commitments"].__setitem__("hidden_activation_commitment", "blake2b-256:" + "12" * 32),
    )
    add(
        "stale_residual_delta_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][4]["target_commitments"].__setitem__("residual_delta_commitment", "blake2b-256:" + "13" * 32),
    )
    add(
        "stale_rmsnorm_statement_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][1]["source_commitments"].__setitem__("source_rmsnorm_statement_commitment", "blake2b-256:" + "14" * 32),
    )
    add(
        "stale_down_statement_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][5]["source_commitments"].__setitem__("source_down_projection_statement_commitment", "blake2b-256:" + "15" * 32),
    )
    add(
        "residual_delta_relabels_output",
        "commitment_chain",
        lambda p: p["slice_chain"][5]["source_commitments"].__setitem__(
            "residual_delta_commitment",
            p["slice_chain"][5]["target_commitments"]["output_activation_commitment"],
        ),
    )
    add(
        "hidden_activation_relabels_output",
        "commitment_chain",
        lambda p: p["slice_chain"][3]["target_commitments"].__setitem__(
            "hidden_activation_commitment",
            p["slice_chain"][5]["target_commitments"]["output_activation_commitment"],
        ),
    )
    add(
        "backend_version_drift",
        "block_receipt",
        lambda p: p["block_receipt"].__setitem__("required_backend_version", "stwo-rmsnorm-swiglu-residual-d128-v2"),
    )
    add(
        "verifier_domain_drift",
        "block_receipt",
        lambda p: p["block_receipt"].__setitem__("verifier_domain", "ptvm:tampered-verifier-domain:v0"),
    )
    add(
        "slice_version_drift",
        "block_receipt",
        lambda p: p["block_receipt"]["slice_versions"][5].__setitem__(
            "proof_backend_version",
            "stwo-d128-residual-add-air-proof-v2",
        ),
    )
    add(
        "model_config_drift",
        "block_receipt",
        lambda p: p["block_receipt"]["model_config"].__setitem__("ff_dim", 256),
    )
    add(
        "input_commitment_drift",
        "block_receipt",
        lambda p: p["block_receipt"].__setitem__("input_activation_commitment", "blake2b-256:" + "33" * 32),
    )
    add(
        "output_commitment_drift",
        "block_receipt",
        lambda p: p["block_receipt"].__setitem__("output_activation_commitment", "blake2b-256:" + "44" * 32),
    )
    add(
        "non_claims_drift",
        "parser_or_schema",
        lambda p: (
            p.__setitem__("non_claims", []),
            p["summary"].__setitem__("non_claims", []),
        ),
        refresh=False,
    )
    add(
        "source_payload_hash_drift",
        "source_evidence_manifest",
        lambda p: p["source_evidence_manifest"][0].__setitem__("payload_sha256", "66" * 32),
    )
    add(
        "source_file_hash_drift",
        "source_evidence_manifest",
        lambda p: p["source_evidence_manifest"][0].__setitem__("file_sha256", "55" * 32),
    )
    return cases


def expected_mutation_inventory() -> list[dict[str, str]]:
    return [
        {"mutation": mutation, "surface": surface, "rejection_layer": surface}
        for mutation, surface, _mutated in _mutated_cases(build_payload())
    ]


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    validate_payload(baseline, require_mutations=False)
    cases = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            validate_payload(mutated, require_mutations=False)
            accepted = True
            error = ""
            layer = "accepted"
        except D128BlockReceiptError as err:
            accepted = False
            error = str(err)
            layer = classify_error(err)
        cases.append(
            {
                "mutation": mutation,
                "surface": surface,
                "baseline_accepted": True,
                "mutated_accepted": accepted,
                "rejected": not accepted,
                "rejection_layer": layer,
                "error": error,
            }
        )
    return cases


def build_gate_result() -> dict[str, Any]:
    payload = build_payload()
    cases = mutation_cases(payload)
    result = copy.deepcopy(payload)
    result["case_count"] = len(cases)
    result["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    result["cases"] = cases
    result["summary"]["mutation_cases"] = len(cases)
    result["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    validate_payload(result)
    if not result["all_mutations_rejected"]:
        raise D128BlockReceiptError("not all d128 block receipt mutations rejected")
    return result


def to_tsv(payload: dict[str, Any]) -> str:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: case[key] for key in TSV_COLUMNS} for case in payload["cases"])
    return buffer.getvalue()


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    candidate = path if path.is_absolute() else ROOT / path
    if candidate.is_symlink():
        raise D128BlockReceiptError(f"output path must not be a symlink: {path}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128BlockReceiptError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128BlockReceiptError(f"output path must not be a directory: {path}")
    parent = resolved.parent
    if parent.exists() and not parent.is_dir():
        raise D128BlockReceiptError(f"output parent is not a directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _fsync_parent_directories(paths: list[pathlib.Path]) -> None:
    seen: set[pathlib.Path] = set()
    for path in paths:
        parent = path.resolve().parent
        if parent in seen:
            continue
        seen.add(parent)
        flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
        try:
            fd = os.open(parent, flags)
        except OSError:
            continue
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _atomic_write_text(path: pathlib.Path, text: str) -> pathlib.Path:
    resolved = _assert_repo_output_path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=resolved.parent, delete=False) as handle:
        tmp = pathlib.Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(tmp, resolved)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return resolved


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    written: list[pathlib.Path] = []
    if json_path is not None:
        written.append(_atomic_write_text(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"))
    if tsv_path is not None:
        written.append(_atomic_write_text(tsv_path, to_tsv(payload)))
    _fsync_parent_directories(written)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
