use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::path::Path;

use super::decoding::{read_json_bytes_with_limit, write_json_with_limit};
use super::lookup_prover::verify_phase10_shared_binary_step_lookup_envelope;
use super::normalization_prover::{
    prepare_phase92_shared_normalization_demo_artifact,
    verify_phase10_shared_normalization_lookup_envelope,
    verify_phase92_shared_normalization_primitive_artifact,
    Phase92SharedNormalizationPrimitiveArtifact, Phase92SharedNormalizationPrimitiveStep,
};
use super::shared_lookup_artifact::{
    EmbeddedSharedActivationLookupProof, EmbeddedSharedNormalizationProof,
};
use crate::assembly::parse_program;
use crate::error::{Result, VmError};
use crate::proof::{
    verify_execution_stark_with_reexecution, StarkProofBackend, VanillaStarkExecutionProof,
};

pub const STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_VERSION_PHASE93: &str =
    "stwo-phase93-tensor-native-chain-artifact-v1";
pub const STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_SCOPE_PHASE93: &str =
    "stwo_tensor_native_transformer_shaped_chain_artifact";
pub const STWO_TENSOR_NATIVE_CARRIED_STATE_VERSION_PHASE93: &str =
    "stwo-phase93-typed-carried-state-v1";
pub const STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_VERSION_PHASE945: &str =
    "stwo-phase94-5-gemma-block-core-slice-artifact-v1";
pub const STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_SCOPE_PHASE945: &str =
    "stwo_tensor_native_gemma_block_core_slice_artifact";
pub const STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_VERSION_PHASE9475: &str =
    "stwo-phase94-75-gemma-block-richer-slice-artifact-v1";
pub const STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_SCOPE_PHASE9475: &str =
    "stwo_tensor_native_gemma_block_richer_slice_artifact";
pub const STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE95: &str =
    "stwo-phase95-repeated-gemma-slice-accumulation-artifact-v1";
pub const STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE95: &str =
    "stwo_tensor_native_repeated_gemma_slice_accumulation_artifact";
pub const STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE965: &str =
    "stwo-phase96-5-folded-gemma-slice-accumulation-artifact-v1";
pub const STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE965: &str =
    "stwo_tensor_native_folded_gemma_slice_accumulation_artifact";
pub const STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_VERSION_PHASE98: &str =
    "stwo-phase98-folded-gemma-richer-slice-family-artifact-v1";
pub const STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_SCOPE_PHASE98: &str =
    "stwo_tensor_native_folded_gemma_richer_slice_family_artifact";
pub const STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_VERSION_PHASE99: &str =
    "stwo-phase99-multi-interval-gemma-richer-family-accumulation-artifact-v1";
pub const STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_SCOPE_PHASE99: &str =
    "stwo_tensor_native_multi_interval_gemma_richer_family_accumulation_artifact";
pub const STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_VERSION_PHASE1015: &str =
    "stwo-phase101-5-folded-multi-interval-gemma-accumulation-prototype-artifact-v1";
pub const STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_SCOPE_PHASE1015: &str =
    "stwo_tensor_native_folded_multi_interval_gemma_accumulation_prototype_artifact";
pub const STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE102: &str =
    "stwo-phase102-folded-multi-interval-gemma-richer-family-artifact-v1";
pub const STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE102: &str =
    "stwo_tensor_native_folded_multi_interval_gemma_richer_family_artifact";
pub const STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE105: &str =
    "stwo-phase105-repeated-multi-interval-gemma-richer-family-artifact-v1";
pub const STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE105: &str =
    "stwo_tensor_native_repeated_multi_interval_gemma_richer_family_artifact";
pub const MAX_PHASE95_REPEATED_GEMMA_TOTAL_SLICES: usize = 16;
pub const MAX_PHASE99_MULTI_INTERVAL_TOTAL_INTERVALS: usize = 8;
pub const MAX_PHASE105_REPEATED_MULTI_INTERVAL_TOTAL_WINDOWS: usize = 8;
pub const PHASE965_DEFAULT_BOUNDED_FOLD_ARITY: usize = 2;
pub const PHASE1015_DEFAULT_BOUNDED_FOLD_ARITY: usize = 2;

const MAX_PHASE93_TENSOR_NATIVE_CHAIN_JSON_BYTES: usize = 8 * 1024 * 1024;
const MAX_PHASE945_GEMMA_BLOCK_CORE_SLICE_JSON_BYTES: usize = 32 * 1024 * 1024;
const MAX_PHASE9475_GEMMA_BLOCK_RICHER_SLICE_JSON_BYTES: usize = 32 * 1024 * 1024;
const MAX_PHASE95_REPEATED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES: usize = 64 * 1024 * 1024;
const MAX_PHASE965_FOLDED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES: usize = 16 * 1024 * 1024;
const MAX_PHASE98_FOLDED_GEMMA_RICHER_SLICE_FAMILY_JSON_BYTES: usize = 16 * 1024 * 1024;
const MAX_PHASE99_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_JSON_BYTES: usize =
    128 * 1024 * 1024;
const MAX_PHASE1015_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_JSON_BYTES: usize =
    16 * 1024 * 1024;
const MAX_PHASE102_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_JSON_BYTES: usize = 16 * 1024 * 1024;
const MAX_PHASE105_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_JSON_BYTES: usize = 64 * 1024 * 1024;
const PHASE93_DEFAULT_BLOCK_INDEX: u64 = 0;
const PHASE93_DEFAULT_TOKEN_POSITION: u64 = 0;
const PHASE93_DEFAULT_CHAIN_TEMPLATE_SEQUENCE: [usize; 4] = [0, 1, 0, 1];
const PHASE93_DEFAULT_CHAIN_LABELS: [&str; 4] = [
    "attention.pre_norm",
    "attention.post_norm",
    "mlp.pre_norm",
    "mlp.post_norm",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase93TypedCarriedStateBoundary {
    pub boundary_version: String,
    pub token_position: u64,
    pub block_index: u64,
    pub substep_index: u64,
    pub hidden_state_commitment: String,
    pub kv_cache_commitment: String,
    pub shared_table_registry_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase93TensorNativeChainStep {
    pub step_index: usize,
    pub step_label: String,
    pub primitive_template_step_index: usize,
    pub primitive_template_step_label: String,
    pub primitive_template_claims_commitment: String,
    pub carried_state_in: Phase93TypedCarriedStateBoundary,
    pub carried_state_in_commitment: String,
    pub carried_state_out: Phase93TypedCarriedStateBoundary,
    pub carried_state_out_commitment: String,
    pub carried_state_link_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase93TensorNativeChainArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub carried_state_type_version: String,
    pub shared_table_registry_commitment: String,
    pub primitive_artifact_commitment: String,
    pub steps_commitment: String,
    pub initial_boundary_commitment: String,
    pub terminal_boundary_commitment: String,
    pub total_steps: usize,
    pub primitive_artifact: Phase92SharedNormalizationPrimitiveArtifact,
    pub steps: Vec<Phase93TensorNativeChainStep>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase945GemmaNormalizationRowSummary {
    pub row_index: usize,
    pub norm_sq_memory_index: u8,
    pub inv_sqrt_q8_memory_index: u8,
    pub norm_sq: u16,
    pub inv_sqrt_q8: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase945GemmaActivationRowSummary {
    pub row_index: usize,
    pub input_memory_index: u8,
    pub output_memory_index: u8,
    pub input: i16,
    pub output: i16,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase945GemmaBlockCoreSliceArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub chain_artifact_commitment: String,
    pub execution_proof_commitment: String,
    pub normalization_row_set_commitment: String,
    pub activation_row_set_commitment: String,
    pub execution_proof_backend: StarkProofBackend,
    pub execution_proof_backend_version: String,
    pub execution_statement_version: String,
    pub shared_normalization_statement_version: String,
    pub shared_normalization_scope: String,
    pub shared_activation_statement_version: String,
    pub shared_activation_scope: String,
    pub final_acc: i64,
    pub total_shared_normalization_rows: usize,
    pub total_shared_activation_rows: usize,
    pub chain_artifact: Phase93TensorNativeChainArtifact,
    pub shared_normalization_rows: Vec<Phase945GemmaNormalizationRowSummary>,
    pub shared_activation_rows: Vec<Phase945GemmaActivationRowSummary>,
    pub execution_proof: VanillaStarkExecutionProof,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase9475GemmaMemoryWindowEntry {
    pub memory_index: u8,
    pub value: i16,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase9475GemmaBlockRicherSliceArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub core_slice_artifact_commitment: String,
    pub chain_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub selected_memory_window_commitment: String,
    pub local_score: i16,
    pub global_score: i16,
    pub grouped_value_mix: i16,
    pub residual_output: i16,
    pub primary_norm_sq: i16,
    pub primary_inv_sqrt_q8: i16,
    pub primary_activation_input: i16,
    pub primary_activation_output: i16,
    pub secondary_norm_sq: i16,
    pub secondary_inv_sqrt_q8: i16,
    pub secondary_activation_input: i16,
    pub secondary_activation_output: i16,
    pub selected_memory_window: Vec<Phase9475GemmaMemoryWindowEntry>,
    pub core_slice_artifact: Phase945GemmaBlockCoreSliceArtifact,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase95RepeatedGemmaSliceMember {
    pub slice_index: usize,
    pub token_position: u64,
    pub block_index: u64,
    pub richer_slice_artifact_commitment: String,
    pub chain_artifact_commitment: String,
    pub initial_boundary_commitment: String,
    pub terminal_boundary_commitment: String,
    pub selected_memory_window_commitment: String,
    pub local_score: i16,
    pub global_score: i16,
    pub grouped_value_mix: i16,
    pub residual_output: i16,
    pub final_acc: i64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase95RepeatedGemmaSliceAccumulationArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub shared_primitive_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub shared_execution_proof_commitment: String,
    pub shared_execution_proof_backend_version: String,
    pub shared_execution_statement_version: String,
    pub total_slices: usize,
    pub repeated_token_position: u64,
    pub start_block_index: u64,
    pub terminal_block_index: u64,
    pub members_commitment: String,
    pub shared_primitive_artifact: Phase92SharedNormalizationPrimitiveArtifact,
    pub shared_execution_proof: VanillaStarkExecutionProof,
    pub members: Vec<Phase95RepeatedGemmaSliceMember>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase965FoldedGemmaSliceGroup {
    pub folded_group_index: usize,
    pub start_slice_index: usize,
    pub terminal_slice_index: usize,
    pub start_block_index: u64,
    pub terminal_block_index: u64,
    pub first_richer_slice_artifact_commitment: String,
    pub terminal_richer_slice_artifact_commitment: String,
    pub initial_boundary_commitment: String,
    pub terminal_boundary_commitment: String,
    pub member_richer_slice_commitment_sequence_commitment: String,
    pub member_selected_memory_window_commitment_sequence_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub folded_group_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase965FoldedGemmaSliceAccumulationArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub source_phase95_artifact_commitment: String,
    pub source_members_commitment: String,
    pub shared_primitive_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub shared_execution_proof_commitment: String,
    pub shared_execution_proof_backend_version: String,
    pub shared_execution_statement_version: String,
    pub total_slices: usize,
    pub repeated_token_position: u64,
    pub start_block_index: u64,
    pub terminal_block_index: u64,
    pub bounded_fold_arity: usize,
    pub total_folded_groups: usize,
    pub global_start_boundary_commitment: String,
    pub global_end_boundary_commitment: String,
    pub first_richer_slice_artifact_commitment: String,
    pub terminal_richer_slice_artifact_commitment: String,
    pub fold_template_commitment: String,
    pub folded_group_sequence_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub folded_slice_accumulator_commitment: String,
    pub folded_groups: Vec<Phase965FoldedGemmaSliceGroup>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase98FoldedGemmaRicherSliceFamilyArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub source_phase95_artifact_commitment: String,
    pub source_phase965_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub total_slices: usize,
    pub repeated_token_position: u64,
    pub start_block_index: u64,
    pub terminal_block_index: u64,
    pub total_folded_groups: usize,
    pub bounded_fold_arity: usize,
    pub global_start_boundary_commitment: String,
    pub global_end_boundary_commitment: String,
    pub first_richer_slice_artifact_commitment: String,
    pub terminal_richer_slice_artifact_commitment: String,
    pub richer_family_template_commitment: String,
    pub richer_slice_commitment_sequence_commitment: String,
    pub selected_memory_window_family_commitment: String,
    pub invariant_summary_family_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub folded_richer_family_accumulator_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase99MultiIntervalGemmaRicherFamilyMember {
    pub interval_index: usize,
    pub repeated_token_position: u64,
    pub start_block_index: u64,
    pub terminal_block_index: u64,
    pub phase95_artifact_commitment: String,
    pub phase965_artifact_commitment: String,
    pub phase98_artifact_commitment: String,
    pub global_start_boundary_commitment: String,
    pub global_end_boundary_commitment: String,
    pub first_richer_slice_artifact_commitment: String,
    pub terminal_richer_slice_artifact_commitment: String,
    pub richer_slice_commitment_sequence_commitment: String,
    pub selected_memory_window_family_commitment: String,
    pub invariant_summary_family_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub interval_member_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub shared_primitive_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub shared_execution_proof_commitment: String,
    pub shared_execution_proof_backend_version: String,
    pub shared_execution_statement_version: String,
    pub total_intervals: usize,
    pub interval_total_slices: usize,
    pub token_position_start: u64,
    pub token_position_stride: u64,
    pub start_block_index: u64,
    pub terminal_token_position: u64,
    pub terminal_block_index: u64,
    pub interval_members_commitment: String,
    pub global_interval_start_boundary_commitment: String,
    pub global_interval_end_boundary_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub shared_primitive_artifact: Phase92SharedNormalizationPrimitiveArtifact,
    pub shared_execution_proof: VanillaStarkExecutionProof,
    pub members: Vec<Phase99MultiIntervalGemmaRicherFamilyMember>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup {
    pub folded_group_index: usize,
    pub start_interval_index: usize,
    pub terminal_interval_index: usize,
    pub start_token_position: u64,
    pub terminal_token_position: u64,
    pub first_phase98_artifact_commitment: String,
    pub terminal_phase98_artifact_commitment: String,
    pub global_start_boundary_commitment: String,
    pub global_end_boundary_commitment: String,
    pub interval_member_commitment_sequence_commitment: String,
    pub interval_phase98_commitment_sequence_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub folded_group_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub source_phase99_artifact_commitment: String,
    pub source_interval_members_commitment: String,
    pub shared_primitive_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub shared_execution_proof_commitment: String,
    pub shared_execution_proof_backend_version: String,
    pub shared_execution_statement_version: String,
    pub total_intervals: usize,
    pub interval_total_slices: usize,
    pub token_position_start: u64,
    pub token_position_stride: u64,
    pub start_block_index: u64,
    pub terminal_token_position: u64,
    pub terminal_block_index: u64,
    pub bounded_fold_arity: usize,
    pub total_folded_interval_groups: usize,
    pub global_interval_start_boundary_commitment: String,
    pub global_interval_end_boundary_commitment: String,
    pub first_phase98_artifact_commitment: String,
    pub terminal_phase98_artifact_commitment: String,
    pub fold_template_commitment: String,
    pub folded_interval_group_sequence_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub accumulation_handoff_commitment: String,
    pub folded_interval_prototype_accumulator_commitment: String,
    pub folded_groups: Vec<Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase102FoldedMultiIntervalGemmaRicherFamilyGroup {
    pub folded_group_index: usize,
    pub start_interval_index: usize,
    pub terminal_interval_index: usize,
    pub start_token_position: u64,
    pub terminal_token_position: u64,
    pub first_phase98_artifact_commitment: String,
    pub terminal_phase98_artifact_commitment: String,
    pub global_start_boundary_commitment: String,
    pub global_end_boundary_commitment: String,
    pub interval_member_commitment_sequence_commitment: String,
    pub interval_phase98_commitment_sequence_commitment: String,
    pub interval_token_position_sequence_commitment: String,
    pub richer_slice_family_commitment_sequence_commitment: String,
    pub selected_memory_window_family_commitment_sequence_commitment: String,
    pub invariant_summary_family_commitment_sequence_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub folded_richer_group_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub source_phase99_artifact_commitment: String,
    pub source_phase1015_artifact_commitment: String,
    pub source_interval_members_commitment: String,
    pub shared_primitive_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub shared_execution_proof_commitment: String,
    pub shared_execution_proof_backend_version: String,
    pub shared_execution_statement_version: String,
    pub total_intervals: usize,
    pub interval_total_slices: usize,
    pub token_position_start: u64,
    pub token_position_stride: u64,
    pub start_block_index: u64,
    pub terminal_token_position: u64,
    pub terminal_block_index: u64,
    pub bounded_fold_arity: usize,
    pub total_folded_richer_groups: usize,
    pub global_interval_start_boundary_commitment: String,
    pub global_interval_end_boundary_commitment: String,
    pub first_phase98_artifact_commitment: String,
    pub terminal_phase98_artifact_commitment: String,
    pub richer_fold_template_commitment: String,
    pub folded_richer_group_sequence_commitment: String,
    pub phase98_commitment_sequence_commitment: String,
    pub token_position_sequence_commitment: String,
    pub richer_slice_family_commitment_sequence_commitment: String,
    pub selected_memory_window_family_commitment_sequence_commitment: String,
    pub invariant_summary_family_commitment_sequence_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub accumulation_handoff_commitment: String,
    pub folded_interval_prototype_accumulator_commitment: String,
    pub folded_richer_multi_interval_family_accumulator_commitment: String,
    pub folded_groups: Vec<Phase102FoldedMultiIntervalGemmaRicherFamilyGroup>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase105RepeatedMultiIntervalGemmaRicherFamilyMember {
    pub window_index: usize,
    pub total_intervals: usize,
    pub bounded_fold_arity: usize,
    pub total_folded_richer_groups: usize,
    pub token_position_start: u64,
    pub token_position_stride: u64,
    pub terminal_token_position: u64,
    pub start_block_index: u64,
    pub terminal_block_index: u64,
    pub source_phase99_artifact_commitment: String,
    pub source_phase1015_artifact_commitment: String,
    pub source_phase102_artifact_commitment: String,
    pub global_interval_start_boundary_commitment: String,
    pub global_interval_end_boundary_commitment: String,
    pub accumulation_handoff_commitment: String,
    pub folded_interval_prototype_accumulator_commitment: String,
    pub phase98_commitment_sequence_commitment: String,
    pub token_position_sequence_commitment: String,
    pub selected_memory_window_family_commitment_sequence_commitment: String,
    pub invariant_summary_family_commitment_sequence_commitment: String,
    pub folded_richer_multi_interval_family_accumulator_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub window_member_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub program_label: String,
    pub shared_primitive_artifact_commitment: String,
    pub shared_table_registry_commitment: String,
    pub shared_execution_proof_commitment: String,
    pub shared_execution_proof_backend_version: String,
    pub shared_execution_statement_version: String,
    pub total_windows: usize,
    pub intervals_per_window: usize,
    pub interval_total_slices: usize,
    pub token_position_start: u64,
    pub token_position_stride: u64,
    pub window_token_position_stride: u64,
    pub start_block_index: u64,
    pub terminal_token_position: u64,
    pub terminal_block_index: u64,
    pub window_members_commitment: String,
    pub phase102_artifact_commitment_sequence_commitment: String,
    pub accumulation_handoff_commitment_sequence_commitment: String,
    pub folded_richer_multi_interval_family_accumulator_sequence_commitment: String,
    pub global_window_start_boundary_commitment: String,
    pub global_window_end_boundary_commitment: String,
    pub local_score_sum: i64,
    pub global_score_sum: i64,
    pub grouped_value_mix_sum: i64,
    pub residual_output_sum: i64,
    pub final_acc_sum: i64,
    pub primary_norm_sq_min: i16,
    pub primary_norm_sq_max: i16,
    pub secondary_norm_sq_min: i16,
    pub secondary_norm_sq_max: i16,
    pub primary_activation_output_sum: i64,
    pub secondary_activation_output_sum: i64,
    pub repeated_multi_interval_family_accumulator_commitment: String,
    pub shared_primitive_artifact: Phase92SharedNormalizationPrimitiveArtifact,
    pub shared_execution_proof: VanillaStarkExecutionProof,
    pub members: Vec<Phase105RepeatedMultiIntervalGemmaRicherFamilyMember>,
}

#[derive(Debug, Deserialize)]
struct Phase945ArithmeticSubsetProofPayload {
    #[serde(default)]
    embedded_shared_normalization: Option<EmbeddedSharedNormalizationProof>,
    #[serde(default)]
    embedded_shared_activation_lookup: Option<EmbeddedSharedActivationLookupProof>,
}

pub fn prepare_phase93_tensor_native_chain_artifact(
    primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
) -> Result<Phase93TensorNativeChainArtifact> {
    prepare_phase93_tensor_native_chain_artifact_at(
        primitive_artifact,
        PHASE93_DEFAULT_TOKEN_POSITION,
        PHASE93_DEFAULT_BLOCK_INDEX,
    )
}

pub fn prepare_phase93_tensor_native_chain_artifact_at(
    primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    token_position: u64,
    block_index: u64,
) -> Result<Phase93TensorNativeChainArtifact> {
    verify_phase92_shared_normalization_primitive_artifact(primitive_artifact)?;
    let steps =
        phase93_default_tensor_native_chain_steps(primitive_artifact, token_position, block_index)?;
    build_phase93_tensor_native_chain_artifact(primitive_artifact.clone(), steps)
}

pub fn prepare_phase93_tensor_native_chain_demo_artifact(
) -> Result<Phase93TensorNativeChainArtifact> {
    let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()?;
    prepare_phase93_tensor_native_chain_artifact(&primitive_artifact)
}

pub fn verify_phase93_tensor_native_chain_artifact(
    artifact: &Phase93TensorNativeChainArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_VERSION_PHASE93 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 93 tensor-native chain artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_SCOPE_PHASE93 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 93 tensor-native chain artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.carried_state_type_version != STWO_TENSOR_NATIVE_CARRIED_STATE_VERSION_PHASE93 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 93 carried-state type version `{}`",
            artifact.carried_state_type_version
        )));
    }

    verify_phase92_shared_normalization_primitive_artifact(&artifact.primitive_artifact)?;
    if artifact.primitive_artifact_commitment != artifact.primitive_artifact.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain primitive_artifact_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment
        != artifact.primitive_artifact.static_table_registry_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain shared_table_registry_commitment does not match the nested primitive artifact registry"
                .to_string(),
        ));
    }

    let canonical_steps = canonicalize_phase93_chain_steps(
        &artifact.steps,
        &artifact.primitive_artifact,
        &artifact.shared_table_registry_commitment,
    )?;
    if canonical_steps != artifact.steps {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain steps are not in canonical step_index order".to_string(),
        ));
    }
    if artifact.total_steps != artifact.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 93 tensor-native chain total_steps {} does not match the step count {}",
            artifact.total_steps,
            artifact.steps.len()
        )));
    }

    for step in &artifact.steps {
        let expected_in = commit_phase93_boundary(&step.carried_state_in)?;
        if step.carried_state_in_commitment != expected_in {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} carried_state_in commitment does not match its serialized boundary",
                step.step_index
            )));
        }
        let expected_out = commit_phase93_boundary(&step.carried_state_out)?;
        if step.carried_state_out_commitment != expected_out {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} carried_state_out commitment does not match its serialized boundary",
                step.step_index
            )));
        }
        let expected_link = commit_phase93_chain_step(step)?;
        if step.carried_state_link_commitment != expected_link {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} carried_state_link_commitment does not match its serialized contents",
                step.step_index
            )));
        }
    }

    for pair in artifact.steps.windows(2) {
        let left = &pair[0];
        let right = &pair[1];
        if left.carried_state_out != right.carried_state_in {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain continuity mismatch between steps {} and {}",
                left.step_index, right.step_index
            )));
        }
    }

    let expected_steps_commitment = commit_phase93_chain_steps(&artifact.steps)?;
    if artifact.steps_commitment != expected_steps_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain steps_commitment does not match the serialized chain steps"
                .to_string(),
        ));
    }
    let first_step = artifact.steps.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 93 tensor-native chain requires at least one chain step".to_string(),
        )
    })?;
    let last_step = artifact.steps.last().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 93 tensor-native chain requires at least one chain step".to_string(),
        )
    })?;
    if artifact.initial_boundary_commitment != first_step.carried_state_in_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain initial boundary commitment does not match the first step input boundary"
                .to_string(),
        ));
    }
    if artifact.terminal_boundary_commitment != last_step.carried_state_out_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain terminal boundary commitment does not match the final step output boundary"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase93_tensor_native_chain_artifact(
        &artifact.primitive_artifact,
        &artifact.shared_table_registry_commitment,
        &artifact.steps,
        &artifact.steps_commitment,
        &artifact.initial_boundary_commitment,
        &artifact.terminal_boundary_commitment,
        artifact.total_steps,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase93_tensor_native_chain_artifact(
    artifact: &Phase93TensorNativeChainArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE93_TENSOR_NATIVE_CHAIN_JSON_BYTES,
        "Phase 93 tensor-native chain artifact",
    )
}

pub fn load_phase93_tensor_native_chain_artifact(
    path: &Path,
) -> Result<Phase93TensorNativeChainArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE93_TENSOR_NATIVE_CHAIN_JSON_BYTES,
        "Phase 93 tensor-native chain artifact",
    )?;
    let artifact: Phase93TensorNativeChainArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase93_tensor_native_chain_artifact(&artifact)?;
    Ok(artifact)
}

pub fn prepare_phase945_gemma_block_core_slice_artifact(
    chain_artifact: &Phase93TensorNativeChainArtifact,
    execution_proof: &VanillaStarkExecutionProof,
) -> Result<Phase945GemmaBlockCoreSliceArtifact> {
    verify_phase93_tensor_native_chain_artifact(chain_artifact)?;
    validate_phase945_gemma_execution_proof(execution_proof)?;

    let payload = parse_phase945_arithmetic_subset_payload(execution_proof)?;
    let shared_normalization = payload.embedded_shared_normalization.ok_or_else(|| {
        VmError::InvalidConfig(
            "gemma_block_v4 S-two proof payload is missing embedded shared normalization proof"
                .to_string(),
        )
    })?;
    let shared_activation = payload.embedded_shared_activation_lookup.ok_or_else(|| {
        VmError::InvalidConfig(
            "gemma_block_v4 S-two proof payload is missing embedded shared activation proof"
                .to_string(),
        )
    })?;
    if !verify_phase10_shared_normalization_lookup_envelope(&shared_normalization.proof_envelope)? {
        return Err(VmError::UnsupportedProof(
            "gemma_block_v4 embedded shared normalization proof did not verify".to_string(),
        ));
    }
    if !verify_phase10_shared_binary_step_lookup_envelope(&shared_activation.proof_envelope)? {
        return Err(VmError::UnsupportedProof(
            "gemma_block_v4 embedded shared activation proof did not verify".to_string(),
        ));
    }

    let shared_normalization_rows =
        phase945_normalization_rows_from_embedded(&shared_normalization)?;
    let shared_activation_rows = phase945_activation_rows_from_embedded(&shared_activation);
    let normalization_row_set_commitment =
        commit_phase945_normalization_row_set(&shared_normalization_rows)?;
    let activation_row_set_commitment =
        commit_phase945_activation_row_set(&shared_activation_rows)?;
    let execution_proof_commitment = commit_phase945_execution_proof(execution_proof)?;

    let primitive_template_set =
        phase93_unique_primitive_normalization_row_set(&chain_artifact.primitive_artifact)?;
    let gemma_normalization_set = phase945_unique_normalization_row_set(&shared_normalization_rows);
    if primitive_template_set != gemma_normalization_set {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice normalization row set does not match the tensor-native primitive template row set"
                .to_string(),
        ));
    }

    let total_shared_normalization_rows = shared_normalization_rows.len();
    let total_shared_activation_rows = shared_activation_rows.len();
    let artifact_commitment = commit_phase945_gemma_block_core_slice_artifact(
        chain_artifact,
        execution_proof,
        &execution_proof_commitment,
        &shared_normalization.statement_version,
        &shared_normalization.semantic_scope,
        &shared_activation.statement_version,
        &shared_activation.semantic_scope,
        &shared_normalization_rows,
        &shared_activation_rows,
        &normalization_row_set_commitment,
        &activation_row_set_commitment,
    )?;

    Ok(Phase945GemmaBlockCoreSliceArtifact {
        artifact_version: STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_VERSION_PHASE945.to_string(),
        semantic_scope: STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_SCOPE_PHASE945.to_string(),
        artifact_commitment,
        program_label: "gemma_block_v4".to_string(),
        chain_artifact_commitment: chain_artifact.artifact_commitment.clone(),
        execution_proof_commitment,
        normalization_row_set_commitment,
        activation_row_set_commitment,
        execution_proof_backend: execution_proof.proof_backend,
        execution_proof_backend_version: execution_proof.proof_backend_version.clone(),
        execution_statement_version: execution_proof.claim.statement_version.clone(),
        shared_normalization_statement_version: shared_normalization.statement_version,
        shared_normalization_scope: shared_normalization.semantic_scope,
        shared_activation_statement_version: shared_activation.statement_version,
        shared_activation_scope: shared_activation.semantic_scope,
        final_acc: i64::from(execution_proof.claim.final_state.acc),
        total_shared_normalization_rows,
        total_shared_activation_rows,
        chain_artifact: chain_artifact.clone(),
        shared_normalization_rows,
        shared_activation_rows,
        execution_proof: execution_proof.clone(),
    })
}

pub fn verify_phase945_gemma_block_core_slice_artifact(
    artifact: &Phase945GemmaBlockCoreSliceArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_VERSION_PHASE945 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 94.5 Gemma core slice artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_SCOPE_PHASE945 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 94.5 Gemma core slice artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 94.5 program label `{}`",
            artifact.program_label
        )));
    }

    verify_phase93_tensor_native_chain_artifact(&artifact.chain_artifact)?;
    if artifact.chain_artifact_commitment != artifact.chain_artifact.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice chain_artifact_commitment does not match the nested chain artifact"
                .to_string(),
        ));
    }

    validate_phase945_gemma_execution_proof(&artifact.execution_proof)?;
    let expected_execution_proof_commitment =
        commit_phase945_execution_proof(&artifact.execution_proof)?;
    if artifact.execution_proof_commitment != expected_execution_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice execution_proof_commitment does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.execution_proof_backend != artifact.execution_proof.proof_backend {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice execution_proof_backend does not match the nested proof"
                .to_string(),
        ));
    }
    if artifact.execution_proof_backend_version != artifact.execution_proof.proof_backend_version {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice execution_proof_backend_version does not match the nested proof"
                .to_string(),
        ));
    }
    if artifact.execution_statement_version != artifact.execution_proof.claim.statement_version {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice execution_statement_version does not match the nested proof"
                .to_string(),
        ));
    }
    if artifact.final_acc != i64::from(artifact.execution_proof.claim.final_state.acc) {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice final_acc does not match the nested execution proof"
                .to_string(),
        ));
    }

    let payload = parse_phase945_arithmetic_subset_payload(&artifact.execution_proof)?;
    let shared_normalization = payload.embedded_shared_normalization.ok_or_else(|| {
        VmError::InvalidConfig(
            "gemma_block_v4 S-two proof payload is missing embedded shared normalization proof"
                .to_string(),
        )
    })?;
    let shared_activation = payload.embedded_shared_activation_lookup.ok_or_else(|| {
        VmError::InvalidConfig(
            "gemma_block_v4 S-two proof payload is missing embedded shared activation proof"
                .to_string(),
        )
    })?;

    if artifact.shared_normalization_statement_version != shared_normalization.statement_version {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice shared_normalization_statement_version does not match the nested proof payload"
                .to_string(),
        ));
    }
    if artifact.shared_normalization_scope != shared_normalization.semantic_scope {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice shared_normalization_scope does not match the nested proof payload"
                .to_string(),
        ));
    }
    if artifact.shared_activation_statement_version != shared_activation.statement_version {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice shared_activation_statement_version does not match the nested proof payload"
                .to_string(),
        ));
    }
    if artifact.shared_activation_scope != shared_activation.semantic_scope {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice shared_activation_scope does not match the nested proof payload"
                .to_string(),
        ));
    }
    if !verify_phase10_shared_normalization_lookup_envelope(&shared_normalization.proof_envelope)? {
        return Err(VmError::UnsupportedProof(
            "Phase 94.5 Gemma core slice embedded shared normalization proof did not verify"
                .to_string(),
        ));
    }
    if !verify_phase10_shared_binary_step_lookup_envelope(&shared_activation.proof_envelope)? {
        return Err(VmError::UnsupportedProof(
            "Phase 94.5 Gemma core slice embedded shared activation proof did not verify"
                .to_string(),
        ));
    }

    let expected_normalization_rows =
        phase945_normalization_rows_from_embedded(&shared_normalization)?;
    if artifact.shared_normalization_rows != expected_normalization_rows {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice shared_normalization_rows do not match the nested proof payload"
                .to_string(),
        ));
    }
    let expected_activation_rows = phase945_activation_rows_from_embedded(&shared_activation);
    if artifact.shared_activation_rows != expected_activation_rows {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice shared_activation_rows do not match the nested proof payload"
                .to_string(),
        ));
    }
    if artifact.total_shared_normalization_rows != artifact.shared_normalization_rows.len() {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice total_shared_normalization_rows does not match the row count"
                .to_string(),
        ));
    }
    if artifact.total_shared_activation_rows != artifact.shared_activation_rows.len() {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice total_shared_activation_rows does not match the row count"
                .to_string(),
        ));
    }

    let expected_normalization_row_set_commitment =
        commit_phase945_normalization_row_set(&artifact.shared_normalization_rows)?;
    if artifact.normalization_row_set_commitment != expected_normalization_row_set_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice normalization_row_set_commitment does not match the serialized normalization rows"
                .to_string(),
        ));
    }
    let expected_activation_row_set_commitment =
        commit_phase945_activation_row_set(&artifact.shared_activation_rows)?;
    if artifact.activation_row_set_commitment != expected_activation_row_set_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice activation_row_set_commitment does not match the serialized activation rows"
                .to_string(),
        ));
    }

    let primitive_template_set = phase93_unique_primitive_normalization_row_set(
        &artifact.chain_artifact.primitive_artifact,
    )?;
    let gemma_normalization_set =
        phase945_unique_normalization_row_set(&artifact.shared_normalization_rows);
    if primitive_template_set != gemma_normalization_set {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice normalization row set does not match the tensor-native primitive template row set"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase945_gemma_block_core_slice_artifact(
        &artifact.chain_artifact,
        &artifact.execution_proof,
        &artifact.execution_proof_commitment,
        &artifact.shared_normalization_statement_version,
        &artifact.shared_normalization_scope,
        &artifact.shared_activation_statement_version,
        &artifact.shared_activation_scope,
        &artifact.shared_normalization_rows,
        &artifact.shared_activation_rows,
        &artifact.normalization_row_set_commitment,
        &artifact.activation_row_set_commitment,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase945_gemma_block_core_slice_artifact(
    artifact: &Phase945GemmaBlockCoreSliceArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE945_GEMMA_BLOCK_CORE_SLICE_JSON_BYTES,
        "Phase 94.5 Gemma block core slice artifact",
    )
}

