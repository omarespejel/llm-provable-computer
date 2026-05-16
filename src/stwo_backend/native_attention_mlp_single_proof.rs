use std::collections::BTreeSet;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use stwo::core::air::{Component, Components};
use stwo::core::channel::{Blake2sM31Channel, Channel};
use stwo::core::fields::m31::BaseField;
use stwo::core::fields::qm31::SecureField;
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

use super::attention_kv_native_d8_bounded_softmax_table_proof::ZkAiAttentionKvNativeD8BoundedSoftmaxTableProofInput;
use super::attention_kv_native_d8_fused_softmax_table_proof::{
    zkai_attention_kv_native_d8_fused_softmax_table_base_trace,
    zkai_attention_kv_native_d8_fused_softmax_table_component_with_allocator,
    zkai_attention_kv_native_d8_fused_softmax_table_interaction_trace,
    zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_column_ids,
    zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_trace,
    zkai_attention_kv_native_d8_fused_softmax_table_summary,
    zkai_attention_kv_native_d8_fused_softmax_table_validate_source_input,
    AttentionKvD8FusedSoftmaxTableRelation, ZkAiAttentionKvNativeD8FusedSoftmaxTableSummary,
    ZKAI_ATTENTION_KV_NATIVE_D8_FUSED_SOFTMAX_TABLE_PROOF_VERSION,
};
use super::d128_native_activation_swiglu_proof::{
    zkai_d128_activation_swiglu_component_with_allocator,
    zkai_d128_activation_swiglu_preprocessed_column_ids, zkai_d128_activation_swiglu_trace,
};
use super::d128_native_down_projection_proof::{
    zkai_d128_down_projection_component_with_allocator,
    zkai_d128_down_projection_preprocessed_column_ids, zkai_d128_down_projection_trace,
};
use super::d128_native_gate_value_projection_proof::{
    zkai_d128_gate_value_projection_component_with_allocator,
    zkai_d128_gate_value_projection_preprocessed_column_ids, zkai_d128_gate_value_projection_rows,
    zkai_d128_gate_value_projection_trace,
};
use super::d128_native_residual_add_proof::{
    zkai_d128_residual_add_component_with_allocator,
    zkai_d128_residual_add_preprocessed_column_ids, zkai_d128_residual_add_trace,
    ZKAI_D128_ATTENTION_DERIVED_INPUT_ACTIVATION_COMMITMENT,
    ZKAI_D128_ATTENTION_DERIVED_INPUT_PROOF_VERSION,
    ZKAI_D128_ATTENTION_DERIVED_INPUT_STATEMENT_COMMITMENT,
};
use super::d128_native_rmsnorm_mlp_fused_proof::{
    zkai_d128_rmsnorm_mlp_fused_validate_input, ZkAiD128RmsnormMlpFusedInput,
    ZKAI_D128_RMSNORM_MLP_FUSED_PROOF_VERSION,
};
use super::d128_native_rmsnorm_public_row_proof::{
    zkai_d128_rmsnorm_public_row_component_with_allocator,
    zkai_d128_rmsnorm_public_row_preprocessed_column_ids, zkai_d128_rmsnorm_public_row_trace,
};
use super::d128_native_rmsnorm_to_projection_bridge_proof::{
    zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator,
    zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids,
    zkai_d128_rmsnorm_to_projection_bridge_trace,
};
use super::{publication_v1_pcs_config, publication_v1_pcs_config_matches};

pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_INPUT_SCHEMA: &str =
    "zkai-native-attention-mlp-single-proof-object-input-v1";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_INPUT_DECISION: &str =
    "GO_INPUT_FOR_NATIVE_ATTENTION_MLP_SINGLE_PROOF_OBJECT_PROBE";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_BACKEND_VERSION: &str =
    "stwo-native-attention-mlp-single-proof-object-probe-v1";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_PROOF_VERSION: &str =
    "stwo-native-attention-mlp-single-proof-object-payload-v1";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_STATEMENT_VERSION: &str =
    "zkai-native-attention-mlp-single-proof-object-statement-v1";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_SEMANTIC_SCOPE: &str =
    "d8_attention_softmax_table_and_attention_derived_d128_rmsnorm_mlp_surfaces_in_one_native_stwo_proof_object";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_DECISION: &str =
    "GO_SINGLE_NATIVE_STWO_PROOF_OBJECT_FOR_STATEMENT_BOUND_ATTENTION_DERIVED_MLP_SURFACES";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_ROUTE_ID: &str =
    "native_stwo_d8_attention_softmax_table_plus_attention_derived_d128_rmsnorm_mlp_single_proof_object_probe";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_TARGET_ID: &str =
    "attention-kv-d8-fused-softmax-table-plus-attention-derived-d128-rmsnorm-mlp-v1";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:native-attention-mlp-single-proof-object:v1";
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES: usize = 2_097_152;
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_PROOF_BYTES: usize = 2_097_152;
pub const ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_ENVELOPE_JSON_BYTES: usize = 10_485_760;

const ATTENTION_LOG_SIZE: u32 = 6;
const EXPECTED_TRACE_COMMITMENT_TREES: usize = 3;
const EXPECTED_PROOF_COMMITMENTS: usize = 4;
const CURRENT_TWO_PROOF_FRONTIER_TYPED_BYTES: usize = 40_700;
const CURRENT_ATTENTION_FUSED_TYPED_BYTES: usize = 18_124;
const CURRENT_DERIVED_MLP_FUSED_TYPED_BYTES: usize = 22_576;
const NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES: usize = 6_900;
const SOURCE_ATTENTION_OUTPUTS_COMMITMENT: &str =
    "blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638";
