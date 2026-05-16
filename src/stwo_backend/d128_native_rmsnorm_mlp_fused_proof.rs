use std::collections::BTreeSet;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use stwo::core::air::{Component, Components};
use stwo::core::channel::Blake2sM31Channel;
use stwo::core::fields::m31::BaseField;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::core::ColumnVec;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::BitReversedOrder;
use stwo::prover::{prove, CommitmentSchemeProver, ComponentProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::TraceLocationAllocator;

use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

use super::d128_native_activation_swiglu_proof::{
    zkai_d128_activation_swiglu_component_with_allocator,
    zkai_d128_activation_swiglu_input_from_json_str,
    zkai_d128_activation_swiglu_preprocessed_column_ids, zkai_d128_activation_swiglu_trace,
    ZkAiD128ActivationSwiGluProofInput, ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
    ZKAI_D128_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_GATE_PROJECTION_OUTPUT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_GATE_VALUE_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_GATE_VALUE_PROJECTION_STATEMENT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_VALUE_PROJECTION_OUTPUT_COMMITMENT,
    ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT,
};
use super::d128_native_down_projection_proof::{
    zkai_d128_down_projection_component_with_allocator,
    zkai_d128_down_projection_input_from_json_str,
    zkai_d128_down_projection_preprocessed_column_ids, zkai_d128_down_projection_trace,
    ZkAiD128DownProjectionProofInput,
    ZKAI_D128_ATTENTION_DERIVED_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_DOWN_PROJECTION_STATEMENT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_HIDDEN_ACTIVATION_COMMITMENT,
    ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION, ZKAI_D128_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_DOWN_PROJECTION_STATEMENT_COMMITMENT, ZKAI_D128_RESIDUAL_DELTA_COMMITMENT,
};
use super::d128_native_gate_value_projection_proof::{
    zkai_d128_gate_value_projection_component_with_allocator,
    zkai_d128_gate_value_projection_input_from_json_str,
    zkai_d128_gate_value_projection_preprocessed_column_ids, zkai_d128_gate_value_projection_rows,
    zkai_d128_gate_value_projection_trace, D128GateValueProjectionMulRow,
    ZkAiD128GateValueProjectionProofInput,
    ZKAI_D128_ATTENTION_DERIVED_PROJECTION_INPUT_ROW_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
    ZKAI_D128_GATE_PROJECTION_OUTPUT_COMMITMENT, ZKAI_D128_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
    ZKAI_D128_GATE_VALUE_PROJECTION_PROOF_VERSION,
    ZKAI_D128_GATE_VALUE_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_GATE_VALUE_PROJECTION_STATEMENT_COMMITMENT,
    ZKAI_D128_VALUE_PROJECTION_OUTPUT_COMMITMENT,
};
use super::d128_native_residual_add_proof::{
    zkai_d128_residual_add_component_with_allocator, zkai_d128_residual_add_input_from_json_str,
    zkai_d128_residual_add_preprocessed_column_ids, zkai_d128_residual_add_trace,
    ZkAiD128ResidualAddProofInput, ZKAI_D128_ATTENTION_DERIVED_INPUT_ACTIVATION_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_INPUT_PROOF_VERSION,
    ZKAI_D128_ATTENTION_DERIVED_INPUT_STATEMENT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_OUTPUT_ACTIVATION_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_ADD_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_ADD_ROW_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_ADD_STATEMENT_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_DELTA_COMMITMENT, ZKAI_D128_INPUT_ACTIVATION_COMMITMENT,
    ZKAI_D128_OUTPUT_ACTIVATION_COMMITMENT, ZKAI_D128_RESIDUAL_ADD_PROOF_VERSION,
    ZKAI_D128_RESIDUAL_ADD_PUBLIC_INSTANCE_COMMITMENT, ZKAI_D128_RESIDUAL_ADD_ROW_COMMITMENT,
    ZKAI_D128_RESIDUAL_ADD_STATEMENT_COMMITMENT,
};
use super::d128_native_rmsnorm_public_row_proof::{
    zkai_d128_rmsnorm_public_row_component_with_allocator,
    zkai_d128_rmsnorm_public_row_input_from_json_str,
    zkai_d128_rmsnorm_public_row_preprocessed_column_ids, zkai_d128_rmsnorm_public_row_trace,
    ZkAiD128RmsnormPublicRowProofInput, ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
    ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
};
use super::d128_native_rmsnorm_to_projection_bridge_proof::{
    zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator,
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str,
    zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids,
    zkai_d128_rmsnorm_to_projection_bridge_trace, ZkAiD128RmsnormToProjectionBridgeInput,
    ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT, ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
};
use super::{publication_v1_pcs_config, publication_v1_pcs_config_matches};

pub const ZKAI_D128_RMSNORM_MLP_FUSED_INPUT_SCHEMA: &str =
    "zkai-d128-rmsnorm-mlp-fused-air-proof-input-v1";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D128_RMSNORM_MLP_FUSED_AIR_PROOF";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_PROOF_VERSION: &str =
    "stwo-d128-rmsnorm-mlp-fused-air-proof-v1";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_STATEMENT_VERSION: &str =
    "zkai-d128-rmsnorm-mlp-fused-statement-v1";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_SEMANTIC_SCOPE: &str =
    "d128_rmsnorm_projection_bridge_gate_value_activation_down_residual_rows_fused_in_one_native_stwo_proof";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_DECISION: &str = "GO_D128_RMSNORM_MLP_FUSED_AIR_PROOF";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_ROUTE_ID: &str =
    "native_stwo_d128_rmsnorm_public_row_plus_projection_bridge_plus_gate_value_plus_activation_swiglu_plus_down_projection_plus_residual_add_fused";
pub const ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES: usize = 4_194_304;
pub const ZKAI_D128_RMSNORM_MLP_FUSED_MAX_PROOF_BYTES: usize = 2_097_152;
pub const ZKAI_D128_RMSNORM_MLP_FUSED_MAX_ENVELOPE_JSON_BYTES: usize = 8_388_608;

const WIDTH: usize = 128;
const FF_DIM: usize = 512;
const RMSNORM_ROWS: usize = 128;
const PROJECTION_BRIDGE_ROWS: usize = 128;
const GATE_VALUE_ROWS: usize = 131_072;
const ACTIVATION_ROWS: usize = 512;
const DOWN_PROJECTION_ROWS: usize = 65_536;
const RESIDUAL_ADD_ROWS: usize = 128;
const EXPECTED_PROOF_COMMITMENTS: usize = 3;
const EXPECTED_TRACE_COMMITMENT_TREES: usize = 2;
const STATEMENT_DOMAIN: &str = "ptvm:zkai:d128-rmsnorm-mlp-fused-statement:v1";
const PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:d128-rmsnorm-mlp-fused-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:d128-rmsnorm-mlp-fused-proof-native-parameter:v1";
const PROOF_NATIVE_PARAMETER_KIND: &str = "d128-rmsnorm-mlp-fused-proof-native-parameter-v1";

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not attention plus MLP in one proof object",
    "not a full transformer block",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not recursion or proof-carrying data",
    "not private parameter-opening proof",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "nested RMSNorm input validated before fused proof construction",
    "nested RMSNorm-to-projection bridge input validated before fused proof construction",
    "nested gate/value input validated before fused proof construction",
    "nested activation/SwiGLU input validated before fused proof construction",
    "nested down-projection input validated before fused proof construction",
    "nested residual-add input validated before fused proof construction",
    "RMSNorm output rows must match bridge source rows",
    "bridge projection input rows must match gate/value projection input rows",
    "activation source commitments and vectors must match gate/value outputs",
    "down-projection source commitment and hidden vector must match activation output",
    "residual-add source commitment and residual vectors must match down-projection output",
    "residual-add input activation must match the original RMSNorm input activation",
    "component preprocessed columns allocated once across six adjacent components",
    "base trace columns allocated once across six adjacent components",
    "single native Stwo proof shares commitment/opening plumbing across the RMSNorm-to-residual MLP surface",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- prove docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- verify docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json",
    "python3 scripts/zkai_d128_rmsnorm_mlp_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_mlp_fused_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_rmsnorm_mlp_fused_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
];

const EXPECTED_ATTENTION_DERIVED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- build-input docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json",
    "python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_rmsnorm_mlp_fused_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
];

const ZKAI_D128_ATTENTION_DERIVED_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT: &str =
    "blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d";
const ZKAI_D128_ATTENTION_DERIVED_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT: &str =
    "blake2b-256:21316dfa0e32f91879bf13b85f99e16db0aa4c6e5f91c0dfc106f300c0c50fff";
const ZKAI_D128_ATTENTION_DERIVED_RMSNORM_OUTPUT_ROW_COMMITMENT: &str =
    "blake2b-256:fbc611c011d2209476aca2055f5f9abe0d6cda12bd0f6fabeec7d1657ce1e1f9";