pub fn load_phase945_gemma_block_core_slice_artifact(
    path: &Path,
) -> Result<Phase945GemmaBlockCoreSliceArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE945_GEMMA_BLOCK_CORE_SLICE_JSON_BYTES,
        "Phase 94.5 Gemma block core slice artifact",
    )?;
    let artifact: Phase945GemmaBlockCoreSliceArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase945_gemma_block_core_slice_artifact(&artifact)?;
    Ok(artifact)
}

pub fn prepare_phase9475_gemma_block_richer_slice_artifact(
    core_slice_artifact: &Phase945GemmaBlockCoreSliceArtifact,
) -> Result<Phase9475GemmaBlockRicherSliceArtifact> {
    verify_phase945_gemma_block_core_slice_artifact(core_slice_artifact)?;
    let selected_memory_window = phase9475_selected_memory_window(
        &core_slice_artifact.execution_proof.claim.final_state.memory,
    )?;
    let selected_memory_window_commitment =
        commit_phase9475_selected_memory_window(&selected_memory_window)?;
    let invariant_summary =
        phase9475_invariant_summary(&core_slice_artifact.execution_proof.claim.final_state.memory)?;

    let artifact_commitment = commit_phase9475_gemma_block_richer_slice_artifact(
        core_slice_artifact,
        &selected_memory_window,
        &selected_memory_window_commitment,
        &invariant_summary,
    )?;

    Ok(Phase9475GemmaBlockRicherSliceArtifact {
        artifact_version: STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_VERSION_PHASE9475.to_string(),
        semantic_scope: STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_SCOPE_PHASE9475.to_string(),
        artifact_commitment,
        program_label: core_slice_artifact.program_label.clone(),
        core_slice_artifact_commitment: core_slice_artifact.artifact_commitment.clone(),
        chain_artifact_commitment: core_slice_artifact.chain_artifact_commitment.clone(),
        shared_table_registry_commitment: core_slice_artifact
            .chain_artifact
            .shared_table_registry_commitment
            .clone(),
        selected_memory_window_commitment,
        local_score: invariant_summary.local_score,
        global_score: invariant_summary.global_score,
        grouped_value_mix: invariant_summary.grouped_value_mix,
        residual_output: invariant_summary.residual_output,
        primary_norm_sq: invariant_summary.primary_norm_sq,
        primary_inv_sqrt_q8: invariant_summary.primary_inv_sqrt_q8,
        primary_activation_input: invariant_summary.primary_activation_input,
        primary_activation_output: invariant_summary.primary_activation_output,
        secondary_norm_sq: invariant_summary.secondary_norm_sq,
        secondary_inv_sqrt_q8: invariant_summary.secondary_inv_sqrt_q8,
        secondary_activation_input: invariant_summary.secondary_activation_input,
        secondary_activation_output: invariant_summary.secondary_activation_output,
        selected_memory_window,
        core_slice_artifact: core_slice_artifact.clone(),
    })
}

pub fn verify_phase9475_gemma_block_richer_slice_artifact(
    artifact: &Phase9475GemmaBlockRicherSliceArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_VERSION_PHASE9475 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 94.75 Gemma richer slice artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_SCOPE_PHASE9475 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 94.75 Gemma richer slice artifact scope `{}`",
            artifact.semantic_scope
        )));
    }

    verify_phase945_gemma_block_core_slice_artifact(&artifact.core_slice_artifact)?;
    if artifact.program_label != artifact.core_slice_artifact.program_label {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice program_label does not match the nested core slice"
                .to_string(),
        ));
    }
    if artifact.core_slice_artifact_commitment != artifact.core_slice_artifact.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice core_slice_artifact_commitment does not match the nested core slice"
                .to_string(),
        ));
    }
    if artifact.chain_artifact_commitment != artifact.core_slice_artifact.chain_artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice chain_artifact_commitment does not match the nested core slice"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment
        != artifact
            .core_slice_artifact
            .chain_artifact
            .shared_table_registry_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice shared_table_registry_commitment does not match the nested chain artifact"
                .to_string(),
        ));
    }

    let expected_memory_window = phase9475_selected_memory_window(
        &artifact
            .core_slice_artifact
            .execution_proof
            .claim
            .final_state
            .memory,
    )?;
    if artifact.selected_memory_window != expected_memory_window {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice selected_memory_window does not match the nested execution proof"
                .to_string(),
        ));
    }
    let expected_memory_window_commitment =
        commit_phase9475_selected_memory_window(&artifact.selected_memory_window)?;
    if artifact.selected_memory_window_commitment != expected_memory_window_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice selected_memory_window_commitment does not match the serialized memory window"
                .to_string(),
        ));
    }

    let expected_invariant_summary = phase9475_invariant_summary(
        &artifact
            .core_slice_artifact
            .execution_proof
            .claim
            .final_state
            .memory,
    )?;
    phase9475_validate_summary_fields(artifact, &expected_invariant_summary)?;

    let expected_artifact_commitment = commit_phase9475_gemma_block_richer_slice_artifact(
        &artifact.core_slice_artifact,
        &artifact.selected_memory_window,
        &artifact.selected_memory_window_commitment,
        &expected_invariant_summary,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase9475_gemma_block_richer_slice_artifact(
    artifact: &Phase9475GemmaBlockRicherSliceArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE9475_GEMMA_BLOCK_RICHER_SLICE_JSON_BYTES,
        "Phase 94.75 Gemma block richer slice artifact",
    )
}

pub fn load_phase9475_gemma_block_richer_slice_artifact(
    path: &Path,
) -> Result<Phase9475GemmaBlockRicherSliceArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE9475_GEMMA_BLOCK_RICHER_SLICE_JSON_BYTES,
        "Phase 94.75 Gemma block richer slice artifact",
    )?;
    let artifact: Phase9475GemmaBlockRicherSliceArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase9475_gemma_block_richer_slice_artifact(&artifact)?;
    Ok(artifact)
}

fn validate_phase95_total_slices(total_slices: usize) -> Result<u64> {
    if total_slices < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 95 repeated Gemma slice accumulation requires at least two slices".to_string(),
        ));
    }
    if total_slices > MAX_PHASE95_REPEATED_GEMMA_TOTAL_SLICES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 95 repeated Gemma slice accumulation supports at most {} slices",
            MAX_PHASE95_REPEATED_GEMMA_TOTAL_SLICES
        )));
    }
    Ok(total_slices as u64)
}

fn checked_phase95_block_index(start_block_index: u64, slice_index: usize) -> Result<u64> {
    start_block_index
        .checked_add(slice_index as u64)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 95 block_index overflow while deriving repeated slice members".to_string(),
            )
        })
}

fn checked_phase95_terminal_block_index(start_block_index: u64, total_slices: u64) -> Result<u64> {
    let last_offset = total_slices.checked_sub(1).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 95 repeated Gemma slice accumulation requires at least two slices".to_string(),
        )
    })?;
    start_block_index.checked_add(last_offset).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 95 terminal_block_index overflow while deriving the repeated slice interval"
                .to_string(),
        )
    })
}

pub fn prepare_phase95_repeated_gemma_slice_accumulation_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    total_slices: usize,
    repeated_token_position: u64,
    start_block_index: u64,
) -> Result<Phase95RepeatedGemmaSliceAccumulationArtifact> {
    verify_phase92_shared_normalization_primitive_artifact(shared_primitive_artifact)?;
    validate_phase945_gemma_execution_proof(shared_execution_proof)?;
    let total_slices_u64 = validate_phase95_total_slices(total_slices)?;

    let shared_execution_proof_commitment =
        commit_phase945_execution_proof(shared_execution_proof)?;
    let mut members = Vec::with_capacity(total_slices);
    for slice_index in 0..total_slices {
        let block_index = checked_phase95_block_index(start_block_index, slice_index)?;
        let chain_artifact = prepare_phase93_tensor_native_chain_artifact_at(
            shared_primitive_artifact,
            repeated_token_position,
            block_index,
        )?;
        let core_slice_artifact = prepare_phase945_gemma_block_core_slice_artifact(
            &chain_artifact,
            shared_execution_proof,
        )?;
        let richer_slice_artifact =
            prepare_phase9475_gemma_block_richer_slice_artifact(&core_slice_artifact)?;
        members.push(Phase95RepeatedGemmaSliceMember {
            slice_index,
            token_position: repeated_token_position,
            block_index,
            richer_slice_artifact_commitment: richer_slice_artifact.artifact_commitment.clone(),
            chain_artifact_commitment: richer_slice_artifact.chain_artifact_commitment.clone(),
            initial_boundary_commitment: chain_artifact.initial_boundary_commitment.clone(),
            terminal_boundary_commitment: chain_artifact.terminal_boundary_commitment.clone(),
            selected_memory_window_commitment: richer_slice_artifact
                .selected_memory_window_commitment
                .clone(),
            local_score: richer_slice_artifact.local_score,
            global_score: richer_slice_artifact.global_score,
            grouped_value_mix: richer_slice_artifact.grouped_value_mix,
            residual_output: richer_slice_artifact.residual_output,
            final_acc: core_slice_artifact.final_acc,
        });
    }

    let members_commitment = commit_phase95_repeated_gemma_members(&members)?;
    let terminal_block_index =
        checked_phase95_terminal_block_index(start_block_index, total_slices_u64)?;
    let artifact_commitment = commit_phase95_repeated_gemma_slice_accumulation_artifact(
        shared_primitive_artifact,
        shared_execution_proof,
        &shared_execution_proof_commitment,
        &members,
        &members_commitment,
        repeated_token_position,
        start_block_index,
        terminal_block_index,
    )?;

    Ok(Phase95RepeatedGemmaSliceAccumulationArtifact {
        artifact_version: STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE95
            .to_string(),
        semantic_scope: STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE95.to_string(),
        artifact_commitment,
        program_label: "gemma_block_v4".to_string(),
        shared_primitive_artifact_commitment: shared_primitive_artifact.artifact_commitment.clone(),
        shared_table_registry_commitment: shared_primitive_artifact
            .static_table_registry_commitment
            .clone(),
        shared_execution_proof_commitment,
        shared_execution_proof_backend_version: shared_execution_proof
            .proof_backend_version
            .clone(),
        shared_execution_statement_version: shared_execution_proof.claim.statement_version.clone(),
        total_slices,
        repeated_token_position,
        start_block_index,
        terminal_block_index,
        members_commitment,
        shared_primitive_artifact: shared_primitive_artifact.clone(),
        shared_execution_proof: shared_execution_proof.clone(),
        members,
    })
}

pub fn verify_phase95_repeated_gemma_slice_accumulation_artifact(
    artifact: &Phase95RepeatedGemmaSliceAccumulationArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE95
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 95 repeated Gemma slice accumulation artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE95 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 95 repeated Gemma slice accumulation artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 95 program label `{}`",
            artifact.program_label
        )));
    }
    verify_phase92_shared_normalization_primitive_artifact(&artifact.shared_primitive_artifact)?;
    if artifact.shared_primitive_artifact_commitment
        != artifact.shared_primitive_artifact.artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 95 shared_primitive_artifact_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment
        != artifact
            .shared_primitive_artifact
            .static_table_registry_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 95 shared_table_registry_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }

    validate_phase945_gemma_execution_proof(&artifact.shared_execution_proof)?;
    let expected_execution_proof_commitment =
        commit_phase945_execution_proof(&artifact.shared_execution_proof)?;
    if artifact.shared_execution_proof_commitment != expected_execution_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 95 shared_execution_proof_commitment does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_backend_version
        != artifact.shared_execution_proof.proof_backend_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 95 shared_execution_proof_backend_version does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.shared_execution_statement_version
        != artifact.shared_execution_proof.claim.statement_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 95 shared_execution_statement_version does not match the nested execution proof"
                .to_string(),
        ));
    }

    let total_slices_u64 = validate_phase95_total_slices(artifact.total_slices)?;
    if artifact.total_slices != artifact.members.len() {
        return Err(VmError::InvalidConfig(
            "Phase 95 total_slices does not match the member count".to_string(),
        ));
    }
    let expected_terminal_block_index =
        checked_phase95_terminal_block_index(artifact.start_block_index, total_slices_u64)?;
    if artifact.terminal_block_index != expected_terminal_block_index {
        return Err(VmError::InvalidConfig(
            "Phase 95 terminal_block_index does not match start_block_index + total_slices - 1"
                .to_string(),
        ));
    }

    for (expected_slice_index, member) in artifact.members.iter().enumerate() {
        if member.slice_index != expected_slice_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 expected contiguous slice_index {}, got {}",
                expected_slice_index, member.slice_index
            )));
        }
        if member.token_position != artifact.repeated_token_position {
            return Err(VmError::InvalidConfig(
                "Phase 95 member token_position does not match repeated_token_position".to_string(),
            ));
        }
        let expected_block_index =
            checked_phase95_block_index(artifact.start_block_index, expected_slice_index)?;
        if member.block_index != expected_block_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 expected contiguous block_index {}, got {}",
                expected_block_index, member.block_index
            )));
        }

        let chain_artifact = prepare_phase93_tensor_native_chain_artifact_at(
            &artifact.shared_primitive_artifact,
            member.token_position,
            member.block_index,
        )?;
        let core_slice_artifact = prepare_phase945_gemma_block_core_slice_artifact(
            &chain_artifact,
            &artifact.shared_execution_proof,
        )?;
        let richer_slice_artifact =
            prepare_phase9475_gemma_block_richer_slice_artifact(&core_slice_artifact)?;

        if member.chain_artifact_commitment != chain_artifact.artifact_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 member {} chain_artifact_commitment does not match the reconstructed chain artifact",
                member.slice_index
            )));
        }
        if member.richer_slice_artifact_commitment != richer_slice_artifact.artifact_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 member {} richer_slice_artifact_commitment does not match the reconstructed richer slice",
                member.slice_index
            )));
        }
        if member.initial_boundary_commitment != chain_artifact.initial_boundary_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 member {} initial_boundary_commitment does not match the reconstructed chain artifact",
                member.slice_index
            )));
        }
        if member.terminal_boundary_commitment != chain_artifact.terminal_boundary_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 member {} terminal_boundary_commitment does not match the reconstructed chain artifact",
                member.slice_index
            )));
        }
        if member.selected_memory_window_commitment
            != richer_slice_artifact.selected_memory_window_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 member {} selected_memory_window_commitment does not match the reconstructed richer slice",
                member.slice_index
            )));
        }
        if member.local_score != richer_slice_artifact.local_score
            || member.global_score != richer_slice_artifact.global_score
            || member.grouped_value_mix != richer_slice_artifact.grouped_value_mix
            || member.residual_output != richer_slice_artifact.residual_output
            || member.final_acc != core_slice_artifact.final_acc
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 95 member {} summary fields do not match the reconstructed richer slice",
                member.slice_index
            )));
        }
    }

    let expected_members_commitment = commit_phase95_repeated_gemma_members(&artifact.members)?;
    if artifact.members_commitment != expected_members_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 95 members_commitment does not match the serialized member summaries"
                .to_string(),
        ));
    }
    let expected_artifact_commitment = commit_phase95_repeated_gemma_slice_accumulation_artifact(
        &artifact.shared_primitive_artifact,
        &artifact.shared_execution_proof,
        &artifact.shared_execution_proof_commitment,
        &artifact.members,
        &artifact.members_commitment,
        artifact.repeated_token_position,
        artifact.start_block_index,
        artifact.terminal_block_index,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 95 repeated Gemma slice accumulation artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase95_repeated_gemma_slice_accumulation_artifact(
    artifact: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE95_REPEATED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES,
        "Phase 95 repeated Gemma slice accumulation artifact",
    )
}

pub fn load_phase95_repeated_gemma_slice_accumulation_artifact(
    path: &Path,
) -> Result<Phase95RepeatedGemmaSliceAccumulationArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE95_REPEATED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES,
        "Phase 95 repeated Gemma slice accumulation artifact",
    )?;
    let artifact: Phase95RepeatedGemmaSliceAccumulationArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase95_repeated_gemma_slice_accumulation_artifact(&artifact)?;
    Ok(artifact)
}

fn validate_phase965_bounded_fold_arity(bounded_fold_arity: usize) -> Result<()> {
    if bounded_fold_arity < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 folded Gemma slice accumulation requires bounded_fold_arity >= 2"
                .to_string(),
        ));
    }
    Ok(())
}

fn canonical_phase965_folded_groups(
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    bounded_fold_arity: usize,
) -> Result<Vec<Phase965FoldedGemmaSliceGroup>> {
    validate_phase965_bounded_fold_arity(bounded_fold_arity)?;
    let mut folded_groups = Vec::new();
    for (folded_group_index, chunk) in source.members.chunks(bounded_fold_arity).enumerate() {
        let first = chunk.first().ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 96.5 folded Gemma slice accumulation encountered an empty member chunk"
                    .to_string(),
            )
        })?;
        let last = chunk
            .last()
            .expect("non-empty member chunk has a last member");
        let richer_commitments = chunk
            .iter()
            .map(|member| member.richer_slice_artifact_commitment.clone())
            .collect::<Vec<_>>();
        let selected_memory_window_commitments = chunk
            .iter()
            .map(|member| member.selected_memory_window_commitment.clone())
            .collect::<Vec<_>>();
        let member_richer_slice_commitment_sequence_commitment = commit_namespace_strings(
            "phase965/member-richer-slice-commitment-sequence",
            &richer_commitments,
        )?;
        let member_selected_memory_window_commitment_sequence_commitment =
            commit_namespace_strings(
                "phase965/member-selected-memory-window-commitment-sequence",
                &selected_memory_window_commitments,
            )?;
        let local_score_sum = chunk
            .iter()
            .map(|member| i64::from(member.local_score))
            .sum::<i64>();
        let global_score_sum = chunk
            .iter()
            .map(|member| i64::from(member.global_score))
            .sum::<i64>();
        let grouped_value_mix_sum = chunk
            .iter()
            .map(|member| i64::from(member.grouped_value_mix))
            .sum::<i64>();
        let residual_output_sum = chunk
            .iter()
            .map(|member| i64::from(member.residual_output))
            .sum::<i64>();
        let final_acc_sum = chunk.iter().map(|member| member.final_acc).sum::<i64>();
        let mut group = Phase965FoldedGemmaSliceGroup {
            folded_group_index,
            start_slice_index: first.slice_index,
            terminal_slice_index: last.slice_index,
            start_block_index: first.block_index,
            terminal_block_index: last.block_index,
            first_richer_slice_artifact_commitment: first.richer_slice_artifact_commitment.clone(),
            terminal_richer_slice_artifact_commitment: last
                .richer_slice_artifact_commitment
                .clone(),
            initial_boundary_commitment: first.initial_boundary_commitment.clone(),
            terminal_boundary_commitment: last.terminal_boundary_commitment.clone(),
            member_richer_slice_commitment_sequence_commitment,
            member_selected_memory_window_commitment_sequence_commitment,
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            folded_group_commitment: String::new(),
        };
        group.folded_group_commitment = commit_phase965_folded_gemma_slice_group(&group)?;
        folded_groups.push(group);
    }
    Ok(folded_groups)
}

fn validate_phase965_folded_gemma_slice_accumulation_artifact_shallow(
    artifact: &Phase965FoldedGemmaSliceAccumulationArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE965 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 96.5 folded Gemma slice accumulation artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE965 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 96.5 folded Gemma slice accumulation artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 96.5 program label `{}`",
            artifact.program_label
        )));
    }
    validate_phase95_total_slices(artifact.total_slices)?;
    validate_phase965_bounded_fold_arity(artifact.bounded_fold_arity)?;
    if artifact.total_folded_groups != artifact.folded_groups.len() {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 total_folded_groups does not match the folded group count".to_string(),
        ));
    }
    if artifact.folded_groups.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 folded Gemma slice accumulation requires at least one folded group"
                .to_string(),
        ));
    }
    Ok(())
}

pub fn prepare_phase965_folded_gemma_slice_accumulation_artifact(
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
) -> Result<Phase965FoldedGemmaSliceAccumulationArtifact> {
    verify_phase95_repeated_gemma_slice_accumulation_artifact(source)?;
    let bounded_fold_arity = PHASE965_DEFAULT_BOUNDED_FOLD_ARITY;
    let folded_groups = canonical_phase965_folded_groups(source, bounded_fold_arity)?;
    let total_folded_groups = folded_groups.len();
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 96.5 folded Gemma slice accumulation requires at least one source member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("source members are non-empty after first check");
    let fold_template_commitment = commit_phase965_fold_template(
        &source.artifact_commitment,
        &source.members_commitment,
        &source.shared_primitive_artifact_commitment,
        &source.shared_table_registry_commitment,
        &source.shared_execution_proof_commitment,
        bounded_fold_arity,
        source.total_slices,
        source.repeated_token_position,
        source.start_block_index,
        source.terminal_block_index,
    )?;
    let folded_group_sequence_commitment = commit_phase965_folded_group_sequence(&folded_groups)?;
    let local_score_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.local_score))
        .sum::<i64>();
    let global_score_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.global_score))
        .sum::<i64>();
    let grouped_value_mix_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.grouped_value_mix))
        .sum::<i64>();
    let residual_output_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.residual_output))
        .sum::<i64>();
    let final_acc_sum = source
        .members
        .iter()
        .map(|member| member.final_acc)
        .sum::<i64>();
    let folded_slice_accumulator_commitment = commit_phase965_folded_slice_accumulator(
        &fold_template_commitment,
        &folded_group_sequence_commitment,
        &first_member.initial_boundary_commitment,
        &last_member.terminal_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        source.total_slices,
        total_folded_groups,
    )?;
    let artifact_commitment = commit_phase965_folded_gemma_slice_accumulation_artifact(
        source,
        &folded_groups,
        &fold_template_commitment,
        &folded_group_sequence_commitment,
        &folded_slice_accumulator_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        bounded_fold_arity,
    )?;

    Ok(Phase965FoldedGemmaSliceAccumulationArtifact {
        artifact_version: STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE965
            .to_string(),
        semantic_scope: STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE965.to_string(),
        artifact_commitment,
        program_label: source.program_label.clone(),
        source_phase95_artifact_commitment: source.artifact_commitment.clone(),
        source_members_commitment: source.members_commitment.clone(),
        shared_primitive_artifact_commitment: source.shared_primitive_artifact_commitment.clone(),
        shared_table_registry_commitment: source.shared_table_registry_commitment.clone(),
        shared_execution_proof_commitment: source.shared_execution_proof_commitment.clone(),
        shared_execution_proof_backend_version: source
            .shared_execution_proof_backend_version
            .clone(),
        shared_execution_statement_version: source.shared_execution_statement_version.clone(),
        total_slices: source.total_slices,
        repeated_token_position: source.repeated_token_position,
        start_block_index: source.start_block_index,
        terminal_block_index: source.terminal_block_index,
        bounded_fold_arity,
        total_folded_groups,
        global_start_boundary_commitment: first_member.initial_boundary_commitment.clone(),
        global_end_boundary_commitment: last_member.terminal_boundary_commitment.clone(),
        first_richer_slice_artifact_commitment: first_member
            .richer_slice_artifact_commitment
            .clone(),
        terminal_richer_slice_artifact_commitment: last_member
            .richer_slice_artifact_commitment
            .clone(),
        fold_template_commitment,
        folded_group_sequence_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        folded_slice_accumulator_commitment,
        folded_groups,
    })
}

pub fn verify_phase965_folded_gemma_slice_accumulation_artifact(
    artifact: &Phase965FoldedGemmaSliceAccumulationArtifact,
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
) -> Result<()> {
    validate_phase965_folded_gemma_slice_accumulation_artifact_shallow(artifact)?;
    verify_phase95_repeated_gemma_slice_accumulation_artifact(source)?;

    if artifact.program_label != source.program_label {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 program_label does not match the source Phase 95 artifact".to_string(),
        ));
    }
    if artifact.source_phase95_artifact_commitment != source.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 source_phase95_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.source_members_commitment != source.members_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 source_members_commitment does not match the source artifact".to_string(),
        ));
    }
    if artifact.shared_primitive_artifact_commitment != source.shared_primitive_artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 shared_primitive_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment != source.shared_table_registry_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 shared_table_registry_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_commitment != source.shared_execution_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 shared_execution_proof_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_backend_version
        != source.shared_execution_proof_backend_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 shared_execution_proof_backend_version does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_execution_statement_version != source.shared_execution_statement_version {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 shared_execution_statement_version does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.total_slices != source.total_slices
        || artifact.repeated_token_position != source.repeated_token_position
        || artifact.start_block_index != source.start_block_index
        || artifact.terminal_block_index != source.terminal_block_index
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 interval metadata does not match the source Phase 95 artifact".to_string(),
        ));
    }

    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 96.5 folded Gemma slice accumulation requires at least one source member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("source members are non-empty after first check");
    if artifact.global_start_boundary_commitment != first_member.initial_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 global_start_boundary_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.global_end_boundary_commitment != last_member.terminal_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 global_end_boundary_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.first_richer_slice_artifact_commitment
        != first_member.richer_slice_artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 first_richer_slice_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.terminal_richer_slice_artifact_commitment
        != last_member.richer_slice_artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 terminal_richer_slice_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }

    let expected_folded_groups =
        canonical_phase965_folded_groups(source, artifact.bounded_fold_arity)?;
    if artifact.folded_groups != expected_folded_groups {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 folded_groups do not match the canonical source-derived groups".to_string(),
        ));
    }

    let expected_fold_template_commitment = commit_phase965_fold_template(
        &source.artifact_commitment,
        &source.members_commitment,
        &source.shared_primitive_artifact_commitment,
        &source.shared_table_registry_commitment,
        &source.shared_execution_proof_commitment,
        artifact.bounded_fold_arity,
        source.total_slices,
        source.repeated_token_position,
        source.start_block_index,
        source.terminal_block_index,
    )?;
    if artifact.fold_template_commitment != expected_fold_template_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 fold_template_commitment does not match the canonical source-derived template"
                .to_string(),
        ));
    }

    let expected_folded_group_sequence_commitment =
        commit_phase965_folded_group_sequence(&artifact.folded_groups)?;
    if artifact.folded_group_sequence_commitment != expected_folded_group_sequence_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 folded_group_sequence_commitment does not match the serialized folded groups"
                .to_string(),
        ));
    }

    let expected_local_score_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.local_score))
        .sum::<i64>();
    let expected_global_score_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.global_score))
        .sum::<i64>();
    let expected_grouped_value_mix_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.grouped_value_mix))
        .sum::<i64>();
    let expected_residual_output_sum = source
        .members
        .iter()
        .map(|member| i64::from(member.residual_output))
        .sum::<i64>();
    let expected_final_acc_sum = source
        .members
        .iter()
        .map(|member| member.final_acc)
        .sum::<i64>();
    if artifact.local_score_sum != expected_local_score_sum
        || artifact.global_score_sum != expected_global_score_sum
        || artifact.grouped_value_mix_sum != expected_grouped_value_mix_sum
        || artifact.residual_output_sum != expected_residual_output_sum
        || artifact.final_acc_sum != expected_final_acc_sum
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 accumulation totals do not match the source member summaries".to_string(),
        ));
    }

    let expected_folded_slice_accumulator_commitment = commit_phase965_folded_slice_accumulator(
        &artifact.fold_template_commitment,
        &artifact.folded_group_sequence_commitment,
        &artifact.global_start_boundary_commitment,
        &artifact.global_end_boundary_commitment,
        artifact.local_score_sum,
        artifact.global_score_sum,
        artifact.grouped_value_mix_sum,
        artifact.residual_output_sum,
        artifact.final_acc_sum,
        artifact.total_slices,
        artifact.total_folded_groups,
    )?;
    if artifact.folded_slice_accumulator_commitment != expected_folded_slice_accumulator_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 folded_slice_accumulator_commitment does not match the serialized folded groups and totals"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase965_folded_gemma_slice_accumulation_artifact(
        source,
        &artifact.folded_groups,
        &artifact.fold_template_commitment,
        &artifact.folded_group_sequence_commitment,
        &artifact.folded_slice_accumulator_commitment,
        artifact.local_score_sum,
        artifact.global_score_sum,
        artifact.grouped_value_mix_sum,
        artifact.residual_output_sum,
        artifact.final_acc_sum,
        artifact.bounded_fold_arity,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 96.5 folded Gemma slice accumulation artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase965_folded_gemma_slice_accumulation_artifact(
    artifact: &Phase965FoldedGemmaSliceAccumulationArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE965_FOLDED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES,
        "Phase 96.5 folded Gemma slice accumulation artifact",
    )
}

pub fn load_phase965_folded_gemma_slice_accumulation_artifact(
    path: &Path,
) -> Result<Phase965FoldedGemmaSliceAccumulationArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE965_FOLDED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES,
        "Phase 96.5 folded Gemma slice accumulation artifact",
    )?;
    let artifact: Phase965FoldedGemmaSliceAccumulationArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_phase965_folded_gemma_slice_accumulation_artifact_shallow(&artifact)?;
    Ok(artifact)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
struct Phase98InvariantSummaryEntry {
    richer_slice_artifact_commitment: String,
    selected_memory_window_commitment: String,
    local_score: i16,
    global_score: i16,
    grouped_value_mix: i16,
    residual_output: i16,
    primary_norm_sq: i16,
    primary_inv_sqrt_q8: i16,
    primary_activation_input: i16,
    primary_activation_output: i16,
    secondary_norm_sq: i16,
    secondary_inv_sqrt_q8: i16,
    secondary_activation_input: i16,
    secondary_activation_output: i16,
    final_acc: i64,
}

fn canonical_phase98_richer_slice_family(
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
) -> Result<Vec<Phase98InvariantSummaryEntry>> {
    let mut summaries = Vec::with_capacity(source.members.len());
    for member in &source.members {
        let chain_artifact = prepare_phase93_tensor_native_chain_artifact_at(
            &source.shared_primitive_artifact,
            member.token_position,
            member.block_index,
        )?;
        let core_slice_artifact = prepare_phase945_gemma_block_core_slice_artifact(
            &chain_artifact,
            &source.shared_execution_proof,
        )?;
        let richer_slice_artifact =
            prepare_phase9475_gemma_block_richer_slice_artifact(&core_slice_artifact)?;
        if member.richer_slice_artifact_commitment != richer_slice_artifact.artifact_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 98 source member {} richer_slice_artifact_commitment does not match the reconstructed richer slice",
                member.slice_index
            )));
        }
        summaries.push(Phase98InvariantSummaryEntry {
            richer_slice_artifact_commitment: richer_slice_artifact.artifact_commitment.clone(),
            selected_memory_window_commitment: richer_slice_artifact
                .selected_memory_window_commitment
                .clone(),
            local_score: richer_slice_artifact.local_score,
            global_score: richer_slice_artifact.global_score,
            grouped_value_mix: richer_slice_artifact.grouped_value_mix,
            residual_output: richer_slice_artifact.residual_output,
            primary_norm_sq: richer_slice_artifact.primary_norm_sq,
            primary_inv_sqrt_q8: richer_slice_artifact.primary_inv_sqrt_q8,
            primary_activation_input: richer_slice_artifact.primary_activation_input,
            primary_activation_output: richer_slice_artifact.primary_activation_output,
            secondary_norm_sq: richer_slice_artifact.secondary_norm_sq,
            secondary_inv_sqrt_q8: richer_slice_artifact.secondary_inv_sqrt_q8,
            secondary_activation_input: richer_slice_artifact.secondary_activation_input,
            secondary_activation_output: richer_slice_artifact.secondary_activation_output,
            final_acc: core_slice_artifact.final_acc,
        });
    }
    Ok(summaries)
}

