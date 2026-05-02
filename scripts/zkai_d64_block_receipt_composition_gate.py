#!/usr/bin/env python3
"""Compose checked d64 proof-slice evidence into one statement-bound block receipt.

This is a composition gate over checked evidence handles. It verifies that the
six native d64 slice artifacts form one ordered commitment chain and exposes one
block receipt commitment. It intentionally does not claim recursive proof
compression or private parameter-opening proof.
"""

from __future__ import annotations

import argparse
import copy
import csv
import dataclasses
import hashlib
import importlib.util
import json
import pathlib
import sys
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
JSON_OUT = EVIDENCE_DIR / "zkai-d64-block-receipt-composition-gate-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d64-block-receipt-composition-gate-2026-05.tsv"

FIXTURE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_swiglu_statement_fixture.py"
BRIDGE_PATH = ROOT / "scripts" / "zkai_d64_rmsnorm_to_projection_bridge_input.py"
GATE_VALUE_PATH = ROOT / "scripts" / "zkai_d64_gate_value_projection_proof_input.py"
ACTIVATION_SWIGLU_PATH = ROOT / "scripts" / "zkai_d64_activation_swiglu_proof_input.py"
DOWN_PROJECTION_PATH = ROOT / "scripts" / "zkai_d64_down_projection_proof_input.py"
RESIDUAL_ADD_PATH = ROOT / "scripts" / "zkai_d64_residual_add_proof_input.py"

SCHEMA = "zkai-d64-block-receipt-composition-gate-v1"
DECISION = "GO_D64_BLOCK_RECEIPT_COMPOSITION_GATE"
RECEIPT_VERSION = "zkai-d64-block-receipt-v1"
STATEMENT_KIND = "d64-rmsnorm-swiglu-residual-block"
TARGET_ID = "rmsnorm-swiglu-residual-d64-v2"
MODEL_ID = "urn:zkai:ptvm:rmsnorm-swiglu-residual-d64-v1"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d64-v2"
VERIFIER_DOMAIN = "ptvm:zkai:d64-rmsnorm-swiglu-statement-target:v2"
WIDTH = 64
FF_DIM = 256
SCALE_Q8 = 256
ACTIVATION_CLAMP_Q8 = 1024
PROOF_NATIVE_PARAMETER_COMMITMENT = "blake2b-256:861784bd57c039f7fd661810eac42f2aa1893a315ba8e14b441c32717e65efbc"
PUBLIC_INSTANCE_COMMITMENT = "blake2b-256:ee01ed070eddd5b85990461776834fd827ecd8d37d295fdfa0b2d518b6b6366d"
STATEMENT_COMMITMENT = "blake2b-256:9689c4c4e46a62d3f4156c818c1cc146e7312ff91a44f521bd897e806b2f3b38"
INPUT_ACTIVATION_COMMITMENT = "blake2b-256:4f765c71601320b3ee9341056299e79a004fa94aaa2edcb5c161cb7366b051fc"
OUTPUT_ACTIVATION_COMMITMENT = "blake2b-256:c63929ab0be63f116d3ad74613392eaa43e3db6c6a8b4f53be32ac57f15e1c5f"

MAX_SOURCE_JSON_BYTES = 4 * 1024 * 1024
M31_MODULUS = (1 << 31) - 1
D64_Q8_SCALE = 256
RMSNORM_OUTPUT_ROW_DOMAIN = "ptvm:zkai:d64-rmsnorm-output-row:v1"
INPUT_ACTIVATION_DOMAIN = "ptvm:zkai:d64-input-activation:v1"

NON_CLAIMS = [
    "not recursive aggregation of the six slice proofs",
    "not one compressed verifier object",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not verifier-time benchmark evidence",
    "not onchain deployment evidence",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d64_block_receipt_composition_gate.py --write-json docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d64_block_receipt_composition_gate",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
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
        {"rmsnorm_output_row_commitment"},
        {"projection_input_row_commitment"},
    ),
    "gate_value_projection": (
        {"projection_input_row_commitment"},
        {
            "gate_projection_output_commitment",
            "value_projection_output_commitment",
            "gate_value_projection_output_commitment",
        },
    ),
    "activation_swiglu": (
        {
            "gate_projection_output_commitment",
            "value_projection_output_commitment",
            "gate_value_projection_output_commitment",
        },
        {"hidden_activation_commitment"},
    ),
    "down_projection": (
        {"hidden_activation_commitment"},
        {"residual_delta_commitment"},
    ),
    "residual_add": (
        {"input_activation_commitment", "residual_delta_commitment"},
        {"output_activation_commitment"},
    ),
}


