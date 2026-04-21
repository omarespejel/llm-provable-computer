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

const MAX_PHASE93_TENSOR_NATIVE_CHAIN_JSON_BYTES: usize = 8 * 1024 * 1024;
const MAX_PHASE945_GEMMA_BLOCK_CORE_SLICE_JSON_BYTES: usize = 32 * 1024 * 1024;
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
    verify_phase92_shared_normalization_primitive_artifact(primitive_artifact)?;
    let steps = phase93_default_tensor_native_chain_steps(primitive_artifact)?;
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
            PHASE93_DEFAULT_TOKEN_POSITION,
            PHASE93_DEFAULT_BLOCK_INDEX,
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