fn validate_phase98_folded_gemma_richer_slice_family_artifact_shallow(
    artifact: &Phase98FoldedGemmaRicherSliceFamilyArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_VERSION_PHASE98 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 98 folded Gemma richer slice family artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_SCOPE_PHASE98 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 98 folded Gemma richer slice family artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 98 program label `{}`",
            artifact.program_label
        )));
    }
    validate_phase95_total_slices(artifact.total_slices)?;
    validate_phase965_bounded_fold_arity(artifact.bounded_fold_arity)?;
    if artifact.total_folded_groups == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 98 folded Gemma richer slice family requires at least one folded group"
                .to_string(),
        ));
    }
    Ok(())
}

pub fn prepare_phase98_folded_gemma_richer_slice_family_artifact(
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    folded: &Phase965FoldedGemmaSliceAccumulationArtifact,
) -> Result<Phase98FoldedGemmaRicherSliceFamilyArtifact> {
    verify_phase965_folded_gemma_slice_accumulation_artifact(folded, source)?;
    let family = canonical_phase98_richer_slice_family(source)?;
    let first = family.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 98 folded Gemma richer slice family requires at least one richer slice"
                .to_string(),
        )
    })?;
    let last = family
        .last()
        .expect("richer slice family is non-empty after first check");
    let richer_slice_commitment_sequence_commitment =
        commit_phase98_richer_slice_sequence(&family)?;
    let selected_memory_window_family_commitment =
        commit_phase98_selected_memory_window_family(&family)?;
    let invariant_summary_family_commitment = commit_phase98_invariant_summary_family(&family)?;
    let richer_family_template_commitment = commit_phase98_richer_family_template(
        &source.artifact_commitment,
        &folded.artifact_commitment,
        &source.shared_table_registry_commitment,
        source.total_slices,
        folded.total_folded_groups,
        folded.bounded_fold_arity,
        source.repeated_token_position,
        source.start_block_index,
        source.terminal_block_index,
    )?;
    let local_score_sum = family
        .iter()
        .map(|entry| i64::from(entry.local_score))
        .sum::<i64>();
    let global_score_sum = family
        .iter()
        .map(|entry| i64::from(entry.global_score))
        .sum::<i64>();
    let grouped_value_mix_sum = family
        .iter()
        .map(|entry| i64::from(entry.grouped_value_mix))
        .sum::<i64>();
    let residual_output_sum = family
        .iter()
        .map(|entry| i64::from(entry.residual_output))
        .sum::<i64>();
    let final_acc_sum = family.iter().map(|entry| entry.final_acc).sum::<i64>();
    let primary_norm_sq_min = family
        .iter()
        .map(|entry| entry.primary_norm_sq)
        .min()
        .expect("family is non-empty");
    let primary_norm_sq_max = family
        .iter()
        .map(|entry| entry.primary_norm_sq)
        .max()
        .expect("family is non-empty");
    let secondary_norm_sq_min = family
        .iter()
        .map(|entry| entry.secondary_norm_sq)
        .min()
        .expect("family is non-empty");
    let secondary_norm_sq_max = family
        .iter()
        .map(|entry| entry.secondary_norm_sq)
        .max()
        .expect("family is non-empty");
    let primary_activation_output_sum = family
        .iter()
        .map(|entry| i64::from(entry.primary_activation_output))
        .sum::<i64>();
    let secondary_activation_output_sum = family
        .iter()
        .map(|entry| i64::from(entry.secondary_activation_output))
        .sum::<i64>();
    let folded_richer_family_accumulator_commitment =
        commit_phase98_folded_richer_family_accumulator(
            &richer_family_template_commitment,
            &richer_slice_commitment_sequence_commitment,
            &selected_memory_window_family_commitment,
            &invariant_summary_family_commitment,
            &folded.global_start_boundary_commitment,
            &folded.global_end_boundary_commitment,
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            primary_norm_sq_min,
            primary_norm_sq_max,
            secondary_norm_sq_min,
            secondary_norm_sq_max,
            primary_activation_output_sum,
            secondary_activation_output_sum,
        )?;
    let artifact_commitment = commit_phase98_folded_gemma_richer_slice_family_artifact(
        source,
        folded,
        &richer_family_template_commitment,
        &richer_slice_commitment_sequence_commitment,
        &selected_memory_window_family_commitment,
        &invariant_summary_family_commitment,
        &folded_richer_family_accumulator_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
    )?;

    Ok(Phase98FoldedGemmaRicherSliceFamilyArtifact {
        artifact_version: STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_VERSION_PHASE98
            .to_string(),
        semantic_scope: STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_SCOPE_PHASE98.to_string(),
        artifact_commitment,
        program_label: source.program_label.clone(),
        source_phase95_artifact_commitment: source.artifact_commitment.clone(),
        source_phase965_artifact_commitment: folded.artifact_commitment.clone(),
        shared_table_registry_commitment: source.shared_table_registry_commitment.clone(),
        total_slices: source.total_slices,
        repeated_token_position: source.repeated_token_position,
        start_block_index: source.start_block_index,
        terminal_block_index: source.terminal_block_index,
        total_folded_groups: folded.total_folded_groups,
        bounded_fold_arity: folded.bounded_fold_arity,
        global_start_boundary_commitment: folded.global_start_boundary_commitment.clone(),
        global_end_boundary_commitment: folded.global_end_boundary_commitment.clone(),
        first_richer_slice_artifact_commitment: first.richer_slice_artifact_commitment.clone(),
        terminal_richer_slice_artifact_commitment: last.richer_slice_artifact_commitment.clone(),
        richer_family_template_commitment,
        richer_slice_commitment_sequence_commitment,
        selected_memory_window_family_commitment,
        invariant_summary_family_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
        folded_richer_family_accumulator_commitment,
    })
}

pub fn verify_phase98_folded_gemma_richer_slice_family_artifact(
    artifact: &Phase98FoldedGemmaRicherSliceFamilyArtifact,
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    folded: &Phase965FoldedGemmaSliceAccumulationArtifact,
) -> Result<()> {
    validate_phase98_folded_gemma_richer_slice_family_artifact_shallow(artifact)?;
    verify_phase965_folded_gemma_slice_accumulation_artifact(folded, source)?;

    if artifact.program_label != source.program_label {
        return Err(VmError::InvalidConfig(
            "Phase 98 program_label does not match the source Phase 95 artifact".to_string(),
        ));
    }
    if artifact.source_phase95_artifact_commitment != source.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 source_phase95_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.source_phase965_artifact_commitment != folded.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 source_phase965_artifact_commitment does not match the folded source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment != source.shared_table_registry_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 shared_table_registry_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.total_slices != source.total_slices
        || artifact.repeated_token_position != source.repeated_token_position
        || artifact.start_block_index != source.start_block_index
        || artifact.terminal_block_index != source.terminal_block_index
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 interval metadata does not match the source Phase 95 artifact".to_string(),
        ));
    }
    if artifact.total_folded_groups != folded.total_folded_groups
        || artifact.bounded_fold_arity != folded.bounded_fold_arity
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 folded-group metadata does not match the Phase 96.5 source artifact"
                .to_string(),
        ));
    }
    if artifact.global_start_boundary_commitment != folded.global_start_boundary_commitment
        || artifact.global_end_boundary_commitment != folded.global_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 global boundary commitments do not match the Phase 96.5 source artifact"
                .to_string(),
        ));
    }

    let family = canonical_phase98_richer_slice_family(source)?;
    let first = family.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 98 folded Gemma richer slice family requires at least one richer slice"
                .to_string(),
        )
    })?;
    let last = family
        .last()
        .expect("richer slice family is non-empty after first check");
    if artifact.first_richer_slice_artifact_commitment != first.richer_slice_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 first_richer_slice_artifact_commitment does not match the canonical richer slice family"
                .to_string(),
        ));
    }
    if artifact.terminal_richer_slice_artifact_commitment != last.richer_slice_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 terminal_richer_slice_artifact_commitment does not match the canonical richer slice family"
                .to_string(),
        ));
    }

    let expected_richer_slice_commitment_sequence_commitment =
        commit_phase98_richer_slice_sequence(&family)?;
    if artifact.richer_slice_commitment_sequence_commitment
        != expected_richer_slice_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 richer_slice_commitment_sequence_commitment does not match the canonical richer slice family"
                .to_string(),
        ));
    }
    let expected_selected_memory_window_family_commitment =
        commit_phase98_selected_memory_window_family(&family)?;
    if artifact.selected_memory_window_family_commitment
        != expected_selected_memory_window_family_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 selected_memory_window_family_commitment does not match the canonical richer slice family"
                .to_string(),
        ));
    }
    let expected_invariant_summary_family_commitment =
        commit_phase98_invariant_summary_family(&family)?;
    if artifact.invariant_summary_family_commitment != expected_invariant_summary_family_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 invariant_summary_family_commitment does not match the canonical richer slice family"
                .to_string(),
        ));
    }
    let expected_richer_family_template_commitment = commit_phase98_richer_family_template(
        &source.artifact_commitment,
        &folded.artifact_commitment,
        &source.shared_table_registry_commitment,
        source.total_slices,
        folded.total_folded_groups,
        folded.bounded_fold_arity,
        source.repeated_token_position,
        source.start_block_index,
        source.terminal_block_index,
    )?;
    if artifact.richer_family_template_commitment != expected_richer_family_template_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 richer_family_template_commitment does not match the canonical family template"
                .to_string(),
        ));
    }

    let expected_local_score_sum = family
        .iter()
        .map(|entry| i64::from(entry.local_score))
        .sum::<i64>();
    let expected_global_score_sum = family
        .iter()
        .map(|entry| i64::from(entry.global_score))
        .sum::<i64>();
    let expected_grouped_value_mix_sum = family
        .iter()
        .map(|entry| i64::from(entry.grouped_value_mix))
        .sum::<i64>();
    let expected_residual_output_sum = family
        .iter()
        .map(|entry| i64::from(entry.residual_output))
        .sum::<i64>();
    let expected_final_acc_sum = family.iter().map(|entry| entry.final_acc).sum::<i64>();
    let expected_primary_norm_sq_min = family
        .iter()
        .map(|entry| entry.primary_norm_sq)
        .min()
        .expect("family is non-empty");
    let expected_primary_norm_sq_max = family
        .iter()
        .map(|entry| entry.primary_norm_sq)
        .max()
        .expect("family is non-empty");
    let expected_secondary_norm_sq_min = family
        .iter()
        .map(|entry| entry.secondary_norm_sq)
        .min()
        .expect("family is non-empty");
    let expected_secondary_norm_sq_max = family
        .iter()
        .map(|entry| entry.secondary_norm_sq)
        .max()
        .expect("family is non-empty");
    let expected_primary_activation_output_sum = family
        .iter()
        .map(|entry| i64::from(entry.primary_activation_output))
        .sum::<i64>();
    let expected_secondary_activation_output_sum = family
        .iter()
        .map(|entry| i64::from(entry.secondary_activation_output))
        .sum::<i64>();

    if artifact.local_score_sum != expected_local_score_sum
        || artifact.global_score_sum != expected_global_score_sum
        || artifact.grouped_value_mix_sum != expected_grouped_value_mix_sum
        || artifact.residual_output_sum != expected_residual_output_sum
        || artifact.final_acc_sum != expected_final_acc_sum
        || artifact.primary_norm_sq_min != expected_primary_norm_sq_min
        || artifact.primary_norm_sq_max != expected_primary_norm_sq_max
        || artifact.secondary_norm_sq_min != expected_secondary_norm_sq_min
        || artifact.secondary_norm_sq_max != expected_secondary_norm_sq_max
        || artifact.primary_activation_output_sum != expected_primary_activation_output_sum
        || artifact.secondary_activation_output_sum != expected_secondary_activation_output_sum
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 richer-family summaries do not match the canonical richer slice family"
                .to_string(),
        ));
    }

    let expected_folded_richer_family_accumulator_commitment =
        commit_phase98_folded_richer_family_accumulator(
            &artifact.richer_family_template_commitment,
            &artifact.richer_slice_commitment_sequence_commitment,
            &artifact.selected_memory_window_family_commitment,
            &artifact.invariant_summary_family_commitment,
            &artifact.global_start_boundary_commitment,
            &artifact.global_end_boundary_commitment,
            artifact.local_score_sum,
            artifact.global_score_sum,
            artifact.grouped_value_mix_sum,
            artifact.residual_output_sum,
            artifact.final_acc_sum,
            artifact.primary_norm_sq_min,
            artifact.primary_norm_sq_max,
            artifact.secondary_norm_sq_min,
            artifact.secondary_norm_sq_max,
            artifact.primary_activation_output_sum,
            artifact.secondary_activation_output_sum,
        )?;
    if artifact.folded_richer_family_accumulator_commitment
        != expected_folded_richer_family_accumulator_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 98 folded_richer_family_accumulator_commitment does not match the canonical richer slice family"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase98_folded_gemma_richer_slice_family_artifact(
        source,
        folded,
        &artifact.richer_family_template_commitment,
        &artifact.richer_slice_commitment_sequence_commitment,
        &artifact.selected_memory_window_family_commitment,
        &artifact.invariant_summary_family_commitment,
        &artifact.folded_richer_family_accumulator_commitment,
        artifact.local_score_sum,
        artifact.global_score_sum,
        artifact.grouped_value_mix_sum,
        artifact.residual_output_sum,
        artifact.final_acc_sum,
        artifact.primary_norm_sq_min,
        artifact.primary_norm_sq_max,
        artifact.secondary_norm_sq_min,
        artifact.secondary_norm_sq_max,
        artifact.primary_activation_output_sum,
        artifact.secondary_activation_output_sum,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 98 folded Gemma richer slice family artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase98_folded_gemma_richer_slice_family_artifact(
    artifact: &Phase98FoldedGemmaRicherSliceFamilyArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE98_FOLDED_GEMMA_RICHER_SLICE_FAMILY_JSON_BYTES,
        "Phase 98 folded Gemma richer slice family artifact",
    )
}

pub fn load_phase98_folded_gemma_richer_slice_family_artifact(
    path: &Path,
) -> Result<Phase98FoldedGemmaRicherSliceFamilyArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE98_FOLDED_GEMMA_RICHER_SLICE_FAMILY_JSON_BYTES,
        "Phase 98 folded Gemma richer slice family artifact",
    )?;
    let artifact: Phase98FoldedGemmaRicherSliceFamilyArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_phase98_folded_gemma_richer_slice_family_artifact_shallow(&artifact)?;
    Ok(artifact)
}

fn validate_phase99_total_intervals(total_intervals: usize) -> Result<u64> {
    if total_intervals < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 99 multi-interval richer-family accumulation requires at least two intervals"
                .to_string(),
        ));
    }
    if total_intervals > MAX_PHASE99_MULTI_INTERVAL_TOTAL_INTERVALS {
        return Err(VmError::InvalidConfig(format!(
            "Phase 99 multi-interval richer-family accumulation supports at most {} intervals",
            MAX_PHASE99_MULTI_INTERVAL_TOTAL_INTERVALS
        )));
    }
    Ok(total_intervals as u64)
}

fn validate_phase99_token_position_stride(token_position_stride: u64) -> Result<()> {
    if token_position_stride == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 99 multi-interval richer-family accumulation requires token_position_stride >= 1"
                .to_string(),
        ));
    }
    Ok(())
}

fn checked_phase99_interval_token_position(
    token_position_start: u64,
    token_position_stride: u64,
    interval_index: usize,
) -> Result<u64> {
    validate_phase99_token_position_stride(token_position_stride)?;
    let offset = (interval_index as u64)
        .checked_mul(token_position_stride)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 99 token_position overflow while deriving interval members".to_string(),
            )
        })?;
    token_position_start.checked_add(offset).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 99 token_position overflow while deriving interval members".to_string(),
        )
    })
}

fn checked_phase99_terminal_token_position(
    token_position_start: u64,
    token_position_stride: u64,
    total_intervals_u64: u64,
) -> Result<u64> {
    validate_phase99_token_position_stride(token_position_stride)?;
    let last_offset = total_intervals_u64.checked_sub(1).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 99 multi-interval richer-family accumulation requires at least two intervals"
                .to_string(),
        )
    })?;
    let token_offset = last_offset
        .checked_mul(token_position_stride)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 99 terminal_token_position overflow while deriving the interval family"
                    .to_string(),
            )
        })?;
    token_position_start
        .checked_add(token_offset)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 99 terminal_token_position overflow while deriving the interval family"
                    .to_string(),
            )
        })
}

fn build_phase99_multi_interval_member(
    interval_index: usize,
    phase95: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    phase965: &Phase965FoldedGemmaSliceAccumulationArtifact,
    phase98: &Phase98FoldedGemmaRicherSliceFamilyArtifact,
) -> Result<Phase99MultiIntervalGemmaRicherFamilyMember> {
    verify_phase965_folded_gemma_slice_accumulation_artifact(phase965, phase95)?;
    verify_phase98_folded_gemma_richer_slice_family_artifact(phase98, phase95, phase965)?;
    let mut member = Phase99MultiIntervalGemmaRicherFamilyMember {
        interval_index,
        repeated_token_position: phase95.repeated_token_position,
        start_block_index: phase95.start_block_index,
        terminal_block_index: phase95.terminal_block_index,
        phase95_artifact_commitment: phase95.artifact_commitment.clone(),
        phase965_artifact_commitment: phase965.artifact_commitment.clone(),
        phase98_artifact_commitment: phase98.artifact_commitment.clone(),
        global_start_boundary_commitment: phase98.global_start_boundary_commitment.clone(),
        global_end_boundary_commitment: phase98.global_end_boundary_commitment.clone(),
        first_richer_slice_artifact_commitment: phase98
            .first_richer_slice_artifact_commitment
            .clone(),
        terminal_richer_slice_artifact_commitment: phase98
            .terminal_richer_slice_artifact_commitment
            .clone(),
        richer_slice_commitment_sequence_commitment: phase98
            .richer_slice_commitment_sequence_commitment
            .clone(),
        selected_memory_window_family_commitment: phase98
            .selected_memory_window_family_commitment
            .clone(),
        invariant_summary_family_commitment: phase98.invariant_summary_family_commitment.clone(),
        local_score_sum: phase98.local_score_sum,
        global_score_sum: phase98.global_score_sum,
        grouped_value_mix_sum: phase98.grouped_value_mix_sum,
        residual_output_sum: phase98.residual_output_sum,
        final_acc_sum: phase98.final_acc_sum,
        primary_norm_sq_min: phase98.primary_norm_sq_min,
        primary_norm_sq_max: phase98.primary_norm_sq_max,
        secondary_norm_sq_min: phase98.secondary_norm_sq_min,
        secondary_norm_sq_max: phase98.secondary_norm_sq_max,
        primary_activation_output_sum: phase98.primary_activation_output_sum,
        secondary_activation_output_sum: phase98.secondary_activation_output_sum,
        interval_member_commitment: String::new(),
    };
    member.interval_member_commitment = commit_phase99_multi_interval_member(&member)?;
    Ok(member)
}

fn validate_phase99_multi_interval_gemma_richer_family_accumulation_artifact_shallow(
    artifact: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
) -> Result<()> {
    if artifact.artifact_version
        != STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_VERSION_PHASE99
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 99 multi-interval richer-family accumulation artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope
        != STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_SCOPE_PHASE99
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 99 multi-interval richer-family accumulation artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 99 program label `{}`",
            artifact.program_label
        )));
    }
    validate_phase99_total_intervals(artifact.total_intervals)?;
    validate_phase95_total_slices(artifact.interval_total_slices)?;
    validate_phase99_token_position_stride(artifact.token_position_stride)?;
    if artifact.total_intervals != artifact.members.len() {
        return Err(VmError::InvalidConfig(
            "Phase 99 total_intervals does not match the interval member count".to_string(),
        ));
    }
    Ok(())
}

pub fn prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    total_intervals: usize,
    interval_total_slices: usize,
    token_position_start: u64,
    token_position_stride: u64,
    start_block_index: u64,
) -> Result<Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact> {
    verify_phase92_shared_normalization_primitive_artifact(shared_primitive_artifact)?;
    validate_phase945_gemma_execution_proof(shared_execution_proof)?;
    let total_intervals_u64 = validate_phase99_total_intervals(total_intervals)?;
    validate_phase95_total_slices(interval_total_slices)?;
    validate_phase99_token_position_stride(token_position_stride)?;
    let terminal_token_position = checked_phase99_terminal_token_position(
        token_position_start,
        token_position_stride,
        total_intervals_u64,
    )?;
    let terminal_block_index =
        checked_phase95_terminal_block_index(start_block_index, interval_total_slices as u64)?;
    let shared_execution_proof_commitment =
        commit_phase945_execution_proof(shared_execution_proof)?;

    let mut members = Vec::with_capacity(total_intervals);
    for interval_index in 0..total_intervals {
        let repeated_token_position = checked_phase99_interval_token_position(
            token_position_start,
            token_position_stride,
            interval_index,
        )?;
        let phase95 = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            shared_primitive_artifact,
            shared_execution_proof,
            interval_total_slices,
            repeated_token_position,
            start_block_index,
        )?;
        let phase965 = prepare_phase965_folded_gemma_slice_accumulation_artifact(&phase95)?;
        let phase98 =
            prepare_phase98_folded_gemma_richer_slice_family_artifact(&phase95, &phase965)?;
        members.push(build_phase99_multi_interval_member(
            interval_index,
            &phase95,
            &phase965,
            &phase98,
        )?);
    }

    let interval_members_commitment = commit_phase99_multi_interval_members(&members)?;
    let first_member = members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 99 multi-interval richer-family accumulation requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = members
        .last()
        .expect("members are non-empty after first check");
    let local_score_sum = members
        .iter()
        .map(|member| member.local_score_sum)
        .sum::<i64>();
    let global_score_sum = members
        .iter()
        .map(|member| member.global_score_sum)
        .sum::<i64>();
    let grouped_value_mix_sum = members
        .iter()
        .map(|member| member.grouped_value_mix_sum)
        .sum::<i64>();
    let residual_output_sum = members
        .iter()
        .map(|member| member.residual_output_sum)
        .sum::<i64>();
    let final_acc_sum = members
        .iter()
        .map(|member| member.final_acc_sum)
        .sum::<i64>();
    let primary_norm_sq_min = members
        .iter()
        .map(|member| member.primary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let primary_norm_sq_max = members
        .iter()
        .map(|member| member.primary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let secondary_norm_sq_min = members
        .iter()
        .map(|member| member.secondary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let secondary_norm_sq_max = members
        .iter()
        .map(|member| member.secondary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let primary_activation_output_sum = members
        .iter()
        .map(|member| member.primary_activation_output_sum)
        .sum::<i64>();
    let secondary_activation_output_sum = members
        .iter()
        .map(|member| member.secondary_activation_output_sum)
        .sum::<i64>();
    let artifact_commitment =
        commit_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            shared_primitive_artifact,
            shared_execution_proof,
            &shared_execution_proof_commitment,
            &interval_members_commitment,
            total_intervals,
            interval_total_slices,
            token_position_start,
            token_position_stride,
            start_block_index,
            terminal_token_position,
            terminal_block_index,
            &first_member.global_start_boundary_commitment,
            &last_member.global_end_boundary_commitment,
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            primary_norm_sq_min,
            primary_norm_sq_max,
            secondary_norm_sq_min,
            secondary_norm_sq_max,
            primary_activation_output_sum,
            secondary_activation_output_sum,
        )?;

    Ok(Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact {
        artifact_version:
            STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_VERSION_PHASE99
                .to_string(),
        semantic_scope: STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_SCOPE_PHASE99
            .to_string(),
        artifact_commitment,
        program_label: "gemma_block_v4".to_string(),
        shared_primitive_artifact_commitment: shared_primitive_artifact.artifact_commitment.clone(),
        shared_table_registry_commitment: shared_primitive_artifact
            .static_table_registry_commitment
            .clone(),
        shared_execution_proof_commitment,
        shared_execution_proof_backend_version: shared_execution_proof
            .proof_backend_version
            .clone(),
        shared_execution_statement_version: shared_execution_proof.claim.statement_version.clone(),
        total_intervals,
        interval_total_slices,
        token_position_start,
        token_position_stride,
        start_block_index,
        terminal_token_position,
        terminal_block_index,
        interval_members_commitment,
        global_interval_start_boundary_commitment: first_member
            .global_start_boundary_commitment
            .clone(),
        global_interval_end_boundary_commitment: last_member.global_end_boundary_commitment.clone(),
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
        shared_primitive_artifact: shared_primitive_artifact.clone(),
        shared_execution_proof: shared_execution_proof.clone(),
        members,
    })
}

pub fn verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
    artifact: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
) -> Result<()> {
    validate_phase99_multi_interval_gemma_richer_family_accumulation_artifact_shallow(artifact)?;
    verify_phase92_shared_normalization_primitive_artifact(&artifact.shared_primitive_artifact)?;
    if artifact.shared_primitive_artifact_commitment
        != artifact.shared_primitive_artifact.artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 shared_primitive_artifact_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment
        != artifact
            .shared_primitive_artifact
            .static_table_registry_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 shared_table_registry_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }
    validate_phase945_gemma_execution_proof(&artifact.shared_execution_proof)?;
    let expected_execution_proof_commitment =
        commit_phase945_execution_proof(&artifact.shared_execution_proof)?;
    if artifact.shared_execution_proof_commitment != expected_execution_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 99 shared_execution_proof_commitment does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_backend_version
        != artifact.shared_execution_proof.proof_backend_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 shared_execution_proof_backend_version does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.shared_execution_statement_version
        != artifact.shared_execution_proof.claim.statement_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 shared_execution_statement_version does not match the nested execution proof"
                .to_string(),
        ));
    }

    let total_intervals_u64 = validate_phase99_total_intervals(artifact.total_intervals)?;
    validate_phase95_total_slices(artifact.interval_total_slices)?;
    validate_phase99_token_position_stride(artifact.token_position_stride)?;
    let expected_terminal_token_position = checked_phase99_terminal_token_position(
        artifact.token_position_start,
        artifact.token_position_stride,
        total_intervals_u64,
    )?;
    if artifact.terminal_token_position != expected_terminal_token_position {
        return Err(VmError::InvalidConfig(
            "Phase 99 terminal_token_position does not match token_position_start + stride * (total_intervals - 1)"
                .to_string(),
        ));
    }
    let expected_terminal_block_index = checked_phase95_terminal_block_index(
        artifact.start_block_index,
        artifact.interval_total_slices as u64,
    )?;
    if artifact.terminal_block_index != expected_terminal_block_index {
        return Err(VmError::InvalidConfig(
            "Phase 99 terminal_block_index does not match start_block_index + interval_total_slices - 1"
                .to_string(),
        ));
    }

    for (expected_interval_index, member) in artifact.members.iter().enumerate() {
        if member.interval_index != expected_interval_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 99 expected contiguous interval_index {}, got {}",
                expected_interval_index, member.interval_index
            )));
        }
        let expected_token_position = checked_phase99_interval_token_position(
            artifact.token_position_start,
            artifact.token_position_stride,
            expected_interval_index,
        )?;
        let phase95 = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &artifact.shared_primitive_artifact,
            &artifact.shared_execution_proof,
            artifact.interval_total_slices,
            expected_token_position,
            artifact.start_block_index,
        )?;
        let phase965 = prepare_phase965_folded_gemma_slice_accumulation_artifact(&phase95)?;
        let phase98 =
            prepare_phase98_folded_gemma_richer_slice_family_artifact(&phase95, &phase965)?;
        let expected_member = build_phase99_multi_interval_member(
            expected_interval_index,
            &phase95,
            &phase965,
            &phase98,
        )?;
        if member != &expected_member {
            return Err(VmError::InvalidConfig(format!(
                "Phase 99 interval member {} does not match the canonical reconstructed richer-family interval",
                expected_interval_index
            )));
        }
    }

    let expected_interval_members_commitment =
        commit_phase99_multi_interval_members(&artifact.members)?;
    if artifact.interval_members_commitment != expected_interval_members_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 99 interval_members_commitment does not match the serialized interval members"
                .to_string(),
        ));
    }
    let first_member = artifact.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 99 multi-interval richer-family accumulation requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = artifact
        .members
        .last()
        .expect("members are non-empty after first check");
    if artifact.global_interval_start_boundary_commitment
        != first_member.global_start_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 global_interval_start_boundary_commitment does not match the first interval member"
                .to_string(),
        ));
    }
    if artifact.global_interval_end_boundary_commitment
        != last_member.global_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 global_interval_end_boundary_commitment does not match the terminal interval member"
                .to_string(),
        ));
    }

    let expected_local_score_sum = artifact
        .members
        .iter()
        .map(|member| member.local_score_sum)
        .sum::<i64>();
    let expected_global_score_sum = artifact
        .members
        .iter()
        .map(|member| member.global_score_sum)
        .sum::<i64>();
    let expected_grouped_value_mix_sum = artifact
        .members
        .iter()
        .map(|member| member.grouped_value_mix_sum)
        .sum::<i64>();
    let expected_residual_output_sum = artifact
        .members
        .iter()
        .map(|member| member.residual_output_sum)
        .sum::<i64>();
    let expected_final_acc_sum = artifact
        .members
        .iter()
        .map(|member| member.final_acc_sum)
        .sum::<i64>();
    let expected_primary_norm_sq_min = artifact
        .members
        .iter()
        .map(|member| member.primary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let expected_primary_norm_sq_max = artifact
        .members
        .iter()
        .map(|member| member.primary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let expected_secondary_norm_sq_min = artifact
        .members
        .iter()
        .map(|member| member.secondary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let expected_secondary_norm_sq_max = artifact
        .members
        .iter()
        .map(|member| member.secondary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let expected_primary_activation_output_sum = artifact
        .members
        .iter()
        .map(|member| member.primary_activation_output_sum)
        .sum::<i64>();
    let expected_secondary_activation_output_sum = artifact
        .members
        .iter()
        .map(|member| member.secondary_activation_output_sum)
        .sum::<i64>();
    if artifact.local_score_sum != expected_local_score_sum
        || artifact.global_score_sum != expected_global_score_sum
        || artifact.grouped_value_mix_sum != expected_grouped_value_mix_sum
        || artifact.residual_output_sum != expected_residual_output_sum
        || artifact.final_acc_sum != expected_final_acc_sum
        || artifact.primary_norm_sq_min != expected_primary_norm_sq_min
        || artifact.primary_norm_sq_max != expected_primary_norm_sq_max
        || artifact.secondary_norm_sq_min != expected_secondary_norm_sq_min
        || artifact.secondary_norm_sq_max != expected_secondary_norm_sq_max
        || artifact.primary_activation_output_sum != expected_primary_activation_output_sum
        || artifact.secondary_activation_output_sum != expected_secondary_activation_output_sum
    {
        return Err(VmError::InvalidConfig(
            "Phase 99 interval summaries do not match the serialized interval members".to_string(),
        ));
    }

    let expected_artifact_commitment =
        commit_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &artifact.shared_primitive_artifact,
            &artifact.shared_execution_proof,
            &artifact.shared_execution_proof_commitment,
            &artifact.interval_members_commitment,
            artifact.total_intervals,
            artifact.interval_total_slices,
            artifact.token_position_start,
            artifact.token_position_stride,
            artifact.start_block_index,
            artifact.terminal_token_position,
            artifact.terminal_block_index,
            &artifact.global_interval_start_boundary_commitment,
            &artifact.global_interval_end_boundary_commitment,
            artifact.local_score_sum,
            artifact.global_score_sum,
            artifact.grouped_value_mix_sum,
            artifact.residual_output_sum,
            artifact.final_acc_sum,
            artifact.primary_norm_sq_min,
            artifact.primary_norm_sq_max,
            artifact.secondary_norm_sq_min,
            artifact.secondary_norm_sq_max,
            artifact.primary_activation_output_sum,
            artifact.secondary_activation_output_sum,
        )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 99 multi-interval richer-family accumulation artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
    artifact: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE99_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_JSON_BYTES,
        "Phase 99 multi-interval richer-family accumulation artifact",
    )
}

pub fn load_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
    path: &Path,
) -> Result<Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE99_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_JSON_BYTES,
        "Phase 99 multi-interval richer-family accumulation artifact",
    )?;
    let artifact: Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact =
        serde_json::from_slice(&bytes)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(&artifact)?;
    Ok(artifact)
}