const STATEMENT_DOMAIN: &str = "ptvm:zkai:native-attention-mlp-single-proof-statement:v1";
const PUBLIC_INSTANCE_DOMAIN: &str =
    "ptvm:zkai:native-attention-mlp-single-proof-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:native-attention-mlp-single-proof-native-parameter:v1";

const EXPECTED_ADAPTER_STATUS: &str =
    "STATEMENT_BOUND_ATTENTION_OUTPUT_TO_D128_INPUT_ADAPTER_NOT_NATIVE_AIR";
const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not a native AIR proof of the attention-output-to-d128-input adapter",
    "not a full transformer block",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not exact real-valued Softmax",
    "not full autoregressive inference",
    "not recursion or proof-carrying data",
    "not timing evidence",
    "not production-ready zkML",
];
const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "attention source input validated before proof construction",
    "attention fused summary recomputed before relation draw",
    "attention LogUp interaction trace committed in the same proof object",
    "attention output commitment pinned to the statement-bound d128 adapter source",
    "d128 RMSNorm-MLP fused input validated before proof construction",
    "d128 MLP input activation commitment pinned to the approved attention-derived vector",
    "d128 residual source anchors pinned to the approved attention-derived input statement",
    "combined preprocessed column IDs checked for uniqueness",
    "combined preprocessed trace column count checked before committing",
    "combined base trace binds attention rows and six MLP component traces",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "fixed publication-v1 PCS verifier profile before commitment-root recomputation",
    "commitment-vector length check before commitment indexing",
    "bounded proof bytes before JSON deserialization",
];
const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- build-input docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- prove docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.input.json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_native_attention_mlp_single_proof -- verify docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-native-attention-mlp-single-proof-binary-accounting-2026-05.json",
    "python3 scripts/zkai_native_attention_mlp_single_proof_gate.py --write-json docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-attention-mlp-single-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_native_attention_mlp_single_proof_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend native_attention_mlp_single_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiNativeAttentionMlpSingleProofInput {
    pub schema: String,
    pub decision: String,
    pub route_id: String,
    pub target_id: String,
    pub verifier_domain: String,
    pub attention_proof_version: String,
    pub mlp_proof_version: String,
    pub attention_statement_commitment: String,
    pub attention_public_instance_commitment: String,
    pub attention_outputs_commitment: String,
    pub attention_score_row_commitment: String,
    pub attention_weight_table_commitment: String,
    pub attention_lookup_claims: usize,
    pub attention_table_rows: usize,
    pub mlp_statement_commitment: String,
    pub mlp_public_instance_commitment: String,
    pub mlp_input_activation_commitment: String,
    pub mlp_output_activation_commitment: String,
    pub mlp_row_count: usize,
    pub adapter_status: String,
    pub pcs_lifting_log_size: u32,
    pub current_two_proof_frontier_typed_bytes: usize,
    pub current_attention_fused_typed_bytes: usize,
    pub current_derived_mlp_fused_typed_bytes: usize,
    pub nanozk_reported_d128_block_proof_bytes: usize,
    pub statement_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub attention_source_input: ZkAiAttentionKvNativeD8BoundedSoftmaxTableProofInput,
    pub mlp_input: ZkAiD128RmsnormMlpFusedInput,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiNativeAttentionMlpSingleProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub proof_schema_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub target_id: String,
    pub verifier_domain: String,
    pub input: ZkAiNativeAttentionMlpSingleProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct NativeAttentionMlpSingleProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn build_zkai_native_attention_mlp_single_proof_input(
    attention_source_input: ZkAiAttentionKvNativeD8BoundedSoftmaxTableProofInput,
    mlp_input: ZkAiD128RmsnormMlpFusedInput,
) -> Result<ZkAiNativeAttentionMlpSingleProofInput> {
    zkai_attention_kv_native_d8_fused_softmax_table_validate_source_input(&attention_source_input)?;
    zkai_d128_rmsnorm_mlp_fused_validate_input(&mlp_input)?;
    let attention_summary =
        zkai_attention_kv_native_d8_fused_softmax_table_summary(&attention_source_input)?;
    let pcs_lifting_log_size = single_pcs_config()?.lifting_log_size.ok_or_else(|| {
        single_error("single proof PCS config must pin an explicit lifting log size")
    })?;
    let mut input = ZkAiNativeAttentionMlpSingleProofInput {
        schema: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_INPUT_SCHEMA.to_string(),
        decision: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_INPUT_DECISION.to_string(),
        route_id: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_ROUTE_ID.to_string(),
        target_id: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_TARGET_ID.to_string(),
        verifier_domain: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_VERIFIER_DOMAIN.to_string(),
        attention_proof_version: ZKAI_ATTENTION_KV_NATIVE_D8_FUSED_SOFTMAX_TABLE_PROOF_VERSION
            .to_string(),
        mlp_proof_version: ZKAI_D128_RMSNORM_MLP_FUSED_PROOF_VERSION.to_string(),
        attention_statement_commitment: attention_source_input.statement_commitment.clone(),
        attention_public_instance_commitment: attention_source_input
            .public_instance_commitment
            .clone(),
        attention_outputs_commitment: attention_source_input.outputs_commitment.clone(),
        attention_score_row_commitment: attention_source_input.score_row_commitment.clone(),
        attention_weight_table_commitment: attention_source_input.weight_table_commitment.clone(),
        attention_lookup_claims: attention_summary.lookup_claims,
        attention_table_rows: attention_summary.table_rows,
        mlp_statement_commitment: mlp_input.statement_commitment.clone(),
        mlp_public_instance_commitment: mlp_input.public_instance_commitment.clone(),
        mlp_input_activation_commitment: mlp_input.input_activation_commitment.clone(),
        mlp_output_activation_commitment: mlp_input.output_activation_commitment.clone(),
        mlp_row_count: mlp_input.rmsnorm_row_count
            + mlp_input.projection_bridge_row_count
            + mlp_input.gate_value_row_count
            + mlp_input.activation_row_count
            + mlp_input.down_projection_row_count
            + mlp_input.residual_add_row_count,
        adapter_status: EXPECTED_ADAPTER_STATUS.to_string(),
        pcs_lifting_log_size,
        current_two_proof_frontier_typed_bytes: CURRENT_TWO_PROOF_FRONTIER_TYPED_BYTES,
        current_attention_fused_typed_bytes: CURRENT_ATTENTION_FUSED_TYPED_BYTES,
        current_derived_mlp_fused_typed_bytes: CURRENT_DERIVED_MLP_FUSED_TYPED_BYTES,
        nanozk_reported_d128_block_proof_bytes: NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        statement_commitment: String::new(),
        public_instance_commitment: String::new(),
        proof_native_parameter_commitment: String::new(),
        attention_source_input,
        mlp_input,
        non_claims: EXPECTED_NON_CLAIMS
            .iter()
            .map(|value| value.to_string())
            .collect(),
        proof_verifier_hardening: EXPECTED_PROOF_VERIFIER_HARDENING
            .iter()
            .map(|value| value.to_string())
            .collect(),
        validation_commands: EXPECTED_VALIDATION_COMMANDS
            .iter()
            .map(|value| value.to_string())
            .collect(),
    };
    input.statement_commitment = statement_commitment(&input)?;
    input.public_instance_commitment = public_instance_commitment(&input.statement_commitment)?;
    input.proof_native_parameter_commitment =
        proof_native_parameter_commitment(&input.statement_commitment)?;
    validate_single_input(&input)?;
    Ok(input)
}