class D64BlockReceiptError(ValueError):
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
        raise D64BlockReceiptError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_module(FIXTURE_PATH, "zkai_d64_fixture_for_block_receipt")
BRIDGE = _load_module(BRIDGE_PATH, "zkai_d64_bridge_for_block_receipt")
GATE_VALUE = _load_module(GATE_VALUE_PATH, "zkai_d64_gate_value_for_block_receipt")
ACTIVATION_SWIGLU = _load_module(ACTIVATION_SWIGLU_PATH, "zkai_d64_activation_for_block_receipt")
DOWN_PROJECTION = _load_module(DOWN_PROJECTION_PATH, "zkai_d64_down_for_block_receipt")
RESIDUAL_ADD = _load_module(RESIDUAL_ADD_PATH, "zkai_d64_residual_for_block_receipt")


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


def blake2b_hex_bytes(data: bytes, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(data)
    return digest.hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise D64BlockReceiptError(f"{field} must be a commitment string")
    if not value.startswith("blake2b-256:"):
        raise D64BlockReceiptError(f"{field} must be blake2b-256 domain-separated")
    raw = value.removeprefix("blake2b-256:")
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise D64BlockReceiptError(f"{field} must be a 32-byte lowercase hex digest")
    return value


def require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise D64BlockReceiptError(f"{field} must be an integer")
    if value <= -M31_MODULUS or value >= M31_MODULUS:
        raise D64BlockReceiptError(f"{field} outside signed M31 bounds")
    return value


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D64BlockReceiptError(f"{field} mismatch")


def integer_sqrt(value: int) -> int:
    if value <= 0:
        return 0
    n = value
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x


def sequence_commitment(values: list[int], domain: str, shape: list[int]) -> str:
    return blake2b_commitment(
        {
            "encoding": "signed_integer_sequence_v1",
            "shape": shape,
            "values_sha256": sha256_hex_json(values),
        },
        domain,
    )


def parse_blake2b_hex(value: str, field: str) -> bytes:
    commitment = require_commitment(value, field)
    return bytes.fromhex(commitment.removeprefix("blake2b-256:"))


def rms_scale_tree_root(scale_values: list[int]) -> str:
    if not scale_values:
        raise D64BlockReceiptError("cannot commit empty RMS scale tree")
    level = [
        blake2b_hex_bytes(
            canonical_json_bytes({"index": index, "kind": "rms_scale", "value_q8": value}),
            "ptvm:zkai:d64:rms-scale-leaf:v1",
        )
        for index, value in enumerate(scale_values)
    ]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level: list[str] = []
        for index in range(0, len(level), 2):
            left = bytes.fromhex(level[index])
            right = bytes.fromhex(level[index + 1])
            next_level.append(blake2b_hex_bytes(left + right, "ptvm:zkai:d64:rms-scale-tree:v1"))
        level = next_level
    return f"blake2b-256:{level[0]}"


def normalization_config_commitment(rms_q8: int, scale_commitment: str) -> str:
    return blake2b_commitment(
        {
            "rms_q8": rms_q8,
            "rms_square_rows": WIDTH,
            "scale_commitment": scale_commitment,
        },
        "ptvm:zkai:d64-rmsnorm-config:v1",
    )


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D64BlockReceiptError(f"source evidence is not a regular file: {path}")
    if ROOT.resolve() not in resolved.parents:
        raise D64BlockReceiptError(f"source evidence path escapes repository: {path}")
    raw = resolved.read_bytes()
    if len(raw) > MAX_SOURCE_JSON_BYTES:
        raise D64BlockReceiptError(f"source evidence exceeds max size: {path}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D64BlockReceiptError(f"failed to load source evidence {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D64BlockReceiptError(f"source evidence must be a JSON object: {path}")
    return payload


def validate_rmsnorm_public_row(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D64BlockReceiptError("RMSNorm public-row evidence must be an object")
    expected = {
        "schema": "zkai-d64-native-rmsnorm-public-row-air-proof-input-v2",
        "decision": "GO_PUBLIC_ROW_INPUT_FOR_D64_RMSNORM_AIR_PROOF",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "width": WIDTH,
        "row_count": WIDTH,
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
    }
    for field, value in expected.items():
        expect_equal(payload.get(field), value, f"rmsnorm {field}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != WIDTH:
        raise D64BlockReceiptError("RMSNorm public-row row vector length mismatch")
    rms_q8 = require_int(payload.get("rms_q8"), "rmsnorm rms_q8")
    if rms_q8 <= 0:
        raise D64BlockReceiptError("RMSNorm rms_q8 must be positive")
    input_values: list[int] = []
    normed_values: list[int] = []
    scale_values: list[int] = []
    sum_squares = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise D64BlockReceiptError("RMSNorm row must be an object")
        expect_equal(row.get("index"), index, "RMSNorm row index")
        input_q8 = require_int(row.get("input_q8"), "RMSNorm input_q8")
        rms_scale_q8 = require_int(row.get("rms_scale_q8"), "RMSNorm rms_scale_q8")
        input_square = require_int(row.get("input_square"), "RMSNorm input_square")
        scaled_floor = require_int(row.get("scaled_floor"), "RMSNorm scaled_floor")
        scale_remainder = require_int(row.get("scale_remainder"), "RMSNorm scale_remainder")
        normed_q8 = require_int(row.get("normed_q8"), "RMSNorm normed_q8")
        norm_remainder = require_int(row.get("norm_remainder"), "RMSNorm norm_remainder")
        expect_equal(require_int(row.get("rms_q8"), "RMSNorm row rms_q8"), rms_q8, "RMSNorm row rms_q8")
        expect_equal(input_square, input_q8 * input_q8, "RMSNorm input square")
        expect_equal(
            input_q8 * rms_scale_q8,
            scaled_floor * D64_Q8_SCALE + scale_remainder,
            "RMSNorm scaled floor relation",
        )
        if not 0 <= scale_remainder < D64_Q8_SCALE:
            raise D64BlockReceiptError("RMSNorm scale remainder is out of q8 range")
        expect_equal(
            scaled_floor * D64_Q8_SCALE,
            normed_q8 * rms_q8 + norm_remainder,
            "RMSNorm normed relation",
        )
        if not 0 <= norm_remainder < rms_q8:
            raise D64BlockReceiptError("RMSNorm norm remainder is out of rms range")
        input_values.append(input_q8)
        normed_values.append(normed_q8)
        scale_values.append(rms_scale_q8)
        sum_squares += input_square
    expect_equal(payload.get("sum_squares"), sum_squares, "RMSNorm sum_squares")
    average_square_floor = sum_squares // WIDTH
    expect_equal(payload.get("average_square_floor"), average_square_floor, "RMSNorm average_square_floor")
    expect_equal(rms_q8, integer_sqrt(average_square_floor), "RMSNorm rms_q8")
    expect_equal(
        sequence_commitment(input_values, INPUT_ACTIVATION_DOMAIN, [WIDTH]),
        INPUT_ACTIVATION_COMMITMENT,
        "RMSNorm input activation commitment",
    )
    expect_equal(
        sequence_commitment(normed_values, RMSNORM_OUTPUT_ROW_DOMAIN, [WIDTH]),
        payload.get("rmsnorm_output_row_commitment"),
        "RMSNorm output row commitment",
    )
    scale_commitment = sequence_commitment(scale_values, "ptvm:zkai:d64-rms-scale:v1", [WIDTH])
    expect_equal(
        normalization_config_commitment(rms_q8, scale_commitment),
        payload.get("normalization_config_commitment"),
        "RMSNorm normalization config commitment",
    )
    expect_equal(rms_scale_tree_root(scale_values), payload.get("rms_scale_tree_root"), "RMS scale tree root")


def wrap_validator(name: str, validator: Callable[[Any], None]) -> Callable[[Any], None]:
    def _wrapped(payload: Any) -> None:
        try:
            validator(payload)
        except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
            raise D64BlockReceiptError(f"{name} validation failed: {err}") from err

    return _wrapped


SLICE_SPECS = [
    SliceSpec(
        "rmsnorm_public_rows",
        EVIDENCE_DIR / "zkai-d64-native-rmsnorm-public-row-proof-2026-05.json",
        "zkai-d64-native-rmsnorm-public-row-air-proof-input-v2",
        "GO_PUBLIC_ROW_INPUT_FOR_D64_RMSNORM_AIR_PROOF",
        "stwo-d64-rmsnorm-public-row-air-proof-v2",
        validate_rmsnorm_public_row,
    ),
    SliceSpec(
        "rmsnorm_projection_bridge",
        EVIDENCE_DIR / "zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json",
        BRIDGE.SCHEMA,
        BRIDGE.DECISION,
        "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1",
        wrap_validator("rmsnorm projection bridge", BRIDGE.validate_payload),
    ),
    SliceSpec(
        "gate_value_projection",
        EVIDENCE_DIR / "zkai-d64-gate-value-projection-proof-2026-05.json",
        GATE_VALUE.SCHEMA,
        GATE_VALUE.DECISION,
        "stwo-d64-gate-value-projection-air-proof-v1",
        wrap_validator("gate/value projection", GATE_VALUE.validate_payload),
    ),
    SliceSpec(
        "activation_swiglu",
        EVIDENCE_DIR / "zkai-d64-activation-swiglu-proof-2026-05.json",
        ACTIVATION_SWIGLU.SCHEMA,
        ACTIVATION_SWIGLU.DECISION,
        "stwo-d64-activation-swiglu-air-proof-v1",
        wrap_validator("activation/SwiGLU", ACTIVATION_SWIGLU.validate_payload),
    ),
    SliceSpec(
        "down_projection",
        EVIDENCE_DIR / "zkai-d64-down-projection-proof-2026-05.json",
        DOWN_PROJECTION.SCHEMA,
        DOWN_PROJECTION.DECISION,
        "stwo-d64-down-projection-air-proof-v1",
        wrap_validator("down projection", DOWN_PROJECTION.validate_payload),
    ),
    SliceSpec(
        "residual_add",
        EVIDENCE_DIR / "zkai-d64-residual-add-proof-2026-05.json",
        RESIDUAL_ADD.SCHEMA,
        RESIDUAL_ADD.DECISION,
        "stwo-d64-residual-add-air-proof-v1",
        wrap_validator("residual add", RESIDUAL_ADD.validate_payload),
    ),
]


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


def slice_chain(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rmsnorm = payloads["rmsnorm_public_rows"]
    bridge = payloads["rmsnorm_projection_bridge"]
    gate = payloads["gate_value_projection"]
    activation = payloads["activation_swiglu"]
    down = payloads["down_projection"]
    residual = payloads["residual_add"]
    return [
        {
            "index": 0,
            "slice_id": "rmsnorm_public_rows",
            "schema": rmsnorm["schema"],
            "decision": rmsnorm["decision"],
            "proof_backend_version": "stwo-d64-rmsnorm-public-row-air-proof-v2",
            "source_commitments": {"input_activation_commitment": rmsnorm["input_activation_commitment"]},
            "target_commitments": {"rmsnorm_output_row_commitment": rmsnorm["rmsnorm_output_row_commitment"]},
            "row_count": rmsnorm["row_count"],
        },
        {
            "index": 1,
            "slice_id": "rmsnorm_projection_bridge",
            "schema": bridge["schema"],
            "decision": bridge["decision"],
            "proof_backend_version": "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1",
            "source_commitments": {"rmsnorm_output_row_commitment": bridge["source_rmsnorm_output_row_commitment"]},
            "target_commitments": {"projection_input_row_commitment": bridge["projection_input_row_commitment"]},
            "row_count": bridge["row_count"],
        },
        {
            "index": 2,
            "slice_id": "gate_value_projection",
            "schema": gate["schema"],
            "decision": gate["decision"],
            "proof_backend_version": "stwo-d64-gate-value-projection-air-proof-v1",
            "source_commitments": {"projection_input_row_commitment": gate["source_projection_input_row_commitment"]},
            "target_commitments": {
                "gate_projection_output_commitment": gate["gate_projection_output_commitment"],
                "value_projection_output_commitment": gate["value_projection_output_commitment"],
                "gate_value_projection_output_commitment": gate["gate_value_projection_output_commitment"],
            },
            "row_count": gate["row_count"],
        },
        {
            "index": 3,
            "slice_id": "activation_swiglu",
            "schema": activation["schema"],
            "decision": activation["decision"],
            "proof_backend_version": "stwo-d64-activation-swiglu-air-proof-v1",
            "source_commitments": {
                "gate_projection_output_commitment": activation["source_gate_projection_output_commitment"],
                "value_projection_output_commitment": activation["source_value_projection_output_commitment"],
                "gate_value_projection_output_commitment": activation["source_gate_value_projection_output_commitment"],
            },
            "target_commitments": {"hidden_activation_commitment": activation["hidden_activation_commitment"]},
            "row_count": activation["row_count"],
        },
        {
            "index": 4,
            "slice_id": "down_projection",
            "schema": down["schema"],
            "decision": down["decision"],
            "proof_backend_version": "stwo-d64-down-projection-air-proof-v1",
            "source_commitments": {"hidden_activation_commitment": down["source_hidden_activation_commitment"]},
            "target_commitments": {"residual_delta_commitment": down["residual_delta_commitment"]},
            "row_count": down["row_count"],
        },
        {
            "index": 5,
            "slice_id": "residual_add",
            "schema": residual["schema"],
            "decision": residual["decision"],
            "proof_backend_version": "stwo-d64-residual-add-air-proof-v1",
            "source_commitments": {
                "input_activation_commitment": residual["input_activation_commitment"],
                "residual_delta_commitment": residual["residual_delta_commitment"],
            },
            "target_commitments": {"output_activation_commitment": residual["output_activation_commitment"]},
            "row_count": residual["row_count"],
        },
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
        "fixture_schema": FIXTURE.SCHEMA,
    }


def _receipt_payload_for_commitment(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    payload["block_receipt_commitment"] = None
    return payload


def refresh_commitments(payload: dict[str, Any]) -> None:
    payload["slice_chain_commitment"] = blake2b_commitment(payload["slice_chain"], "ptvm:zkai:d64-block:slice-chain:v1")
    payload["evidence_manifest_commitment"] = blake2b_commitment(
        payload["source_evidence_manifest"],
        "ptvm:zkai:d64-block:evidence-manifest:v1",
    )
    receipt = payload["block_receipt"]
    receipt["slice_chain_commitment"] = payload["slice_chain_commitment"]
    receipt["evidence_manifest_commitment"] = payload["evidence_manifest_commitment"]
    receipt["block_receipt_commitment"] = blake2b_commitment(
        _receipt_payload_for_commitment(receipt),
        "ptvm:zkai:d64-block:receipt:v1",
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
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "verifier_domain": VERIFIER_DOMAIN,
        "slice_versions": [
            {"slice_id": spec.slice_id, "proof_backend_version": spec.proof_version, "schema": spec.schema}
            for spec in SLICE_SPECS
        ],
        "slice_chain_commitment": None,
        "evidence_manifest_commitment": None,
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
    validate_payload(payload)
    return payload


def _manifest_by_slice(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = payload.get("source_evidence_manifest")
    if not isinstance(manifest, list):
        raise D64BlockReceiptError("source evidence manifest must be a list")
    by_slice: dict[str, dict[str, Any]] = {}
    for expected_index, item in enumerate(manifest):
        if not isinstance(item, dict):
            raise D64BlockReceiptError("source evidence manifest item must be an object")
        if item.get("index") != expected_index:
            raise D64BlockReceiptError("source evidence manifest index mismatch")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D64BlockReceiptError("source evidence manifest slice_id must be a string")
        if slice_id in by_slice:
            raise D64BlockReceiptError("duplicate source evidence manifest slice")
        by_slice[slice_id] = item
    return by_slice


def _chain_by_slice(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    chain = payload.get("slice_chain")
    if not isinstance(chain, list):
        raise D64BlockReceiptError("slice chain must be a list")
    by_slice: dict[str, dict[str, Any]] = {}
    expected_ids = [spec.slice_id for spec in SLICE_SPECS]
    actual_ids: list[str] = []
    for expected_index, item in enumerate(chain):
        if not isinstance(item, dict):
            raise D64BlockReceiptError("slice chain item must be an object")
        if item.get("index") != expected_index:
            raise D64BlockReceiptError("slice chain index mismatch")
        slice_id = item.get("slice_id")
        if not isinstance(slice_id, str):
            raise D64BlockReceiptError("slice chain slice_id must be a string")
        if slice_id in by_slice:
            raise D64BlockReceiptError("duplicate slice in slice chain")
        actual_ids.append(slice_id)
        by_slice[slice_id] = item
    if actual_ids != expected_ids:
        raise D64BlockReceiptError("slice chain order or membership mismatch")
    for spec in SLICE_SPECS:
        item = by_slice[spec.slice_id]
        expect_equal(item.get("schema"), spec.schema, f"{spec.slice_id} schema")
        expect_equal(item.get("decision"), spec.decision, f"{spec.slice_id} decision")
        expect_equal(item.get("proof_backend_version"), spec.proof_version, f"{spec.slice_id} proof version")
        row_count = require_int(item.get("row_count"), f"{spec.slice_id} row_count")
        if row_count <= 0:
            raise D64BlockReceiptError(f"{spec.slice_id} row_count must be positive")
        if not isinstance(item.get("source_commitments"), dict):
            raise D64BlockReceiptError(f"{spec.slice_id} source commitments must be an object")
        if not isinstance(item.get("target_commitments"), dict):
            raise D64BlockReceiptError(f"{spec.slice_id} target commitments must be an object")
        expected_source_keys, expected_target_keys = EXPECTED_COMMITMENT_KEYS[spec.slice_id]
        if set(item["source_commitments"]) != expected_source_keys:
            raise D64BlockReceiptError(f"{spec.slice_id} source commitment keys mismatch")
        if set(item["target_commitments"]) != expected_target_keys:
            raise D64BlockReceiptError(f"{spec.slice_id} target commitment keys mismatch")
        for field, value in [*item["source_commitments"].items(), *item["target_commitments"].items()]:
            require_commitment(value, f"{spec.slice_id} {field}")
    return by_slice


def _validate_source_hashes(payload: dict[str, Any]) -> None:
    by_slice = _manifest_by_slice(payload)
    for spec in SLICE_SPECS:
        item = by_slice.get(spec.slice_id)
        if item is None:
            raise D64BlockReceiptError("missing source evidence manifest slice")
        expect_equal(item.get("schema"), spec.schema, f"{spec.slice_id} manifest schema")
        expect_equal(item.get("decision"), spec.decision, f"{spec.slice_id} manifest decision")
        expect_equal(item.get("proof_backend_version"), spec.proof_version, f"{spec.slice_id} manifest proof version")
        path_value = item.get("path")
        if not isinstance(path_value, str):
            raise D64BlockReceiptError(f"{spec.slice_id} manifest path must be a string")
        path = (ROOT / path_value).resolve()
        if path != spec.evidence_path.resolve():
            raise D64BlockReceiptError(f"{spec.slice_id} manifest path mismatch")
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
        bridge["source_commitments"]["rmsnorm_output_row_commitment"],
        rmsnorm["target_commitments"]["rmsnorm_output_row_commitment"],
        "RMSNorm-to-bridge commitment edge",
    )
    expect_equal(
        gate["source_commitments"]["projection_input_row_commitment"],
        bridge["target_commitments"]["projection_input_row_commitment"],
        "bridge-to-projection commitment edge",
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
        down["source_commitments"]["hidden_activation_commitment"],
        activation["target_commitments"]["hidden_activation_commitment"],
        "activation-to-down commitment edge",
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
    if residual["source_commitments"]["residual_delta_commitment"] == residual["target_commitments"]["output_activation_commitment"]:
        raise D64BlockReceiptError("residual delta commitment relabeled as final output")
    if residual["source_commitments"]["input_activation_commitment"] == residual["target_commitments"]["output_activation_commitment"]:
        raise D64BlockReceiptError("input activation commitment relabeled as final output")


def _validate_receipt(payload: dict[str, Any]) -> None:
    receipt = payload.get("block_receipt")
    if not isinstance(receipt, dict):
        raise D64BlockReceiptError("block receipt must be an object")
    expected = {
        "receipt_version": RECEIPT_VERSION,
        "statement_kind": STATEMENT_KIND,
        "target_id": TARGET_ID,
        "input_activation_commitment": INPUT_ACTIVATION_COMMITMENT,
        "output_activation_commitment": OUTPUT_ACTIVATION_COMMITMENT,
        "proof_native_parameter_commitment": PROOF_NATIVE_PARAMETER_COMMITMENT,
        "public_instance_commitment": PUBLIC_INSTANCE_COMMITMENT,
        "statement_commitment": STATEMENT_COMMITMENT,
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
        raise D64BlockReceiptError("block receipt slice_versions mismatch")
    for version, spec in zip(slice_versions, SLICE_SPECS, strict=True):
        expect_equal(version.get("slice_id"), spec.slice_id, "block receipt slice version id")
        expect_equal(version.get("schema"), spec.schema, "block receipt slice version schema")
        expect_equal(version.get("proof_backend_version"), spec.proof_version, "block receipt slice proof version")
    expect_equal(
        receipt.get("block_receipt_commitment"),
        blake2b_commitment(_receipt_payload_for_commitment(receipt), "ptvm:zkai:d64-block:receipt:v1"),
        "block receipt commitment",
    )


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise D64BlockReceiptError("block receipt composition payload must be an object")
    expect_equal(payload.get("schema"), SCHEMA, "schema")
    expect_equal(payload.get("decision"), DECISION, "decision")
    expect_equal(payload.get("result"), "GO", "result")
    chain = _chain_by_slice(payload)
    _validate_chain_edges(chain)
    expect_equal(
        payload.get("slice_chain_commitment"),
        blake2b_commitment(payload["slice_chain"], "ptvm:zkai:d64-block:slice-chain:v1"),
        "slice chain commitment",
    )
    expect_equal(
        payload.get("evidence_manifest_commitment"),
        blake2b_commitment(payload["source_evidence_manifest"], "ptvm:zkai:d64-block:evidence-manifest:v1"),
        "evidence manifest commitment",
    )
    _validate_source_hashes(payload)
    _validate_receipt(payload)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise D64BlockReceiptError("summary must be an object")
    expect_equal(summary.get("slice_count"), len(SLICE_SPECS), "summary slice count")
    total_checked_rows = sum(
        require_int(item.get("row_count"), f"{item.get('slice_id', 'unknown')} row_count")
        for item in chain.values()
    )
    expect_equal(summary.get("total_checked_rows"), total_checked_rows, "summary row count")
    expect_equal(summary.get("input_activation_commitment"), INPUT_ACTIVATION_COMMITMENT, "summary input commitment")
    expect_equal(summary.get("output_activation_commitment"), OUTPUT_ACTIVATION_COMMITMENT, "summary output commitment")


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
        "stale_hidden_activation_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][3]["target_commitments"].__setitem__("hidden_activation_commitment", "blake2b-256:" + "11" * 32),
    )
    add(
        "stale_residual_delta_edge",
        "commitment_chain",
        lambda p: p["slice_chain"][4]["target_commitments"].__setitem__("residual_delta_commitment", "blake2b-256:" + "22" * 32),
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
        "backend_version_drift",
        "block_receipt",
        lambda p: p["block_receipt"].__setitem__("required_backend_version", "stwo-rmsnorm-swiglu-residual-d64-v3"),
    )
    add(
        "slice_version_drift",
        "block_receipt",
        lambda p: p["block_receipt"]["slice_versions"][5].__setitem__(
            "proof_backend_version",
            "stwo-d64-residual-add-air-proof-v2",
        ),
    )
    add(
        "model_config_drift",
        "block_receipt",
        lambda p: p["block_receipt"]["model_config"].__setitem__("width", 128),
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


def mutation_cases(baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(baseline or build_payload())
    validate_payload(baseline)
    cases = []
    for mutation, surface, mutated in _mutated_cases(baseline):
        try:
            validate_payload(mutated)
            accepted = True
            error = ""
            layer = "accepted"
        except D64BlockReceiptError as err:
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
        raise D64BlockReceiptError("not all d64 block receipt mutations rejected")
    return result


def to_tsv(payload: dict[str, Any]) -> str:
    output = []
    writer_buffer: list[dict[str, Any]] = []
    for case in payload["cases"]:
        writer_buffer.append({key: case[key] for key in TSV_COLUMNS})
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(writer_buffer)
    output.append(buffer.getvalue())
    return "".join(output)


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if tsv_path is not None:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        tsv_path.write_text(to_tsv(payload), encoding="utf-8")


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