fn validate_phase1015_bounded_fold_arity(bounded_fold_arity: usize) -> Result<()> {
    if bounded_fold_arity < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 folded multi-interval prototype requires bounded_fold_arity >= 2"
                .to_string(),
        ));
    }
    Ok(())
}

fn canonical_phase1015_folded_groups(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    bounded_fold_arity: usize,
) -> Result<Vec<Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup>> {
    validate_phase1015_bounded_fold_arity(bounded_fold_arity)?;
    let mut folded_groups = Vec::new();
    for (folded_group_index, chunk) in source.members.chunks(bounded_fold_arity).enumerate() {
        let first = chunk.first().ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 101.5 folded multi-interval prototype encountered an empty interval chunk"
                    .to_string(),
            )
        })?;
        let last = chunk
            .last()
            .expect("non-empty interval chunk has a last member");
        let interval_member_commitments = chunk
            .iter()
            .map(|member| member.interval_member_commitment.clone())
            .collect::<Vec<_>>();
        let interval_phase98_commitments = chunk
            .iter()
            .map(|member| member.phase98_artifact_commitment.clone())
            .collect::<Vec<_>>();
        let interval_member_commitment_sequence_commitment = commit_namespace_strings(
            "phase1015/interval-member-commitment-sequence",
            &interval_member_commitments,
        )?;
        let interval_phase98_commitment_sequence_commitment = commit_namespace_strings(
            "phase1015/interval-phase98-commitment-sequence",
            &interval_phase98_commitments,
        )?;
        let local_score_sum = chunk
            .iter()
            .map(|member| member.local_score_sum)
            .sum::<i64>();
        let global_score_sum = chunk
            .iter()
            .map(|member| member.global_score_sum)
            .sum::<i64>();
        let grouped_value_mix_sum = chunk
            .iter()
            .map(|member| member.grouped_value_mix_sum)
            .sum::<i64>();
        let residual_output_sum = chunk
            .iter()
            .map(|member| member.residual_output_sum)
            .sum::<i64>();
        let final_acc_sum = chunk.iter().map(|member| member.final_acc_sum).sum::<i64>();
        let primary_norm_sq_min = chunk
            .iter()
            .map(|member| member.primary_norm_sq_min)
            .min()
            .expect("non-empty chunk");
        let primary_norm_sq_max = chunk
            .iter()
            .map(|member| member.primary_norm_sq_max)
            .max()
            .expect("non-empty chunk");
        let secondary_norm_sq_min = chunk
            .iter()
            .map(|member| member.secondary_norm_sq_min)
            .min()
            .expect("non-empty chunk");
        let secondary_norm_sq_max = chunk
            .iter()
            .map(|member| member.secondary_norm_sq_max)
            .max()
            .expect("non-empty chunk");
        let primary_activation_output_sum = chunk
            .iter()
            .map(|member| member.primary_activation_output_sum)
            .sum::<i64>();
        let secondary_activation_output_sum = chunk
            .iter()
            .map(|member| member.secondary_activation_output_sum)
            .sum::<i64>();
        let mut group = Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup {
            folded_group_index,
            start_interval_index: first.interval_index,
            terminal_interval_index: last.interval_index,
            start_token_position: first.repeated_token_position,
            terminal_token_position: last.repeated_token_position,
            first_phase98_artifact_commitment: first.phase98_artifact_commitment.clone(),
            terminal_phase98_artifact_commitment: last.phase98_artifact_commitment.clone(),
            global_start_boundary_commitment: first.global_start_boundary_commitment.clone(),
            global_end_boundary_commitment: last.global_end_boundary_commitment.clone(),
            interval_member_commitment_sequence_commitment,
            interval_phase98_commitment_sequence_commitment,
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            primary_norm_sq_min,
            primary_norm_sq_max,
            secondary_norm_sq_min,
            secondary_norm_sq_max,
            primary_activation_output_sum,
            secondary_activation_output_sum,
            folded_group_commitment: String::new(),
        };
        group.folded_group_commitment = commit_phase1015_folded_multi_interval_group(&group)?;
        folded_groups.push(group);
    }
    Ok(folded_groups)
}

fn validate_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact_shallow(
    artifact: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
) -> Result<()> {
    if artifact.artifact_version
        != STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_VERSION_PHASE1015
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 101.5 folded multi-interval prototype artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope
        != STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_SCOPE_PHASE1015
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 101.5 folded multi-interval prototype artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 101.5 program label `{}`",
            artifact.program_label
        )));
    }
    validate_phase99_total_intervals(artifact.total_intervals)?;
    validate_phase95_total_slices(artifact.interval_total_slices)?;
    validate_phase99_token_position_stride(artifact.token_position_stride)?;
    validate_phase1015_bounded_fold_arity(artifact.bounded_fold_arity)?;
    if artifact.total_folded_interval_groups != artifact.folded_groups.len() {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 total_folded_interval_groups does not match the folded group count"
                .to_string(),
        ));
    }
    if artifact.folded_groups.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 folded multi-interval prototype requires at least one folded group"
                .to_string(),
        ));
    }
    Ok(())
}

pub fn prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
) -> Result<Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact> {
    verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(source)?;
    let bounded_fold_arity = PHASE1015_DEFAULT_BOUNDED_FOLD_ARITY;
    let folded_groups = canonical_phase1015_folded_groups(source, bounded_fold_arity)?;
    let total_folded_interval_groups = folded_groups.len();
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 101.5 folded multi-interval prototype requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("members are non-empty after first check");
    let fold_template_commitment = commit_phase1015_fold_template(
        &source.artifact_commitment,
        &source.interval_members_commitment,
        &source.shared_primitive_artifact_commitment,
        &source.shared_table_registry_commitment,
        &source.shared_execution_proof_commitment,
        bounded_fold_arity,
        source.total_intervals,
        source.interval_total_slices,
        source.token_position_start,
        source.token_position_stride,
        source.start_block_index,
        source.terminal_token_position,
        source.terminal_block_index,
    )?;
    let folded_interval_group_sequence_commitment =
        commit_phase1015_folded_interval_group_sequence(&folded_groups)?;
    let accumulation_handoff_commitment = commit_phase1015_accumulation_handoff(
        source,
        &fold_template_commitment,
        &folded_interval_group_sequence_commitment,
        total_folded_interval_groups,
        bounded_fold_arity,
    )?;
    let folded_interval_prototype_accumulator_commitment =
        commit_phase1015_folded_interval_prototype_accumulator(
            &accumulation_handoff_commitment,
            &fold_template_commitment,
            &folded_interval_group_sequence_commitment,
            &first_member.global_start_boundary_commitment,
            &last_member.global_end_boundary_commitment,
            source.local_score_sum,
            source.global_score_sum,
            source.grouped_value_mix_sum,
            source.residual_output_sum,
            source.final_acc_sum,
            source.primary_norm_sq_min,
            source.primary_norm_sq_max,
            source.secondary_norm_sq_min,
            source.secondary_norm_sq_max,
            source.primary_activation_output_sum,
            source.secondary_activation_output_sum,
            total_folded_interval_groups,
        )?;
    let artifact_commitment =
        commit_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
            source,
            &folded_groups,
            &fold_template_commitment,
            &folded_interval_group_sequence_commitment,
            &accumulation_handoff_commitment,
            &folded_interval_prototype_accumulator_commitment,
            bounded_fold_arity,
        )?;

    Ok(
        Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact {
            artifact_version:
                STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_VERSION_PHASE1015
                    .to_string(),
            semantic_scope:
                STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_SCOPE_PHASE1015
                    .to_string(),
            artifact_commitment,
            program_label: source.program_label.clone(),
            source_phase99_artifact_commitment: source.artifact_commitment.clone(),
            source_interval_members_commitment: source.interval_members_commitment.clone(),
            shared_primitive_artifact_commitment: source
                .shared_primitive_artifact_commitment
                .clone(),
            shared_table_registry_commitment: source.shared_table_registry_commitment.clone(),
            shared_execution_proof_commitment: source.shared_execution_proof_commitment.clone(),
            shared_execution_proof_backend_version: source
                .shared_execution_proof_backend_version
                .clone(),
            shared_execution_statement_version: source.shared_execution_statement_version.clone(),
            total_intervals: source.total_intervals,
            interval_total_slices: source.interval_total_slices,
            token_position_start: source.token_position_start,
            token_position_stride: source.token_position_stride,
            start_block_index: source.start_block_index,
            terminal_token_position: source.terminal_token_position,
            terminal_block_index: source.terminal_block_index,
            bounded_fold_arity,
            total_folded_interval_groups,
            global_interval_start_boundary_commitment: first_member
                .global_start_boundary_commitment
                .clone(),
            global_interval_end_boundary_commitment: last_member
                .global_end_boundary_commitment
                .clone(),
            first_phase98_artifact_commitment: first_member.phase98_artifact_commitment.clone(),
            terminal_phase98_artifact_commitment: last_member.phase98_artifact_commitment.clone(),
            fold_template_commitment,
            folded_interval_group_sequence_commitment,
            local_score_sum: source.local_score_sum,
            global_score_sum: source.global_score_sum,
            grouped_value_mix_sum: source.grouped_value_mix_sum,
            residual_output_sum: source.residual_output_sum,
            final_acc_sum: source.final_acc_sum,
            primary_norm_sq_min: source.primary_norm_sq_min,
            primary_norm_sq_max: source.primary_norm_sq_max,
            secondary_norm_sq_min: source.secondary_norm_sq_min,
            secondary_norm_sq_max: source.secondary_norm_sq_max,
            primary_activation_output_sum: source.primary_activation_output_sum,
            secondary_activation_output_sum: source.secondary_activation_output_sum,
            accumulation_handoff_commitment,
            folded_interval_prototype_accumulator_commitment,
            folded_groups,
        },
    )
}

pub fn verify_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
    artifact: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
) -> Result<()> {
    validate_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact_shallow(
        artifact,
    )?;
    verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(source)?;

    if artifact.program_label != source.program_label {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 program_label does not match the source Phase 99 artifact".to_string(),
        ));
    }
    if artifact.source_phase99_artifact_commitment != source.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 source_phase99_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.source_interval_members_commitment != source.interval_members_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 source_interval_members_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_primitive_artifact_commitment != source.shared_primitive_artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 shared_primitive_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment != source.shared_table_registry_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 shared_table_registry_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_commitment != source.shared_execution_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 shared_execution_proof_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_backend_version
        != source.shared_execution_proof_backend_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 shared_execution_proof_backend_version does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.shared_execution_statement_version != source.shared_execution_statement_version {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 shared_execution_statement_version does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.total_intervals != source.total_intervals
        || artifact.interval_total_slices != source.interval_total_slices
        || artifact.token_position_start != source.token_position_start
        || artifact.token_position_stride != source.token_position_stride
        || artifact.start_block_index != source.start_block_index
        || artifact.terminal_token_position != source.terminal_token_position
        || artifact.terminal_block_index != source.terminal_block_index
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 interval metadata does not match the source Phase 99 artifact".to_string(),
        ));
    }

    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 101.5 folded multi-interval prototype requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("members are non-empty after first check");
    if artifact.global_interval_start_boundary_commitment
        != first_member.global_start_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 global_interval_start_boundary_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.global_interval_end_boundary_commitment
        != last_member.global_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 global_interval_end_boundary_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.first_phase98_artifact_commitment != first_member.phase98_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 first_phase98_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.terminal_phase98_artifact_commitment != last_member.phase98_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 terminal_phase98_artifact_commitment does not match the source artifact"
                .to_string(),
        ));
    }

    let expected_folded_groups =
        canonical_phase1015_folded_groups(source, artifact.bounded_fold_arity)?;
    if artifact.folded_groups != expected_folded_groups {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 folded_groups do not match the canonical source-derived interval groups"
                .to_string(),
        ));
    }

    let expected_fold_template_commitment = commit_phase1015_fold_template(
        &source.artifact_commitment,
        &source.interval_members_commitment,
        &source.shared_primitive_artifact_commitment,
        &source.shared_table_registry_commitment,
        &source.shared_execution_proof_commitment,
        artifact.bounded_fold_arity,
        source.total_intervals,
        source.interval_total_slices,
        source.token_position_start,
        source.token_position_stride,
        source.start_block_index,
        source.terminal_token_position,
        source.terminal_block_index,
    )?;
    if artifact.fold_template_commitment != expected_fold_template_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 fold_template_commitment does not match the canonical source-derived template"
                .to_string(),
        ));
    }

    let expected_folded_interval_group_sequence_commitment =
        commit_phase1015_folded_interval_group_sequence(&artifact.folded_groups)?;
    if artifact.folded_interval_group_sequence_commitment
        != expected_folded_interval_group_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 folded_interval_group_sequence_commitment does not match the serialized folded interval groups"
                .to_string(),
        ));
    }
    if artifact.local_score_sum != source.local_score_sum
        || artifact.global_score_sum != source.global_score_sum
        || artifact.grouped_value_mix_sum != source.grouped_value_mix_sum
        || artifact.residual_output_sum != source.residual_output_sum
        || artifact.final_acc_sum != source.final_acc_sum
        || artifact.primary_norm_sq_min != source.primary_norm_sq_min
        || artifact.primary_norm_sq_max != source.primary_norm_sq_max
        || artifact.secondary_norm_sq_min != source.secondary_norm_sq_min
        || artifact.secondary_norm_sq_max != source.secondary_norm_sq_max
        || artifact.primary_activation_output_sum != source.primary_activation_output_sum
        || artifact.secondary_activation_output_sum != source.secondary_activation_output_sum
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 accumulated summaries do not match the source Phase 99 artifact"
                .to_string(),
        ));
    }

    let expected_accumulation_handoff_commitment = commit_phase1015_accumulation_handoff(
        source,
        &artifact.fold_template_commitment,
        &artifact.folded_interval_group_sequence_commitment,
        artifact.total_folded_interval_groups,
        artifact.bounded_fold_arity,
    )?;
    if artifact.accumulation_handoff_commitment != expected_accumulation_handoff_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 accumulation_handoff_commitment does not match the canonical folded interval handoff"
                .to_string(),
        ));
    }

    let expected_folded_interval_prototype_accumulator_commitment =
        commit_phase1015_folded_interval_prototype_accumulator(
            &artifact.accumulation_handoff_commitment,
            &artifact.fold_template_commitment,
            &artifact.folded_interval_group_sequence_commitment,
            &artifact.global_interval_start_boundary_commitment,
            &artifact.global_interval_end_boundary_commitment,
            artifact.local_score_sum,
            artifact.global_score_sum,
            artifact.grouped_value_mix_sum,
            artifact.residual_output_sum,
            artifact.final_acc_sum,
            artifact.primary_norm_sq_min,
            artifact.primary_norm_sq_max,
            artifact.secondary_norm_sq_min,
            artifact.secondary_norm_sq_max,
            artifact.primary_activation_output_sum,
            artifact.secondary_activation_output_sum,
            artifact.total_folded_interval_groups,
        )?;
    if artifact.folded_interval_prototype_accumulator_commitment
        != expected_folded_interval_prototype_accumulator_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 folded_interval_prototype_accumulator_commitment does not match the serialized folded interval groups"
                .to_string(),
        ));
    }

    let expected_artifact_commitment =
        commit_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
            source,
            &artifact.folded_groups,
            &artifact.fold_template_commitment,
            &artifact.folded_interval_group_sequence_commitment,
            &artifact.accumulation_handoff_commitment,
            &artifact.folded_interval_prototype_accumulator_commitment,
            artifact.bounded_fold_arity,
        )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 101.5 folded multi-interval prototype artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
    artifact: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE1015_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_JSON_BYTES,
        "Phase 101.5 folded multi-interval Gemma accumulation prototype artifact",
    )
}

pub fn load_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
    path: &Path,
) -> Result<Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE1015_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_JSON_BYTES,
        "Phase 101.5 folded multi-interval Gemma accumulation prototype artifact",
    )?;
    let artifact: Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact =
        serde_json::from_slice(&bytes)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact_shallow(
        &artifact,
    )?;
    Ok(artifact)
}

fn canonical_phase102_folded_richer_groups(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    bounded_fold_arity: usize,
) -> Result<Vec<Phase102FoldedMultiIntervalGemmaRicherFamilyGroup>> {
    validate_phase1015_bounded_fold_arity(bounded_fold_arity)?;
    let mut folded_groups = Vec::new();
    for (folded_group_index, chunk) in source.members.chunks(bounded_fold_arity).enumerate() {
        let first = chunk.first().ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 102 folded richer family encountered an empty interval chunk".to_string(),
            )
        })?;
        let last = chunk
            .last()
            .expect("non-empty interval chunk has a last member");
        let interval_member_commitments = chunk
            .iter()
            .map(|member| member.interval_member_commitment.clone())
            .collect::<Vec<_>>();
        let interval_phase98_commitments = chunk
            .iter()
            .map(|member| member.phase98_artifact_commitment.clone())
            .collect::<Vec<_>>();
        let interval_token_positions = chunk
            .iter()
            .map(|member| member.repeated_token_position)
            .collect::<Vec<_>>();
        let richer_slice_family_commitments = chunk
            .iter()
            .map(|member| member.richer_slice_commitment_sequence_commitment.clone())
            .collect::<Vec<_>>();
        let selected_memory_window_family_commitments = chunk
            .iter()
            .map(|member| member.selected_memory_window_family_commitment.clone())
            .collect::<Vec<_>>();
        let invariant_summary_family_commitments = chunk
            .iter()
            .map(|member| member.invariant_summary_family_commitment.clone())
            .collect::<Vec<_>>();
        let interval_member_commitment_sequence_commitment = commit_namespace_strings(
            "phase102/interval-member-commitment-sequence",
            &interval_member_commitments,
        )?;
        let interval_phase98_commitment_sequence_commitment = commit_namespace_strings(
            "phase102/interval-phase98-commitment-sequence",
            &interval_phase98_commitments,
        )?;
        let interval_token_position_sequence_commitment = commit_namespace_u64s(
            "phase102/interval-token-position-sequence",
            &interval_token_positions,
        )?;
        let richer_slice_family_commitment_sequence_commitment = commit_namespace_strings(
            "phase102/richer-slice-family-commitment-sequence",
            &richer_slice_family_commitments,
        )?;
        let selected_memory_window_family_commitment_sequence_commitment =
            commit_namespace_strings(
                "phase102/selected-memory-window-family-commitment-sequence",
                &selected_memory_window_family_commitments,
            )?;
        let invariant_summary_family_commitment_sequence_commitment = commit_namespace_strings(
            "phase102/invariant-summary-family-commitment-sequence",
            &invariant_summary_family_commitments,
        )?;
        let local_score_sum = chunk
            .iter()
            .map(|member| member.local_score_sum)
            .sum::<i64>();
        let global_score_sum = chunk
            .iter()
            .map(|member| member.global_score_sum)
            .sum::<i64>();
        let grouped_value_mix_sum = chunk
            .iter()
            .map(|member| member.grouped_value_mix_sum)
            .sum::<i64>();
        let residual_output_sum = chunk
            .iter()
            .map(|member| member.residual_output_sum)
            .sum::<i64>();
        let final_acc_sum = chunk.iter().map(|member| member.final_acc_sum).sum::<i64>();
        let primary_norm_sq_min = chunk
            .iter()
            .map(|member| member.primary_norm_sq_min)
            .min()
            .expect("non-empty chunk");
        let primary_norm_sq_max = chunk
            .iter()
            .map(|member| member.primary_norm_sq_max)
            .max()
            .expect("non-empty chunk");
        let secondary_norm_sq_min = chunk
            .iter()
            .map(|member| member.secondary_norm_sq_min)
            .min()
            .expect("non-empty chunk");
        let secondary_norm_sq_max = chunk
            .iter()
            .map(|member| member.secondary_norm_sq_max)
            .max()
            .expect("non-empty chunk");
        let primary_activation_output_sum = chunk
            .iter()
            .map(|member| member.primary_activation_output_sum)
            .sum::<i64>();
        let secondary_activation_output_sum = chunk
            .iter()
            .map(|member| member.secondary_activation_output_sum)
            .sum::<i64>();
        let mut group = Phase102FoldedMultiIntervalGemmaRicherFamilyGroup {
            folded_group_index,
            start_interval_index: first.interval_index,
            terminal_interval_index: last.interval_index,
            start_token_position: first.repeated_token_position,
            terminal_token_position: last.repeated_token_position,
            first_phase98_artifact_commitment: first.phase98_artifact_commitment.clone(),
            terminal_phase98_artifact_commitment: last.phase98_artifact_commitment.clone(),
            global_start_boundary_commitment: first.global_start_boundary_commitment.clone(),
            global_end_boundary_commitment: last.global_end_boundary_commitment.clone(),
            interval_member_commitment_sequence_commitment,
            interval_phase98_commitment_sequence_commitment,
            interval_token_position_sequence_commitment,
            richer_slice_family_commitment_sequence_commitment,
            selected_memory_window_family_commitment_sequence_commitment,
            invariant_summary_family_commitment_sequence_commitment,
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            primary_norm_sq_min,
            primary_norm_sq_max,
            secondary_norm_sq_min,
            secondary_norm_sq_max,
            primary_activation_output_sum,
            secondary_activation_output_sum,
            folded_richer_group_commitment: String::new(),
        };
        group.folded_richer_group_commitment =
            commit_phase102_folded_multi_interval_richer_group(&group)?;
        folded_groups.push(group);
    }
    Ok(folded_groups)
}

fn validate_phase102_folded_multi_interval_gemma_richer_family_artifact_shallow(
    artifact: &Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact,
) -> Result<()> {
    if artifact.artifact_version
        != STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE102
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 102 folded richer-family artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope
        != STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE102
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 102 folded richer-family artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 102 program label `{}`",
            artifact.program_label
        )));
    }
    validate_phase99_total_intervals(artifact.total_intervals)?;
    validate_phase95_total_slices(artifact.interval_total_slices)?;
    validate_phase99_token_position_stride(artifact.token_position_stride)?;
    validate_phase1015_bounded_fold_arity(artifact.bounded_fold_arity)?;
    if artifact.total_folded_richer_groups != artifact.folded_groups.len() {
        return Err(VmError::InvalidConfig(
            "Phase 102 total_folded_richer_groups does not match the folded group count"
                .to_string(),
        ));
    }
    if artifact.folded_groups.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 102 folded richer-family artifact requires at least one folded group"
                .to_string(),
        ));
    }
    Ok(())
}

pub fn prepare_phase102_folded_multi_interval_gemma_richer_family_artifact(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    folded: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
) -> Result<Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact> {
    verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(source)?;
    verify_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(folded, source)?;
    let bounded_fold_arity = folded.bounded_fold_arity;
    let folded_groups = canonical_phase102_folded_richer_groups(source, bounded_fold_arity)?;
    let total_folded_richer_groups = folded_groups.len();
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 102 folded richer-family artifact requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("members are non-empty after first check");
    let phase98_commitments = source
        .members
        .iter()
        .map(|member| member.phase98_artifact_commitment.clone())
        .collect::<Vec<_>>();
    let token_positions = source
        .members
        .iter()
        .map(|member| member.repeated_token_position)
        .collect::<Vec<_>>();
    let richer_slice_family_commitments = source
        .members
        .iter()
        .map(|member| member.richer_slice_commitment_sequence_commitment.clone())
        .collect::<Vec<_>>();
    let selected_memory_window_family_commitments = source
        .members
        .iter()
        .map(|member| member.selected_memory_window_family_commitment.clone())
        .collect::<Vec<_>>();
    let invariant_summary_family_commitments = source
        .members
        .iter()
        .map(|member| member.invariant_summary_family_commitment.clone())
        .collect::<Vec<_>>();
    let phase98_commitment_sequence_commitment =
        commit_namespace_strings("phase102/phase98-commitment-sequence", &phase98_commitments)?;
    let token_position_sequence_commitment =
        commit_namespace_u64s("phase102/token-position-sequence", &token_positions)?;
    let richer_slice_family_commitment_sequence_commitment = commit_namespace_strings(
        "phase102/richer-slice-family-commitment-sequence",
        &richer_slice_family_commitments,
    )?;
    let selected_memory_window_family_commitment_sequence_commitment = commit_namespace_strings(
        "phase102/selected-memory-window-family-commitment-sequence",
        &selected_memory_window_family_commitments,
    )?;
    let invariant_summary_family_commitment_sequence_commitment = commit_namespace_strings(
        "phase102/invariant-summary-family-commitment-sequence",
        &invariant_summary_family_commitments,
    )?;
    let richer_fold_template_commitment = commit_phase102_richer_fold_template(
        &source.artifact_commitment,
        &folded.artifact_commitment,
        &source.interval_members_commitment,
        &source.shared_primitive_artifact_commitment,
        &source.shared_table_registry_commitment,
        &source.shared_execution_proof_commitment,
        bounded_fold_arity,
        source.total_intervals,
        source.interval_total_slices,
        source.token_position_start,
        source.token_position_stride,
        source.start_block_index,
        source.terminal_token_position,
        source.terminal_block_index,
    )?;
    let folded_richer_group_sequence_commitment =
        commit_phase102_folded_richer_group_sequence(&folded_groups)?;
    let folded_richer_multi_interval_family_accumulator_commitment =
        commit_phase102_folded_richer_multi_interval_family_accumulator(
            &folded.accumulation_handoff_commitment,
            &folded.folded_interval_prototype_accumulator_commitment,
            &richer_fold_template_commitment,
            &folded_richer_group_sequence_commitment,
            &phase98_commitment_sequence_commitment,
            &token_position_sequence_commitment,
            &richer_slice_family_commitment_sequence_commitment,
            &selected_memory_window_family_commitment_sequence_commitment,
            &invariant_summary_family_commitment_sequence_commitment,
            &first_member.global_start_boundary_commitment,
            &last_member.global_end_boundary_commitment,
            source.local_score_sum,
            source.global_score_sum,
            source.grouped_value_mix_sum,
            source.residual_output_sum,
            source.final_acc_sum,
            source.primary_norm_sq_min,
            source.primary_norm_sq_max,
            source.secondary_norm_sq_min,
            source.secondary_norm_sq_max,
            source.primary_activation_output_sum,
            source.secondary_activation_output_sum,
            total_folded_richer_groups,
        )?;
    let artifact_commitment = commit_phase102_folded_multi_interval_gemma_richer_family_artifact(
        source,
        folded,
        &folded_groups,
        &richer_fold_template_commitment,
        &folded_richer_group_sequence_commitment,
        &phase98_commitment_sequence_commitment,
        &token_position_sequence_commitment,
        &richer_slice_family_commitment_sequence_commitment,
        &selected_memory_window_family_commitment_sequence_commitment,
        &invariant_summary_family_commitment_sequence_commitment,
        &folded_richer_multi_interval_family_accumulator_commitment,
    )?;

    Ok(Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact {
        artifact_version: STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE102
            .to_string(),
        semantic_scope: STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE102
            .to_string(),
        artifact_commitment,
        program_label: source.program_label.clone(),
        source_phase99_artifact_commitment: source.artifact_commitment.clone(),
        source_phase1015_artifact_commitment: folded.artifact_commitment.clone(),
        source_interval_members_commitment: source.interval_members_commitment.clone(),
        shared_primitive_artifact_commitment: source.shared_primitive_artifact_commitment.clone(),
        shared_table_registry_commitment: source.shared_table_registry_commitment.clone(),
        shared_execution_proof_commitment: source.shared_execution_proof_commitment.clone(),
        shared_execution_proof_backend_version: source
            .shared_execution_proof_backend_version
            .clone(),
        shared_execution_statement_version: source.shared_execution_statement_version.clone(),
        total_intervals: source.total_intervals,
        interval_total_slices: source.interval_total_slices,
        token_position_start: source.token_position_start,
        token_position_stride: source.token_position_stride,
        start_block_index: source.start_block_index,
        terminal_token_position: source.terminal_token_position,
        terminal_block_index: source.terminal_block_index,
        bounded_fold_arity,
        total_folded_richer_groups,
        global_interval_start_boundary_commitment: first_member
            .global_start_boundary_commitment
            .clone(),
        global_interval_end_boundary_commitment: last_member.global_end_boundary_commitment.clone(),
        first_phase98_artifact_commitment: first_member.phase98_artifact_commitment.clone(),
        terminal_phase98_artifact_commitment: last_member.phase98_artifact_commitment.clone(),
        richer_fold_template_commitment,
        folded_richer_group_sequence_commitment,
        phase98_commitment_sequence_commitment,
        token_position_sequence_commitment,
        richer_slice_family_commitment_sequence_commitment,
        selected_memory_window_family_commitment_sequence_commitment,
        invariant_summary_family_commitment_sequence_commitment,
        local_score_sum: source.local_score_sum,
        global_score_sum: source.global_score_sum,
        grouped_value_mix_sum: source.grouped_value_mix_sum,
        residual_output_sum: source.residual_output_sum,
        final_acc_sum: source.final_acc_sum,
        primary_norm_sq_min: source.primary_norm_sq_min,
        primary_norm_sq_max: source.primary_norm_sq_max,
        secondary_norm_sq_min: source.secondary_norm_sq_min,
        secondary_norm_sq_max: source.secondary_norm_sq_max,
        primary_activation_output_sum: source.primary_activation_output_sum,
        secondary_activation_output_sum: source.secondary_activation_output_sum,
        accumulation_handoff_commitment: folded.accumulation_handoff_commitment.clone(),
        folded_interval_prototype_accumulator_commitment: folded
            .folded_interval_prototype_accumulator_commitment
            .clone(),
        folded_richer_multi_interval_family_accumulator_commitment,
        folded_groups,
    })
}

