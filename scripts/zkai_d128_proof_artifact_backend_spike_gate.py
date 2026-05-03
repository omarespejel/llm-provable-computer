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
import stat as stat_module
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs" / "engineering" / "evidence"
TARGET_GATE_PATH = ROOT / "scripts" / "zkai_d128_layerwise_comparator_target_gate.py"
D64_BLOCK_GATE_PATH = ROOT / "scripts" / "zkai_d64_block_receipt_composition_gate.py"
VECTOR_RESIDUAL_GATE_PATH = ROOT / "scripts" / "zkai_d128_vector_residual_add_proof_input.py"
D128_RESIDUAL_GATE_PATH = ROOT / "scripts" / "zkai_d128_residual_add_proof_input.py"
D128_RMSNORM_GATE_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_public_row_proof_input.py"
D128_BRIDGE_GATE_PATH = ROOT / "scripts" / "zkai_d128_rmsnorm_to_projection_bridge_input.py"
D128_GATE_VALUE_GATE_PATH = ROOT / "scripts" / "zkai_d128_gate_value_projection_proof_input.py"
D128_ACTIVATION_GATE_PATH = ROOT / "scripts" / "zkai_d128_activation_swiglu_proof_input.py"
D128_DOWN_GATE_PATH = ROOT / "scripts" / "zkai_d128_down_projection_proof_input.py"
D128_BLOCK_GATE_PATH = ROOT / "scripts" / "zkai_d128_block_receipt_composition_gate.py"
TARGET_EVIDENCE = EVIDENCE_DIR / "zkai-d128-layerwise-comparator-target-2026-05.json"
D64_BLOCK_EVIDENCE = EVIDENCE_DIR / "zkai-d64-block-receipt-composition-gate-2026-05.json"
VECTOR_RESIDUAL_EVIDENCE = EVIDENCE_DIR / "zkai-d128-vector-residual-add-proof-2026-05.json"
D128_RESIDUAL_EVIDENCE = EVIDENCE_DIR / "zkai-d128-residual-add-proof-2026-05.json"
D128_RMSNORM_EVIDENCE = EVIDENCE_DIR / "zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
D128_BRIDGE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
D128_GATE_VALUE_EVIDENCE = EVIDENCE_DIR / "zkai-d128-gate-value-projection-proof-2026-05.json"
D128_ACTIVATION_EVIDENCE = EVIDENCE_DIR / "zkai-d128-activation-swiglu-proof-2026-05.json"
D128_DOWN_EVIDENCE = EVIDENCE_DIR / "zkai-d128-down-projection-proof-2026-05.json"
D128_BLOCK_EVIDENCE = EVIDENCE_DIR / "zkai-d128-block-receipt-composition-gate-2026-05.json"
JSON_OUT = EVIDENCE_DIR / "zkai-d128-proof-artifact-backend-spike-2026-05.json"
TSV_OUT = EVIDENCE_DIR / "zkai-d128-proof-artifact-backend-spike-2026-05.tsv"

SCHEMA = "zkai-d128-proof-artifact-backend-spike-v1"
DECISION = "NO_GO_D128_AGGREGATED_FULL_BLOCK_PROOF_ARTIFACT_MISSING"
RESULT = "BOUNDED_NO_GO"
ISSUE = 387
TARGET_ID = "rmsnorm-swiglu-residual-d128-v1"
TARGET_WIDTH = 128
TARGET_FF_DIM = 512
D128_BLOCK_RECEIPT_MUTATION_CASES = 20
D128_BLOCK_STATEMENT_COMMITMENT = "blake2b-256:f808e10c539370b63f8f8300a0a6dfa9cb0fa02eed4ca3fbd83a378c4a0a2b60"
D128_BLOCK_RECEIPT_COMMITMENT = "blake2b-256:a2cd8a3dc2f3a5d176fe0a569929fd6e146c4cccfab9aaa18a92a3da057b9c3a"
REQUIRED_BACKEND_VERSION = "stwo-rmsnorm-swiglu-residual-d128-v1"
REQUIRED_TOOLCHAIN = "nightly-2025-07-14"
GATE_COMMITMENT_DOMAIN = "ptvm:zkai:d128-proof-artifact-backend-spike:v1"
FIRST_BLOCKER = "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING"
FIRST_BLOCKER_DETAIL = (
    "a statement-bound d128 block receipt now composes six proof-backed slices, "
    "but recursive aggregation or a single compressed verifier object is still missing"
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
    "src/stwo_backend/d128_native_transformer_block_proof.rs",
)

