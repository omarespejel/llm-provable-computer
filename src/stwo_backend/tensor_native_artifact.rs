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

const MAX_PHASE93_TENSOR_NATIVE_CHAIN_JSON_BYTES: usize = 8 * 1024 * 1024;
const MAX_PHASE945_GEMMA_BLOCK_CORE_SLICE_JSON_BYTES: usize = 32 * 1024 * 1024;
const MAX_PHASE9475_GEMMA_BLOCK_RICHER_SLICE_JSON_BYTES: usize = 32 * 1024 * 1024;
const MAX_PHASE95_REPEATED_GEMMA_SLICE_ACCUMULATION_JSON_BYTES: usize = 64 * 1024 * 1024;
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
    let steps = phase93_default_tensor_native_chain_steps(
        primitive_artifact,
        token_position,
        block_index,
    )?;
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
    let selected_memory_window =
        phase9475_selected_memory_window(&core_slice_artifact.execution_proof.claim.final_state.memory)?;
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
    if artifact.chain_artifact_commitment != artifact.core_slice_artifact.chain_artifact_commitment {
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

    let expected_memory_window =
        phase9475_selected_memory_window(&artifact.core_slice_artifact.execution_proof.claim.final_state.memory)?;
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

    let expected_invariant_summary =
        phase9475_invariant_summary(&artifact.core_slice_artifact.execution_proof.claim.final_state.memory)?;
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

pub fn prepare_phase95_repeated_gemma_slice_accumulation_artifact(
    shared_primitive_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    shared_execution_proof: &VanillaStarkExecutionProof,
    total_slices: usize,
    repeated_token_position: u64,
    start_block_index: u64,
) -> Result<Phase95RepeatedGemmaSliceAccumulationArtifact> {
    verify_phase92_shared_normalization_primitive_artifact(shared_primitive_artifact)?;
    validate_phase945_gemma_execution_proof(shared_execution_proof)?;
    if total_slices < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 95 repeated Gemma slice accumulation requires at least two slices".to_string(),
        ));
    }

    let shared_execution_proof_commitment = commit_phase945_execution_proof(shared_execution_proof)?;
    let mut members = Vec::with_capacity(total_slices);
    for slice_index in 0..total_slices {
        let block_index = start_block_index + slice_index as u64;
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
    let terminal_block_index = start_block_index + total_slices as u64 - 1;
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

    if artifact.total_slices != artifact.members.len() {
        return Err(VmError::InvalidConfig(
            "Phase 95 total_slices does not match the member count".to_string(),
        ));
    }
    if artifact.total_slices < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 95 repeated Gemma slice accumulation requires at least two slices".to_string(),
        ));
    }
    let expected_terminal_block_index = artifact.start_block_index + artifact.total_slices as u64 - 1;
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
        let expected_block_index = artifact.start_block_index + expected_slice_index as u64;
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

fn phase9475_selected_memory_window(memory: &[i16]) -> Result<Vec<Phase9475GemmaMemoryWindowEntry>> {
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
    let primary_activation_output =
        phase9475_memory_i16(memory, 16, "primary_activation_output")?;
    let secondary_norm_sq = phase9475_memory_i16(memory, 17, "secondary_norm_sq")?;
    let secondary_inv_sqrt_q8 =
        phase9475_memory_i16(memory, 18, "secondary_inv_sqrt_q8")?;
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
    hasher.update(shared_primitive_artifact.static_table_registry_commitment.as_bytes());
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

fn commit_namespace_u64s(namespace: &str, values: &[u64]) -> Result<String> {
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
            error
                .to_string()
                .contains("selected_memory_window")
                || error.to_string().contains("selected_memory_window_commitment")
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
            error.to_string().contains("block_index")
                || error.to_string().contains("member 1")
        );
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