pub fn verify_phase102_folded_multi_interval_gemma_richer_family_artifact(
    artifact: &Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact,
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    folded: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
) -> Result<()> {
    validate_phase102_folded_multi_interval_gemma_richer_family_artifact_shallow(artifact)?;
    verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(source)?;
    verify_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(folded, source)?;

    if artifact.program_label != source.program_label
        || artifact.program_label != folded.program_label
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 program_label does not match the source artifacts".to_string(),
        ));
    }
    if artifact.source_phase99_artifact_commitment != source.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 source_phase99_artifact_commitment does not match the source Phase 99 artifact"
                .to_string(),
        ));
    }
    if artifact.source_phase1015_artifact_commitment != folded.artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 source_phase1015_artifact_commitment does not match the source Phase 101.5 artifact"
                .to_string(),
        ));
    }
    if artifact.source_interval_members_commitment != source.interval_members_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 source_interval_members_commitment does not match the source Phase 99 artifact"
                .to_string(),
        ));
    }
    if artifact.shared_primitive_artifact_commitment != source.shared_primitive_artifact_commitment
        || artifact.shared_table_registry_commitment != source.shared_table_registry_commitment
        || artifact.shared_execution_proof_commitment != source.shared_execution_proof_commitment
        || artifact.shared_execution_proof_backend_version
            != source.shared_execution_proof_backend_version
        || artifact.shared_execution_statement_version != source.shared_execution_statement_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 shared commitments do not match the source Phase 99 artifact".to_string(),
        ));
    }
    if artifact.total_intervals != source.total_intervals
        || artifact.interval_total_slices != source.interval_total_slices
        || artifact.token_position_start != source.token_position_start
        || artifact.token_position_stride != source.token_position_stride
        || artifact.start_block_index != source.start_block_index
        || artifact.terminal_token_position != source.terminal_token_position
        || artifact.terminal_block_index != source.terminal_block_index
        || artifact.bounded_fold_arity != folded.bounded_fold_arity
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 interval metadata does not match the source artifacts".to_string(),
        ));
    }

    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 102 folded richer-family artifact requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("members are non-empty after first check");
    if artifact.global_interval_start_boundary_commitment
        != first_member.global_start_boundary_commitment
        || artifact.global_interval_end_boundary_commitment
            != last_member.global_end_boundary_commitment
        || artifact.first_phase98_artifact_commitment != first_member.phase98_artifact_commitment
        || artifact.terminal_phase98_artifact_commitment != last_member.phase98_artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 boundary or Phase 98 edge commitments do not match the source artifact"
                .to_string(),
        ));
    }
    if artifact.accumulation_handoff_commitment != folded.accumulation_handoff_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 accumulation_handoff_commitment does not match the source Phase 101.5 artifact"
                .to_string(),
        ));
    }
    if artifact.folded_interval_prototype_accumulator_commitment
        != folded.folded_interval_prototype_accumulator_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 folded_interval_prototype_accumulator_commitment does not match the source Phase 101.5 artifact"
                .to_string(),
        ));
    }

    let expected_folded_groups =
        canonical_phase102_folded_richer_groups(source, artifact.bounded_fold_arity)?;
    if artifact.folded_groups != expected_folded_groups {
        return Err(VmError::InvalidConfig(
            "Phase 102 folded_groups do not match the canonical richer-family groups".to_string(),
        ));
    }

    let phase98_commitments = source
        .members
        .iter()
        .map(|member| member.phase98_artifact_commitment.clone())
        .collect::<Vec<_>>();
    let token_positions = source
        .members
        .iter()
        .map(|member| member.repeated_token_position)
        .collect::<Vec<_>>();
    let richer_slice_family_commitments = source
        .members
        .iter()
        .map(|member| member.richer_slice_commitment_sequence_commitment.clone())
        .collect::<Vec<_>>();
    let selected_memory_window_family_commitments = source
        .members
        .iter()
        .map(|member| member.selected_memory_window_family_commitment.clone())
        .collect::<Vec<_>>();
    let invariant_summary_family_commitments = source
        .members
        .iter()
        .map(|member| member.invariant_summary_family_commitment.clone())
        .collect::<Vec<_>>();
    let expected_phase98_commitment_sequence_commitment =
        commit_namespace_strings("phase102/phase98-commitment-sequence", &phase98_commitments)?;
    if artifact.phase98_commitment_sequence_commitment
        != expected_phase98_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 phase98_commitment_sequence_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    let expected_token_position_sequence_commitment =
        commit_namespace_u64s("phase102/token-position-sequence", &token_positions)?;
    if artifact.token_position_sequence_commitment != expected_token_position_sequence_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 token_position_sequence_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    let expected_richer_slice_family_commitment_sequence_commitment = commit_namespace_strings(
        "phase102/richer-slice-family-commitment-sequence",
        &richer_slice_family_commitments,
    )?;
    if artifact.richer_slice_family_commitment_sequence_commitment
        != expected_richer_slice_family_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 richer_slice_family_commitment_sequence_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    let expected_selected_memory_window_family_commitment_sequence_commitment =
        commit_namespace_strings(
            "phase102/selected-memory-window-family-commitment-sequence",
            &selected_memory_window_family_commitments,
        )?;
    if artifact.selected_memory_window_family_commitment_sequence_commitment
        != expected_selected_memory_window_family_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 selected_memory_window_family_commitment_sequence_commitment does not match the source artifact"
                .to_string(),
        ));
    }
    let expected_invariant_summary_family_commitment_sequence_commitment =
        commit_namespace_strings(
            "phase102/invariant-summary-family-commitment-sequence",
            &invariant_summary_family_commitments,
        )?;
    if artifact.invariant_summary_family_commitment_sequence_commitment
        != expected_invariant_summary_family_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 invariant_summary_family_commitment_sequence_commitment does not match the source artifact"
                .to_string(),
        ));
    }

    if artifact.local_score_sum != source.local_score_sum
        || artifact.global_score_sum != source.global_score_sum
        || artifact.grouped_value_mix_sum != source.grouped_value_mix_sum
        || artifact.residual_output_sum != source.residual_output_sum
        || artifact.final_acc_sum != source.final_acc_sum
        || artifact.primary_norm_sq_min != source.primary_norm_sq_min
        || artifact.primary_norm_sq_max != source.primary_norm_sq_max
        || artifact.secondary_norm_sq_min != source.secondary_norm_sq_min
        || artifact.secondary_norm_sq_max != source.secondary_norm_sq_max
        || artifact.primary_activation_output_sum != source.primary_activation_output_sum
        || artifact.secondary_activation_output_sum != source.secondary_activation_output_sum
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 accumulated summaries do not match the source Phase 99 artifact".to_string(),
        ));
    }

    let expected_richer_fold_template_commitment = commit_phase102_richer_fold_template(
        &source.artifact_commitment,
        &folded.artifact_commitment,
        &source.interval_members_commitment,
        &source.shared_primitive_artifact_commitment,
        &source.shared_table_registry_commitment,
        &source.shared_execution_proof_commitment,
        artifact.bounded_fold_arity,
        source.total_intervals,
        source.interval_total_slices,
        source.token_position_start,
        source.token_position_stride,
        source.start_block_index,
        source.terminal_token_position,
        source.terminal_block_index,
    )?;
    if artifact.richer_fold_template_commitment != expected_richer_fold_template_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 richer_fold_template_commitment does not match the canonical template"
                .to_string(),
        ));
    }
    let expected_folded_richer_group_sequence_commitment =
        commit_phase102_folded_richer_group_sequence(&artifact.folded_groups)?;
    if artifact.folded_richer_group_sequence_commitment
        != expected_folded_richer_group_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 folded_richer_group_sequence_commitment does not match the serialized folded groups"
                .to_string(),
        ));
    }
    let expected_folded_richer_multi_interval_family_accumulator_commitment =
        commit_phase102_folded_richer_multi_interval_family_accumulator(
            &artifact.accumulation_handoff_commitment,
            &artifact.folded_interval_prototype_accumulator_commitment,
            &artifact.richer_fold_template_commitment,
            &artifact.folded_richer_group_sequence_commitment,
            &artifact.phase98_commitment_sequence_commitment,
            &artifact.token_position_sequence_commitment,
            &artifact.richer_slice_family_commitment_sequence_commitment,
            &artifact.selected_memory_window_family_commitment_sequence_commitment,
            &artifact.invariant_summary_family_commitment_sequence_commitment,
            &artifact.global_interval_start_boundary_commitment,
            &artifact.global_interval_end_boundary_commitment,
            artifact.local_score_sum,
            artifact.global_score_sum,
            artifact.grouped_value_mix_sum,
            artifact.residual_output_sum,
            artifact.final_acc_sum,
            artifact.primary_norm_sq_min,
            artifact.primary_norm_sq_max,
            artifact.secondary_norm_sq_min,
            artifact.secondary_norm_sq_max,
            artifact.primary_activation_output_sum,
            artifact.secondary_activation_output_sum,
            artifact.total_folded_richer_groups,
        )?;
    if artifact.folded_richer_multi_interval_family_accumulator_commitment
        != expected_folded_richer_multi_interval_family_accumulator_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 102 folded_richer_multi_interval_family_accumulator_commitment does not match the serialized richer-family surface"
                .to_string(),
        ));
    }
    let expected_artifact_commitment =
        commit_phase102_folded_multi_interval_gemma_richer_family_artifact(
            source,
            folded,
            &artifact.folded_groups,
            &artifact.richer_fold_template_commitment,
            &artifact.folded_richer_group_sequence_commitment,
            &artifact.phase98_commitment_sequence_commitment,
            &artifact.token_position_sequence_commitment,
            &artifact.richer_slice_family_commitment_sequence_commitment,
            &artifact.selected_memory_window_family_commitment_sequence_commitment,
            &artifact.invariant_summary_family_commitment_sequence_commitment,
            &artifact.folded_richer_multi_interval_family_accumulator_commitment,
        )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 102 folded richer-family artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }
    Ok(())
}

pub fn save_phase102_folded_multi_interval_gemma_richer_family_artifact(
    artifact: &Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE102_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_JSON_BYTES,
        "Phase 102 folded multi-interval Gemma richer-family artifact",
    )
}

pub fn load_phase102_folded_multi_interval_gemma_richer_family_artifact(
    path: &Path,
) -> Result<Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE102_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_JSON_BYTES,
        "Phase 102 folded multi-interval Gemma richer-family artifact",
    )?;
    let artifact: Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact =
        serde_json::from_slice(&bytes)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_phase102_folded_multi_interval_gemma_richer_family_artifact_shallow(&artifact)?;
    Ok(artifact)
}

fn validate_phase105_total_windows(total_windows: usize) -> Result<u64> {
    if total_windows < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 105 repeated multi-interval richer-family accumulation requires at least two windows"
                .to_string(),
        ));
    }
    if total_windows > MAX_PHASE105_REPEATED_MULTI_INTERVAL_TOTAL_WINDOWS {
        return Err(VmError::InvalidConfig(format!(
            "Phase 105 repeated multi-interval richer-family accumulation supports at most {} windows",
            MAX_PHASE105_REPEATED_MULTI_INTERVAL_TOTAL_WINDOWS
        )));
    }
    Ok(total_windows as u64)
}

fn checked_phase105_window_token_position_stride(
    intervals_per_window: usize,
    token_position_stride: u64,
) -> Result<u64> {
    validate_phase99_total_intervals(intervals_per_window)?;
    validate_phase99_token_position_stride(token_position_stride)?;
    (intervals_per_window as u64)
        .checked_mul(token_position_stride)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 105 window token-position stride overflow while deriving repeated windows"
                    .to_string(),
            )
        })
}

fn checked_phase105_window_token_position_start(
    token_position_start: u64,
    token_position_stride: u64,
    intervals_per_window: usize,
    window_index: usize,
) -> Result<u64> {
    let window_token_position_stride =
        checked_phase105_window_token_position_stride(intervals_per_window, token_position_stride)?;
    let offset = (window_index as u64)
        .checked_mul(window_token_position_stride)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 105 token_position overflow while deriving repeated windows".to_string(),
            )
        })?;
    token_position_start.checked_add(offset).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 105 token_position overflow while deriving repeated windows".to_string(),
        )
    })
}

fn checked_phase105_terminal_token_position(
    token_position_start: u64,
    token_position_stride: u64,
    total_windows: usize,
    intervals_per_window: usize,
) -> Result<u64> {
    let total_windows_u64 = validate_phase105_total_windows(total_windows)?;
    let intervals_per_window_u64 = validate_phase99_total_intervals(intervals_per_window)?;
    validate_phase99_token_position_stride(token_position_stride)?;
    let total_intervals = total_windows_u64
        .checked_mul(intervals_per_window_u64)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 105 total interval count overflow while deriving the repeated window family"
                    .to_string(),
            )
        })?;
    checked_phase99_terminal_token_position(
        token_position_start,
        token_position_stride,
        total_intervals,
    )
}

fn build_phase105_repeated_multi_interval_member(
    window_index: usize,
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    folded: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
    richer: &Phase102FoldedMultiIntervalGemmaRicherFamilyArtifact,
) -> Result<Phase105RepeatedMultiIntervalGemmaRicherFamilyMember> {
    verify_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(folded, source)?;
    verify_phase102_folded_multi_interval_gemma_richer_family_artifact(richer, source, folded)?;
    let mut member = Phase105RepeatedMultiIntervalGemmaRicherFamilyMember {
        window_index,
        total_intervals: source.total_intervals,
        bounded_fold_arity: richer.bounded_fold_arity,
        total_folded_richer_groups: richer.total_folded_richer_groups,
        token_position_start: source.token_position_start,
        token_position_stride: source.token_position_stride,
        terminal_token_position: source.terminal_token_position,
        start_block_index: source.start_block_index,
        terminal_block_index: source.terminal_block_index,
        source_phase99_artifact_commitment: source.artifact_commitment.clone(),
        source_phase1015_artifact_commitment: folded.artifact_commitment.clone(),
        source_phase102_artifact_commitment: richer.artifact_commitment.clone(),
        global_interval_start_boundary_commitment: richer
            .global_interval_start_boundary_commitment
            .clone(),
        global_interval_end_boundary_commitment: richer
            .global_interval_end_boundary_commitment
            .clone(),
        accumulation_handoff_commitment: folded.accumulation_handoff_commitment.clone(),
        folded_interval_prototype_accumulator_commitment: folded
            .folded_interval_prototype_accumulator_commitment
            .clone(),
        phase98_commitment_sequence_commitment: richer
            .phase98_commitment_sequence_commitment
            .clone(),
        token_position_sequence_commitment: richer.token_position_sequence_commitment.clone(),
        selected_memory_window_family_commitment_sequence_commitment: richer
            .selected_memory_window_family_commitment_sequence_commitment
            .clone(),
        invariant_summary_family_commitment_sequence_commitment: richer
            .invariant_summary_family_commitment_sequence_commitment
            .clone(),
        folded_richer_multi_interval_family_accumulator_commitment: richer
            .folded_richer_multi_interval_family_accumulator_commitment
            .clone(),
        local_score_sum: richer.local_score_sum,
        global_score_sum: richer.global_score_sum,
        grouped_value_mix_sum: richer.grouped_value_mix_sum,
        residual_output_sum: richer.residual_output_sum,
        final_acc_sum: richer.final_acc_sum,
        primary_norm_sq_min: richer.primary_norm_sq_min,
        primary_norm_sq_max: richer.primary_norm_sq_max,
        secondary_norm_sq_min: richer.secondary_norm_sq_min,
        secondary_norm_sq_max: richer.secondary_norm_sq_max,
        primary_activation_output_sum: richer.primary_activation_output_sum,
        secondary_activation_output_sum: richer.secondary_activation_output_sum,
        window_member_commitment: String::new(),
    };
    member.window_member_commitment = commit_phase105_repeated_multi_interval_member(&member)?;
    Ok(member)
}

fn validate_phase105_repeated_multi_interval_gemma_richer_family_artifact_shallow(
    artifact: &Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact,
) -> Result<()> {
    if artifact.artifact_version
        != STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE105
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 105 repeated multi-interval richer-family artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope
        != STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE105
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 105 repeated multi-interval richer-family artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.program_label != "gemma_block_v4" {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 105 program label `{}`",
            artifact.program_label
        )));
    }
    validate_phase105_total_windows(artifact.total_windows)?;
    validate_phase99_total_intervals(artifact.intervals_per_window)?;
    validate_phase95_total_slices(artifact.interval_total_slices)?;
    validate_phase99_token_position_stride(artifact.token_position_stride)?;
    let expected_window_token_position_stride = checked_phase105_window_token_position_stride(
        artifact.intervals_per_window,
        artifact.token_position_stride,
    )?;
    if artifact.window_token_position_stride != expected_window_token_position_stride {
        return Err(VmError::InvalidConfig(
            "Phase 105 window_token_position_stride does not match intervals_per_window * token_position_stride"
                .to_string(),
        ));
    }
    if artifact.total_windows != artifact.members.len() {
        return Err(VmError::InvalidConfig(
            "Phase 105 total_windows does not match the repeated window member count".to_string(),
        ));
    }
    Ok(())
}

pub fn prepare_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    total_windows: usize,
    intervals_per_window: usize,
    interval_total_slices: usize,
    token_position_start: u64,
    token_position_stride: u64,
    start_block_index: u64,
) -> Result<Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact> {
    verify_phase92_shared_normalization_primitive_artifact(shared_primitive_artifact)?;
    validate_phase945_gemma_execution_proof(shared_execution_proof)?;
    validate_phase105_total_windows(total_windows)?;
    validate_phase99_total_intervals(intervals_per_window)?;
    validate_phase95_total_slices(interval_total_slices)?;
    validate_phase99_token_position_stride(token_position_stride)?;
    let window_token_position_stride =
        checked_phase105_window_token_position_stride(intervals_per_window, token_position_stride)?;
    let terminal_token_position = checked_phase105_terminal_token_position(
        token_position_start,
        token_position_stride,
        total_windows,
        intervals_per_window,
    )?;
    let terminal_block_index =
        checked_phase95_terminal_block_index(start_block_index, interval_total_slices as u64)?;
    let shared_execution_proof_commitment =
        commit_phase945_execution_proof(shared_execution_proof)?;

    let mut members = Vec::with_capacity(total_windows);
    for window_index in 0..total_windows {
        let window_token_position_start = checked_phase105_window_token_position_start(
            token_position_start,
            token_position_stride,
            intervals_per_window,
            window_index,
        )?;
        let source = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            shared_primitive_artifact,
            shared_execution_proof,
            intervals_per_window,
            interval_total_slices,
            window_token_position_start,
            token_position_stride,
            start_block_index,
        )?;
        let folded =
            prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(&source)?;
        let richer =
            prepare_phase102_folded_multi_interval_gemma_richer_family_artifact(&source, &folded)?;
        members.push(build_phase105_repeated_multi_interval_member(
            window_index,
            &source,
            &folded,
            &richer,
        )?);
    }

    let window_members_commitment = commit_phase105_repeated_multi_interval_members(&members)?;
    let phase102_artifact_commitments = members
        .iter()
        .map(|member| member.source_phase102_artifact_commitment.clone())
        .collect::<Vec<_>>();
    let phase102_artifact_commitment_sequence_commitment = commit_namespace_strings(
        "phase105/phase102-artifact-commitment-sequence",
        &phase102_artifact_commitments,
    )?;
    let accumulation_handoff_commitments = members
        .iter()
        .map(|member| member.accumulation_handoff_commitment.clone())
        .collect::<Vec<_>>();
    let accumulation_handoff_commitment_sequence_commitment = commit_namespace_strings(
        "phase105/accumulation-handoff-commitment-sequence",
        &accumulation_handoff_commitments,
    )?;
    let folded_richer_accumulator_commitments = members
        .iter()
        .map(|member| {
            member
                .folded_richer_multi_interval_family_accumulator_commitment
                .clone()
        })
        .collect::<Vec<_>>();
    let folded_richer_multi_interval_family_accumulator_sequence_commitment =
        commit_namespace_strings(
            "phase105/folded-richer-multi-interval-family-accumulator-sequence",
            &folded_richer_accumulator_commitments,
        )?;
    let first_member = members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 105 repeated multi-interval richer-family accumulation requires at least one repeated window member"
                .to_string(),
        )
    })?;
    let last_member = members
        .last()
        .expect("members are non-empty after first check");
    let local_score_sum = members
        .iter()
        .map(|member| member.local_score_sum)
        .sum::<i64>();
    let global_score_sum = members
        .iter()
        .map(|member| member.global_score_sum)
        .sum::<i64>();
    let grouped_value_mix_sum = members
        .iter()
        .map(|member| member.grouped_value_mix_sum)
        .sum::<i64>();
    let residual_output_sum = members
        .iter()
        .map(|member| member.residual_output_sum)
        .sum::<i64>();
    let final_acc_sum = members
        .iter()
        .map(|member| member.final_acc_sum)
        .sum::<i64>();
    let primary_norm_sq_min = members
        .iter()
        .map(|member| member.primary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let primary_norm_sq_max = members
        .iter()
        .map(|member| member.primary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let secondary_norm_sq_min = members
        .iter()
        .map(|member| member.secondary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let secondary_norm_sq_max = members
        .iter()
        .map(|member| member.secondary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let primary_activation_output_sum = members
        .iter()
        .map(|member| member.primary_activation_output_sum)
        .sum::<i64>();
    let secondary_activation_output_sum = members
        .iter()
        .map(|member| member.secondary_activation_output_sum)
        .sum::<i64>();
    let repeated_multi_interval_family_accumulator_commitment =
        commit_phase105_repeated_multi_interval_family_accumulator(
            &window_members_commitment,
            &phase102_artifact_commitment_sequence_commitment,
            &accumulation_handoff_commitment_sequence_commitment,
            &folded_richer_multi_interval_family_accumulator_sequence_commitment,
            &first_member.global_interval_start_boundary_commitment,
            &last_member.global_interval_end_boundary_commitment,
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            primary_norm_sq_min,
            primary_norm_sq_max,
            secondary_norm_sq_min,
            secondary_norm_sq_max,
            primary_activation_output_sum,
            secondary_activation_output_sum,
            total_windows,
        )?;
    let artifact_commitment = commit_phase105_repeated_multi_interval_gemma_richer_family_artifact(
        shared_primitive_artifact,
        shared_execution_proof,
        &shared_execution_proof_commitment,
        &window_members_commitment,
        total_windows,
        intervals_per_window,
        interval_total_slices,
        token_position_start,
        token_position_stride,
        window_token_position_stride,
        start_block_index,
        terminal_token_position,
        terminal_block_index,
        &phase102_artifact_commitment_sequence_commitment,
        &accumulation_handoff_commitment_sequence_commitment,
        &folded_richer_multi_interval_family_accumulator_sequence_commitment,
        &first_member.global_interval_start_boundary_commitment,
        &last_member.global_interval_end_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
        &repeated_multi_interval_family_accumulator_commitment,
    )?;

    Ok(
        Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact {
            artifact_version:
                STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE105
                    .to_string(),
            semantic_scope:
                STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE105.to_string(),
            artifact_commitment,
            program_label: "gemma_block_v4".to_string(),
            shared_primitive_artifact_commitment: shared_primitive_artifact
                .artifact_commitment
                .clone(),
            shared_table_registry_commitment: shared_primitive_artifact
                .static_table_registry_commitment
                .clone(),
            shared_execution_proof_commitment,
            shared_execution_proof_backend_version: shared_execution_proof
                .proof_backend_version
                .clone(),
            shared_execution_statement_version: shared_execution_proof
                .claim
                .statement_version
                .clone(),
            total_windows,
            intervals_per_window,
            interval_total_slices,
            token_position_start,
            token_position_stride,
            window_token_position_stride,
            start_block_index,
            terminal_token_position,
            terminal_block_index,
            window_members_commitment,
            phase102_artifact_commitment_sequence_commitment,
            accumulation_handoff_commitment_sequence_commitment,
            folded_richer_multi_interval_family_accumulator_sequence_commitment,
            global_window_start_boundary_commitment: first_member
                .global_interval_start_boundary_commitment
                .clone(),
            global_window_end_boundary_commitment: last_member
                .global_interval_end_boundary_commitment
                .clone(),
            local_score_sum,
            global_score_sum,
            grouped_value_mix_sum,
            residual_output_sum,
            final_acc_sum,
            primary_norm_sq_min,
            primary_norm_sq_max,
            secondary_norm_sq_min,
            secondary_norm_sq_max,
            primary_activation_output_sum,
            secondary_activation_output_sum,
            repeated_multi_interval_family_accumulator_commitment,
            shared_primitive_artifact: shared_primitive_artifact.clone(),
            shared_execution_proof: shared_execution_proof.clone(),
            members,
        },
    )
}

pub fn verify_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
    artifact: &Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact,
) -> Result<()> {
    validate_phase105_repeated_multi_interval_gemma_richer_family_artifact_shallow(artifact)?;
    verify_phase92_shared_normalization_primitive_artifact(&artifact.shared_primitive_artifact)?;
    if artifact.shared_primitive_artifact_commitment
        != artifact.shared_primitive_artifact.artifact_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 shared_primitive_artifact_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }
    if artifact.shared_table_registry_commitment
        != artifact
            .shared_primitive_artifact
            .static_table_registry_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 shared_table_registry_commitment does not match the nested primitive artifact"
                .to_string(),
        ));
    }
    validate_phase945_gemma_execution_proof(&artifact.shared_execution_proof)?;
    let expected_execution_proof_commitment =
        commit_phase945_execution_proof(&artifact.shared_execution_proof)?;
    if artifact.shared_execution_proof_commitment != expected_execution_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 105 shared_execution_proof_commitment does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.shared_execution_proof_backend_version
        != artifact.shared_execution_proof.proof_backend_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 shared_execution_proof_backend_version does not match the nested execution proof"
                .to_string(),
        ));
    }
    if artifact.shared_execution_statement_version
        != artifact.shared_execution_proof.claim.statement_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 shared_execution_statement_version does not match the nested execution proof"
                .to_string(),
        ));
    }

    validate_phase105_total_windows(artifact.total_windows)?;
    validate_phase99_total_intervals(artifact.intervals_per_window)?;
    validate_phase95_total_slices(artifact.interval_total_slices)?;
    validate_phase99_token_position_stride(artifact.token_position_stride)?;
    let expected_window_token_position_stride = checked_phase105_window_token_position_stride(
        artifact.intervals_per_window,
        artifact.token_position_stride,
    )?;
    if artifact.window_token_position_stride != expected_window_token_position_stride {
        return Err(VmError::InvalidConfig(
            "Phase 105 window_token_position_stride does not match intervals_per_window * token_position_stride"
                .to_string(),
        ));
    }
    let expected_terminal_token_position = checked_phase105_terminal_token_position(
        artifact.token_position_start,
        artifact.token_position_stride,
        artifact.total_windows,
        artifact.intervals_per_window,
    )?;
    if artifact.terminal_token_position != expected_terminal_token_position {
        return Err(VmError::InvalidConfig(
            "Phase 105 terminal_token_position does not match the repeated window family"
                .to_string(),
        ));
    }
    let expected_terminal_block_index = checked_phase95_terminal_block_index(
        artifact.start_block_index,
        artifact.interval_total_slices as u64,
    )?;
    if artifact.terminal_block_index != expected_terminal_block_index {
        return Err(VmError::InvalidConfig(
            "Phase 105 terminal_block_index does not match start_block_index + interval_total_slices - 1"
                .to_string(),
        ));
    }

    for (expected_window_index, member) in artifact.members.iter().enumerate() {
        if member.window_index != expected_window_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 105 expected contiguous window_index {}, got {}",
                expected_window_index, member.window_index
            )));
        }
        let window_token_position_start = checked_phase105_window_token_position_start(
            artifact.token_position_start,
            artifact.token_position_stride,
            artifact.intervals_per_window,
            expected_window_index,
        )?;
        let source = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &artifact.shared_primitive_artifact,
            &artifact.shared_execution_proof,
            artifact.intervals_per_window,
            artifact.interval_total_slices,
            window_token_position_start,
            artifact.token_position_stride,
            artifact.start_block_index,
        )?;
        let folded =
            prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(&source)?;
        let richer =
            prepare_phase102_folded_multi_interval_gemma_richer_family_artifact(&source, &folded)?;
        let expected_member = build_phase105_repeated_multi_interval_member(
            expected_window_index,
            &source,
            &folded,
            &richer,
        )?;
        if member != &expected_member {
            return Err(VmError::InvalidConfig(format!(
                "Phase 105 repeated window member {} does not match the canonical reconstructed Phase102 window",
                expected_window_index
            )));
        }
    }

    let expected_window_members_commitment =
        commit_phase105_repeated_multi_interval_members(&artifact.members)?;
    if artifact.window_members_commitment != expected_window_members_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 105 window_members_commitment does not match the serialized repeated window members"
                .to_string(),
        ));
    }
    let expected_phase102_artifact_commitment_sequence_commitment = commit_namespace_strings(
        "phase105/phase102-artifact-commitment-sequence",
        &artifact
            .members
            .iter()
            .map(|member| member.source_phase102_artifact_commitment.clone())
            .collect::<Vec<_>>(),
    )?;
    if artifact.phase102_artifact_commitment_sequence_commitment
        != expected_phase102_artifact_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 phase102_artifact_commitment_sequence_commitment does not match the serialized repeated window members"
                .to_string(),
        ));
    }
    let expected_accumulation_handoff_commitment_sequence_commitment = commit_namespace_strings(
        "phase105/accumulation-handoff-commitment-sequence",
        &artifact
            .members
            .iter()
            .map(|member| member.accumulation_handoff_commitment.clone())
            .collect::<Vec<_>>(),
    )?;
    if artifact.accumulation_handoff_commitment_sequence_commitment
        != expected_accumulation_handoff_commitment_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 accumulation_handoff_commitment_sequence_commitment does not match the serialized repeated window members"
                .to_string(),
        ));
    }
    let expected_folded_richer_multi_interval_family_accumulator_sequence_commitment =
        commit_namespace_strings(
            "phase105/folded-richer-multi-interval-family-accumulator-sequence",
            &artifact
                .members
                .iter()
                .map(|member| {
                    member
                        .folded_richer_multi_interval_family_accumulator_commitment
                        .clone()
                })
                .collect::<Vec<_>>(),
        )?;
    if artifact.folded_richer_multi_interval_family_accumulator_sequence_commitment
        != expected_folded_richer_multi_interval_family_accumulator_sequence_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 folded_richer_multi_interval_family_accumulator_sequence_commitment does not match the serialized repeated window members"
                .to_string(),
        ));
    }

    let first_member = artifact.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 105 repeated multi-interval richer-family accumulation requires at least one repeated window member"
                .to_string(),
        )
    })?;
    let last_member = artifact
        .members
        .last()
        .expect("members are non-empty after first check");
    if artifact.global_window_start_boundary_commitment
        != first_member.global_interval_start_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 global_window_start_boundary_commitment does not match the first repeated window member"
                .to_string(),
        ));
    }
    if artifact.global_window_end_boundary_commitment
        != last_member.global_interval_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 global_window_end_boundary_commitment does not match the terminal repeated window member"
                .to_string(),
        ));
    }

    let expected_local_score_sum = artifact
        .members
        .iter()
        .map(|member| member.local_score_sum)
        .sum::<i64>();
    let expected_global_score_sum = artifact
        .members
        .iter()
        .map(|member| member.global_score_sum)
        .sum::<i64>();
    let expected_grouped_value_mix_sum = artifact
        .members
        .iter()
        .map(|member| member.grouped_value_mix_sum)
        .sum::<i64>();
    let expected_residual_output_sum = artifact
        .members
        .iter()
        .map(|member| member.residual_output_sum)
        .sum::<i64>();
    let expected_final_acc_sum = artifact
        .members
        .iter()
        .map(|member| member.final_acc_sum)
        .sum::<i64>();
    let expected_primary_norm_sq_min = artifact
        .members
        .iter()
        .map(|member| member.primary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let expected_primary_norm_sq_max = artifact
        .members
        .iter()
        .map(|member| member.primary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let expected_secondary_norm_sq_min = artifact
        .members
        .iter()
        .map(|member| member.secondary_norm_sq_min)
        .min()
        .expect("members are non-empty");
    let expected_secondary_norm_sq_max = artifact
        .members
        .iter()
        .map(|member| member.secondary_norm_sq_max)
        .max()
        .expect("members are non-empty");
    let expected_primary_activation_output_sum = artifact
        .members
        .iter()
        .map(|member| member.primary_activation_output_sum)
        .sum::<i64>();
    let expected_secondary_activation_output_sum = artifact
        .members
        .iter()
        .map(|member| member.secondary_activation_output_sum)
        .sum::<i64>();
    if artifact.local_score_sum != expected_local_score_sum
        || artifact.global_score_sum != expected_global_score_sum
        || artifact.grouped_value_mix_sum != expected_grouped_value_mix_sum
        || artifact.residual_output_sum != expected_residual_output_sum
        || artifact.final_acc_sum != expected_final_acc_sum
        || artifact.primary_norm_sq_min != expected_primary_norm_sq_min
        || artifact.primary_norm_sq_max != expected_primary_norm_sq_max
        || artifact.secondary_norm_sq_min != expected_secondary_norm_sq_min
        || artifact.secondary_norm_sq_max != expected_secondary_norm_sq_max
        || artifact.primary_activation_output_sum != expected_primary_activation_output_sum
        || artifact.secondary_activation_output_sum != expected_secondary_activation_output_sum
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 repeated window summaries do not match the serialized repeated window members"
                .to_string(),
        ));
    }

    let expected_repeated_multi_interval_family_accumulator_commitment =
        commit_phase105_repeated_multi_interval_family_accumulator(
            &artifact.window_members_commitment,
            &artifact.phase102_artifact_commitment_sequence_commitment,
            &artifact.accumulation_handoff_commitment_sequence_commitment,
            &artifact.folded_richer_multi_interval_family_accumulator_sequence_commitment,
            &artifact.global_window_start_boundary_commitment,
            &artifact.global_window_end_boundary_commitment,
            artifact.local_score_sum,
            artifact.global_score_sum,
            artifact.grouped_value_mix_sum,
            artifact.residual_output_sum,
            artifact.final_acc_sum,
            artifact.primary_norm_sq_min,
            artifact.primary_norm_sq_max,
            artifact.secondary_norm_sq_min,
            artifact.secondary_norm_sq_max,
            artifact.primary_activation_output_sum,
            artifact.secondary_activation_output_sum,
            artifact.total_windows,
        )?;
    if artifact.repeated_multi_interval_family_accumulator_commitment
        != expected_repeated_multi_interval_family_accumulator_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 105 repeated_multi_interval_family_accumulator_commitment does not match the serialized repeated window surface"
                .to_string(),
        ));
    }

    let expected_artifact_commitment =
        commit_phase105_repeated_multi_interval_gemma_richer_family_artifact(
            &artifact.shared_primitive_artifact,
            &artifact.shared_execution_proof,
            &artifact.shared_execution_proof_commitment,
            &artifact.window_members_commitment,
            artifact.total_windows,
            artifact.intervals_per_window,
            artifact.interval_total_slices,
            artifact.token_position_start,
            artifact.token_position_stride,
            artifact.window_token_position_stride,
            artifact.start_block_index,
            artifact.terminal_token_position,
            artifact.terminal_block_index,
            &artifact.phase102_artifact_commitment_sequence_commitment,
            &artifact.accumulation_handoff_commitment_sequence_commitment,
            &artifact.folded_richer_multi_interval_family_accumulator_sequence_commitment,
            &artifact.global_window_start_boundary_commitment,
            &artifact.global_window_end_boundary_commitment,
            artifact.local_score_sum,
            artifact.global_score_sum,
            artifact.grouped_value_mix_sum,
            artifact.residual_output_sum,
            artifact.final_acc_sum,
            artifact.primary_norm_sq_min,
            artifact.primary_norm_sq_max,
            artifact.secondary_norm_sq_min,
            artifact.secondary_norm_sq_max,
            artifact.primary_activation_output_sum,
            artifact.secondary_activation_output_sum,
            &artifact.repeated_multi_interval_family_accumulator_commitment,
        )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 105 repeated multi-interval richer-family artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
    artifact: &Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE105_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_JSON_BYTES,
        "Phase 105 repeated multi-interval richer-family accumulation artifact",
    )
}

pub fn load_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
    path: &Path,
) -> Result<Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE105_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_JSON_BYTES,
        "Phase 105 repeated multi-interval richer-family accumulation artifact",
    )?;
    let artifact: Phase105RepeatedMultiIntervalGemmaRicherFamilyAccumulationArtifact =
        serde_json::from_slice(&bytes)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(&artifact)?;
    Ok(artifact)
}