#[derive(Clone, Copy)]
struct FusedSourceProfile {
    residual_source_proof_version: &'static str,
    residual_source_statement_commitment: &'static str,
    rmsnorm_statement_commitment: &'static str,
    rmsnorm_public_instance_commitment: &'static str,
    input_activation_commitment: &'static str,
    rmsnorm_output_row_commitment: &'static str,
    projection_bridge_statement_commitment: &'static str,
    projection_bridge_public_instance_commitment: &'static str,
    projection_input_row_commitment: &'static str,
    gate_value_statement_commitment: &'static str,
    gate_value_public_instance_commitment: &'static str,
    gate_projection_output_commitment: &'static str,
    value_projection_output_commitment: &'static str,
    gate_value_projection_output_commitment: &'static str,
    activation_statement_commitment: &'static str,
    activation_public_instance_commitment: &'static str,
    hidden_activation_commitment: &'static str,
    down_projection_statement_commitment: &'static str,
    down_projection_public_instance_commitment: &'static str,
    residual_delta_commitment: &'static str,
    residual_add_statement_commitment: &'static str,
    residual_add_public_instance_commitment: &'static str,
    output_activation_commitment: &'static str,
    residual_add_row_commitment: &'static str,
    validation_commands: &'static [&'static str],
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128RmsnormMlpFusedInput {
    pub schema: String,
    pub decision: String,
    pub route_id: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub ff_dim: usize,
    pub rmsnorm_row_count: usize,
    pub projection_bridge_row_count: usize,
    pub gate_value_row_count: usize,
    pub activation_row_count: usize,
    pub down_projection_row_count: usize,
    pub residual_add_row_count: usize,
    pub rmsnorm_proof_version: String,
    pub projection_bridge_proof_version: String,
    pub gate_value_proof_version: String,
    pub activation_swiglu_proof_version: String,
    pub down_projection_proof_version: String,
    pub residual_add_proof_version: String,
    pub rmsnorm_statement_commitment: String,
    pub rmsnorm_public_instance_commitment: String,
    pub projection_bridge_statement_commitment: String,
    pub projection_bridge_public_instance_commitment: String,
    pub gate_value_statement_commitment: String,
    pub gate_value_public_instance_commitment: String,
    pub activation_statement_commitment: String,
    pub activation_public_instance_commitment: String,
    pub down_projection_statement_commitment: String,
    pub down_projection_public_instance_commitment: String,
    pub residual_add_statement_commitment: String,
    pub residual_add_public_instance_commitment: String,
    pub input_activation_commitment: String,
    pub rmsnorm_output_row_commitment: String,
    pub projection_input_row_commitment: String,
    pub gate_projection_output_commitment: String,
    pub value_projection_output_commitment: String,
    pub gate_value_projection_output_commitment: String,
    pub hidden_activation_commitment: String,
    pub residual_delta_commitment: String,
    pub output_activation_commitment: String,
    pub residual_add_row_commitment: String,
    pub statement_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub rmsnorm_input: ZkAiD128RmsnormPublicRowProofInput,
    pub projection_bridge_input: ZkAiD128RmsnormToProjectionBridgeInput,
    pub gate_value_input: ZkAiD128GateValueProjectionProofInput,
    pub activation_input: ZkAiD128ActivationSwiGluProofInput,
    pub down_projection_input: ZkAiD128DownProjectionProofInput,
    pub residual_add_input: ZkAiD128ResidualAddProofInput,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128RmsnormMlpFusedEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD128RmsnormMlpFusedInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct D128RmsnormMlpFusedProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d128_rmsnorm_mlp_fused_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128RmsnormMlpFusedInput> {
    if raw_json.len() > ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES {
        return Err(fused_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD128RmsnormMlpFusedInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_fused_input(&input)?;
    Ok(input)
}

pub fn zkai_d128_rmsnorm_mlp_fused_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiD128RmsnormMlpFusedEnvelope> {
    if raw_json.len() > ZKAI_D128_RMSNORM_MLP_FUSED_MAX_ENVELOPE_JSON_BYTES {
        return Err(fused_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_RMSNORM_MLP_FUSED_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiD128RmsnormMlpFusedEnvelope = serde_json::from_slice(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_fused_envelope(&envelope)?;
    Ok(envelope)
}

pub fn build_zkai_d128_rmsnorm_mlp_fused_input(
    rmsnorm_input: ZkAiD128RmsnormPublicRowProofInput,
    projection_bridge_input: ZkAiD128RmsnormToProjectionBridgeInput,
    gate_value_input: ZkAiD128GateValueProjectionProofInput,
    activation_input: ZkAiD128ActivationSwiGluProofInput,
    down_projection_input: ZkAiD128DownProjectionProofInput,
    residual_add_input: ZkAiD128ResidualAddProofInput,
) -> Result<ZkAiD128RmsnormMlpFusedInput> {
    validate_nested_rmsnorm_input(&rmsnorm_input)?;
    validate_nested_bridge_input(&projection_bridge_input)?;
    validate_nested_gate_value_input(&gate_value_input)?;
    validate_nested_activation_input(&activation_input)?;
    validate_nested_down_projection_input(&down_projection_input)?;
    validate_nested_residual_add_input(&residual_add_input)?;
    let source_profile = approved_fused_source_profile_from_components(
        &rmsnorm_input,
        &projection_bridge_input,
        &gate_value_input,
        &activation_input,
        &down_projection_input,
        &residual_add_input,
    )?;
    validate_rmsnorm_bridge_handoff(&rmsnorm_input, &projection_bridge_input)?;
    validate_bridge_gate_handoff(&projection_bridge_input, &gate_value_input)?;
    validate_gate_activation_handoff(&gate_value_input, &activation_input)?;
    validate_activation_down_handoff(&activation_input, &down_projection_input)?;
    validate_down_residual_handoff(&down_projection_input, &residual_add_input)?;
    validate_rmsnorm_residual_handoff(&rmsnorm_input, &residual_add_input, source_profile)?;

    let mut input = ZkAiD128RmsnormMlpFusedInput {
        schema: ZKAI_D128_RMSNORM_MLP_FUSED_INPUT_SCHEMA.to_string(),
        decision: ZKAI_D128_RMSNORM_MLP_FUSED_INPUT_DECISION.to_string(),
        route_id: ZKAI_D128_RMSNORM_MLP_FUSED_ROUTE_ID.to_string(),
        target_id: gate_value_input.target_id.clone(),
        required_backend_version: gate_value_input.required_backend_version.clone(),
        verifier_domain: gate_value_input.verifier_domain.clone(),
        width: WIDTH,
        ff_dim: FF_DIM,
        rmsnorm_row_count: RMSNORM_ROWS,
        projection_bridge_row_count: PROJECTION_BRIDGE_ROWS,
        gate_value_row_count: GATE_VALUE_ROWS,
        activation_row_count: ACTIVATION_ROWS,
        down_projection_row_count: DOWN_PROJECTION_ROWS,
        residual_add_row_count: RESIDUAL_ADD_ROWS,
        rmsnorm_proof_version: ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION.to_string(),
        projection_bridge_proof_version: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION
            .to_string(),
        gate_value_proof_version: ZKAI_D128_GATE_VALUE_PROJECTION_PROOF_VERSION.to_string(),
        activation_swiglu_proof_version: ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION.to_string(),
        down_projection_proof_version: ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION.to_string(),
        residual_add_proof_version: ZKAI_D128_RESIDUAL_ADD_PROOF_VERSION.to_string(),
        rmsnorm_statement_commitment: rmsnorm_input.statement_commitment.clone(),
        rmsnorm_public_instance_commitment: rmsnorm_input.public_instance_commitment.clone(),
        projection_bridge_statement_commitment: projection_bridge_input
            .statement_commitment
            .clone(),
        projection_bridge_public_instance_commitment: projection_bridge_input
            .public_instance_commitment
            .clone(),
        gate_value_statement_commitment: gate_value_input.statement_commitment.clone(),
        gate_value_public_instance_commitment: gate_value_input.public_instance_commitment.clone(),
        activation_statement_commitment: activation_input.statement_commitment.clone(),
        activation_public_instance_commitment: activation_input.public_instance_commitment.clone(),
        down_projection_statement_commitment: down_projection_input.statement_commitment.clone(),
        down_projection_public_instance_commitment: down_projection_input
            .public_instance_commitment
            .clone(),
        residual_add_statement_commitment: residual_add_input.statement_commitment.clone(),
        residual_add_public_instance_commitment: residual_add_input
            .public_instance_commitment
            .clone(),
        input_activation_commitment: rmsnorm_input.input_activation_commitment.clone(),
        rmsnorm_output_row_commitment: rmsnorm_input.rmsnorm_output_row_commitment.clone(),
        projection_input_row_commitment: projection_bridge_input
            .projection_input_row_commitment
            .clone(),
        gate_projection_output_commitment: gate_value_input
            .gate_projection_output_commitment
            .clone(),
        value_projection_output_commitment: gate_value_input
            .value_projection_output_commitment
            .clone(),
        gate_value_projection_output_commitment: gate_value_input
            .gate_value_projection_output_commitment
            .clone(),
        hidden_activation_commitment: activation_input.hidden_activation_commitment.clone(),
        residual_delta_commitment: down_projection_input.residual_delta_commitment.clone(),
        output_activation_commitment: residual_add_input.output_activation_commitment.clone(),
        residual_add_row_commitment: residual_add_input.residual_add_row_commitment.clone(),
        statement_commitment: String::new(),
        public_instance_commitment: String::new(),
        proof_native_parameter_commitment: String::new(),
        rmsnorm_input,
        projection_bridge_input,
        gate_value_input,
        activation_input,
        down_projection_input,
        residual_add_input,
        non_claims: EXPECTED_NON_CLAIMS
            .iter()
            .map(|value| value.to_string())
            .collect(),
        proof_verifier_hardening: EXPECTED_PROOF_VERIFIER_HARDENING
            .iter()
            .map(|value| value.to_string())
            .collect(),
        validation_commands: source_profile
            .validation_commands
            .iter()
            .map(|value| value.to_string())
            .collect(),
    };
    input.statement_commitment = statement_commitment(&input)?;
    input.public_instance_commitment = public_instance_commitment(&input.statement_commitment)?;
    input.proof_native_parameter_commitment =
        proof_native_parameter_commitment(&input.statement_commitment)?;
    validate_fused_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d128_rmsnorm_mlp_fused_envelope(
    input: &ZkAiD128RmsnormMlpFusedInput,
) -> Result<ZkAiD128RmsnormMlpFusedEnvelope> {
    validate_fused_input(input)?;
    let proof = prove_fused_components(input)?;
    if proof.len() > ZKAI_D128_RMSNORM_MLP_FUSED_MAX_PROOF_BYTES {
        return Err(fused_error(format!(
            "proof bytes exceed bounded prover limit: got {}, max {}",
            proof.len(),
            ZKAI_D128_RMSNORM_MLP_FUSED_MAX_PROOF_BYTES
        )));
    }
    Ok(ZkAiD128RmsnormMlpFusedEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D128_RMSNORM_MLP_FUSED_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D128_RMSNORM_MLP_FUSED_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D128_RMSNORM_MLP_FUSED_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D128_RMSNORM_MLP_FUSED_DECISION.to_string(),
        input: input.clone(),
        proof,
    })
}

pub fn verify_zkai_d128_rmsnorm_mlp_fused_envelope(
    envelope: &ZkAiD128RmsnormMlpFusedEnvelope,
) -> Result<bool> {
    validate_fused_envelope(envelope)?;
    verify_fused_components(&envelope.input, &envelope.proof)
}

fn validate_fused_envelope(envelope: &ZkAiD128RmsnormMlpFusedEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(fused_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_RMSNORM_MLP_FUSED_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_RMSNORM_MLP_FUSED_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_RMSNORM_MLP_FUSED_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_RMSNORM_MLP_FUSED_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(fused_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D128_RMSNORM_MLP_FUSED_MAX_PROOF_BYTES {
        return Err(fused_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_RMSNORM_MLP_FUSED_MAX_PROOF_BYTES
        )));
    }
    validate_fused_input(&envelope.input)
}

fn fused_source_profiles() -> [FusedSourceProfile; 2] {
    [
        FusedSourceProfile {
            residual_source_proof_version: ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
            residual_source_statement_commitment: ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
            rmsnorm_statement_commitment: ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
            rmsnorm_public_instance_commitment:
                "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72",
            input_activation_commitment: ZKAI_D128_INPUT_ACTIVATION_COMMITMENT,
            rmsnorm_output_row_commitment: ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT,
            projection_bridge_statement_commitment:
                ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
            projection_bridge_public_instance_commitment:
                ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
            projection_input_row_commitment: ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT,
            gate_value_statement_commitment: ZKAI_D128_GATE_VALUE_PROJECTION_STATEMENT_COMMITMENT,
            gate_value_public_instance_commitment:
                ZKAI_D128_GATE_VALUE_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
            gate_projection_output_commitment: ZKAI_D128_GATE_PROJECTION_OUTPUT_COMMITMENT,
            value_projection_output_commitment: ZKAI_D128_VALUE_PROJECTION_OUTPUT_COMMITMENT,
            gate_value_projection_output_commitment:
                ZKAI_D128_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
            activation_statement_commitment: ZKAI_D128_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
            activation_public_instance_commitment:
                ZKAI_D128_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
            hidden_activation_commitment: ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT,
            down_projection_statement_commitment: ZKAI_D128_DOWN_PROJECTION_STATEMENT_COMMITMENT,
            down_projection_public_instance_commitment:
                ZKAI_D128_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
            residual_delta_commitment: ZKAI_D128_RESIDUAL_DELTA_COMMITMENT,
            residual_add_statement_commitment: ZKAI_D128_RESIDUAL_ADD_STATEMENT_COMMITMENT,
            residual_add_public_instance_commitment:
                ZKAI_D128_RESIDUAL_ADD_PUBLIC_INSTANCE_COMMITMENT,
            output_activation_commitment: ZKAI_D128_OUTPUT_ACTIVATION_COMMITMENT,
            residual_add_row_commitment: ZKAI_D128_RESIDUAL_ADD_ROW_COMMITMENT,
            validation_commands: EXPECTED_VALIDATION_COMMANDS,
        },
        FusedSourceProfile {
            residual_source_proof_version: ZKAI_D128_ATTENTION_DERIVED_INPUT_PROOF_VERSION,
            residual_source_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_INPUT_STATEMENT_COMMITMENT,
            rmsnorm_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
            rmsnorm_public_instance_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT,
            input_activation_commitment: ZKAI_D128_ATTENTION_DERIVED_INPUT_ACTIVATION_COMMITMENT,
            rmsnorm_output_row_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RMSNORM_OUTPUT_ROW_COMMITMENT,
            projection_bridge_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
            projection_bridge_public_instance_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
            projection_input_row_commitment:
                ZKAI_D128_ATTENTION_DERIVED_PROJECTION_INPUT_ROW_COMMITMENT,
            gate_value_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_GATE_VALUE_PROJECTION_STATEMENT_COMMITMENT,
            gate_value_public_instance_commitment:
                ZKAI_D128_ATTENTION_DERIVED_GATE_VALUE_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
            gate_projection_output_commitment:
                ZKAI_D128_ATTENTION_DERIVED_GATE_PROJECTION_OUTPUT_COMMITMENT,
            value_projection_output_commitment:
                ZKAI_D128_ATTENTION_DERIVED_VALUE_PROJECTION_OUTPUT_COMMITMENT,
            gate_value_projection_output_commitment:
                ZKAI_D128_ATTENTION_DERIVED_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
            activation_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
            activation_public_instance_commitment:
                ZKAI_D128_ATTENTION_DERIVED_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
            hidden_activation_commitment: ZKAI_D128_ATTENTION_DERIVED_HIDDEN_ACTIVATION_COMMITMENT,
            down_projection_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_DOWN_PROJECTION_STATEMENT_COMMITMENT,
            down_projection_public_instance_commitment:
                ZKAI_D128_ATTENTION_DERIVED_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
            residual_delta_commitment: ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_DELTA_COMMITMENT,
            residual_add_statement_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_ADD_STATEMENT_COMMITMENT,
            residual_add_public_instance_commitment:
                ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_ADD_PUBLIC_INSTANCE_COMMITMENT,
            output_activation_commitment: ZKAI_D128_ATTENTION_DERIVED_OUTPUT_ACTIVATION_COMMITMENT,
            residual_add_row_commitment: ZKAI_D128_ATTENTION_DERIVED_RESIDUAL_ADD_ROW_COMMITMENT,
            validation_commands: EXPECTED_ATTENTION_DERIVED_VALIDATION_COMMANDS,
        },
    ]
}

fn approved_fused_source_profile(
    input: &ZkAiD128RmsnormMlpFusedInput,
) -> Result<FusedSourceProfile> {
    approved_fused_source_profile_fields(FusedSourceProfileFields {
        residual_source_proof_version: &input.residual_add_input.source_rmsnorm_proof_version,
        residual_source_statement_commitment: &input
            .residual_add_input
            .source_rmsnorm_statement_commitment,
        rmsnorm_statement_commitment: &input.rmsnorm_statement_commitment,
        rmsnorm_public_instance_commitment: &input.rmsnorm_public_instance_commitment,
        input_activation_commitment: &input.input_activation_commitment,
        rmsnorm_output_row_commitment: &input.rmsnorm_output_row_commitment,
        projection_bridge_statement_commitment: &input.projection_bridge_statement_commitment,
        projection_bridge_public_instance_commitment: &input
            .projection_bridge_public_instance_commitment,
        projection_input_row_commitment: &input.projection_input_row_commitment,
        gate_value_statement_commitment: &input.gate_value_statement_commitment,
        gate_value_public_instance_commitment: &input.gate_value_public_instance_commitment,
        gate_projection_output_commitment: &input.gate_projection_output_commitment,
        value_projection_output_commitment: &input.value_projection_output_commitment,
        gate_value_projection_output_commitment: &input.gate_value_projection_output_commitment,
        activation_statement_commitment: &input.activation_statement_commitment,
        activation_public_instance_commitment: &input.activation_public_instance_commitment,
        hidden_activation_commitment: &input.hidden_activation_commitment,
        down_projection_statement_commitment: &input.down_projection_statement_commitment,
        down_projection_public_instance_commitment: &input
            .down_projection_public_instance_commitment,
        residual_delta_commitment: &input.residual_delta_commitment,
        residual_add_statement_commitment: &input.residual_add_statement_commitment,
        residual_add_public_instance_commitment: &input.residual_add_public_instance_commitment,
        output_activation_commitment: &input.output_activation_commitment,
        residual_add_row_commitment: &input.residual_add_row_commitment,
    })
}

fn approved_fused_source_profile_from_components(
    rmsnorm_input: &ZkAiD128RmsnormPublicRowProofInput,
    projection_bridge_input: &ZkAiD128RmsnormToProjectionBridgeInput,
    gate_value_input: &ZkAiD128GateValueProjectionProofInput,
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
    down_projection_input: &ZkAiD128DownProjectionProofInput,
    residual_add_input: &ZkAiD128ResidualAddProofInput,
) -> Result<FusedSourceProfile> {
    approved_fused_source_profile_fields(FusedSourceProfileFields {
        residual_source_proof_version: &residual_add_input.source_rmsnorm_proof_version,
        residual_source_statement_commitment: &residual_add_input
            .source_rmsnorm_statement_commitment,
        rmsnorm_statement_commitment: &rmsnorm_input.statement_commitment,
        rmsnorm_public_instance_commitment: &rmsnorm_input.public_instance_commitment,
        input_activation_commitment: &rmsnorm_input.input_activation_commitment,
        rmsnorm_output_row_commitment: &rmsnorm_input.rmsnorm_output_row_commitment,
        projection_bridge_statement_commitment: &projection_bridge_input.statement_commitment,
        projection_bridge_public_instance_commitment: &projection_bridge_input
            .public_instance_commitment,
        projection_input_row_commitment: &projection_bridge_input.projection_input_row_commitment,
        gate_value_statement_commitment: &gate_value_input.statement_commitment,
        gate_value_public_instance_commitment: &gate_value_input.public_instance_commitment,
        gate_projection_output_commitment: &gate_value_input.gate_projection_output_commitment,
        value_projection_output_commitment: &gate_value_input.value_projection_output_commitment,
        gate_value_projection_output_commitment: &gate_value_input
            .gate_value_projection_output_commitment,
        activation_statement_commitment: &activation_input.statement_commitment,
        activation_public_instance_commitment: &activation_input.public_instance_commitment,
        hidden_activation_commitment: &activation_input.hidden_activation_commitment,
        down_projection_statement_commitment: &down_projection_input.statement_commitment,
        down_projection_public_instance_commitment: &down_projection_input
            .public_instance_commitment,
        residual_delta_commitment: &down_projection_input.residual_delta_commitment,
        residual_add_statement_commitment: &residual_add_input.statement_commitment,
        residual_add_public_instance_commitment: &residual_add_input.public_instance_commitment,
        output_activation_commitment: &residual_add_input.output_activation_commitment,
        residual_add_row_commitment: &residual_add_input.residual_add_row_commitment,
    })
}

struct FusedSourceProfileFields<'a> {
    residual_source_proof_version: &'a str,
    residual_source_statement_commitment: &'a str,
    rmsnorm_statement_commitment: &'a str,
    rmsnorm_public_instance_commitment: &'a str,
    input_activation_commitment: &'a str,
    rmsnorm_output_row_commitment: &'a str,
    projection_bridge_statement_commitment: &'a str,
    projection_bridge_public_instance_commitment: &'a str,
    projection_input_row_commitment: &'a str,
    gate_value_statement_commitment: &'a str,
    gate_value_public_instance_commitment: &'a str,
    gate_projection_output_commitment: &'a str,
    value_projection_output_commitment: &'a str,
    gate_value_projection_output_commitment: &'a str,
    activation_statement_commitment: &'a str,
    activation_public_instance_commitment: &'a str,
    hidden_activation_commitment: &'a str,
    down_projection_statement_commitment: &'a str,
    down_projection_public_instance_commitment: &'a str,
    residual_delta_commitment: &'a str,
    residual_add_statement_commitment: &'a str,
    residual_add_public_instance_commitment: &'a str,
    output_activation_commitment: &'a str,
    residual_add_row_commitment: &'a str,
}

fn approved_fused_source_profile_fields(
    fields: FusedSourceProfileFields<'_>,
) -> Result<FusedSourceProfile> {
    let mut diagnostics = Vec::new();
    for (index, profile) in fused_source_profiles().into_iter().enumerate() {
        let mismatches = fused_source_profile_mismatches(&fields, profile);
        if mismatches.is_empty() {
            return Ok(profile);
        }
        diagnostics.push(format!("profile_{index}:{}", mismatches.join(",")));
    }
    Err(fused_error(format!(
        "fused source profile is not approved: expected synthetic or attention_derived component anchors; mismatches={}",
        diagnostics.join(";")
    )))
}

fn fused_source_profile_mismatches(
    fields: &FusedSourceProfileFields<'_>,
    profile: FusedSourceProfile,
) -> Vec<&'static str> {
    let mut mismatches = Vec::new();
    macro_rules! check_field {
        ($name:literal, $field:ident) => {
            if fields.$field != profile.$field {
                mismatches.push($name);
            }
        };
    }
    check_field!(
        "residual_source_proof_version",
        residual_source_proof_version
    );
    check_field!(
        "residual_source_statement_commitment",
        residual_source_statement_commitment
    );
    check_field!("rmsnorm_statement_commitment", rmsnorm_statement_commitment);
    check_field!(
        "rmsnorm_public_instance_commitment",
        rmsnorm_public_instance_commitment
    );
    check_field!("input_activation_commitment", input_activation_commitment);
    check_field!(
        "rmsnorm_output_row_commitment",
        rmsnorm_output_row_commitment
    );
    check_field!(
        "projection_bridge_statement_commitment",
        projection_bridge_statement_commitment
    );
    check_field!(
        "projection_bridge_public_instance_commitment",
        projection_bridge_public_instance_commitment
    );
    check_field!(
        "projection_input_row_commitment",
        projection_input_row_commitment
    );
    check_field!(
        "gate_value_statement_commitment",
        gate_value_statement_commitment
    );
    check_field!(
        "gate_value_public_instance_commitment",
        gate_value_public_instance_commitment
    );
    check_field!(
        "gate_projection_output_commitment",
        gate_projection_output_commitment
    );
    check_field!(
        "value_projection_output_commitment",
        value_projection_output_commitment
    );
    check_field!(
        "gate_value_projection_output_commitment",
        gate_value_projection_output_commitment
    );
    check_field!(
        "activation_statement_commitment",
        activation_statement_commitment
    );
    check_field!(
        "activation_public_instance_commitment",
        activation_public_instance_commitment
    );
    check_field!("hidden_activation_commitment", hidden_activation_commitment);
    check_field!(
        "down_projection_statement_commitment",
        down_projection_statement_commitment
    );
    check_field!(
        "down_projection_public_instance_commitment",
        down_projection_public_instance_commitment
    );
    check_field!("residual_delta_commitment", residual_delta_commitment);
    check_field!(
        "residual_add_statement_commitment",
        residual_add_statement_commitment
    );
    check_field!(
        "residual_add_public_instance_commitment",
        residual_add_public_instance_commitment
    );
    check_field!("output_activation_commitment", output_activation_commitment);
    check_field!("residual_add_row_commitment", residual_add_row_commitment);
    mismatches
}

fn validate_fused_input(input: &ZkAiD128RmsnormMlpFusedInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D128_RMSNORM_MLP_FUSED_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D128_RMSNORM_MLP_FUSED_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(
        &input.route_id,
        ZKAI_D128_RMSNORM_MLP_FUSED_ROUTE_ID,
        "route id",
    )?;
    expect_eq(
        &input.target_id,
        &input.rmsnorm_input.target_id,
        "target id",
    )?;
    expect_eq(
        &input.required_backend_version,
        &input.rmsnorm_input.required_backend_version,
        "required backend version",
    )?;
    expect_eq(
        &input.verifier_domain,
        &input.rmsnorm_input.verifier_domain,
        "verifier domain",
    )?;
    expect_usize(input.width, WIDTH, "width")?;
    expect_usize(input.ff_dim, FF_DIM, "ff dim")?;
    expect_usize(input.rmsnorm_row_count, RMSNORM_ROWS, "RMSNorm row count")?;
    expect_usize(
        input.projection_bridge_row_count,
        PROJECTION_BRIDGE_ROWS,
        "projection bridge row count",
    )?;
    expect_usize(
        input.gate_value_row_count,
        GATE_VALUE_ROWS,
        "gate/value row count",
    )?;
    expect_usize(
        input.activation_row_count,
        ACTIVATION_ROWS,
        "activation row count",
    )?;
    expect_usize(
        input.down_projection_row_count,
        DOWN_PROJECTION_ROWS,
        "down-projection row count",
    )?;
    expect_usize(
        input.residual_add_row_count,
        RESIDUAL_ADD_ROWS,
        "residual-add row count",
    )?;
    expect_eq(
        &input.rmsnorm_proof_version,
        ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "RMSNorm proof version",
    )?;
    expect_eq(
        &input.projection_bridge_proof_version,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
        "projection bridge proof version",
    )?;
    expect_eq(
        &input.gate_value_proof_version,
        ZKAI_D128_GATE_VALUE_PROJECTION_PROOF_VERSION,
        "gate/value proof version",
    )?;
    expect_eq(
        &input.activation_swiglu_proof_version,
        ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
        "activation/SwiGLU proof version",
    )?;
    expect_eq(
        &input.down_projection_proof_version,
        ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION,
        "down-projection proof version",
    )?;
    expect_eq(
        &input.residual_add_proof_version,
        ZKAI_D128_RESIDUAL_ADD_PROOF_VERSION,
        "residual-add proof version",
    )?;
    let source_profile = approved_fused_source_profile(input)?;
    expect_eq(
        &input.rmsnorm_statement_commitment,
        source_profile.rmsnorm_statement_commitment,
        "RMSNorm statement commitment",
    )?;
    expect_eq(
        &input.rmsnorm_public_instance_commitment,
        source_profile.rmsnorm_public_instance_commitment,
        "RMSNorm public instance commitment",
    )?;
    expect_eq(
        &input.projection_bridge_statement_commitment,
        source_profile.projection_bridge_statement_commitment,
        "projection bridge statement commitment",
    )?;
    expect_eq(
        &input.projection_bridge_public_instance_commitment,
        source_profile.projection_bridge_public_instance_commitment,
        "projection bridge public instance commitment",
    )?;
    expect_eq(
        &input.gate_value_statement_commitment,
        source_profile.gate_value_statement_commitment,
        "gate/value statement commitment",
    )?;
    expect_eq(
        &input.gate_value_public_instance_commitment,
        source_profile.gate_value_public_instance_commitment,
        "gate/value public instance commitment",
    )?;
    expect_eq(
        &input.activation_statement_commitment,
        source_profile.activation_statement_commitment,
        "activation statement commitment",
    )?;
    expect_eq(
        &input.activation_public_instance_commitment,
        source_profile.activation_public_instance_commitment,
        "activation public instance commitment",
    )?;
    expect_eq(
        &input.down_projection_statement_commitment,
        source_profile.down_projection_statement_commitment,
        "down-projection statement commitment",
    )?;
    expect_eq(
        &input.down_projection_public_instance_commitment,
        source_profile.down_projection_public_instance_commitment,
        "down-projection public instance commitment",
    )?;
    expect_eq(
        &input.residual_add_statement_commitment,
        source_profile.residual_add_statement_commitment,
        "residual-add statement commitment",
    )?;
    expect_eq(
        &input.residual_add_public_instance_commitment,
        source_profile.residual_add_public_instance_commitment,
        "residual-add public instance commitment",
    )?;
    expect_eq(
        &input.input_activation_commitment,
        source_profile.input_activation_commitment,
        "input activation commitment",
    )?;
    expect_eq(
        &input.rmsnorm_output_row_commitment,
        source_profile.rmsnorm_output_row_commitment,
        "RMSNorm output row commitment",
    )?;
    expect_eq(
        &input.projection_input_row_commitment,
        source_profile.projection_input_row_commitment,
        "projection input row commitment",
    )?;
    expect_eq(
        &input.gate_projection_output_commitment,
        source_profile.gate_projection_output_commitment,
        "gate projection output commitment",
    )?;
    expect_eq(
        &input.value_projection_output_commitment,
        source_profile.value_projection_output_commitment,
        "value projection output commitment",
    )?;
    expect_eq(
        &input.gate_value_projection_output_commitment,
        source_profile.gate_value_projection_output_commitment,
        "gate/value projection output commitment",
    )?;
    expect_eq(
        &input.hidden_activation_commitment,
        source_profile.hidden_activation_commitment,
        "hidden activation commitment",
    )?;
    expect_eq(
        &input.residual_delta_commitment,
        source_profile.residual_delta_commitment,
        "residual delta commitment",
    )?;
    expect_eq(
        &input.output_activation_commitment,
        source_profile.output_activation_commitment,
        "output activation commitment",
    )?;
    expect_eq(
        &input.residual_add_row_commitment,
        source_profile.residual_add_row_commitment,
        "residual-add row commitment",
    )?;
    expect_vec_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non-claims")?;
    expect_vec_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_vec_eq(
        &input.validation_commands,
        source_profile.validation_commands,
        "validation commands",
    )?;
    validate_nested_rmsnorm_input(&input.rmsnorm_input)?;
    expect_eq(
        &input.rmsnorm_statement_commitment,
        &input.rmsnorm_input.statement_commitment,
        "RMSNorm statement commitment",
    )?;
    expect_eq(
        &input.rmsnorm_public_instance_commitment,
        &input.rmsnorm_input.public_instance_commitment,
        "RMSNorm public instance commitment",
    )?;
    expect_eq(
        &input.input_activation_commitment,
        &input.rmsnorm_input.input_activation_commitment,
        "input activation commitment",
    )?;
    expect_eq(
        &input.rmsnorm_output_row_commitment,
        &input.rmsnorm_input.rmsnorm_output_row_commitment,
        "RMSNorm output row commitment",
    )?;
    validate_nested_bridge_input(&input.projection_bridge_input)?;
    validate_nested_gate_value_input(&input.gate_value_input)?;
    validate_nested_activation_input(&input.activation_input)?;
    validate_nested_down_projection_input(&input.down_projection_input)?;
    validate_nested_residual_add_input(&input.residual_add_input)?;
    validate_top_level_metadata_matches_nested_chain(input)?;
    validate_rmsnorm_bridge_handoff(&input.rmsnorm_input, &input.projection_bridge_input)?;
    validate_bridge_gate_handoff(&input.projection_bridge_input, &input.gate_value_input)?;
    validate_gate_activation_handoff(&input.gate_value_input, &input.activation_input)?;
    validate_activation_down_handoff(&input.activation_input, &input.down_projection_input)?;
    validate_down_residual_handoff(&input.down_projection_input, &input.residual_add_input)?;
    validate_rmsnorm_residual_handoff(
        &input.rmsnorm_input,
        &input.residual_add_input,
        source_profile,
    )?;
    expect_eq(
        &input.statement_commitment,
        &statement_commitment(input)?,
        "statement commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        &public_instance_commitment(&input.statement_commitment)?,
        "public instance commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        &proof_native_parameter_commitment(&input.statement_commitment)?,
        "proof-native parameter commitment",
    )
}

fn validate_nested_rmsnorm_input(input: &ZkAiD128RmsnormPublicRowProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_rmsnorm_public_row_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_bridge_input(input: &ZkAiD128RmsnormToProjectionBridgeInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_gate_value_input(input: &ZkAiD128GateValueProjectionProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_gate_value_projection_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_activation_input(input: &ZkAiD128ActivationSwiGluProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_activation_swiglu_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_down_projection_input(input: &ZkAiD128DownProjectionProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_down_projection_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_residual_add_input(input: &ZkAiD128ResidualAddProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_residual_add_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_top_level_metadata_matches_nested_chain(
    input: &ZkAiD128RmsnormMlpFusedInput,
) -> Result<()> {
    expect_component_metadata(
        "RMSNorm",
        &input.rmsnorm_input.target_id,
        &input.rmsnorm_input.required_backend_version,
        &input.rmsnorm_input.verifier_domain,
        input,
    )?;
    expect_component_metadata(
        "projection bridge",
        &input.projection_bridge_input.target_id,
        &input.projection_bridge_input.required_backend_version,
        &input.projection_bridge_input.verifier_domain,
        input,
    )?;
    expect_component_metadata(
        "gate/value",
        &input.gate_value_input.target_id,
        &input.gate_value_input.required_backend_version,
        &input.gate_value_input.verifier_domain,
        input,
    )?;
    expect_component_metadata(
        "activation",
        &input.activation_input.target_id,
        &input.activation_input.required_backend_version,
        &input.activation_input.verifier_domain,
        input,
    )?;
    expect_component_metadata(
        "down-projection",
        &input.down_projection_input.target_id,
        &input.down_projection_input.required_backend_version,
        &input.down_projection_input.verifier_domain,
        input,
    )?;
    expect_component_metadata(
        "residual-add",
        &input.residual_add_input.target_id,
        &input.residual_add_input.required_backend_version,
        &input.residual_add_input.verifier_domain,
        input,
    )
}

fn expect_component_metadata(
    label: &str,
    target_id: &str,
    required_backend_version: &str,
    verifier_domain: &str,
    input: &ZkAiD128RmsnormMlpFusedInput,
) -> Result<()> {
    expect_eq(&input.target_id, target_id, &format!("{label} target id"))?;
    expect_eq(
        &input.required_backend_version,
        required_backend_version,
        &format!("{label} required backend version"),
    )?;
    expect_eq(
        &input.verifier_domain,
        verifier_domain,
        &format!("{label} verifier domain"),
    )
}

fn validate_rmsnorm_bridge_handoff(
    rmsnorm_input: &ZkAiD128RmsnormPublicRowProofInput,
    bridge_input: &ZkAiD128RmsnormToProjectionBridgeInput,
) -> Result<()> {
    expect_eq(
        &bridge_input.target_id,
        &rmsnorm_input.target_id,
        "bridge target id matches RMSNorm target id",
    )?;
    expect_eq(
        &bridge_input.required_backend_version,
        &rmsnorm_input.required_backend_version,
        "bridge required backend version matches RMSNorm required backend version",
    )?;
    expect_eq(
        &bridge_input.verifier_domain,
        &rmsnorm_input.verifier_domain,
        "bridge verifier domain matches RMSNorm verifier domain",
    )?;
    expect_eq(
        &bridge_input.source_rmsnorm_statement_commitment,
        &rmsnorm_input.statement_commitment,
        "bridge source RMSNorm statement commitment",
    )?;
    expect_eq(
        &bridge_input.source_rmsnorm_public_instance_commitment,
        &rmsnorm_input.public_instance_commitment,
        "bridge source RMSNorm public instance commitment",
    )?;
    expect_eq(
        &bridge_input.source_rmsnorm_output_row_commitment,
        &rmsnorm_input.rmsnorm_output_row_commitment,
        "bridge source RMSNorm output row commitment",
    )?;
    let rmsnorm_normed = rmsnorm_input
        .rows
        .iter()
        .map(|row| row.normed_q8)
        .collect::<Vec<_>>();
    let bridge_source = bridge_input
        .rows
        .iter()
        .map(|row| row.rmsnorm_normed_q8)
        .collect::<Vec<_>>();
    if bridge_source != rmsnorm_normed {
        return Err(fused_error(
            "bridge source rows do not match RMSNorm normed output rows",
        ));
    }
    Ok(())
}

fn validate_bridge_gate_handoff(
    bridge_input: &ZkAiD128RmsnormToProjectionBridgeInput,
    gate_value_input: &ZkAiD128GateValueProjectionProofInput,
) -> Result<()> {
    expect_eq(
        &gate_value_input.target_id,
        &bridge_input.target_id,
        "gate/value target id matches bridge target id",
    )?;
    expect_eq(
        &gate_value_input.required_backend_version,
        &bridge_input.required_backend_version,
        "gate/value required backend version matches bridge required backend version",
    )?;
    expect_eq(
        &gate_value_input.verifier_domain,
        &bridge_input.verifier_domain,
        "gate/value verifier domain matches bridge verifier domain",
    )?;
    expect_eq(
        &gate_value_input.source_bridge_proof_version,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
        "gate/value source bridge proof version",
    )?;
    expect_eq(
        &gate_value_input.source_projection_input_row_commitment,
        &bridge_input.projection_input_row_commitment,
        "gate/value source projection input row commitment",
    )?;
    let bridge_projection = bridge_input
        .rows
        .iter()
        .map(|row| row.projection_input_q8)
        .collect::<Vec<_>>();
    if gate_value_input.projection_input_q8 != bridge_projection {
        return Err(fused_error(
            "gate/value projection input vector does not match bridge projection output vector",
        ));
    }
    Ok(())
}

fn validate_gate_activation_handoff(
    gate_value_input: &ZkAiD128GateValueProjectionProofInput,
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
) -> Result<()> {
    expect_eq(
        &activation_input.target_id,
        &gate_value_input.target_id,
        "activation target id matches gate/value target id",
    )?;
    expect_eq(
        &activation_input.required_backend_version,
        &gate_value_input.required_backend_version,
        "activation required backend version matches gate/value required backend version",
    )?;
    expect_eq(
        &activation_input.verifier_domain,
        &gate_value_input.verifier_domain,
        "activation verifier domain matches gate/value verifier domain",
    )?;
    expect_eq(
        &activation_input.source_gate_value_projection_statement_commitment,
        &gate_value_input.statement_commitment,
        "activation source gate/value statement commitment",
    )?;
    expect_eq(
        &activation_input.source_gate_value_projection_public_instance_commitment,
        &gate_value_input.public_instance_commitment,
        "activation source gate/value public instance commitment",
    )?;
    expect_eq(
        &activation_input.source_gate_projection_output_commitment,
        &gate_value_input.gate_projection_output_commitment,
        "activation source gate projection output commitment",
    )?;
    expect_eq(
        &activation_input.source_value_projection_output_commitment,
        &gate_value_input.value_projection_output_commitment,
        "activation source value projection output commitment",
    )?;
    expect_eq(
        &activation_input.source_gate_value_projection_output_commitment,
        &gate_value_input.gate_value_projection_output_commitment,
        "activation source gate/value projection output commitment",
    )?;
    if activation_input.gate_projection_q8 != gate_value_input.gate_projection_q8 {
        return Err(fused_error(
            "activation source gate vector does not match gate/value output vector",
        ));
    }
    if activation_input.value_projection_q8 != gate_value_input.value_projection_q8 {
        return Err(fused_error(
            "activation source value vector does not match gate/value output vector",
        ));
    }
    Ok(())
}

fn validate_activation_down_handoff(
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
    down_projection_input: &ZkAiD128DownProjectionProofInput,
) -> Result<()> {
    expect_eq(
        &down_projection_input.target_id,
        &activation_input.target_id,
        "down-projection target id matches activation target id",
    )?;
    expect_eq(
        &down_projection_input.required_backend_version,
        &activation_input.required_backend_version,
        "down-projection required backend version matches activation required backend version",
    )?;
    expect_eq(
        &down_projection_input.verifier_domain,
        &activation_input.verifier_domain,
        "down-projection verifier domain matches activation verifier domain",
    )?;
    expect_eq(
        &down_projection_input.source_activation_swiglu_statement_commitment,
        &activation_input.statement_commitment,
        "down-projection source activation statement commitment",
    )?;
    expect_eq(
        &down_projection_input.source_activation_swiglu_public_instance_commitment,
        &activation_input.public_instance_commitment,
        "down-projection source activation public instance commitment",
    )?;
    expect_eq(
        &down_projection_input.source_hidden_activation_commitment,
        &activation_input.hidden_activation_commitment,
        "down-projection source hidden activation commitment",
    )?;
    if down_projection_input.hidden_q8 != activation_input.hidden_q8 {
        return Err(fused_error(
            "down-projection hidden vector does not match activation hidden output vector",
        ));
    }
    Ok(())
}

fn validate_down_residual_handoff(
    down_projection_input: &ZkAiD128DownProjectionProofInput,
    residual_add_input: &ZkAiD128ResidualAddProofInput,
) -> Result<()> {
    expect_eq(
        &residual_add_input.target_id,
        &down_projection_input.target_id,
        "residual-add target id matches down-projection target id",
    )?;
    expect_eq(
        &residual_add_input.required_backend_version,
        &down_projection_input.required_backend_version,
        "residual-add required backend version matches down-projection required backend version",
    )?;
    expect_eq(
        &residual_add_input.verifier_domain,
        &down_projection_input.verifier_domain,
        "residual-add verifier domain matches down-projection verifier domain",
    )?;
    expect_eq(
        &residual_add_input.source_down_projection_statement_commitment,
        &down_projection_input.statement_commitment,
        "residual-add source down-projection statement commitment",
    )?;
    expect_eq(
        &residual_add_input.source_down_projection_public_instance_commitment,
        &down_projection_input.public_instance_commitment,
        "residual-add source down-projection public instance commitment",
    )?;
    expect_eq(
        &residual_add_input.residual_delta_commitment,
        &down_projection_input.residual_delta_commitment,
        "residual-add residual delta commitment",
    )?;
    if residual_add_input.residual_delta_q8 != down_projection_input.residual_delta_q8 {
        return Err(fused_error(
            "residual-add residual delta vector does not match down-projection output vector",
        ));
    }
    if residual_add_input.residual_delta_remainder_q8
        != down_projection_input.residual_delta_remainder_q8
    {
        return Err(fused_error(
            "residual-add residual remainder vector does not match down-projection remainder vector",
        ));
    }
    Ok(())
}

fn validate_rmsnorm_residual_handoff(
    rmsnorm_input: &ZkAiD128RmsnormPublicRowProofInput,
    residual_add_input: &ZkAiD128ResidualAddProofInput,
    source_profile: FusedSourceProfile,
) -> Result<()> {
    expect_eq(
        &residual_add_input.source_rmsnorm_proof_version,
        source_profile.residual_source_proof_version,
        "residual-add source input proof version",
    )?;
    expect_eq(
        &residual_add_input.source_rmsnorm_statement_commitment,
        source_profile.residual_source_statement_commitment,
        "residual-add source input statement commitment",
    )?;
    expect_eq(
        &residual_add_input.input_activation_commitment,
        &rmsnorm_input.input_activation_commitment,
        "residual-add input activation commitment",
    )?;
    let rmsnorm_input_q8 = rmsnorm_input
        .rows
        .iter()
        .map(|row| row.input_q8)
        .collect::<Vec<_>>();
    if residual_add_input.input_q8 != rmsnorm_input_q8 {
        return Err(fused_error(
            "residual-add input vector does not match original RMSNorm input activation vector",
        ));
    }
    Ok(())
}

fn prove_fused_components(input: &ZkAiD128RmsnormMlpFusedInput) -> Result<Vec<u8>> {
    let gate_rows = zkai_d128_gate_value_projection_rows(&input.gate_value_input)?;
    let preprocessed_ids = fused_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let down_projection_component =
        zkai_d128_down_projection_component_with_allocator(&mut allocator);
    let residual_add_component = zkai_d128_residual_add_component_with_allocator(&mut allocator);
    let config = publication_v1_pcs_config();
    let max_constraint_log_degree_bound = rmsnorm_component
        .max_constraint_log_degree_bound()
        .max(bridge_component.max_constraint_log_degree_bound())
        .max(gate_value_component.max_constraint_log_degree_bound())
        .max(activation_component.max_constraint_log_degree_bound())
        .max(down_projection_component.max_constraint_log_degree_bound())
        .max(residual_add_component.max_constraint_log_degree_bound());
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let preprocessed_trace = fused_preprocessed_trace(
        &input.rmsnorm_input,
        &input.projection_bridge_input,
        &gate_rows,
        &input.activation_input,
        &input.down_projection_input,
        &input.residual_add_input,
    )?;
    if preprocessed_trace.len() != preprocessed_ids.len() {
        return Err(fused_error(format!(
            "fused preprocessed trace column count drift: got {}, expected {}",
            preprocessed_trace.len(),
            preprocessed_ids.len()
        )));
    }
    let fused_trace = fused_trace(
        &input.rmsnorm_input,
        &input.projection_bridge_input,
        &gate_rows,
        &input.activation_input,
        &input.down_projection_input,
        &input.residual_add_input,
    )?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(preprocessed_trace);
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(fused_trace);
    tree_builder.commit(channel);

    let components: [&dyn ComponentProver<SimdBackend>; 6] = [
        &rmsnorm_component,
        &bridge_component,
        &gate_value_component,
        &activation_component,
        &down_projection_component,
        &residual_add_component,
    ];
    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&components, channel, commitment_scheme)
            .map_err(|error| {
                fused_error(format!(
                    "d128 RMSNorm plus MLP fused AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128RmsnormMlpFusedProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_fused_components(input: &ZkAiD128RmsnormMlpFusedInput, proof: &[u8]) -> Result<bool> {
    let payload: D128RmsnormMlpFusedProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_fused_pcs_config(stark_proof.config)?;
    let preprocessed_ids = fused_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let down_projection_component =
        zkai_d128_down_projection_component_with_allocator(&mut allocator);
    let residual_add_component = zkai_d128_residual_add_component_with_allocator(&mut allocator);
    let components: Vec<&dyn Component> = vec![
        &rmsnorm_component,
        &bridge_component,
        &gate_value_component,
        &activation_component,
        &down_projection_component,
        &residual_add_component,
    ];
    let sizes = Components {
        components: components.clone(),
        n_preprocessed_columns: preprocessed_ids.len(),
    }
    .column_log_sizes();
    if sizes.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(fused_error(format!(
            "internal fused component tree count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(fused_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = fused_commitment_roots(input, config)?;
    if expected_roots.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(fused_error(format!(
            "expected roots count mismatch: got {}, expected {}",
            expected_roots.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(fused_error(
            "preprocessed commitment does not match checked fused component rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(fused_error(
            "base commitment does not match checked fused component rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&components, channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            fused_error(format!(
                "RMSNorm-MLP fused STARK verification failed: {error}"
            ))
        })
}

fn fused_commitment_roots(
    input: &ZkAiD128RmsnormMlpFusedInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let gate_rows = zkai_d128_gate_value_projection_rows(&input.gate_value_input)?;
    let preprocessed_ids = fused_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let down_projection_component =
        zkai_d128_down_projection_component_with_allocator(&mut allocator);
    let residual_add_component = zkai_d128_residual_add_component_with_allocator(&mut allocator);
    let max_constraint_log_degree_bound = rmsnorm_component
        .max_constraint_log_degree_bound()
        .max(bridge_component.max_constraint_log_degree_bound())
        .max(gate_value_component.max_constraint_log_degree_bound())
        .max(activation_component.max_constraint_log_degree_bound())
        .max(down_projection_component.max_constraint_log_degree_bound())
        .max(residual_add_component.max_constraint_log_degree_bound());
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let preprocessed_trace = fused_preprocessed_trace(
        &input.rmsnorm_input,
        &input.projection_bridge_input,
        &gate_rows,
        &input.activation_input,
        &input.down_projection_input,
        &input.residual_add_input,
    )?;
    if preprocessed_trace.len() != preprocessed_ids.len() {
        return Err(fused_error(format!(
            "fused preprocessed trace column count drift: got {}, expected {}",
            preprocessed_trace.len(),
            preprocessed_ids.len()
        )));
    }
    let trace = fused_trace(
        &input.rmsnorm_input,
        &input.projection_bridge_input,
        &gate_rows,
        &input.activation_input,
        &input.down_projection_input,
        &input.residual_add_input,
    )?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(preprocessed_trace);
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(trace);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn fused_trace(
    rmsnorm_input: &ZkAiD128RmsnormPublicRowProofInput,
    bridge_input: &ZkAiD128RmsnormToProjectionBridgeInput,
    gate_rows: &[D128GateValueProjectionMulRow],
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
    down_projection_input: &ZkAiD128DownProjectionProofInput,
    residual_add_input: &ZkAiD128ResidualAddProofInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let mut trace = zkai_d128_rmsnorm_public_row_trace(rmsnorm_input);
    trace.extend(zkai_d128_rmsnorm_to_projection_bridge_trace(bridge_input));
    trace.extend(zkai_d128_gate_value_projection_trace(gate_rows)?);
    trace.extend(zkai_d128_activation_swiglu_trace(activation_input)?);
    trace.extend(zkai_d128_down_projection_trace(down_projection_input)?);
    trace.extend(zkai_d128_residual_add_trace(residual_add_input));
    Ok(trace)
}

fn fused_preprocessed_trace(
    rmsnorm_input: &ZkAiD128RmsnormPublicRowProofInput,
    bridge_input: &ZkAiD128RmsnormToProjectionBridgeInput,
    gate_rows: &[D128GateValueProjectionMulRow],
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
    down_projection_input: &ZkAiD128DownProjectionProofInput,
    residual_add_input: &ZkAiD128ResidualAddProofInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    // These component AIRs mirror checked row values into preprocessed columns.
    fused_trace(
        rmsnorm_input,
        bridge_input,
        gate_rows,
        activation_input,
        down_projection_input,
        residual_add_input,
    )
}

fn fused_preprocessed_column_ids() -> Result<Vec<PreProcessedColumnId>> {
    let mut ids = zkai_d128_rmsnorm_public_row_preprocessed_column_ids();
    ids.extend(zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids());
    ids.extend(zkai_d128_gate_value_projection_preprocessed_column_ids());
    ids.extend(zkai_d128_activation_swiglu_preprocessed_column_ids());
    ids.extend(zkai_d128_down_projection_preprocessed_column_ids());
    ids.extend(zkai_d128_residual_add_preprocessed_column_ids());
    let mut seen = BTreeSet::new();
    for id in &ids {
        if !seen.insert(id.id.clone()) {
            return Err(fused_error(format!(
                "duplicate fused preprocessed column id: {}",
                id.id
            )));
        }
    }
    Ok(ids)
}

fn validate_fused_pcs_config(config: PcsConfig) -> Result<PcsConfig> {
    if !publication_v1_pcs_config_matches(&config) {
        return Err(fused_error("unexpected PCS config for fused proof"));
    }
    Ok(publication_v1_pcs_config())
}

fn statement_commitment(input: &ZkAiD128RmsnormMlpFusedInput) -> Result<String> {
    let payload = serde_json::json!({
        "activation_public_instance_commitment": input.activation_public_instance_commitment,
        "activation_row_count": input.activation_row_count,
        "activation_statement_commitment": input.activation_statement_commitment,
        "activation_swiglu_proof_version": input.activation_swiglu_proof_version,
        "down_projection_proof_version": input.down_projection_proof_version,
        "down_projection_public_instance_commitment": input.down_projection_public_instance_commitment,
        "down_projection_row_count": input.down_projection_row_count,
        "down_projection_statement_commitment": input.down_projection_statement_commitment,
        "ff_dim": input.ff_dim,
        "gate_value_projection_output_commitment": input.gate_value_projection_output_commitment,
        "gate_value_proof_version": input.gate_value_proof_version,
        "gate_value_public_instance_commitment": input.gate_value_public_instance_commitment,
        "gate_value_row_count": input.gate_value_row_count,
        "gate_value_statement_commitment": input.gate_value_statement_commitment,
        "hidden_activation_commitment": input.hidden_activation_commitment,
        "input_activation_commitment": input.input_activation_commitment,
        "operation": "rmsnorm_mlp_fused",
        "output_activation_commitment": input.output_activation_commitment,
        "projection_bridge_proof_version": input.projection_bridge_proof_version,
        "projection_bridge_public_instance_commitment": input.projection_bridge_public_instance_commitment,
        "projection_bridge_row_count": input.projection_bridge_row_count,
        "projection_bridge_statement_commitment": input.projection_bridge_statement_commitment,
        "projection_input_row_commitment": input.projection_input_row_commitment,
        "required_backend_version": input.required_backend_version,
        "residual_add_proof_version": input.residual_add_proof_version,
        "residual_add_public_instance_commitment": input.residual_add_public_instance_commitment,
        "residual_add_row_commitment": input.residual_add_row_commitment,
        "residual_add_row_count": input.residual_add_row_count,
        "residual_add_statement_commitment": input.residual_add_statement_commitment,
        "residual_delta_commitment": input.residual_delta_commitment,
        "rmsnorm_output_row_commitment": input.rmsnorm_output_row_commitment,
        "rmsnorm_proof_version": input.rmsnorm_proof_version,
        "rmsnorm_public_instance_commitment": input.rmsnorm_public_instance_commitment,
        "rmsnorm_row_count": input.rmsnorm_row_count,
        "rmsnorm_statement_commitment": input.rmsnorm_statement_commitment,
        "route_id": input.route_id,
        "target_id": input.target_id,
        "verifier_domain": input.verifier_domain,
        "width": input.width,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, STATEMENT_DOMAIN))
}

fn public_instance_commitment(statement: &str) -> Result<String> {
    let payload = serde_json::json!({
        "operation": "rmsnorm_mlp_fused",
        "route_id": ZKAI_D128_RMSNORM_MLP_FUSED_ROUTE_ID,
        "statement_commitment": statement,
        "width": WIDTH,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, PUBLIC_INSTANCE_DOMAIN))
}

fn proof_native_parameter_commitment(statement: &str) -> Result<String> {
    let payload = serde_json::json!({
        "kind": PROOF_NATIVE_PARAMETER_KIND,
        "pcs_profile": "publication_v1",
        "statement_commitment": statement,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(
        &bytes,
        PROOF_NATIVE_PARAMETER_DOMAIN,
    ))
}

fn blake2b_commitment_bytes(bytes: &[u8], domain: &str) -> String {
    let mut hasher = Blake2bVar::new(32).expect("valid blake2b output length");
    hasher.update(domain.as_bytes());
    hasher.update(&[0]);
    hasher.update(bytes);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b output length is fixed");
    format!(
        "blake2b-256:{}",
        out.iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    )
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(fused_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(fused_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_vec_eq(actual: &[String], expected: &[&str], label: &str) -> Result<()> {
    let expected_strings = expected
        .iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    if actual != expected_strings {
        return Err(fused_error(format!("{label} drift")));
    }
    Ok(())
}

fn fused_error(message: impl Into<String>) -> VmError {
    VmError::UnsupportedProof(format!("d128 RMSNorm-MLP fused proof: {}", message.into()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_input() -> ZkAiD128RmsnormMlpFusedInput {
        let rmsnorm_raw = include_str!(
            "../../docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json"
        );
        let bridge_raw = include_str!(
            "../../docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
        );
        let gate_raw = include_str!(
            "../../docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json"
        );
        let rmsnorm =
            zkai_d128_rmsnorm_public_row_input_from_json_str(rmsnorm_raw).expect("rmsnorm fixture");
        let bridge = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(bridge_raw)
            .expect("bridge fixture");
        let gate = zkai_d128_gate_value_projection_input_from_json_str(gate_raw)
            .expect("gate/value fixture");
        let activation = zkai_d128_activation_swiglu_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json"
        ))
        .expect("activation fixture");
        let down = zkai_d128_down_projection_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json"
        ))
        .expect("down fixture");
        let residual = zkai_d128_residual_add_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json"
        ))
        .expect("residual fixture");
        build_zkai_d128_rmsnorm_mlp_fused_input(rmsnorm, bridge, gate, activation, down, residual)
            .expect("fused input")
    }

    fn derived_fixture_input() -> ZkAiD128RmsnormMlpFusedInput {
        let rmsnorm_wrapper: serde_json::Value = serde_json::from_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
        ))
        .expect("derived rmsnorm wrapper");
        let rmsnorm_raw = serde_json::to_string(
            rmsnorm_wrapper
                .get("rmsnorm_public_row_payload")
                .expect("derived rmsnorm payload"),
        )
        .expect("derived rmsnorm payload JSON");
        let rmsnorm = zkai_d128_rmsnorm_public_row_input_from_json_str(&rmsnorm_raw)
            .expect("rmsnorm fixture");
        let bridge = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json"
        ))
        .expect("bridge fixture");
        let gate = zkai_d128_gate_value_projection_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json"
        ))
        .expect("gate/value fixture");
        let activation = zkai_d128_activation_swiglu_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json"
        ))
        .expect("activation fixture");
        let down = zkai_d128_down_projection_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json"
        ))
        .expect("down fixture");
        let residual = zkai_d128_residual_add_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json"
        ))
        .expect("residual fixture");
        build_zkai_d128_rmsnorm_mlp_fused_input(rmsnorm, bridge, gate, activation, down, residual)
            .expect("derived fused input")
    }

    fn fixture_envelope() -> ZkAiD128RmsnormMlpFusedEnvelope {
        zkai_d128_rmsnorm_mlp_fused_envelope_from_json_slice(include_bytes!(
            "../../docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json"
        ))
        .expect("fused envelope")
    }

    #[test]
    fn fused_input_validates_expected_chain() {
        let input = fixture_input();
        assert_eq!(input.rmsnorm_row_count, 128);
        assert_eq!(input.projection_bridge_row_count, 128);
        assert_eq!(input.gate_value_row_count, 131_072);
        assert_eq!(input.activation_row_count, 512);
        assert_eq!(input.down_projection_row_count, 65_536);
        assert_eq!(input.residual_add_row_count, 128);
        assert_eq!(
            input.projection_input_row_commitment,
            input
                .gate_value_input
                .source_projection_input_row_commitment
        );
        validate_fused_input(&input).expect("input validates");
    }

    #[test]
    fn fused_input_accepts_attention_derived_component_chain() {
        let input = derived_fixture_input();
        assert_eq!(
            input.input_activation_commitment,
            ZKAI_D128_ATTENTION_DERIVED_INPUT_ACTIVATION_COMMITMENT
        );
        assert_eq!(
            input.residual_add_input.source_rmsnorm_proof_version,
            ZKAI_D128_ATTENTION_DERIVED_INPUT_PROOF_VERSION
        );
        assert_eq!(
            input.validation_commands,
            EXPECTED_ATTENTION_DERIVED_VALIDATION_COMMANDS
        );
        validate_fused_input(&input).expect("derived input validates");
    }

    #[test]
    fn fused_input_rejects_mixed_attention_derived_source_profile() {
        let mut input = derived_fixture_input();
        input.residual_add_input.source_rmsnorm_statement_commitment =
            ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT.to_string();
        input.statement_commitment = statement_commitment(&input).expect("statement commitment");
        input.public_instance_commitment =
            public_instance_commitment(&input.statement_commitment).expect("public instance");
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment).expect("proof params");
        assert!(validate_fused_input(&input).is_err());
    }

    #[test]
    fn fused_input_rejects_bridge_projection_drift() {
        let mut input = fixture_input();
        input.projection_bridge_input.rows[0].projection_input_q8 += 1;
        assert!(validate_fused_input(&input).is_err());
    }

    #[test]
    fn fused_input_rejects_residual_source_drift() {
        let mut input = fixture_input();
        input.residual_add_input.input_q8[0] += 1;
        assert!(validate_fused_input(&input).is_err());
    }

    #[test]
    fn fused_input_rejects_rmsnorm_public_instance_commitment_drift() {
        let mut input = fixture_input();
        input.rmsnorm_public_instance_commitment =
            "blake2b-256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
                .to_string();
        input.statement_commitment = statement_commitment(&input).expect("statement commitment");
        input.public_instance_commitment =
            public_instance_commitment(&input.statement_commitment).expect("public instance");
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment).expect("proof params");
        assert!(validate_fused_input(&input).is_err());
    }

    #[test]
    fn fused_input_rejects_top_level_target_drift() {
        let mut input = fixture_input();
        input.target_id = "d128-different-target".to_string();
        input.statement_commitment = statement_commitment(&input).expect("statement commitment");
        input.public_instance_commitment =
            public_instance_commitment(&input.statement_commitment).expect("public instance");
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment).expect("proof params");
        assert!(validate_fused_input(&input).is_err());
    }

    #[test]
    fn fused_input_rejects_rmsnorm_output_commitment_drift() {
        let mut input = fixture_input();
        input.rmsnorm_output_row_commitment =
            "blake2b-256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
                .to_string();
        input.statement_commitment = statement_commitment(&input).expect("statement commitment");
        input.public_instance_commitment =
            public_instance_commitment(&input.statement_commitment).expect("public instance");
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment).expect("proof params");
        assert!(validate_fused_input(&input).is_err());
    }

    #[test]
    fn fused_envelope_rejects_empty_proof() {
        let mut envelope = fixture_envelope();
        envelope.proof.clear();
        assert!(verify_zkai_d128_rmsnorm_mlp_fused_envelope(&envelope).is_err());
    }

    #[test]
    fn fused_envelope_rejects_oversized_proof() {
        let mut envelope = fixture_envelope();
        envelope.proof = vec![0; ZKAI_D128_RMSNORM_MLP_FUSED_MAX_PROOF_BYTES + 1];
        assert!(verify_zkai_d128_rmsnorm_mlp_fused_envelope(&envelope).is_err());
    }

    #[test]
    fn fused_envelope_rejects_nested_handoff_drift() {
        let mut envelope = fixture_envelope();
        envelope.input.residual_add_input.input_q8[0] += 1;
        assert!(verify_zkai_d128_rmsnorm_mlp_fused_envelope(&envelope).is_err());
    }
}
