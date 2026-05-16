#!/usr/bin/env python3
"""Classify the attention-derived d128 native RMSNorm-MLP proof route."""

from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
import json
import os
import pathlib
import sys
import tempfile
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"

DERIVED_RMSNORM = EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
DERIVED_NATIVE_RMSNORM_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json"
)
DERIVED_NATIVE_BRIDGE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json"
)
DERIVED_NATIVE_BRIDGE_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json"
)
DERIVED_NATIVE_GATE_VALUE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json"
)
DERIVED_NATIVE_GATE_VALUE_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json"
)
DERIVED_NATIVE_ACTIVATION = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json"
)
DERIVED_NATIVE_ACTIVATION_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json"
)
DERIVED_NATIVE_DOWN = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-down-projection-proof-2026-05.json"
)
DERIVED_NATIVE_DOWN_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json"
)
DERIVED_NATIVE_RESIDUAL = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-residual-add-proof-2026-05.json"
)
DERIVED_NATIVE_RESIDUAL_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json"
)
DERIVED_FUSED_INPUT = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json"
)
DERIVED_FUSED_ENVELOPE = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"
)
DERIVED_FUSED_ACCOUNTING = (
    EVIDENCE_DIR / "zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json"
)
DERIVED_PROJECTION = EVIDENCE_DIR / "zkai-attention-derived-d128-projection-boundary-2026-05.json"
DERIVED_RESIDUAL = EVIDENCE_DIR / "zkai-attention-derived-d128-residual-add-2026-05.json"
DERIVED_CHAIN = EVIDENCE_DIR / "zkai-attention-derived-d128-block-statement-chain-2026-05.json"
CURRENT_MLP_FUSED_GATE = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json"
CURRENT_MLP_FUSED_INPUT = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json"
CURRENT_MLP_FUSED_ENVELOPE = EVIDENCE_DIR / "zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"
JSON_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv"

SCHEMA = "zkai-attention-derived-d128-native-mlp-proof-route-gate-v1"
DECISION = "GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_REGENERATED"
RESULT = "GO_DERIVED_NATIVE_RMSNORM_MLP_FUSED_PROOF_EXISTS_WITH_EXACT_SIX_BASELINE_SAVING"
VALUE_CHAIN_STATUS = "GO_ATTENTION_DERIVED_D128_VALUE_CONNECTED_STATEMENT_CHAIN"
NATIVE_ROUTE_STATUS = "GO_DERIVED_COMPONENT_INPUTS_NATIVE_SHAPE_AND_FUSED_PROOF_REGENERATED"
FIRST_BLOCKER = (
    "the attention-derived RMSNorm-MLP fused proof now exists, but attention arithmetic is not yet "
    "inside the same native proof object"
)
PAYLOAD_DOMAIN = "ptvm:zkai:attention-derived-d128:native-mlp-proof-route:v1"
EXPECTED_DERIVED_INPUT_COMMITMENT = (
    "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35"
)
EXPECTED_CURRENT_INPUT_COMMITMENT = (
    "blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78"
)
EXPECTED_NATIVE_ACTIVATION_STATEMENT_COMMITMENT = (
    "blake2b-256:6fe34d1b0da8ad503ee3ac83b42199fc242110f0e81cd9353f7ba71ceea90738"
)
EXPECTED_NATIVE_RMSNORM_STATEMENT_COMMITMENT = (
    "blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d"
)
EXPECTED_NATIVE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:21316dfa0e32f91879bf13b85f99e16db0aa4c6e5f91c0dfc106f300c0c50fff"
)
EXPECTED_NATIVE_RMSNORM_OUTPUT_ROW_COMMITMENT = (
    "blake2b-256:fbc611c011d2209476aca2055f5f9abe0d6cda12bd0f6fabeec7d1657ce1e1f9"
)
EXPECTED_NATIVE_BRIDGE_STATEMENT_COMMITMENT = (
    "blake2b-256:85a4f027ea7570b388a585fb53cb9c66a7358e2431730e044e39f4bdea859abf"
)
EXPECTED_NATIVE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:7939a60307f2b0f078e55430faf45cde8598158dd2090c5d65bf4fd72e436f4b"
)
EXPECTED_NATIVE_BRIDGE_PROJECTION_INPUT_ROW_COMMITMENT = (
    "blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba"
)
EXPECTED_NATIVE_GATE_VALUE_STATEMENT_COMMITMENT = (
    "blake2b-256:e6dca036c80385d2d47c3953cb4aca15ed058b2a0ac3fc2596767a0658b30d6c"
)
EXPECTED_NATIVE_GATE_VALUE_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:a24402af117710fca3b0100bc8480ba03e73e4cb86914ba64f45bc785791d51e"
)
EXPECTED_NATIVE_GATE_VALUE_MUL_ROW_COMMITMENT = (
    "blake2b-256:f8811ca51b98f6661e59c9f0fbbed1a6a96a6cba35f39cbca4ee443a87c89d90"
)
EXPECTED_NATIVE_GATE_OUTPUT_COMMITMENT = (
    "blake2b-256:d0d681a8db0c32b7c47e24425cda29b93512d40e46d6b9b9aafdb7cddd2880d8"
)
EXPECTED_NATIVE_VALUE_OUTPUT_COMMITMENT = (
    "blake2b-256:b63e4d4fd6f1c3ba867f4cce7c332deafa67f003d2208bbbe1013b075b7b4781"
)
EXPECTED_NATIVE_GATE_VALUE_OUTPUT_COMMITMENT = (
    "blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2"
)
EXPECTED_NATIVE_ACTIVATION_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:c1848a2bbdb4d8f897cd4a6764bc8b74c1db0bcd8441828ab2cde1e68310b4fb"
)
EXPECTED_NATIVE_ACTIVATION_HIDDEN_COMMITMENT = (
    "blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4"
)
EXPECTED_NATIVE_DOWN_STATEMENT_COMMITMENT = (
    "blake2b-256:3ca2a06054a8ae8a9526bce62a4bc3a91e6f302fc3cb4866d7e2dc2afbf5f23e"
)
EXPECTED_NATIVE_DOWN_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:a4c0e39d34dce67783230532ee7031449b1d2aec9add232ef40f43073e372735"
)
EXPECTED_NATIVE_DOWN_RESIDUAL_DELTA_COMMITMENT = (
    "blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec"
)
EXPECTED_NATIVE_DOWN_MUL_ROW_COMMITMENT = (
    "blake2b-256:cd051c1ff66c5b413203b6d612d7c70ff14a0be7723c214c2808b12625fcc278"
)
EXPECTED_NATIVE_RESIDUAL_STATEMENT_COMMITMENT = (
    "blake2b-256:106bf2581e2588d8ed28f31d93438ba0f546a752d743bea533df8640a6048c5d"
)
EXPECTED_NATIVE_RESIDUAL_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:35d93e7086d773fdba30b455374533df6271b1d98d6b35418f1af0d250be8ee8"
)
EXPECTED_NATIVE_RESIDUAL_OUTPUT_COMMITMENT = (
    "blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9"
)
EXPECTED_NATIVE_RESIDUAL_ROW_COMMITMENT = (
    "blake2b-256:e1128497a36a68aa3c1a769c7368b3d7b302140ca4535f03e02c5084b54fffcf"
)
EXPECTED_DERIVED_FUSED_STATEMENT_COMMITMENT = (
    "blake2b-256:ed6524cc9f5da4b614e14b6e6c32b9e5170e089ee2ea50872b8ff90f2748ffe3"
)
EXPECTED_DERIVED_FUSED_PUBLIC_INSTANCE_COMMITMENT = (
    "blake2b-256:281440678289f1a5ab4ca85cf07aaf831ae6e4f881c00f33500dd67e535f2bee"
)

REQUIRED_DERIVED_FUSED_ARTIFACTS = (
    "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json",
    "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json",
)
MISSING_MATCHED_SEPARATE_ENVELOPES = (
)
EXPECTED_ACCOUNTING_PATHS = (
    "zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json",
    "zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json",
    "zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json",
    "zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json",
    "zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json",
    "zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json",
)