fn build_phase93_tensor_native_chain_artifact(
    primitive_artifact: Phase92SharedNormalizationPrimitiveArtifact,
    steps: Vec<Phase93TensorNativeChainStep>,
) -> Result<Phase93TensorNativeChainArtifact> {
    let total_steps = steps.len();
    let steps_commitment = commit_phase93_chain_steps(&steps)?;
    let initial_boundary_commitment = steps
        .first()
        .map(|step| step.carried_state_in_commitment.clone())
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 93 tensor-native chain requires at least one chain step".to_string(),
            )
        })?;
    let terminal_boundary_commitment = steps
        .last()
        .map(|step| step.carried_state_out_commitment.clone())
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 93 tensor-native chain requires at least one chain step".to_string(),
            )
        })?;
    let artifact_commitment = commit_phase93_tensor_native_chain_artifact(
        &primitive_artifact,
        &primitive_artifact.static_table_registry_commitment,
        &steps,
        &steps_commitment,
        &initial_boundary_commitment,
        &terminal_boundary_commitment,
        total_steps,
    )?;
    Ok(Phase93TensorNativeChainArtifact {
        artifact_version: STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_VERSION_PHASE93.to_string(),
        semantic_scope: STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_SCOPE_PHASE93.to_string(),
        artifact_commitment,
        carried_state_type_version: STWO_TENSOR_NATIVE_CARRIED_STATE_VERSION_PHASE93.to_string(),
        shared_table_registry_commitment: primitive_artifact
            .static_table_registry_commitment
            .clone(),
        primitive_artifact_commitment: primitive_artifact.artifact_commitment.clone(),
        steps_commitment,
        initial_boundary_commitment,
        terminal_boundary_commitment,
        total_steps,
        primitive_artifact,
        steps,
    })
}

fn phase93_default_tensor_native_chain_steps(
    primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    token_position: u64,
    block_index: u64,
) -> Result<Vec<Phase93TensorNativeChainStep>> {
    if primitive_artifact.steps.len() < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain requires a primitive artifact with at least two template steps"
                .to_string(),
        ));
    }
    let mut boundaries = Vec::with_capacity(PHASE93_DEFAULT_CHAIN_TEMPLATE_SEQUENCE.len() + 1);
    for substep_index in 0..=PHASE93_DEFAULT_CHAIN_TEMPLATE_SEQUENCE.len() {
        boundaries.push(build_phase93_demo_boundary(
            token_position,
            block_index,
            substep_index as u64,
            &primitive_artifact.static_table_registry_commitment,
        )?);
    }

    PHASE93_DEFAULT_CHAIN_LABELS
        .iter()
        .enumerate()
        .map(|(step_index, step_label)| {
            let primitive_step_index = PHASE93_DEFAULT_CHAIN_TEMPLATE_SEQUENCE[step_index];
            let primitive_step = primitive_artifact
                .steps
                .get(primitive_step_index)
                .ok_or_else(|| {
                    VmError::InvalidConfig(format!(
                    "Phase 93 tensor-native chain references missing primitive template step {}",
                    primitive_step_index
                ))
                })?;
            let primitive_template_claims_commitment =
                commit_phase93_primitive_template_step(primitive_step)?;
            let carried_state_in = boundaries[step_index].clone();
            let carried_state_out = boundaries[step_index + 1].clone();
            let carried_state_in_commitment = commit_phase93_boundary(&carried_state_in)?;
            let carried_state_out_commitment = commit_phase93_boundary(&carried_state_out)?;
            let mut step = Phase93TensorNativeChainStep {
                step_index,
                step_label: (*step_label).to_string(),
                primitive_template_step_index: primitive_step_index,
                primitive_template_step_label: primitive_step.step_label.clone(),
                primitive_template_claims_commitment,
                carried_state_in,
                carried_state_in_commitment,
                carried_state_out,
                carried_state_out_commitment,
                carried_state_link_commitment: String::new(),
            };
            step.carried_state_link_commitment = commit_phase93_chain_step(&step)?;
            Ok(step)
        })
        .collect()
}

fn build_phase93_demo_boundary(
    token_position: u64,
    block_index: u64,
    substep_index: u64,
    shared_table_registry_commitment: &str,
) -> Result<Phase93TypedCarriedStateBoundary> {
    Ok(Phase93TypedCarriedStateBoundary {
        boundary_version: STWO_TENSOR_NATIVE_CARRIED_STATE_VERSION_PHASE93.to_string(),
        token_position,
        block_index,
        substep_index,
        hidden_state_commitment: commit_namespace_u64s(
            "phase93/demo/hidden-state",
            &[token_position, block_index, substep_index],
        )?,
        kv_cache_commitment: commit_namespace_u64s(
            "phase93/demo/kv-cache",
            &[token_position, block_index, substep_index],
        )?,
        shared_table_registry_commitment: shared_table_registry_commitment.to_string(),
    })
}

fn canonicalize_phase93_chain_steps(
    steps: &[Phase93TensorNativeChainStep],
    primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_table_registry_commitment: &str,
) -> Result<Vec<Phase93TensorNativeChainStep>> {
    if steps.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 93 tensor-native chain requires at least one step".to_string(),
        ));
    }

    let mut canonical_steps = steps.to_vec();
    canonical_steps.sort_by_key(|step| step.step_index);
    let mut seen_labels = BTreeSet::new();
    let mut expected_token_position = None;
    let mut expected_block_index = None;
    for (expected_step_index, step) in canonical_steps.iter().enumerate() {
        if step.step_index != expected_step_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain expected contiguous step_index {}, got {}",
                expected_step_index, step.step_index
            )));
        }
        if step.step_label.trim().is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} has an empty step_label",
                step.step_index
            )));
        }
        if !seen_labels.insert(step.step_label.clone()) {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain reuses step_label `{}`",
                step.step_label
            )));
        }

        let primitive_step = primitive_artifact
            .steps
            .get(step.primitive_template_step_index)
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "Phase 93 tensor-native chain step {} references missing primitive template step {}",
                    step.step_index, step.primitive_template_step_index
                ))
            })?;
        if step.primitive_template_step_label != primitive_step.step_label {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} primitive template label does not match the nested primitive artifact",
                step.step_index
            )));
        }
        let expected_template_claims = commit_phase93_primitive_template_step(primitive_step)?;
        if step.primitive_template_claims_commitment != expected_template_claims {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} primitive template claims commitment does not match the nested primitive artifact",
                step.step_index
            )));
        }

        validate_phase93_boundary(
            &step.carried_state_in,
            shared_table_registry_commitment,
            step.step_index as u64,
        )?;
        validate_phase93_boundary(
            &step.carried_state_out,
            shared_table_registry_commitment,
            step.step_index as u64 + 1,
        )?;
        if step.carried_state_in.token_position != step.carried_state_out.token_position {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} changes token_position inside a single local transition",
                step.step_index
            )));
        }
        if step.carried_state_in.block_index != step.carried_state_out.block_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 93 tensor-native chain step {} changes block_index inside a single local transition",
                step.step_index
            )));
        }
        if let Some(token_position) = expected_token_position {
            if step.carried_state_in.token_position != token_position {
                return Err(VmError::InvalidConfig(
                    "Phase 93 tensor-native chain mixes token_position values inside one fixed-shape chain"
                        .to_string(),
                ));
            }
        } else {
            expected_token_position = Some(step.carried_state_in.token_position);
        }
        if let Some(block_index) = expected_block_index {
            if step.carried_state_in.block_index != block_index {
                return Err(VmError::InvalidConfig(
                    "Phase 93 tensor-native chain mixes block_index values inside one fixed-shape chain"
                        .to_string(),
                ));
            }
        } else {
            expected_block_index = Some(step.carried_state_in.block_index);
        }
    }

    Ok(canonical_steps)
}

fn validate_phase93_boundary(
    boundary: &Phase93TypedCarriedStateBoundary,
    shared_table_registry_commitment: &str,
    expected_substep_index: u64,
) -> Result<()> {
    if boundary.boundary_version != STWO_TENSOR_NATIVE_CARRIED_STATE_VERSION_PHASE93 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 93 carried-state boundary version `{}`",
            boundary.boundary_version
        )));
    }
    if boundary.shared_table_registry_commitment != shared_table_registry_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 93 carried-state boundary shared_table_registry_commitment does not match the artifact registry"
                .to_string(),
        ));
    }
    if boundary.hidden_state_commitment.trim().is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 93 carried-state boundary hidden_state_commitment is empty".to_string(),
        ));
    }
    if boundary.kv_cache_commitment.trim().is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 93 carried-state boundary kv_cache_commitment is empty".to_string(),
        ));
    }
    if boundary.substep_index != expected_substep_index {
        return Err(VmError::InvalidConfig(format!(
            "Phase 93 carried-state boundary expected substep_index {}, got {}",
            expected_substep_index, boundary.substep_index
        )));
    }
    Ok(())
}

fn phase93_unique_primitive_normalization_row_set(
    primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
) -> Result<BTreeSet<(u16, u16)>> {
    let mut rows = BTreeSet::new();
    for step in &primitive_artifact.steps {
        for row in &step.claimed_rows {
            if !rows.insert(*row) {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 93 primitive artifact reuses row ({}, {}); unique template rows are required",
                    row.0, row.1
                )));
            }
        }
    }
    Ok(rows)
}

fn phase945_unique_normalization_row_set(
    rows: &[Phase945GemmaNormalizationRowSummary],
) -> BTreeSet<(u16, u16)> {
    rows.iter()
        .map(|row| (row.norm_sq, row.inv_sqrt_q8))
        .collect()
}

fn phase945_normalization_rows_from_embedded(
    embedded: &EmbeddedSharedNormalizationProof,
) -> Result<Vec<Phase945GemmaNormalizationRowSummary>> {
    embedded
        .claimed_rows
        .iter()
        .enumerate()
        .map(|(row_index, row)| {
            Ok(Phase945GemmaNormalizationRowSummary {
                row_index,
                norm_sq_memory_index: row.norm_sq_memory_index,
                inv_sqrt_q8_memory_index: row.inv_sqrt_q8_memory_index,
                norm_sq: u16::try_from(row.expected_norm_sq).map_err(|_| {
                    VmError::InvalidConfig(format!(
                        "gemma_block_v4 shared normalization row {} norm_sq is not a canonical u16",
                        row_index
                    ))
                })?,
                inv_sqrt_q8: u16::try_from(row.expected_inv_sqrt_q8).map_err(|_| {
                    VmError::InvalidConfig(format!(
                        "gemma_block_v4 shared normalization row {} inv_sqrt_q8 is not a canonical u16",
                        row_index
                    ))
                })?,
            })
        })
        .collect()
}

fn phase945_activation_rows_from_embedded(
    embedded: &EmbeddedSharedActivationLookupProof,
) -> Vec<Phase945GemmaActivationRowSummary> {
    embedded
        .claimed_rows
        .iter()
        .enumerate()
        .map(|(row_index, row)| Phase945GemmaActivationRowSummary {
            row_index,
            input_memory_index: row.input_memory_index,
            output_memory_index: row.output_memory_index,
            input: row.expected_input,
            output: row.expected_output,
        })
        .collect()
}

fn parse_phase945_arithmetic_subset_payload(
    execution_proof: &VanillaStarkExecutionProof,
) -> Result<Phase945ArithmeticSubsetProofPayload> {
    serde_json::from_slice(&execution_proof.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn validate_phase945_gemma_execution_proof(
    execution_proof: &VanillaStarkExecutionProof,
) -> Result<()> {
    if execution_proof.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.5 Gemma core slice requires an S-two execution proof, got `{}`",
            execution_proof.proof_backend
        )));
    }
    let canonical_program = canonical_gemma_block_v4_program()?;
    if execution_proof.claim.program != canonical_program {
        return Err(VmError::InvalidConfig(
            "Phase 94.5 Gemma core slice requires the canonical `programs/gemma_block_v4.tvm` program"
                .to_string(),
        ));
    }
    if !verify_execution_stark_with_reexecution(execution_proof)? {
        return Err(VmError::UnsupportedProof(
            "Phase 94.5 Gemma core slice nested execution proof did not verify under reexecution"
                .to_string(),
        ));
    }
    Ok(())
}

fn canonical_gemma_block_v4_program() -> Result<crate::Program> {
    parse_program(include_str!("../../programs/gemma_block_v4.tvm"))
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct Phase9475InvariantSummary {
    local_score: i16,
    global_score: i16,
    grouped_value_mix: i16,
    residual_output: i16,
    primary_norm_sq: i16,
    primary_inv_sqrt_q8: i16,
    primary_activation_input: i16,
    primary_activation_output: i16,
    secondary_norm_sq: i16,
    secondary_inv_sqrt_q8: i16,
    secondary_activation_input: i16,
    secondary_activation_output: i16,
}

fn phase9475_selected_memory_window(
    memory: &[i16],
) -> Result<Vec<Phase9475GemmaMemoryWindowEntry>> {
    let selected_indices = [8usize, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
    selected_indices
        .into_iter()
        .map(|memory_index| {
            let value = *memory.get(memory_index).ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "Phase 94.75 requires gemma_block_v4 final memory index {}",
                    memory_index
                ))
            })?;
            Ok(Phase9475GemmaMemoryWindowEntry {
                memory_index: u8::try_from(memory_index).expect("memory window index fits in u8"),
                value: i16::try_from(value).map_err(|_| {
                    VmError::InvalidConfig(format!(
                        "Phase 94.75 gemma_block_v4 final memory index {} is not a canonical i16",
                        memory_index
                    ))
                })?,
            })
        })
        .collect()
}

fn phase9475_memory_i16(memory: &[i16], index: usize, label: &str) -> Result<i16> {
    let value = *memory.get(index).ok_or_else(|| {
        VmError::InvalidConfig(format!(
            "Phase 94.75 requires gemma_block_v4 final memory index {} for {}",
            index, label
        ))
    })?;
    i16::try_from(value).map_err(|_| {
        VmError::InvalidConfig(format!(
            "Phase 94.75 gemma_block_v4 final memory index {} for {} is not a canonical i16",
            index, label
        ))
    })
}

fn phase9475_checked_mul(lhs: i16, rhs: i16, label: &str) -> Result<i16> {
    lhs.checked_mul(rhs).ok_or_else(|| {
        VmError::InvalidConfig(format!(
            "Phase 94.75 {} multiplication overflowed i16",
            label
        ))
    })
}

fn phase9475_checked_add(lhs: i16, rhs: i16, label: &str) -> Result<i16> {
    lhs.checked_add(rhs).ok_or_else(|| {
        VmError::InvalidConfig(format!("Phase 94.75 {} addition overflowed i16", label))
    })
}

fn phase9475_invariant_summary(memory: &[i16]) -> Result<Phase9475InvariantSummary> {
    let q0 = phase9475_memory_i16(memory, 0, "q0")?;
    let q1 = phase9475_memory_i16(memory, 1, "q1")?;
    let k_local_0 = phase9475_memory_i16(memory, 2, "k_local_0")?;
    let k_local_1 = phase9475_memory_i16(memory, 3, "k_local_1")?;
    let k_global_0 = phase9475_memory_i16(memory, 4, "k_global_0")?;
    let k_global_1 = phase9475_memory_i16(memory, 5, "k_global_1")?;
    let v_local = phase9475_memory_i16(memory, 6, "v_local")?;
    let bias = phase9475_memory_i16(memory, 7, "bias")?;
    let residual_output = phase9475_memory_i16(memory, 8, "residual_output")?;
    let v_global = phase9475_memory_i16(memory, 9, "v_global")?;
    let local_score = phase9475_memory_i16(memory, 10, "local_score")?;
    let global_score = phase9475_memory_i16(memory, 11, "global_score")?;
    let grouped_value_mix = phase9475_memory_i16(memory, 12, "grouped_value_mix")?;
    let primary_norm_sq = phase9475_memory_i16(memory, 13, "primary_norm_sq")?;
    let primary_inv_sqrt_q8 = phase9475_memory_i16(memory, 14, "primary_inv_sqrt_q8")?;
    let primary_activation_input = phase9475_memory_i16(memory, 15, "primary_activation_input")?;
    let primary_activation_output = phase9475_memory_i16(memory, 16, "primary_activation_output")?;
    let secondary_norm_sq = phase9475_memory_i16(memory, 17, "secondary_norm_sq")?;
    let secondary_inv_sqrt_q8 = phase9475_memory_i16(memory, 18, "secondary_inv_sqrt_q8")?;
    let secondary_activation_input =
        phase9475_memory_i16(memory, 19, "secondary_activation_input")?;
    let secondary_activation_output =
        phase9475_memory_i16(memory, 20, "secondary_activation_output")?;

    let expected_local_score = phase9475_checked_add(
        phase9475_checked_mul(q0, k_local_0, "local_score term 0")?,
        phase9475_checked_mul(q1, k_local_1, "local_score term 1")?,
        "local_score",
    )?;
    if local_score != expected_local_score {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 local_score memory value {} does not match the fixed gemma_block_v4 dot-product result {}",
            local_score, expected_local_score
        )));
    }

    let expected_global_score = phase9475_checked_add(
        phase9475_checked_mul(q0, k_global_0, "global_score term 0")?,
        phase9475_checked_mul(q1, k_global_1, "global_score term 1")?,
        "global_score",
    )?;
    if global_score != expected_global_score {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 global_score memory value {} does not match the fixed gemma_block_v4 dot-product result {}",
            global_score, expected_global_score
        )));
    }

    let expected_grouped_value_mix = phase9475_checked_add(
        phase9475_checked_mul(local_score, v_local, "grouped_value_mix local term")?,
        phase9475_checked_mul(global_score, v_global, "grouped_value_mix global term")?,
        "grouped_value_mix",
    )?;
    if grouped_value_mix != expected_grouped_value_mix {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 grouped_value_mix memory value {} does not match the fixed gemma_block_v4 weighted value mix {}",
            grouped_value_mix, expected_grouped_value_mix
        )));
    }

    let expected_residual_output =
        phase9475_checked_add(grouped_value_mix, bias, "residual_output")?;
    if residual_output != expected_residual_output {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 residual_output memory value {} does not match the fixed gemma_block_v4 residual projection {}",
            residual_output, expected_residual_output
        )));
    }

    let expected_primary_norm_sq =
        phase9475_checked_mul(residual_output, residual_output, "primary_norm_sq")?;
    if primary_norm_sq != expected_primary_norm_sq {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 primary_norm_sq memory value {} does not match residual_output^2 {}",
            primary_norm_sq, expected_primary_norm_sq
        )));
    }
    if primary_inv_sqrt_q8 != 64 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 primary_inv_sqrt_q8 expected 64, got {}",
            primary_inv_sqrt_q8
        )));
    }
    if primary_activation_input != 1 || primary_activation_output != 1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 primary activation expected (1 -> 1), got ({} -> {})",
            primary_activation_input, primary_activation_output
        )));
    }
    if secondary_norm_sq != 4 || secondary_inv_sqrt_q8 != 128 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 secondary normalization expected (4, 128), got ({}, {})",
            secondary_norm_sq, secondary_inv_sqrt_q8
        )));
    }
    if secondary_activation_input != 0 || secondary_activation_output != 1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 94.75 secondary activation expected (0 -> 1), got ({} -> {})",
            secondary_activation_input, secondary_activation_output
        )));
    }

    Ok(Phase9475InvariantSummary {
        local_score,
        global_score,
        grouped_value_mix,
        residual_output,
        primary_norm_sq,
        primary_inv_sqrt_q8,
        primary_activation_input,
        primary_activation_output,
        secondary_norm_sq,
        secondary_inv_sqrt_q8,
        secondary_activation_input,
        secondary_activation_output,
    })
}

fn phase9475_validate_summary_fields(
    artifact: &Phase9475GemmaBlockRicherSliceArtifact,
    expected: &Phase9475InvariantSummary,
) -> Result<()> {
    if artifact.local_score != expected.local_score
        || artifact.global_score != expected.global_score
        || artifact.grouped_value_mix != expected.grouped_value_mix
        || artifact.residual_output != expected.residual_output
        || artifact.primary_norm_sq != expected.primary_norm_sq
        || artifact.primary_inv_sqrt_q8 != expected.primary_inv_sqrt_q8
        || artifact.primary_activation_input != expected.primary_activation_input
        || artifact.primary_activation_output != expected.primary_activation_output
        || artifact.secondary_norm_sq != expected.secondary_norm_sq
        || artifact.secondary_inv_sqrt_q8 != expected.secondary_inv_sqrt_q8
        || artifact.secondary_activation_input != expected.secondary_activation_input
        || artifact.secondary_activation_output != expected.secondary_activation_output
    {
        return Err(VmError::InvalidConfig(
            "Phase 94.75 Gemma richer slice summary fields do not match the reconstructed fixed-program invariants"
                .to_string(),
        ));
    }
    Ok(())
}

fn commit_phase93_boundary(boundary: &Phase93TypedCarriedStateBoundary) -> Result<String> {
    let json =
        serde_json::to_vec(boundary).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase93/carried-boundary", &json)
}

fn commit_phase93_primitive_template_step(
    step: &Phase92SharedNormalizationPrimitiveStep,
) -> Result<String> {
    let json =
        serde_json::to_vec(step).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase93/primitive-template-step", &json)
}

fn commit_phase93_chain_step(step: &Phase93TensorNativeChainStep) -> Result<String> {
    #[derive(Serialize)]
    struct StepCommitmentPayload<'a> {
        step_index: usize,
        step_label: &'a str,
        primitive_template_step_index: usize,
        primitive_template_step_label: &'a str,
        primitive_template_claims_commitment: &'a str,
        carried_state_in: &'a Phase93TypedCarriedStateBoundary,
        carried_state_in_commitment: &'a str,
        carried_state_out: &'a Phase93TypedCarriedStateBoundary,
        carried_state_out_commitment: &'a str,
    }
    let payload = StepCommitmentPayload {
        step_index: step.step_index,
        step_label: &step.step_label,
        primitive_template_step_index: step.primitive_template_step_index,
        primitive_template_step_label: &step.primitive_template_step_label,
        primitive_template_claims_commitment: &step.primitive_template_claims_commitment,
        carried_state_in: &step.carried_state_in,
        carried_state_in_commitment: &step.carried_state_in_commitment,
        carried_state_out: &step.carried_state_out,
        carried_state_out_commitment: &step.carried_state_out_commitment,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase93/chain-step", &json)
}

fn commit_phase93_chain_steps(steps: &[Phase93TensorNativeChainStep]) -> Result<String> {
    let json =
        serde_json::to_vec(steps).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase93/chain-steps", &json)
}

