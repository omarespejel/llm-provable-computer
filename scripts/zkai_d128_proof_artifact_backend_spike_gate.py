#!/usr/bin/env python3
"""Gate the current backend route for a real d128 transformer-block proof.

This is intentionally narrower than the d128 comparator target gate.  It does
not ask whether the d128 shape is useful; that was already checked.  It asks
whether today's repository can actually produce a local d128 proof artifact
with a verifier handle and relabeling tests.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
TARGET_GATE_PATH = ROOT / "scripts" / "zkai_d128_layerwise_comparator_target_gate.py"
D64_BLOCK_GATE_PATH = ROOT / "scripts" / "zkai_d64_block_receipt_composition_gate.py"
VECTOR_RESIDUAL_GATE_PATH = ROOT / "scripts" / "zkai_d128_vector_residual_add_proof_input.py"
D128_RMSNORM_GATE_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
D128_BRIDGE_GATE_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_to_projection_bridge_input.py"
TARGET_EVIDENCE = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"
D64_BLOCK_EVIDENCE = EVIDENCE_DIR / "zkai-d64-block-receipt-composition-gate-2026-05.json"
VECTOR_RESIDUAL_EVIDENCE = EVIDENCE_DIR / "zkai-d128-vector-residual-add-proof-2026-05.json"
D128_RMSNORM_EVIDENCE = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
D128_BRIDGE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-proof-artifact-backend-spike-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-proof-artifact-backend-spike-2026-05.tsv"

SCHEMA = "zkai-d128-proof-artifact-backend-spike-v1"
DECISION = "NO_GO_D128_FULL_BLOCK_PROOF_ARTIFACT_SLICES_MISSING"
RESULT = "BOUNDED_NO_GO"
ISSUE = 387
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
TARGET_WIDTH = 128
TARGET_FF_DIM = 512
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
REQUIRED_TOOLCHAIN = "nightly-2025-07-14"
GATE_COMMITMENT_DOMAIN = "ptvm:zkai:d128-proof-artifact-backend-spike:v1"
FIRST_BLOCKER = (
    "d128 RMSNorm public-row, RMSNorm-to-projection bridge, and residual-add proof "
    "handles exist, but gate/value projection, activation, down-projection, native "
    "residual, and full transformer-block composition handles are still missing"
)

D64_PROOF_SLICES = (
    {
        "slice": "rmsnorm_public_rows",
        "module": "src/stwo_backend/d64_native_rmsnorm_public_row_proof.rs",
        "evidence": "docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.json",
        "prove_symbol": "prove_zkai_d64_rmsnorm_public_row_envelope",
        "verify_symbol": "verify_zkai_d64_rmsnorm_public_row_envelope",
        "proof_version": "stwo-d64-rmsnorm-public-row-air-proof-v2",
    },
    {
        "slice": "rmsnorm_projection_bridge",
        "module": "src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs",
        "evidence": "docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json",
        "prove_symbol": "prove_zkai_d64_rmsnorm_to_projection_bridge_envelope",
        "verify_symbol": "verify_zkai_d64_rmsnorm_to_projection_bridge_envelope",
        "proof_version": "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1",
    },
    {
        "slice": "gate_value_projection",
        "module": "src/stwo_backend/d64_native_gate_value_projection_proof.rs",
        "evidence": "docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json",
        "prove_symbol": "prove_zkai_d64_gate_value_projection_envelope",
        "verify_symbol": "verify_zkai_d64_gate_value_projection_envelope",
        "proof_version": "stwo-d64-gate-value-projection-air-proof-v1",
    },
    {
        "slice": "activation_swiglu",
        "module": "src/stwo_backend/d64_native_activation_swiglu_proof.rs",
        "evidence": "docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json",
        "prove_symbol": "prove_zkai_d64_activation_swiglu_envelope",
        "verify_symbol": "verify_zkai_d64_activation_swiglu_envelope",
        "proof_version": "stwo-d64-activation-swiglu-air-proof-v1",
    },
    {
        "slice": "down_projection",
        "module": "src/stwo_backend/d64_native_down_projection_proof.rs",
        "evidence": "docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json",
        "prove_symbol": "prove_zkai_d64_down_projection_envelope",
        "verify_symbol": "verify_zkai_d64_down_projection_envelope",
        "proof_version": "stwo-d64-down-projection-air-proof-v1",
    },
    {
        "slice": "residual_add",
        "module": "src/stwo_backend/d64_native_residual_add_proof.rs",
        "evidence": "docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json",
        "prove_symbol": "prove_zkai_d64_residual_add_envelope",
        "verify_symbol": "verify_zkai_d64_residual_add_envelope",
        "proof_version": "stwo-d64-residual-add-air-proof-v1",
    },
)

EXPECTED_D128_MODULES = (
    "src/stwo_backend/d128_native_gate_value_projection_proof.rs",
    "src/stwo_backend/d128_native_activation_swiglu_proof.rs",
    "src/stwo_backend/d128_native_down_projection_proof.rs",
    "src/stwo_backend/d128_native_residual_add_proof.rs",
    "src/stwo_backend/d128_native_transformer_block_proof.rs",
)

EXPECTED_D128_EXPORT_SYMBOLS = (
    "prove_zkai_d128_gate_value_projection_envelope",
    "verify_zkai_d128_gate_value_projection_envelope",
    "prove_zkai_d128_activation_swiglu_envelope",
    "verify_zkai_d128_activation_swiglu_envelope",
    "prove_zkai_d128_down_projection_envelope",
    "verify_zkai_d128_down_projection_envelope",
    "prove_zkai_d128_residual_add_envelope",
    "verify_zkai_d128_residual_add_envelope",
    "prove_zkai_d128_transformer_block_envelope",
    "verify_zkai_d128_transformer_block_envelope",
)

D128_RMSNORM_SYMBOLS = (
    "ZkAiD128RmsnormPublicRowProofInput",
    "ZkAiD128RmsnormPublicRowProofEnvelope",
    "zkai_d128_rmsnorm_public_row_input_from_json_str",
    "prove_zkai_d128_rmsnorm_public_row_envelope",
    "verify_zkai_d128_rmsnorm_public_row_envelope",
)

D128_BRIDGE_SYMBOLS = (
    "D128RmsnormToProjectionBridgeRow",
    "ZkAiD128RmsnormToProjectionBridgeInput",
    "ZkAiD128RmsnormToProjectionBridgeEnvelope",
    "zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str",
    "prove_zkai_d128_rmsnorm_to_projection_bridge_envelope",
    "verify_zkai_d128_rmsnorm_to_projection_bridge_envelope",
)

PARAMETERIZED_RESIDUAL_ADD_SYMBOLS = (
    "ZkAiVectorBlockProofInput",
    "ZkAiVectorBlockProofEnvelope",
    "zkai_vector_block_input_from_json_str",
    "prove_zkai_vector_block_envelope",
    "verify_zkai_vector_block_envelope",
)

MISSING_PARAMETERIZED_FULL_BLOCK_SYMBOLS = (
    "ZkAiParameterizedTransformerBlockProof",
    "parameterized_transformer_block_air",
    "prove_zkai_parameterized_transformer_block_envelope",
    "verify_zkai_parameterized_transformer_block_envelope",
)

D64_HARDCODE_MARKERS = {
    "src/stwo_backend/d64_native_rmsnorm_public_row_proof.rs": (
        "expect_usize(input.width, ZKAI_D64_WIDTH",
        "ZKAI_D64_RMSNORM_PUBLIC_ROW_PROOF_VERSION",
        "ZKAI_D64_TARGET_ID",
    ),
    "src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs": (
        "expect_usize(input.width, ZKAI_D64_WIDTH",
        "ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION",
        "D64_BRIDGE_LOG_SIZE",
    ),
    "src/stwo_backend/d64_native_gate_value_projection_proof.rs": (
        "expect_usize(input.width, ZKAI_D64_WIDTH",
        "expect_usize(input.ff_dim, ZKAI_D64_FF_DIM",
        "D64_GATE_VALUE_LOG_SIZE",
    ),
    "src/stwo_backend/d64_native_activation_swiglu_proof.rs": (
        "expect_usize(input.width, ZKAI_D64_WIDTH",
        "expect_usize(input.ff_dim, ZKAI_D64_FF_DIM",
        "D64_ACTIVATION_SWIGLU_LOG_SIZE",
    ),
    "src/stwo_backend/d64_native_down_projection_proof.rs": (
        "expect_usize(input.width, ZKAI_D64_WIDTH",
        "expect_usize(input.ff_dim, ZKAI_D64_FF_DIM",
        "D64_DOWN_PROJECTION_LOG_SIZE",
    ),
    "src/stwo_backend/d64_native_residual_add_proof.rs": (
        "expect_usize(input.width, ZKAI_D64_WIDTH",
        "ZKAI_D64_RESIDUAL_ADD_PROOF_VERSION",
        "D64_RESIDUAL_ADD_LOG_SIZE",
    ),
}

NON_CLAIMS = [
    "not a full local d128 transformer-block proof artifact",
    "not verifier-time evidence for a full d128 transformer block",
    "not proof-size evidence for a full d128 transformer block",
    "not recursive aggregation",
    "not backend independence evidence",
    "not a matched NANOZK or DeepProve benchmark",
    "not a claim that d128 is impossible",
]

VALIDATION_COMMANDS = [
    "python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_public_row_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_vector_residual_add_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test d128_native_rmsnorm_public_row_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test zkai_vector_block_residual_add_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test --lib stwo_backend::d64_native_rmsnorm_air_feasibility::tests::d64_rmsnorm_air_feasibility_records_existing_component_no_go --features stwo-backend -- --nocapture --exact",
    "just gate-fast",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "just gate",
]

TSV_COLUMNS = (
    "route",
    "status",
    "target_width",
    "target_ff_dim",
    "proof_artifact_exists",
    "verifier_handle_exists",
    "proof_size_bytes",
    "verifier_time_ms",
    "blocker",
)

MUTATION_TSV_COLUMNS = (
    "mutation",
    "surface",
    "mutated_accepted",
    "rejected",
    "rejection_layer",
    "error",
)

EXPECTED_MUTATION_INVENTORY = (
    ("decision_promoted_to_go", "top_level"),
    ("target_width_drift", "target_spec"),
    ("target_backend_version_drift", "target_spec"),
    ("local_proof_artifact_smuggled", "proof_status"),
    ("local_verifier_handle_smuggled", "proof_status"),
    ("proof_size_metric_smuggled", "metrics"),
    ("verifier_time_metric_smuggled", "metrics"),
    ("direct_d128_route_promoted", "backend_routes"),
    ("d128_rmsnorm_public_row_route_promoted", "backend_routes"),
    ("partial_d128_rmsnorm_public_row_proof_removed", "proof_status"),
    ("partial_d128_rmsnorm_public_row_verifier_removed", "proof_status"),
    ("partial_d128_rmsnorm_public_row_local_roundtrip_removed", "proof_status"),
    ("partial_d128_rmsnorm_public_row_checked_in_artifact_smuggled", "proof_status"),
    ("d128_rmsnorm_to_projection_bridge_route_promoted", "backend_routes"),
    ("partial_d128_rmsnorm_to_projection_bridge_proof_removed", "proof_status"),
    ("partial_d128_rmsnorm_to_projection_bridge_verifier_removed", "proof_status"),
    ("partial_d128_rmsnorm_to_projection_bridge_local_roundtrip_removed", "proof_status"),
    ("partial_d128_rmsnorm_to_projection_bridge_checked_in_artifact_smuggled", "proof_status"),
    ("full_block_parameterized_route_promoted", "backend_routes"),
    ("d64_anchor_removed", "d64_anchor"),
    ("missing_module_removed", "source_probe"),
    ("d64_hardcoded_marker_removed", "source_probe"),
    ("non_claim_removed", "claim_boundary"),
    ("mutation_case_accepted", "mutation_harness"),
)


class D128BackendSpikeError(ValueError):
    pass


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise D128BackendSpikeError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


TARGET_GATE = _load_module(TARGET_GATE_PATH, "zkai_d128_target_for_backend_spike")
D64_BLOCK_GATE = _load_module(D64_BLOCK_GATE_PATH, "zkai_d64_block_for_d128_backend_spike")
VECTOR_RESIDUAL_GATE = _load_module(
    VECTOR_RESIDUAL_GATE_PATH,
    "zkai_d128_vector_residual_add_for_backend_spike",
)
D128_RMSNORM_GATE = _load_module(
    D128_RMSNORM_GATE_PATH,
    "zkai_d128_rmsnorm_public_row_for_backend_spike",
)
D128_BRIDGE_GATE = _load_module(
    D128_BRIDGE_GATE_PATH,
    "zkai_d128_rmsnorm_to_projection_bridge_for_backend_spike",
)


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


def gate_commitment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "gate_commitment"}


def set_gate_commitment(payload: dict[str, Any]) -> None:
    payload["gate_commitment"] = blake2b_commitment(gate_commitment_payload(payload), GATE_COMMITMENT_DOMAIN)


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise D128BackendSpikeError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise D128BackendSpikeError(f"{field} must be a list")
    return value


def require_commitment(value: Any, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"blake2b-256:[0-9a-f]{64}", value) is None:
        raise D128BackendSpikeError(f"{field} must be a blake2b-256 commitment")
    return value


def expect_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise D128BackendSpikeError(f"{field} mismatch")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise D128BackendSpikeError(f"JSON source is not a regular file: {path}")
    if ROOT.resolve() not in resolved.parents:
        raise D128BackendSpikeError(f"JSON source escapes repository: {path}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise D128BackendSpikeError(f"failed to load JSON source {path}: {err}") from err
    if not isinstance(payload, dict):
        raise D128BackendSpikeError(f"JSON source must be an object: {path}")
    return payload


def source_descriptor(path: pathlib.Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": relative_path(path),
        "file_sha256": file_sha256(path),
        "payload_sha256": sha256_hex_json(payload),
        "schema": payload.get("schema"),
        "decision": payload.get("decision"),
        "result": payload.get("result"),
    }


def load_checked_target() -> dict[str, Any]:
    payload = load_json(TARGET_EVIDENCE)
    try:
        TARGET_GATE.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128BackendSpikeError(f"d128 comparator target validation failed: {err}") from err
    if payload.get("target_result") != TARGET_GATE.TARGET_RESULT:
        raise D128BackendSpikeError("d128 target spec is not a GO target")
    if payload.get("local_proof_result") != TARGET_GATE.LOCAL_PROOF_RESULT:
        raise D128BackendSpikeError("d128 target evidence no longer records missing local proof")
    return payload


def load_checked_d64_block() -> dict[str, Any]:
    payload = load_json(D64_BLOCK_EVIDENCE)
    try:
        D64_BLOCK_GATE.validate_payload(payload)
    except Exception as err:  # noqa: BLE001 - normalize imported validator errors.
        raise D128BackendSpikeError(f"d64 block composition validation failed: {err}") from err
    if payload.get("decision") != D64_BLOCK_GATE.DECISION:
        raise D128BackendSpikeError("d64 block composition is not a GO anchor")
    return payload


def read_repo_file(path: str) -> str:
    full = ROOT / path
    if not full.is_file():
        raise D128BackendSpikeError(f"required source file missing: {path}")
    return full.read_text(encoding="utf-8")


def repo_file_descriptor(path: str) -> dict[str, Any]:
    full = ROOT / path
    return {
        "path": path,
        "exists": full.is_file(),
        "file_sha256": file_sha256(full) if full.is_file() else None,
    }


def rust_declares_symbol(module_text: str, symbol: str) -> bool:
    escaped = re.escape(symbol)
    return bool(
        re.search(rf"(?m)^\s*pub(?:\s*\([^)]*\))?\s+(?:struct|fn)\s+{escaped}\b", module_text)
    )


def rust_reexports_symbol(mod_rs: str, module_name: str, symbol: str) -> bool:
    escaped_module = re.escape(module_name)
    escaped_symbol = re.escape(symbol)
    direct = rf"(?m)^\s*pub\s+use\s+{escaped_module}::{escaped_symbol}\b"
    if re.search(direct, mod_rs):
        return True
    block_pattern = rf"(?ms)^\s*pub\s+use\s+{escaped_module}::\{{(?P<body>.*?)^\s*\}};"
    for match in re.finditer(block_pattern, mod_rs, flags=re.DOTALL):
        if re.search(rf"\b{escaped_symbol}\b", match.group("body")):
            return True
    return False


def build_source_probe() -> dict[str, Any]:
    mod_rs = read_repo_file("src/stwo_backend/mod.rs")
    d64_slices = []
    for spec in D64_PROOF_SLICES:
        module_text = read_repo_file(spec["module"])
        evidence = load_json(ROOT / spec["evidence"])
        for symbol in (spec["prove_symbol"], spec["verify_symbol"]):
            if symbol not in mod_rs:
                raise D128BackendSpikeError(f"d64 exported symbol missing from mod.rs: {symbol}")
            if symbol not in module_text:
                raise D128BackendSpikeError(f"d64 module symbol missing from source: {symbol}")
        expect_equal(evidence.get("target_id"), "rmsnorm-swiglu-residual-d64-v2", f"{spec['slice']} target id")
        expect_equal(evidence.get("width"), 64, f"{spec['slice']} width")
        d64_slices.append(
            {
                "slice": spec["slice"],
                "module": repo_file_descriptor(spec["module"]),
                "evidence": source_descriptor(ROOT / spec["evidence"], evidence),
                "prove_symbol": spec["prove_symbol"],
                "verify_symbol": spec["verify_symbol"],
                "proof_version": spec["proof_version"],
            }
        )

    d128_rmsnorm_module_path = "src/stwo_backend/d128_native_rmsnorm_public_row_proof.rs"
    d128_rmsnorm_module = read_repo_file(d128_rmsnorm_module_path)
    if "mod d128_native_rmsnorm_public_row_proof;" not in mod_rs:
        raise D128BackendSpikeError("d128 RMSNorm public-row module missing from mod.rs")
    missing_d128_rmsnorm_symbols = []
    for symbol in D128_RMSNORM_SYMBOLS:
        if not rust_declares_symbol(
            d128_rmsnorm_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "d128_native_rmsnorm_public_row_proof", symbol):
            missing_d128_rmsnorm_symbols.append(symbol)
    if missing_d128_rmsnorm_symbols:
        raise D128BackendSpikeError(
            "d128 RMSNorm public-row route disappeared; refresh this partial-go gate"
        )

    d128_rmsnorm_evidence = load_json(D128_RMSNORM_EVIDENCE)
    try:
        D128_RMSNORM_GATE.validate_payload(d128_rmsnorm_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 RMSNorm public-row evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
        "decision": "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
        "operation": "rmsnorm_public_rows",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "row_count": TARGET_WIDTH,
    }.items():
        expect_equal(d128_rmsnorm_evidence.get(field), expected, f"d128 RMSNorm public-row {field}")

    d128_bridge_module_path = "src/stwo_backend/d128_native_rmsnorm_to_projection_bridge_proof.rs"
    d128_bridge_module = read_repo_file(d128_bridge_module_path)
    if "mod d128_native_rmsnorm_to_projection_bridge_proof;" not in mod_rs:
        raise D128BackendSpikeError("d128 RMSNorm-to-projection bridge module missing from mod.rs")
    missing_d128_bridge_symbols = []
    for symbol in D128_BRIDGE_SYMBOLS:
        if not rust_declares_symbol(
            d128_bridge_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "d128_native_rmsnorm_to_projection_bridge_proof", symbol):
            missing_d128_bridge_symbols.append(symbol)
    if missing_d128_bridge_symbols:
        raise D128BackendSpikeError(
            "d128 RMSNorm-to-projection bridge route disappeared; refresh this partial-go gate"
        )

    d128_bridge_evidence = load_json(D128_BRIDGE_EVIDENCE)
    try:
        D128_BRIDGE_GATE.validate_payload(d128_bridge_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 RMSNorm-to-projection bridge evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1",
        "decision": "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF",
        "operation": "rmsnorm_to_projection_bridge",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "row_count": TARGET_WIDTH,
    }.items():
        expect_equal(
            d128_bridge_evidence.get(field),
            expected,
            f"d128 RMSNorm-to-projection bridge {field}",
        )
    expect_equal(
        d128_bridge_evidence.get("source_rmsnorm_output_row_commitment"),
        d128_rmsnorm_evidence.get("rmsnorm_output_row_commitment"),
        "d128 bridge source RMSNorm output row commitment",
    )
    expect_equal(
        d128_bridge_evidence.get("source_rmsnorm_statement_commitment"),
        d128_rmsnorm_evidence.get("statement_commitment"),
        "d128 bridge source RMSNorm statement commitment",
    )
    expect_equal(
        d128_bridge_evidence.get("source_rmsnorm_public_instance_commitment"),
        d128_rmsnorm_evidence.get("public_instance_commitment"),
        "d128 bridge source RMSNorm public-instance commitment",
    )

    missing_d128_modules = []
    for path in EXPECTED_D128_MODULES:
        full = ROOT / path
        if full.exists():
            raise D128BackendSpikeError(
                "additional d128 native module route may now exist; refresh this gate before relying on it"
            )
        else:
            missing_d128_modules.append(path)

    present_d128_symbols = [symbol for symbol in EXPECTED_D128_EXPORT_SYMBOLS if symbol in mod_rs]
    if present_d128_symbols:
        raise D128BackendSpikeError(
            "d128 export route may now exist; refresh this no-go gate before relying on it"
        )
    missing_d128_symbols = list(EXPECTED_D128_EXPORT_SYMBOLS)

    residual_module_path = "src/stwo_backend/zkai_vector_block_residual_add_proof.rs"
    residual_module = read_repo_file(residual_module_path)
    if "mod zkai_vector_block_residual_add_proof;" not in mod_rs:
        raise D128BackendSpikeError("parameterized residual-add module missing from mod.rs")
    missing_parameterized_residual_symbols = []
    for symbol in PARAMETERIZED_RESIDUAL_ADD_SYMBOLS:
        if not rust_declares_symbol(
            residual_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "zkai_vector_block_residual_add_proof", symbol):
            missing_parameterized_residual_symbols.append(symbol)
    if missing_parameterized_residual_symbols:
        raise D128BackendSpikeError(
            "parameterized residual-add vector route disappeared; refresh this partial-go gate"
        )
    present_parameterized_residual_symbols = list(PARAMETERIZED_RESIDUAL_ADD_SYMBOLS)
    missing_parameterized_full_block_symbols = [
        symbol
        for symbol in MISSING_PARAMETERIZED_FULL_BLOCK_SYMBOLS
        if not rust_reexports_symbol(mod_rs, "zkai_parameterized_transformer_block_proof", symbol)
    ]
    present_parameterized_full_block_symbols = [
        symbol
        for symbol in MISSING_PARAMETERIZED_FULL_BLOCK_SYMBOLS
        if rust_reexports_symbol(mod_rs, "zkai_parameterized_transformer_block_proof", symbol)
    ]
    if present_parameterized_full_block_symbols:
        raise D128BackendSpikeError(
            "parameterized full transformer-block route may now exist; refresh this no-go gate before relying on it"
        )

    residual_evidence = load_json(VECTOR_RESIDUAL_EVIDENCE)
    try:
        VECTOR_RESIDUAL_GATE.validate_payload(residual_evidence)
    except Exception as err:
        raise D128BackendSpikeError("parameterized residual-add evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-vector-block-residual-add-air-proof-input-v1",
        "decision": "GO_INPUT_FOR_VECTOR_BLOCK_RESIDUAL_ADD_AIR_PROOF",
        "operation": "residual_add",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "row_count": TARGET_WIDTH,
    }.items():
        expect_equal(residual_evidence.get(field), expected, f"parameterized residual-add {field}")

    hardcoded_markers = []
    for path, markers in D64_HARDCODE_MARKERS.items():
        text = read_repo_file(path)
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise D128BackendSpikeError(f"d64 hard-code marker missing unexpectedly in {path}: {missing}")
        hardcoded_markers.append({"path": path, "markers": list(markers)})

    return {
        "d64_slices": d64_slices,
        "missing_d128_modules": missing_d128_modules,
        "missing_d128_export_symbols": missing_d128_symbols,
        "d128_rmsnorm_public_row": {
            "status": "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
            "module": repo_file_descriptor(d128_rmsnorm_module_path),
            "evidence": source_descriptor(D128_RMSNORM_EVIDENCE, d128_rmsnorm_evidence),
            "present_symbols": list(D128_RMSNORM_SYMBOLS),
            "operation": d128_rmsnorm_evidence["operation"],
            "target_width": d128_rmsnorm_evidence["width"],
            "row_count": d128_rmsnorm_evidence["row_count"],
            "statement_commitment": d128_rmsnorm_evidence["statement_commitment"],
            "public_instance_commitment": d128_rmsnorm_evidence["public_instance_commitment"],
            "rmsnorm_output_row_commitment": d128_rmsnorm_evidence["rmsnorm_output_row_commitment"],
            "rms_q8": d128_rmsnorm_evidence["rms_q8"],
        },
        "d128_rmsnorm_to_projection_bridge": {
            "status": "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
            "module": repo_file_descriptor(d128_bridge_module_path),
            "evidence": source_descriptor(D128_BRIDGE_EVIDENCE, d128_bridge_evidence),
            "present_symbols": list(D128_BRIDGE_SYMBOLS),
            "operation": d128_bridge_evidence["operation"],
            "target_width": d128_bridge_evidence["width"],
            "row_count": d128_bridge_evidence["row_count"],
            "source_rmsnorm_statement_commitment": d128_bridge_evidence["source_rmsnorm_statement_commitment"],
            "source_rmsnorm_public_instance_commitment": d128_bridge_evidence[
                "source_rmsnorm_public_instance_commitment"
            ],
            "source_rmsnorm_output_row_commitment": d128_bridge_evidence["source_rmsnorm_output_row_commitment"],
            "projection_input_row_commitment": d128_bridge_evidence["projection_input_row_commitment"],
            "projection_input_relabels_full_output": (
                d128_bridge_evidence["projection_input_row_commitment"]
                == d128_bridge_evidence["forbidden_output_activation_commitment"]
            ),
        },
        "parameterized_residual_add": {
            "status": "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
            "module": repo_file_descriptor(residual_module_path),
            "evidence": source_descriptor(VECTOR_RESIDUAL_EVIDENCE, residual_evidence),
            "present_symbols": present_parameterized_residual_symbols,
            "operation": residual_evidence["operation"],
            "target_width": residual_evidence["width"],
            "row_count": residual_evidence["row_count"],
        },
        "missing_parameterized_full_block_symbols": missing_parameterized_full_block_symbols,
        "d64_hardcoded_markers": hardcoded_markers,
    }


def build_backend_routes(source_probe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "route": "existing_d64_slice_chain",
            "status": "GO_ANCHOR_ONLY",
            "target_width": 64,
            "target_ff_dim": 256,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "d64 slice proofs exist, but this is not the d128 target",
            "evidence": "docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json",
        },
        {
            "route": "direct_d128_native_modules",
            "status": "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": False,
            "verifier_handle_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "d128 RMSNorm public-row and RMSNorm-to-projection bridge native proofs exist, but the remaining native d128 slices and full block verifier do not",
            "missing_modules": source_probe["missing_d128_modules"],
            "missing_export_symbols": source_probe["missing_d128_export_symbols"],
        },
        {
            "route": "direct_d128_rmsnorm_public_row_air",
            "status": "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": None,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "RMSNorm public-row slice only; not projection, activation, down-projection, residual, bridge, or full block",
            "evidence": "docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json",
            "present_symbols": source_probe["d128_rmsnorm_public_row"]["present_symbols"],
        },
        {
            "route": "direct_d128_rmsnorm_to_projection_bridge_air",
            "status": "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": None,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "RMSNorm-to-projection bridge slice only; not gate/value projection, activation, down-projection, residual, or full block",
            "evidence": "docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json",
            "present_symbols": source_probe["d128_rmsnorm_to_projection_bridge"]["present_symbols"],
            "source_rmsnorm_statement_commitment": source_probe["d128_rmsnorm_to_projection_bridge"][
                "source_rmsnorm_statement_commitment"
            ],
            "source_rmsnorm_public_instance_commitment": source_probe["d128_rmsnorm_to_projection_bridge"][
                "source_rmsnorm_public_instance_commitment"
            ],
            "source_rmsnorm_output_row_commitment": source_probe["d128_rmsnorm_to_projection_bridge"][
                "source_rmsnorm_output_row_commitment"
            ],
            "projection_input_row_commitment": source_probe["d128_rmsnorm_to_projection_bridge"][
                "projection_input_row_commitment"
            ],
        },
        {
            "route": "lift_existing_d64_modules_by_metadata",
            "status": "NO_GO",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": False,
            "verifier_handle_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "d64 modules validate hard-coded width, target id, domains, and log sizes",
            "hardcoded_markers": source_probe["d64_hardcoded_markers"],
        },
        {
            "route": "parameterized_vector_residual_add_air",
            "status": "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": None,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "residual-add vector slice only; not a full d128 transformer-block proof",
            "evidence": "docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json",
            "present_symbols": source_probe["parameterized_residual_add"]["present_symbols"],
        },
        {
            "route": "parameterized_transformer_block_air",
            "status": "NO_GO_FULL_BLOCK_SLICES_MISSING",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": False,
            "verifier_handle_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": FIRST_BLOCKER,
            "missing_symbols": source_probe["missing_parameterized_full_block_symbols"],
        },
        {
            "route": "d128_metrics_and_relabeling_suite",
            "status": "NO_GO_BLOCKED_BEFORE_PROOF_OBJECT",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": False,
            "verifier_handle_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "do not report proof size, verifier time, or relabeling resistance until a d128 proof object and verifier handle exist",
        },
    ]


def expected_mutation_inventory() -> list[dict[str, Any]]:
    return [
        {"index": index, "mutation": mutation, "surface": surface}
        for index, (mutation, surface) in enumerate(EXPECTED_MUTATION_INVENTORY)
    ]


def build_payload() -> dict[str, Any]:
    target_payload = load_checked_target()
    d64_block_payload = load_checked_d64_block()
    source_probe = build_source_probe()
    routes = build_backend_routes(source_probe)
    target_spec = require_object(target_payload.get("target_spec"), "target spec")
    summary = {
        "issue": ISSUE,
        "target_id": TARGET_ID,
        "target_width": TARGET_WIDTH,
        "target_ff_dim": TARGET_FF_DIM,
        "first_blocker": FIRST_BLOCKER,
        "d64_anchor_route": "GO_ANCHOR_ONLY",
        "direct_d128_route": "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING",
        "d128_rmsnorm_public_row_route": "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
        "d128_rmsnorm_to_projection_bridge_route": "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        "parameterized_residual_add_route": "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "parameterized_full_block_route": "NO_GO_FULL_BLOCK_SLICES_MISSING",
        "blocked_before_metrics": True,
        "mutation_cases": len(EXPECTED_MUTATION_INVENTORY),
    }
    proof_status = {
        "proof_artifact_exists": False,
        "verifier_handle_exists": False,
        "partial_d128_rmsnorm_public_row_proof_exists": True,
        "partial_d128_rmsnorm_public_row_verifier_exists": True,
        "partial_d128_rmsnorm_public_row_local_roundtrip_proof_constructed": True,
        "partial_d128_rmsnorm_public_row_checked_in_proof_artifact_exists": False,
        "partial_d128_rmsnorm_to_projection_bridge_proof_exists": True,
        "partial_d128_rmsnorm_to_projection_bridge_verifier_exists": True,
        "partial_d128_rmsnorm_to_projection_bridge_local_roundtrip_proof_constructed": True,
        "partial_d128_rmsnorm_to_projection_bridge_checked_in_proof_artifact_exists": False,
        "partial_parameterized_residual_add_proof_exists": True,
        "partial_parameterized_residual_add_verifier_exists": True,
        "partial_parameterized_residual_add_local_roundtrip_proof_constructed": True,
        "partial_parameterized_residual_add_checked_in_proof_artifact_exists": False,
        "statement_relabeling_suite_exists": False,
        "proof_size_bytes": None,
        "verifier_time_ms": None,
        "blocked_before_metrics": True,
        "first_blocker": FIRST_BLOCKER,
        "required_toolchain": REQUIRED_TOOLCHAIN,
        "stable_toolchain_status": "not_supported_by_upstream_stwo_feature_gates",
    }
    d64_summary = require_object(d64_block_payload.get("summary"), "d64 block summary")
    d64_anchor = {
        "status": "GO_ANCHOR_ONLY",
        "claim_boundary": "working d64 slice proof chain, not a d128 proof route",
        "slice_count": d64_summary.get("slice_count"),
        "total_checked_rows": d64_summary.get("total_checked_rows"),
        "decision": d64_block_payload.get("decision"),
        "source": source_descriptor(D64_BLOCK_EVIDENCE, d64_block_payload),
        "slices": source_probe["d64_slices"],
    }
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "issue": ISSUE,
        "summary": summary,
        "target": {
            "target_id": TARGET_ID,
            "statement_kind": target_spec.get("statement_kind"),
            "width": target_spec.get("width"),
            "ff_dim": target_spec.get("ff_dim"),
            "required_backend_version": REQUIRED_BACKEND_VERSION,
            "target_commitment": target_spec.get("target_commitment"),
            "source": source_descriptor(TARGET_EVIDENCE, target_payload),
        },
        "d64_anchor": d64_anchor,
        "source_probe": source_probe,
        "backend_routes": routes,
        "proof_status": proof_status,
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    set_gate_commitment(payload)
    return payload


def _mutated_cases(payload: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    cases: list[tuple[str, str, dict[str, Any]]] = []

    def add(name: str, surface: str, mutator: Any) -> None:
        mutated = copy.deepcopy(payload)
        mutator(mutated)
        cases.append((name, surface, mutated))

    add("decision_promoted_to_go", "top_level", lambda p: p.__setitem__("decision", "GO_D128_PROOF_ARTIFACT"))
    add("target_width_drift", "target_spec", lambda p: p["target"].__setitem__("width", 64))
    add(
        "target_backend_version_drift",
        "target_spec",
        lambda p: p["target"].__setitem__("required_backend_version", "stwo-rmsnorm-swiglu-residual-d64-v2"),
    )
    add("local_proof_artifact_smuggled", "proof_status", lambda p: p["proof_status"].__setitem__("proof_artifact_exists", True))
    add("local_verifier_handle_smuggled", "proof_status", lambda p: p["proof_status"].__setitem__("verifier_handle_exists", True))
    add("proof_size_metric_smuggled", "metrics", lambda p: p["proof_status"].__setitem__("proof_size_bytes", 1_234_567))
    add("verifier_time_metric_smuggled", "metrics", lambda p: p["proof_status"].__setitem__("verifier_time_ms", 42.0))

    def promote_direct_route(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_native_modules")
        route["status"] = "GO"
        route["proof_artifact_exists"] = True
        route["verifier_handle_exists"] = True

    add("direct_d128_route_promoted", "backend_routes", promote_direct_route)

    def promote_d128_rmsnorm_public_row_route(p: dict[str, Any]) -> None:
        p["summary"]["d128_rmsnorm_public_row_route"] = "GO_D128_FULL_RMSNORM_BLOCK"
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_rmsnorm_public_row_air")
        route["status"] = "GO_D128_FULL_RMSNORM_BLOCK"
        route["proof_size_bytes"] = 4096

    add(
        "d128_rmsnorm_public_row_route_promoted",
        "backend_routes",
        promote_d128_rmsnorm_public_row_route,
    )
    add(
        "partial_d128_rmsnorm_public_row_proof_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_rmsnorm_public_row_proof_exists", False),
    )
    add(
        "partial_d128_rmsnorm_public_row_verifier_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_rmsnorm_public_row_verifier_exists", False),
    )
    add(
        "partial_d128_rmsnorm_public_row_local_roundtrip_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_rmsnorm_public_row_local_roundtrip_proof_constructed",
            False,
        ),
    )
    add(
        "partial_d128_rmsnorm_public_row_checked_in_artifact_smuggled",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_rmsnorm_public_row_checked_in_proof_artifact_exists",
            True,
        ),
    )

    def promote_d128_bridge_route(p: dict[str, Any]) -> None:
        p["summary"]["d128_rmsnorm_to_projection_bridge_route"] = "GO_D128_FULL_BRIDGE_BLOCK"
        route = next(
            row
            for row in p["backend_routes"]
            if row["route"] == "direct_d128_rmsnorm_to_projection_bridge_air"
        )
        route["status"] = "GO_D128_FULL_BRIDGE_BLOCK"
        route["proof_size_bytes"] = 4096

    add(
        "d128_rmsnorm_to_projection_bridge_route_promoted",
        "backend_routes",
        promote_d128_bridge_route,
    )
    add(
        "partial_d128_rmsnorm_to_projection_bridge_proof_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_rmsnorm_to_projection_bridge_proof_exists",
            False,
        ),
    )
    add(
        "partial_d128_rmsnorm_to_projection_bridge_verifier_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_rmsnorm_to_projection_bridge_verifier_exists",
            False,
        ),
    )
    add(
        "partial_d128_rmsnorm_to_projection_bridge_local_roundtrip_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_rmsnorm_to_projection_bridge_local_roundtrip_proof_constructed",
            False,
        ),
    )
    add(
        "partial_d128_rmsnorm_to_projection_bridge_checked_in_artifact_smuggled",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_rmsnorm_to_projection_bridge_checked_in_proof_artifact_exists",
            True,
        ),
    )

    def promote_full_block_parameterized_route(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "parameterized_transformer_block_air")
        route["status"] = "GO"
        route["missing_symbols"] = []
        route["proof_artifact_exists"] = True
        route["verifier_handle_exists"] = True

    add("full_block_parameterized_route_promoted", "backend_routes", promote_full_block_parameterized_route)
    add("d64_anchor_removed", "d64_anchor", lambda p: p.__setitem__("d64_anchor", {"status": "MISSING"}))

    def remove_missing_module(p: dict[str, Any]) -> None:
        p["source_probe"]["missing_d128_modules"] = p["source_probe"]["missing_d128_modules"][1:]
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_native_modules")
        route["missing_modules"] = route["missing_modules"][1:]

    add("missing_module_removed", "source_probe", remove_missing_module)

    def remove_hardcoded_marker(p: dict[str, Any]) -> None:
        p["source_probe"]["d64_hardcoded_markers"][0]["markers"] = []
        route = next(row for row in p["backend_routes"] if row["route"] == "lift_existing_d64_modules_by_metadata")
        route["hardcoded_markers"][0]["markers"] = []

    add("d64_hardcoded_marker_removed", "source_probe", remove_hardcoded_marker)
    add("non_claim_removed", "claim_boundary", lambda p: p["non_claims"].remove("not a full local d128 transformer-block proof artifact"))
    add("mutation_case_accepted", "mutation_harness", lambda p: p["summary"].__setitem__("mutation_cases", 0))
    return cases


def mutation_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, (mutation, surface, mutated) in enumerate(_mutated_cases(payload)):
        try:
            validate_payload(mutated, require_mutations=False)
        except D128BackendSpikeError as err:
            error = str(err) or f"{err.__class__.__name__} with empty message"
            results.append(
                {
                    "index": index,
                    "mutation": mutation,
                    "surface": surface,
                    "mutated_accepted": False,
                    "rejected": True,
                    "rejection_layer": surface,
                    "error": error,
                }
            )
        except Exception as err:  # noqa: BLE001 - harness bugs must fail the gate.
            raise RuntimeError(
                f"mutation harness failed for {mutation}: {err.__class__.__name__}: {err}"
            ) from err
        else:
            results.append(
                {
                    "index": index,
                    "mutation": mutation,
                    "surface": surface,
                    "mutated_accepted": True,
                    "rejected": False,
                    "rejection_layer": surface,
                    "error": "mutation was accepted",
                }
            )
    return results


def build_gate_result() -> dict[str, Any]:
    payload = build_payload()
    cases = mutation_cases(payload)
    payload["mutation_inventory"] = expected_mutation_inventory()
    payload["cases"] = cases
    payload["case_count"] = len(cases)
    payload["all_mutations_rejected"] = all(case["rejected"] for case in cases)
    payload["summary"]["mutations_rejected"] = sum(1 for case in cases if case["rejected"])
    set_gate_commitment(payload)
    validate_payload(payload)
    return payload


def validate_payload(payload: Any, *, require_mutations: bool = True) -> None:
    data = require_object(payload, "payload")
    expect_equal(data.get("schema"), SCHEMA, "schema")
    expect_equal(data.get("decision"), DECISION, "decision")
    expect_equal(data.get("result"), RESULT, "result")
    expect_equal(data.get("issue"), ISSUE, "issue")
    summary = require_object(data.get("summary"), "summary")
    expect_equal(summary.get("target_width"), TARGET_WIDTH, "summary target width")
    expect_equal(summary.get("target_ff_dim"), TARGET_FF_DIM, "summary target ff_dim")
    expect_equal(summary.get("first_blocker"), FIRST_BLOCKER, "summary first blocker")
    expect_equal(
        summary.get("direct_d128_route"),
        "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING",
        "summary direct d128 route",
    )
    expect_equal(
        summary.get("d128_rmsnorm_public_row_route"),
        "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
        "summary d128 RMSNorm public-row route",
    )
    expect_equal(
        summary.get("d128_rmsnorm_to_projection_bridge_route"),
        "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        "summary d128 RMSNorm-to-projection bridge route",
    )
    expect_equal(
        summary.get("parameterized_residual_add_route"),
        "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "summary parameterized residual-add route",
    )
    expect_equal(
        summary.get("parameterized_full_block_route"),
        "NO_GO_FULL_BLOCK_SLICES_MISSING",
        "summary parameterized full-block route",
    )
    expect_equal(summary.get("blocked_before_metrics"), True, "summary blocked-before-metrics")
    expect_equal(summary.get("mutation_cases"), len(EXPECTED_MUTATION_INVENTORY), "summary mutation count")

    target = require_object(data.get("target"), "target")
    expect_equal(target.get("target_id"), TARGET_ID, "target id")
    expect_equal(target.get("width"), TARGET_WIDTH, "target width")
    expect_equal(target.get("ff_dim"), TARGET_FF_DIM, "target ff_dim")
    expect_equal(target.get("required_backend_version"), REQUIRED_BACKEND_VERSION, "target backend version")

    d64_anchor = require_object(data.get("d64_anchor"), "d64 anchor")
    expect_equal(d64_anchor.get("status"), "GO_ANCHOR_ONLY", "d64 anchor status")
    expect_equal(d64_anchor.get("slice_count"), 6, "d64 anchor slice count")
    slices = require_list(d64_anchor.get("slices"), "d64 anchor slices")
    expect_equal(len(slices), len(D64_PROOF_SLICES), "d64 anchor slice list length")

    source_probe = require_object(data.get("source_probe"), "source probe")
    expect_equal(
        source_probe.get("missing_d128_modules"),
        list(EXPECTED_D128_MODULES),
        "missing d128 module inventory",
    )
    expect_equal(
        source_probe.get("missing_d128_export_symbols"),
        list(EXPECTED_D128_EXPORT_SYMBOLS),
        "missing d128 export inventory",
    )
    rmsnorm_probe = require_object(
        source_probe.get("d128_rmsnorm_public_row"),
        "d128 RMSNorm public-row probe",
    )
    expect_equal(
        rmsnorm_probe.get("status"),
        "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
        "d128 RMSNorm public-row status",
    )
    expect_equal(
        rmsnorm_probe.get("present_symbols"),
        list(D128_RMSNORM_SYMBOLS),
        "present d128 RMSNorm public-row symbol inventory",
    )
    rmsnorm_statement_commitment = rmsnorm_probe.get("statement_commitment")
    rmsnorm_public_instance_commitment = rmsnorm_probe.get("public_instance_commitment")
    rmsnorm_output_row_commitment = rmsnorm_probe.get("rmsnorm_output_row_commitment")
    expect_equal(
        rmsnorm_statement_commitment,
        D128_BRIDGE_GATE.SOURCE_RMSNORM_STATEMENT_COMMITMENT,
        "d128 RMSNorm public-row statement commitment",
    )
    expect_equal(
        rmsnorm_public_instance_commitment,
        D128_BRIDGE_GATE.SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT,
        "d128 RMSNorm public-row public-instance commitment",
    )
    expect_equal(
        rmsnorm_output_row_commitment,
        D128_BRIDGE_GATE.SOURCE_RMSNORM_OUTPUT_ROW_COMMITMENT,
        "d128 RMSNorm public-row output-row commitment",
    )
    bridge_probe = require_object(
        source_probe.get("d128_rmsnorm_to_projection_bridge"),
        "d128 RMSNorm-to-projection bridge probe",
    )
    expect_equal(
        bridge_probe.get("status"),
        "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        "d128 RMSNorm-to-projection bridge status",
    )
    expect_equal(
        bridge_probe.get("present_symbols"),
        list(D128_BRIDGE_SYMBOLS),
        "present d128 RMSNorm-to-projection bridge symbol inventory",
    )
    expect_equal(
        bridge_probe.get("projection_input_relabels_full_output"),
        False,
        "d128 RMSNorm-to-projection bridge relabel guard",
    )
    bridge_projection_input_commitment = require_commitment(
        bridge_probe.get("projection_input_row_commitment"),
        "d128 RMSNorm-to-projection bridge projection-input commitment",
    )
    expect_equal(
        bridge_projection_input_commitment,
        D128_BRIDGE_GATE.PROJECTION_INPUT_ROW_COMMITMENT,
        "d128 RMSNorm-to-projection bridge authoritative projection-input commitment",
    )
    expect_equal(
        bridge_probe.get("source_rmsnorm_statement_commitment"),
        rmsnorm_statement_commitment,
        "bridge source RMSNorm statement commitment",
    )
    expect_equal(
        bridge_probe.get("source_rmsnorm_public_instance_commitment"),
        rmsnorm_public_instance_commitment,
        "bridge source RMSNorm public-instance commitment",
    )
    expect_equal(
        bridge_probe.get("source_rmsnorm_output_row_commitment"),
        rmsnorm_output_row_commitment,
        "bridge source RMSNorm output row commitment",
    )
    residual_probe = require_object(
        source_probe.get("parameterized_residual_add"),
        "parameterized residual-add probe",
    )
    expect_equal(
        residual_probe.get("status"),
        "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "parameterized residual-add status",
    )
    expect_equal(
        residual_probe.get("present_symbols"),
        list(PARAMETERIZED_RESIDUAL_ADD_SYMBOLS),
        "present parameterized residual-add symbol inventory",
    )
    expect_equal(
        source_probe.get("missing_parameterized_full_block_symbols"),
        list(MISSING_PARAMETERIZED_FULL_BLOCK_SYMBOLS),
        "missing parameterized full-block symbol inventory",
    )
    hardcoded = require_list(source_probe.get("d64_hardcoded_markers"), "d64 hardcoded markers")
    expect_equal(len(hardcoded), len(D64_HARDCODE_MARKERS), "hardcoded marker file count")
    for record in hardcoded:
        record = require_object(record, "hardcoded marker")
        path = record.get("path")
        if path not in D64_HARDCODE_MARKERS:
            raise D128BackendSpikeError(f"unexpected hardcoded marker path: {path}")
        expect_equal(record.get("markers"), list(D64_HARDCODE_MARKERS[path]), f"{path} hardcoded markers")

    routes = require_list(data.get("backend_routes"), "backend routes")
    route_by_name = {require_object(route, "backend route").get("route"): route for route in routes}
    expected_routes = {
        "existing_d64_slice_chain",
        "direct_d128_native_modules",
        "direct_d128_rmsnorm_public_row_air",
        "direct_d128_rmsnorm_to_projection_bridge_air",
        "lift_existing_d64_modules_by_metadata",
        "parameterized_vector_residual_add_air",
        "parameterized_transformer_block_air",
        "d128_metrics_and_relabeling_suite",
    }
    if set(route_by_name) != expected_routes:
        raise D128BackendSpikeError("backend route inventory mismatch")
    expect_equal(route_by_name["existing_d64_slice_chain"].get("status"), "GO_ANCHOR_ONLY", "d64 anchor route status")
    expect_equal(
        route_by_name["direct_d128_native_modules"].get("status"),
        "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING",
        "direct d128 route status",
    )
    expect_equal(
        route_by_name["direct_d128_rmsnorm_public_row_air"].get("status"),
        "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
        "direct d128 RMSNorm public-row route status",
    )
    expect_equal(
        route_by_name["direct_d128_rmsnorm_to_projection_bridge_air"].get("status"),
        "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        "direct d128 RMSNorm-to-projection bridge route status",
    )
    expect_equal(
        route_by_name["direct_d128_rmsnorm_to_projection_bridge_air"].get("source_rmsnorm_statement_commitment"),
        rmsnorm_statement_commitment,
        "direct d128 RMSNorm-to-projection bridge route source statement commitment",
    )
    expect_equal(
        route_by_name["direct_d128_rmsnorm_to_projection_bridge_air"].get(
            "source_rmsnorm_public_instance_commitment"
        ),
        rmsnorm_public_instance_commitment,
        "direct d128 RMSNorm-to-projection bridge route source public-instance commitment",
    )
    expect_equal(
        route_by_name["direct_d128_rmsnorm_to_projection_bridge_air"].get("source_rmsnorm_output_row_commitment"),
        rmsnorm_output_row_commitment,
        "direct d128 RMSNorm-to-projection bridge route source output-row commitment",
    )
    route_projection_input_commitment = require_commitment(
        route_by_name["direct_d128_rmsnorm_to_projection_bridge_air"].get(
            "projection_input_row_commitment"
        ),
        "direct d128 RMSNorm-to-projection bridge route projection-input commitment",
    )
    expect_equal(
        route_projection_input_commitment,
        bridge_projection_input_commitment,
        "direct d128 RMSNorm-to-projection bridge route projection-input commitment",
    )
    if route_projection_input_commitment == D128_BRIDGE_GATE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT:
        raise D128BackendSpikeError(
            "direct d128 RMSNorm-to-projection bridge route projection-input commitment relabeled as full output"
        )
    expect_equal(
        route_by_name["parameterized_vector_residual_add_air"].get("status"),
        "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "parameterized residual-add route status",
    )
    expect_equal(
        route_by_name["parameterized_transformer_block_air"].get("status"),
        "NO_GO_FULL_BLOCK_SLICES_MISSING",
        "parameterized full-block route status",
    )
    for raw_route in routes:
        route_obj = require_object(raw_route, "backend route")
        if route_obj["route"] == "existing_d64_slice_chain":
            continue
        if route_obj["route"] in {
            "direct_d128_rmsnorm_public_row_air",
            "direct_d128_rmsnorm_to_projection_bridge_air",
            "parameterized_vector_residual_add_air",
        }:
            expect_equal(route_obj.get("target_width"), TARGET_WIDTH, f"{route_obj['route']} target width")
            expect_equal(route_obj.get("proof_artifact_exists"), True, f"{route_obj['route']} proof artifact")
            expect_equal(route_obj.get("verifier_handle_exists"), True, f"{route_obj['route']} verifier handle")
            expect_equal(
                route_obj.get("local_roundtrip_proof_constructed"),
                True,
                f"{route_obj['route']} local proof roundtrip",
            )
            expect_equal(
                route_obj.get("checked_in_proof_artifact_exists"),
                False,
                f"{route_obj['route']} checked-in proof artifact",
            )
        else:
            expect_equal(route_obj.get("target_width"), TARGET_WIDTH, f"{route_obj['route']} target width")
            expect_equal(route_obj.get("proof_artifact_exists"), False, f"{route_obj['route']} proof artifact")
            expect_equal(route_obj.get("verifier_handle_exists"), False, f"{route_obj['route']} verifier handle")
        if route_obj.get("proof_size_bytes") is not None:
            raise D128BackendSpikeError("proof-size metric must remain absent before d128 proof exists")
        if route_obj.get("verifier_time_ms") is not None:
            raise D128BackendSpikeError("verifier-time metric must remain absent before d128 proof exists")

    proof_status = require_object(data.get("proof_status"), "proof status")
    expect_equal(proof_status.get("proof_artifact_exists"), False, "proof artifact exists")
    expect_equal(proof_status.get("verifier_handle_exists"), False, "verifier handle exists")
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_public_row_proof_exists"),
        True,
        "partial d128 RMSNorm public-row proof exists",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_public_row_verifier_exists"),
        True,
        "partial d128 RMSNorm public-row verifier exists",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_public_row_local_roundtrip_proof_constructed"),
        True,
        "partial d128 RMSNorm public-row local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_public_row_checked_in_proof_artifact_exists"),
        False,
        "partial d128 RMSNorm public-row checked-in proof artifact",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_to_projection_bridge_proof_exists"),
        True,
        "partial d128 RMSNorm-to-projection bridge proof exists",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_to_projection_bridge_verifier_exists"),
        True,
        "partial d128 RMSNorm-to-projection bridge verifier exists",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_to_projection_bridge_local_roundtrip_proof_constructed"),
        True,
        "partial d128 RMSNorm-to-projection bridge local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_d128_rmsnorm_to_projection_bridge_checked_in_proof_artifact_exists"),
        False,
        "partial d128 RMSNorm-to-projection bridge checked-in proof artifact",
    )
    expect_equal(
        proof_status.get("partial_parameterized_residual_add_proof_exists"),
        True,
        "partial residual-add proof exists",
    )
    expect_equal(
        proof_status.get("partial_parameterized_residual_add_verifier_exists"),
        True,
        "partial residual-add verifier exists",
    )
    expect_equal(
        proof_status.get("partial_parameterized_residual_add_local_roundtrip_proof_constructed"),
        True,
        "partial residual-add local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_parameterized_residual_add_checked_in_proof_artifact_exists"),
        False,
        "partial residual-add checked-in proof artifact",
    )
    expect_equal(proof_status.get("statement_relabeling_suite_exists"), False, "relabeling suite exists")
    expect_equal(proof_status.get("proof_size_bytes"), None, "proof size")
    expect_equal(proof_status.get("verifier_time_ms"), None, "verifier time")
    expect_equal(proof_status.get("blocked_before_metrics"), True, "blocked before metrics")
    expect_equal(proof_status.get("required_toolchain"), REQUIRED_TOOLCHAIN, "required toolchain")

    if set(data.get("non_claims", [])) != set(NON_CLAIMS):
        raise D128BackendSpikeError("non-claims inventory mismatch")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise D128BackendSpikeError("validation command inventory mismatch")

    if require_mutations:
        if data.get("mutation_inventory") != expected_mutation_inventory():
            raise D128BackendSpikeError("mutation inventory mismatch")
        cases = require_list(data.get("cases"), "mutation cases")
        expect_equal(data.get("case_count"), len(EXPECTED_MUTATION_INVENTORY), "case count")
        expect_equal(len(cases), len(EXPECTED_MUTATION_INVENTORY), "mutation case length")
        expect_equal(data.get("all_mutations_rejected"), True, "all mutations rejected")
        seen = set()
        for case in cases:
            case = require_object(case, "mutation case")
            mutation = case.get("mutation")
            if mutation in seen:
                raise D128BackendSpikeError("duplicate mutation case")
            seen.add(mutation)
            if not case.get("rejected"):
                raise D128BackendSpikeError(f"mutation was accepted: {mutation}")
            if not case.get("error"):
                raise D128BackendSpikeError(f"mutation case error must be non-empty: {mutation}")
        expect_equal(seen, {name for name, _surface in EXPECTED_MUTATION_INVENTORY}, "mutation case set")
        expected_gate_commitment = blake2b_commitment(gate_commitment_payload(data), GATE_COMMITMENT_DOMAIN)
        expect_equal(data.get("gate_commitment"), expected_gate_commitment, "gate commitment")


def rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for route in payload["backend_routes"]:
        rows.append({column: route.get(column) for column in TSV_COLUMNS})
    return rows


def mutation_rows_for_tsv(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [{column: case.get(column) for column in MUTATION_TSV_COLUMNS} for case in payload["cases"]]


def _assert_repo_output_path(path: pathlib.Path) -> pathlib.Path:
    if path.is_symlink():
        raise D128BackendSpikeError(f"output path must not be a symlink: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as err:
        raise D128BackendSpikeError(f"output path escapes repository: {path}") from err
    if resolved.exists() and resolved.is_dir():
        raise D128BackendSpikeError(f"output path must not be a directory: {path}")
    parent = resolved.parent
    if parent.exists() and not parent.is_dir():
        raise D128BackendSpikeError(f"output parent is not a directory: {parent}")
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


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
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


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    validate_payload(payload)
    written: list[pathlib.Path] = []
    if json_path is not None:
        text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
        _atomic_write_text(json_path, text)
        written.append(json_path.resolve())
    if tsv_path is not None:
        from io import StringIO

        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_for_tsv(payload))
        buffer.write("\n")
        mutation_writer = csv.DictWriter(
            buffer,
            fieldnames=MUTATION_TSV_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
        )
        mutation_writer.writeheader()
        mutation_writer.writerows(mutation_rows_for_tsv(payload))
        _atomic_write_text(tsv_path, buffer.getvalue())
        written.append(tsv_path.resolve())
    _fsync_parent_directories(written)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-json", type=pathlib.Path, default=None)
    parser.add_argument("--write-tsv", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    payload = build_gate_result()
    write_outputs(payload, args.write_json, args.write_tsv)
    if args.write_json is None and args.write_tsv is None:
        print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