COMPONENT_SPECS = (
    {
        "component_id": "rmsnorm_public_rows",
        "path": DERIVED_RMSNORM,
        "payload_key": "rmsnorm_public_row_payload",
        "required_native_schema": "zkai-d128-native-rmsnorm-public-row-air-proof-input-v3",
        "required_native_decision": "GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "rmsnorm_projection_bridge",
        "path": DERIVED_NATIVE_BRIDGE,
        "payload_key": None,
        "required_native_schema": "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "gate_value_projection",
        "path": DERIVED_NATIVE_GATE_VALUE,
        "payload_key": None,
        "required_native_schema": "zkai-d128-gate-value-projection-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_GATE_VALUE_PROJECTION_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "activation_swiglu",
        "path": DERIVED_NATIVE_ACTIVATION,
        "payload_key": None,
        "required_native_schema": "zkai-d128-activation-swiglu-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_ACTIVATION_SWIGLU_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "down_projection",
        "path": DERIVED_NATIVE_DOWN,
        "payload_key": None,
        "required_native_schema": "zkai-d128-down-projection-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
    {
        "component_id": "residual_add",
        "path": DERIVED_NATIVE_RESIDUAL,
        "payload_key": None,
        "required_native_schema": "zkai-d128-residual-add-air-proof-input-v1",
        "required_native_decision": "GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF",
        "required_fields": ("validation_commands", "proof_verifier_hardening", "non_claims"),
    },
)

NON_CLAIMS = [
    "not attention plus MLP in one native proof object",
    "not a full transformer block proof",
    "not a NANOZK benchmark win",
    "not a matched external zkML benchmark",
    "not timing evidence",
    "not recursion or proof-carrying data",
    "not production-ready zkML",
]

VALIDATION_COMMANDS = [
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- build-input docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_public_row_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_public_row_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_to_projection_bridge_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_to_projection_bridge_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_residual_add_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json",
    "python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv",
    "python3 -m py_compile scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py scripts/tests/test_zkai_attention_derived_d128_native_mlp_proof_route_gate.py",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate",
    "python3 scripts/research_issue_lint.py --repo-root .",
    "python3 scripts/paper/paper_preflight.py --repo-root .",
    "git diff --check",
    "just gate-fast",
    "just gate",
]

CORE_KEYS = {
    "schema",
    "decision",
    "result",
    "value_chain_status",
    "native_route_status",
    "first_blocker",
    "source_artifacts",
    "component_input_frontier",
    "required_derived_fused_artifacts",
    "missing_matched_separate_envelopes",
    "comparison",
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
    "value_chain_status",
    "native_route_status",
    "derived_input_activation_commitment",
    "current_mlp_input_activation_commitment",
    "value_connected_chain_rows",
    "current_mlp_fused_rows",
    "row_ratio",
    "current_mlp_fused_typed_bytes",
    "current_mlp_typed_saving_vs_separate_bytes",
    "derived_fused_proof_bytes",
    "derived_fused_envelope_bytes",
    "derived_fused_typed_bytes",
    "available_separate_component_count",
    "available_separate_typed_bytes",
    "typed_saving_vs_available_separate_bytes",
    "typed_ratio_vs_available_separate",
    "native_compatible_components",
    "native_incompatible_components",
    "derived_native_rmsnorm_proof_bytes",
    "derived_native_rmsnorm_envelope_bytes",
    "derived_native_bridge_proof_bytes",
    "derived_native_bridge_envelope_bytes",
    "derived_native_gate_value_proof_bytes",
    "derived_native_gate_value_envelope_bytes",
    "derived_native_activation_proof_bytes",
    "derived_native_activation_envelope_bytes",
    "derived_native_down_proof_bytes",
    "derived_native_down_envelope_bytes",
    "derived_native_residual_proof_bytes",
    "derived_native_residual_envelope_bytes",
)


class NativeMlpProofRouteError(ValueError):
    pass


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as err:
        raise NativeMlpProofRouteError(f"invalid JSON value: {err}") from err


def pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise NativeMlpProofRouteError(f"invalid JSON value: {err}") from err


def payload_commitment(payload: dict[str, Any]) -> str:
    material = {key: value for key, value in payload.items() if key != "payload_commitment"}
    return "sha256:" + hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def refresh_payload_commitment(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = payload_commitment(payload)


def blake2b_commitment(value: Any, domain: str) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(domain.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(value))
    return "blake2b-256:" + digest.hexdigest()


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeMlpProofRouteError(f"{label} must be object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeMlpProofRouteError(f"{label} must be list")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeMlpProofRouteError(f"{label} must be non-empty string")
    return value


def _int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NativeMlpProofRouteError(f"{label} must be integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise NativeMlpProofRouteError(f"{label} must be boolean")
    return value


def _commitment(value: Any, label: str) -> str:
    text = _str(value, label)
    for prefix in ("blake2b-256:", "sha256:"):
        digest = text.removeprefix(prefix)
        if digest != text and len(digest) == 64 and all(char in "0123456789abcdef" for char in digest):
            return text
    raise NativeMlpProofRouteError(f"{label} must be a typed 32-byte commitment")


def _load_json(path: pathlib.Path, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink():
        raise NativeMlpProofRouteError(f"{label} must not be a symlink: {path}")
    try:
        raw = path.read_bytes()
    except OSError as err:
        raise NativeMlpProofRouteError(f"failed reading {label}: {path}") from err
    if len(raw) > 16 * 1024 * 1024:
        raise NativeMlpProofRouteError(f"{label} exceeds max bytes: {len(raw)}")
    try:
        payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise NativeMlpProofRouteError(f"failed parsing {label}: {path}: {err}") from err
    if not isinstance(payload, dict):
        raise NativeMlpProofRouteError(f"{label} must be JSON object")
    return payload, raw


def source_artifact(artifact_id: str, path: pathlib.Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def component_frontier_row(spec: dict[str, Any], source_payloads: dict[pathlib.Path, dict[str, Any]]) -> dict[str, Any]:
    payload_key = spec["payload_key"]
    payload = (
        source_payloads[spec["path"]]
        if payload_key is None
        else _dict(source_payloads[spec["path"]].get(payload_key), f"{spec['component_id']} payload")
    )
    missing = [field for field in spec["required_fields"] if field not in payload]
    schema = _str(payload.get("schema"), f"{spec['component_id']} schema")
    decision = _str(payload.get("decision"), f"{spec['component_id']} decision")
    schema_matches = schema == spec["required_native_schema"]
    decision_matches = decision == spec["required_native_decision"]
    compatible = schema_matches and decision_matches and not missing
    commitments = {
        key: value
        for key, value in payload.items()
        if key.endswith("_commitment") and isinstance(value, str) and value.startswith(("blake2b-256:", "sha256:"))
    }
    return {
        "component_id": spec["component_id"],
        "source_path": spec["path"].relative_to(ROOT).as_posix(),
        "payload_key": "root" if payload_key is None else payload_key,
        "schema": schema,
        "required_native_schema": spec["required_native_schema"],
        "schema_matches_native": schema_matches,
        "decision": decision,
        "required_native_decision": spec["required_native_decision"],
        "decision_matches_native": decision_matches,
        "missing_required_native_fields": missing,
        "native_component_input_status": "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE" if compatible else "NO_GO_NOT_CURRENT_NATIVE_COMPONENT_INPUT",
        "commitments": commitments,
    }


def accounting_typed_bytes(row: dict[str, Any], label: str) -> int:
    accounting = _dict(row.get("local_binary_accounting"), f"{label} local binary accounting")
    return _int(accounting.get("typed_size_estimate_bytes"), f"{label} typed bytes")


def accounting_group(row: dict[str, Any], label: str) -> dict[str, int]:
    accounting = _dict(row.get("local_binary_accounting"), f"{label} local binary accounting")
    group = _dict(accounting.get("grouped_reconstruction"), f"{label} grouped reconstruction")
    return {key: _int(group.get(key), f"{label} grouped {key}") for key in group}


def build_context() -> dict[str, Any]:
    paths = {
        DERIVED_RMSNORM,
        DERIVED_NATIVE_RMSNORM_ENVELOPE,
        DERIVED_NATIVE_BRIDGE,
        DERIVED_NATIVE_BRIDGE_ENVELOPE,
        DERIVED_NATIVE_GATE_VALUE,
        DERIVED_NATIVE_GATE_VALUE_ENVELOPE,
        DERIVED_NATIVE_ACTIVATION,
        DERIVED_NATIVE_ACTIVATION_ENVELOPE,
        DERIVED_NATIVE_DOWN,
        DERIVED_NATIVE_DOWN_ENVELOPE,
        DERIVED_NATIVE_RESIDUAL,
        DERIVED_NATIVE_RESIDUAL_ENVELOPE,
        DERIVED_FUSED_INPUT,
        DERIVED_FUSED_ENVELOPE,
        DERIVED_FUSED_ACCOUNTING,
        DERIVED_PROJECTION,
        DERIVED_RESIDUAL,
        DERIVED_CHAIN,
        CURRENT_MLP_FUSED_GATE,
        CURRENT_MLP_FUSED_INPUT,
        CURRENT_MLP_FUSED_ENVELOPE,
    }
    loaded: dict[pathlib.Path, dict[str, Any]] = {}
    raw_by_path: dict[pathlib.Path, bytes] = {}
    artifacts = []
    for path in sorted(paths):
        payload, raw = _load_json(path, path.name)
        loaded[path] = payload
        raw_by_path[path] = raw
        artifacts.append(source_artifact(path.stem, path, payload, raw))

    chain_summary = _dict(loaded[DERIVED_CHAIN].get("summary"), "derived chain summary")
    current_aggregate = _dict(loaded[CURRENT_MLP_FUSED_GATE].get("aggregate"), "current MLP aggregate")
    current_input = loaded[CURRENT_MLP_FUSED_INPUT]
    current_envelope = loaded[CURRENT_MLP_FUSED_ENVELOPE]
    native_rmsnorm_wrapper = loaded[DERIVED_RMSNORM]
    native_rmsnorm = _dict(
        native_rmsnorm_wrapper.get("rmsnorm_public_row_payload"),
        "derived native rmsnorm public-row payload",
    )
    native_rmsnorm_envelope = loaded[DERIVED_NATIVE_RMSNORM_ENVELOPE]
    native_bridge = loaded[DERIVED_NATIVE_BRIDGE]
    native_bridge_envelope = loaded[DERIVED_NATIVE_BRIDGE_ENVELOPE]
    native_gate_value = loaded[DERIVED_NATIVE_GATE_VALUE]
    native_gate_value_envelope = loaded[DERIVED_NATIVE_GATE_VALUE_ENVELOPE]
    native_activation = loaded[DERIVED_NATIVE_ACTIVATION]
    native_activation_envelope = loaded[DERIVED_NATIVE_ACTIVATION_ENVELOPE]
    native_down = loaded[DERIVED_NATIVE_DOWN]
    native_down_envelope = loaded[DERIVED_NATIVE_DOWN_ENVELOPE]
    native_residual = loaded[DERIVED_NATIVE_RESIDUAL]
    native_residual_envelope = loaded[DERIVED_NATIVE_RESIDUAL_ENVELOPE]
    derived_fused_input = loaded[DERIVED_FUSED_INPUT]
    derived_fused_envelope = loaded[DERIVED_FUSED_ENVELOPE]
    derived_fused_accounting = loaded[DERIVED_FUSED_ACCOUNTING]
    derived_input_commitment = _commitment(
        chain_summary.get("derived_input_activation_commitment"),
        "derived input activation commitment",
    )
    current_input_commitment = _commitment(
        current_input.get("input_activation_commitment"),
        "current MLP fused input activation commitment",
    )
    envelope_input_commitment = _commitment(
        _dict(current_envelope.get("input"), "current envelope input").get("input_activation_commitment"),
        "current envelope input activation commitment",
    )
    if derived_input_commitment != EXPECTED_DERIVED_INPUT_COMMITMENT:
        raise NativeMlpProofRouteError("derived input commitment drift")
    if current_input_commitment != EXPECTED_CURRENT_INPUT_COMMITMENT:
        raise NativeMlpProofRouteError("current MLP input commitment drift")
    if envelope_input_commitment != current_input_commitment:
        raise NativeMlpProofRouteError("current MLP envelope/input activation commitment mismatch")
    derived_fused_input_commitment = _commitment(
        derived_fused_input.get("input_activation_commitment"),
        "derived fused input activation commitment",
    )
    derived_fused_envelope_input = _dict(derived_fused_envelope.get("input"), "derived fused envelope input")
    if derived_fused_input_commitment != EXPECTED_DERIVED_INPUT_COMMITMENT:
        raise NativeMlpProofRouteError("derived fused input commitment drift")
    if derived_fused_envelope_input != derived_fused_input:
        raise NativeMlpProofRouteError("derived fused envelope/input mismatch")
    if derived_fused_envelope.get("proof_backend_version") != "stwo-d128-rmsnorm-mlp-fused-air-proof-v1":
        raise NativeMlpProofRouteError("derived fused proof backend version drift")
    if derived_fused_envelope.get("statement_version") != "zkai-d128-rmsnorm-mlp-fused-statement-v1":
        raise NativeMlpProofRouteError("derived fused statement version drift")
    if derived_fused_envelope.get("decision") != "GO_D128_RMSNORM_MLP_FUSED_AIR_PROOF":
        raise NativeMlpProofRouteError("derived fused proof decision drift")
    if derived_fused_input.get("statement_commitment") != EXPECTED_DERIVED_FUSED_STATEMENT_COMMITMENT:
        raise NativeMlpProofRouteError("derived fused statement commitment drift")
    if derived_fused_input.get("public_instance_commitment") != EXPECTED_DERIVED_FUSED_PUBLIC_INSTANCE_COMMITMENT:
        raise NativeMlpProofRouteError("derived fused public instance commitment drift")
    if derived_fused_input.get("input_activation_commitment") == current_input_commitment:
        raise NativeMlpProofRouteError("derived fused input relabeled as current MLP input")
    if _dict(native_rmsnorm_envelope.get("input"), "derived native RMSNorm envelope input") != native_rmsnorm:
        raise NativeMlpProofRouteError("derived native RMSNorm envelope/input mismatch")
    if native_rmsnorm_envelope.get("proof_backend_version") != "stwo-d128-rmsnorm-public-row-air-proof-v3":
        raise NativeMlpProofRouteError("derived native RMSNorm proof backend version drift")
    if native_rmsnorm_envelope.get("statement_version") != "zkai-d128-rmsnorm-public-row-statement-v2":
        raise NativeMlpProofRouteError("derived native RMSNorm statement version drift")
    if native_rmsnorm_envelope.get("decision") != "GO_PUBLIC_ROW_D128_RMSNORM_AIR_PROOF":
        raise NativeMlpProofRouteError("derived native RMSNorm proof decision drift")
    if _dict(native_bridge_envelope.get("input"), "derived native bridge envelope input") != native_bridge:
        raise NativeMlpProofRouteError("derived native bridge envelope/input mismatch")
    if native_bridge_envelope.get("proof_backend_version") != "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1":
        raise NativeMlpProofRouteError("derived native bridge proof backend version drift")
    if native_bridge_envelope.get("statement_version") != "zkai-d128-rmsnorm-to-projection-bridge-statement-v1":
        raise NativeMlpProofRouteError("derived native bridge statement version drift")
    if native_bridge_envelope.get("decision") != "GO_D128_RMSNORM_TO_PROJECTION_INPUT_BRIDGE_AIR_PROOF":
        raise NativeMlpProofRouteError("derived native bridge proof decision drift")
    if _dict(native_gate_value_envelope.get("input"), "derived native gate/value envelope input") != native_gate_value:
        raise NativeMlpProofRouteError("derived native gate/value envelope/input mismatch")
    if native_gate_value_envelope.get("proof_backend_version") != "stwo-d128-gate-value-projection-air-proof-v1":
        raise NativeMlpProofRouteError("derived native gate/value proof backend version drift")
    if native_gate_value_envelope.get("statement_version") != "zkai-d128-gate-value-projection-statement-v1":
        raise NativeMlpProofRouteError("derived native gate/value statement version drift")
    if native_gate_value_envelope.get("decision") != "GO_D128_GATE_VALUE_PROJECTION_AIR_PROOF":
        raise NativeMlpProofRouteError("derived native gate/value proof decision drift")
    if _dict(native_activation_envelope.get("input"), "derived native activation envelope input") != native_activation:
        raise NativeMlpProofRouteError("derived native activation envelope/input mismatch")
    if native_activation_envelope.get("proof_backend_version") != "stwo-d128-activation-swiglu-air-proof-v1":
        raise NativeMlpProofRouteError("derived native activation proof backend version drift")
    if native_activation_envelope.get("decision") != "GO_D128_ACTIVATION_SWIGLU_AIR_PROOF":
        raise NativeMlpProofRouteError("derived native activation proof decision drift")
    if _dict(native_down_envelope.get("input"), "derived native down envelope input") != native_down:
        raise NativeMlpProofRouteError("derived native down envelope/input mismatch")
    if native_down_envelope.get("proof_backend_version") != "stwo-d128-down-projection-air-proof-v1":
        raise NativeMlpProofRouteError("derived native down proof backend version drift")
    if native_down_envelope.get("decision") != "GO_D128_DOWN_PROJECTION_AIR_PROOF":
        raise NativeMlpProofRouteError("derived native down proof decision drift")
    if _dict(native_residual_envelope.get("input"), "derived native residual envelope input") != native_residual:
        raise NativeMlpProofRouteError("derived native residual envelope/input mismatch")
    if native_residual_envelope.get("proof_backend_version") != "stwo-d128-residual-add-air-proof-v1":
        raise NativeMlpProofRouteError("derived native residual proof backend version drift")
    if native_residual_envelope.get("decision") != "GO_D128_RESIDUAL_ADD_AIR_PROOF":
        raise NativeMlpProofRouteError("derived native residual proof decision drift")
    expected_commitments = (
        (
            native_rmsnorm.get("statement_commitment"),
            EXPECTED_NATIVE_RMSNORM_STATEMENT_COMMITMENT,
            "derived native RMSNorm statement_commitment",
        ),
        (
            native_rmsnorm.get("public_instance_commitment"),
            EXPECTED_NATIVE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT,
            "derived native RMSNorm public_instance_commitment",
        ),
        (
            native_rmsnorm.get("input_activation_commitment"),
            EXPECTED_DERIVED_INPUT_COMMITMENT,
            "derived native RMSNorm input_activation_commitment",
        ),
        (
            native_rmsnorm.get("rmsnorm_output_row_commitment"),
            EXPECTED_NATIVE_RMSNORM_OUTPUT_ROW_COMMITMENT,
            "derived native RMSNorm rmsnorm_output_row_commitment",
        ),
        (
            native_bridge.get("statement_commitment"),
            EXPECTED_NATIVE_BRIDGE_STATEMENT_COMMITMENT,
            "derived native bridge statement_commitment",
        ),
        (
            native_bridge.get("public_instance_commitment"),
            EXPECTED_NATIVE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
            "derived native bridge public_instance_commitment",
        ),
        (
            native_bridge.get("source_rmsnorm_statement_commitment"),
            EXPECTED_NATIVE_RMSNORM_STATEMENT_COMMITMENT,
            "derived native bridge source_rmsnorm_statement_commitment",
        ),
        (
            native_bridge.get("source_rmsnorm_public_instance_commitment"),
            EXPECTED_NATIVE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT,
            "derived native bridge source_rmsnorm_public_instance_commitment",
        ),
        (
            native_bridge.get("source_rmsnorm_output_row_commitment"),
            EXPECTED_NATIVE_RMSNORM_OUTPUT_ROW_COMMITMENT,
            "derived native bridge source_rmsnorm_output_row_commitment",
        ),
        (
            native_bridge.get("projection_input_row_commitment"),
            EXPECTED_NATIVE_BRIDGE_PROJECTION_INPUT_ROW_COMMITMENT,
            "derived native bridge projection_input_row_commitment",
        ),
        (
            native_gate_value.get("statement_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_STATEMENT_COMMITMENT,
            "derived native gate/value statement_commitment",
        ),
        (
            native_gate_value.get("public_instance_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_PUBLIC_INSTANCE_COMMITMENT,
            "derived native gate/value public_instance_commitment",
        ),
        (
            native_gate_value.get("source_bridge_statement_commitment"),
            EXPECTED_NATIVE_BRIDGE_STATEMENT_COMMITMENT,
            "derived native gate/value source_bridge_statement_commitment",
        ),
        (
            native_gate_value.get("source_bridge_public_instance_commitment"),
            EXPECTED_NATIVE_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
            "derived native gate/value source_bridge_public_instance_commitment",
        ),
        (
            native_gate_value.get("source_projection_input_row_commitment"),
            EXPECTED_NATIVE_BRIDGE_PROJECTION_INPUT_ROW_COMMITMENT,
            "derived native gate/value source_projection_input_row_commitment",
        ),
        (
            native_gate_value.get("gate_value_projection_mul_row_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_MUL_ROW_COMMITMENT,
            "derived native gate/value gate_value_projection_mul_row_commitment",
        ),
        (
            native_gate_value.get("gate_projection_output_commitment"),
            EXPECTED_NATIVE_GATE_OUTPUT_COMMITMENT,
            "derived native gate/value gate_projection_output_commitment",
        ),
        (
            native_gate_value.get("value_projection_output_commitment"),
            EXPECTED_NATIVE_VALUE_OUTPUT_COMMITMENT,
            "derived native gate/value value_projection_output_commitment",
        ),
        (
            native_gate_value.get("gate_value_projection_output_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_OUTPUT_COMMITMENT,
            "derived native gate/value gate_value_projection_output_commitment",
        ),
        (
            native_activation.get("statement_commitment"),
            EXPECTED_NATIVE_ACTIVATION_STATEMENT_COMMITMENT,
            "derived native activation statement_commitment",
        ),
        (
            native_activation.get("public_instance_commitment"),
            EXPECTED_NATIVE_ACTIVATION_PUBLIC_INSTANCE_COMMITMENT,
            "derived native activation public_instance_commitment",
        ),
        (
            native_activation.get("hidden_activation_commitment"),
            EXPECTED_NATIVE_ACTIVATION_HIDDEN_COMMITMENT,
            "derived native activation hidden_activation_commitment",
        ),
        (
            native_activation.get("source_gate_value_projection_statement_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_STATEMENT_COMMITMENT,
            "derived native activation source_gate_value_projection_statement_commitment",
        ),
        (
            native_activation.get("source_gate_value_projection_public_instance_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_PUBLIC_INSTANCE_COMMITMENT,
            "derived native activation source_gate_value_projection_public_instance_commitment",
        ),
        (
            native_activation.get("source_gate_value_projection_output_commitment"),
            EXPECTED_NATIVE_GATE_VALUE_OUTPUT_COMMITMENT,
            "derived native activation source_gate_value_projection_output_commitment",
        ),
        (
            native_activation.get("source_gate_projection_output_commitment"),
            EXPECTED_NATIVE_GATE_OUTPUT_COMMITMENT,
            "derived native activation source_gate_projection_output_commitment",
        ),
        (
            native_activation.get("source_value_projection_output_commitment"),
            EXPECTED_NATIVE_VALUE_OUTPUT_COMMITMENT,
            "derived native activation source_value_projection_output_commitment",
        ),
        (
            native_down.get("statement_commitment"),
            EXPECTED_NATIVE_DOWN_STATEMENT_COMMITMENT,
            "derived native down statement_commitment",
        ),
        (
            native_down.get("public_instance_commitment"),
            EXPECTED_NATIVE_DOWN_PUBLIC_INSTANCE_COMMITMENT,
            "derived native down public_instance_commitment",
        ),
        (
            native_down.get("residual_delta_commitment"),
            EXPECTED_NATIVE_DOWN_RESIDUAL_DELTA_COMMITMENT,
            "derived native down residual_delta_commitment",
        ),
        (
            native_down.get("down_projection_mul_row_commitment"),
            EXPECTED_NATIVE_DOWN_MUL_ROW_COMMITMENT,
            "derived native down down_projection_mul_row_commitment",
        ),
        (
            native_down.get("source_activation_swiglu_statement_commitment"),
            EXPECTED_NATIVE_ACTIVATION_STATEMENT_COMMITMENT,
            "derived native down source_activation_swiglu_statement_commitment",
        ),
        (
            native_down.get("source_activation_swiglu_public_instance_commitment"),
            EXPECTED_NATIVE_ACTIVATION_PUBLIC_INSTANCE_COMMITMENT,
            "derived native down source_activation_swiglu_public_instance_commitment",
        ),
        (
            native_down.get("source_hidden_activation_commitment"),
            EXPECTED_NATIVE_ACTIVATION_HIDDEN_COMMITMENT,
            "derived native down source_hidden_activation_commitment",
        ),
        (
            native_residual.get("statement_commitment"),
            EXPECTED_NATIVE_RESIDUAL_STATEMENT_COMMITMENT,
            "derived native residual statement_commitment",
        ),
        (
            native_residual.get("public_instance_commitment"),
            EXPECTED_NATIVE_RESIDUAL_PUBLIC_INSTANCE_COMMITMENT,
            "derived native residual public_instance_commitment",
        ),
        (
            native_residual.get("input_activation_commitment"),
            EXPECTED_DERIVED_INPUT_COMMITMENT,
            "derived native residual input_activation_commitment",
        ),
        (
            native_residual.get("residual_delta_commitment"),
            EXPECTED_NATIVE_DOWN_RESIDUAL_DELTA_COMMITMENT,
            "derived native residual residual_delta_commitment",
        ),
        (
            native_residual.get("output_activation_commitment"),
            EXPECTED_NATIVE_RESIDUAL_OUTPUT_COMMITMENT,
            "derived native residual output_activation_commitment",
        ),
        (
            native_residual.get("residual_add_row_commitment"),
            EXPECTED_NATIVE_RESIDUAL_ROW_COMMITMENT,
            "derived native residual residual_add_row_commitment",
        ),
        (
            native_residual.get("source_down_projection_statement_commitment"),
            EXPECTED_NATIVE_DOWN_STATEMENT_COMMITMENT,
            "derived native residual source_down_projection_statement_commitment",
        ),
        (
            native_residual.get("source_down_projection_public_instance_commitment"),
            EXPECTED_NATIVE_DOWN_PUBLIC_INSTANCE_COMMITMENT,
            "derived native residual source_down_projection_public_instance_commitment",
        ),
    )
    for actual, expected, label in expected_commitments:
        if actual != expected:
            raise NativeMlpProofRouteError(f"{label} drift")
    if native_bridge.get("source_rmsnorm_statement_commitment") != native_rmsnorm.get("statement_commitment"):
        raise NativeMlpProofRouteError("derived native RMSNorm/bridge statement commitment mismatch")
    if native_bridge.get("source_rmsnorm_public_instance_commitment") != native_rmsnorm.get("public_instance_commitment"):
        raise NativeMlpProofRouteError("derived native RMSNorm/bridge public instance commitment mismatch")
    if native_bridge.get("source_rmsnorm_output_row_commitment") != native_rmsnorm.get("rmsnorm_output_row_commitment"):
        raise NativeMlpProofRouteError("derived native RMSNorm/bridge output row commitment mismatch")
    if native_gate_value.get("source_bridge_statement_commitment") != native_bridge.get("statement_commitment"):
        raise NativeMlpProofRouteError("derived native bridge/gate-value statement commitment mismatch")
    if native_gate_value.get("source_bridge_public_instance_commitment") != native_bridge.get("public_instance_commitment"):
        raise NativeMlpProofRouteError("derived native bridge/gate-value public instance commitment mismatch")
    if native_gate_value.get("source_projection_input_row_commitment") != native_bridge.get("projection_input_row_commitment"):
        raise NativeMlpProofRouteError("derived native bridge/gate-value projection input commitment mismatch")
    if (
        native_activation.get("source_gate_value_projection_statement_commitment")
        != native_gate_value.get("statement_commitment")
    ):
        raise NativeMlpProofRouteError("derived native gate-value/activation statement commitment mismatch")
    if (
        native_activation.get("source_gate_value_projection_public_instance_commitment")
        != native_gate_value.get("public_instance_commitment")
    ):
        raise NativeMlpProofRouteError("derived native gate-value/activation public instance commitment mismatch")
    if (
        native_activation.get("source_gate_value_projection_output_commitment")
        != native_gate_value.get("gate_value_projection_output_commitment")
    ):
        raise NativeMlpProofRouteError("derived native gate-value/activation output commitment mismatch")
    if native_down.get("source_hidden_activation_commitment") != native_activation.get("hidden_activation_commitment"):
        raise NativeMlpProofRouteError("derived native activation/down hidden commitment mismatch")
    if native_down.get("source_activation_swiglu_statement_commitment") != native_activation.get("statement_commitment"):
        raise NativeMlpProofRouteError("derived native activation/down statement commitment mismatch")
    if (
        native_down.get("source_activation_swiglu_public_instance_commitment")
        != native_activation.get("public_instance_commitment")
    ):
        raise NativeMlpProofRouteError("derived native activation/down public instance commitment mismatch")
    if native_residual.get("source_down_projection_statement_commitment") != native_down.get("statement_commitment"):
        raise NativeMlpProofRouteError("derived native down/residual statement commitment mismatch")
    if native_residual.get("source_down_projection_public_instance_commitment") != native_down.get("public_instance_commitment"):
        raise NativeMlpProofRouteError("derived native down/residual public instance commitment mismatch")
    if native_residual.get("residual_delta_commitment") != native_down.get("residual_delta_commitment"):
        raise NativeMlpProofRouteError("derived native down/residual delta commitment mismatch")
    rmsnorm_proof = _list(native_rmsnorm_envelope.get("proof"), "derived native RMSNorm proof bytes")
    bridge_proof = _list(native_bridge_envelope.get("proof"), "derived native bridge proof bytes")
    gate_value_proof = _list(native_gate_value_envelope.get("proof"), "derived native gate/value proof bytes")
    activation_proof = _list(native_activation_envelope.get("proof"), "derived native activation proof bytes")
    down_proof = _list(native_down_envelope.get("proof"), "derived native down proof bytes")
    residual_proof = _list(native_residual_envelope.get("proof"), "derived native residual proof bytes")
    derived_fused_proof = _list(derived_fused_envelope.get("proof"), "derived fused proof bytes")
    accounting_rows_payload = _list(derived_fused_accounting.get("rows"), "derived fused accounting rows")
    accounting_paths = tuple(_str(row.get("evidence_relative_path"), "accounting evidence path") for row in accounting_rows_payload)
    if accounting_paths != EXPECTED_ACCOUNTING_PATHS:
        raise NativeMlpProofRouteError("derived fused accounting path order drift")
    if _int(accounting_rows_payload[0].get("proof_json_size_bytes"), "derived fused accounting proof bytes") != len(
        derived_fused_proof
    ):
        raise NativeMlpProofRouteError("derived fused accounting/proof byte mismatch")
    derived_fused_typed_bytes = accounting_typed_bytes(accounting_rows_payload[0], "derived fused")
    available_separate_typed_bytes = sum(
        accounting_typed_bytes(row, f"available separate {index}")
        for index, row in enumerate(accounting_rows_payload[1:], start=1)
    )
    available_separate_json_bytes = sum(
        _int(row.get("proof_json_size_bytes"), f"available separate {index} proof bytes")
        for index, row in enumerate(accounting_rows_payload[1:], start=1)
    )
    if available_separate_json_bytes <= 0:
        raise NativeMlpProofRouteError("available separate proof bytes must be positive")
    if available_separate_typed_bytes <= 0:
        raise NativeMlpProofRouteError("available separate typed bytes must be positive")
    grouped_delta = {}
    fused_group = accounting_group(accounting_rows_payload[0], "derived fused")
    separate_groups = [accounting_group(row, f"available separate {index}") for index, row in enumerate(accounting_rows_payload[1:], start=1)]
    for key in sorted(fused_group):
        grouped_delta[key] = fused_group[key] - sum(group.get(key, 0) for group in separate_groups)
    rows = _int(chain_summary.get("accounted_relation_rows"), "attention-derived relation rows")
    mlp_rows = _int(current_aggregate.get("fused_total_row_count"), "current MLP fused rows")
    if mlp_rows <= 0:
        raise NativeMlpProofRouteError("current MLP fused rows must be positive before computing row_ratio")
    component_rows = [component_frontier_row(spec, loaded) for spec in COMPONENT_SPECS]
    required_derived_fused_artifacts = [
        {
            "path": path,
            "exists": (ROOT / path).exists(),
            "required_for_go": True,
            "status": "PRESENT_REQUIRED_NATIVE_ATTENTION_DERIVED_FUSED_PROOF_ARTIFACT",
        }
        for path in REQUIRED_DERIVED_FUSED_ARTIFACTS
    ]
    missing_matched_separate_envelopes = [
        {
            "path": path,
            "exists": (ROOT / path).exists(),
            "required_for_complete_six_separate_baseline": True,
            "status": "MISSING_MATCHED_DERIVED_SEPARATE_COMPONENT_ENVELOPE",
        }
        for path in MISSING_MATCHED_SEPARATE_ENVELOPES
    ]
    return {
        "loaded": loaded,
        "source_artifacts": artifacts,
        "component_input_frontier": component_rows,
        "required_derived_fused_artifacts": required_derived_fused_artifacts,
        "missing_matched_separate_envelopes": missing_matched_separate_envelopes,
        "comparison": {
            "derived_input_activation_commitment": derived_input_commitment,
            "current_mlp_input_activation_commitment": current_input_commitment,
            "current_mlp_fused_envelope_input_activation_commitment": envelope_input_commitment,
            "current_mlp_proof_backend_version": _str(
                current_envelope.get("proof_backend_version"),
                "current MLP proof backend version",
            ),
            "derived_fused_statement_commitment": _commitment(
                derived_fused_input.get("statement_commitment"),
                "derived fused statement commitment",
            ),
            "derived_fused_public_instance_commitment": _commitment(
                derived_fused_input.get("public_instance_commitment"),
                "derived fused public instance commitment",
            ),
            "derived_fused_proof_backend_version": _str(
                derived_fused_envelope.get("proof_backend_version"),
                "derived fused proof backend version",
            ),
            "derived_fused_proof_bytes": len(derived_fused_proof),
            "derived_fused_envelope_bytes": len(raw_by_path[DERIVED_FUSED_ENVELOPE]),
            "derived_fused_input_bytes": len(raw_by_path[DERIVED_FUSED_INPUT]),
            "derived_fused_typed_bytes": derived_fused_typed_bytes,
            "available_separate_component_count": len(accounting_rows_payload) - 1,
            "available_separate_proof_bytes": available_separate_json_bytes,
            "available_separate_typed_bytes": available_separate_typed_bytes,
            "json_saving_vs_available_separate_bytes": available_separate_json_bytes - len(derived_fused_proof),
            "json_ratio_vs_available_separate": round(len(derived_fused_proof) / available_separate_json_bytes, 6),
            "typed_saving_vs_available_separate_bytes": available_separate_typed_bytes - derived_fused_typed_bytes,
            "typed_ratio_vs_available_separate": round(derived_fused_typed_bytes / available_separate_typed_bytes, 6),
            "grouped_typed_delta_vs_available_separate": grouped_delta,
            "matched_six_separate_derived_baseline_status": "COMPLETE_EXACT_SIX_DERIVED_SEPARATE_ENVELOPES",
            "value_connected_chain_rows": rows,
            "current_mlp_fused_rows": mlp_rows,
            "row_ratio": round(rows / mlp_rows, 6),
            "extra_rows_vs_current_mlp_fused": rows - mlp_rows,
            "current_mlp_fused_typed_bytes": _int(
                current_aggregate.get("fused_local_typed_bytes"),
                "current fused typed bytes",
            ),
            "current_mlp_separate_typed_bytes": _int(
                current_aggregate.get("separate_local_typed_bytes"),
                "current separate typed bytes",
            ),
            "current_mlp_typed_saving_vs_separate_bytes": _int(
                current_aggregate.get("typed_saving_vs_separate_bytes"),
                "current typed saving bytes",
            ),
            "current_mlp_typed_saving_ratio_vs_separate": current_aggregate.get(
                "typed_saving_ratio_vs_separate"
            ),
            "derived_native_rmsnorm_statement_commitment": _commitment(
                native_rmsnorm.get("statement_commitment"),
                "derived native RMSNorm statement commitment",
            ),
            "derived_native_rmsnorm_public_instance_commitment": _commitment(
                native_rmsnorm.get("public_instance_commitment"),
                "derived native RMSNorm public instance commitment",
            ),
            "derived_native_rmsnorm_output_row_commitment": _commitment(
                native_rmsnorm.get("rmsnorm_output_row_commitment"),
                "derived native RMSNorm output row commitment",
            ),
            "derived_native_rmsnorm_proof_backend_version": _str(
                native_rmsnorm_envelope.get("proof_backend_version"),
                "derived native RMSNorm proof backend version",
            ),
            "derived_native_rmsnorm_proof_bytes": len(rmsnorm_proof),
            "derived_native_rmsnorm_envelope_bytes": len(raw_by_path[DERIVED_NATIVE_RMSNORM_ENVELOPE]),
            "derived_native_bridge_statement_commitment": _commitment(
                native_bridge.get("statement_commitment"),
                "derived native bridge statement commitment",
            ),
            "derived_native_bridge_public_instance_commitment": _commitment(
                native_bridge.get("public_instance_commitment"),
                "derived native bridge public instance commitment",
            ),
            "derived_native_bridge_projection_input_row_commitment": _commitment(
                native_bridge.get("projection_input_row_commitment"),
                "derived native bridge projection input row commitment",
            ),
            "derived_native_bridge_proof_backend_version": _str(
                native_bridge_envelope.get("proof_backend_version"),
                "derived native bridge proof backend version",
            ),
            "derived_native_bridge_proof_bytes": len(bridge_proof),
            "derived_native_bridge_envelope_bytes": len(raw_by_path[DERIVED_NATIVE_BRIDGE_ENVELOPE]),
            "derived_native_gate_value_statement_commitment": _commitment(
                native_gate_value.get("statement_commitment"),
                "derived native gate/value statement commitment",
            ),
            "derived_native_gate_value_public_instance_commitment": _commitment(
                native_gate_value.get("public_instance_commitment"),
                "derived native gate/value public instance commitment",
            ),
            "derived_native_gate_value_output_commitment": _commitment(
                native_gate_value.get("gate_value_projection_output_commitment"),
                "derived native gate/value output commitment",
            ),
            "derived_native_gate_value_proof_backend_version": _str(
                native_gate_value_envelope.get("proof_backend_version"),
                "derived native gate/value proof backend version",
            ),
            "derived_native_gate_value_proof_bytes": len(gate_value_proof),
            "derived_native_gate_value_envelope_bytes": len(raw_by_path[DERIVED_NATIVE_GATE_VALUE_ENVELOPE]),
            "derived_native_activation_statement_commitment": _commitment(
                native_activation.get("statement_commitment"),
                "derived native activation statement commitment",
            ),
            "derived_native_activation_public_instance_commitment": _commitment(
                native_activation.get("public_instance_commitment"),
                "derived native activation public instance commitment",
            ),
            "derived_native_activation_hidden_commitment": _commitment(
                native_activation.get("hidden_activation_commitment"),
                "derived native activation hidden commitment",
            ),
            "derived_native_activation_proof_backend_version": _str(
                native_activation_envelope.get("proof_backend_version"),
                "derived native activation proof backend version",
            ),
            "derived_native_activation_proof_bytes": len(activation_proof),
            "derived_native_activation_envelope_bytes": len(raw_by_path[DERIVED_NATIVE_ACTIVATION_ENVELOPE]),
            "derived_native_down_statement_commitment": _commitment(
                native_down.get("statement_commitment"),
                "derived native down statement commitment",
            ),
            "derived_native_down_public_instance_commitment": _commitment(
                native_down.get("public_instance_commitment"),
                "derived native down public instance commitment",
            ),
            "derived_native_down_residual_delta_commitment": _commitment(
                native_down.get("residual_delta_commitment"),
                "derived native down residual delta commitment",
            ),
            "derived_native_down_projection_mul_row_commitment": _commitment(
                native_down.get("down_projection_mul_row_commitment"),
                "derived native down projection row commitment",
            ),
            "derived_native_down_proof_backend_version": _str(
                native_down_envelope.get("proof_backend_version"),
                "derived native down proof backend version",
            ),
            "derived_native_down_proof_bytes": len(down_proof),
            "derived_native_down_envelope_bytes": len(raw_by_path[DERIVED_NATIVE_DOWN_ENVELOPE]),
            "derived_native_residual_statement_commitment": _commitment(
                native_residual.get("statement_commitment"),
                "derived native residual statement commitment",
            ),
            "derived_native_residual_public_instance_commitment": _commitment(
                native_residual.get("public_instance_commitment"),
                "derived native residual public instance commitment",
            ),
            "derived_native_residual_output_commitment": _commitment(
                native_residual.get("output_activation_commitment"),
                "derived native residual output commitment",
            ),
            "derived_native_residual_add_row_commitment": _commitment(
                native_residual.get("residual_add_row_commitment"),
                "derived native residual-add row commitment",
            ),
            "derived_native_residual_proof_backend_version": _str(
                native_residual_envelope.get("proof_backend_version"),
                "derived native residual proof backend version",
            ),
            "derived_native_residual_proof_bytes": len(residual_proof),
            "derived_native_residual_envelope_bytes": len(raw_by_path[DERIVED_NATIVE_RESIDUAL_ENVELOPE]),
            "current_native_fused_proof_can_be_reused_for_derived_input": False,
        },
    }


def build_core_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_context() if context is None else context
    compatible_count = sum(
        1
        for row in context["component_input_frontier"]
        if row["native_component_input_status"] == "COMPATIBLE_WITH_CURRENT_NATIVE_INPUT_SHAPE"
    )
    incompatible_count = len(context["component_input_frontier"]) - compatible_count
    comparison = context["comparison"]
    if _int(comparison.get("current_mlp_fused_rows"), "current MLP fused rows") <= 0:
        raise NativeMlpProofRouteError("current MLP fused rows must be positive before carrying row_ratio")
    if (
        comparison.get("current_mlp_fused_envelope_input_activation_commitment")
        != comparison.get("current_mlp_input_activation_commitment")
    ):
        raise NativeMlpProofRouteError("current MLP envelope/input activation commitment mismatch")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "result": RESULT,
        "value_chain_status": VALUE_CHAIN_STATUS,
        "native_route_status": NATIVE_ROUTE_STATUS,
        "first_blocker": FIRST_BLOCKER,
        "source_artifacts": copy.deepcopy(context["source_artifacts"]),
        "component_input_frontier": copy.deepcopy(context["component_input_frontier"]),
        "required_derived_fused_artifacts": copy.deepcopy(context["required_derived_fused_artifacts"]),
        "missing_matched_separate_envelopes": copy.deepcopy(context["missing_matched_separate_envelopes"]),
        "comparison": copy.deepcopy(comparison),
        "summary": {
            "go_result": "GO for a value-connected attention-derived d128 statement chain",
            "proof_result": "GO for a regenerated attention-derived native RMSNorm-MLP fused proof",
            "remaining_no_go_result": "NO-GO for attention plus MLP in one native proof object or matched external benchmark",
            "derived_input_activation_commitment": comparison["derived_input_activation_commitment"],
            "current_mlp_input_activation_commitment": comparison["current_mlp_input_activation_commitment"],
            "derived_fused_statement_commitment": comparison["derived_fused_statement_commitment"],
            "derived_fused_public_instance_commitment": comparison[
                "derived_fused_public_instance_commitment"
            ],
            "derived_fused_proof_backend_version": comparison[
                "derived_fused_proof_backend_version"
            ],
            "derived_fused_proof_bytes": comparison["derived_fused_proof_bytes"],
            "derived_fused_envelope_bytes": comparison["derived_fused_envelope_bytes"],
            "derived_fused_input_bytes": comparison["derived_fused_input_bytes"],
            "derived_fused_typed_bytes": comparison["derived_fused_typed_bytes"],
            "available_separate_component_count": comparison["available_separate_component_count"],
            "available_separate_proof_bytes": comparison["available_separate_proof_bytes"],
            "available_separate_typed_bytes": comparison["available_separate_typed_bytes"],
            "json_saving_vs_available_separate_bytes": comparison[
                "json_saving_vs_available_separate_bytes"
            ],
            "json_ratio_vs_available_separate": comparison["json_ratio_vs_available_separate"],
            "typed_saving_vs_available_separate_bytes": comparison[
                "typed_saving_vs_available_separate_bytes"
            ],
            "typed_ratio_vs_available_separate": comparison["typed_ratio_vs_available_separate"],
            "matched_six_separate_derived_baseline_status": comparison[
                "matched_six_separate_derived_baseline_status"
            ],
            "value_connected_chain_rows": comparison["value_connected_chain_rows"],
            "current_mlp_fused_rows": comparison["current_mlp_fused_rows"],
            "row_ratio": comparison["row_ratio"],
            "current_mlp_fused_typed_bytes": comparison["current_mlp_fused_typed_bytes"],
            "current_mlp_typed_saving_vs_separate_bytes": comparison[
                "current_mlp_typed_saving_vs_separate_bytes"
            ],
            "current_mlp_typed_saving_ratio_vs_separate": comparison[
                "current_mlp_typed_saving_ratio_vs_separate"
            ],
            "derived_native_rmsnorm_statement_commitment": comparison[
                "derived_native_rmsnorm_statement_commitment"
            ],
            "derived_native_rmsnorm_public_instance_commitment": comparison[
                "derived_native_rmsnorm_public_instance_commitment"
            ],
            "derived_native_rmsnorm_output_row_commitment": comparison[
                "derived_native_rmsnorm_output_row_commitment"
            ],
            "derived_native_rmsnorm_proof_backend_version": comparison[
                "derived_native_rmsnorm_proof_backend_version"
            ],
            "derived_native_rmsnorm_proof_bytes": comparison["derived_native_rmsnorm_proof_bytes"],
            "derived_native_rmsnorm_envelope_bytes": comparison[
                "derived_native_rmsnorm_envelope_bytes"
            ],
            "derived_native_bridge_statement_commitment": comparison[
                "derived_native_bridge_statement_commitment"
            ],
            "derived_native_bridge_public_instance_commitment": comparison[
                "derived_native_bridge_public_instance_commitment"
            ],
            "derived_native_bridge_projection_input_row_commitment": comparison[
                "derived_native_bridge_projection_input_row_commitment"
            ],
            "derived_native_bridge_proof_backend_version": comparison[
                "derived_native_bridge_proof_backend_version"
            ],
            "derived_native_bridge_proof_bytes": comparison["derived_native_bridge_proof_bytes"],
            "derived_native_bridge_envelope_bytes": comparison[
                "derived_native_bridge_envelope_bytes"
            ],
            "derived_native_gate_value_statement_commitment": comparison[
                "derived_native_gate_value_statement_commitment"
            ],
            "derived_native_gate_value_public_instance_commitment": comparison[
                "derived_native_gate_value_public_instance_commitment"
            ],
            "derived_native_gate_value_output_commitment": comparison[
                "derived_native_gate_value_output_commitment"
            ],
            "derived_native_gate_value_proof_backend_version": comparison[
                "derived_native_gate_value_proof_backend_version"
            ],
            "derived_native_gate_value_proof_bytes": comparison[
                "derived_native_gate_value_proof_bytes"
            ],
            "derived_native_gate_value_envelope_bytes": comparison[
                "derived_native_gate_value_envelope_bytes"
            ],
            "derived_native_activation_statement_commitment": comparison[
                "derived_native_activation_statement_commitment"
            ],
            "derived_native_activation_public_instance_commitment": comparison[
                "derived_native_activation_public_instance_commitment"
            ],
            "derived_native_activation_hidden_commitment": comparison[
                "derived_native_activation_hidden_commitment"
            ],
            "derived_native_activation_proof_backend_version": comparison[
                "derived_native_activation_proof_backend_version"
            ],
            "derived_native_activation_proof_bytes": comparison[
                "derived_native_activation_proof_bytes"
            ],
            "derived_native_activation_envelope_bytes": comparison[
                "derived_native_activation_envelope_bytes"
            ],
            "derived_native_down_statement_commitment": comparison[
                "derived_native_down_statement_commitment"
            ],
            "derived_native_down_public_instance_commitment": comparison[
                "derived_native_down_public_instance_commitment"
            ],
            "derived_native_down_residual_delta_commitment": comparison[
                "derived_native_down_residual_delta_commitment"
            ],
            "derived_native_down_projection_mul_row_commitment": comparison[
                "derived_native_down_projection_mul_row_commitment"
            ],
            "derived_native_down_proof_backend_version": comparison[
                "derived_native_down_proof_backend_version"
            ],
            "derived_native_down_proof_bytes": comparison["derived_native_down_proof_bytes"],
            "derived_native_down_envelope_bytes": comparison["derived_native_down_envelope_bytes"],
            "derived_native_residual_statement_commitment": comparison[
                "derived_native_residual_statement_commitment"
            ],
            "derived_native_residual_public_instance_commitment": comparison[
                "derived_native_residual_public_instance_commitment"
            ],
            "derived_native_residual_output_commitment": comparison[
                "derived_native_residual_output_commitment"
            ],
            "derived_native_residual_add_row_commitment": comparison[
                "derived_native_residual_add_row_commitment"
            ],
            "derived_native_residual_proof_backend_version": comparison[
                "derived_native_residual_proof_backend_version"
            ],
            "derived_native_residual_proof_bytes": comparison[
                "derived_native_residual_proof_bytes"
            ],
            "derived_native_residual_envelope_bytes": comparison[
                "derived_native_residual_envelope_bytes"
            ],
            "native_compatible_components": compatible_count,
            "native_incompatible_components": incompatible_count,
            "required_derived_fused_artifacts_present": sum(
                1 for artifact in context["required_derived_fused_artifacts"] if artifact["exists"]
            ),
            "missing_matched_separate_envelopes": len(context["missing_matched_separate_envelopes"]),
            "route_commitment": blake2b_commitment(
                {
                    "derived_input": comparison["derived_input_activation_commitment"],
                    "derived_fused": comparison["derived_fused_statement_commitment"],
                    "component_frontier": context["component_input_frontier"],
                    "required_derived_fused_artifacts": context["required_derived_fused_artifacts"],
                    "missing_matched_separate_envelopes": context["missing_matched_separate_envelopes"],
                },
                PAYLOAD_DOMAIN,
            ),
        },
        "non_claims": list(NON_CLAIMS),
        "validation_commands": list(VALIDATION_COMMANDS),
    }
    refresh_payload_commitment(payload)
    return payload


def validate_payload(payload: Any, *, context: dict[str, Any] | None = None) -> None:
    data = _dict(payload, "payload")
    if set(data) not in (CORE_KEYS, FINAL_KEYS):
        raise NativeMlpProofRouteError("payload key set drift")
    if data.get("schema") != SCHEMA:
        raise NativeMlpProofRouteError("schema drift")
    if data.get("decision") != DECISION:
        raise NativeMlpProofRouteError("decision drift")
    if data.get("result") != RESULT:
        raise NativeMlpProofRouteError("result drift")
    if data.get("value_chain_status") != VALUE_CHAIN_STATUS:
        raise NativeMlpProofRouteError("value-chain status drift")
    if data.get("native_route_status") != NATIVE_ROUTE_STATUS:
        raise NativeMlpProofRouteError("native route status drift")
    if data.get("first_blocker") != FIRST_BLOCKER:
        raise NativeMlpProofRouteError("first blocker drift")
    if data.get("non_claims") != NON_CLAIMS:
        raise NativeMlpProofRouteError("non-claims drift")
    if data.get("validation_commands") != VALIDATION_COMMANDS:
        raise NativeMlpProofRouteError("validation commands drift")
    context = build_context() if context is None else context
    expected = build_core_payload(context)
    comparable = {key: value for key, value in data.items() if key not in MUTATION_KEYS | {"payload_commitment"}}
    expected_comparable = {key: value for key, value in expected.items() if key != "payload_commitment"}
    if comparable != expected_comparable:
        raise NativeMlpProofRouteError("payload content drift")
    summary = _dict(data.get("summary"), "summary")
    if _int(summary.get("native_compatible_components"), "native compatible components") != len(COMPONENT_SPECS):
        raise NativeMlpProofRouteError("native component frontier drift")
    if _int(summary.get("native_incompatible_components"), "native incompatible components") != 0:
        raise NativeMlpProofRouteError("native component frontier drift")
    if _int(summary.get("available_separate_component_count"), "available separate component count") != len(
        COMPONENT_SPECS
    ):
        raise NativeMlpProofRouteError("matched six-separate baseline component count drift")
    if _int(summary.get("required_derived_fused_artifacts_present"), "required derived fused artifacts") != len(
        REQUIRED_DERIVED_FUSED_ARTIFACTS
    ):
        raise NativeMlpProofRouteError("required derived fused artifact missing")
    if _int(summary.get("missing_matched_separate_envelopes"), "missing matched separate envelopes") != len(
        MISSING_MATCHED_SEPARATE_ENVELOPES
    ):
        raise NativeMlpProofRouteError("matched separate baseline boundary drift")
    if (
        data["comparison"].get("matched_six_separate_derived_baseline_status")
        != "COMPLETE_EXACT_SIX_DERIVED_SEPARATE_ENVELOPES"
    ):
        raise NativeMlpProofRouteError("matched six-separate baseline status drift")
    if data["comparison"]["derived_fused_typed_bytes"] >= data["comparison"]["available_separate_typed_bytes"]:
        raise NativeMlpProofRouteError("derived fused exact-baseline saving disappeared")
    if data["comparison"]["derived_fused_proof_bytes"] >= data["comparison"]["available_separate_proof_bytes"]:
        raise NativeMlpProofRouteError("derived fused exact-baseline proof-byte saving disappeared")
    if data["comparison"]["current_native_fused_proof_can_be_reused_for_derived_input"] is not False:
        raise NativeMlpProofRouteError("current proof reuse overclaim")
    for row in _list(data.get("required_derived_fused_artifacts"), "required derived fused artifacts"):
        artifact = _dict(row, "required derived fused artifact")
        if _bool(artifact.get("exists"), "required artifact exists") is not True:
            raise NativeMlpProofRouteError("required derived fused artifact missing")
        if _bool(artifact.get("required_for_go"), "required for go") is not True:
            raise NativeMlpProofRouteError("required derived fused artifact no longer required")
        if artifact.get("status") != "PRESENT_REQUIRED_NATIVE_ATTENTION_DERIVED_FUSED_PROOF_ARTIFACT":
            raise NativeMlpProofRouteError("required derived fused artifact status drift")
    for row in _list(data.get("missing_matched_separate_envelopes"), "missing matched separate envelopes"):
        artifact = _dict(row, "missing matched separate envelope")
        if _bool(artifact.get("exists"), "missing matched separate envelope exists") is not False:
            raise NativeMlpProofRouteError("matched separate envelope relabeled as existing")
        if _bool(
            artifact.get("required_for_complete_six_separate_baseline"),
            "required for complete six separate baseline",
        ) is not True:
            raise NativeMlpProofRouteError("matched separate baseline requirement weakened")
        if artifact.get("status") != "MISSING_MATCHED_DERIVED_SEPARATE_COMPONENT_ENVELOPE":
            raise NativeMlpProofRouteError("missing matched separate envelope status drift")
    if data.get("payload_commitment") != payload_commitment(data):
        raise NativeMlpProofRouteError("payload commitment drift")
    if set(data) == FINAL_KEYS:
        cases = _list(data.get("cases"), "cases")
        if data.get("mutation_inventory") != list(EXPECTED_MUTATIONS):
            raise NativeMlpProofRouteError("mutation inventory drift")
        if data.get("case_count") != len(EXPECTED_MUTATIONS):
            raise NativeMlpProofRouteError("case count drift")
        if data.get("all_mutations_rejected") is not True:
            raise NativeMlpProofRouteError("not all mutations rejected")
        if len(cases) != len(EXPECTED_MUTATIONS):
            raise NativeMlpProofRouteError("mutation cases length drift")
        for index, (name, case_value) in enumerate(zip(EXPECTED_MUTATIONS, cases, strict=True)):
            case = _dict(case_value, f"case {index}")
            if set(case) != {"name", "accepted", "rejected", "error"}:
                raise NativeMlpProofRouteError("mutation case field drift")
            if case.get("name") != name:
                raise NativeMlpProofRouteError("mutation case order drift")
            if case.get("accepted") is not False or case.get("rejected") is not True:
                raise NativeMlpProofRouteError("mutation accepted")
            if not isinstance(case.get("error"), str) or not case["error"]:
                raise NativeMlpProofRouteError("mutation error missing")


MutationFn = Callable[[dict[str, Any]], None]


def _set_payload_commitment_drift(payload: dict[str, Any]) -> None:
    payload["payload_commitment"] = "sha256:" + "11" * 32


def _promote_component_schema(payload: dict[str, Any], component_id: str) -> None:
    for component in payload["component_input_frontier"]:
        if component.get("component_id") == component_id:
            component["schema"] = component["required_native_schema"]
            return
    raise NativeMlpProofRouteError(f"component not found: {component_id}")


def _relabel_residual_component_source(payload: dict[str, Any]) -> None:
    for component in payload["component_input_frontier"]:
        if component.get("component_id") == "residual_add":
            component["source_path"] = DERIVED_RESIDUAL.relative_to(ROOT).as_posix()
            return
    raise NativeMlpProofRouteError("residual component not found")


MUTATION_BUILDERS: tuple[tuple[str, MutationFn, bool], ...] = (
    (
        "decision_downgraded_to_no_go",
        lambda p: p.__setitem__("decision", "NO_GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_NOT_REGENERATED"),
        True,
    ),
    ("result_overclaims_full_block", lambda p: p.__setitem__("result", "GO_FULL_TRANSFORMER_BLOCK"), True),
    ("native_route_status_overclaims_attention", lambda p: p.__setitem__("native_route_status", "GO_ATTENTION_PLUS_MLP_NATIVE_BLOCK"), True),
    ("first_blocker_removed", lambda p: p.__setitem__("first_blocker", ""), True),
    (
        "derived_input_relabels_current_mlp_input",
        lambda p: p["comparison"].__setitem__(
            "derived_input_activation_commitment", EXPECTED_CURRENT_INPUT_COMMITMENT
        ),
        True,
    ),
    (
        "current_proof_reuse_overclaim",
        lambda p: p["comparison"].__setitem__("current_native_fused_proof_can_be_reused_for_derived_input", True),
        True,
    ),
    (
        "native_compatible_component_count_drift",
        lambda p: p["summary"].__setitem__("native_compatible_components", 5),
        True,
    ),
    (
        "residual_component_source_relabels_statement_chain",
        _relabel_residual_component_source,
        True,
    ),
    (
        "required_fused_artifact_marked_missing",
        lambda p: p["required_derived_fused_artifacts"][0].__setitem__("exists", False),
        True,
    ),
    (
        "required_fused_artifact_not_required",
        lambda p: p["required_derived_fused_artifacts"][0].__setitem__("required_for_go", False),
        True,
    ),
    (
        "matched_six_separate_baseline_status_downgraded",
        lambda p: p["comparison"].__setitem__(
            "matched_six_separate_derived_baseline_status",
            "PARTIAL_ONLY_MISSING_RMSNORM_AND_BRIDGE_SEPARATE_ENVELOPES",
        ),
        True,
    ),
    (
        "matched_six_separate_component_count_drift",
        lambda p: p["summary"].__setitem__("available_separate_component_count", 5),
        True,
    ),
    (
        "exact_baseline_saving_smuggled",
        lambda p: p["comparison"].__setitem__(
            "derived_fused_typed_bytes", p["comparison"]["available_separate_typed_bytes"] + 1
        ),
        True,
    ),
    (
        "exact_baseline_proof_byte_saving_smuggled",
        lambda p: p["comparison"].__setitem__(
            "derived_fused_proof_bytes", p["comparison"]["available_separate_proof_bytes"] + 1
        ),
        True,
    ),
    ("non_claim_removed", lambda p: p.__setitem__("non_claims", p["non_claims"][1:]), True),
    ("validation_command_removed", lambda p: p.__setitem__("validation_commands", p["validation_commands"][1:]), True),
    ("payload_commitment_drift", _set_payload_commitment_drift, False),
)

EXPECTED_MUTATIONS = tuple(name for name, _, _ in MUTATION_BUILDERS)


def run_mutation_cases(core_payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for name, mutator, refresh in MUTATION_BUILDERS:
        mutated = copy.deepcopy(core_payload)
        mutator(mutated)
        if refresh:
            refresh_payload_commitment(mutated)
        try:
            validate_payload(mutated, context=context)
        except NativeMlpProofRouteError as err:
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


def to_tsv(payload: dict[str, Any], *, context: dict[str, Any] | None = None) -> str:
    validate_payload(payload, context=context)
    summary = _dict(payload.get("summary"), "summary")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TSV_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "decision": payload["decision"],
            "result": payload["result"],
            "value_chain_status": payload["value_chain_status"],
            "native_route_status": payload["native_route_status"],
            "derived_input_activation_commitment": summary["derived_input_activation_commitment"],
            "current_mlp_input_activation_commitment": summary["current_mlp_input_activation_commitment"],
            "value_connected_chain_rows": summary["value_connected_chain_rows"],
            "current_mlp_fused_rows": summary["current_mlp_fused_rows"],
            "row_ratio": summary["row_ratio"],
            "current_mlp_fused_typed_bytes": summary["current_mlp_fused_typed_bytes"],
            "current_mlp_typed_saving_vs_separate_bytes": summary[
                "current_mlp_typed_saving_vs_separate_bytes"
            ],
            "derived_fused_proof_bytes": summary["derived_fused_proof_bytes"],
            "derived_fused_envelope_bytes": summary["derived_fused_envelope_bytes"],
            "derived_fused_typed_bytes": summary["derived_fused_typed_bytes"],
            "available_separate_component_count": summary["available_separate_component_count"],
            "available_separate_typed_bytes": summary["available_separate_typed_bytes"],
            "typed_saving_vs_available_separate_bytes": summary[
                "typed_saving_vs_available_separate_bytes"
            ],
            "typed_ratio_vs_available_separate": summary["typed_ratio_vs_available_separate"],
            "native_compatible_components": summary["native_compatible_components"],
            "native_incompatible_components": summary["native_incompatible_components"],
            "derived_native_rmsnorm_proof_bytes": summary["derived_native_rmsnorm_proof_bytes"],
            "derived_native_rmsnorm_envelope_bytes": summary["derived_native_rmsnorm_envelope_bytes"],
            "derived_native_bridge_proof_bytes": summary["derived_native_bridge_proof_bytes"],
            "derived_native_bridge_envelope_bytes": summary["derived_native_bridge_envelope_bytes"],
            "derived_native_gate_value_proof_bytes": summary["derived_native_gate_value_proof_bytes"],
            "derived_native_gate_value_envelope_bytes": summary[
                "derived_native_gate_value_envelope_bytes"
            ],
            "derived_native_activation_proof_bytes": summary["derived_native_activation_proof_bytes"],
            "derived_native_activation_envelope_bytes": summary["derived_native_activation_envelope_bytes"],
            "derived_native_down_proof_bytes": summary["derived_native_down_proof_bytes"],
            "derived_native_down_envelope_bytes": summary["derived_native_down_envelope_bytes"],
            "derived_native_residual_proof_bytes": summary["derived_native_residual_proof_bytes"],
            "derived_native_residual_envelope_bytes": summary["derived_native_residual_envelope_bytes"],
        }
    )
    return output.getvalue()


def require_output_path(path: pathlib.Path | None, suffix: str) -> pathlib.Path | None:
    if path is None:
        return None
    resolved_root = ROOT.resolve()
    candidate = (ROOT / path if not path.is_absolute() else path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as err:
        raise NativeMlpProofRouteError(f"output path must stay inside repository: {path}") from err
    if candidate.suffix != suffix:
        raise NativeMlpProofRouteError(f"output path must end with {suffix}: {path}")
    if candidate.exists() and candidate.is_symlink():
        raise NativeMlpProofRouteError(f"output path must not be symlink: {path}")
    return candidate


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd: int | None = None
    tmp: pathlib.Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        tmp = pathlib.Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp is not None:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)
        raise


def write_outputs(payload: dict[str, Any], json_path: pathlib.Path | None, tsv_path: pathlib.Path | None) -> None:
    context = build_context()
    validate_payload(payload, context=context)
    json_target = require_output_path(json_path, ".json")
    tsv_target = require_output_path(tsv_path, ".tsv")
    if json_target is not None:
        atomic_write(json_target, pretty_json(payload) + "\n")
    if tsv_target is not None:
        atomic_write(tsv_target, to_tsv(payload, context=context))


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
    except NativeMlpProofRouteError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