fn commit_phase93_tensor_native_chain_artifact(
    primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_table_registry_commitment: &str,
    steps: &[Phase93TensorNativeChainStep],
    steps_commitment: &str,
    initial_boundary_commitment: &str,
    terminal_boundary_commitment: &str,
    total_steps: usize,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_VERSION_PHASE93.as_bytes());
    hasher.update(STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_SCOPE_PHASE93.as_bytes());
    hasher.update(STWO_TENSOR_NATIVE_CARRIED_STATE_VERSION_PHASE93.as_bytes());
    hasher.update(primitive_artifact.artifact_commitment.as_bytes());
    hasher.update(shared_table_registry_commitment.as_bytes());
    hasher.update(steps_commitment.as_bytes());
    hasher.update(initial_boundary_commitment.as_bytes());
    hasher.update(terminal_boundary_commitment.as_bytes());
    hasher.update(&(total_steps as u64).to_le_bytes());
    let steps_json =
        serde_json::to_vec(steps).map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(steps_json.len() as u64).to_le_bytes());
    hasher.update(&steps_json);
    let primitive_json = serde_json::to_vec(primitive_artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(primitive_json.len() as u64).to_le_bytes());
    hasher.update(&primitive_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase945_execution_proof(execution_proof: &VanillaStarkExecutionProof) -> Result<String> {
    let json = serde_json::to_vec(execution_proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase945/execution-proof", &json)
}

fn commit_phase945_normalization_row_set(
    rows: &[Phase945GemmaNormalizationRowSummary],
) -> Result<String> {
    let json =
        serde_json::to_vec(rows).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase945/normalization-row-set", &json)
}

fn commit_phase945_activation_row_set(
    rows: &[Phase945GemmaActivationRowSummary],
) -> Result<String> {
    let json =
        serde_json::to_vec(rows).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase945/activation-row-set", &json)
}

fn commit_phase945_gemma_block_core_slice_artifact(
    chain_artifact: &Phase93TensorNativeChainArtifact,
    execution_proof: &VanillaStarkExecutionProof,
    execution_proof_commitment: &str,
    shared_normalization_statement_version: &str,
    shared_normalization_scope: &str,
    shared_activation_statement_version: &str,
    shared_activation_scope: &str,
    shared_normalization_rows: &[Phase945GemmaNormalizationRowSummary],
    shared_activation_rows: &[Phase945GemmaActivationRowSummary],
    normalization_row_set_commitment: &str,
    activation_row_set_commitment: &str,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_VERSION_PHASE945.as_bytes());
    hasher.update(STWO_GEMMA_BLOCK_CORE_SLICE_ARTIFACT_SCOPE_PHASE945.as_bytes());
    hasher.update(chain_artifact.artifact_commitment.as_bytes());
    hasher.update(execution_proof_commitment.as_bytes());
    hasher.update(shared_normalization_statement_version.as_bytes());
    hasher.update(shared_normalization_scope.as_bytes());
    hasher.update(shared_activation_statement_version.as_bytes());
    hasher.update(shared_activation_scope.as_bytes());
    hasher.update(normalization_row_set_commitment.as_bytes());
    hasher.update(activation_row_set_commitment.as_bytes());
    let chain_json = serde_json::to_vec(chain_artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(chain_json.len() as u64).to_le_bytes());
    hasher.update(&chain_json);
    let proof_json = serde_json::to_vec(execution_proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(proof_json.len() as u64).to_le_bytes());
    hasher.update(&proof_json);
    let norm_json = serde_json::to_vec(shared_normalization_rows)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(norm_json.len() as u64).to_le_bytes());
    hasher.update(&norm_json);
    let act_json = serde_json::to_vec(shared_activation_rows)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(act_json.len() as u64).to_le_bytes());
    hasher.update(&act_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase9475_selected_memory_window(
    window: &[Phase9475GemmaMemoryWindowEntry],
) -> Result<String> {
    let json =
        serde_json::to_vec(window).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase9475/selected-memory-window", &json)
}

fn commit_phase9475_gemma_block_richer_slice_artifact(
    core_slice_artifact: &Phase945GemmaBlockCoreSliceArtifact,
    selected_memory_window: &[Phase9475GemmaMemoryWindowEntry],
    selected_memory_window_commitment: &str,
    invariant_summary: &Phase9475InvariantSummary,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_VERSION_PHASE9475.as_bytes());
    hasher.update(STWO_GEMMA_BLOCK_RICHER_SLICE_ARTIFACT_SCOPE_PHASE9475.as_bytes());
    hasher.update(core_slice_artifact.artifact_commitment.as_bytes());
    hasher.update(selected_memory_window_commitment.as_bytes());
    hasher.update(&invariant_summary.local_score.to_le_bytes());
    hasher.update(&invariant_summary.global_score.to_le_bytes());
    hasher.update(&invariant_summary.grouped_value_mix.to_le_bytes());
    hasher.update(&invariant_summary.residual_output.to_le_bytes());
    hasher.update(&invariant_summary.primary_norm_sq.to_le_bytes());
    hasher.update(&invariant_summary.primary_inv_sqrt_q8.to_le_bytes());
    hasher.update(&invariant_summary.primary_activation_input.to_le_bytes());
    hasher.update(&invariant_summary.primary_activation_output.to_le_bytes());
    hasher.update(&invariant_summary.secondary_norm_sq.to_le_bytes());
    hasher.update(&invariant_summary.secondary_inv_sqrt_q8.to_le_bytes());
    hasher.update(&invariant_summary.secondary_activation_input.to_le_bytes());
    hasher.update(&invariant_summary.secondary_activation_output.to_le_bytes());
    let core_slice_json = serde_json::to_vec(core_slice_artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(core_slice_json.len() as u64).to_le_bytes());
    hasher.update(&core_slice_json);
    let memory_window_json = serde_json::to_vec(selected_memory_window)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(memory_window_json.len() as u64).to_le_bytes());
    hasher.update(&memory_window_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase95_repeated_gemma_members(
    members: &[Phase95RepeatedGemmaSliceMember],
) -> Result<String> {
    let json =
        serde_json::to_vec(members).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase95/repeated-gemma-members", &json)
}

fn commit_phase95_repeated_gemma_slice_accumulation_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    shared_execution_proof_commitment: &str,
    members: &[Phase95RepeatedGemmaSliceMember],
    members_commitment: &str,
    repeated_token_position: u64,
    start_block_index: u64,
    terminal_block_index: u64,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE95.as_bytes());
    hasher.update(STWO_REPEATED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE95.as_bytes());
    hasher.update(shared_primitive_artifact.artifact_commitment.as_bytes());
    hasher.update(
        shared_primitive_artifact
            .static_table_registry_commitment
            .as_bytes(),
    );
    hasher.update(shared_execution_proof_commitment.as_bytes());
    hasher.update(&repeated_token_position.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    hasher.update(&(members.len() as u64).to_le_bytes());
    hasher.update(members_commitment.as_bytes());
    let primitive_json = serde_json::to_vec(shared_primitive_artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(primitive_json.len() as u64).to_le_bytes());
    hasher.update(&primitive_json);
    let proof_json = serde_json::to_vec(shared_execution_proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(proof_json.len() as u64).to_le_bytes());
    hasher.update(&proof_json);
    let members_json =
        serde_json::to_vec(members).map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(members_json.len() as u64).to_le_bytes());
    hasher.update(&members_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase965_folded_gemma_slice_group(
    group: &Phase965FoldedGemmaSliceGroup,
) -> Result<String> {
    #[derive(Serialize)]
    struct GroupCommitmentPayload<'a> {
        folded_group_index: usize,
        start_slice_index: usize,
        terminal_slice_index: usize,
        start_block_index: u64,
        terminal_block_index: u64,
        first_richer_slice_artifact_commitment: &'a str,
        terminal_richer_slice_artifact_commitment: &'a str,
        initial_boundary_commitment: &'a str,
        terminal_boundary_commitment: &'a str,
        member_richer_slice_commitment_sequence_commitment: &'a str,
        member_selected_memory_window_commitment_sequence_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
    }
    let payload = GroupCommitmentPayload {
        folded_group_index: group.folded_group_index,
        start_slice_index: group.start_slice_index,
        terminal_slice_index: group.terminal_slice_index,
        start_block_index: group.start_block_index,
        terminal_block_index: group.terminal_block_index,
        first_richer_slice_artifact_commitment: &group.first_richer_slice_artifact_commitment,
        terminal_richer_slice_artifact_commitment: &group.terminal_richer_slice_artifact_commitment,
        initial_boundary_commitment: &group.initial_boundary_commitment,
        terminal_boundary_commitment: &group.terminal_boundary_commitment,
        member_richer_slice_commitment_sequence_commitment: &group
            .member_richer_slice_commitment_sequence_commitment,
        member_selected_memory_window_commitment_sequence_commitment: &group
            .member_selected_memory_window_commitment_sequence_commitment,
        local_score_sum: group.local_score_sum,
        global_score_sum: group.global_score_sum,
        grouped_value_mix_sum: group.grouped_value_mix_sum,
        residual_output_sum: group.residual_output_sum,
        final_acc_sum: group.final_acc_sum,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase965/folded-gemma-slice-group", &json)
}

fn commit_phase965_fold_template(
    source_phase95_artifact_commitment: &str,
    source_members_commitment: &str,
    shared_primitive_artifact_commitment: &str,
    shared_table_registry_commitment: &str,
    shared_execution_proof_commitment: &str,
    bounded_fold_arity: usize,
    total_slices: usize,
    repeated_token_position: u64,
    start_block_index: u64,
    terminal_block_index: u64,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE965.as_bytes());
    hasher.update(STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE965.as_bytes());
    hasher.update(source_phase95_artifact_commitment.as_bytes());
    hasher.update(source_members_commitment.as_bytes());
    hasher.update(shared_primitive_artifact_commitment.as_bytes());
    hasher.update(shared_table_registry_commitment.as_bytes());
    hasher.update(shared_execution_proof_commitment.as_bytes());
    hasher.update(&(bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&(total_slices as u64).to_le_bytes());
    hasher.update(&repeated_token_position.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase965_folded_group_sequence(
    groups: &[Phase965FoldedGemmaSliceGroup],
) -> Result<String> {
    let json =
        serde_json::to_vec(groups).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase965/folded-group-sequence", &json)
}

fn commit_phase965_folded_slice_accumulator(
    fold_template_commitment: &str,
    folded_group_sequence_commitment: &str,
    global_start_boundary_commitment: &str,
    global_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    total_slices: usize,
    total_folded_groups: usize,
) -> Result<String> {
    #[derive(Serialize)]
    struct FoldedAccumulatorPayload<'a> {
        fold_template_commitment: &'a str,
        folded_group_sequence_commitment: &'a str,
        global_start_boundary_commitment: &'a str,
        global_end_boundary_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        total_slices: usize,
        total_folded_groups: usize,
    }
    let payload = FoldedAccumulatorPayload {
        fold_template_commitment,
        folded_group_sequence_commitment,
        global_start_boundary_commitment,
        global_end_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        total_slices,
        total_folded_groups,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase965/folded-slice-accumulator", &json)
}

fn commit_phase965_folded_gemma_slice_accumulation_artifact(
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    folded_groups: &[Phase965FoldedGemmaSliceGroup],
    fold_template_commitment: &str,
    folded_group_sequence_commitment: &str,
    folded_slice_accumulator_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    bounded_fold_arity: usize,
) -> Result<String> {
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 96.5 folded Gemma slice accumulation requires at least one source member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("source members are non-empty after first check");
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_VERSION_PHASE965.as_bytes());
    hasher.update(STWO_FOLDED_GEMMA_SLICE_ACCUMULATION_ARTIFACT_SCOPE_PHASE965.as_bytes());
    hasher.update(source.program_label.as_bytes());
    hasher.update(source.artifact_commitment.as_bytes());
    hasher.update(source.members_commitment.as_bytes());
    hasher.update(source.shared_primitive_artifact_commitment.as_bytes());
    hasher.update(source.shared_table_registry_commitment.as_bytes());
    hasher.update(source.shared_execution_proof_commitment.as_bytes());
    hasher.update(source.shared_execution_proof_backend_version.as_bytes());
    hasher.update(source.shared_execution_statement_version.as_bytes());
    hasher.update(&(source.total_slices as u64).to_le_bytes());
    hasher.update(&source.repeated_token_position.to_le_bytes());
    hasher.update(&source.start_block_index.to_le_bytes());
    hasher.update(&source.terminal_block_index.to_le_bytes());
    hasher.update(&(bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&(folded_groups.len() as u64).to_le_bytes());
    hasher.update(first_member.initial_boundary_commitment.as_bytes());
    hasher.update(last_member.terminal_boundary_commitment.as_bytes());
    hasher.update(first_member.richer_slice_artifact_commitment.as_bytes());
    hasher.update(last_member.richer_slice_artifact_commitment.as_bytes());
    hasher.update(fold_template_commitment.as_bytes());
    hasher.update(folded_group_sequence_commitment.as_bytes());
    hasher.update(&local_score_sum.to_le_bytes());
    hasher.update(&global_score_sum.to_le_bytes());
    hasher.update(&grouped_value_mix_sum.to_le_bytes());
    hasher.update(&residual_output_sum.to_le_bytes());
    hasher.update(&final_acc_sum.to_le_bytes());
    hasher.update(folded_slice_accumulator_commitment.as_bytes());
    let folded_groups_json = serde_json::to_vec(folded_groups)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(folded_groups_json.len() as u64).to_le_bytes());
    hasher.update(&folded_groups_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase98_richer_slice_sequence(family: &[Phase98InvariantSummaryEntry]) -> Result<String> {
    let commitments = family
        .iter()
        .map(|entry| entry.richer_slice_artifact_commitment.clone())
        .collect::<Vec<_>>();
    commit_namespace_strings("phase98/richer-slice-sequence", &commitments)
}

fn commit_phase98_selected_memory_window_family(
    family: &[Phase98InvariantSummaryEntry],
) -> Result<String> {
    let commitments = family
        .iter()
        .map(|entry| entry.selected_memory_window_commitment.clone())
        .collect::<Vec<_>>();
    commit_namespace_strings("phase98/selected-memory-window-family", &commitments)
}

fn commit_phase98_invariant_summary_family(
    family: &[Phase98InvariantSummaryEntry],
) -> Result<String> {
    let json =
        serde_json::to_vec(family).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase98/invariant-summary-family", &json)
}

fn commit_phase98_richer_family_template(
    source_phase95_artifact_commitment: &str,
    source_phase965_artifact_commitment: &str,
    shared_table_registry_commitment: &str,
    total_slices: usize,
    total_folded_groups: usize,
    bounded_fold_arity: usize,
    repeated_token_position: u64,
    start_block_index: u64,
    terminal_block_index: u64,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_VERSION_PHASE98.as_bytes());
    hasher.update(STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_SCOPE_PHASE98.as_bytes());
    hasher.update(source_phase95_artifact_commitment.as_bytes());
    hasher.update(source_phase965_artifact_commitment.as_bytes());
    hasher.update(shared_table_registry_commitment.as_bytes());
    hasher.update(&(total_slices as u64).to_le_bytes());
    hasher.update(&(total_folded_groups as u64).to_le_bytes());
    hasher.update(&(bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&repeated_token_position.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

#[allow(clippy::too_many_arguments)]
fn commit_phase98_folded_richer_family_accumulator(
    richer_family_template_commitment: &str,
    richer_slice_commitment_sequence_commitment: &str,
    selected_memory_window_family_commitment: &str,
    invariant_summary_family_commitment: &str,
    global_start_boundary_commitment: &str,
    global_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
) -> Result<String> {
    #[derive(Serialize)]
    struct FoldedRicherFamilyAccumulatorPayload<'a> {
        richer_family_template_commitment: &'a str,
        richer_slice_commitment_sequence_commitment: &'a str,
        selected_memory_window_family_commitment: &'a str,
        invariant_summary_family_commitment: &'a str,
        global_start_boundary_commitment: &'a str,
        global_end_boundary_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
    }
    let payload = FoldedRicherFamilyAccumulatorPayload {
        richer_family_template_commitment,
        richer_slice_commitment_sequence_commitment,
        selected_memory_window_family_commitment,
        invariant_summary_family_commitment,
        global_start_boundary_commitment,
        global_end_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase98/folded-richer-family-accumulator", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase98_folded_gemma_richer_slice_family_artifact(
    source: &Phase95RepeatedGemmaSliceAccumulationArtifact,
    folded: &Phase965FoldedGemmaSliceAccumulationArtifact,
    richer_family_template_commitment: &str,
    richer_slice_commitment_sequence_commitment: &str,
    selected_memory_window_family_commitment: &str,
    invariant_summary_family_commitment: &str,
    folded_richer_family_accumulator_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
) -> Result<String> {
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 98 folded Gemma richer slice family requires at least one source member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("source members are non-empty after first check");
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_VERSION_PHASE98.as_bytes());
    hasher.update(STWO_FOLDED_GEMMA_RICHER_SLICE_FAMILY_ARTIFACT_SCOPE_PHASE98.as_bytes());
    hasher.update(source.program_label.as_bytes());
    hasher.update(source.artifact_commitment.as_bytes());
    hasher.update(folded.artifact_commitment.as_bytes());
    hasher.update(source.shared_table_registry_commitment.as_bytes());
    hasher.update(&(source.total_slices as u64).to_le_bytes());
    hasher.update(&source.repeated_token_position.to_le_bytes());
    hasher.update(&source.start_block_index.to_le_bytes());
    hasher.update(&source.terminal_block_index.to_le_bytes());
    hasher.update(&(folded.total_folded_groups as u64).to_le_bytes());
    hasher.update(&(folded.bounded_fold_arity as u64).to_le_bytes());
    hasher.update(folded.global_start_boundary_commitment.as_bytes());
    hasher.update(folded.global_end_boundary_commitment.as_bytes());
    hasher.update(first_member.richer_slice_artifact_commitment.as_bytes());
    hasher.update(last_member.richer_slice_artifact_commitment.as_bytes());
    hasher.update(richer_family_template_commitment.as_bytes());
    hasher.update(richer_slice_commitment_sequence_commitment.as_bytes());
    hasher.update(selected_memory_window_family_commitment.as_bytes());
    hasher.update(invariant_summary_family_commitment.as_bytes());
    hasher.update(&local_score_sum.to_le_bytes());
    hasher.update(&global_score_sum.to_le_bytes());
    hasher.update(&grouped_value_mix_sum.to_le_bytes());
    hasher.update(&residual_output_sum.to_le_bytes());
    hasher.update(&final_acc_sum.to_le_bytes());
    hasher.update(&primary_norm_sq_min.to_le_bytes());
    hasher.update(&primary_norm_sq_max.to_le_bytes());
    hasher.update(&secondary_norm_sq_min.to_le_bytes());
    hasher.update(&secondary_norm_sq_max.to_le_bytes());
    hasher.update(&primary_activation_output_sum.to_le_bytes());
    hasher.update(&secondary_activation_output_sum.to_le_bytes());
    hasher.update(folded_richer_family_accumulator_commitment.as_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase99_multi_interval_member(
    member: &Phase99MultiIntervalGemmaRicherFamilyMember,
) -> Result<String> {
    #[derive(Serialize)]
    struct IntervalMemberPayload<'a> {
        interval_index: usize,
        repeated_token_position: u64,
        start_block_index: u64,
        terminal_block_index: u64,
        phase95_artifact_commitment: &'a str,
        phase965_artifact_commitment: &'a str,
        phase98_artifact_commitment: &'a str,
        global_start_boundary_commitment: &'a str,
        global_end_boundary_commitment: &'a str,
        first_richer_slice_artifact_commitment: &'a str,
        terminal_richer_slice_artifact_commitment: &'a str,
        richer_slice_commitment_sequence_commitment: &'a str,
        selected_memory_window_family_commitment: &'a str,
        invariant_summary_family_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
    }
    let payload = IntervalMemberPayload {
        interval_index: member.interval_index,
        repeated_token_position: member.repeated_token_position,
        start_block_index: member.start_block_index,
        terminal_block_index: member.terminal_block_index,
        phase95_artifact_commitment: &member.phase95_artifact_commitment,
        phase965_artifact_commitment: &member.phase965_artifact_commitment,
        phase98_artifact_commitment: &member.phase98_artifact_commitment,
        global_start_boundary_commitment: &member.global_start_boundary_commitment,
        global_end_boundary_commitment: &member.global_end_boundary_commitment,
        first_richer_slice_artifact_commitment: &member.first_richer_slice_artifact_commitment,
        terminal_richer_slice_artifact_commitment: &member
            .terminal_richer_slice_artifact_commitment,
        richer_slice_commitment_sequence_commitment: &member
            .richer_slice_commitment_sequence_commitment,
        selected_memory_window_family_commitment: &member.selected_memory_window_family_commitment,
        invariant_summary_family_commitment: &member.invariant_summary_family_commitment,
        local_score_sum: member.local_score_sum,
        global_score_sum: member.global_score_sum,
        grouped_value_mix_sum: member.grouped_value_mix_sum,
        residual_output_sum: member.residual_output_sum,
        final_acc_sum: member.final_acc_sum,
        primary_norm_sq_min: member.primary_norm_sq_min,
        primary_norm_sq_max: member.primary_norm_sq_max,
        secondary_norm_sq_min: member.secondary_norm_sq_min,
        secondary_norm_sq_max: member.secondary_norm_sq_max,
        primary_activation_output_sum: member.primary_activation_output_sum,
        secondary_activation_output_sum: member.secondary_activation_output_sum,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase99/multi-interval-member", &json)
}

fn commit_phase99_multi_interval_members(
    members: &[Phase99MultiIntervalGemmaRicherFamilyMember],
) -> Result<String> {
    let commitments = members
        .iter()
        .map(|member| member.interval_member_commitment.clone())
        .collect::<Vec<_>>();
    commit_namespace_strings("phase99/multi-interval-member-sequence", &commitments)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    shared_execution_proof_commitment: &str,
    interval_members_commitment: &str,
    total_intervals: usize,
    interval_total_slices: usize,
    token_position_start: u64,
    token_position_stride: u64,
    start_block_index: u64,
    terminal_token_position: u64,
    terminal_block_index: u64,
    global_interval_start_boundary_commitment: &str,
    global_interval_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(
        STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_VERSION_PHASE99.as_bytes(),
    );
    hasher.update(
        STWO_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ACCUMULATION_ARTIFACT_SCOPE_PHASE99.as_bytes(),
    );
    hasher.update(shared_primitive_artifact.artifact_commitment.as_bytes());
    hasher.update(
        shared_primitive_artifact
            .static_table_registry_commitment
            .as_bytes(),
    );
    hasher.update(shared_execution_proof_commitment.as_bytes());
    hasher.update(shared_execution_proof.proof_backend_version.as_bytes());
    hasher.update(shared_execution_proof.claim.statement_version.as_bytes());
    hasher.update(&(total_intervals as u64).to_le_bytes());
    hasher.update(&(interval_total_slices as u64).to_le_bytes());
    hasher.update(&token_position_start.to_le_bytes());
    hasher.update(&token_position_stride.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_token_position.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    hasher.update(interval_members_commitment.as_bytes());
    hasher.update(global_interval_start_boundary_commitment.as_bytes());
    hasher.update(global_interval_end_boundary_commitment.as_bytes());
    hasher.update(&local_score_sum.to_le_bytes());
    hasher.update(&global_score_sum.to_le_bytes());
    hasher.update(&grouped_value_mix_sum.to_le_bytes());
    hasher.update(&residual_output_sum.to_le_bytes());
    hasher.update(&final_acc_sum.to_le_bytes());
    hasher.update(&primary_norm_sq_min.to_le_bytes());
    hasher.update(&primary_norm_sq_max.to_le_bytes());
    hasher.update(&secondary_norm_sq_min.to_le_bytes());
    hasher.update(&secondary_norm_sq_max.to_le_bytes());
    hasher.update(&primary_activation_output_sum.to_le_bytes());
    hasher.update(&secondary_activation_output_sum.to_le_bytes());
    let primitive_json = serde_json::to_vec(shared_primitive_artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(primitive_json.len() as u64).to_le_bytes());
    hasher.update(&primitive_json);
    let proof_json = serde_json::to_vec(shared_execution_proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(proof_json.len() as u64).to_le_bytes());
    hasher.update(&proof_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase1015_folded_multi_interval_group(
    group: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup,
) -> Result<String> {
    #[derive(Serialize)]
    struct FoldedIntervalGroupPayload<'a> {
        folded_group_index: usize,
        start_interval_index: usize,
        terminal_interval_index: usize,
        start_token_position: u64,
        terminal_token_position: u64,
        first_phase98_artifact_commitment: &'a str,
        terminal_phase98_artifact_commitment: &'a str,
        global_start_boundary_commitment: &'a str,
        global_end_boundary_commitment: &'a str,
        interval_member_commitment_sequence_commitment: &'a str,
        interval_phase98_commitment_sequence_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
    }
    let payload = FoldedIntervalGroupPayload {
        folded_group_index: group.folded_group_index,
        start_interval_index: group.start_interval_index,
        terminal_interval_index: group.terminal_interval_index,
        start_token_position: group.start_token_position,
        terminal_token_position: group.terminal_token_position,
        first_phase98_artifact_commitment: &group.first_phase98_artifact_commitment,
        terminal_phase98_artifact_commitment: &group.terminal_phase98_artifact_commitment,
        global_start_boundary_commitment: &group.global_start_boundary_commitment,
        global_end_boundary_commitment: &group.global_end_boundary_commitment,
        interval_member_commitment_sequence_commitment: &group
            .interval_member_commitment_sequence_commitment,
        interval_phase98_commitment_sequence_commitment: &group
            .interval_phase98_commitment_sequence_commitment,
        local_score_sum: group.local_score_sum,
        global_score_sum: group.global_score_sum,
        grouped_value_mix_sum: group.grouped_value_mix_sum,
        residual_output_sum: group.residual_output_sum,
        final_acc_sum: group.final_acc_sum,
        primary_norm_sq_min: group.primary_norm_sq_min,
        primary_norm_sq_max: group.primary_norm_sq_max,
        secondary_norm_sq_min: group.secondary_norm_sq_min,
        secondary_norm_sq_max: group.secondary_norm_sq_max,
        primary_activation_output_sum: group.primary_activation_output_sum,
        secondary_activation_output_sum: group.secondary_activation_output_sum,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase1015/folded-multi-interval-group", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase1015_fold_template(
    source_phase99_artifact_commitment: &str,
    source_interval_members_commitment: &str,
    shared_primitive_artifact_commitment: &str,
    shared_table_registry_commitment: &str,
    shared_execution_proof_commitment: &str,
    bounded_fold_arity: usize,
    total_intervals: usize,
    interval_total_slices: usize,
    token_position_start: u64,
    token_position_stride: u64,
    start_block_index: u64,
    terminal_token_position: u64,
    terminal_block_index: u64,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(
        STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_VERSION_PHASE1015
            .as_bytes(),
    );
    hasher.update(
        STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_SCOPE_PHASE1015.as_bytes(),
    );
    hasher.update(source_phase99_artifact_commitment.as_bytes());
    hasher.update(source_interval_members_commitment.as_bytes());
    hasher.update(shared_primitive_artifact_commitment.as_bytes());
    hasher.update(shared_table_registry_commitment.as_bytes());
    hasher.update(shared_execution_proof_commitment.as_bytes());
    hasher.update(&(bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&(total_intervals as u64).to_le_bytes());
    hasher.update(&(interval_total_slices as u64).to_le_bytes());
    hasher.update(&token_position_start.to_le_bytes());
    hasher.update(&token_position_stride.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_token_position.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase1015_folded_interval_group_sequence(
    groups: &[Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup],
) -> Result<String> {
    let json =
        serde_json::to_vec(groups).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase1015/folded-interval-group-sequence", &json)
}

fn commit_phase1015_accumulation_handoff(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    fold_template_commitment: &str,
    folded_interval_group_sequence_commitment: &str,
    total_folded_interval_groups: usize,
    bounded_fold_arity: usize,
) -> Result<String> {
    #[derive(Serialize)]
    struct AccumulationHandoffPayload<'a> {
        source_phase99_artifact_commitment: &'a str,
        source_interval_members_commitment: &'a str,
        shared_primitive_artifact_commitment: &'a str,
        shared_table_registry_commitment: &'a str,
        shared_execution_proof_commitment: &'a str,
        total_intervals: usize,
        interval_total_slices: usize,
        token_position_start: u64,
        token_position_stride: u64,
        start_block_index: u64,
        terminal_token_position: u64,
        terminal_block_index: u64,
        bounded_fold_arity: usize,
        total_folded_interval_groups: usize,
        fold_template_commitment: &'a str,
        folded_interval_group_sequence_commitment: &'a str,
        global_interval_start_boundary_commitment: &'a str,
        global_interval_end_boundary_commitment: &'a str,
    }
    let payload = AccumulationHandoffPayload {
        source_phase99_artifact_commitment: &source.artifact_commitment,
        source_interval_members_commitment: &source.interval_members_commitment,
        shared_primitive_artifact_commitment: &source.shared_primitive_artifact_commitment,
        shared_table_registry_commitment: &source.shared_table_registry_commitment,
        shared_execution_proof_commitment: &source.shared_execution_proof_commitment,
        total_intervals: source.total_intervals,
        interval_total_slices: source.interval_total_slices,
        token_position_start: source.token_position_start,
        token_position_stride: source.token_position_stride,
        start_block_index: source.start_block_index,
        terminal_token_position: source.terminal_token_position,
        terminal_block_index: source.terminal_block_index,
        bounded_fold_arity,
        total_folded_interval_groups,
        fold_template_commitment,
        folded_interval_group_sequence_commitment,
        global_interval_start_boundary_commitment: &source
            .global_interval_start_boundary_commitment,
        global_interval_end_boundary_commitment: &source.global_interval_end_boundary_commitment,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase1015/accumulation-handoff", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase1015_folded_interval_prototype_accumulator(
    accumulation_handoff_commitment: &str,
    fold_template_commitment: &str,
    folded_interval_group_sequence_commitment: &str,
    global_interval_start_boundary_commitment: &str,
    global_interval_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
    total_folded_interval_groups: usize,
) -> Result<String> {
    #[derive(Serialize)]
    struct FoldedIntervalPrototypeAccumulatorPayload<'a> {
        accumulation_handoff_commitment: &'a str,
        fold_template_commitment: &'a str,
        folded_interval_group_sequence_commitment: &'a str,
        global_interval_start_boundary_commitment: &'a str,
        global_interval_end_boundary_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
        total_folded_interval_groups: usize,
    }
    let payload = FoldedIntervalPrototypeAccumulatorPayload {
        accumulation_handoff_commitment,
        fold_template_commitment,
        folded_interval_group_sequence_commitment,
        global_interval_start_boundary_commitment,
        global_interval_end_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
        total_folded_interval_groups,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase1015/folded-interval-prototype-accumulator", &json)
}

fn commit_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    folded_groups: &[Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeGroup],
    fold_template_commitment: &str,
    folded_interval_group_sequence_commitment: &str,
    accumulation_handoff_commitment: &str,
    folded_interval_prototype_accumulator_commitment: &str,
    bounded_fold_arity: usize,
) -> Result<String> {
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 101.5 folded multi-interval prototype requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("source members are non-empty after first check");
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(
        STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_VERSION_PHASE1015
            .as_bytes(),
    );
    hasher.update(
        STWO_FOLDED_MULTI_INTERVAL_GEMMA_ACCUMULATION_PROTOTYPE_ARTIFACT_SCOPE_PHASE1015.as_bytes(),
    );
    hasher.update(source.program_label.as_bytes());
    hasher.update(source.artifact_commitment.as_bytes());
    hasher.update(source.interval_members_commitment.as_bytes());
    hasher.update(source.shared_primitive_artifact_commitment.as_bytes());
    hasher.update(source.shared_table_registry_commitment.as_bytes());
    hasher.update(source.shared_execution_proof_commitment.as_bytes());
    hasher.update(source.shared_execution_proof_backend_version.as_bytes());
    hasher.update(source.shared_execution_statement_version.as_bytes());
    hasher.update(&(source.total_intervals as u64).to_le_bytes());
    hasher.update(&(source.interval_total_slices as u64).to_le_bytes());
    hasher.update(&source.token_position_start.to_le_bytes());
    hasher.update(&source.token_position_stride.to_le_bytes());
    hasher.update(&source.start_block_index.to_le_bytes());
    hasher.update(&source.terminal_token_position.to_le_bytes());
    hasher.update(&source.terminal_block_index.to_le_bytes());
    hasher.update(&(bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&(folded_groups.len() as u64).to_le_bytes());
    hasher.update(first_member.global_start_boundary_commitment.as_bytes());
    hasher.update(last_member.global_end_boundary_commitment.as_bytes());
    hasher.update(first_member.phase98_artifact_commitment.as_bytes());
    hasher.update(last_member.phase98_artifact_commitment.as_bytes());
    hasher.update(fold_template_commitment.as_bytes());
    hasher.update(folded_interval_group_sequence_commitment.as_bytes());
    hasher.update(&source.local_score_sum.to_le_bytes());
    hasher.update(&source.global_score_sum.to_le_bytes());
    hasher.update(&source.grouped_value_mix_sum.to_le_bytes());
    hasher.update(&source.residual_output_sum.to_le_bytes());
    hasher.update(&source.final_acc_sum.to_le_bytes());
    hasher.update(&source.primary_norm_sq_min.to_le_bytes());
    hasher.update(&source.primary_norm_sq_max.to_le_bytes());
    hasher.update(&source.secondary_norm_sq_min.to_le_bytes());
    hasher.update(&source.secondary_norm_sq_max.to_le_bytes());
    hasher.update(&source.primary_activation_output_sum.to_le_bytes());
    hasher.update(&source.secondary_activation_output_sum.to_le_bytes());
    hasher.update(accumulation_handoff_commitment.as_bytes());
    hasher.update(folded_interval_prototype_accumulator_commitment.as_bytes());
    let folded_groups_json = serde_json::to_vec(folded_groups)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(folded_groups_json.len() as u64).to_le_bytes());
    hasher.update(&folded_groups_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase102_folded_multi_interval_richer_group(
    group: &Phase102FoldedMultiIntervalGemmaRicherFamilyGroup,
) -> Result<String> {
    #[derive(Serialize)]
    struct FoldedRicherGroupPayload<'a> {
        folded_group_index: usize,
        start_interval_index: usize,
        terminal_interval_index: usize,
        start_token_position: u64,
        terminal_token_position: u64,
        first_phase98_artifact_commitment: &'a str,
        terminal_phase98_artifact_commitment: &'a str,
        global_start_boundary_commitment: &'a str,
        global_end_boundary_commitment: &'a str,
        interval_member_commitment_sequence_commitment: &'a str,
        interval_phase98_commitment_sequence_commitment: &'a str,
        interval_token_position_sequence_commitment: &'a str,
        richer_slice_family_commitment_sequence_commitment: &'a str,
        selected_memory_window_family_commitment_sequence_commitment: &'a str,
        invariant_summary_family_commitment_sequence_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
    }
    let payload = FoldedRicherGroupPayload {
        folded_group_index: group.folded_group_index,
        start_interval_index: group.start_interval_index,
        terminal_interval_index: group.terminal_interval_index,
        start_token_position: group.start_token_position,
        terminal_token_position: group.terminal_token_position,
        first_phase98_artifact_commitment: &group.first_phase98_artifact_commitment,
        terminal_phase98_artifact_commitment: &group.terminal_phase98_artifact_commitment,
        global_start_boundary_commitment: &group.global_start_boundary_commitment,
        global_end_boundary_commitment: &group.global_end_boundary_commitment,
        interval_member_commitment_sequence_commitment: &group
            .interval_member_commitment_sequence_commitment,
        interval_phase98_commitment_sequence_commitment: &group
            .interval_phase98_commitment_sequence_commitment,
        interval_token_position_sequence_commitment: &group
            .interval_token_position_sequence_commitment,
        richer_slice_family_commitment_sequence_commitment: &group
            .richer_slice_family_commitment_sequence_commitment,
        selected_memory_window_family_commitment_sequence_commitment: &group
            .selected_memory_window_family_commitment_sequence_commitment,
        invariant_summary_family_commitment_sequence_commitment: &group
            .invariant_summary_family_commitment_sequence_commitment,
        local_score_sum: group.local_score_sum,
        global_score_sum: group.global_score_sum,
        grouped_value_mix_sum: group.grouped_value_mix_sum,
        residual_output_sum: group.residual_output_sum,
        final_acc_sum: group.final_acc_sum,
        primary_norm_sq_min: group.primary_norm_sq_min,
        primary_norm_sq_max: group.primary_norm_sq_max,
        secondary_norm_sq_min: group.secondary_norm_sq_min,
        secondary_norm_sq_max: group.secondary_norm_sq_max,
        primary_activation_output_sum: group.primary_activation_output_sum,
        secondary_activation_output_sum: group.secondary_activation_output_sum,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase102/folded-multi-interval-richer-group", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase102_richer_fold_template(
    source_phase99_artifact_commitment: &str,
    source_phase1015_artifact_commitment: &str,
    source_interval_members_commitment: &str,
    shared_primitive_artifact_commitment: &str,
    shared_table_registry_commitment: &str,
    shared_execution_proof_commitment: &str,
    bounded_fold_arity: usize,
    total_intervals: usize,
    interval_total_slices: usize,
    token_position_start: u64,
    token_position_stride: u64,
    start_block_index: u64,
    terminal_token_position: u64,
    terminal_block_index: u64,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(
        STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE102.as_bytes(),
    );
    hasher
        .update(STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE102.as_bytes());
    hasher.update(source_phase99_artifact_commitment.as_bytes());
    hasher.update(source_phase1015_artifact_commitment.as_bytes());
    hasher.update(source_interval_members_commitment.as_bytes());
    hasher.update(shared_primitive_artifact_commitment.as_bytes());
    hasher.update(shared_table_registry_commitment.as_bytes());
    hasher.update(shared_execution_proof_commitment.as_bytes());
    hasher.update(&(bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&(total_intervals as u64).to_le_bytes());
    hasher.update(&(interval_total_slices as u64).to_le_bytes());
    hasher.update(&token_position_start.to_le_bytes());
    hasher.update(&token_position_stride.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_token_position.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase102_folded_richer_group_sequence(
    groups: &[Phase102FoldedMultiIntervalGemmaRicherFamilyGroup],
) -> Result<String> {
    let json =
        serde_json::to_vec(groups).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase102/folded-richer-group-sequence", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase102_folded_richer_multi_interval_family_accumulator(
    accumulation_handoff_commitment: &str,
    folded_interval_prototype_accumulator_commitment: &str,
    richer_fold_template_commitment: &str,
    folded_richer_group_sequence_commitment: &str,
    phase98_commitment_sequence_commitment: &str,
    token_position_sequence_commitment: &str,
    richer_slice_family_commitment_sequence_commitment: &str,
    selected_memory_window_family_commitment_sequence_commitment: &str,
    invariant_summary_family_commitment_sequence_commitment: &str,
    global_interval_start_boundary_commitment: &str,
    global_interval_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
    total_folded_richer_groups: usize,
) -> Result<String> {
    #[derive(Serialize)]
    struct FoldedRicherFamilyAccumulatorPayload<'a> {
        accumulation_handoff_commitment: &'a str,
        folded_interval_prototype_accumulator_commitment: &'a str,
        richer_fold_template_commitment: &'a str,
        folded_richer_group_sequence_commitment: &'a str,
        phase98_commitment_sequence_commitment: &'a str,
        token_position_sequence_commitment: &'a str,
        richer_slice_family_commitment_sequence_commitment: &'a str,
        selected_memory_window_family_commitment_sequence_commitment: &'a str,
        invariant_summary_family_commitment_sequence_commitment: &'a str,
        global_interval_start_boundary_commitment: &'a str,
        global_interval_end_boundary_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
        total_folded_richer_groups: usize,
    }
    let payload = FoldedRicherFamilyAccumulatorPayload {
        accumulation_handoff_commitment,
        folded_interval_prototype_accumulator_commitment,
        richer_fold_template_commitment,
        folded_richer_group_sequence_commitment,
        phase98_commitment_sequence_commitment,
        token_position_sequence_commitment,
        richer_slice_family_commitment_sequence_commitment,
        selected_memory_window_family_commitment_sequence_commitment,
        invariant_summary_family_commitment_sequence_commitment,
        global_interval_start_boundary_commitment,
        global_interval_end_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
        total_folded_richer_groups,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase102/folded-richer-family-accumulator", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase102_folded_multi_interval_gemma_richer_family_artifact(
    source: &Phase99MultiIntervalGemmaRicherFamilyAccumulationArtifact,
    folded: &Phase1015FoldedMultiIntervalGemmaAccumulationPrototypeArtifact,
    folded_groups: &[Phase102FoldedMultiIntervalGemmaRicherFamilyGroup],
    richer_fold_template_commitment: &str,
    folded_richer_group_sequence_commitment: &str,
    phase98_commitment_sequence_commitment: &str,
    token_position_sequence_commitment: &str,
    richer_slice_family_commitment_sequence_commitment: &str,
    selected_memory_window_family_commitment_sequence_commitment: &str,
    invariant_summary_family_commitment_sequence_commitment: &str,
    folded_richer_multi_interval_family_accumulator_commitment: &str,
) -> Result<String> {
    let first_member = source.members.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 102 folded richer-family artifact requires at least one interval member"
                .to_string(),
        )
    })?;
    let last_member = source
        .members
        .last()
        .expect("source members are non-empty after first check");
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(
        STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE102.as_bytes(),
    );
    hasher
        .update(STWO_FOLDED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE102.as_bytes());
    hasher.update(source.program_label.as_bytes());
    hasher.update(source.artifact_commitment.as_bytes());
    hasher.update(folded.artifact_commitment.as_bytes());
    hasher.update(source.interval_members_commitment.as_bytes());
    hasher.update(source.shared_primitive_artifact_commitment.as_bytes());
    hasher.update(source.shared_table_registry_commitment.as_bytes());
    hasher.update(source.shared_execution_proof_commitment.as_bytes());
    hasher.update(source.shared_execution_proof_backend_version.as_bytes());
    hasher.update(source.shared_execution_statement_version.as_bytes());
    hasher.update(&(source.total_intervals as u64).to_le_bytes());
    hasher.update(&(source.interval_total_slices as u64).to_le_bytes());
    hasher.update(&source.token_position_start.to_le_bytes());
    hasher.update(&source.token_position_stride.to_le_bytes());
    hasher.update(&source.start_block_index.to_le_bytes());
    hasher.update(&source.terminal_token_position.to_le_bytes());
    hasher.update(&source.terminal_block_index.to_le_bytes());
    hasher.update(&(folded.bounded_fold_arity as u64).to_le_bytes());
    hasher.update(&(folded_groups.len() as u64).to_le_bytes());
    hasher.update(first_member.global_start_boundary_commitment.as_bytes());
    hasher.update(last_member.global_end_boundary_commitment.as_bytes());
    hasher.update(first_member.phase98_artifact_commitment.as_bytes());
    hasher.update(last_member.phase98_artifact_commitment.as_bytes());
    hasher.update(richer_fold_template_commitment.as_bytes());
    hasher.update(folded_richer_group_sequence_commitment.as_bytes());
    hasher.update(phase98_commitment_sequence_commitment.as_bytes());
    hasher.update(token_position_sequence_commitment.as_bytes());
    hasher.update(richer_slice_family_commitment_sequence_commitment.as_bytes());
    hasher.update(selected_memory_window_family_commitment_sequence_commitment.as_bytes());
    hasher.update(invariant_summary_family_commitment_sequence_commitment.as_bytes());
    hasher.update(&source.local_score_sum.to_le_bytes());
    hasher.update(&source.global_score_sum.to_le_bytes());
    hasher.update(&source.grouped_value_mix_sum.to_le_bytes());
    hasher.update(&source.residual_output_sum.to_le_bytes());
    hasher.update(&source.final_acc_sum.to_le_bytes());
    hasher.update(&source.primary_norm_sq_min.to_le_bytes());
    hasher.update(&source.primary_norm_sq_max.to_le_bytes());
    hasher.update(&source.secondary_norm_sq_min.to_le_bytes());
    hasher.update(&source.secondary_norm_sq_max.to_le_bytes());
    hasher.update(&source.primary_activation_output_sum.to_le_bytes());
    hasher.update(&source.secondary_activation_output_sum.to_le_bytes());
    hasher.update(folded.accumulation_handoff_commitment.as_bytes());
    hasher.update(
        folded
            .folded_interval_prototype_accumulator_commitment
            .as_bytes(),
    );
    hasher.update(folded_richer_multi_interval_family_accumulator_commitment.as_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase105_repeated_multi_interval_member(
    member: &Phase105RepeatedMultiIntervalGemmaRicherFamilyMember,
) -> Result<String> {
    #[derive(Serialize)]
    struct RepeatedWindowMemberPayload<'a> {
        window_index: usize,
        total_intervals: usize,
        bounded_fold_arity: usize,
        total_folded_richer_groups: usize,
        token_position_start: u64,
        token_position_stride: u64,
        terminal_token_position: u64,
        start_block_index: u64,
        terminal_block_index: u64,
        source_phase99_artifact_commitment: &'a str,
        source_phase1015_artifact_commitment: &'a str,
        source_phase102_artifact_commitment: &'a str,
        global_interval_start_boundary_commitment: &'a str,
        global_interval_end_boundary_commitment: &'a str,
        accumulation_handoff_commitment: &'a str,
        folded_interval_prototype_accumulator_commitment: &'a str,
        phase98_commitment_sequence_commitment: &'a str,
        token_position_sequence_commitment: &'a str,
        selected_memory_window_family_commitment_sequence_commitment: &'a str,
        invariant_summary_family_commitment_sequence_commitment: &'a str,
        folded_richer_multi_interval_family_accumulator_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
    }
    let payload = RepeatedWindowMemberPayload {
        window_index: member.window_index,
        total_intervals: member.total_intervals,
        bounded_fold_arity: member.bounded_fold_arity,
        total_folded_richer_groups: member.total_folded_richer_groups,
        token_position_start: member.token_position_start,
        token_position_stride: member.token_position_stride,
        terminal_token_position: member.terminal_token_position,
        start_block_index: member.start_block_index,
        terminal_block_index: member.terminal_block_index,
        source_phase99_artifact_commitment: &member.source_phase99_artifact_commitment,
        source_phase1015_artifact_commitment: &member.source_phase1015_artifact_commitment,
        source_phase102_artifact_commitment: &member.source_phase102_artifact_commitment,
        global_interval_start_boundary_commitment: &member
            .global_interval_start_boundary_commitment,
        global_interval_end_boundary_commitment: &member.global_interval_end_boundary_commitment,
        accumulation_handoff_commitment: &member.accumulation_handoff_commitment,
        folded_interval_prototype_accumulator_commitment: &member
            .folded_interval_prototype_accumulator_commitment,
        phase98_commitment_sequence_commitment: &member.phase98_commitment_sequence_commitment,
        token_position_sequence_commitment: &member.token_position_sequence_commitment,
        selected_memory_window_family_commitment_sequence_commitment: &member
            .selected_memory_window_family_commitment_sequence_commitment,
        invariant_summary_family_commitment_sequence_commitment: &member
            .invariant_summary_family_commitment_sequence_commitment,
        folded_richer_multi_interval_family_accumulator_commitment: &member
            .folded_richer_multi_interval_family_accumulator_commitment,
        local_score_sum: member.local_score_sum,
        global_score_sum: member.global_score_sum,
        grouped_value_mix_sum: member.grouped_value_mix_sum,
        residual_output_sum: member.residual_output_sum,
        final_acc_sum: member.final_acc_sum,
        primary_norm_sq_min: member.primary_norm_sq_min,
        primary_norm_sq_max: member.primary_norm_sq_max,
        secondary_norm_sq_min: member.secondary_norm_sq_min,
        secondary_norm_sq_max: member.secondary_norm_sq_max,
        primary_activation_output_sum: member.primary_activation_output_sum,
        secondary_activation_output_sum: member.secondary_activation_output_sum,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase105/repeated-multi-interval-member", &json)
}

fn commit_phase105_repeated_multi_interval_members(
    members: &[Phase105RepeatedMultiIntervalGemmaRicherFamilyMember],
) -> Result<String> {
    let commitments = members
        .iter()
        .map(|member| member.window_member_commitment.clone())
        .collect::<Vec<_>>();
    commit_namespace_strings(
        "phase105/repeated-multi-interval-member-sequence",
        &commitments,
    )
}

#[allow(clippy::too_many_arguments)]
fn commit_phase105_repeated_multi_interval_family_accumulator(
    window_members_commitment: &str,
    phase102_artifact_commitment_sequence_commitment: &str,
    accumulation_handoff_commitment_sequence_commitment: &str,
    folded_richer_multi_interval_family_accumulator_sequence_commitment: &str,
    global_window_start_boundary_commitment: &str,
    global_window_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
    total_windows: usize,
) -> Result<String> {
    #[derive(Serialize)]
    struct RepeatedWindowAccumulatorPayload<'a> {
        window_members_commitment: &'a str,
        phase102_artifact_commitment_sequence_commitment: &'a str,
        accumulation_handoff_commitment_sequence_commitment: &'a str,
        folded_richer_multi_interval_family_accumulator_sequence_commitment: &'a str,
        global_window_start_boundary_commitment: &'a str,
        global_window_end_boundary_commitment: &'a str,
        local_score_sum: i64,
        global_score_sum: i64,
        grouped_value_mix_sum: i64,
        residual_output_sum: i64,
        final_acc_sum: i64,
        primary_norm_sq_min: i16,
        primary_norm_sq_max: i16,
        secondary_norm_sq_min: i16,
        secondary_norm_sq_max: i16,
        primary_activation_output_sum: i64,
        secondary_activation_output_sum: i64,
        total_windows: usize,
    }
    let payload = RepeatedWindowAccumulatorPayload {
        window_members_commitment,
        phase102_artifact_commitment_sequence_commitment,
        accumulation_handoff_commitment_sequence_commitment,
        folded_richer_multi_interval_family_accumulator_sequence_commitment,
        global_window_start_boundary_commitment,
        global_window_end_boundary_commitment,
        local_score_sum,
        global_score_sum,
        grouped_value_mix_sum,
        residual_output_sum,
        final_acc_sum,
        primary_norm_sq_min,
        primary_norm_sq_max,
        secondary_norm_sq_min,
        secondary_norm_sq_max,
        primary_activation_output_sum,
        secondary_activation_output_sum,
        total_windows,
    };
    let json =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes("phase105/repeated-multi-interval-family-accumulator", &json)
}

#[allow(clippy::too_many_arguments)]
fn commit_phase105_repeated_multi_interval_gemma_richer_family_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    shared_execution_proof_commitment: &str,
    window_members_commitment: &str,
    total_windows: usize,
    intervals_per_window: usize,
    interval_total_slices: usize,
    token_position_start: u64,
    token_position_stride: u64,
    window_token_position_stride: u64,
    start_block_index: u64,
    terminal_token_position: u64,
    terminal_block_index: u64,
    phase102_artifact_commitment_sequence_commitment: &str,
    accumulation_handoff_commitment_sequence_commitment: &str,
    folded_richer_multi_interval_family_accumulator_sequence_commitment: &str,
    global_window_start_boundary_commitment: &str,
    global_window_end_boundary_commitment: &str,
    local_score_sum: i64,
    global_score_sum: i64,
    grouped_value_mix_sum: i64,
    residual_output_sum: i64,
    final_acc_sum: i64,
    primary_norm_sq_min: i16,
    primary_norm_sq_max: i16,
    secondary_norm_sq_min: i16,
    secondary_norm_sq_max: i16,
    primary_activation_output_sum: i64,
    secondary_activation_output_sum: i64,
    repeated_multi_interval_family_accumulator_commitment: &str,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(
        STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_VERSION_PHASE105.as_bytes(),
    );
    hasher.update(
        STWO_REPEATED_MULTI_INTERVAL_GEMMA_RICHER_FAMILY_ARTIFACT_SCOPE_PHASE105.as_bytes(),
    );
    hasher.update(shared_primitive_artifact.artifact_commitment.as_bytes());
    hasher.update(
        shared_primitive_artifact
            .static_table_registry_commitment
            .as_bytes(),
    );
    hasher.update(shared_execution_proof_commitment.as_bytes());
    hasher.update(shared_execution_proof.proof_backend_version.as_bytes());
    hasher.update(shared_execution_proof.claim.statement_version.as_bytes());
    hasher.update(&(total_windows as u64).to_le_bytes());
    hasher.update(&(intervals_per_window as u64).to_le_bytes());
    hasher.update(&(interval_total_slices as u64).to_le_bytes());
    hasher.update(&token_position_start.to_le_bytes());
    hasher.update(&token_position_stride.to_le_bytes());
    hasher.update(&window_token_position_stride.to_le_bytes());
    hasher.update(&start_block_index.to_le_bytes());
    hasher.update(&terminal_token_position.to_le_bytes());
    hasher.update(&terminal_block_index.to_le_bytes());
    hasher.update(window_members_commitment.as_bytes());
    hasher.update(phase102_artifact_commitment_sequence_commitment.as_bytes());
    hasher.update(accumulation_handoff_commitment_sequence_commitment.as_bytes());
    hasher.update(folded_richer_multi_interval_family_accumulator_sequence_commitment.as_bytes());
    hasher.update(global_window_start_boundary_commitment.as_bytes());
    hasher.update(global_window_end_boundary_commitment.as_bytes());
    hasher.update(&local_score_sum.to_le_bytes());
    hasher.update(&global_score_sum.to_le_bytes());
    hasher.update(&grouped_value_mix_sum.to_le_bytes());
    hasher.update(&residual_output_sum.to_le_bytes());
    hasher.update(&final_acc_sum.to_le_bytes());
    hasher.update(&primary_norm_sq_min.to_le_bytes());
    hasher.update(&primary_norm_sq_max.to_le_bytes());
    hasher.update(&secondary_norm_sq_min.to_le_bytes());
    hasher.update(&secondary_norm_sq_max.to_le_bytes());
    hasher.update(&primary_activation_output_sum.to_le_bytes());
    hasher.update(&secondary_activation_output_sum.to_le_bytes());
    hasher.update(repeated_multi_interval_family_accumulator_commitment.as_bytes());
    let primitive_json = serde_json::to_vec(shared_primitive_artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(primitive_json.len() as u64).to_le_bytes());
    hasher.update(&primitive_json);
    let proof_json = serde_json::to_vec(shared_execution_proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(proof_json.len() as u64).to_le_bytes());
    hasher.update(&proof_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_namespace_u64s(namespace: &str, values: &[u64]) -> Result<String> {
    let json =
        serde_json::to_vec(values).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes(namespace, &json)
}

fn commit_namespace_strings(namespace: &str, values: &[String]) -> Result<String> {
    let json =
        serde_json::to_vec(values).map_err(|error| VmError::Serialization(error.to_string()))?;
    commit_namespace_bytes(namespace, &json)
}

fn commit_namespace_bytes(namespace: &str, bytes: &[u8]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(namespace.as_bytes());
    hasher.update(&(bytes.len() as u64).to_le_bytes());
    hasher.update(bytes);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn lower_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::{Attention2DMode, TransformerVmConfig};
    use crate::proof::{
        production_v1_stark_options, prove_execution_stark_with_backend_and_options,
    };
    use crate::ProgramCompiler;

    fn prove_gemma_block_v4_execution() -> VanillaStarkExecutionProof {
        let model = ProgramCompiler
            .compile_source(
                include_str!("../../programs/gemma_block_v4.tvm"),
                TransformerVmConfig {
                    attention_mode: Attention2DMode::AverageHard,
                    ..TransformerVmConfig::default()
                },
            )
            .expect("compile gemma_block_v4");
        prove_execution_stark_with_backend_and_options(
            &model,
            256,
            StarkProofBackend::Stwo,
            production_v1_stark_options(),
        )
        .expect("prove gemma_block_v4")
    }

    #[test]
    fn phase93_tensor_native_chain_round_trips() {
        let artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 tensor-native chain artifact");
        assert_eq!(artifact.total_steps, 4);
        assert_eq!(
            artifact.artifact_version,
            STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_VERSION_PHASE93
        );
        assert_eq!(
            artifact.semantic_scope,
            STWO_TENSOR_NATIVE_CHAIN_ARTIFACT_SCOPE_PHASE93
        );
        verify_phase93_tensor_native_chain_artifact(&artifact)
            .expect("verify phase93 tensor-native chain artifact");
    }

    #[test]
    fn phase93_tensor_native_chain_rejects_continuity_drift() {
        let mut artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 tensor-native chain artifact");
        artifact.steps[1].carried_state_in.hidden_state_commitment = "bad".to_string();
        let error = verify_phase93_tensor_native_chain_artifact(&artifact)
            .expect_err("continuity drift should fail");
        assert!(
            error.to_string().contains("continuity mismatch")
                || error.to_string().contains("carried_state_in commitment")
        );
    }

    #[test]
    fn phase93_tensor_native_chain_rejects_template_label_drift() {
        let mut artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 tensor-native chain artifact");
        artifact.steps[2].primitive_template_step_label = "wrong".to_string();
        let error = verify_phase93_tensor_native_chain_artifact(&artifact)
            .expect_err("template label drift should fail");
        assert!(error.to_string().contains("primitive template label"));
    }

    #[test]
    fn phase93_tensor_native_chain_round_trips_on_disk() {
        let artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 tensor-native chain artifact");
        let temp = tempfile::NamedTempFile::new().expect("temp chain artifact");
        save_phase93_tensor_native_chain_artifact(&artifact, temp.path())
            .expect("save phase93 tensor-native chain artifact");
        let loaded = load_phase93_tensor_native_chain_artifact(temp.path())
            .expect("load phase93 tensor-native chain artifact");
        assert_eq!(loaded, artifact);
    }

    #[test]
    fn phase945_gemma_block_core_slice_round_trips() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let artifact =
            prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &execution_proof)
                .expect("prepare phase94.5 gemma core slice artifact");
        assert_eq!(artifact.total_shared_normalization_rows, 2);
        assert_eq!(artifact.total_shared_activation_rows, 2);
        assert_eq!(artifact.program_label, "gemma_block_v4");
        verify_phase945_gemma_block_core_slice_artifact(&artifact)
            .expect("verify phase94.5 gemma core slice artifact");
    }

    #[test]
    fn phase9475_gemma_block_richer_slice_round_trips() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let core_slice =
            prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &execution_proof)
                .expect("prepare phase94.5 gemma core slice artifact");
        let artifact = prepare_phase9475_gemma_block_richer_slice_artifact(&core_slice)
            .expect("prepare phase94.75 gemma richer slice artifact");
        assert_eq!(artifact.local_score, 2);
        assert_eq!(artifact.global_score, 2);
        assert_eq!(artifact.grouped_value_mix, 8);
        assert_eq!(artifact.residual_output, 4);
        assert_eq!(artifact.selected_memory_window.len(), 12);
        verify_phase9475_gemma_block_richer_slice_artifact(&artifact)
            .expect("verify phase94.75 gemma richer slice artifact");
    }

    #[test]
    fn phase9475_gemma_block_richer_slice_rejects_memory_window_drift() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let core_slice =
            prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &execution_proof)
                .expect("prepare phase94.5 gemma core slice artifact");
        let mut artifact = prepare_phase9475_gemma_block_richer_slice_artifact(&core_slice)
            .expect("prepare phase94.75 gemma richer slice artifact");
        artifact.selected_memory_window[3].value = 9;
        let error = verify_phase9475_gemma_block_richer_slice_artifact(&artifact)
            .expect_err("tampered memory window should fail");
        assert!(
            error.to_string().contains("selected_memory_window")
                || error
                    .to_string()
                    .contains("selected_memory_window_commitment")
        );
    }

    #[test]
    fn phase95_repeated_gemma_slice_accumulation_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let artifact = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            0,
        )
        .expect("prepare phase95 accumulation artifact");
        assert_eq!(artifact.total_slices, 4);
        assert_eq!(artifact.members.len(), 4);
        assert_eq!(artifact.members[0].block_index, 0);
        assert_eq!(artifact.members[3].block_index, 3);
        verify_phase95_repeated_gemma_slice_accumulation_artifact(&artifact)
            .expect("verify phase95 accumulation artifact");
    }

    #[test]
    fn phase95_repeated_gemma_slice_accumulation_rejects_member_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let mut artifact = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            3,
            0,
            0,
        )
        .expect("prepare phase95 accumulation artifact");
        artifact.members[1].block_index = 9;
        let error = verify_phase95_repeated_gemma_slice_accumulation_artifact(&artifact)
            .expect_err("tampered member block index should fail");
        assert!(
            error.to_string().contains("block_index") || error.to_string().contains("member 1")
        );
    }

    #[test]
    fn phase95_repeated_gemma_slice_accumulation_rejects_oversized_total_slices() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let error = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            MAX_PHASE95_REPEATED_GEMMA_TOTAL_SLICES + 1,
            0,
            0,
        )
        .expect_err("oversized total_slices should fail");
        assert!(error.to_string().contains("at most"));
    }

    #[test]
    fn phase95_repeated_gemma_slice_accumulation_rejects_block_index_overflow() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let error = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            2,
            0,
            u64::MAX,
        )
        .expect_err("overflowing start_block_index should fail");
        assert!(error.to_string().contains("overflow"));
    }

    #[test]
    fn phase95_repeated_gemma_slice_accumulation_verify_rejects_terminal_overflow() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let mut artifact = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            2,
            0,
            0,
        )
        .expect("prepare phase95 accumulation artifact");
        artifact.start_block_index = u64::MAX;
        artifact.terminal_block_index = u64::MAX;
        let error = verify_phase95_repeated_gemma_slice_accumulation_artifact(&artifact)
            .expect_err("overflowing terminal interval should fail");
        assert!(error.to_string().contains("overflow"));
    }

    #[test]
    fn phase965_folded_gemma_slice_accumulation_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            2,
        )
        .expect("prepare phase95 source artifact");
        let artifact = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        assert_eq!(artifact.total_slices, 4);
        assert_eq!(
            artifact.bounded_fold_arity,
            PHASE965_DEFAULT_BOUNDED_FOLD_ARITY
        );
        assert_eq!(artifact.total_folded_groups, 2);
        assert_eq!(artifact.folded_groups.len(), 2);
        assert_eq!(artifact.local_score_sum, 8);
        assert_eq!(artifact.global_score_sum, 8);
        assert_eq!(artifact.grouped_value_mix_sum, 32);
        assert_eq!(artifact.residual_output_sum, 16);
        verify_phase965_folded_gemma_slice_accumulation_artifact(&artifact, &source)
            .expect("verify phase96.5 folded artifact");
    }

    #[test]
    fn phase965_folded_gemma_slice_accumulation_rejects_source_commitment_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            0,
        )
        .expect("prepare phase95 source artifact");
        let mut artifact = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        artifact.source_phase95_artifact_commitment = "bad-source".to_string();
        let error = verify_phase965_folded_gemma_slice_accumulation_artifact(&artifact, &source)
            .expect_err("tampered source artifact commitment should fail");
        assert!(error
            .to_string()
            .contains("source_phase95_artifact_commitment"));
    }

    #[test]
    fn phase965_folded_gemma_slice_accumulation_rejects_group_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            0,
        )
        .expect("prepare phase95 source artifact");
        let mut artifact = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        artifact.folded_groups[0].terminal_block_index += 1;
        let error = verify_phase965_folded_gemma_slice_accumulation_artifact(&artifact, &source)
            .expect_err("tampered folded group should fail");
        assert!(error.to_string().contains("folded_groups"));
    }

    #[test]
    fn phase965_folded_gemma_slice_accumulation_rejects_accumulator_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            0,
        )
        .expect("prepare phase95 source artifact");
        let mut artifact = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        artifact.folded_slice_accumulator_commitment = "bad-accumulator".to_string();
        let error = verify_phase965_folded_gemma_slice_accumulation_artifact(&artifact, &source)
            .expect_err("tampered accumulator commitment should fail");
        assert!(error
            .to_string()
            .contains("folded_slice_accumulator_commitment"));
    }

    #[test]
    fn phase98_folded_gemma_richer_slice_family_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            2,
        )
        .expect("prepare phase95 source artifact");
        let folded = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        let artifact = prepare_phase98_folded_gemma_richer_slice_family_artifact(&source, &folded)
            .expect("prepare phase98 richer family artifact");
        assert_eq!(artifact.total_slices, 4);
        assert_eq!(artifact.total_folded_groups, 2);
        assert_eq!(artifact.local_score_sum, 8);
        assert_eq!(artifact.global_score_sum, 8);
        assert_eq!(artifact.grouped_value_mix_sum, 32);
        assert_eq!(artifact.residual_output_sum, 16);
        assert_eq!(artifact.primary_norm_sq_min, 16);
        assert_eq!(artifact.primary_norm_sq_max, 16);
        assert_eq!(artifact.secondary_norm_sq_min, 4);
        assert_eq!(artifact.secondary_norm_sq_max, 4);
        assert_eq!(artifact.primary_activation_output_sum, 4);
        assert_eq!(artifact.secondary_activation_output_sum, 4);
        verify_phase98_folded_gemma_richer_slice_family_artifact(&artifact, &source, &folded)
            .expect("verify phase98 richer family artifact");
    }

    #[test]
    fn phase98_folded_gemma_richer_slice_family_rejects_memory_window_family_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            0,
        )
        .expect("prepare phase95 source artifact");
        let folded = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        let mut artifact =
            prepare_phase98_folded_gemma_richer_slice_family_artifact(&source, &folded)
                .expect("prepare phase98 richer family artifact");
        artifact.selected_memory_window_family_commitment = "bad-memory-family".to_string();
        let error =
            verify_phase98_folded_gemma_richer_slice_family_artifact(&artifact, &source, &folded)
                .expect_err("tampered memory window family commitment should fail");
        assert!(error
            .to_string()
            .contains("selected_memory_window_family_commitment"));
    }

    #[test]
    fn phase98_folded_gemma_richer_slice_family_rejects_summary_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase95_repeated_gemma_slice_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            0,
            0,
        )
        .expect("prepare phase95 source artifact");
        let folded = prepare_phase965_folded_gemma_slice_accumulation_artifact(&source)
            .expect("prepare phase96.5 folded artifact");
        let mut artifact =
            prepare_phase98_folded_gemma_richer_slice_family_artifact(&source, &folded)
                .expect("prepare phase98 richer family artifact");
        artifact.primary_norm_sq_max = 17;
        let error =
            verify_phase98_folded_gemma_richer_slice_family_artifact(&artifact, &source, &folded)
                .expect_err("tampered richer-family summary should fail");
        assert!(error.to_string().contains("richer-family summaries"));
    }

    #[test]
    fn phase99_multi_interval_gemma_richer_family_accumulation_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let artifact = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            4,
            1,
            2,
            2,
        )
        .expect("prepare phase99 multi-interval artifact");
        assert_eq!(artifact.total_intervals, 4);
        assert_eq!(artifact.interval_total_slices, 4);
        assert_eq!(artifact.token_position_start, 1);
        assert_eq!(artifact.token_position_stride, 2);
        assert_eq!(artifact.terminal_token_position, 7);
        assert_eq!(artifact.terminal_block_index, 5);
        assert_eq!(artifact.members.len(), 4);
        assert_eq!(artifact.local_score_sum, 32);
        assert_eq!(artifact.global_score_sum, 32);
        assert_eq!(artifact.grouped_value_mix_sum, 128);
        assert_eq!(artifact.residual_output_sum, 64);
        assert_eq!(artifact.primary_activation_output_sum, 16);
        assert_eq!(artifact.secondary_activation_output_sum, 16);
        verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(&artifact)
            .expect("verify phase99 multi-interval artifact");
    }

    #[test]
    fn phase99_multi_interval_gemma_richer_family_accumulation_rejects_interval_member_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let mut artifact =
            prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
                &primitive_artifact,
                &execution_proof,
                3,
                4,
                0,
                1,
                2,
            )
            .expect("prepare phase99 multi-interval artifact");
        artifact.members[1].repeated_token_position = 99;
        let error =
            verify_phase99_multi_interval_gemma_richer_family_accumulation_artifact(&artifact)
                .expect_err("tampered interval member should fail");
        assert!(
            error.to_string().contains("interval member 1")
                || error.to_string().contains("canonical reconstructed")
        );
    }

    #[test]
    fn phase1015_folded_multi_interval_gemma_accumulation_prototype_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            4,
            0,
            1,
            2,
        )
        .expect("prepare phase99 source artifact");
        let artifact =
            prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(&source)
                .expect("prepare phase101.5 folded prototype");
        assert_eq!(artifact.total_intervals, 4);
        assert_eq!(
            artifact.bounded_fold_arity,
            PHASE1015_DEFAULT_BOUNDED_FOLD_ARITY
        );
        assert_eq!(artifact.total_folded_interval_groups, 2);
        assert_eq!(artifact.folded_groups.len(), 2);
        assert_eq!(artifact.local_score_sum, source.local_score_sum);
        assert_eq!(
            artifact.accumulation_handoff_commitment.len(),
            64,
            "blake2b-256 hex"
        );
        verify_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
            &artifact, &source,
        )
        .expect("verify phase101.5 folded prototype");
    }

    #[test]
    fn phase1015_folded_multi_interval_gemma_accumulation_prototype_rejects_handoff_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            4,
            0,
            1,
            2,
        )
        .expect("prepare phase99 source artifact");
        let mut artifact =
            prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(&source)
                .expect("prepare phase101.5 folded prototype");
        artifact.accumulation_handoff_commitment = "bad-handoff".to_string();
        let error = verify_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(
            &artifact, &source,
        )
        .expect_err("tampered handoff commitment should fail");
        assert!(error
            .to_string()
            .contains("accumulation_handoff_commitment"));
    }

    #[test]
    fn phase102_folded_multi_interval_gemma_richer_family_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            4,
            1,
            2,
            2,
        )
        .expect("prepare phase99 source artifact");
        let folded =
            prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(&source)
                .expect("prepare phase101.5 folded prototype");
        let artifact =
            prepare_phase102_folded_multi_interval_gemma_richer_family_artifact(&source, &folded)
                .expect("prepare phase102 richer family artifact");
        assert_eq!(artifact.total_intervals, 4);
        assert_eq!(artifact.interval_total_slices, 4);
        assert_eq!(artifact.token_position_start, 1);
        assert_eq!(artifact.token_position_stride, 2);
        assert_eq!(artifact.terminal_token_position, 7);
        assert_eq!(
            artifact.bounded_fold_arity,
            PHASE1015_DEFAULT_BOUNDED_FOLD_ARITY
        );
        assert_eq!(artifact.total_folded_richer_groups, 2);
        assert_eq!(artifact.folded_groups.len(), 2);
        assert_eq!(artifact.local_score_sum, source.local_score_sum);
        assert_eq!(
            artifact
                .folded_richer_multi_interval_family_accumulator_commitment
                .len(),
            64,
            "blake2b-256 hex"
        );
        verify_phase102_folded_multi_interval_gemma_richer_family_artifact(
            &artifact, &source, &folded,
        )
        .expect("verify phase102 richer family artifact");
    }

    #[test]
    fn phase102_folded_multi_interval_gemma_richer_family_rejects_sequence_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let source = prepare_phase99_multi_interval_gemma_richer_family_accumulation_artifact(
            &primitive_artifact,
            &execution_proof,
            4,
            4,
            0,
            1,
            2,
        )
        .expect("prepare phase99 source artifact");
        let folded =
            prepare_phase1015_folded_multi_interval_gemma_accumulation_prototype_artifact(&source)
                .expect("prepare phase101.5 folded prototype");
        let mut artifact =
            prepare_phase102_folded_multi_interval_gemma_richer_family_artifact(&source, &folded)
                .expect("prepare phase102 richer family artifact");
        artifact.selected_memory_window_family_commitment_sequence_commitment =
            "bad-sequence".to_string();
        let error = verify_phase102_folded_multi_interval_gemma_richer_family_artifact(
            &artifact, &source, &folded,
        )
        .expect_err("tampered richer family sequence should fail");
        assert!(error
            .to_string()
            .contains("selected_memory_window_family_commitment_sequence_commitment"));
    }

    #[test]
    fn phase105_repeated_multi_interval_gemma_richer_family_round_trips() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let artifact =
            prepare_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
                &primitive_artifact,
                &execution_proof,
                2,
                2,
                2,
                0,
                1,
                0,
            )
            .expect("prepare phase105 repeated multi-interval artifact");
        assert_eq!(artifact.total_windows, 2);
        assert_eq!(artifact.intervals_per_window, 2);
        assert_eq!(artifact.interval_total_slices, 2);
        assert_eq!(artifact.window_token_position_stride, 2);
        assert_eq!(artifact.terminal_token_position, 3);
        assert_eq!(artifact.members.len(), 2);
        assert_eq!(
            artifact
                .repeated_multi_interval_family_accumulator_commitment
                .len(),
            64,
            "blake2b-256 hex"
        );
        verify_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
            &artifact,
        )
        .expect("verify phase105 repeated multi-interval artifact");
    }

    #[test]
    fn phase105_repeated_multi_interval_gemma_richer_family_rejects_handoff_sequence_drift() {
        let primitive_artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 primitive artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let mut artifact =
            prepare_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
                &primitive_artifact,
                &execution_proof,
                2,
                2,
                2,
                0,
                1,
                0,
            )
            .expect("prepare phase105 repeated multi-interval artifact");
        artifact.accumulation_handoff_commitment_sequence_commitment = "bad-sequence".to_string();
        let error =
            verify_phase105_repeated_multi_interval_gemma_richer_family_accumulation_artifact(
                &artifact,
            )
            .expect_err("tampered handoff sequence should fail");
        assert!(error
            .to_string()
            .contains("accumulation_handoff_commitment_sequence_commitment"));
    }

    #[test]
    fn phase945_gemma_block_core_slice_rejects_normalization_row_set_drift() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let mut artifact =
            prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &execution_proof)
                .expect("prepare phase94.5 gemma core slice artifact");
        artifact.shared_normalization_rows[1].inv_sqrt_q8 = 65;
        let error = verify_phase945_gemma_block_core_slice_artifact(&artifact)
            .expect_err("normalization row drift should fail");
        assert!(
            error.to_string().contains("shared_normalization_rows")
                || error
                    .to_string()
                    .contains("normalization_row_set_commitment")
        );
    }

    #[test]
    fn phase945_gemma_block_core_slice_rejects_chain_drift() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let mut artifact =
            prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &execution_proof)
                .expect("prepare phase94.5 gemma core slice artifact");
        artifact.chain_artifact.steps[0].step_label = "bad".to_string();
        let error = verify_phase945_gemma_block_core_slice_artifact(&artifact)
            .expect_err("chain drift should fail");
        assert!(
            error.to_string().contains("step_label")
                || error.to_string().contains("chain_artifact_commitment")
                || error.to_string().contains("Phase 93 tensor-native chain")
        );
    }

    #[test]
    fn phase945_gemma_block_core_slice_round_trips_on_disk() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let execution_proof = prove_gemma_block_v4_execution();
        let artifact =
            prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &execution_proof)
                .expect("prepare phase94.5 gemma core slice artifact");
        let temp = tempfile::NamedTempFile::new().expect("temp gemma slice artifact");
        save_phase945_gemma_block_core_slice_artifact(&artifact, temp.path())
            .expect("save phase94.5 gemma core slice artifact");
        let loaded = load_phase945_gemma_block_core_slice_artifact(temp.path())
            .expect("load phase94.5 gemma core slice artifact");
        assert_eq!(loaded, artifact);
    }

    #[test]
    fn phase945_gemma_block_core_slice_rejects_non_gemma_proof() {
        let chain_artifact = prepare_phase93_tensor_native_chain_demo_artifact()
            .expect("prepare phase93 chain artifact");
        let addition_model = ProgramCompiler
            .compile_source(
                include_str!("../../programs/addition.tvm"),
                TransformerVmConfig {
                    attention_mode: Attention2DMode::AverageHard,
                    ..TransformerVmConfig::default()
                },
            )
            .expect("compile addition");
        let proof = prove_execution_stark_with_backend_and_options(
            &addition_model,
            32,
            StarkProofBackend::Stwo,
            production_v1_stark_options(),
        )
        .expect("prove addition with stwo");
        let error = prepare_phase945_gemma_block_core_slice_artifact(&chain_artifact, &proof)
            .expect_err("non-gemma proof should fail");
        assert!(error
            .to_string()
            .contains("canonical `programs/gemma_block_v4.tvm`"));
    }
}