pub fn zkai_native_attention_mlp_single_proof_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiNativeAttentionMlpSingleProofInput> {
    if raw_json.len() > ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES {
        return Err(single_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES
        )));
    }
    let input: ZkAiNativeAttentionMlpSingleProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_single_input(&input)?;
    Ok(input)
}

pub fn zkai_native_attention_mlp_single_proof_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiNativeAttentionMlpSingleProofEnvelope> {
    if raw_json.len() > ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_ENVELOPE_JSON_BYTES {
        return Err(single_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiNativeAttentionMlpSingleProofEnvelope = serde_json::from_slice(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_single_envelope(&envelope)?;
    Ok(envelope)
}

pub fn prove_zkai_native_attention_mlp_single_proof_envelope(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
) -> Result<ZkAiNativeAttentionMlpSingleProofEnvelope> {
    validate_single_input(input)?;
    let proof = prove_single_proof(input)?;
    if proof.len() > ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_PROOF_BYTES {
        return Err(single_error(format!(
            "proof bytes exceed bounded prover limit: got {}, max {}",
            proof.len(),
            ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_PROOF_BYTES
        )));
    }
    Ok(ZkAiNativeAttentionMlpSingleProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_BACKEND_VERSION.to_string(),
        proof_schema_version: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_PROOF_VERSION.to_string(),
        statement_version: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_DECISION.to_string(),
        target_id: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_TARGET_ID.to_string(),
        verifier_domain: ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_VERIFIER_DOMAIN.to_string(),
        input: input.clone(),
        proof,
    })
}

pub fn verify_zkai_native_attention_mlp_single_proof_envelope(
    envelope: &ZkAiNativeAttentionMlpSingleProofEnvelope,
) -> Result<bool> {
    validate_single_envelope(envelope)?;
    verify_single_proof(&envelope.input, &envelope.proof)
}

fn validate_single_envelope(envelope: &ZkAiNativeAttentionMlpSingleProofEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(single_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_BACKEND_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.proof_schema_version,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_PROOF_VERSION,
        "proof schema version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_DECISION,
        "decision",
    )?;
    expect_eq(
        &envelope.target_id,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_TARGET_ID,
        "target id",
    )?;
    expect_eq(
        &envelope.verifier_domain,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    if envelope.proof.is_empty()
        || envelope.proof.len() > ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_PROOF_BYTES
    {
        return Err(single_error("proof byte length outside bounded cap"));
    }
    validate_single_input(&envelope.input)
}

fn validate_single_input(input: &ZkAiNativeAttentionMlpSingleProofInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(
        &input.route_id,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_ROUTE_ID,
        "route id",
    )?;
    expect_eq(
        &input.target_id,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_TARGET_ID,
        "target id",
    )?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_eq(
        &input.attention_proof_version,
        ZKAI_ATTENTION_KV_NATIVE_D8_FUSED_SOFTMAX_TABLE_PROOF_VERSION,
        "attention proof version",
    )?;
    expect_eq(
        &input.mlp_proof_version,
        ZKAI_D128_RMSNORM_MLP_FUSED_PROOF_VERSION,
        "MLP proof version",
    )?;
    zkai_attention_kv_native_d8_fused_softmax_table_validate_source_input(
        &input.attention_source_input,
    )?;
    zkai_d128_rmsnorm_mlp_fused_validate_input(&input.mlp_input)?;
    let attention_summary =
        zkai_attention_kv_native_d8_fused_softmax_table_summary(&input.attention_source_input)?;
    expect_attention_summary(input, &attention_summary)?;
    expect_eq(
        &input.attention_outputs_commitment,
        SOURCE_ATTENTION_OUTPUTS_COMMITMENT,
        "attention output commitment route pin",
    )?;
    expect_eq(
        &input.attention_outputs_commitment,
        &input.attention_source_input.outputs_commitment,
        "attention output commitment source",
    )?;
    expect_eq(
        &input.mlp_input_activation_commitment,
        ZKAI_D128_ATTENTION_DERIVED_INPUT_ACTIVATION_COMMITMENT,
        "MLP input activation commitment route pin",
    )?;
    expect_eq(
        &input.mlp_input_activation_commitment,
        &input.mlp_input.input_activation_commitment,
        "MLP input activation commitment",
    )?;
    expect_eq(
        &input
            .mlp_input
            .residual_add_input
            .source_rmsnorm_proof_version,
        ZKAI_D128_ATTENTION_DERIVED_INPUT_PROOF_VERSION,
        "MLP residual source proof version",
    )?;
    expect_eq(
        &input
            .mlp_input
            .residual_add_input
            .source_rmsnorm_statement_commitment,
        ZKAI_D128_ATTENTION_DERIVED_INPUT_STATEMENT_COMMITMENT,
        "MLP residual source statement commitment",
    )?;
    expect_eq(
        &input.mlp_statement_commitment,
        &input.mlp_input.statement_commitment,
        "MLP statement commitment",
    )?;
    expect_eq(
        &input.mlp_public_instance_commitment,
        &input.mlp_input.public_instance_commitment,
        "MLP public instance commitment",
    )?;
    expect_eq(
        &input.mlp_output_activation_commitment,
        &input.mlp_input.output_activation_commitment,
        "MLP output activation commitment",
    )?;
    expect_usize(
        input.mlp_row_count,
        input.mlp_input.rmsnorm_row_count
            + input.mlp_input.projection_bridge_row_count
            + input.mlp_input.gate_value_row_count
            + input.mlp_input.activation_row_count
            + input.mlp_input.down_projection_row_count
            + input.mlp_input.residual_add_row_count,
        "MLP row count",
    )?;
    expect_eq(
        &input.adapter_status,
        EXPECTED_ADAPTER_STATUS,
        "adapter status",
    )?;
    let expected_lifting_log_size = single_pcs_config()?.lifting_log_size.ok_or_else(|| {
        single_error("single proof PCS config must pin an explicit lifting log size")
    })?;
    expect_usize(
        input.pcs_lifting_log_size as usize,
        expected_lifting_log_size as usize,
        "PCS lifting log size",
    )?;
    expect_usize(
        input.current_two_proof_frontier_typed_bytes,
        CURRENT_TWO_PROOF_FRONTIER_TYPED_BYTES,
        "current two-proof frontier typed bytes",
    )?;
    expect_usize(
        input.current_attention_fused_typed_bytes,
        CURRENT_ATTENTION_FUSED_TYPED_BYTES,
        "current attention fused typed bytes",
    )?;
    expect_usize(
        input.current_derived_mlp_fused_typed_bytes,
        CURRENT_DERIVED_MLP_FUSED_TYPED_BYTES,
        "current derived MLP fused typed bytes",
    )?;
    expect_usize(
        input.nanozk_reported_d128_block_proof_bytes,
        NANOZK_REPORTED_D128_BLOCK_PROOF_BYTES,
        "NANOZK reported d128 block proof bytes",
    )?;
    expect_vec_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non-claims")?;
    expect_vec_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_vec_eq(
        &input.validation_commands,
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
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
    )?;
    let ids = combined_preprocessed_column_ids()?;
    if ids.is_empty() {
        return Err(single_error("combined preprocessed column IDs are empty"));
    }
    Ok(())
}

fn expect_attention_summary(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
    summary: &ZkAiAttentionKvNativeD8FusedSoftmaxTableSummary,
) -> Result<()> {
    expect_eq(
        &input.attention_statement_commitment,
        &input.attention_source_input.statement_commitment,
        "attention statement commitment source",
    )?;
    expect_eq(
        &input.attention_statement_commitment,
        &summary.source_statement_commitment,
        "attention statement commitment summary",
    )?;
    expect_eq(
        &input.attention_public_instance_commitment,
        &input.attention_source_input.public_instance_commitment,
        "attention public instance commitment source",
    )?;
    expect_eq(
        &input.attention_public_instance_commitment,
        &summary.source_public_instance_commitment,
        "attention public instance commitment summary",
    )?;
    expect_eq(
        &input.attention_score_row_commitment,
        &input.attention_source_input.score_row_commitment,
        "attention score row commitment source",
    )?;
    expect_eq(
        &input.attention_score_row_commitment,
        &summary.source_score_row_commitment,
        "attention score row commitment summary",
    )?;
    expect_eq(
        &input.attention_weight_table_commitment,
        &input.attention_source_input.weight_table_commitment,
        "attention weight table commitment source",
    )?;
    expect_eq(
        &input.attention_weight_table_commitment,
        &summary.source_weight_table_commitment,
        "attention weight table commitment summary",
    )?;
    expect_usize(
        input.attention_lookup_claims,
        summary.lookup_claims,
        "attention lookup claims",
    )?;
    expect_usize(
        input.attention_table_rows,
        summary.table_rows,
        "attention table rows",
    )
}

fn prove_single_proof(input: &ZkAiNativeAttentionMlpSingleProofInput) -> Result<Vec<u8>> {
    let attention_summary =
        zkai_attention_kv_native_d8_fused_softmax_table_summary(&input.attention_source_input)?;
    let attention_preprocessed =
        zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_trace(
            &input.attention_source_input,
            &attention_summary,
        )?;
    let attention_base =
        zkai_attention_kv_native_d8_fused_softmax_table_base_trace(&input.attention_source_input)?;
    let preprocessed_ids = combined_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let attention_placeholder =
        zkai_attention_kv_native_d8_fused_softmax_table_component_with_allocator(
            &mut allocator,
            AttentionKvD8FusedSoftmaxTableRelation::dummy(),
        );
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let down_projection_component =
        zkai_d128_down_projection_component_with_allocator(&mut allocator);
    let residual_add_component = zkai_d128_residual_add_component_with_allocator(&mut allocator);
    let max_constraint_log_degree_bound = attention_placeholder
        .max_constraint_log_degree_bound()
        .max(rmsnorm_component.max_constraint_log_degree_bound())
        .max(bridge_component.max_constraint_log_degree_bound())
        .max(gate_value_component.max_constraint_log_degree_bound())
        .max(activation_component.max_constraint_log_degree_bound())
        .max(down_projection_component.max_constraint_log_degree_bound())
        .max(residual_add_component.max_constraint_log_degree_bound());
    let config = single_pcs_config()?;
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

    let preprocessed_trace = combined_preprocessed_trace(input, attention_preprocessed)?;
    if preprocessed_trace.len() != preprocessed_ids.len() {
        return Err(single_error(format!(
            "combined preprocessed trace column count drift: got {}, expected {}",
            preprocessed_trace.len(),
            preprocessed_ids.len()
        )));
    }
    let base_trace = combined_base_trace(input, attention_base.clone())?;
    let sizes = combined_column_log_sizes(&preprocessed_ids);
    ensure_trace_shape("preprocessed", &preprocessed_trace, &sizes[0])?;
    ensure_trace_shape("base", &base_trace, &sizes[1])?;

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(preprocessed_trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(base_trace);
    tree_builder.commit(channel);

    mix_single_statement(channel, input, &attention_summary);
    let lookup_elements = AttentionKvD8FusedSoftmaxTableRelation::draw(channel);
    let (interaction_trace, claimed_sum) =
        zkai_attention_kv_native_d8_fused_softmax_table_interaction_trace(
            ATTENTION_LOG_SIZE,
            &attention_base,
            &preprocessed_trace
                [..zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_column_ids().len()]
                .to_vec(),
            &lookup_elements,
        );
    if claimed_sum != SecureField::from(BaseField::from(0u32)) {
        return Err(single_error(
            "attention Softmax-table LogUp expected zero claimed sum in combined proof",
        ));
    }
    ensure_trace_shape("interaction", &interaction_trace, &sizes[2])?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let attention_component =
        zkai_attention_kv_native_d8_fused_softmax_table_component_with_allocator(
            &mut allocator,
            lookup_elements,
        );
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let down_projection_component =
        zkai_d128_down_projection_component_with_allocator(&mut allocator);
    let residual_add_component = zkai_d128_residual_add_component_with_allocator(&mut allocator);
    let components: Vec<&dyn ComponentProver<SimdBackend>> = vec![
        &attention_component,
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
                single_error(format!("native attention plus MLP proving failed: {error}"))
            })?;
    serde_json::to_vec(&NativeAttentionMlpSingleProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_single_proof(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
    proof: &[u8],
) -> Result<bool> {
    if proof.is_empty() || proof.len() > ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_PROOF_BYTES {
        return Err(single_error("proof byte length outside bounded cap"));
    }
    let payload: NativeAttentionMlpSingleProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_pcs_config(stark_proof.config)?;
    let preprocessed_ids = combined_preprocessed_column_ids()?;
    let sizes = combined_column_log_sizes(&preprocessed_ids);
    if sizes.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(single_error(format!(
            "combined trace commitment tree count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(single_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = single_commitment_roots(input, config)?;
    if expected_roots.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(single_error(format!(
            "expected root count drift: got {}, expected {}",
            expected_roots.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    for index in 0..EXPECTED_TRACE_COMMITMENT_TREES {
        if stark_proof.commitments[index] != expected_roots[index] {
            return Err(single_error(format!(
                "proof commitment {index} does not match recomputed combined rows"
            )));
        }
    }

    let attention_summary =
        zkai_attention_kv_native_d8_fused_softmax_table_summary(&input.attention_source_input)?;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_single_statement(channel, input, &attention_summary);
    let lookup_elements = AttentionKvD8FusedSoftmaxTableRelation::draw(channel);
    let component_boxes = combined_component_boxes(&preprocessed_ids, lookup_elements);
    let components = component_boxes
        .iter()
        .map(|component| component.as_ref() as &dyn Component)
        .collect::<Vec<_>>();
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);
    verify(&components, channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| single_error(format!("native attention plus MLP proof rejected: {error}")))
}

fn single_commitment_roots(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let attention_summary =
        zkai_attention_kv_native_d8_fused_softmax_table_summary(&input.attention_source_input)?;
    let attention_preprocessed =
        zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_trace(
            &input.attention_source_input,
            &attention_summary,
        )?;
    let attention_base =
        zkai_attention_kv_native_d8_fused_softmax_table_base_trace(&input.attention_source_input)?;
    let preprocessed_ids = combined_preprocessed_column_ids()?;
    let sizes = combined_column_log_sizes(&preprocessed_ids);
    let max_constraint_log_degree_bound =
        combined_max_constraint_log_degree_bound(&preprocessed_ids);
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
    let preprocessed_trace = combined_preprocessed_trace(input, attention_preprocessed)?;
    if preprocessed_trace.len() != preprocessed_ids.len() {
        return Err(single_error(format!(
            "combined preprocessed trace column count drift: got {}, expected {}",
            preprocessed_trace.len(),
            preprocessed_ids.len()
        )));
    }
    let base_trace = combined_base_trace(input, attention_base.clone())?;
    ensure_trace_shape("preprocessed", &preprocessed_trace, &sizes[0])?;
    ensure_trace_shape("base", &base_trace, &sizes[1])?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(preprocessed_trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(base_trace);
    tree_builder.commit(channel);

    mix_single_statement(channel, input, &attention_summary);
    let lookup_elements = AttentionKvD8FusedSoftmaxTableRelation::draw(channel);
    let attention_preprocessed_len =
        zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_column_ids().len();
    let attention_preprocessed_trace = preprocessed_trace[..attention_preprocessed_len].to_vec();
    let (interaction_trace, claimed_sum) =
        zkai_attention_kv_native_d8_fused_softmax_table_interaction_trace(
            ATTENTION_LOG_SIZE,
            &attention_base,
            &attention_preprocessed_trace,
            &lookup_elements,
        );
    if claimed_sum != SecureField::from(BaseField::from(0u32)) {
        return Err(single_error(
            "attention Softmax-table LogUp expected zero claimed sum in combined proof",
        ));
    }
    ensure_trace_shape("interaction", &interaction_trace, &sizes[2])?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);
    if commitment_scheme.roots().len() != sizes.len() {
        return Err(single_error(
            "commitment root count does not match component sizes",
        ));
    }
    Ok(commitment_scheme.roots())
}

fn ensure_trace_shape(
    label: &str,
    trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    log_sizes: &ColumnVec<u32>,
) -> Result<()> {
    if trace.len() != log_sizes.len() {
        return Err(single_error(format!(
            "{label} trace column count mismatch: got {}, expected {}",
            trace.len(),
            log_sizes.len()
        )));
    }
    for (index, (column, expected_log_size)) in trace.iter().zip(log_sizes).enumerate() {
        let actual_log_size = column.domain.log_size();
        if actual_log_size != *expected_log_size {
            return Err(single_error(format!(
                "{label} trace column {index} log-size mismatch: got {actual_log_size}, expected {expected_log_size}"
            )));
        }
    }
    Ok(())
}

fn combined_preprocessed_trace(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
    mut attention_preprocessed: ColumnVec<
        CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>,
    >,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    attention_preprocessed.extend(mlp_trace(input)?);
    Ok(attention_preprocessed)
}

fn combined_base_trace(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
    mut attention_base: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    attention_base.extend(mlp_trace(input)?);
    Ok(attention_base)
}

fn mlp_trace(
    input: &ZkAiNativeAttentionMlpSingleProofInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let gate_rows = zkai_d128_gate_value_projection_rows(&input.mlp_input.gate_value_input)?;
    let mut trace = zkai_d128_rmsnorm_public_row_trace(&input.mlp_input.rmsnorm_input);
    trace.extend(zkai_d128_rmsnorm_to_projection_bridge_trace(
        &input.mlp_input.projection_bridge_input,
    ));
    trace.extend(zkai_d128_gate_value_projection_trace(&gate_rows)?);
    trace.extend(zkai_d128_activation_swiglu_trace(
        &input.mlp_input.activation_input,
    )?);
    trace.extend(zkai_d128_down_projection_trace(
        &input.mlp_input.down_projection_input,
    )?);
    trace.extend(zkai_d128_residual_add_trace(
        &input.mlp_input.residual_add_input,
    ));
    Ok(trace)
}

fn combined_preprocessed_column_ids() -> Result<Vec<PreProcessedColumnId>> {
    let mut ids = zkai_attention_kv_native_d8_fused_softmax_table_preprocessed_column_ids();
    ids.extend(zkai_d128_rmsnorm_public_row_preprocessed_column_ids());
    ids.extend(zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids());
    ids.extend(zkai_d128_gate_value_projection_preprocessed_column_ids());
    ids.extend(zkai_d128_activation_swiglu_preprocessed_column_ids());
    ids.extend(zkai_d128_down_projection_preprocessed_column_ids());
    ids.extend(zkai_d128_residual_add_preprocessed_column_ids());
    let mut seen = BTreeSet::new();
    for id in &ids {
        if !seen.insert(id.id.clone()) {
            return Err(single_error(format!(
                "duplicate combined preprocessed column id: {}",
                id.id
            )));
        }
    }
    Ok(ids)
}

fn combined_max_constraint_log_degree_bound(preprocessed_ids: &[PreProcessedColumnId]) -> u32 {
    combined_component_boxes(
        preprocessed_ids,
        AttentionKvD8FusedSoftmaxTableRelation::dummy(),
    )
    .iter()
    .map(|component| component.max_constraint_log_degree_bound())
    .max()
    .unwrap_or(0)
}

fn combined_column_log_sizes(
    preprocessed_ids: &[PreProcessedColumnId],
) -> stwo::core::pcs::TreeVec<ColumnVec<u32>> {
    let component_boxes = combined_component_boxes(
        preprocessed_ids,
        AttentionKvD8FusedSoftmaxTableRelation::dummy(),
    );
    let components = component_boxes
        .iter()
        .map(|component| component.as_ref() as &dyn Component)
        .collect::<Vec<_>>();
    Components {
        components,
        n_preprocessed_columns: preprocessed_ids.len(),
    }
    .column_log_sizes()
}

fn combined_component_boxes(
    preprocessed_ids: &[PreProcessedColumnId],
    lookup_elements: AttentionKvD8FusedSoftmaxTableRelation,
) -> Vec<Box<dyn Component>> {
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(preprocessed_ids);
    let attention_component = Box::new(
        zkai_attention_kv_native_d8_fused_softmax_table_component_with_allocator(
            &mut allocator,
            lookup_elements,
        ),
    );
    let rmsnorm_component = Box::new(zkai_d128_rmsnorm_public_row_component_with_allocator(
        &mut allocator,
    ));
    let bridge_component =
        Box::new(zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator));
    let gate_value_component = Box::new(zkai_d128_gate_value_projection_component_with_allocator(
        &mut allocator,
    ));
    let activation_component = Box::new(zkai_d128_activation_swiglu_component_with_allocator(
        &mut allocator,
    ));
    let down_projection_component = Box::new(zkai_d128_down_projection_component_with_allocator(
        &mut allocator,
    ));
    let residual_add_component = Box::new(zkai_d128_residual_add_component_with_allocator(
        &mut allocator,
    ));
    vec![
        attention_component as Box<dyn Component>,
        rmsnorm_component as Box<dyn Component>,
        bridge_component as Box<dyn Component>,
        gate_value_component as Box<dyn Component>,
        activation_component as Box<dyn Component>,
        down_projection_component as Box<dyn Component>,
        residual_add_component as Box<dyn Component>,
    ]
}

fn validate_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    let expected = single_pcs_config()?;
    if actual.pow_bits != expected.pow_bits
        || actual.fri_config.log_blowup_factor != expected.fri_config.log_blowup_factor
        || actual.fri_config.n_queries != expected.fri_config.n_queries
        || actual.fri_config.log_last_layer_degree_bound
            != expected.fri_config.log_last_layer_degree_bound
        || actual.fri_config.fold_step != expected.fri_config.fold_step
        || actual.lifting_log_size != expected.lifting_log_size
    {
        return Err(single_error(
            "PCS config does not match publication-v1 profile with route-specific explicit lifting log size",
        ));
    }
    Ok(expected)
}

fn single_pcs_config() -> Result<PcsConfig> {
    let preprocessed_ids = combined_preprocessed_column_ids()?;
    let max_constraint_log_degree_bound =
        combined_max_constraint_log_degree_bound(&preprocessed_ids);
    let mut config = publication_v1_pcs_config();
    config.lifting_log_size =
        Some(max_constraint_log_degree_bound + config.fri_config.log_blowup_factor);
    if publication_v1_pcs_config_matches(&config) {
        return Err(single_error(
            "single proof PCS config unexpectedly matches publication-v1 default",
        ));
    }
    Ok(config)
}

fn mix_single_statement(
    channel: &mut Blake2sM31Channel,
    input: &ZkAiNativeAttentionMlpSingleProofInput,
    attention_summary: &ZkAiAttentionKvNativeD8FusedSoftmaxTableSummary,
) {
    channel.mix_u64(input.attention_lookup_claims as u64);
    channel.mix_u64(input.attention_table_rows as u64);
    channel.mix_u64(input.mlp_row_count as u64);
    channel.mix_u64(input.current_two_proof_frontier_typed_bytes as u64);
    channel.mix_u64(input.current_attention_fused_typed_bytes as u64);
    channel.mix_u64(input.current_derived_mlp_fused_typed_bytes as u64);
    channel.mix_u64(input.nanozk_reported_d128_block_proof_bytes as u64);
    channel.mix_u64(input.pcs_lifting_log_size as u64);
    mix_commitment(channel, &input.statement_commitment);
    mix_commitment(channel, &input.attention_statement_commitment);
    mix_commitment(channel, &input.attention_outputs_commitment);
    mix_commitment(channel, &input.mlp_statement_commitment);
    mix_commitment(channel, &input.mlp_input_activation_commitment);
    for entry in &attention_summary.table_multiplicities {
        channel.mix_u64(entry.gap as u64);
        channel.mix_u64(entry.weight.rem_euclid((1i64 << 31) - 1) as u64);
        channel.mix_u64(entry.multiplicity as u64);
    }
}

fn mix_commitment(channel: &mut Blake2sM31Channel, commitment: &str) {
    for chunk in commitment.as_bytes().chunks(8) {
        let mut bytes = [0u8; 8];
        bytes[..chunk.len()].copy_from_slice(chunk);
        channel.mix_u64(u64::from_le_bytes(bytes));
    }
}

fn statement_commitment(input: &ZkAiNativeAttentionMlpSingleProofInput) -> Result<String> {
    let payload = serde_json::json!({
        "adapter_status": input.adapter_status,
        "attention_lookup_claims": input.attention_lookup_claims,
        "attention_outputs_commitment": input.attention_outputs_commitment,
        "attention_proof_version": input.attention_proof_version,
        "attention_public_instance_commitment": input.attention_public_instance_commitment,
        "attention_score_row_commitment": input.attention_score_row_commitment,
        "attention_statement_commitment": input.attention_statement_commitment,
        "attention_table_rows": input.attention_table_rows,
        "attention_weight_table_commitment": input.attention_weight_table_commitment,
        "current_attention_fused_typed_bytes": input.current_attention_fused_typed_bytes,
        "current_derived_mlp_fused_typed_bytes": input.current_derived_mlp_fused_typed_bytes,
        "current_two_proof_frontier_typed_bytes": input.current_two_proof_frontier_typed_bytes,
        "mlp_input_activation_commitment": input.mlp_input_activation_commitment,
        "mlp_output_activation_commitment": input.mlp_output_activation_commitment,
        "mlp_proof_version": input.mlp_proof_version,
        "mlp_public_instance_commitment": input.mlp_public_instance_commitment,
        "mlp_row_count": input.mlp_row_count,
        "mlp_statement_commitment": input.mlp_statement_commitment,
        "nanozk_reported_d128_block_proof_bytes": input.nanozk_reported_d128_block_proof_bytes,
        "operation": "native_attention_mlp_single_proof_object_probe",
        "pcs_lifting_log_size": input.pcs_lifting_log_size,
        "route_id": input.route_id,
        "target_id": input.target_id,
        "verifier_domain": input.verifier_domain,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, STATEMENT_DOMAIN))
}

fn public_instance_commitment(statement: &str) -> Result<String> {
    let payload = serde_json::json!({
        "operation": "native_attention_mlp_single_proof_object_probe",
        "route_id": ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_ROUTE_ID,
        "statement_commitment": statement,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, PUBLIC_INSTANCE_DOMAIN))
}

fn proof_native_parameter_commitment(statement: &str) -> Result<String> {
    let pcs_lifting_log_size = single_pcs_config()?.lifting_log_size.ok_or_else(|| {
        single_error("single proof PCS config must pin an explicit lifting log size")
    })?;
    let payload = serde_json::json!({
        "kind": "native-attention-mlp-single-proof-native-parameter-v1",
        "pcs_lifting_log_size": pcs_lifting_log_size,
        "pcs_profile": "publication_v1_with_explicit_lifting_log_size",
        "statement_commitment": statement,
        "trace_commitment_trees": EXPECTED_TRACE_COMMITMENT_TREES,
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
        return Err(single_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(single_error(format!(
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
        return Err(single_error(format!("{label} drift")));
    }
    Ok(())
}

fn single_error(message: impl Into<String>) -> VmError {
    VmError::UnsupportedProof(format!(
        "native attention plus MLP single proof object: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::stwo_backend::{
        zkai_attention_kv_native_d8_fused_softmax_table_source_input_from_json_str,
        zkai_d128_rmsnorm_mlp_fused_input_from_json_str,
    };

    fn fixture_input() -> ZkAiNativeAttentionMlpSingleProofInput {
        let attention = zkai_attention_kv_native_d8_fused_softmax_table_source_input_from_json_str(
            include_str!(
                "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json"
            ),
        )
        .expect("attention source");
        let mlp = zkai_d128_rmsnorm_mlp_fused_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json"
        ))
        .expect("MLP input");
        build_zkai_native_attention_mlp_single_proof_input(attention, mlp).expect("single input")
    }

    #[test]
    fn single_proof_input_validates_statement_bound_route() {
        let input = fixture_input();
        assert_eq!(
            input.attention_outputs_commitment,
            SOURCE_ATTENTION_OUTPUTS_COMMITMENT
        );
        assert_eq!(
            input.mlp_input_activation_commitment,
            ZKAI_D128_ATTENTION_DERIVED_INPUT_ACTIVATION_COMMITMENT
        );
        assert_eq!(
            input.current_two_proof_frontier_typed_bytes,
            CURRENT_TWO_PROOF_FRONTIER_TYPED_BYTES
        );
        validate_single_input(&input).expect("input validates");
    }

    #[test]
    fn single_proof_input_rejects_attention_output_commitment_drift() {
        let mut input = fixture_input();
        input.attention_outputs_commitment =
            "blake2b-256:1111111111111111111111111111111111111111111111111111111111111111"
                .to_string();
        input.statement_commitment = statement_commitment(&input).expect("statement");
        input.public_instance_commitment =
            public_instance_commitment(&input.statement_commitment).expect("public instance");
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment).expect("params");
        assert!(validate_single_input(&input).is_err());
    }

    #[test]
    fn single_proof_input_rejects_mlp_input_activation_drift() {
        let mut input = fixture_input();
        input.mlp_input_activation_commitment =
            "blake2b-256:2222222222222222222222222222222222222222222222222222222222222222"
                .to_string();
        input.statement_commitment = statement_commitment(&input).expect("statement");
        input.public_instance_commitment =
            public_instance_commitment(&input.statement_commitment).expect("public instance");
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment).expect("params");
        assert!(validate_single_input(&input).is_err());
    }

    #[test]
    fn combined_preprocessed_columns_are_unique() {
        let ids = combined_preprocessed_column_ids().expect("ids");
        let unique = ids.iter().map(|id| id.id.clone()).collect::<BTreeSet<_>>();
        assert_eq!(ids.len(), unique.len());
    }
}