EXPECTED_D128_EXPORT_SYMBOLS = (
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

D128_GATE_VALUE_SYMBOLS = (
    "D128GateValueProjectionMulRow",
    "ZkAiD128GateValueProjectionProofInput",
    "ZkAiD128GateValueProjectionEnvelope",
    "zkai_d128_gate_value_projection_input_from_json_str",
    "prove_zkai_d128_gate_value_projection_envelope",
    "verify_zkai_d128_gate_value_projection_envelope",
)

D128_ACTIVATION_SYMBOLS = (
    "D128ActivationSwiGluRow",
    "ZkAiD128ActivationSwiGluProofInput",
    "ZkAiD128ActivationSwiGluEnvelope",
    "zkai_d128_activation_swiglu_input_from_json_str",
    "prove_zkai_d128_activation_swiglu_envelope",
    "verify_zkai_d128_activation_swiglu_envelope",
)

D128_DOWN_SYMBOLS = (
    "D128DownProjectionMulRow",
    "ZkAiD128DownProjectionProofInput",
    "ZkAiD128DownProjectionEnvelope",
    "zkai_d128_down_projection_input_from_json_str",
    "prove_zkai_d128_down_projection_envelope",
    "verify_zkai_d128_down_projection_envelope",
)

D128_RESIDUAL_SYMBOLS = (
    "D128ResidualAddRow",
    "ZkAiD128ResidualAddProofInput",
    "ZkAiD128ResidualAddEnvelope",
    "zkai_d128_residual_add_input_from_json_str",
    "prove_zkai_d128_residual_add_envelope",
    "verify_zkai_d128_residual_add_envelope",
)

D128_GATE_VALUE_COMMITMENT_FIELDS = (
    "source_projection_input_row_commitment",
    "gate_matrix_root",
    "value_matrix_root",
    "gate_projection_output_commitment",
    "value_projection_output_commitment",
    "gate_value_projection_output_commitment",
    "gate_value_projection_mul_row_commitment",
    "proof_native_parameter_commitment",
    "statement_commitment",
    "public_instance_commitment",
)

D128_ACTIVATION_COMMITMENT_FIELDS = (
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
    "statement_commitment",
    "public_instance_commitment",
)

D128_DOWN_COMMITMENT_FIELDS = (
    "source_activation_swiglu_statement_commitment",
    "source_activation_swiglu_public_instance_commitment",
    "source_hidden_activation_commitment",
    "down_matrix_root",
    "proof_native_parameter_commitment",
    "residual_delta_commitment",
    "residual_delta_scale_divisor",
    "down_projection_mul_row_commitment",
    "statement_commitment",
    "public_instance_commitment",
)

D128_RESIDUAL_COMMITMENT_FIELDS = (
    "source_rmsnorm_statement_commitment",
    "source_down_projection_statement_commitment",
    "source_down_projection_public_instance_commitment",
    "input_activation_commitment",
    "residual_delta_commitment",
    "residual_delta_scale_divisor",
    "residual_delta_remainder_sha256",
    "output_activation_commitment",
    "residual_add_row_commitment",
    "proof_native_parameter_commitment",
    "statement_commitment",
    "public_instance_commitment",
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
    "python3 scripts/zkai_d128_rmsnorm_public_row_proof_input.py --write-json docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_gate_value_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_activation_swiglu_proof_input.py --write-json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_down_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_residual_add_proof_input.py --write-json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_vector_residual_add_proof_input.py --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv",
    "python3 scripts/zkai_d128_block_receipt_composition_gate.py --write-json docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv",
    "python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_projection_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_activation_swiglu_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_residual_add_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_public_row_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_vector_residual_add_proof_input",
    "python3 -m unittest scripts.tests.test_zkai_d128_block_receipt_composition_gate",
    "cargo +nightly-2025-07-14 test d128_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test d128_native_gate_value_projection_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test d128_native_activation_swiglu_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test d128_native_down_projection_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 test d128_native_residual_add_proof --lib --features stwo-backend",
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
    ("d128_gate_value_projection_route_promoted", "backend_routes"),
    ("partial_d128_gate_value_projection_proof_removed", "proof_status"),
    ("partial_d128_gate_value_projection_verifier_removed", "proof_status"),
    ("partial_d128_gate_value_projection_local_roundtrip_removed", "proof_status"),
    ("partial_d128_gate_value_projection_checked_in_artifact_smuggled", "proof_status"),
    ("d128_gate_value_projection_gate_matrix_root_drift", "source_probe"),
    ("d128_gate_value_projection_value_matrix_root_drift", "source_probe"),
    ("d128_gate_value_projection_mul_row_commitment_drift", "source_probe"),
    ("d128_gate_value_projection_proof_native_parameter_commitment_drift", "source_probe"),
    ("d128_gate_value_projection_statement_commitment_drift", "source_probe"),
    ("d128_gate_value_projection_public_instance_commitment_drift", "source_probe"),
    ("d128_gate_value_projection_route_statement_commitment_drift", "backend_routes"),
    ("d128_activation_swiglu_route_promoted", "backend_routes"),
    ("partial_d128_activation_swiglu_proof_removed", "proof_status"),
    ("partial_d128_activation_swiglu_verifier_removed", "proof_status"),
    ("partial_d128_activation_swiglu_local_roundtrip_removed", "proof_status"),
    ("partial_d128_activation_swiglu_checked_in_artifact_smuggled", "proof_status"),
    ("d128_activation_swiglu_source_statement_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_source_proof_version_drift", "source_probe"),
    ("d128_activation_swiglu_source_gate_projection_output_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_source_value_projection_output_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_source_output_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_activation_lookup_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_hidden_activation_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_hidden_relabels_full_output", "source_probe"),
    ("d128_activation_swiglu_row_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_statement_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_public_instance_commitment_drift", "source_probe"),
    ("d128_activation_swiglu_route_statement_commitment_drift", "backend_routes"),
    ("d128_down_projection_route_promoted", "backend_routes"),
    ("partial_d128_down_projection_proof_removed", "proof_status"),
    ("partial_d128_down_projection_verifier_removed", "proof_status"),
    ("partial_d128_down_projection_local_roundtrip_removed", "proof_status"),
    ("partial_d128_down_projection_checked_in_artifact_smuggled", "proof_status"),
    ("d128_down_projection_source_hidden_commitment_drift", "source_probe"),
    ("d128_down_projection_source_statement_commitment_drift", "source_probe"),
    ("d128_down_projection_source_public_instance_commitment_drift", "source_probe"),
    ("d128_down_projection_down_matrix_root_drift", "source_probe"),
    ("d128_down_projection_residual_delta_commitment_drift", "source_probe"),
    ("d128_down_projection_residual_delta_scale_divisor_drift", "source_probe"),
    ("d128_down_projection_residual_delta_remainder_sha256_drift", "source_probe"),
    ("d128_down_projection_range_policy_drift", "source_probe"),
    ("d128_down_projection_residual_delta_relabels_full_output", "source_probe"),
    ("d128_down_projection_row_commitment_drift", "source_probe"),
    ("d128_down_projection_statement_commitment_drift", "source_probe"),
    ("d128_down_projection_public_instance_commitment_drift", "source_probe"),
    ("d128_down_projection_route_statement_commitment_drift", "backend_routes"),
    ("d128_down_projection_route_remainder_sha256_drift", "backend_routes"),
    ("d128_down_projection_route_range_policy_drift", "backend_routes"),
    ("d128_residual_add_route_promoted", "backend_routes"),
    ("partial_d128_residual_add_proof_removed", "proof_status"),
    ("partial_d128_residual_add_verifier_removed", "proof_status"),
    ("partial_d128_residual_add_local_roundtrip_removed", "proof_status"),
    ("partial_d128_residual_add_checked_in_artifact_smuggled", "proof_status"),
    ("d128_residual_add_source_rmsnorm_statement_commitment_drift", "source_probe"),
    ("d128_residual_add_source_down_statement_commitment_drift", "source_probe"),
    ("d128_residual_add_source_down_public_instance_commitment_drift", "source_probe"),
    ("d128_residual_add_input_activation_commitment_drift", "source_probe"),
    ("d128_residual_add_residual_delta_commitment_drift", "source_probe"),
    ("d128_residual_add_residual_delta_scale_divisor_drift", "source_probe"),
    ("d128_residual_add_residual_delta_remainder_sha256_drift", "source_probe"),
    ("d128_residual_add_range_policy_drift", "source_probe"),
    ("d128_residual_add_output_commitment_drift", "source_probe"),
    ("d128_residual_add_row_commitment_drift", "source_probe"),
    ("d128_residual_add_statement_commitment_drift", "source_probe"),
    ("d128_residual_add_public_instance_commitment_drift", "source_probe"),
    ("d128_residual_add_relabels_full_output", "source_probe"),
    ("d128_residual_add_route_statement_commitment_drift", "backend_routes"),
    ("d128_residual_add_route_output_commitment_drift", "backend_routes"),
    ("full_block_parameterized_route_promoted", "backend_routes"),
    ("d128_block_receipt_composition_route_status_drift", "backend_routes"),
    ("d128_block_receipt_composition_route_commitment_drift", "backend_routes"),
    ("d128_block_receipt_composition_route_receipt_flag_drift", "backend_routes"),
    ("d128_block_receipt_composition_proof_artifact_exists_drift", "backend_routes"),
    ("d128_block_receipt_composition_mutations_rejected_drift", "source_probe"),
    ("d128_block_receipt_composition_synchronized_commitment_drift", "source_probe"),
    ("d128_block_receipt_composition_evidence_descriptor_drift", "source_probe"),
    ("d64_anchor_removed", "d64_anchor"),
    ("missing_module_removed", "source_probe"),
    ("d64_hardcoded_marker_removed", "source_probe"),
    ("non_claim_removed", "claim_boundary"),
    ("mutation_case_accepted", "mutation_harness"),
)


class D128BackendSpikeError(ValueError):
    pass


def _open_repo_regular_file(path: pathlib.Path | str) -> tuple[int, pathlib.Path]:
    candidate = pathlib.Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        if candidate.is_symlink():
            raise D128BackendSpikeError(f"source file must not be a symlink: {path}")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as err:
            raise D128BackendSpikeError(f"source file escapes repository: {path}") from err
        pre_stat = resolved.lstat()
        if not stat_module.S_ISREG(pre_stat.st_mode):
            raise D128BackendSpikeError(f"source file is not a regular file: {path}")
        fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            post_stat = os.fstat(fd)
            if not stat_module.S_ISREG(post_stat.st_mode):
                raise D128BackendSpikeError(f"source file is not a regular file: {path}")
            if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
                raise D128BackendSpikeError(f"source file changed while reading: {path}")
            opened_fd = fd
            fd = None
            return opened_fd, resolved
        finally:
            if fd is not None:
                os.close(fd)
    except OSError as err:
        raise D128BackendSpikeError(f"failed to read source file {path}: {err}") from err


def _read_repo_regular_file_bytes(path: pathlib.Path | str) -> tuple[bytes, pathlib.Path]:
    fd, resolved = _open_repo_regular_file(path)
    with os.fdopen(fd, "rb") as handle:
        return handle.read(), resolved


def _load_module(path: pathlib.Path, module_name: str) -> Any:
    source, resolved = _read_repo_regular_file_bytes(path)
    spec = importlib.util.spec_from_loader(module_name, loader=None, origin=str(resolved))
    if spec is None:
        raise D128BackendSpikeError(f"failed to load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(resolved)
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(resolved), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


TARGET_GATE = _load_module(TARGET_GATE_PATH, "zkai_d128_target_for_backend_spike")
D64_BLOCK_GATE = _load_module(D64_BLOCK_GATE_PATH, "zkai_d64_block_for_d128_backend_spike")
VECTOR_RESIDUAL_GATE = _load_module(
    VECTOR_RESIDUAL_GATE_PATH,
    "zkai_d128_vector_residual_add_for_backend_spike",
)
D128_RESIDUAL_GATE = _load_module(
    D128_RESIDUAL_GATE_PATH,
    "zkai_d128_residual_add_for_backend_spike",
)
D128_RMSNORM_GATE = _load_module(
    D128_RMSNORM_GATE_PATH,
    "zkai_d128_rmsnorm_public_row_for_backend_spike",
)
D128_BRIDGE_GATE = _load_module(
    D128_BRIDGE_GATE_PATH,
    "zkai_d128_rmsnorm_to_projection_bridge_for_backend_spike",
)
D128_GATE_VALUE_GATE = _load_module(
    D128_GATE_VALUE_GATE_PATH,
    "zkai_d128_gate_value_projection_for_backend_spike",
)
D128_ACTIVATION_GATE = _load_module(
    D128_ACTIVATION_GATE_PATH,
    "zkai_d128_activation_swiglu_for_backend_spike",
)
D128_DOWN_GATE = _load_module(
    D128_DOWN_GATE_PATH,
    "zkai_d128_down_projection_for_backend_spike",
)
D128_BLOCK_GATE = _load_module(
    D128_BLOCK_GATE_PATH,
    "zkai_d128_block_receipt_composition_for_backend_spike",
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
    fd, _resolved = _open_repo_regular_file(path)
    digest = hashlib.sha256()
    with os.fdopen(fd, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


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
    source_bytes, _resolved = _read_repo_regular_file_bytes(path)
    try:
        payload = json.loads(source_bytes.decode("utf-8"))
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


def authoritative_d128_block_evidence_descriptor() -> dict[str, Any]:
    return source_descriptor(
        D128_BLOCK_EVIDENCE,
        load_json(D128_BLOCK_EVIDENCE),
    )


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
    source_bytes, _resolved = _read_repo_regular_file_bytes(path)
    try:
        return source_bytes.decode("utf-8")
    except UnicodeDecodeError as err:
        raise D128BackendSpikeError(f"required source file is not valid UTF-8: {path}") from err


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

    d128_gate_value_module_path = "src/stwo_backend/d128_native_gate_value_projection_proof.rs"
    d128_gate_value_module = read_repo_file(d128_gate_value_module_path)
    if "mod d128_native_gate_value_projection_proof;" not in mod_rs:
        raise D128BackendSpikeError("d128 gate/value projection module missing from mod.rs")
    missing_d128_gate_value_symbols = []
    for symbol in D128_GATE_VALUE_SYMBOLS:
        if not rust_declares_symbol(
            d128_gate_value_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "d128_native_gate_value_projection_proof", symbol):
            missing_d128_gate_value_symbols.append(symbol)
    if missing_d128_gate_value_symbols:
        raise D128BackendSpikeError(
            "d128 gate/value projection route disappeared; refresh this partial-go gate"
        )

    d128_gate_value_evidence = load_json(D128_GATE_VALUE_EVIDENCE)
    try:
        D128_GATE_VALUE_GATE.validate_payload(d128_gate_value_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 gate/value projection evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-d128-gate-value-projection-air-proof-input-v1",
        "decision": "GO_INPUT_FOR_D128_GATE_VALUE_PROJECTION_AIR_PROOF",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "ff_dim": TARGET_FF_DIM,
        "row_count": 2 * TARGET_FF_DIM * TARGET_WIDTH,
        "gate_projection_mul_rows": TARGET_FF_DIM * TARGET_WIDTH,
        "value_projection_mul_rows": TARGET_FF_DIM * TARGET_WIDTH,
    }.items():
        expect_equal(d128_gate_value_evidence.get(field), expected, f"d128 gate/value projection {field}")
    expect_equal(
        d128_gate_value_evidence.get("source_projection_input_row_commitment"),
        d128_bridge_evidence.get("projection_input_row_commitment"),
        "d128 gate/value source projection-input commitment",
    )
    if d128_gate_value_evidence.get("gate_value_projection_output_commitment") == D128_BRIDGE_GATE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT:
        raise D128BackendSpikeError("d128 gate/value output commitment relabeled as full output")

    d128_activation_module_path = "src/stwo_backend/d128_native_activation_swiglu_proof.rs"
    d128_activation_module = read_repo_file(d128_activation_module_path)
    if "mod d128_native_activation_swiglu_proof;" not in mod_rs:
        raise D128BackendSpikeError("d128 activation/SwiGLU module missing from mod.rs")
    missing_d128_activation_symbols = []
    for symbol in D128_ACTIVATION_SYMBOLS:
        if not rust_declares_symbol(
            d128_activation_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "d128_native_activation_swiglu_proof", symbol):
            missing_d128_activation_symbols.append(symbol)
    if missing_d128_activation_symbols:
        raise D128BackendSpikeError(
            "d128 activation/SwiGLU route disappeared; refresh this partial-go gate"
        )

    d128_activation_evidence = load_json(D128_ACTIVATION_EVIDENCE)
    try:
        D128_ACTIVATION_GATE.validate_payload(d128_activation_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 activation/SwiGLU evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-d128-activation-swiglu-air-proof-input-v1",
        "decision": "GO_INPUT_FOR_D128_ACTIVATION_SWIGLU_AIR_PROOF",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "ff_dim": TARGET_FF_DIM,
        "row_count": TARGET_FF_DIM,
        "activation_lookup_rows": D128_ACTIVATION_GATE.ACTIVATION_TABLE_ROWS,
        "swiglu_mix_rows": TARGET_FF_DIM,
    }.items():
        expect_equal(d128_activation_evidence.get(field), expected, f"d128 activation/SwiGLU {field}")
    expect_equal(
        d128_activation_evidence.get("source_gate_value_projection_output_commitment"),
        d128_gate_value_evidence.get("gate_value_projection_output_commitment"),
        "d128 activation source gate/value output commitment",
    )
    expect_equal(
        d128_activation_evidence.get("source_gate_value_projection_statement_commitment"),
        d128_gate_value_evidence.get("statement_commitment"),
        "d128 activation source gate/value statement commitment",
    )
    expect_equal(
        d128_activation_evidence.get("source_gate_value_projection_public_instance_commitment"),
        d128_gate_value_evidence.get("public_instance_commitment"),
        "d128 activation source gate/value public-instance commitment",
    )
    expect_equal(
        d128_activation_evidence.get("source_gate_projection_output_commitment"),
        d128_gate_value_evidence.get("gate_projection_output_commitment"),
        "d128 activation source gate projection output commitment",
    )
    expect_equal(
        d128_activation_evidence.get("source_value_projection_output_commitment"),
        d128_gate_value_evidence.get("value_projection_output_commitment"),
        "d128 activation source value projection output commitment",
    )
    if d128_activation_evidence.get("hidden_activation_commitment") == D128_ACTIVATION_GATE.OUTPUT_ACTIVATION_COMMITMENT:
        raise D128BackendSpikeError("d128 activation hidden commitment relabeled as full output")

    d128_down_module_path = "src/stwo_backend/d128_native_down_projection_proof.rs"
    d128_down_module = read_repo_file(d128_down_module_path)
    if "mod d128_native_down_projection_proof;" not in mod_rs:
        raise D128BackendSpikeError("d128 down-projection module missing from mod.rs")
    missing_d128_down_symbols = []
    for symbol in D128_DOWN_SYMBOLS:
        if not rust_declares_symbol(
            d128_down_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "d128_native_down_projection_proof", symbol):
            missing_d128_down_symbols.append(symbol)
    if missing_d128_down_symbols:
        raise D128BackendSpikeError(
            "d128 down-projection route disappeared; refresh this partial-go gate"
        )

    d128_down_evidence = load_json(D128_DOWN_EVIDENCE)
    try:
        D128_DOWN_GATE.validate_payload(d128_down_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 down-projection evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-d128-down-projection-air-proof-input-v1",
        "decision": "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "ff_dim": TARGET_FF_DIM,
        "row_count": TARGET_WIDTH * TARGET_FF_DIM,
        "down_projection_mul_rows": TARGET_WIDTH * TARGET_FF_DIM,
        "residual_delta_rows": TARGET_WIDTH,
        "residual_delta_scale_divisor": TARGET_FF_DIM,
    }.items():
        expect_equal(d128_down_evidence.get(field), expected, f"d128 down-projection {field}")
    expect_equal(
        d128_down_evidence.get("source_hidden_activation_commitment"),
        d128_activation_evidence.get("hidden_activation_commitment"),
        "d128 down-projection source hidden activation commitment",
    )
    expect_equal(
        d128_down_evidence.get("source_activation_swiglu_statement_commitment"),
        d128_activation_evidence.get("statement_commitment"),
        "d128 down-projection source activation statement commitment",
    )
    expect_equal(
        d128_down_evidence.get("source_activation_swiglu_public_instance_commitment"),
        d128_activation_evidence.get("public_instance_commitment"),
        "d128 down-projection source activation public-instance commitment",
    )
    if d128_down_evidence.get("residual_delta_commitment") == D128_DOWN_GATE.OUTPUT_ACTIVATION_COMMITMENT:
        raise D128BackendSpikeError("d128 down-projection residual delta relabeled as full output")

    d128_residual_module_path = "src/stwo_backend/d128_native_residual_add_proof.rs"
    d128_residual_module = read_repo_file(d128_residual_module_path)
    if "mod d128_native_residual_add_proof;" not in mod_rs:
        raise D128BackendSpikeError("d128 residual-add module missing from mod.rs")
    missing_d128_residual_symbols = []
    for symbol in D128_RESIDUAL_SYMBOLS:
        if not rust_declares_symbol(
            d128_residual_module, symbol
        ) or not rust_reexports_symbol(mod_rs, "d128_native_residual_add_proof", symbol):
            missing_d128_residual_symbols.append(symbol)
    if missing_d128_residual_symbols:
        raise D128BackendSpikeError(
            "d128 source-bound residual-add route disappeared; refresh this partial-go gate"
        )

    d128_residual_evidence = load_json(D128_RESIDUAL_EVIDENCE)
    try:
        D128_RESIDUAL_GATE.validate_payload(d128_residual_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 residual-add evidence failed validation") from err
    for field, expected in {
        "schema": "zkai-d128-residual-add-air-proof-input-v1",
        "decision": "GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF",
        "target_id": TARGET_ID,
        "required_backend_version": REQUIRED_BACKEND_VERSION,
        "width": TARGET_WIDTH,
        "row_count": TARGET_WIDTH,
        "residual_delta_scale_divisor": TARGET_FF_DIM,
    }.items():
        expect_equal(d128_residual_evidence.get(field), expected, f"d128 residual-add {field}")
    expect_equal(
        d128_residual_evidence.get("source_rmsnorm_statement_commitment"),
        d128_rmsnorm_evidence.get("statement_commitment"),
        "d128 residual-add source RMSNorm statement commitment",
    )
    expect_equal(
        d128_residual_evidence.get("source_down_projection_statement_commitment"),
        d128_down_evidence.get("statement_commitment"),
        "d128 residual-add source down-projection statement commitment",
    )
    expect_equal(
        d128_residual_evidence.get("source_down_projection_public_instance_commitment"),
        d128_down_evidence.get("public_instance_commitment"),
        "d128 residual-add source down-projection public-instance commitment",
    )
    expect_equal(
        d128_residual_evidence.get("residual_delta_commitment"),
        d128_down_evidence.get("residual_delta_commitment"),
        "d128 residual-add source residual-delta commitment",
    )
    expect_equal(
        d128_residual_evidence.get("residual_delta_remainder_sha256"),
        sha256_hex_json(d128_down_evidence["residual_delta_remainder_q8"]),
        "d128 residual-add residual delta remainder hash",
    )
    expect_equal(
        d128_residual_evidence.get("input_activation_commitment"),
        d128_rmsnorm_evidence.get("input_activation_commitment"),
        "d128 residual-add input activation commitment",
    )
    if d128_residual_evidence.get("residual_delta_commitment") == d128_residual_evidence.get("output_activation_commitment"):
        raise D128BackendSpikeError("d128 residual-add residual delta relabeled as full output")
    if d128_residual_evidence.get("input_activation_commitment") == d128_residual_evidence.get("output_activation_commitment"):
        raise D128BackendSpikeError("d128 residual-add input activation relabeled as full output")

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

    block_receipt_evidence = load_json(D128_BLOCK_EVIDENCE)
    try:
        D128_BLOCK_GATE.validate_payload(block_receipt_evidence)
    except Exception as err:
        raise D128BackendSpikeError("d128 block receipt composition evidence failed validation") from err
    expect_equal(
        block_receipt_evidence.get("decision"),
        D128_BLOCK_GATE.DECISION,
        "d128 block receipt decision",
    )
    block_summary = require_object(block_receipt_evidence.get("summary"), "d128 block receipt summary")
    expect_equal(block_summary.get("slice_count"), 6, "d128 block receipt slice count")
    expect_equal(block_summary.get("total_checked_rows"), 197_504, "d128 block receipt checked rows")
    expect_equal(
        block_summary.get("output_activation_commitment"),
        d128_residual_evidence["output_activation_commitment"],
        "d128 block receipt output activation",
    )
    block_receipt = require_object(block_receipt_evidence.get("block_receipt"), "d128 block receipt")
    expect_equal(
        block_receipt.get("output_activation_commitment"),
        d128_residual_evidence["output_activation_commitment"],
        "d128 block receipt final output",
    )

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
        "d128_gate_value_projection": {
            "status": "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY",
            "module": repo_file_descriptor(d128_gate_value_module_path),
            "evidence": source_descriptor(D128_GATE_VALUE_EVIDENCE, d128_gate_value_evidence),
            "present_symbols": list(D128_GATE_VALUE_SYMBOLS),
            "target_width": d128_gate_value_evidence["width"],
            "target_ff_dim": d128_gate_value_evidence["ff_dim"],
            "row_count": d128_gate_value_evidence["row_count"],
            "source_projection_input_row_commitment": d128_gate_value_evidence["source_projection_input_row_commitment"],
            "gate_matrix_root": d128_gate_value_evidence["gate_matrix_root"],
            "value_matrix_root": d128_gate_value_evidence["value_matrix_root"],
            "gate_projection_output_commitment": d128_gate_value_evidence["gate_projection_output_commitment"],
            "value_projection_output_commitment": d128_gate_value_evidence["value_projection_output_commitment"],
            "gate_value_projection_output_commitment": d128_gate_value_evidence["gate_value_projection_output_commitment"],
            "gate_value_projection_mul_row_commitment": d128_gate_value_evidence[
                "gate_value_projection_mul_row_commitment"
            ],
            "proof_native_parameter_commitment": d128_gate_value_evidence["proof_native_parameter_commitment"],
            "statement_commitment": d128_gate_value_evidence["statement_commitment"],
            "public_instance_commitment": d128_gate_value_evidence["public_instance_commitment"],
            "projection_output_relabels_full_output": (
                d128_gate_value_evidence["gate_value_projection_output_commitment"]
                == D128_BRIDGE_GATE.FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT
            ),
        },
        "d128_activation_swiglu": {
            "status": "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY",
            "module": repo_file_descriptor(d128_activation_module_path),
            "evidence": source_descriptor(D128_ACTIVATION_EVIDENCE, d128_activation_evidence),
            "present_symbols": list(D128_ACTIVATION_SYMBOLS),
            "target_width": d128_activation_evidence["width"],
            "target_ff_dim": d128_activation_evidence["ff_dim"],
            "row_count": d128_activation_evidence["row_count"],
            "activation_lookup_rows": d128_activation_evidence["activation_lookup_rows"],
            "swiglu_mix_rows": d128_activation_evidence["swiglu_mix_rows"],
            "source_gate_value_projection_proof_version": d128_activation_evidence[
                "source_gate_value_projection_proof_version"
            ],
            "scale_q8": d128_activation_evidence["scale_q8"],
            "activation_clamp_q8": d128_activation_evidence["activation_clamp_q8"],
            "source_gate_value_projection_statement_commitment": d128_activation_evidence[
                "source_gate_value_projection_statement_commitment"
            ],
            "source_gate_value_projection_public_instance_commitment": d128_activation_evidence[
                "source_gate_value_projection_public_instance_commitment"
            ],
            "source_gate_projection_output_commitment": d128_activation_evidence[
                "source_gate_projection_output_commitment"
            ],
            "source_value_projection_output_commitment": d128_activation_evidence[
                "source_value_projection_output_commitment"
            ],
            "source_gate_value_projection_output_commitment": d128_activation_evidence[
                "source_gate_value_projection_output_commitment"
            ],
            "activation_lookup_commitment": d128_activation_evidence["activation_lookup_commitment"],
            "proof_native_parameter_commitment": d128_activation_evidence["proof_native_parameter_commitment"],
            "activation_output_commitment": d128_activation_evidence["activation_output_commitment"],
            "hidden_activation_commitment": d128_activation_evidence["hidden_activation_commitment"],
            "activation_swiglu_row_commitment": d128_activation_evidence["activation_swiglu_row_commitment"],
            "statement_commitment": d128_activation_evidence["statement_commitment"],
            "public_instance_commitment": d128_activation_evidence["public_instance_commitment"],
            "hidden_relabels_full_output": (
                d128_activation_evidence["hidden_activation_commitment"]
                == D128_ACTIVATION_GATE.OUTPUT_ACTIVATION_COMMITMENT
            ),
        },
        "d128_down_projection": {
            "status": "GO_PARTIAL_D128_DOWN_PROJECTION_ONLY",
            "module": repo_file_descriptor(d128_down_module_path),
            "evidence": source_descriptor(D128_DOWN_EVIDENCE, d128_down_evidence),
            "present_symbols": list(D128_DOWN_SYMBOLS),
            "target_width": d128_down_evidence["width"],
            "target_ff_dim": d128_down_evidence["ff_dim"],
            "row_count": d128_down_evidence["row_count"],
            "down_projection_mul_rows": d128_down_evidence["down_projection_mul_rows"],
            "residual_delta_rows": d128_down_evidence["residual_delta_rows"],
            "residual_delta_scale_divisor": d128_down_evidence["residual_delta_scale_divisor"],
            "residual_delta_remainder_sha256": sha256_hex_json(d128_down_evidence["residual_delta_remainder_q8"]),
            "source_activation_swiglu_proof_version": d128_down_evidence[
                "source_activation_swiglu_proof_version"
            ],
            "source_activation_swiglu_statement_commitment": d128_down_evidence[
                "source_activation_swiglu_statement_commitment"
            ],
            "source_activation_swiglu_public_instance_commitment": d128_down_evidence[
                "source_activation_swiglu_public_instance_commitment"
            ],
            "source_hidden_activation_commitment": d128_down_evidence["source_hidden_activation_commitment"],
            "down_matrix_root": d128_down_evidence["down_matrix_root"],
            "proof_native_parameter_commitment": d128_down_evidence["proof_native_parameter_commitment"],
            "residual_delta_commitment": d128_down_evidence["residual_delta_commitment"],
            "down_projection_mul_row_commitment": d128_down_evidence["down_projection_mul_row_commitment"],
            "statement_commitment": d128_down_evidence["statement_commitment"],
            "public_instance_commitment": d128_down_evidence["public_instance_commitment"],
            "residual_delta_relabels_full_output": (
                d128_down_evidence["residual_delta_commitment"] == D128_DOWN_GATE.OUTPUT_ACTIVATION_COMMITMENT
            ),
            "range_policy": D128_DOWN_GATE.RANGE_POLICY,
        },
        "d128_residual_add": {
            "status": "GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY",
            "module": repo_file_descriptor(d128_residual_module_path),
            "evidence": source_descriptor(D128_RESIDUAL_EVIDENCE, d128_residual_evidence),
            "present_symbols": list(D128_RESIDUAL_SYMBOLS),
            "target_width": d128_residual_evidence["width"],
            "row_count": d128_residual_evidence["row_count"],
            "source_rmsnorm_proof_version": d128_residual_evidence["source_rmsnorm_proof_version"],
            "source_rmsnorm_statement_commitment": d128_residual_evidence[
                "source_rmsnorm_statement_commitment"
            ],
            "source_down_projection_proof_version": d128_residual_evidence[
                "source_down_projection_proof_version"
            ],
            "source_down_projection_statement_commitment": d128_residual_evidence[
                "source_down_projection_statement_commitment"
            ],
            "source_down_projection_public_instance_commitment": d128_residual_evidence[
                "source_down_projection_public_instance_commitment"
            ],
            "input_activation_commitment": d128_residual_evidence["input_activation_commitment"],
            "residual_delta_commitment": d128_residual_evidence["residual_delta_commitment"],
            "residual_delta_scale_divisor": d128_residual_evidence["residual_delta_scale_divisor"],
            "residual_delta_remainder_sha256": d128_residual_evidence["residual_delta_remainder_sha256"],
            "range_policy": d128_residual_evidence["range_policy"],
            "output_activation_commitment": d128_residual_evidence["output_activation_commitment"],
            "residual_add_row_commitment": d128_residual_evidence["residual_add_row_commitment"],
            "proof_native_parameter_commitment": d128_residual_evidence["proof_native_parameter_commitment"],
            "statement_commitment": d128_residual_evidence["statement_commitment"],
            "public_instance_commitment": d128_residual_evidence["public_instance_commitment"],
            "residual_delta_relabels_full_output": (
                d128_residual_evidence["residual_delta_commitment"]
                == d128_residual_evidence["output_activation_commitment"]
            ),
            "input_relabels_output": (
                d128_residual_evidence["input_activation_commitment"]
                == d128_residual_evidence["output_activation_commitment"]
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
        "d128_block_receipt_composition": {
            "status": "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE",
            "evidence": source_descriptor(D128_BLOCK_EVIDENCE, block_receipt_evidence),
            "slice_count": block_summary["slice_count"],
            "total_checked_rows": block_summary["total_checked_rows"],
            "mutation_cases": block_receipt_evidence["case_count"],
            "mutations_rejected": block_summary["mutations_rejected"],
            "statement_commitment": block_receipt["statement_commitment"],
            "block_receipt_commitment": block_receipt["block_receipt_commitment"],
            "output_activation_commitment": block_receipt["output_activation_commitment"],
            "non_claims": block_receipt_evidence["non_claims"],
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
            "blocker": "d128 RMSNorm public-row, bridge, gate/value, activation, down-projection, and source-bound residual-add native proofs exist, and a statement-bound receipt composition gate exists, but no aggregated/native full-block proof object exists",
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
            "route": "direct_d128_gate_value_projection_air",
            "status": "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "gate/value projection slice only; not activation, down-projection, residual, composition, or full block",
            "evidence": "docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json",
            "present_symbols": source_probe["d128_gate_value_projection"]["present_symbols"],
            "source_projection_input_row_commitment": source_probe["d128_gate_value_projection"][
                "source_projection_input_row_commitment"
            ],
            "gate_matrix_root": source_probe["d128_gate_value_projection"]["gate_matrix_root"],
            "value_matrix_root": source_probe["d128_gate_value_projection"]["value_matrix_root"],
            "gate_projection_output_commitment": source_probe["d128_gate_value_projection"][
                "gate_projection_output_commitment"
            ],
            "value_projection_output_commitment": source_probe["d128_gate_value_projection"][
                "value_projection_output_commitment"
            ],
            "gate_value_projection_output_commitment": source_probe["d128_gate_value_projection"][
                "gate_value_projection_output_commitment"
            ],
            "gate_value_projection_mul_row_commitment": source_probe["d128_gate_value_projection"][
                "gate_value_projection_mul_row_commitment"
            ],
            "proof_native_parameter_commitment": source_probe["d128_gate_value_projection"][
                "proof_native_parameter_commitment"
            ],
            "statement_commitment": source_probe["d128_gate_value_projection"]["statement_commitment"],
            "public_instance_commitment": source_probe["d128_gate_value_projection"][
                "public_instance_commitment"
            ],
        },
        {
            "route": "direct_d128_activation_swiglu_air",
            "status": "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "activation/SwiGLU slice only; not down-projection, residual, composition, or full block",
            "evidence": "docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json",
            "present_symbols": source_probe["d128_activation_swiglu"]["present_symbols"],
            "source_gate_value_projection_statement_commitment": source_probe["d128_activation_swiglu"][
                "source_gate_value_projection_statement_commitment"
            ],
            "source_gate_value_projection_public_instance_commitment": source_probe["d128_activation_swiglu"][
                "source_gate_value_projection_public_instance_commitment"
            ],
            "source_gate_projection_output_commitment": source_probe["d128_activation_swiglu"][
                "source_gate_projection_output_commitment"
            ],
            "source_value_projection_output_commitment": source_probe["d128_activation_swiglu"][
                "source_value_projection_output_commitment"
            ],
            "source_gate_value_projection_output_commitment": source_probe["d128_activation_swiglu"][
                "source_gate_value_projection_output_commitment"
            ],
            "activation_output_commitment": source_probe["d128_activation_swiglu"][
                "activation_output_commitment"
            ],
            "activation_lookup_commitment": source_probe["d128_activation_swiglu"][
                "activation_lookup_commitment"
            ],
            "hidden_activation_commitment": source_probe["d128_activation_swiglu"][
                "hidden_activation_commitment"
            ],
            "activation_swiglu_row_commitment": source_probe["d128_activation_swiglu"][
                "activation_swiglu_row_commitment"
            ],
            "proof_native_parameter_commitment": source_probe["d128_activation_swiglu"][
                "proof_native_parameter_commitment"
            ],
            "statement_commitment": source_probe["d128_activation_swiglu"]["statement_commitment"],
            "public_instance_commitment": source_probe["d128_activation_swiglu"][
                "public_instance_commitment"
            ],
        },
        {
            "route": "direct_d128_down_projection_air",
            "status": "GO_PARTIAL_D128_DOWN_PROJECTION_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "down-projection slice only; not source-bound residual-add, composition, or full block",
            "evidence": "docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json",
            "present_symbols": source_probe["d128_down_projection"]["present_symbols"],
            "source_activation_swiglu_statement_commitment": source_probe["d128_down_projection"][
                "source_activation_swiglu_statement_commitment"
            ],
            "source_activation_swiglu_public_instance_commitment": source_probe["d128_down_projection"][
                "source_activation_swiglu_public_instance_commitment"
            ],
            "source_hidden_activation_commitment": source_probe["d128_down_projection"][
                "source_hidden_activation_commitment"
            ],
            "down_matrix_root": source_probe["d128_down_projection"]["down_matrix_root"],
            "proof_native_parameter_commitment": source_probe["d128_down_projection"][
                "proof_native_parameter_commitment"
            ],
            "residual_delta_commitment": source_probe["d128_down_projection"]["residual_delta_commitment"],
            "residual_delta_scale_divisor": source_probe["d128_down_projection"]["residual_delta_scale_divisor"],
            "residual_delta_remainder_sha256": source_probe["d128_down_projection"]["residual_delta_remainder_sha256"],
            "range_policy": source_probe["d128_down_projection"]["range_policy"],
            "down_projection_mul_row_commitment": source_probe["d128_down_projection"][
                "down_projection_mul_row_commitment"
            ],
            "statement_commitment": source_probe["d128_down_projection"]["statement_commitment"],
            "public_instance_commitment": source_probe["d128_down_projection"]["public_instance_commitment"],
        },
        {
            "route": "direct_d128_residual_add_air",
            "status": "GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": None,
            "proof_artifact_exists": True,
            "verifier_handle_exists": True,
            "local_roundtrip_proof_constructed": True,
            "checked_in_proof_artifact_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "source-bound residual-add slice only; not composed with the previous d128 slices into a full block receipt",
            "evidence": "docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json",
            "present_symbols": source_probe["d128_residual_add"]["present_symbols"],
            "source_rmsnorm_statement_commitment": source_probe["d128_residual_add"][
                "source_rmsnorm_statement_commitment"
            ],
            "source_down_projection_statement_commitment": source_probe["d128_residual_add"][
                "source_down_projection_statement_commitment"
            ],
            "source_down_projection_public_instance_commitment": source_probe["d128_residual_add"][
                "source_down_projection_public_instance_commitment"
            ],
            "input_activation_commitment": source_probe["d128_residual_add"]["input_activation_commitment"],
            "residual_delta_commitment": source_probe["d128_residual_add"]["residual_delta_commitment"],
            "residual_delta_scale_divisor": source_probe["d128_residual_add"]["residual_delta_scale_divisor"],
            "residual_delta_remainder_sha256": source_probe["d128_residual_add"][
                "residual_delta_remainder_sha256"
            ],
            "range_policy": source_probe["d128_residual_add"]["range_policy"],
            "output_activation_commitment": source_probe["d128_residual_add"]["output_activation_commitment"],
            "residual_add_row_commitment": source_probe["d128_residual_add"]["residual_add_row_commitment"],
            "proof_native_parameter_commitment": source_probe["d128_residual_add"][
                "proof_native_parameter_commitment"
            ],
            "statement_commitment": source_probe["d128_residual_add"]["statement_commitment"],
            "public_instance_commitment": source_probe["d128_residual_add"]["public_instance_commitment"],
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
            "status": "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": False,
            "verifier_handle_exists": False,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": FIRST_BLOCKER,
            "blocker_detail": FIRST_BLOCKER_DETAIL,
            "missing_symbols": source_probe["missing_parameterized_full_block_symbols"],
        },
        {
            "route": "d128_block_receipt_composition",
            "status": "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE",
            "target_width": TARGET_WIDTH,
            "target_ff_dim": TARGET_FF_DIM,
            "proof_artifact_exists": False,
            "verifier_handle_exists": True,
            "receipt_artifact_exists": True,
            "proof_size_bytes": None,
            "verifier_time_ms": None,
            "blocker": "receipt composition only; not recursive aggregation or one compressed verifier object",
            "evidence": "docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json",
            "block_receipt_commitment": source_probe["d128_block_receipt_composition"][
                "block_receipt_commitment"
            ],
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
        "first_blocker_detail": FIRST_BLOCKER_DETAIL,
        "d64_anchor_route": "GO_ANCHOR_ONLY",
        "direct_d128_route": "NO_GO_FULL_NATIVE_CHAIN_SLICES_MISSING",
        "d128_rmsnorm_public_row_route": "GO_PARTIAL_D128_RMSNORM_PUBLIC_ROWS_ONLY",
        "d128_rmsnorm_to_projection_bridge_route": "GO_D128_RMSNORM_TO_PROJECTION_BRIDGE_ONLY",
        "d128_gate_value_projection_route": "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY",
        "d128_activation_swiglu_route": "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY",
        "d128_down_projection_route": "GO_PARTIAL_D128_DOWN_PROJECTION_ONLY",
        "d128_residual_add_route": "GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY",
        "parameterized_residual_add_route": "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "d128_block_receipt_composition_route": "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE",
        "parameterized_full_block_route": "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING",
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
        "partial_d128_gate_value_projection_proof_exists": True,
        "partial_d128_gate_value_projection_verifier_exists": True,
        "partial_d128_gate_value_projection_local_roundtrip_proof_constructed": True,
        "partial_d128_gate_value_projection_checked_in_proof_artifact_exists": False,
        "partial_d128_activation_swiglu_proof_exists": True,
        "partial_d128_activation_swiglu_verifier_exists": True,
        "partial_d128_activation_swiglu_local_roundtrip_proof_constructed": True,
        "partial_d128_activation_swiglu_checked_in_proof_artifact_exists": False,
        "partial_d128_down_projection_proof_exists": True,
        "partial_d128_down_projection_verifier_exists": True,
        "partial_d128_down_projection_local_roundtrip_proof_constructed": True,
        "partial_d128_down_projection_checked_in_proof_artifact_exists": False,
        "partial_d128_residual_add_proof_exists": True,
        "partial_d128_residual_add_verifier_exists": True,
        "partial_d128_residual_add_local_roundtrip_proof_constructed": True,
        "partial_d128_residual_add_checked_in_proof_artifact_exists": False,
        "d128_block_receipt_composition_exists": True,
        "d128_block_receipt_composition_mutation_cases": source_probe["d128_block_receipt_composition"][
            "mutation_cases"
        ],
        "partial_parameterized_residual_add_proof_exists": True,
        "partial_parameterized_residual_add_verifier_exists": True,
        "partial_parameterized_residual_add_local_roundtrip_proof_constructed": True,
        "partial_parameterized_residual_add_checked_in_proof_artifact_exists": False,
        "statement_relabeling_suite_exists": False,
        "proof_size_bytes": None,
        "verifier_time_ms": None,
        "blocked_before_metrics": True,
        "first_blocker": FIRST_BLOCKER,
        "first_blocker_detail": FIRST_BLOCKER_DETAIL,
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

    def promote_d128_gate_value_projection_route(p: dict[str, Any]) -> None:
        p["summary"]["d128_gate_value_projection_route"] = "GO_D128_FULL_GATE_VALUE_BLOCK"
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_gate_value_projection_air")
        route["status"] = "GO_D128_FULL_GATE_VALUE_BLOCK"
        route["proof_size_bytes"] = 4096

    add(
        "d128_gate_value_projection_route_promoted",
        "backend_routes",
        promote_d128_gate_value_projection_route,
    )
    add(
        "partial_d128_gate_value_projection_proof_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_gate_value_projection_proof_exists", False),
    )
    add(
        "partial_d128_gate_value_projection_verifier_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_gate_value_projection_verifier_exists", False),
    )
    add(
        "partial_d128_gate_value_projection_local_roundtrip_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_gate_value_projection_local_roundtrip_proof_constructed", False
        ),
    )
    add(
        "partial_d128_gate_value_projection_checked_in_artifact_smuggled",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_gate_value_projection_checked_in_proof_artifact_exists", True
        ),
    )
    add(
        "d128_gate_value_projection_gate_matrix_root_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_gate_value_projection"].__setitem__(
            "gate_matrix_root", "blake2b-256:" + "41" * 32
        ),
    )
    add(
        "d128_gate_value_projection_value_matrix_root_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_gate_value_projection"].__setitem__(
            "value_matrix_root", "blake2b-256:" + "42" * 32
        ),
    )
    add(
        "d128_gate_value_projection_mul_row_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_gate_value_projection"].__setitem__(
            "gate_value_projection_mul_row_commitment", "blake2b-256:" + "43" * 32
        ),
    )
    add(
        "d128_gate_value_projection_proof_native_parameter_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_gate_value_projection"].__setitem__(
            "proof_native_parameter_commitment", "blake2b-256:" + "44" * 32
        ),
    )
    add(
        "d128_gate_value_projection_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_gate_value_projection"].__setitem__(
            "statement_commitment", "blake2b-256:" + "45" * 32
        ),
    )
    add(
        "d128_gate_value_projection_public_instance_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_gate_value_projection"].__setitem__(
            "public_instance_commitment", "blake2b-256:" + "46" * 32
        ),
    )

    def drift_d128_gate_value_projection_route_statement(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_gate_value_projection_air")
        route["statement_commitment"] = "blake2b-256:" + "47" * 32

    add(
        "d128_gate_value_projection_route_statement_commitment_drift",
        "backend_routes",
        drift_d128_gate_value_projection_route_statement,
    )

    def promote_d128_activation_swiglu_route(p: dict[str, Any]) -> None:
        p["summary"]["d128_activation_swiglu_route"] = "GO_D128_FULL_ACTIVATION_BLOCK"
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_activation_swiglu_air")
        route["status"] = "GO_D128_FULL_ACTIVATION_BLOCK"
        route["proof_size_bytes"] = 4096

    add(
        "d128_activation_swiglu_route_promoted",
        "backend_routes",
        promote_d128_activation_swiglu_route,
    )
    add(
        "partial_d128_activation_swiglu_proof_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_activation_swiglu_proof_exists", False),
    )
    add(
        "partial_d128_activation_swiglu_verifier_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_activation_swiglu_verifier_exists", False),
    )
    add(
        "partial_d128_activation_swiglu_local_roundtrip_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_activation_swiglu_local_roundtrip_proof_constructed", False
        ),
    )
    add(
        "partial_d128_activation_swiglu_checked_in_artifact_smuggled",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_activation_swiglu_checked_in_proof_artifact_exists", True
        ),
    )
    add(
        "d128_activation_swiglu_source_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "source_gate_value_projection_statement_commitment", "blake2b-256:" + "51" * 32
        ),
    )
    add(
        "d128_activation_swiglu_source_proof_version_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "source_gate_value_projection_proof_version", "stwo-d128-gate-value-projection-air-proof-v0"
        ),
    )
    add(
        "d128_activation_swiglu_source_gate_projection_output_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "source_gate_projection_output_commitment", "blake2b-256:" + "56" * 32
        ),
    )
    add(
        "d128_activation_swiglu_source_value_projection_output_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "source_value_projection_output_commitment", "blake2b-256:" + "57" * 32
        ),
    )
    add(
        "d128_activation_swiglu_source_output_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "source_gate_value_projection_output_commitment", "blake2b-256:" + "58" * 32
        ),
    )
    add(
        "d128_activation_swiglu_activation_lookup_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "activation_lookup_commitment", "blake2b-256:" + "52" * 32
        ),
    )
    add(
        "d128_activation_swiglu_hidden_activation_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "hidden_activation_commitment", "blake2b-256:" + "53" * 32
        ),
    )

    def relabel_d128_activation_swiglu_hidden_output(p: dict[str, Any]) -> None:
        activation = p["source_probe"]["d128_activation_swiglu"]
        activation["hidden_activation_commitment"] = D128_ACTIVATION_GATE.OUTPUT_ACTIVATION_COMMITMENT
        activation["hidden_relabels_full_output"] = True
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_activation_swiglu_air")
        route["hidden_activation_commitment"] = D128_ACTIVATION_GATE.OUTPUT_ACTIVATION_COMMITMENT

    add(
        "d128_activation_swiglu_hidden_relabels_full_output",
        "source_probe",
        relabel_d128_activation_swiglu_hidden_output,
    )
    add(
        "d128_activation_swiglu_row_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "activation_swiglu_row_commitment", "blake2b-256:" + "54" * 32
        ),
    )
    add(
        "d128_activation_swiglu_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "statement_commitment", "blake2b-256:" + "55" * 32
        ),
    )
    add(
        "d128_activation_swiglu_public_instance_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_activation_swiglu"].__setitem__(
            "public_instance_commitment", "blake2b-256:" + "56" * 32
        ),
    )

    def drift_d128_activation_swiglu_route_statement(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_activation_swiglu_air")
        route["statement_commitment"] = "blake2b-256:" + "57" * 32

    add(
        "d128_activation_swiglu_route_statement_commitment_drift",
        "backend_routes",
        drift_d128_activation_swiglu_route_statement,
    )

    def promote_d128_down_projection_route(p: dict[str, Any]) -> None:
        p["summary"]["d128_down_projection_route"] = "GO_D128_FULL_DOWN_PROJECTION_BLOCK"
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_down_projection_air")
        route["status"] = "GO_D128_FULL_DOWN_PROJECTION_BLOCK"
        route["proof_size_bytes"] = 4096

    add(
        "d128_down_projection_route_promoted",
        "backend_routes",
        promote_d128_down_projection_route,
    )
    add(
        "partial_d128_down_projection_proof_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_down_projection_proof_exists", False),
    )
    add(
        "partial_d128_down_projection_verifier_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_down_projection_verifier_exists", False),
    )
    add(
        "partial_d128_down_projection_local_roundtrip_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_down_projection_local_roundtrip_proof_constructed", False
        ),
    )
    add(
        "partial_d128_down_projection_checked_in_artifact_smuggled",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_down_projection_checked_in_proof_artifact_exists", True
        ),
    )
    add(
        "d128_down_projection_source_hidden_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "source_hidden_activation_commitment", "blake2b-256:" + "61" * 32
        ),
    )
    add(
        "d128_down_projection_source_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "source_activation_swiglu_statement_commitment", "blake2b-256:" + "62" * 32
        ),
    )
    add(
        "d128_down_projection_source_public_instance_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "source_activation_swiglu_public_instance_commitment", "blake2b-256:" + "69" * 32
        ),
    )
    add(
        "d128_down_projection_down_matrix_root_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "down_matrix_root", "blake2b-256:" + "63" * 32
        ),
    )
    add(
        "d128_down_projection_residual_delta_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "residual_delta_commitment", "blake2b-256:" + "64" * 32
        ),
    )
    add(
        "d128_down_projection_residual_delta_scale_divisor_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "residual_delta_scale_divisor", TARGET_FF_DIM + 1
        ),
    )
    add(
        "d128_down_projection_residual_delta_remainder_sha256_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "residual_delta_remainder_sha256", "00" * 32
        ),
    )
    add(
        "d128_down_projection_range_policy_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "range_policy", "q8 hidden activations"
        ),
    )

    def relabel_d128_down_projection_residual_output(p: dict[str, Any]) -> None:
        down = p["source_probe"]["d128_down_projection"]
        down["residual_delta_commitment"] = D128_DOWN_GATE.OUTPUT_ACTIVATION_COMMITMENT
        down["residual_delta_relabels_full_output"] = True
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_down_projection_air")
        route["residual_delta_commitment"] = D128_DOWN_GATE.OUTPUT_ACTIVATION_COMMITMENT

    add(
        "d128_down_projection_residual_delta_relabels_full_output",
        "source_probe",
        relabel_d128_down_projection_residual_output,
    )
    add(
        "d128_down_projection_row_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "down_projection_mul_row_commitment", "blake2b-256:" + "65" * 32
        ),
    )
    add(
        "d128_down_projection_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "statement_commitment", "blake2b-256:" + "66" * 32
        ),
    )
    add(
        "d128_down_projection_public_instance_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_down_projection"].__setitem__(
            "public_instance_commitment", "blake2b-256:" + "67" * 32
        ),
    )

    def drift_d128_down_projection_route_statement(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_down_projection_air")
        route["statement_commitment"] = "blake2b-256:" + "68" * 32

    add(
        "d128_down_projection_route_statement_commitment_drift",
        "backend_routes",
        drift_d128_down_projection_route_statement,
    )

    def drift_d128_down_projection_route_remainder_hash(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_down_projection_air")
        route["residual_delta_remainder_sha256"] = "11" * 32

    add(
        "d128_down_projection_route_remainder_sha256_drift",
        "backend_routes",
        drift_d128_down_projection_route_remainder_hash,
    )

    def drift_d128_down_projection_route_range_policy(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_down_projection_air")
        route["range_policy"] = "q8 hidden activations"

    add(
        "d128_down_projection_route_range_policy_drift",
        "backend_routes",
        drift_d128_down_projection_route_range_policy,
    )

    def promote_d128_residual_add_route(p: dict[str, Any]) -> None:
        p["summary"]["d128_residual_add_route"] = "GO_D128_FULL_RESIDUAL_BLOCK"
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_residual_add_air")
        route["status"] = "GO_D128_FULL_RESIDUAL_BLOCK"
        route["proof_size_bytes"] = 4096

    add(
        "d128_residual_add_route_promoted",
        "backend_routes",
        promote_d128_residual_add_route,
    )
    add(
        "partial_d128_residual_add_proof_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_residual_add_proof_exists", False),
    )
    add(
        "partial_d128_residual_add_verifier_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__("partial_d128_residual_add_verifier_exists", False),
    )
    add(
        "partial_d128_residual_add_local_roundtrip_removed",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_residual_add_local_roundtrip_proof_constructed", False
        ),
    )
    add(
        "partial_d128_residual_add_checked_in_artifact_smuggled",
        "proof_status",
        lambda p: p["proof_status"].__setitem__(
            "partial_d128_residual_add_checked_in_proof_artifact_exists", True
        ),
    )
    add(
        "d128_residual_add_source_rmsnorm_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "source_rmsnorm_statement_commitment", "blake2b-256:" + "71" * 32
        ),
    )
    add(
        "d128_residual_add_source_down_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "source_down_projection_statement_commitment", "blake2b-256:" + "72" * 32
        ),
    )
    add(
        "d128_residual_add_source_down_public_instance_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "source_down_projection_public_instance_commitment", "blake2b-256:" + "73" * 32
        ),
    )
    add(
        "d128_residual_add_input_activation_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "input_activation_commitment", "blake2b-256:" + "74" * 32
        ),
    )
    add(
        "d128_residual_add_residual_delta_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "residual_delta_commitment", "blake2b-256:" + "75" * 32
        ),
    )
    add(
        "d128_residual_add_residual_delta_scale_divisor_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "residual_delta_scale_divisor", TARGET_FF_DIM + 1
        ),
    )
    add(
        "d128_residual_add_residual_delta_remainder_sha256_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "residual_delta_remainder_sha256", "22" * 32
        ),
    )
    add(
        "d128_residual_add_range_policy_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "range_policy", "q8 activation and residual deltas"
        ),
    )
    add(
        "d128_residual_add_output_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "output_activation_commitment", "blake2b-256:" + "76" * 32
        ),
    )
    add(
        "d128_residual_add_row_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "residual_add_row_commitment", "blake2b-256:" + "77" * 32
        ),
    )
    add(
        "d128_residual_add_statement_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "statement_commitment", "blake2b-256:" + "78" * 32
        ),
    )
    add(
        "d128_residual_add_public_instance_commitment_drift",
        "source_probe",
        lambda p: p["source_probe"]["d128_residual_add"].__setitem__(
            "public_instance_commitment", "blake2b-256:" + "79" * 32
        ),
    )

    def relabel_d128_residual_add_intermediate_as_output(p: dict[str, Any]) -> None:
        residual = p["source_probe"]["d128_residual_add"]
        residual["residual_delta_commitment"] = residual["output_activation_commitment"]
        residual["residual_delta_relabels_full_output"] = True
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_residual_add_air")
        route["residual_delta_commitment"] = residual["output_activation_commitment"]

    add(
        "d128_residual_add_relabels_full_output",
        "source_probe",
        relabel_d128_residual_add_intermediate_as_output,
    )

    def drift_d128_residual_add_route_statement(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_residual_add_air")
        route["statement_commitment"] = "blake2b-256:" + "7a" * 32

    add(
        "d128_residual_add_route_statement_commitment_drift",
        "backend_routes",
        drift_d128_residual_add_route_statement,
    )

    def drift_d128_residual_add_route_output(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "direct_d128_residual_add_air")
        route["output_activation_commitment"] = "blake2b-256:" + "7b" * 32

    add(
        "d128_residual_add_route_output_commitment_drift",
        "backend_routes",
        drift_d128_residual_add_route_output,
    )

    def promote_full_block_parameterized_route(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "parameterized_transformer_block_air")
        route["status"] = "GO"
        route["missing_symbols"] = []
        route["proof_artifact_exists"] = True
        route["verifier_handle_exists"] = True

    add("full_block_parameterized_route_promoted", "backend_routes", promote_full_block_parameterized_route)

    def drift_d128_block_receipt_status(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "d128_block_receipt_composition")
        route["status"] = "GO_D128_RECURSIVE_AGGREGATION_OBJECT"

    add(
        "d128_block_receipt_composition_route_status_drift",
        "backend_routes",
        drift_d128_block_receipt_status,
    )

    def drift_d128_block_receipt_commitment(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "d128_block_receipt_composition")
        route["block_receipt_commitment"] = "blake2b-256:" + "8a" * 32

    add(
        "d128_block_receipt_composition_route_commitment_drift",
        "backend_routes",
        drift_d128_block_receipt_commitment,
    )

    def drift_d128_block_receipt_flag(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "d128_block_receipt_composition")
        route["receipt_artifact_exists"] = False

    add(
        "d128_block_receipt_composition_route_receipt_flag_drift",
        "backend_routes",
        drift_d128_block_receipt_flag,
    )

    def drift_d128_block_receipt_proof_artifact_flag(p: dict[str, Any]) -> None:
        route = next(row for row in p["backend_routes"] if row["route"] == "d128_block_receipt_composition")
        route["proof_artifact_exists"] = True

    add(
        "d128_block_receipt_composition_proof_artifact_exists_drift",
        "backend_routes",
        drift_d128_block_receipt_proof_artifact_flag,
    )

    def drift_d128_block_receipt_mutation_count(p: dict[str, Any]) -> None:
        p["source_probe"]["d128_block_receipt_composition"]["mutations_rejected"] = 0

    add(
        "d128_block_receipt_composition_mutations_rejected_drift",
        "source_probe",
        drift_d128_block_receipt_mutation_count,
    )

    def drift_d128_block_receipt_synchronized_commitments(p: dict[str, Any]) -> None:
        probe = p["source_probe"]["d128_block_receipt_composition"]
        fake = "blake2b-256:" + "8b" * 32
        probe["statement_commitment"] = "blake2b-256:" + "8c" * 32
        probe["block_receipt_commitment"] = fake
        route = next(row for row in p["backend_routes"] if row["route"] == "d128_block_receipt_composition")
        route["block_receipt_commitment"] = fake

    add(
        "d128_block_receipt_composition_synchronized_commitment_drift",
        "source_probe",
        drift_d128_block_receipt_synchronized_commitments,
    )

    def drift_d128_block_receipt_evidence_descriptor(p: dict[str, Any]) -> None:
        p["source_probe"]["d128_block_receipt_composition"]["evidence"]["path"] = (
            "docs/engineering/evidence/tampered-d128-block-receipt.json"
        )

    add(
        "d128_block_receipt_composition_evidence_descriptor_drift",
        "source_probe",
        drift_d128_block_receipt_evidence_descriptor,
    )
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
    expect_equal(summary.get("first_blocker_detail"), FIRST_BLOCKER_DETAIL, "summary first blocker detail")
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
        summary.get("d128_gate_value_projection_route"),
        "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY",
        "summary d128 gate/value projection route",
    )
    expect_equal(
        summary.get("d128_activation_swiglu_route"),
        "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY",
        "summary d128 activation/SwiGLU route",
    )
    expect_equal(
        summary.get("d128_down_projection_route"),
        "GO_PARTIAL_D128_DOWN_PROJECTION_ONLY",
        "summary d128 down-projection route",
    )
    expect_equal(
        summary.get("d128_residual_add_route"),
        "GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY",
        "summary d128 residual-add route",
    )
    expect_equal(
        summary.get("parameterized_residual_add_route"),
        "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "summary parameterized residual-add route",
    )
    expect_equal(
        summary.get("d128_block_receipt_composition_route"),
        "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE",
        "summary d128 block receipt composition route",
    )
    expect_equal(
        summary.get("parameterized_full_block_route"),
        "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING",
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
    gate_value_probe = require_object(
        source_probe.get("d128_gate_value_projection"),
        "d128 gate/value projection probe",
    )
    expect_equal(
        gate_value_probe.get("status"),
        "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY",
        "d128 gate/value projection status",
    )
    expect_equal(
        gate_value_probe.get("present_symbols"),
        list(D128_GATE_VALUE_SYMBOLS),
        "present d128 gate/value projection symbol inventory",
    )
    gate_value_source_projection_input = require_commitment(
        gate_value_probe.get("source_projection_input_row_commitment"),
        "d128 gate/value source projection-input commitment",
    )
    expect_equal(
        gate_value_source_projection_input,
        bridge_projection_input_commitment,
        "d128 gate/value source projection-input commitment",
    )
    expect_equal(
        gate_value_probe.get("projection_output_relabels_full_output"),
        False,
        "d128 gate/value output relabel guard",
    )
    expected_gate_value_commitments = {
        "source_projection_input_row_commitment": bridge_projection_input_commitment,
        "gate_matrix_root": D128_GATE_VALUE_GATE.GATE_MATRIX_ROOT,
        "value_matrix_root": D128_GATE_VALUE_GATE.VALUE_MATRIX_ROOT,
        "gate_projection_output_commitment": D128_GATE_VALUE_GATE.GATE_PROJECTION_OUTPUT_COMMITMENT,
        "value_projection_output_commitment": D128_GATE_VALUE_GATE.VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "gate_value_projection_output_commitment": D128_GATE_VALUE_GATE.GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "gate_value_projection_mul_row_commitment": D128_GATE_VALUE_GATE.GATE_VALUE_PROJECTION_MUL_ROW_COMMITMENT,
        "proof_native_parameter_commitment": D128_GATE_VALUE_GATE.PROOF_NATIVE_PARAMETER_COMMITMENT,
        "statement_commitment": D128_GATE_VALUE_GATE.STATEMENT_COMMITMENT,
        "public_instance_commitment": D128_GATE_VALUE_GATE.PUBLIC_INSTANCE_COMMITMENT,
    }
    for field, expected in expected_gate_value_commitments.items():
        actual = require_commitment(
            gate_value_probe.get(field),
            f"d128 gate/value projection {field}",
        )
        expect_equal(actual, expected, f"d128 gate/value projection {field}")
    activation_probe = require_object(
        source_probe.get("d128_activation_swiglu"),
        "d128 activation/SwiGLU probe",
    )
    expect_equal(
        activation_probe.get("status"),
        "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY",
        "d128 activation/SwiGLU status",
    )
    expect_equal(
        activation_probe.get("present_symbols"),
        list(D128_ACTIVATION_SYMBOLS),
        "present d128 activation/SwiGLU symbol inventory",
    )
    expect_equal(
        activation_probe.get("row_count"),
        TARGET_FF_DIM,
        "d128 activation/SwiGLU row count",
    )
    expect_equal(
        activation_probe.get("activation_lookup_rows"),
        D128_ACTIVATION_GATE.ACTIVATION_TABLE_ROWS,
        "d128 activation/SwiGLU activation lookup rows",
    )
    expect_equal(
        activation_probe.get("swiglu_mix_rows"),
        TARGET_FF_DIM,
        "d128 activation/SwiGLU swiglu mix rows",
    )
    expect_equal(
        activation_probe.get("source_gate_value_projection_proof_version"),
        D128_ACTIVATION_GATE.SOURCE_GATE_VALUE_PROOF_VERSION,
        "d128 activation/SwiGLU source gate/value proof version",
    )
    expect_equal(
        activation_probe.get("scale_q8"),
        D128_ACTIVATION_GATE.SCALE_Q8,
        "d128 activation/SwiGLU scale_q8",
    )
    expect_equal(
        activation_probe.get("activation_clamp_q8"),
        D128_ACTIVATION_GATE.ACTIVATION_CLAMP_Q8,
        "d128 activation/SwiGLU activation clamp q8",
    )
    expect_equal(
        activation_probe.get("hidden_relabels_full_output"),
        False,
        "d128 activation/SwiGLU hidden relabel guard",
    )
    expect_equal(
        activation_probe.get("source_gate_value_projection_output_commitment"),
        gate_value_probe.get("gate_value_projection_output_commitment"),
        "d128 activation/SwiGLU source gate/value output commitment",
    )
    expect_equal(
        activation_probe.get("source_gate_value_projection_statement_commitment"),
        gate_value_probe.get("statement_commitment"),
        "d128 activation/SwiGLU source gate/value statement commitment",
    )
    expect_equal(
        activation_probe.get("source_gate_value_projection_public_instance_commitment"),
        gate_value_probe.get("public_instance_commitment"),
        "d128 activation/SwiGLU source gate/value public-instance commitment",
    )
    expected_activation_commitments = {
        "source_gate_value_projection_statement_commitment": gate_value_probe.get("statement_commitment"),
        "source_gate_value_projection_public_instance_commitment": gate_value_probe.get("public_instance_commitment"),
        "source_gate_projection_output_commitment": D128_GATE_VALUE_GATE.GATE_PROJECTION_OUTPUT_COMMITMENT,
        "source_value_projection_output_commitment": D128_GATE_VALUE_GATE.VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "source_gate_value_projection_output_commitment": D128_GATE_VALUE_GATE.GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "activation_lookup_commitment": D128_ACTIVATION_GATE.ACTIVATION_LOOKUP_COMMITMENT,
        "proof_native_parameter_commitment": D128_ACTIVATION_GATE.PROOF_NATIVE_PARAMETER_COMMITMENT,
        "activation_output_commitment": D128_ACTIVATION_GATE.ACTIVATION_OUTPUT_COMMITMENT,
        "hidden_activation_commitment": D128_ACTIVATION_GATE.HIDDEN_ACTIVATION_COMMITMENT,
        "activation_swiglu_row_commitment": D128_ACTIVATION_GATE.ACTIVATION_SWIGLU_ROW_COMMITMENT,
        "statement_commitment": D128_ACTIVATION_GATE.STATEMENT_COMMITMENT,
        "public_instance_commitment": D128_ACTIVATION_GATE.PUBLIC_INSTANCE_COMMITMENT,
    }
    for field, expected in expected_activation_commitments.items():
        actual = require_commitment(
            activation_probe.get(field),
            f"d128 activation/SwiGLU {field}",
        )
        expect_equal(actual, expected, f"d128 activation/SwiGLU {field}")
    down_probe = require_object(
        source_probe.get("d128_down_projection"),
        "d128 down-projection probe",
    )
    expect_equal(
        down_probe.get("status"),
        "GO_PARTIAL_D128_DOWN_PROJECTION_ONLY",
        "d128 down-projection status",
    )
    expect_equal(
        down_probe.get("present_symbols"),
        list(D128_DOWN_SYMBOLS),
        "present d128 down-projection symbol inventory",
    )
    expect_equal(
        down_probe.get("row_count"),
        TARGET_WIDTH * TARGET_FF_DIM,
        "d128 down-projection row count",
    )
    expect_equal(
        down_probe.get("down_projection_mul_rows"),
        TARGET_WIDTH * TARGET_FF_DIM,
        "d128 down-projection multiplication row count",
    )
    expect_equal(
        down_probe.get("residual_delta_rows"),
        TARGET_WIDTH,
        "d128 down-projection residual delta rows",
    )
    expect_equal(
        down_probe.get("residual_delta_scale_divisor"),
        TARGET_FF_DIM,
        "d128 down-projection residual delta scale divisor",
    )
    expect_equal(
        down_probe.get("residual_delta_remainder_sha256"),
        D128_DOWN_GATE.RESIDUAL_DELTA_REMAINDER_SHA256,
        "d128 down-projection residual delta remainder hash",
    )
    expect_equal(
        down_probe.get("range_policy"),
        D128_DOWN_GATE.RANGE_POLICY,
        "d128 down-projection range policy",
    )
    expect_equal(
        down_probe.get("source_activation_swiglu_proof_version"),
        D128_DOWN_GATE.SOURCE_ACTIVATION_SWIGLU_PROOF_VERSION,
        "d128 down-projection source activation proof version",
    )
    expect_equal(
        down_probe.get("source_hidden_activation_commitment"),
        activation_probe.get("hidden_activation_commitment"),
        "d128 down-projection source hidden activation commitment",
    )
    expect_equal(
        down_probe.get("source_activation_swiglu_statement_commitment"),
        activation_probe.get("statement_commitment"),
        "d128 down-projection source activation statement commitment",
    )
    expect_equal(
        down_probe.get("source_activation_swiglu_public_instance_commitment"),
        activation_probe.get("public_instance_commitment"),
        "d128 down-projection source activation public-instance commitment",
    )
    expect_equal(
        down_probe.get("residual_delta_relabels_full_output"),
        False,
        "d128 down-projection residual relabel guard",
    )
    expected_down_commitments = {
        "source_activation_swiglu_statement_commitment": activation_probe.get("statement_commitment"),
        "source_activation_swiglu_public_instance_commitment": activation_probe.get("public_instance_commitment"),
        "source_hidden_activation_commitment": D128_DOWN_GATE.HIDDEN_ACTIVATION_COMMITMENT,
        "down_matrix_root": D128_DOWN_GATE.DOWN_MATRIX_ROOT,
        "proof_native_parameter_commitment": D128_DOWN_GATE.PROOF_NATIVE_PARAMETER_COMMITMENT,
        "residual_delta_commitment": D128_DOWN_GATE.RESIDUAL_DELTA_COMMITMENT,
        "down_projection_mul_row_commitment": D128_DOWN_GATE.DOWN_PROJECTION_MUL_ROW_COMMITMENT,
        "statement_commitment": D128_DOWN_GATE.STATEMENT_COMMITMENT,
        "public_instance_commitment": D128_DOWN_GATE.PUBLIC_INSTANCE_COMMITMENT,
    }
    for field, expected in expected_down_commitments.items():
        actual = require_commitment(
            down_probe.get(field),
            f"d128 down-projection {field}",
        )
        expect_equal(actual, expected, f"d128 down-projection {field}")
    residual_add_probe = require_object(
        source_probe.get("d128_residual_add"),
        "d128 residual-add probe",
    )
    expect_equal(
        residual_add_probe.get("status"),
        "GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY",
        "d128 residual-add status",
    )
    expect_equal(
        residual_add_probe.get("present_symbols"),
        list(D128_RESIDUAL_SYMBOLS),
        "present d128 residual-add symbol inventory",
    )
    expect_equal(
        residual_add_probe.get("row_count"),
        TARGET_WIDTH,
        "d128 residual-add row count",
    )
    expect_equal(
        residual_add_probe.get("source_rmsnorm_statement_commitment"),
        rmsnorm_probe.get("statement_commitment"),
        "d128 residual-add source RMSNorm statement commitment",
    )
    expect_equal(
        residual_add_probe.get("source_down_projection_statement_commitment"),
        down_probe.get("statement_commitment"),
        "d128 residual-add source down-projection statement commitment",
    )
    expect_equal(
        residual_add_probe.get("source_down_projection_public_instance_commitment"),
        down_probe.get("public_instance_commitment"),
        "d128 residual-add source down-projection public-instance commitment",
    )
    expect_equal(
        residual_add_probe.get("input_activation_commitment"),
        D128_RESIDUAL_GATE.INPUT_ACTIVATION_COMMITMENT,
        "d128 residual-add input activation commitment",
    )
    expect_equal(
        residual_add_probe.get("residual_delta_commitment"),
        down_probe.get("residual_delta_commitment"),
        "d128 residual-add residual-delta commitment",
    )
    expect_equal(
        residual_add_probe.get("residual_delta_scale_divisor"),
        TARGET_FF_DIM,
        "d128 residual-add residual delta scale divisor",
    )
    expect_equal(
        residual_add_probe.get("residual_delta_remainder_sha256"),
        down_probe.get("residual_delta_remainder_sha256"),
        "d128 residual-add residual delta remainder hash",
    )
    expect_equal(
        residual_add_probe.get("range_policy"),
        D128_RESIDUAL_GATE.RANGE_POLICY,
        "d128 residual-add range policy",
    )
    expect_equal(
        residual_add_probe.get("residual_delta_relabels_full_output"),
        False,
        "d128 residual-add residual relabel guard",
    )
    expect_equal(
        residual_add_probe.get("input_relabels_output"),
        False,
        "d128 residual-add input relabel guard",
    )
    expected_residual_commitments = {
        "source_rmsnorm_statement_commitment": rmsnorm_probe.get("statement_commitment"),
        "source_down_projection_statement_commitment": down_probe.get("statement_commitment"),
        "source_down_projection_public_instance_commitment": down_probe.get("public_instance_commitment"),
        "input_activation_commitment": D128_RESIDUAL_GATE.INPUT_ACTIVATION_COMMITMENT,
        "residual_delta_commitment": D128_RESIDUAL_GATE.RESIDUAL_DELTA_COMMITMENT,
        "output_activation_commitment": D128_RESIDUAL_GATE.OUTPUT_ACTIVATION_COMMITMENT,
        "residual_add_row_commitment": D128_RESIDUAL_GATE.RESIDUAL_ADD_ROW_COMMITMENT,
        "proof_native_parameter_commitment": D128_RESIDUAL_GATE.PROOF_NATIVE_PARAMETER_COMMITMENT,
        "statement_commitment": D128_RESIDUAL_GATE.STATEMENT_COMMITMENT,
        "public_instance_commitment": D128_RESIDUAL_GATE.PUBLIC_INSTANCE_COMMITMENT,
    }
    for field, expected in expected_residual_commitments.items():
        actual = require_commitment(
            residual_add_probe.get(field),
            f"d128 residual-add {field}",
        )
        expect_equal(actual, expected, f"d128 residual-add {field}")
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
    block_receipt_probe = require_object(
        source_probe.get("d128_block_receipt_composition"),
        "d128 block receipt composition probe",
    )
    expect_equal(
        block_receipt_probe.get("status"),
        "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE",
        "d128 block receipt composition status",
    )
    expect_equal(
        block_receipt_probe.get("evidence"),
        authoritative_d128_block_evidence_descriptor(),
        "d128 block receipt evidence descriptor",
    )
    expect_equal(block_receipt_probe.get("slice_count"), 6, "d128 block receipt slice count")
    expect_equal(
        block_receipt_probe.get("total_checked_rows"),
        197_504,
        "d128 block receipt checked rows",
    )
    expect_equal(
        block_receipt_probe.get("mutation_cases"),
        D128_BLOCK_RECEIPT_MUTATION_CASES,
        "d128 block receipt mutation cases",
    )
    expect_equal(
        block_receipt_probe.get("mutations_rejected"),
        D128_BLOCK_RECEIPT_MUTATION_CASES,
        "d128 block receipt mutations rejected",
    )
    statement_commitment = require_commitment(
        block_receipt_probe.get("statement_commitment"),
        "d128 block receipt statement commitment",
    )
    expect_equal(
        statement_commitment,
        D128_BLOCK_STATEMENT_COMMITMENT,
        "d128 block receipt statement commitment",
    )
    block_receipt_commitment = require_commitment(
        block_receipt_probe.get("block_receipt_commitment"),
        "d128 block receipt commitment",
    )
    expect_equal(
        block_receipt_commitment,
        D128_BLOCK_RECEIPT_COMMITMENT,
        "d128 block receipt commitment",
    )
    expect_equal(
        block_receipt_probe.get("output_activation_commitment"),
        residual_add_probe.get("output_activation_commitment"),
        "d128 block receipt output activation",
    )
    expect_equal(
        block_receipt_probe.get("non_claims"),
        D128_BLOCK_GATE.NON_CLAIMS,
        "d128 block receipt non-claims",
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
        "direct_d128_gate_value_projection_air",
        "direct_d128_activation_swiglu_air",
        "direct_d128_down_projection_air",
        "direct_d128_residual_add_air",
        "lift_existing_d64_modules_by_metadata",
        "parameterized_vector_residual_add_air",
        "parameterized_transformer_block_air",
        "d128_block_receipt_composition",
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
        route_by_name["direct_d128_gate_value_projection_air"].get("status"),
        "GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY",
        "direct d128 gate/value projection route status",
    )
    expect_equal(
        route_by_name["direct_d128_gate_value_projection_air"].get("source_projection_input_row_commitment"),
        bridge_projection_input_commitment,
        "direct d128 gate/value projection route source projection-input commitment",
    )
    for field, expected in expected_gate_value_commitments.items():
        actual = require_commitment(
            route_by_name["direct_d128_gate_value_projection_air"].get(field),
            f"direct d128 gate/value projection route {field}",
        )
        expect_equal(actual, expected, f"direct d128 gate/value projection route {field}")
    expect_equal(
        route_by_name["direct_d128_activation_swiglu_air"].get("status"),
        "GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY",
        "direct d128 activation/SwiGLU route status",
    )
    expect_equal(
        route_by_name["direct_d128_activation_swiglu_air"].get("source_gate_value_projection_output_commitment"),
        gate_value_probe.get("gate_value_projection_output_commitment"),
        "direct d128 activation/SwiGLU route source gate/value output commitment",
    )
    for field, expected in expected_activation_commitments.items():
        actual = require_commitment(
            route_by_name["direct_d128_activation_swiglu_air"].get(field),
            f"direct d128 activation/SwiGLU route {field}",
        )
        expect_equal(actual, expected, f"direct d128 activation/SwiGLU route {field}")
    expect_equal(
        route_by_name["direct_d128_down_projection_air"].get("status"),
        "GO_PARTIAL_D128_DOWN_PROJECTION_ONLY",
        "direct d128 down-projection route status",
    )
    expect_equal(
        route_by_name["direct_d128_down_projection_air"].get("source_hidden_activation_commitment"),
        activation_probe.get("hidden_activation_commitment"),
        "direct d128 down-projection route source hidden commitment",
    )
    for field, expected in expected_down_commitments.items():
        actual = require_commitment(
            route_by_name["direct_d128_down_projection_air"].get(field),
            f"direct d128 down-projection route {field}",
        )
        expect_equal(actual, expected, f"direct d128 down-projection route {field}")
    expect_equal(
        route_by_name["direct_d128_down_projection_air"].get("residual_delta_scale_divisor"),
        TARGET_FF_DIM,
        "direct d128 down-projection route residual delta scale divisor",
    )
    expect_equal(
        route_by_name["direct_d128_down_projection_air"].get("residual_delta_remainder_sha256"),
        D128_DOWN_GATE.RESIDUAL_DELTA_REMAINDER_SHA256,
        "direct d128 down-projection route residual delta remainder hash",
    )
    expect_equal(
        route_by_name["direct_d128_down_projection_air"].get("range_policy"),
        D128_DOWN_GATE.RANGE_POLICY,
        "direct d128 down-projection route range policy",
    )
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("status"),
        "GO_D128_SOURCE_BOUND_RESIDUAL_ADD_ONLY",
        "direct d128 residual-add route status",
    )
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("source_rmsnorm_statement_commitment"),
        rmsnorm_probe.get("statement_commitment"),
        "direct d128 residual-add route source RMSNorm statement commitment",
    )
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("source_down_projection_statement_commitment"),
        down_probe.get("statement_commitment"),
        "direct d128 residual-add route source down-projection statement commitment",
    )
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("source_down_projection_public_instance_commitment"),
        down_probe.get("public_instance_commitment"),
        "direct d128 residual-add route source down-projection public-instance commitment",
    )
    for field, expected in expected_residual_commitments.items():
        actual = require_commitment(
            route_by_name["direct_d128_residual_add_air"].get(field),
            f"direct d128 residual-add route {field}",
        )
        expect_equal(actual, expected, f"direct d128 residual-add route {field}")
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("residual_delta_scale_divisor"),
        TARGET_FF_DIM,
        "direct d128 residual-add route residual delta scale divisor",
    )
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("residual_delta_remainder_sha256"),
        down_probe.get("residual_delta_remainder_sha256"),
        "direct d128 residual-add route residual delta remainder hash",
    )
    expect_equal(
        route_by_name["direct_d128_residual_add_air"].get("range_policy"),
        D128_RESIDUAL_GATE.RANGE_POLICY,
        "direct d128 residual-add route range policy",
    )
    expect_equal(
        route_by_name["parameterized_vector_residual_add_air"].get("status"),
        "GO_PARTIAL_D128_RESIDUAL_ADD_ONLY",
        "parameterized residual-add route status",
    )
    expect_equal(
        route_by_name["parameterized_transformer_block_air"].get("status"),
        "NO_GO_AGGREGATED_PROOF_OBJECT_MISSING",
        "parameterized full-block route status",
    )
    expect_equal(
        route_by_name["d128_block_receipt_composition"].get("status"),
        "GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE",
        "d128 block receipt route status",
    )
    expect_equal(
        route_by_name["d128_block_receipt_composition"].get("block_receipt_commitment"),
        source_probe["d128_block_receipt_composition"]["block_receipt_commitment"],
        "d128 block receipt route commitment",
    )
    for raw_route in routes:
        route_obj = require_object(raw_route, "backend route")
        if route_obj["route"] == "existing_d64_slice_chain":
            continue
        if route_obj["route"] in {
            "direct_d128_rmsnorm_public_row_air",
            "direct_d128_rmsnorm_to_projection_bridge_air",
            "direct_d128_gate_value_projection_air",
            "direct_d128_activation_swiglu_air",
            "direct_d128_down_projection_air",
            "direct_d128_residual_add_air",
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
        elif route_obj["route"] == "d128_block_receipt_composition":
            expect_equal(route_obj.get("target_width"), TARGET_WIDTH, "d128 receipt target width")
            expect_equal(route_obj.get("proof_artifact_exists"), False, "d128 receipt proof artifact")
            expect_equal(route_obj.get("verifier_handle_exists"), True, "d128 receipt verifier handle")
            expect_equal(route_obj.get("receipt_artifact_exists"), True, "d128 receipt artifact")
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
        proof_status.get("partial_d128_gate_value_projection_proof_exists"),
        True,
        "partial d128 gate/value projection proof exists",
    )
    expect_equal(
        proof_status.get("partial_d128_gate_value_projection_verifier_exists"),
        True,
        "partial d128 gate/value projection verifier exists",
    )
    expect_equal(
        proof_status.get("partial_d128_gate_value_projection_local_roundtrip_proof_constructed"),
        True,
        "partial d128 gate/value projection local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_d128_gate_value_projection_checked_in_proof_artifact_exists"),
        False,
        "partial d128 gate/value projection checked-in proof artifact",
    )
    expect_equal(
        proof_status.get("partial_d128_activation_swiglu_proof_exists"),
        True,
        "partial d128 activation/SwiGLU proof exists",
    )
    expect_equal(
        proof_status.get("partial_d128_activation_swiglu_verifier_exists"),
        True,
        "partial d128 activation/SwiGLU verifier exists",
    )
    expect_equal(
        proof_status.get("partial_d128_activation_swiglu_local_roundtrip_proof_constructed"),
        True,
        "partial d128 activation/SwiGLU local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_d128_activation_swiglu_checked_in_proof_artifact_exists"),
        False,
        "partial d128 activation/SwiGLU checked-in proof artifact",
    )
    expect_equal(
        proof_status.get("partial_d128_down_projection_proof_exists"),
        True,
        "partial d128 down-projection proof exists",
    )
    expect_equal(
        proof_status.get("partial_d128_down_projection_verifier_exists"),
        True,
        "partial d128 down-projection verifier exists",
    )
    expect_equal(
        proof_status.get("partial_d128_down_projection_local_roundtrip_proof_constructed"),
        True,
        "partial d128 down-projection local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_d128_down_projection_checked_in_proof_artifact_exists"),
        False,
        "partial d128 down-projection checked-in proof artifact",
    )
    expect_equal(
        proof_status.get("partial_d128_residual_add_proof_exists"),
        True,
        "partial d128 residual-add proof exists",
    )
    expect_equal(
        proof_status.get("partial_d128_residual_add_verifier_exists"),
        True,
        "partial d128 residual-add verifier exists",
    )
    expect_equal(
        proof_status.get("partial_d128_residual_add_local_roundtrip_proof_constructed"),
        True,
        "partial d128 residual-add local roundtrip proof",
    )
    expect_equal(
        proof_status.get("partial_d128_residual_add_checked_in_proof_artifact_exists"),
        False,
        "partial d128 residual-add checked-in proof artifact",
    )
    expect_equal(
        proof_status.get("d128_block_receipt_composition_exists"),
        True,
        "d128 block receipt composition exists",
    )
    expect_equal(
        proof_status.get("d128_block_receipt_composition_mutation_cases"),
        source_probe["d128_block_receipt_composition"]["mutation_cases"],
        "d128 block receipt composition mutation cases",
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
    expect_equal(proof_status.get("first_blocker_detail"), FIRST_BLOCKER_DETAIL, "proof status first blocker detail")
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
