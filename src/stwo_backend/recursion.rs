use serde::{Deserialize, Serialize};
#[cfg(feature = "stwo-backend")]
use std::path::Path;

use crate::error::{Result, VmError};
use crate::proof::{ExecutionClaimCommitments, StarkProofBackend, VanillaStarkExecutionProof};

#[cfg(feature = "stwo-backend")]
use super::decoding::{
    read_json_bytes_with_limit,
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase30_decoding_step_proof_envelope_manifest,
    Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    Phase30DecodingStepProofEnvelopeManifest,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
};
#[cfg(feature = "stwo-backend")]
use super::STWO_BACKEND_VERSION_PHASE12;
#[cfg(feature = "stwo-backend")]
use crate::proof::CLAIM_STATEMENT_VERSION_V1;
#[cfg(feature = "stwo-backend")]
use blake2::{
    digest::{Update, VariableOutput},
    Blake2bVar,
};

pub const STWO_RECURSION_BATCH_VERSION_PHASE6: &str = "stwo-phase6-recursion-batch-v1";
pub const STWO_RECURSION_BATCH_SCOPE_PHASE6: &str =
    "stwo_execution_proof_batch_preaggregation_manifest";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29: &str =
    "stwo-phase29-recursive-compression-input-contract-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29: &str =
    "stwo_phase29_recursive_compression_input_contract";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31: &str =
    "stwo-phase31-recursive-compression-decode-boundary-manifest-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31: &str =
    "stwo_execution_parameterized_recursive_compression_decode_boundary_manifest";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE31_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32: &str =
    "stwo-phase32-recursive-compression-statement-contract-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32: &str =
    "stwo_execution_parameterized_recursive_compression_statement_contract";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE32_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33: &str =
    "stwo-phase33-recursive-compression-public-input-manifest-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33: &str =
    "stwo_execution_parameterized_recursive_compression_public_input_manifest";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE33_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34: &str =
    "stwo-phase34-recursive-compression-shared-lookup-manifest-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34: &str =
    "stwo_execution_parameterized_recursive_compression_shared_lookup_manifest";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE34_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35: &str =
    "stwo-phase35-recursive-compression-target-manifest-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35: &str =
    "stwo_execution_parameterized_recursive_compression_target_manifest";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE35_RECURSIVE_COMPRESSION_TARGET_MANIFEST_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36: &str =
    "stwo-phase36-recursive-verifier-harness-receipt-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36: &str =
    "stwo_execution_parameterized_recursive_verifier_harness_receipt";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_HARNESS_KIND_PHASE36: &str = "source-bound-target-verifier-v1";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE36_RECURSIVE_VERIFIER_HARNESS_RECEIPT_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37: &str =
    "stwo-phase37-recursive-artifact-chain-harness-receipt-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37: &str =
    "stwo_execution_parameterized_recursive_artifact_chain_harness_receipt";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_KIND_PHASE37: &str =
    "source-bound-recursive-artifact-chain-verifier-v1";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE37_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_PAPER3_COMPOSITION_PROTOTYPE_VERSION_PHASE38: &str =
    "stwo-phase38-paper3-composition-prototype-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_PAPER3_COMPOSITION_PROTOTYPE_SCOPE_PHASE38: &str =
    "stwo_execution_parameterized_paper3_composition_prototype";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase6RecursionBatchEntry {
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub steps: usize,
    pub proof_bytes: usize,
    pub commitment_program_hash: String,
    pub commitment_stark_options_hash: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase6RecursionBatchManifest {
    pub proof_backend: StarkProofBackend,
    pub batch_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub total_proofs: usize,
    pub total_steps: usize,
    pub total_proof_bytes: usize,
    pub entries: Vec<Phase6RecursionBatchEntry>,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase29RecursiveCompressionInputContractUnchecked")]
pub struct Phase29RecursiveCompressionInputContract {
    pub proof_backend: StarkProofBackend,
    pub contract_version: String,
    pub semantic_scope: String,
    pub phase28_artifact_version: String,
    pub phase28_semantic_scope: String,
    pub phase28_proof_backend_version: String,
    pub statement_version: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase28_bounded_aggregation_arity: usize,
    pub phase28_member_count: usize,
    pub phase28_member_summaries: usize,
    pub phase28_nested_members: usize,
    pub total_phase26_members: usize,
    pub total_phase25_members: usize,
    pub max_nested_chain_arity: usize,
    pub max_nested_fold_arity: usize,
    pub total_matrices: usize,
    pub total_layouts: usize,
    pub total_rollups: usize,
    pub total_segments: usize,
    pub total_steps: usize,
    pub lookup_delta_entries: usize,
    pub max_lookup_frontier_entries: usize,
    pub source_template_commitment: String,
    pub global_start_state_commitment: String,
    pub global_end_state_commitment: String,
    pub aggregation_template_commitment: String,
    pub aggregated_chained_folded_interval_accumulator_commitment: String,
    pub input_contract_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase29RecursiveCompressionInputContractUnchecked {
    pub proof_backend: StarkProofBackend,
    pub contract_version: String,
    pub semantic_scope: String,
    pub phase28_artifact_version: String,
    pub phase28_semantic_scope: String,
    pub phase28_proof_backend_version: String,
    pub statement_version: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase28_bounded_aggregation_arity: usize,
    pub phase28_member_count: usize,
    pub phase28_member_summaries: usize,
    pub phase28_nested_members: usize,
    pub total_phase26_members: usize,
    pub total_phase25_members: usize,
    pub max_nested_chain_arity: usize,
    pub max_nested_fold_arity: usize,
    pub total_matrices: usize,
    pub total_layouts: usize,
    pub total_rollups: usize,
    pub total_segments: usize,
    pub total_steps: usize,
    pub lookup_delta_entries: usize,
    pub max_lookup_frontier_entries: usize,
    pub source_template_commitment: String,
    pub global_start_state_commitment: String,
    pub global_end_state_commitment: String,
    pub aggregation_template_commitment: String,
    pub aggregated_chained_folded_interval_accumulator_commitment: String,
    pub input_contract_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase31RecursiveCompressionDecodeBoundaryManifestUnchecked")]
pub struct Phase31RecursiveCompressionDecodeBoundaryManifest {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase29_contract_version: String,
    pub phase29_semantic_scope: String,
    pub phase29_contract_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub decode_boundary_bridge_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase31RecursiveCompressionDecodeBoundaryManifestUnchecked {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase29_contract_version: String,
    pub phase29_semantic_scope: String,
    pub phase29_contract_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub decode_boundary_bridge_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase32RecursiveCompressionStatementContractUnchecked")]
pub struct Phase32RecursiveCompressionStatementContract {
    pub proof_backend: StarkProofBackend,
    pub contract_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase31_manifest_version: String,
    pub phase31_semantic_scope: String,
    pub phase31_decode_boundary_bridge_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub recursive_statement_contract_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase32RecursiveCompressionStatementContractUnchecked {
    pub proof_backend: StarkProofBackend,
    pub contract_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase31_manifest_version: String,
    pub phase31_semantic_scope: String,
    pub phase31_decode_boundary_bridge_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub recursive_statement_contract_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase33RecursiveCompressionPublicInputManifestUnchecked")]
pub struct Phase33RecursiveCompressionPublicInputManifest {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase32_contract_version: String,
    pub phase32_semantic_scope: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub total_steps: usize,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub phase31_decode_boundary_bridge_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub recursive_public_inputs_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase33RecursiveCompressionPublicInputManifestUnchecked {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase32_contract_version: String,
    pub phase32_semantic_scope: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub total_steps: usize,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub phase31_decode_boundary_bridge_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub recursive_public_inputs_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase34RecursiveCompressionSharedLookupManifestUnchecked")]
pub struct Phase34RecursiveCompressionSharedLookupManifest {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase33_manifest_version: String,
    pub phase33_semantic_scope: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub shared_lookup_public_inputs_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase34RecursiveCompressionSharedLookupManifestUnchecked {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase33_manifest_version: String,
    pub phase33_semantic_scope: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub shared_lookup_public_inputs_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase35RecursiveCompressionTargetManifestUnchecked")]
pub struct Phase35RecursiveCompressionTargetManifest {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase32_contract_version: String,
    pub phase32_semantic_scope: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub phase33_manifest_version: String,
    pub phase33_semantic_scope: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase34_manifest_version: String,
    pub phase34_semantic_scope: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub total_steps: usize,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub recursive_target_manifest_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase35RecursiveCompressionTargetManifestUnchecked {
    pub proof_backend: StarkProofBackend,
    pub manifest_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase32_contract_version: String,
    pub phase32_semantic_scope: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub phase33_manifest_version: String,
    pub phase33_semantic_scope: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase34_manifest_version: String,
    pub phase34_semantic_scope: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub total_steps: usize,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub recursive_target_manifest_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase36RecursiveVerifierHarnessReceiptUnchecked")]
pub struct Phase36RecursiveVerifierHarnessReceipt {
    pub proof_backend: StarkProofBackend,
    pub receipt_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub target_manifest_verified: bool,
    pub source_binding_verified: bool,
    pub phase35_manifest_version: String,
    pub phase35_semantic_scope: String,
    pub phase35_recursive_target_manifest_commitment: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub total_steps: usize,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub recursive_verifier_harness_receipt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase36RecursiveVerifierHarnessReceiptUnchecked {
    pub proof_backend: StarkProofBackend,
    pub receipt_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub target_manifest_verified: bool,
    pub source_binding_verified: bool,
    pub phase35_manifest_version: String,
    pub phase35_semantic_scope: String,
    pub phase35_recursive_target_manifest_commitment: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub total_steps: usize,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub recursive_verifier_harness_receipt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase37RecursiveArtifactChainHarnessReceiptUnchecked")]
pub struct Phase37RecursiveArtifactChainHarnessReceipt {
    pub proof_backend: StarkProofBackend,
    pub receipt_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase29_input_contract_verified: bool,
    pub phase30_step_envelope_manifest_verified: bool,
    pub phase31_decode_boundary_bridge_verified: bool,
    pub phase32_statement_contract_verified: bool,
    pub phase33_public_inputs_verified: bool,
    pub phase34_shared_lookup_verified: bool,
    pub phase35_target_manifest_verified: bool,
    pub phase36_verifier_harness_receipt_verified: bool,
    pub source_binding_verified: bool,
    pub phase29_contract_version: String,
    pub phase29_semantic_scope: String,
    pub phase29_input_contract_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub phase31_decode_boundary_bridge_commitment: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub phase35_recursive_target_manifest_commitment: String,
    pub phase36_recursive_verifier_harness_receipt_commitment: String,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub recursive_artifact_chain_harness_receipt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase37RecursiveArtifactChainHarnessReceiptUnchecked {
    pub proof_backend: StarkProofBackend,
    pub receipt_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub phase29_input_contract_verified: bool,
    pub phase30_step_envelope_manifest_verified: bool,
    pub phase31_decode_boundary_bridge_verified: bool,
    pub phase32_statement_contract_verified: bool,
    pub phase33_public_inputs_verified: bool,
    pub phase34_shared_lookup_verified: bool,
    pub phase35_target_manifest_verified: bool,
    pub phase36_verifier_harness_receipt_verified: bool,
    pub source_binding_verified: bool,
    pub phase29_contract_version: String,
    pub phase29_semantic_scope: String,
    pub phase29_input_contract_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub phase31_decode_boundary_bridge_commitment: String,
    pub phase32_recursive_statement_contract_commitment: String,
    pub phase33_recursive_public_inputs_commitment: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub phase35_recursive_target_manifest_commitment: String,
    pub phase36_recursive_verifier_harness_receipt_commitment: String,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
    pub recursive_artifact_chain_harness_receipt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase38Paper3CompositionSegmentUnchecked")]
pub struct Phase38Paper3CompositionSegment {
    pub segment_index: usize,
    pub step_start: usize,
    pub step_end: usize,
    pub total_steps: usize,
    pub phase37_receipt_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase38Paper3CompositionSegmentUnchecked {
    pub segment_index: usize,
    pub step_start: usize,
    pub step_end: usize,
    pub total_steps: usize,
    pub phase37_receipt_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub phase34_shared_lookup_public_inputs_commitment: String,
    pub input_lookup_rows_commitments_commitment: String,
    pub output_lookup_rows_commitments_commitment: String,
    pub shared_lookup_artifact_commitments_commitment: String,
    pub static_lookup_registry_commitments_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase38Paper3CompositionPrototypeUnchecked")]
pub struct Phase38Paper3CompositionPrototype {
    pub proof_backend: StarkProofBackend,
    pub prototype_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub segment_count: usize,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub shared_lookup_identity_commitment: String,
    pub segment_list_commitment: String,
    pub naive_per_step_package_count: usize,
    pub composed_segment_package_count: usize,
    pub package_count_delta: usize,
    pub segments: Vec<Phase38Paper3CompositionSegment>,
    pub composition_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase38Paper3CompositionPrototypeUnchecked {
    pub proof_backend: StarkProofBackend,
    pub prototype_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub segment_count: usize,
    pub total_steps: usize,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub shared_lookup_identity_commitment: String,
    pub segment_list_commitment: String,
    pub naive_per_step_package_count: usize,
    pub composed_segment_package_count: usize,
    pub package_count_delta: usize,
    pub segments: Vec<Phase38Paper3CompositionSegment>,
    pub composition_commitment: String,
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase38Paper3CompositionSegmentUnchecked> for Phase38Paper3CompositionSegment {
    type Error = VmError;

    fn try_from(unchecked: Phase38Paper3CompositionSegmentUnchecked) -> Result<Self> {
        let segment = Phase38Paper3CompositionSegment {
            segment_index: unchecked.segment_index,
            step_start: unchecked.step_start,
            step_end: unchecked.step_end,
            total_steps: unchecked.total_steps,
            phase37_receipt_commitment: unchecked.phase37_receipt_commitment,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            phase34_shared_lookup_public_inputs_commitment: unchecked
                .phase34_shared_lookup_public_inputs_commitment,
            input_lookup_rows_commitments_commitment: unchecked
                .input_lookup_rows_commitments_commitment,
            output_lookup_rows_commitments_commitment: unchecked
                .output_lookup_rows_commitments_commitment,
            shared_lookup_artifact_commitments_commitment: unchecked
                .shared_lookup_artifact_commitments_commitment,
            static_lookup_registry_commitments_commitment: unchecked
                .static_lookup_registry_commitments_commitment,
        };
        for (label, value) in [
            (
                "phase37_receipt_commitment",
                segment.phase37_receipt_commitment.as_str(),
            ),
            (
                "phase30_source_chain_commitment",
                segment.phase30_source_chain_commitment.as_str(),
            ),
            (
                "phase30_step_envelopes_commitment",
                segment.phase30_step_envelopes_commitment.as_str(),
            ),
            (
                "chain_start_boundary_commitment",
                segment.chain_start_boundary_commitment.as_str(),
            ),
            (
                "chain_end_boundary_commitment",
                segment.chain_end_boundary_commitment.as_str(),
            ),
            (
                "phase34_shared_lookup_public_inputs_commitment",
                segment
                    .phase34_shared_lookup_public_inputs_commitment
                    .as_str(),
            ),
            (
                "input_lookup_rows_commitments_commitment",
                segment.input_lookup_rows_commitments_commitment.as_str(),
            ),
            (
                "output_lookup_rows_commitments_commitment",
                segment.output_lookup_rows_commitments_commitment.as_str(),
            ),
            (
                "shared_lookup_artifact_commitments_commitment",
                segment
                    .shared_lookup_artifact_commitments_commitment
                    .as_str(),
            ),
            (
                "static_lookup_registry_commitments_commitment",
                segment
                    .static_lookup_registry_commitments_commitment
                    .as_str(),
            ),
        ] {
            phase38_require_hash32(label, value)?;
        }
        Ok(segment)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase38Paper3CompositionPrototypeUnchecked> for Phase38Paper3CompositionPrototype {
    type Error = VmError;

    fn try_from(unchecked: Phase38Paper3CompositionPrototypeUnchecked) -> Result<Self> {
        let prototype = Phase38Paper3CompositionPrototype {
            proof_backend: unchecked.proof_backend,
            prototype_version: unchecked.prototype_version,
            semantic_scope: unchecked.semantic_scope,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            segment_count: unchecked.segment_count,
            total_steps: unchecked.total_steps,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            shared_lookup_identity_commitment: unchecked.shared_lookup_identity_commitment,
            segment_list_commitment: unchecked.segment_list_commitment,
            naive_per_step_package_count: unchecked.naive_per_step_package_count,
            composed_segment_package_count: unchecked.composed_segment_package_count,
            package_count_delta: unchecked.package_count_delta,
            segments: unchecked.segments,
            composition_commitment: unchecked.composition_commitment,
        };
        verify_phase38_paper3_composition_prototype(&prototype)?;
        Ok(prototype)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase29RecursiveCompressionInputContractUnchecked>
    for Phase29RecursiveCompressionInputContract
{
    type Error = VmError;

    fn try_from(
        unchecked: Phase29RecursiveCompressionInputContractUnchecked,
    ) -> std::result::Result<Self, Self::Error> {
        let contract = Self {
            proof_backend: unchecked.proof_backend,
            contract_version: unchecked.contract_version,
            semantic_scope: unchecked.semantic_scope,
            phase28_artifact_version: unchecked.phase28_artifact_version,
            phase28_semantic_scope: unchecked.phase28_semantic_scope,
            phase28_proof_backend_version: unchecked.phase28_proof_backend_version,
            statement_version: unchecked.statement_version,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase28_bounded_aggregation_arity: unchecked.phase28_bounded_aggregation_arity,
            phase28_member_count: unchecked.phase28_member_count,
            phase28_member_summaries: unchecked.phase28_member_summaries,
            phase28_nested_members: unchecked.phase28_nested_members,
            total_phase26_members: unchecked.total_phase26_members,
            total_phase25_members: unchecked.total_phase25_members,
            max_nested_chain_arity: unchecked.max_nested_chain_arity,
            max_nested_fold_arity: unchecked.max_nested_fold_arity,
            total_matrices: unchecked.total_matrices,
            total_layouts: unchecked.total_layouts,
            total_rollups: unchecked.total_rollups,
            total_segments: unchecked.total_segments,
            total_steps: unchecked.total_steps,
            lookup_delta_entries: unchecked.lookup_delta_entries,
            max_lookup_frontier_entries: unchecked.max_lookup_frontier_entries,
            source_template_commitment: unchecked.source_template_commitment,
            global_start_state_commitment: unchecked.global_start_state_commitment,
            global_end_state_commitment: unchecked.global_end_state_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
            aggregated_chained_folded_interval_accumulator_commitment: unchecked
                .aggregated_chained_folded_interval_accumulator_commitment,
            input_contract_commitment: unchecked.input_contract_commitment,
        };
        verify_phase29_recursive_compression_input_contract(&contract)?;
        Ok(contract)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase31RecursiveCompressionDecodeBoundaryManifestUnchecked>
    for Phase31RecursiveCompressionDecodeBoundaryManifest
{
    type Error = VmError;

    fn try_from(
        unchecked: Phase31RecursiveCompressionDecodeBoundaryManifestUnchecked,
    ) -> std::result::Result<Self, Self::Error> {
        let manifest = Self {
            proof_backend: unchecked.proof_backend,
            manifest_version: unchecked.manifest_version,
            semantic_scope: unchecked.semantic_scope,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase29_contract_version: unchecked.phase29_contract_version,
            phase29_semantic_scope: unchecked.phase29_semantic_scope,
            phase29_contract_commitment: unchecked.phase29_contract_commitment,
            phase30_manifest_version: unchecked.phase30_manifest_version,
            phase30_semantic_scope: unchecked.phase30_semantic_scope,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            total_steps: unchecked.total_steps,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            source_template_commitment: unchecked.source_template_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
            decode_boundary_bridge_commitment: unchecked.decode_boundary_bridge_commitment,
        };
        verify_phase31_recursive_compression_decode_boundary_manifest(&manifest)?;
        Ok(manifest)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase32RecursiveCompressionStatementContractUnchecked>
    for Phase32RecursiveCompressionStatementContract
{
    type Error = VmError;

    fn try_from(
        unchecked: Phase32RecursiveCompressionStatementContractUnchecked,
    ) -> std::result::Result<Self, Self::Error> {
        let contract = Self {
            proof_backend: unchecked.proof_backend,
            contract_version: unchecked.contract_version,
            semantic_scope: unchecked.semantic_scope,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase31_manifest_version: unchecked.phase31_manifest_version,
            phase31_semantic_scope: unchecked.phase31_semantic_scope,
            phase31_decode_boundary_bridge_commitment: unchecked
                .phase31_decode_boundary_bridge_commitment,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            total_steps: unchecked.total_steps,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            source_template_commitment: unchecked.source_template_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
            recursive_statement_contract_commitment: unchecked
                .recursive_statement_contract_commitment,
        };
        verify_phase32_recursive_compression_statement_contract(&contract)?;
        Ok(contract)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase33RecursiveCompressionPublicInputManifestUnchecked>
    for Phase33RecursiveCompressionPublicInputManifest
{
    type Error = VmError;

    fn try_from(
        unchecked: Phase33RecursiveCompressionPublicInputManifestUnchecked,
    ) -> std::result::Result<Self, Self::Error> {
        let manifest = Self {
            proof_backend: unchecked.proof_backend,
            manifest_version: unchecked.manifest_version,
            semantic_scope: unchecked.semantic_scope,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase32_contract_version: unchecked.phase32_contract_version,
            phase32_semantic_scope: unchecked.phase32_semantic_scope,
            phase32_recursive_statement_contract_commitment: unchecked
                .phase32_recursive_statement_contract_commitment,
            total_steps: unchecked.total_steps,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            phase31_decode_boundary_bridge_commitment: unchecked
                .phase31_decode_boundary_bridge_commitment,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            source_template_commitment: unchecked.source_template_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
            recursive_public_inputs_commitment: unchecked.recursive_public_inputs_commitment,
        };
        verify_phase33_recursive_compression_public_input_manifest(&manifest)?;
        Ok(manifest)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase34RecursiveCompressionSharedLookupManifestUnchecked>
    for Phase34RecursiveCompressionSharedLookupManifest
{
    type Error = VmError;

    fn try_from(
        unchecked: Phase34RecursiveCompressionSharedLookupManifestUnchecked,
    ) -> std::result::Result<Self, Self::Error> {
        let manifest = Self {
            proof_backend: unchecked.proof_backend,
            manifest_version: unchecked.manifest_version,
            semantic_scope: unchecked.semantic_scope,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase33_manifest_version: unchecked.phase33_manifest_version,
            phase33_semantic_scope: unchecked.phase33_semantic_scope,
            phase33_recursive_public_inputs_commitment: unchecked
                .phase33_recursive_public_inputs_commitment,
            phase30_manifest_version: unchecked.phase30_manifest_version,
            phase30_semantic_scope: unchecked.phase30_semantic_scope,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            total_steps: unchecked.total_steps,
            input_lookup_rows_commitments_commitment: unchecked
                .input_lookup_rows_commitments_commitment,
            output_lookup_rows_commitments_commitment: unchecked
                .output_lookup_rows_commitments_commitment,
            shared_lookup_artifact_commitments_commitment: unchecked
                .shared_lookup_artifact_commitments_commitment,
            static_lookup_registry_commitments_commitment: unchecked
                .static_lookup_registry_commitments_commitment,
            shared_lookup_public_inputs_commitment: unchecked
                .shared_lookup_public_inputs_commitment,
        };
        verify_phase34_recursive_compression_shared_lookup_manifest(&manifest)?;
        Ok(manifest)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase35RecursiveCompressionTargetManifestUnchecked>
    for Phase35RecursiveCompressionTargetManifest
{
    type Error = VmError;

    fn try_from(unchecked: Phase35RecursiveCompressionTargetManifestUnchecked) -> Result<Self> {
        let manifest = Self {
            proof_backend: unchecked.proof_backend,
            manifest_version: unchecked.manifest_version,
            semantic_scope: unchecked.semantic_scope,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase32_contract_version: unchecked.phase32_contract_version,
            phase32_semantic_scope: unchecked.phase32_semantic_scope,
            phase32_recursive_statement_contract_commitment: unchecked
                .phase32_recursive_statement_contract_commitment,
            phase33_manifest_version: unchecked.phase33_manifest_version,
            phase33_semantic_scope: unchecked.phase33_semantic_scope,
            phase33_recursive_public_inputs_commitment: unchecked
                .phase33_recursive_public_inputs_commitment,
            phase34_manifest_version: unchecked.phase34_manifest_version,
            phase34_semantic_scope: unchecked.phase34_semantic_scope,
            phase34_shared_lookup_public_inputs_commitment: unchecked
                .phase34_shared_lookup_public_inputs_commitment,
            total_steps: unchecked.total_steps,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            source_template_commitment: unchecked.source_template_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
            input_lookup_rows_commitments_commitment: unchecked
                .input_lookup_rows_commitments_commitment,
            output_lookup_rows_commitments_commitment: unchecked
                .output_lookup_rows_commitments_commitment,
            shared_lookup_artifact_commitments_commitment: unchecked
                .shared_lookup_artifact_commitments_commitment,
            static_lookup_registry_commitments_commitment: unchecked
                .static_lookup_registry_commitments_commitment,
            recursive_target_manifest_commitment: unchecked.recursive_target_manifest_commitment,
        };
        verify_phase35_recursive_compression_target_manifest(&manifest)?;
        Ok(manifest)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase36RecursiveVerifierHarnessReceiptUnchecked>
    for Phase36RecursiveVerifierHarnessReceipt
{
    type Error = VmError;

    fn try_from(unchecked: Phase36RecursiveVerifierHarnessReceiptUnchecked) -> Result<Self> {
        let receipt = Self {
            proof_backend: unchecked.proof_backend,
            receipt_version: unchecked.receipt_version,
            semantic_scope: unchecked.semantic_scope,
            verifier_harness: unchecked.verifier_harness,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            target_manifest_verified: unchecked.target_manifest_verified,
            source_binding_verified: unchecked.source_binding_verified,
            phase35_manifest_version: unchecked.phase35_manifest_version,
            phase35_semantic_scope: unchecked.phase35_semantic_scope,
            phase35_recursive_target_manifest_commitment: unchecked
                .phase35_recursive_target_manifest_commitment,
            phase32_recursive_statement_contract_commitment: unchecked
                .phase32_recursive_statement_contract_commitment,
            phase33_recursive_public_inputs_commitment: unchecked
                .phase33_recursive_public_inputs_commitment,
            phase34_shared_lookup_public_inputs_commitment: unchecked
                .phase34_shared_lookup_public_inputs_commitment,
            total_steps: unchecked.total_steps,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            input_lookup_rows_commitments_commitment: unchecked
                .input_lookup_rows_commitments_commitment,
            output_lookup_rows_commitments_commitment: unchecked
                .output_lookup_rows_commitments_commitment,
            shared_lookup_artifact_commitments_commitment: unchecked
                .shared_lookup_artifact_commitments_commitment,
            static_lookup_registry_commitments_commitment: unchecked
                .static_lookup_registry_commitments_commitment,
            recursive_verifier_harness_receipt_commitment: unchecked
                .recursive_verifier_harness_receipt_commitment,
        };
        verify_phase36_recursive_verifier_harness_receipt(&receipt)?;
        Ok(receipt)
    }
}

#[cfg(feature = "stwo-backend")]
impl TryFrom<Phase37RecursiveArtifactChainHarnessReceiptUnchecked>
    for Phase37RecursiveArtifactChainHarnessReceipt
{
    type Error = VmError;

    fn try_from(unchecked: Phase37RecursiveArtifactChainHarnessReceiptUnchecked) -> Result<Self> {
        let receipt = Self {
            proof_backend: unchecked.proof_backend,
            receipt_version: unchecked.receipt_version,
            semantic_scope: unchecked.semantic_scope,
            verifier_harness: unchecked.verifier_harness,
            proof_backend_version: unchecked.proof_backend_version,
            statement_version: unchecked.statement_version,
            step_relation: unchecked.step_relation,
            required_recursion_posture: unchecked.required_recursion_posture,
            recursive_verification_claimed: unchecked.recursive_verification_claimed,
            cryptographic_compression_claimed: unchecked.cryptographic_compression_claimed,
            phase29_input_contract_verified: unchecked.phase29_input_contract_verified,
            phase30_step_envelope_manifest_verified: unchecked
                .phase30_step_envelope_manifest_verified,
            phase31_decode_boundary_bridge_verified: unchecked
                .phase31_decode_boundary_bridge_verified,
            phase32_statement_contract_verified: unchecked.phase32_statement_contract_verified,
            phase33_public_inputs_verified: unchecked.phase33_public_inputs_verified,
            phase34_shared_lookup_verified: unchecked.phase34_shared_lookup_verified,
            phase35_target_manifest_verified: unchecked.phase35_target_manifest_verified,
            phase36_verifier_harness_receipt_verified: unchecked
                .phase36_verifier_harness_receipt_verified,
            source_binding_verified: unchecked.source_binding_verified,
            phase29_contract_version: unchecked.phase29_contract_version,
            phase29_semantic_scope: unchecked.phase29_semantic_scope,
            phase29_input_contract_commitment: unchecked.phase29_input_contract_commitment,
            phase30_manifest_version: unchecked.phase30_manifest_version,
            phase30_semantic_scope: unchecked.phase30_semantic_scope,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            phase31_decode_boundary_bridge_commitment: unchecked
                .phase31_decode_boundary_bridge_commitment,
            phase32_recursive_statement_contract_commitment: unchecked
                .phase32_recursive_statement_contract_commitment,
            phase33_recursive_public_inputs_commitment: unchecked
                .phase33_recursive_public_inputs_commitment,
            phase34_shared_lookup_public_inputs_commitment: unchecked
                .phase34_shared_lookup_public_inputs_commitment,
            phase35_recursive_target_manifest_commitment: unchecked
                .phase35_recursive_target_manifest_commitment,
            phase36_recursive_verifier_harness_receipt_commitment: unchecked
                .phase36_recursive_verifier_harness_receipt_commitment,
            total_steps: unchecked.total_steps,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            source_template_commitment: unchecked.source_template_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
            input_lookup_rows_commitments_commitment: unchecked
                .input_lookup_rows_commitments_commitment,
            output_lookup_rows_commitments_commitment: unchecked
                .output_lookup_rows_commitments_commitment,
            shared_lookup_artifact_commitments_commitment: unchecked
                .shared_lookup_artifact_commitments_commitment,
            static_lookup_registry_commitments_commitment: unchecked
                .static_lookup_registry_commitments_commitment,
            recursive_artifact_chain_harness_receipt_commitment: unchecked
                .recursive_artifact_chain_harness_receipt_commitment,
        };
        verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)?;
        Ok(receipt)
    }
}

pub fn phase6_prepare_recursion_batch(
    proofs: &[VanillaStarkExecutionProof],
) -> Result<Phase6RecursionBatchManifest> {
    let first = proofs.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "recursion batch preparation requires at least one proof".to_string(),
        )
    })?;
    if first.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "recursion batch preparation requires `stwo` proofs, got `{}`",
            first.proof_backend
        )));
    }
    required_commitments(first)?;

    let mut entries = Vec::with_capacity(proofs.len());
    let mut total_steps = 0usize;
    let mut total_proof_bytes = 0usize;

    for (index, proof) in proofs.iter().enumerate() {
        if proof.proof_backend != StarkProofBackend::Stwo {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses backend `{}`; expected `stwo` for recursion batching",
                proof.proof_backend
            )));
        }
        if proof.proof_backend_version != first.proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses backend version `{}`; expected `{}`",
                proof.proof_backend_version, first.proof_backend_version
            )));
        }
        if proof.claim.statement_version != first.claim.statement_version {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses statement version `{}`; expected `{}`",
                proof.claim.statement_version, first.claim.statement_version
            )));
        }
        if proof.claim.semantic_scope != first.claim.semantic_scope {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses semantic scope `{}`; expected `{}`",
                proof.claim.semantic_scope, first.claim.semantic_scope
            )));
        }
        let commitments = required_commitments(proof)?;
        if commitments.stark_options_hash != first_commitment_stark_options_hash(first)? {
            return Err(VmError::InvalidConfig(format!(
                "proof {index} uses stark options hash `{}`; expected `{}`",
                commitments.stark_options_hash,
                first_commitment_stark_options_hash(first)?
            )));
        }

        total_steps += proof.claim.steps;
        total_proof_bytes += proof.proof.len();
        entries.push(Phase6RecursionBatchEntry {
            proof_backend_version: proof.proof_backend_version.clone(),
            statement_version: proof.claim.statement_version.clone(),
            semantic_scope: proof.claim.semantic_scope.clone(),
            steps: proof.claim.steps,
            proof_bytes: proof.proof.len(),
            commitment_program_hash: commitments.program_hash.clone(),
            commitment_stark_options_hash: commitments.stark_options_hash.clone(),
        });
    }

    Ok(Phase6RecursionBatchManifest {
        proof_backend: StarkProofBackend::Stwo,
        batch_version: STWO_RECURSION_BATCH_VERSION_PHASE6.to_string(),
        semantic_scope: STWO_RECURSION_BATCH_SCOPE_PHASE6.to_string(),
        proof_backend_version: first.proof_backend_version.clone(),
        statement_version: first.claim.statement_version.clone(),
        total_proofs: entries.len(),
        total_steps,
        total_proof_bytes,
        entries,
    })
}

fn required_commitments(proof: &VanillaStarkExecutionProof) -> Result<&ExecutionClaimCommitments> {
    proof.claim.commitments.as_ref().ok_or_else(|| {
        VmError::InvalidConfig(
            "recursion batch preparation requires commitment metadata".to_string(),
        )
    })
}

fn first_commitment_stark_options_hash(proof: &VanillaStarkExecutionProof) -> Result<String> {
    Ok(required_commitments(proof)?.stark_options_hash.clone())
}

#[cfg(feature = "stwo-backend")]
pub fn phase29_prepare_recursive_compression_input_contract(
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
) -> Result<Phase29RecursiveCompressionInputContract> {
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks(
        phase28,
    )?;

    phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28(phase28)
}

#[cfg(feature = "stwo-backend")]
pub fn phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28(
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
) -> Result<Phase29RecursiveCompressionInputContract> {
    let mut contract = Phase29RecursiveCompressionInputContract {
        proof_backend: StarkProofBackend::Stwo,
        contract_version: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29.to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29.to_string(),
        phase28_artifact_version: phase28.artifact_version.clone(),
        phase28_semantic_scope: phase28.semantic_scope.clone(),
        phase28_proof_backend_version: phase28.proof_backend_version.clone(),
        statement_version: phase28.statement_version.clone(),
        required_recursion_posture: phase28.recursion_posture.clone(),
        recursive_verification_claimed: phase28.recursive_verification_claimed,
        cryptographic_compression_claimed: phase28.cryptographic_compression_claimed,
        phase28_bounded_aggregation_arity: phase28.bounded_aggregation_arity,
        phase28_member_count: phase28.member_count,
        phase28_member_summaries: phase28.member_summaries.len(),
        phase28_nested_members: phase28.members.len(),
        total_phase26_members: phase28.total_phase26_members,
        total_phase25_members: phase28.total_phase25_members,
        max_nested_chain_arity: phase28.max_nested_chain_arity,
        max_nested_fold_arity: phase28.max_nested_fold_arity,
        total_matrices: phase28.total_matrices,
        total_layouts: phase28.total_layouts,
        total_rollups: phase28.total_rollups,
        total_segments: phase28.total_segments,
        total_steps: phase28.total_steps,
        lookup_delta_entries: phase28.lookup_delta_entries,
        max_lookup_frontier_entries: phase28.max_lookup_frontier_entries,
        source_template_commitment: phase28.source_template_commitment.clone(),
        global_start_state_commitment: phase28.global_start_state_commitment.clone(),
        global_end_state_commitment: phase28.global_end_state_commitment.clone(),
        aggregation_template_commitment: phase28.aggregation_template_commitment.clone(),
        aggregated_chained_folded_interval_accumulator_commitment: phase28
            .aggregated_chained_folded_interval_accumulator_commitment
            .clone(),
        input_contract_commitment: String::new(),
    };
    contract.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&contract)?;
    verify_phase29_recursive_compression_input_contract(&contract)?;
    Ok(contract)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase29_recursive_compression_input_contract_json(
    json: &str,
) -> Result<Phase29RecursiveCompressionInputContract> {
    if json.len() > MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase29_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase29_recursive_compression_input_contract(
    path: &Path,
) -> Result<Phase29RecursiveCompressionInputContract> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES,
        "Phase 29 recursive-compression input contract",
    )?;
    serde_json::from_slice(&bytes).map_err(phase29_json_error)
}

#[cfg(feature = "stwo-backend")]
fn phase29_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase29_recursive_compression_input_contract(
    contract: &Phase29RecursiveCompressionInputContract,
) -> Result<()> {
    if contract.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires `stwo` backend, got `{}`",
            contract.proof_backend
        )));
    }
    if contract.contract_version != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract version `{}` does not match expected `{}`",
            contract.contract_version, STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29
        )));
    }
    if contract.semantic_scope != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract scope `{}` does not match expected `{}`",
            contract.semantic_scope, STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29
        )));
    }
    if contract.phase28_artifact_version
        != STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires Phase 28 artifact version `{}`, got `{}`",
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
            contract.phase28_artifact_version
        )));
    }
    if contract.phase28_semantic_scope
        != STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires Phase 28 scope `{}`, got `{}`",
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
            contract.phase28_semantic_scope
        )));
    }
    if contract.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires Phase 28 posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
            contract.required_recursion_posture
        )));
    }
    if contract.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 29 recursive-compression input contract must not claim recursive verification"
                .to_string(),
        ));
    }
    if contract.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 29 recursive-compression input contract must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if contract.phase28_member_count < 2 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires at least two Phase 28 members, got {}",
            contract.phase28_member_count
        )));
    }
    if contract.phase28_bounded_aggregation_arity < contract.phase28_member_count {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract bounded arity {} is smaller than member count {}",
            contract.phase28_bounded_aggregation_arity, contract.phase28_member_count
        )));
    }
    if contract.phase28_member_summaries != contract.phase28_member_count {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract summarizes {} members but declares {}",
            contract.phase28_member_summaries, contract.phase28_member_count
        )));
    }
    if contract.phase28_nested_members != contract.phase28_member_count {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract carries {} nested members but declares {}",
            contract.phase28_nested_members, contract.phase28_member_count
        )));
    }
    for (label, value) in [
        (
            "phase28_proof_backend_version",
            contract.phase28_proof_backend_version.as_str(),
        ),
        ("statement_version", contract.statement_version.as_str()),
        (
            "source_template_commitment",
            contract.source_template_commitment.as_str(),
        ),
        (
            "global_start_state_commitment",
            contract.global_start_state_commitment.as_str(),
        ),
        (
            "global_end_state_commitment",
            contract.global_end_state_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            contract.aggregation_template_commitment.as_str(),
        ),
        (
            "aggregated_chained_folded_interval_accumulator_commitment",
            contract
                .aggregated_chained_folded_interval_accumulator_commitment
                .as_str(),
        ),
        (
            "input_contract_commitment",
            contract.input_contract_commitment.as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 29 recursive-compression input contract `{label}` must be non-empty"
            )));
        }
    }

    if contract.phase28_proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires Phase 28 proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, contract.phase28_proof_backend_version
        )));
    }
    if contract.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, contract.statement_version
        )));
    }

    let expected = commit_phase29_recursive_compression_input_contract(contract)?;
    if contract.input_contract_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 29 recursive-compression input contract commitment `{}` does not match recomputed `{}`",
            contract.input_contract_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase29_recursive_compression_input_contract(
    contract: &Phase29RecursiveCompressionInputContract,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 29 input contract commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase29-contract");
    phase29_update_len_prefixed(&mut hasher, contract.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.phase28_artifact_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.phase28_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        contract.phase28_proof_backend_version.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, contract.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, contract.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, contract.cryptographic_compression_claimed);
    phase29_update_usize(&mut hasher, contract.phase28_bounded_aggregation_arity);
    phase29_update_usize(&mut hasher, contract.phase28_member_count);
    phase29_update_usize(&mut hasher, contract.phase28_member_summaries);
    phase29_update_usize(&mut hasher, contract.phase28_nested_members);
    phase29_update_usize(&mut hasher, contract.total_phase26_members);
    phase29_update_usize(&mut hasher, contract.total_phase25_members);
    phase29_update_usize(&mut hasher, contract.max_nested_chain_arity);
    phase29_update_usize(&mut hasher, contract.max_nested_fold_arity);
    phase29_update_usize(&mut hasher, contract.total_matrices);
    phase29_update_usize(&mut hasher, contract.total_layouts);
    phase29_update_usize(&mut hasher, contract.total_rollups);
    phase29_update_usize(&mut hasher, contract.total_segments);
    phase29_update_usize(&mut hasher, contract.total_steps);
    phase29_update_usize(&mut hasher, contract.lookup_delta_entries);
    phase29_update_usize(&mut hasher, contract.max_lookup_frontier_entries);
    phase29_update_len_prefixed(&mut hasher, contract.source_template_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        contract.global_start_state_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, contract.global_end_state_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        contract.aggregation_template_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        contract
            .aggregated_chained_folded_interval_accumulator_commitment
            .as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 29 input contract commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase29_update_len_prefixed(hasher: &mut Blake2bVar, bytes: &[u8]) {
    phase29_update_usize(hasher, bytes.len());
    hasher.update(bytes);
}

#[cfg(feature = "stwo-backend")]
fn phase29_update_bool(hasher: &mut Blake2bVar, value: bool) {
    hasher.update(&[u8::from(value)]);
}

#[cfg(feature = "stwo-backend")]
fn phase29_update_usize(hasher: &mut Blake2bVar, value: usize) {
    hasher.update(&(value as u128).to_le_bytes());
}

#[cfg(feature = "stwo-backend")]
fn phase29_lower_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

#[cfg(feature = "stwo-backend")]
fn phase37_is_lower_hex_byte(byte: u8) -> bool {
    matches!(byte, b'0'..=b'9' | b'a'..=b'f')
}

#[cfg(feature = "stwo-backend")]
fn phase37_is_hash32_lower_hex(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(phase37_is_lower_hex_byte)
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Phase33PublicInputLane {
    Phase32RecursiveStatementContract,
    TotalSteps,
    Phase30SourceChain,
    Phase30StepEnvelopes,
    Phase31DecodeBoundaryBridge,
    ChainStartBoundary,
    ChainEndBoundary,
    SourceTemplate,
    AggregationTemplate,
}

#[cfg(feature = "stwo-backend")]
const PHASE33_PUBLIC_INPUT_LANES: [Phase33PublicInputLane; 9] = [
    Phase33PublicInputLane::Phase32RecursiveStatementContract,
    Phase33PublicInputLane::TotalSteps,
    Phase33PublicInputLane::Phase30SourceChain,
    Phase33PublicInputLane::Phase30StepEnvelopes,
    Phase33PublicInputLane::Phase31DecodeBoundaryBridge,
    Phase33PublicInputLane::ChainStartBoundary,
    Phase33PublicInputLane::ChainEndBoundary,
    Phase33PublicInputLane::SourceTemplate,
    Phase33PublicInputLane::AggregationTemplate,
];

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Phase33PublicInputLanePayload<'a> {
    Bytes(&'a str),
    Usize(usize),
}

#[cfg(all(kani, feature = "stwo-backend"))]
fn phase33_public_input_lanes_are_canonical(lanes: &[Phase33PublicInputLane; 9]) -> bool {
    *lanes
        == [
            Phase33PublicInputLane::Phase32RecursiveStatementContract,
            Phase33PublicInputLane::TotalSteps,
            Phase33PublicInputLane::Phase30SourceChain,
            Phase33PublicInputLane::Phase30StepEnvelopes,
            Phase33PublicInputLane::Phase31DecodeBoundaryBridge,
            Phase33PublicInputLane::ChainStartBoundary,
            Phase33PublicInputLane::ChainEndBoundary,
            Phase33PublicInputLane::SourceTemplate,
            Phase33PublicInputLane::AggregationTemplate,
        ]
}

#[cfg(feature = "stwo-backend")]
fn phase33_public_input_lane_payload<'a>(
    manifest: &'a Phase33RecursiveCompressionPublicInputManifest,
    lane: Phase33PublicInputLane,
) -> Phase33PublicInputLanePayload<'a> {
    match lane {
        Phase33PublicInputLane::Phase32RecursiveStatementContract => {
            Phase33PublicInputLanePayload::Bytes(
                &manifest.phase32_recursive_statement_contract_commitment,
            )
        }
        Phase33PublicInputLane::TotalSteps => {
            Phase33PublicInputLanePayload::Usize(manifest.total_steps)
        }
        Phase33PublicInputLane::Phase30SourceChain => {
            Phase33PublicInputLanePayload::Bytes(&manifest.phase30_source_chain_commitment)
        }
        Phase33PublicInputLane::Phase30StepEnvelopes => {
            Phase33PublicInputLanePayload::Bytes(&manifest.phase30_step_envelopes_commitment)
        }
        Phase33PublicInputLane::Phase31DecodeBoundaryBridge => {
            Phase33PublicInputLanePayload::Bytes(
                &manifest.phase31_decode_boundary_bridge_commitment,
            )
        }
        Phase33PublicInputLane::ChainStartBoundary => {
            Phase33PublicInputLanePayload::Bytes(&manifest.chain_start_boundary_commitment)
        }
        Phase33PublicInputLane::ChainEndBoundary => {
            Phase33PublicInputLanePayload::Bytes(&manifest.chain_end_boundary_commitment)
        }
        Phase33PublicInputLane::SourceTemplate => {
            Phase33PublicInputLanePayload::Bytes(&manifest.source_template_commitment)
        }
        Phase33PublicInputLane::AggregationTemplate => {
            Phase33PublicInputLanePayload::Bytes(&manifest.aggregation_template_commitment)
        }
    }
}

#[cfg(feature = "stwo-backend")]
fn phase36_receipt_flag_surface_is_valid(
    recursive_verification_claimed: bool,
    cryptographic_compression_claimed: bool,
    target_manifest_verified: bool,
    source_binding_verified: bool,
    total_steps: usize,
) -> bool {
    !recursive_verification_claimed
        && !cryptographic_compression_claimed
        && target_manifest_verified
        && source_binding_verified
        && total_steps > 0
}

#[cfg(feature = "stwo-backend")]
fn phase37_source_flags_are_all_set(flags: &[bool; 9]) -> bool {
    for flag in flags {
        if !*flag {
            return false;
        }
    }
    true
}

#[cfg(feature = "stwo-backend")]
fn phase37_receipt_flag_surface_is_valid(
    recursive_verification_claimed: bool,
    cryptographic_compression_claimed: bool,
    source_flags: &[bool; 9],
    total_steps: usize,
) -> bool {
    !recursive_verification_claimed
        && !cryptographic_compression_claimed
        && phase37_source_flags_are_all_set(source_flags)
        && total_steps > 0
}

#[cfg(feature = "stwo-backend")]
fn phase37_require_hash32(label: &str, value: &str) -> Result<()> {
    if !phase37_is_hash32_lower_hex(value) {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase38_require_hash32(label: &str, value: &str) -> Result<()> {
    if !phase37_is_hash32_lower_hex(value) {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    Ok(())
}

#[cfg(all(kani, feature = "stwo-backend"))]
mod kani_phase36_phase37_proofs {
    use super::{
        phase33_public_input_lane_payload, phase33_public_input_lanes_are_canonical,
        phase36_receipt_flag_surface_is_valid, phase37_is_hash32_lower_hex,
        phase37_is_lower_hex_byte, phase37_receipt_flag_surface_is_valid, Phase33PublicInputLane,
        Phase33PublicInputLanePayload, Phase33RecursiveCompressionPublicInputManifest,
        PHASE33_PUBLIC_INPUT_LANES,
    };
    use crate::proof::StarkProofBackend;

    const PHASE37_SOURCE_FLAG_COUNT: usize = 9;

    #[kani::proof]
    fn kani_phase37_hash32_accepts_lowercase_hex_boundary() {
        const LOWER_ZERO: &str = concat!(
            "00000000", "00000000", "00000000", "00000000", "00000000", "00000000", "00000000",
            "00000000"
        );
        const LOWER_F: &str = concat!(
            "ffffffff", "ffffffff", "ffffffff", "ffffffff", "ffffffff", "ffffffff", "ffffffff",
            "ffffffff"
        );

        assert!(phase37_is_hash32_lower_hex(LOWER_ZERO));
        assert!(phase37_is_hash32_lower_hex(LOWER_F));
        assert!(phase37_is_hash32_lower_hex(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        ));
    }

    #[kani::proof]
    fn kani_phase37_hash32_rejects_non_lowercase_hex_examples() {
        const UPPERCASE_HEX: &str = concat!(
            "A", "aaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa",
            "aaaaaaaa"
        );
        const PUNCTUATION: &str = concat!(
            "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa",
            "aaaaaaa", ":"
        );

        assert!(UPPERCASE_HEX.len() == 64);
        assert!(PUNCTUATION.len() == 64);
        assert!(!phase37_is_lower_hex_byte(b'A'));
        assert!(!phase37_is_lower_hex_byte(b':'));
        assert!(!phase37_is_hash32_lower_hex(UPPERCASE_HEX));
        assert!(!phase37_is_hash32_lower_hex(PUNCTUATION));
    }

    #[kani::proof]
    fn kani_phase37_hash32_requires_exact_length() {
        const HEX_63: &str = concat!(
            "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa",
            "aaaaaaa"
        );
        const HEX_64: &str = concat!(
            "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa",
            "aaaaaaaa"
        );
        const HEX_65: &str = concat!(
            "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa", "aaaaaaaa",
            "aaaaaaaa", "a"
        );

        assert!(HEX_63.len() == 63);
        assert!(HEX_64.len() == 64);
        assert!(HEX_65.len() == 65);
        assert!(!phase37_is_hash32_lower_hex(HEX_63));
        assert!(phase37_is_hash32_lower_hex(HEX_64));
        assert!(!phase37_is_hash32_lower_hex(HEX_65));
    }

    #[kani::proof]
    fn kani_phase36_receipt_flags_accept_canonical_nonclaim_receipt() {
        assert!(phase36_receipt_flag_surface_is_valid(
            false, false, true, true, 1
        ));
    }

    #[kani::proof]
    fn kani_phase36_receipt_flags_reject_any_claim_or_missing_source_check() {
        let recursive_claimed = kani::any::<bool>();
        let compression_claimed = kani::any::<bool>();
        let target_manifest_verified = kani::any::<bool>();
        let source_binding_verified = kani::any::<bool>();
        let total_steps = if kani::any::<bool>() { 0 } else { 1 };
        kani::assume(
            recursive_claimed
                || compression_claimed
                || !target_manifest_verified
                || !source_binding_verified
                || total_steps == 0,
        );

        assert!(!phase36_receipt_flag_surface_is_valid(
            recursive_claimed,
            compression_claimed,
            target_manifest_verified,
            source_binding_verified,
            total_steps,
        ));
    }

    #[kani::proof]
    fn kani_phase37_receipt_flags_accept_canonical_source_bound_receipt() {
        assert!(phase37_receipt_flag_surface_is_valid(
            false,
            false,
            &[true; PHASE37_SOURCE_FLAG_COUNT],
            1
        ));
    }

    #[kani::proof]
    fn kani_phase37_receipt_flags_reject_any_claim_or_missing_source_check() {
        let mut source_flags = [true; PHASE37_SOURCE_FLAG_COUNT];
        let bad_flag_index = kani::any::<usize>();
        kani::assume(bad_flag_index < PHASE37_SOURCE_FLAG_COUNT);
        source_flags[bad_flag_index] = false;

        assert!(!phase37_receipt_flag_surface_is_valid(
            false,
            false,
            &source_flags,
            1,
        ));
        assert!(!phase37_receipt_flag_surface_is_valid(
            true,
            false,
            &[true; PHASE37_SOURCE_FLAG_COUNT],
            1,
        ));
        assert!(!phase37_receipt_flag_surface_is_valid(
            false,
            true,
            &[true; PHASE37_SOURCE_FLAG_COUNT],
            1,
        ));
        assert!(!phase37_receipt_flag_surface_is_valid(
            false,
            false,
            &[true; PHASE37_SOURCE_FLAG_COUNT],
            0,
        ));
    }

    #[kani::proof]
    fn kani_phase33_public_input_ordering_accepts_canonical_order() {
        assert!(phase33_public_input_lanes_are_canonical(
            &PHASE33_PUBLIC_INPUT_LANES
        ));
    }

    #[kani::proof]
    fn kani_phase33_public_input_lane_payload_wires_canonical_fields() {
        let manifest = Phase33RecursiveCompressionPublicInputManifest {
            proof_backend: StarkProofBackend::Stwo,
            manifest_version: "manifest-version".to_string(),
            semantic_scope: "semantic-scope".to_string(),
            proof_backend_version: "proof-backend-version".to_string(),
            statement_version: "statement-version".to_string(),
            step_relation: "step-relation".to_string(),
            required_recursion_posture: "required-recursion-posture".to_string(),
            recursive_verification_claimed: false,
            cryptographic_compression_claimed: false,
            phase32_contract_version: "phase32-contract-version".to_string(),
            phase32_semantic_scope: "phase32-semantic-scope".to_string(),
            phase32_recursive_statement_contract_commitment: "lane-phase32-contract".to_string(),
            total_steps: 73,
            phase30_source_chain_commitment: "lane-phase30-source-chain".to_string(),
            phase30_step_envelopes_commitment: "lane-phase30-step-envelopes".to_string(),
            phase31_decode_boundary_bridge_commitment: "lane-phase31-boundary-bridge".to_string(),
            chain_start_boundary_commitment: "lane-chain-start".to_string(),
            chain_end_boundary_commitment: "lane-chain-end".to_string(),
            source_template_commitment: "lane-source-template".to_string(),
            aggregation_template_commitment: "lane-aggregation-template".to_string(),
            recursive_public_inputs_commitment: "not-a-public-input-lane".to_string(),
        };

        assert!(
            phase33_public_input_lane_payload(
                &manifest,
                Phase33PublicInputLane::Phase32RecursiveStatementContract
            ) == Phase33PublicInputLanePayload::Bytes("lane-phase32-contract")
        );
        assert!(
            phase33_public_input_lane_payload(&manifest, Phase33PublicInputLane::TotalSteps)
                == Phase33PublicInputLanePayload::Usize(73)
        );
        assert!(
            phase33_public_input_lane_payload(
                &manifest,
                Phase33PublicInputLane::Phase30SourceChain
            ) == Phase33PublicInputLanePayload::Bytes("lane-phase30-source-chain")
        );
        assert!(
            phase33_public_input_lane_payload(
                &manifest,
                Phase33PublicInputLane::Phase30StepEnvelopes
            ) == Phase33PublicInputLanePayload::Bytes("lane-phase30-step-envelopes")
        );
        assert!(
            phase33_public_input_lane_payload(
                &manifest,
                Phase33PublicInputLane::Phase31DecodeBoundaryBridge
            ) == Phase33PublicInputLanePayload::Bytes("lane-phase31-boundary-bridge")
        );
        assert!(
            phase33_public_input_lane_payload(
                &manifest,
                Phase33PublicInputLane::ChainStartBoundary
            ) == Phase33PublicInputLanePayload::Bytes("lane-chain-start")
        );
        assert!(
            phase33_public_input_lane_payload(&manifest, Phase33PublicInputLane::ChainEndBoundary)
                == Phase33PublicInputLanePayload::Bytes("lane-chain-end")
        );
        assert!(
            phase33_public_input_lane_payload(&manifest, Phase33PublicInputLane::SourceTemplate)
                == Phase33PublicInputLanePayload::Bytes("lane-source-template")
        );
        assert!(
            phase33_public_input_lane_payload(
                &manifest,
                Phase33PublicInputLane::AggregationTemplate
            ) == Phase33PublicInputLanePayload::Bytes("lane-aggregation-template")
        );
    }

    #[kani::proof]
    fn kani_phase33_public_input_ordering_rejects_any_lane_drift() {
        let mut observed = PHASE33_PUBLIC_INPUT_LANES;
        let bad_lane = kani::any::<usize>();
        kani::assume(bad_lane < PHASE33_PUBLIC_INPUT_LANES.len());
        observed[bad_lane] =
            if observed[bad_lane] == Phase33PublicInputLane::Phase32RecursiveStatementContract {
                Phase33PublicInputLane::TotalSteps
            } else {
                Phase33PublicInputLane::Phase32RecursiveStatementContract
            };

        assert!(!phase33_public_input_lanes_are_canonical(&observed));
    }
}

#[cfg(feature = "stwo-backend")]
pub fn phase31_prepare_recursive_compression_decode_boundary_manifest(
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase31RecursiveCompressionDecodeBoundaryManifest> {
    verify_phase29_recursive_compression_input_contract(contract)?;
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;
    if contract.phase28_proof_backend_version != phase30.proof_backend_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires matching proof backend version between Phase 29 (`{}`) and Phase 30 (`{}`)",
            contract.phase28_proof_backend_version, phase30.proof_backend_version
        )));
    }
    if contract.statement_version != phase30.statement_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires matching statement version between Phase 29 (`{}`) and Phase 30 (`{}`)",
            contract.statement_version, phase30.statement_version
        )));
    }
    if contract.total_steps != phase30.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires matching total_steps between Phase 29 ({}) and Phase 30 ({})",
            contract.total_steps, phase30.total_steps
        )));
    }
    if contract.global_start_state_commitment != phase30.chain_start_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 31 decode-boundary manifest requires Phase 29 global_start_state_commitment to match the Phase 30 chain_start_boundary_commitment".to_string(),
        ));
    }
    if contract.global_end_state_commitment != phase30.chain_end_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 31 decode-boundary manifest requires Phase 29 global_end_state_commitment to match the Phase 30 chain_end_boundary_commitment".to_string(),
        ));
    }

    let mut manifest = Phase31RecursiveCompressionDecodeBoundaryManifest {
        proof_backend: StarkProofBackend::Stwo,
        manifest_version: STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31
            .to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31
            .to_string(),
        proof_backend_version: contract.phase28_proof_backend_version.clone(),
        statement_version: contract.statement_version.clone(),
        step_relation: STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30.to_string(),
        required_recursion_posture: contract.required_recursion_posture.clone(),
        recursive_verification_claimed: contract.recursive_verification_claimed,
        cryptographic_compression_claimed: contract.cryptographic_compression_claimed,
        phase29_contract_version: contract.contract_version.clone(),
        phase29_semantic_scope: contract.semantic_scope.clone(),
        phase29_contract_commitment: contract.input_contract_commitment.clone(),
        phase30_manifest_version: phase30.manifest_version.clone(),
        phase30_semantic_scope: phase30.semantic_scope.clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        total_steps: phase30.total_steps,
        chain_start_boundary_commitment: phase30.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: phase30.chain_end_boundary_commitment.clone(),
        source_template_commitment: contract.source_template_commitment.clone(),
        aggregation_template_commitment: contract.aggregation_template_commitment.clone(),
        decode_boundary_bridge_commitment: String::new(),
    };
    manifest.decode_boundary_bridge_commitment =
        commit_phase31_recursive_compression_decode_boundary_manifest(&manifest)?;
    verify_phase31_recursive_compression_decode_boundary_manifest(&manifest)?;
    Ok(manifest)
}

#[cfg(feature = "stwo-backend")]
pub fn phase32_prepare_recursive_compression_statement_contract(
    manifest: &Phase31RecursiveCompressionDecodeBoundaryManifest,
) -> Result<Phase32RecursiveCompressionStatementContract> {
    verify_phase31_recursive_compression_decode_boundary_manifest(manifest)?;

    let mut contract = Phase32RecursiveCompressionStatementContract {
        proof_backend: StarkProofBackend::Stwo,
        contract_version: STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32.to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32.to_string(),
        proof_backend_version: manifest.proof_backend_version.clone(),
        statement_version: manifest.statement_version.clone(),
        step_relation: manifest.step_relation.clone(),
        required_recursion_posture: manifest.required_recursion_posture.clone(),
        recursive_verification_claimed: manifest.recursive_verification_claimed,
        cryptographic_compression_claimed: manifest.cryptographic_compression_claimed,
        phase31_manifest_version: manifest.manifest_version.clone(),
        phase31_semantic_scope: manifest.semantic_scope.clone(),
        phase31_decode_boundary_bridge_commitment: manifest
            .decode_boundary_bridge_commitment
            .clone(),
        phase30_source_chain_commitment: manifest.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: manifest.phase30_step_envelopes_commitment.clone(),
        total_steps: manifest.total_steps,
        chain_start_boundary_commitment: manifest.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: manifest.chain_end_boundary_commitment.clone(),
        source_template_commitment: manifest.source_template_commitment.clone(),
        aggregation_template_commitment: manifest.aggregation_template_commitment.clone(),
        recursive_statement_contract_commitment: String::new(),
    };
    contract.recursive_statement_contract_commitment =
        commit_phase32_recursive_compression_statement_contract(&contract)?;
    verify_phase32_recursive_compression_statement_contract(&contract)?;
    Ok(contract)
}

#[cfg(feature = "stwo-backend")]
pub fn phase33_prepare_recursive_compression_public_input_manifest(
    contract: &Phase32RecursiveCompressionStatementContract,
) -> Result<Phase33RecursiveCompressionPublicInputManifest> {
    verify_phase32_recursive_compression_statement_contract(contract)?;

    let mut manifest = Phase33RecursiveCompressionPublicInputManifest {
        proof_backend: StarkProofBackend::Stwo,
        manifest_version: STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33
            .to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33.to_string(),
        proof_backend_version: contract.proof_backend_version.clone(),
        statement_version: contract.statement_version.clone(),
        step_relation: contract.step_relation.clone(),
        required_recursion_posture: contract.required_recursion_posture.clone(),
        recursive_verification_claimed: contract.recursive_verification_claimed,
        cryptographic_compression_claimed: contract.cryptographic_compression_claimed,
        phase32_contract_version: contract.contract_version.clone(),
        phase32_semantic_scope: contract.semantic_scope.clone(),
        phase32_recursive_statement_contract_commitment: contract
            .recursive_statement_contract_commitment
            .clone(),
        total_steps: contract.total_steps,
        phase30_source_chain_commitment: contract.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: contract.phase30_step_envelopes_commitment.clone(),
        phase31_decode_boundary_bridge_commitment: contract
            .phase31_decode_boundary_bridge_commitment
            .clone(),
        chain_start_boundary_commitment: contract.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: contract.chain_end_boundary_commitment.clone(),
        source_template_commitment: contract.source_template_commitment.clone(),
        aggregation_template_commitment: contract.aggregation_template_commitment.clone(),
        recursive_public_inputs_commitment: String::new(),
    };
    manifest.recursive_public_inputs_commitment =
        commit_phase33_recursive_compression_public_input_manifest(&manifest)?;
    verify_phase33_recursive_compression_public_input_manifest(&manifest)?;
    Ok(manifest)
}

#[cfg(feature = "stwo-backend")]
pub fn phase34_prepare_recursive_compression_shared_lookup_manifest(
    public_inputs: &Phase33RecursiveCompressionPublicInputManifest,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase34RecursiveCompressionSharedLookupManifest> {
    verify_phase33_recursive_compression_public_input_manifest(public_inputs)?;
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;

    if public_inputs.proof_backend_version != phase30.proof_backend_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 shared-lookup manifest requires Phase 33 proof backend version `{}` to match the Phase 30 proof backend version `{}`",
            public_inputs.proof_backend_version, phase30.proof_backend_version
        )));
    }
    if public_inputs.statement_version != phase30.statement_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 shared-lookup manifest requires Phase 33 statement version `{}` to match the Phase 30 statement version `{}`",
            public_inputs.statement_version, phase30.statement_version
        )));
    }
    if public_inputs.total_steps != phase30.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 shared-lookup manifest requires Phase 33 total_steps={} to match the Phase 30 total_steps={}",
            public_inputs.total_steps, phase30.total_steps
        )));
    }
    if public_inputs.phase30_source_chain_commitment != phase30.source_chain_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 34 shared-lookup manifest requires the Phase 33 source-chain commitment to match the Phase 30 source-chain commitment".to_string(),
        ));
    }
    if public_inputs.phase30_step_envelopes_commitment != phase30.step_envelopes_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 34 shared-lookup manifest requires the Phase 33 step-envelope commitment to match the Phase 30 step-envelope commitment".to_string(),
        ));
    }

    let input_lookup_rows_commitment = phase34_commit_ordered_commitment_list(
        b"phase34-input-lookup-rows",
        phase30
            .envelopes
            .iter()
            .map(|envelope| envelope.input_lookup_rows_commitment.as_str()),
    )?;
    let output_lookup_rows_commitment = phase34_commit_ordered_commitment_list(
        b"phase34-output-lookup-rows",
        phase30
            .envelopes
            .iter()
            .map(|envelope| envelope.output_lookup_rows_commitment.as_str()),
    )?;
    let shared_lookup_artifact_commitment = phase34_commit_ordered_commitment_list(
        b"phase34-shared-lookup-artifacts",
        phase30
            .envelopes
            .iter()
            .map(|envelope| envelope.shared_lookup_artifact_commitment.as_str()),
    )?;
    let static_lookup_registry_commitment = phase34_commit_ordered_commitment_list(
        b"phase34-static-lookup-registries",
        phase30
            .envelopes
            .iter()
            .map(|envelope| envelope.static_lookup_registry_commitment.as_str()),
    )?;

    let mut manifest = Phase34RecursiveCompressionSharedLookupManifest {
        proof_backend: StarkProofBackend::Stwo,
        manifest_version: STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34
            .to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34.to_string(),
        proof_backend_version: public_inputs.proof_backend_version.clone(),
        statement_version: public_inputs.statement_version.clone(),
        step_relation: public_inputs.step_relation.clone(),
        required_recursion_posture: public_inputs.required_recursion_posture.clone(),
        recursive_verification_claimed: public_inputs.recursive_verification_claimed,
        cryptographic_compression_claimed: public_inputs.cryptographic_compression_claimed,
        phase33_manifest_version: public_inputs.manifest_version.clone(),
        phase33_semantic_scope: public_inputs.semantic_scope.clone(),
        phase33_recursive_public_inputs_commitment: public_inputs
            .recursive_public_inputs_commitment
            .clone(),
        phase30_manifest_version: phase30.manifest_version.clone(),
        phase30_semantic_scope: phase30.semantic_scope.clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        total_steps: phase30.total_steps,
        input_lookup_rows_commitments_commitment: input_lookup_rows_commitment,
        output_lookup_rows_commitments_commitment: output_lookup_rows_commitment,
        shared_lookup_artifact_commitments_commitment: shared_lookup_artifact_commitment,
        static_lookup_registry_commitments_commitment: static_lookup_registry_commitment,
        shared_lookup_public_inputs_commitment: String::new(),
    };
    manifest.shared_lookup_public_inputs_commitment =
        commit_phase34_recursive_compression_shared_lookup_manifest(&manifest)?;
    verify_phase34_recursive_compression_shared_lookup_manifest(&manifest)?;
    Ok(manifest)
}

#[cfg(feature = "stwo-backend")]
pub fn phase35_prepare_recursive_compression_target_manifest(
    phase32: &Phase32RecursiveCompressionStatementContract,
    phase33: &Phase33RecursiveCompressionPublicInputManifest,
    phase34: &Phase34RecursiveCompressionSharedLookupManifest,
) -> Result<Phase35RecursiveCompressionTargetManifest> {
    verify_phase32_recursive_compression_statement_contract(phase32)?;
    verify_phase33_recursive_compression_public_input_manifest(phase33)?;
    verify_phase34_recursive_compression_shared_lookup_manifest(phase34)?;

    if phase32.proof_backend_version != phase33.proof_backend_version
        || phase32.proof_backend_version != phase34.proof_backend_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 proof backend versions to match".to_string(),
        ));
    }
    if phase32.statement_version != phase33.statement_version
        || phase32.statement_version != phase34.statement_version
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 statement versions to match".to_string(),
        ));
    }
    if phase32.step_relation != phase33.step_relation
        || phase32.step_relation != phase34.step_relation
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 step relations to match".to_string(),
        ));
    }
    if phase32.required_recursion_posture != phase33.required_recursion_posture
        || phase32.required_recursion_posture != phase34.required_recursion_posture
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 recursion posture to match".to_string(),
        ));
    }
    if phase32.recursive_verification_claimed != phase33.recursive_verification_claimed
        || phase32.recursive_verification_claimed != phase34.recursive_verification_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 recursive-verification flags to match".to_string(),
        ));
    }
    if phase32.cryptographic_compression_claimed != phase33.cryptographic_compression_claimed
        || phase32.cryptographic_compression_claimed != phase34.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 cryptographic-compression flags to match".to_string(),
        ));
    }
    if phase32.total_steps != phase33.total_steps || phase32.total_steps != phase34.total_steps {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 total_steps to match".to_string(),
        ));
    }
    if phase33.phase32_recursive_statement_contract_commitment
        != phase32.recursive_statement_contract_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires the Phase 33 statement-contract commitment to match the Phase 32 statement-contract commitment".to_string(),
        ));
    }
    if phase34.phase33_recursive_public_inputs_commitment
        != phase33.recursive_public_inputs_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires the Phase 34 public-input commitment to match the Phase 33 public-input commitment".to_string(),
        ));
    }
    if phase32.phase30_source_chain_commitment != phase33.phase30_source_chain_commitment
        || phase32.phase30_source_chain_commitment != phase34.phase30_source_chain_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 source-chain commitments to match".to_string(),
        ));
    }
    if phase32.phase30_step_envelopes_commitment != phase33.phase30_step_envelopes_commitment
        || phase32.phase30_step_envelopes_commitment != phase34.phase30_step_envelopes_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires Phase 32, Phase 33, and Phase 34 step-envelope commitments to match".to_string(),
        ));
    }
    if phase32.chain_start_boundary_commitment != phase33.chain_start_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires the Phase 32 and Phase 33 start-boundary commitments to match".to_string(),
        ));
    }
    if phase32.chain_end_boundary_commitment != phase33.chain_end_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires the Phase 32 and Phase 33 end-boundary commitments to match".to_string(),
        ));
    }
    if phase32.source_template_commitment != phase33.source_template_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires the Phase 32 and Phase 33 source-template commitments to match".to_string(),
        ));
    }
    if phase32.aggregation_template_commitment != phase33.aggregation_template_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive target manifest requires the Phase 32 and Phase 33 aggregation-template commitments to match".to_string(),
        ));
    }

    let mut manifest = Phase35RecursiveCompressionTargetManifest {
        proof_backend: StarkProofBackend::Stwo,
        manifest_version: STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35.to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35.to_string(),
        proof_backend_version: phase32.proof_backend_version.clone(),
        statement_version: phase32.statement_version.clone(),
        step_relation: phase32.step_relation.clone(),
        required_recursion_posture: phase32.required_recursion_posture.clone(),
        recursive_verification_claimed: phase32.recursive_verification_claimed,
        cryptographic_compression_claimed: phase32.cryptographic_compression_claimed,
        phase32_contract_version: phase32.contract_version.clone(),
        phase32_semantic_scope: phase32.semantic_scope.clone(),
        phase32_recursive_statement_contract_commitment: phase32
            .recursive_statement_contract_commitment
            .clone(),
        phase33_manifest_version: phase33.manifest_version.clone(),
        phase33_semantic_scope: phase33.semantic_scope.clone(),
        phase33_recursive_public_inputs_commitment: phase33
            .recursive_public_inputs_commitment
            .clone(),
        phase34_manifest_version: phase34.manifest_version.clone(),
        phase34_semantic_scope: phase34.semantic_scope.clone(),
        phase34_shared_lookup_public_inputs_commitment: phase34
            .shared_lookup_public_inputs_commitment
            .clone(),
        total_steps: phase32.total_steps,
        phase30_source_chain_commitment: phase32.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase32.phase30_step_envelopes_commitment.clone(),
        chain_start_boundary_commitment: phase32.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: phase32.chain_end_boundary_commitment.clone(),
        source_template_commitment: phase32.source_template_commitment.clone(),
        aggregation_template_commitment: phase32.aggregation_template_commitment.clone(),
        input_lookup_rows_commitments_commitment: phase34
            .input_lookup_rows_commitments_commitment
            .clone(),
        output_lookup_rows_commitments_commitment: phase34
            .output_lookup_rows_commitments_commitment
            .clone(),
        shared_lookup_artifact_commitments_commitment: phase34
            .shared_lookup_artifact_commitments_commitment
            .clone(),
        static_lookup_registry_commitments_commitment: phase34
            .static_lookup_registry_commitments_commitment
            .clone(),
        recursive_target_manifest_commitment: String::new(),
    };
    manifest.recursive_target_manifest_commitment =
        commit_phase35_recursive_compression_target_manifest(&manifest)?;
    verify_phase35_recursive_compression_target_manifest(&manifest)?;
    Ok(manifest)
}

#[cfg(feature = "stwo-backend")]
pub fn phase36_prepare_recursive_verifier_harness_receipt(
    target: &Phase35RecursiveCompressionTargetManifest,
    phase32: &Phase32RecursiveCompressionStatementContract,
    phase33: &Phase33RecursiveCompressionPublicInputManifest,
    phase34: &Phase34RecursiveCompressionSharedLookupManifest,
) -> Result<Phase36RecursiveVerifierHarnessReceipt> {
    verify_phase35_recursive_compression_target_manifest_against_sources(
        target, phase32, phase33, phase34,
    )?;

    let mut receipt = Phase36RecursiveVerifierHarnessReceipt {
        proof_backend: StarkProofBackend::Stwo,
        receipt_version: STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36.to_string(),
        semantic_scope: STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36.to_string(),
        verifier_harness: STWO_RECURSIVE_VERIFIER_HARNESS_KIND_PHASE36.to_string(),
        proof_backend_version: target.proof_backend_version.clone(),
        statement_version: target.statement_version.clone(),
        step_relation: target.step_relation.clone(),
        required_recursion_posture: target.required_recursion_posture.clone(),
        recursive_verification_claimed: target.recursive_verification_claimed,
        cryptographic_compression_claimed: target.cryptographic_compression_claimed,
        target_manifest_verified: true,
        source_binding_verified: true,
        phase35_manifest_version: target.manifest_version.clone(),
        phase35_semantic_scope: target.semantic_scope.clone(),
        phase35_recursive_target_manifest_commitment: target
            .recursive_target_manifest_commitment
            .clone(),
        phase32_recursive_statement_contract_commitment: target
            .phase32_recursive_statement_contract_commitment
            .clone(),
        phase33_recursive_public_inputs_commitment: target
            .phase33_recursive_public_inputs_commitment
            .clone(),
        phase34_shared_lookup_public_inputs_commitment: target
            .phase34_shared_lookup_public_inputs_commitment
            .clone(),
        total_steps: target.total_steps,
        phase30_source_chain_commitment: target.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: target.phase30_step_envelopes_commitment.clone(),
        chain_start_boundary_commitment: target.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: target.chain_end_boundary_commitment.clone(),
        input_lookup_rows_commitments_commitment: target
            .input_lookup_rows_commitments_commitment
            .clone(),
        output_lookup_rows_commitments_commitment: target
            .output_lookup_rows_commitments_commitment
            .clone(),
        shared_lookup_artifact_commitments_commitment: target
            .shared_lookup_artifact_commitments_commitment
            .clone(),
        static_lookup_registry_commitments_commitment: target
            .static_lookup_registry_commitments_commitment
            .clone(),
        recursive_verifier_harness_receipt_commitment: String::new(),
    };
    receipt.recursive_verifier_harness_receipt_commitment =
        commit_phase36_recursive_verifier_harness_receipt(&receipt)?;
    verify_phase36_recursive_verifier_harness_receipt(&receipt)?;
    Ok(receipt)
}

#[cfg(feature = "stwo-backend")]
pub fn phase37_prepare_recursive_artifact_chain_harness_receipt(
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase37RecursiveArtifactChainHarnessReceipt> {
    verify_phase29_recursive_compression_input_contract(contract)?;
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;

    let phase31 =
        phase31_prepare_recursive_compression_decode_boundary_manifest(contract, phase30)?;
    verify_phase31_recursive_compression_decode_boundary_manifest_against_sources(
        &phase31, contract, phase30,
    )?;
    let phase32 = phase32_prepare_recursive_compression_statement_contract(&phase31)?;
    verify_phase32_recursive_compression_statement_contract_against_phase31(&phase32, &phase31)?;
    let phase33 = phase33_prepare_recursive_compression_public_input_manifest(&phase32)?;
    verify_phase33_recursive_compression_public_input_manifest_against_phase32(&phase33, &phase32)?;
    let phase34 = phase34_prepare_recursive_compression_shared_lookup_manifest(&phase33, phase30)?;
    verify_phase34_recursive_compression_shared_lookup_manifest_against_sources(
        &phase34, &phase33, phase30,
    )?;
    let phase35 =
        phase35_prepare_recursive_compression_target_manifest(&phase32, &phase33, &phase34)?;
    verify_phase35_recursive_compression_target_manifest_against_sources(
        &phase35, &phase32, &phase33, &phase34,
    )?;
    let phase36 =
        phase36_prepare_recursive_verifier_harness_receipt(&phase35, &phase32, &phase33, &phase34)?;
    verify_phase36_recursive_verifier_harness_receipt_against_sources(
        &phase36, &phase35, &phase32, &phase33, &phase34,
    )?;

    let mut receipt = Phase37RecursiveArtifactChainHarnessReceipt {
        proof_backend: StarkProofBackend::Stwo,
        receipt_version: STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37.to_string(),
        semantic_scope: STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37.to_string(),
        verifier_harness: STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_KIND_PHASE37.to_string(),
        proof_backend_version: phase35.proof_backend_version.clone(),
        statement_version: phase35.statement_version.clone(),
        step_relation: phase35.step_relation.clone(),
        required_recursion_posture: phase35.required_recursion_posture.clone(),
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        phase29_input_contract_verified: true,
        phase30_step_envelope_manifest_verified: true,
        phase31_decode_boundary_bridge_verified: true,
        phase32_statement_contract_verified: true,
        phase33_public_inputs_verified: true,
        phase34_shared_lookup_verified: true,
        phase35_target_manifest_verified: true,
        phase36_verifier_harness_receipt_verified: true,
        source_binding_verified: true,
        phase29_contract_version: contract.contract_version.clone(),
        phase29_semantic_scope: contract.semantic_scope.clone(),
        phase29_input_contract_commitment: contract.input_contract_commitment.clone(),
        phase30_manifest_version: phase30.manifest_version.clone(),
        phase30_semantic_scope: phase30.semantic_scope.clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        phase31_decode_boundary_bridge_commitment: phase31.decode_boundary_bridge_commitment,
        phase32_recursive_statement_contract_commitment: phase32
            .recursive_statement_contract_commitment,
        phase33_recursive_public_inputs_commitment: phase33.recursive_public_inputs_commitment,
        phase34_shared_lookup_public_inputs_commitment: phase34
            .shared_lookup_public_inputs_commitment,
        phase35_recursive_target_manifest_commitment: phase35.recursive_target_manifest_commitment,
        phase36_recursive_verifier_harness_receipt_commitment: phase36
            .recursive_verifier_harness_receipt_commitment,
        total_steps: phase35.total_steps,
        chain_start_boundary_commitment: phase35.chain_start_boundary_commitment,
        chain_end_boundary_commitment: phase35.chain_end_boundary_commitment,
        source_template_commitment: phase35.source_template_commitment,
        aggregation_template_commitment: phase35.aggregation_template_commitment,
        input_lookup_rows_commitments_commitment: phase35.input_lookup_rows_commitments_commitment,
        output_lookup_rows_commitments_commitment: phase35
            .output_lookup_rows_commitments_commitment,
        shared_lookup_artifact_commitments_commitment: phase35
            .shared_lookup_artifact_commitments_commitment,
        static_lookup_registry_commitments_commitment: phase35
            .static_lookup_registry_commitments_commitment,
        recursive_artifact_chain_harness_receipt_commitment: String::new(),
    };
    receipt.recursive_artifact_chain_harness_receipt_commitment =
        commit_phase37_recursive_artifact_chain_harness_receipt(&receipt)?;
    verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)?;
    Ok(receipt)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase31_recursive_compression_decode_boundary_manifest(
    manifest: &Phase31RecursiveCompressionDecodeBoundaryManifest,
) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires `stwo` backend, got `{}`",
            manifest.proof_backend
        )));
    }
    if manifest.manifest_version
        != STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest version `{}` does not match expected `{}`",
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31
        )));
    }
    if manifest.semantic_scope != STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest scope `{}` does not match expected `{}`",
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31
        )));
    }
    if manifest.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, manifest.proof_backend_version
        )));
    }
    if manifest.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, manifest.statement_version
        )));
    }
    if manifest.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, manifest.step_relation
        )));
    }
    if manifest.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, manifest.required_recursion_posture
        )));
    }
    if manifest.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 31 decode-boundary manifest must not claim recursive verification".to_string(),
        ));
    }
    if manifest.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 31 decode-boundary manifest must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if manifest.phase29_contract_version
        != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires Phase 29 contract version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
            manifest.phase29_contract_version
        )));
    }
    if manifest.phase29_semantic_scope != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires Phase 29 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
            manifest.phase29_semantic_scope
        )));
    }
    if manifest.phase30_manifest_version != STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires Phase 30 manifest version `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30, manifest.phase30_manifest_version
        )));
    }
    if manifest.phase30_semantic_scope != STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest requires Phase 30 semantic scope `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30, manifest.phase30_semantic_scope
        )));
    }
    if manifest.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 31 decode-boundary manifest requires at least one decode step".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase29_contract_commitment",
            manifest.phase29_contract_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            manifest.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            manifest.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "chain_start_boundary_commitment",
            manifest.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            manifest.chain_end_boundary_commitment.as_str(),
        ),
        (
            "source_template_commitment",
            manifest.source_template_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            manifest.aggregation_template_commitment.as_str(),
        ),
        (
            "decode_boundary_bridge_commitment",
            manifest.decode_boundary_bridge_commitment.as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 31 decode-boundary manifest `{label}` must be non-empty"
            )));
        }
    }

    let expected = commit_phase31_recursive_compression_decode_boundary_manifest(manifest)?;
    if manifest.decode_boundary_bridge_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 decode-boundary manifest commitment `{}` does not match recomputed `{}`",
            manifest.decode_boundary_bridge_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase31_recursive_compression_decode_boundary_manifest_against_sources(
    manifest: &Phase31RecursiveCompressionDecodeBoundaryManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase31_recursive_compression_decode_boundary_manifest(manifest)?;
    let expected =
        phase31_prepare_recursive_compression_decode_boundary_manifest(contract, phase30)?;
    if manifest != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 31 decode-boundary manifest does not match the recomputed Phase 29 + Phase 30 source artifacts".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase32_recursive_compression_statement_contract(
    contract: &Phase32RecursiveCompressionStatementContract,
) -> Result<()> {
    if contract.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires `stwo` backend, got `{}`",
            contract.proof_backend
        )));
    }
    if contract.contract_version != STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract version `{}` does not match expected `{}`",
            contract.contract_version,
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32
        )));
    }
    if contract.semantic_scope != STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract scope `{}` does not match expected `{}`",
            contract.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32
        )));
    }
    if contract.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, contract.proof_backend_version
        )));
    }
    if contract.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, contract.statement_version
        )));
    }
    if contract.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, contract.step_relation
        )));
    }
    if contract.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, contract.required_recursion_posture
        )));
    }
    if contract.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 32 recursive-compression statement contract must not claim recursive verification"
                .to_string(),
        ));
    }
    if contract.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 32 recursive-compression statement contract must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if contract.phase31_manifest_version
        != STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires Phase 31 manifest version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31,
            contract.phase31_manifest_version
        )));
    }
    if contract.phase31_semantic_scope
        != STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract requires Phase 31 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31,
            contract.phase31_semantic_scope
        )));
    }
    if contract.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 32 recursive-compression statement contract requires at least one decode step"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase31_decode_boundary_bridge_commitment",
            contract.phase31_decode_boundary_bridge_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            contract.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            contract.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "chain_start_boundary_commitment",
            contract.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            contract.chain_end_boundary_commitment.as_str(),
        ),
        (
            "source_template_commitment",
            contract.source_template_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            contract.aggregation_template_commitment.as_str(),
        ),
        (
            "recursive_statement_contract_commitment",
            contract.recursive_statement_contract_commitment.as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 32 recursive-compression statement contract `{label}` must be non-empty"
            )));
        }
    }

    let expected = commit_phase32_recursive_compression_statement_contract(contract)?;
    if contract.recursive_statement_contract_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract commitment `{}` does not match recomputed `{}`",
            contract.recursive_statement_contract_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase32_recursive_compression_statement_contract_against_phase31(
    contract: &Phase32RecursiveCompressionStatementContract,
    manifest: &Phase31RecursiveCompressionDecodeBoundaryManifest,
) -> Result<()> {
    verify_phase32_recursive_compression_statement_contract(contract)?;
    let expected = phase32_prepare_recursive_compression_statement_contract(manifest)?;
    if contract != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 32 recursive-compression statement contract does not match the recomputed Phase 31 source manifest".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase33_recursive_compression_public_input_manifest(
    manifest: &Phase33RecursiveCompressionPublicInputManifest,
) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires `stwo` backend, got `{}`",
            manifest.proof_backend
        )));
    }
    if manifest.manifest_version != STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest version `{}` does not match expected `{}`",
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33
        )));
    }
    if manifest.semantic_scope != STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest scope `{}` does not match expected `{}`",
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33
        )));
    }
    if manifest.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, manifest.proof_backend_version
        )));
    }
    if manifest.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, manifest.statement_version
        )));
    }
    if manifest.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, manifest.step_relation
        )));
    }
    if manifest.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, manifest.required_recursion_posture
        )));
    }
    if manifest.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 33 recursive-compression public-input manifest must not claim recursive verification"
                .to_string(),
        ));
    }
    if manifest.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 33 recursive-compression public-input manifest must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if manifest.phase32_contract_version
        != STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires Phase 32 contract version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32,
            manifest.phase32_contract_version
        )));
    }
    if manifest.phase32_semantic_scope
        != STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest requires Phase 32 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32,
            manifest.phase32_semantic_scope
        )));
    }
    if manifest.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 33 recursive-compression public-input manifest requires at least one decode step"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase32_recursive_statement_contract_commitment",
            manifest
                .phase32_recursive_statement_contract_commitment
                .as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            manifest.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            manifest.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "phase31_decode_boundary_bridge_commitment",
            manifest.phase31_decode_boundary_bridge_commitment.as_str(),
        ),
        (
            "chain_start_boundary_commitment",
            manifest.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            manifest.chain_end_boundary_commitment.as_str(),
        ),
        (
            "source_template_commitment",
            manifest.source_template_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            manifest.aggregation_template_commitment.as_str(),
        ),
        (
            "recursive_public_inputs_commitment",
            manifest.recursive_public_inputs_commitment.as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 33 recursive-compression public-input manifest `{label}` must be non-empty"
            )));
        }
    }

    let expected = commit_phase33_recursive_compression_public_input_manifest(manifest)?;
    if manifest.recursive_public_inputs_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest commitment `{}` does not match recomputed `{}`",
            manifest.recursive_public_inputs_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase33_recursive_compression_public_input_manifest_against_phase32(
    manifest: &Phase33RecursiveCompressionPublicInputManifest,
    contract: &Phase32RecursiveCompressionStatementContract,
) -> Result<()> {
    verify_phase33_recursive_compression_public_input_manifest(manifest)?;
    let expected = phase33_prepare_recursive_compression_public_input_manifest(contract)?;
    if manifest != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 33 recursive-compression public-input manifest does not match the recomputed Phase 32 source contract".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase34_recursive_compression_shared_lookup_manifest(
    manifest: &Phase34RecursiveCompressionSharedLookupManifest,
) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires `stwo` backend, got `{}`",
            manifest.proof_backend
        )));
    }
    if manifest.manifest_version
        != STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest version `{}` does not match expected `{}`",
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34
        )));
    }
    if manifest.semantic_scope != STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest scope `{}` does not match expected `{}`",
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34
        )));
    }
    if manifest.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, manifest.proof_backend_version
        )));
    }
    if manifest.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, manifest.statement_version
        )));
    }
    if manifest.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, manifest.step_relation
        )));
    }
    if manifest.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, manifest.required_recursion_posture
        )));
    }
    if manifest.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 34 recursive-compression shared-lookup manifest must not claim recursive verification"
                .to_string(),
        ));
    }
    if manifest.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 34 recursive-compression shared-lookup manifest must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if manifest.phase33_manifest_version
        != STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires Phase 33 manifest version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33,
            manifest.phase33_manifest_version
        )));
    }
    if manifest.phase33_semantic_scope
        != STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires Phase 33 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33,
            manifest.phase33_semantic_scope
        )));
    }
    if manifest.phase30_manifest_version != STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires Phase 30 manifest version `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
            manifest.phase30_manifest_version
        )));
    }
    if manifest.phase30_semantic_scope != STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest requires Phase 30 semantic scope `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
            manifest.phase30_semantic_scope
        )));
    }
    if manifest.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 34 recursive-compression shared-lookup manifest requires at least one decode step"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase33_recursive_public_inputs_commitment",
            manifest.phase33_recursive_public_inputs_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            manifest.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            manifest.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "input_lookup_rows_commitments_commitment",
            manifest.input_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "output_lookup_rows_commitments_commitment",
            manifest.output_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "shared_lookup_artifact_commitments_commitment",
            manifest
                .shared_lookup_artifact_commitments_commitment
                .as_str(),
        ),
        (
            "static_lookup_registry_commitments_commitment",
            manifest
                .static_lookup_registry_commitments_commitment
                .as_str(),
        ),
        (
            "shared_lookup_public_inputs_commitment",
            manifest.shared_lookup_public_inputs_commitment.as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 34 recursive-compression shared-lookup manifest `{label}` must be non-empty"
            )));
        }
    }

    let expected = commit_phase34_recursive_compression_shared_lookup_manifest(manifest)?;
    if manifest.shared_lookup_public_inputs_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest commitment `{}` does not match recomputed `{}`",
            manifest.shared_lookup_public_inputs_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase34_recursive_compression_shared_lookup_manifest_against_sources(
    manifest: &Phase34RecursiveCompressionSharedLookupManifest,
    public_inputs: &Phase33RecursiveCompressionPublicInputManifest,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase34_recursive_compression_shared_lookup_manifest(manifest)?;
    let expected =
        phase34_prepare_recursive_compression_shared_lookup_manifest(public_inputs, phase30)?;
    if manifest != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 34 recursive-compression shared-lookup manifest does not match the recomputed Phase 33 + Phase 30 source artifacts".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase35_recursive_compression_target_manifest(
    manifest: &Phase35RecursiveCompressionTargetManifest,
) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires `stwo` backend, got `{}`",
            manifest.proof_backend
        )));
    }
    if manifest.manifest_version != STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest version `{}` does not match expected `{}`",
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35
        )));
    }
    if manifest.semantic_scope != STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest scope `{}` does not match expected `{}`",
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35
        )));
    }
    if manifest.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, manifest.proof_backend_version
        )));
    }
    if manifest.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, manifest.statement_version
        )));
    }
    if manifest.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, manifest.step_relation
        )));
    }
    if manifest.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, manifest.required_recursion_posture
        )));
    }
    if manifest.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive-compression target manifest must not claim recursive verification"
                .to_string(),
        ));
    }
    if manifest.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive-compression target manifest must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if manifest.phase32_contract_version
        != STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires Phase 32 contract version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32,
            manifest.phase32_contract_version
        )));
    }
    if manifest.phase32_semantic_scope
        != STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires Phase 32 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32,
            manifest.phase32_semantic_scope
        )));
    }
    if manifest.phase33_manifest_version
        != STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires Phase 33 manifest version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33,
            manifest.phase33_manifest_version
        )));
    }
    if manifest.phase33_semantic_scope
        != STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires Phase 33 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33,
            manifest.phase33_semantic_scope
        )));
    }
    if manifest.phase34_manifest_version
        != STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires Phase 34 manifest version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34,
            manifest.phase34_manifest_version
        )));
    }
    if manifest.phase34_semantic_scope
        != STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest requires Phase 34 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34,
            manifest.phase34_semantic_scope
        )));
    }
    if manifest.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive-compression target manifest requires at least one decode step"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase32_recursive_statement_contract_commitment",
            manifest
                .phase32_recursive_statement_contract_commitment
                .as_str(),
        ),
        (
            "phase33_recursive_public_inputs_commitment",
            manifest.phase33_recursive_public_inputs_commitment.as_str(),
        ),
        (
            "phase34_shared_lookup_public_inputs_commitment",
            manifest
                .phase34_shared_lookup_public_inputs_commitment
                .as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            manifest.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            manifest.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "chain_start_boundary_commitment",
            manifest.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            manifest.chain_end_boundary_commitment.as_str(),
        ),
        (
            "source_template_commitment",
            manifest.source_template_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            manifest.aggregation_template_commitment.as_str(),
        ),
        (
            "input_lookup_rows_commitments_commitment",
            manifest.input_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "output_lookup_rows_commitments_commitment",
            manifest.output_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "shared_lookup_artifact_commitments_commitment",
            manifest
                .shared_lookup_artifact_commitments_commitment
                .as_str(),
        ),
        (
            "static_lookup_registry_commitments_commitment",
            manifest
                .static_lookup_registry_commitments_commitment
                .as_str(),
        ),
        (
            "recursive_target_manifest_commitment",
            manifest.recursive_target_manifest_commitment.as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 35 recursive-compression target manifest `{label}` must be non-empty"
            )));
        }
    }

    let expected = commit_phase35_recursive_compression_target_manifest(manifest)?;
    if manifest.recursive_target_manifest_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest commitment `{}` does not match recomputed `{}`",
            manifest.recursive_target_manifest_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase35_recursive_compression_target_manifest_against_sources(
    manifest: &Phase35RecursiveCompressionTargetManifest,
    phase32: &Phase32RecursiveCompressionStatementContract,
    phase33: &Phase33RecursiveCompressionPublicInputManifest,
    phase34: &Phase34RecursiveCompressionSharedLookupManifest,
) -> Result<()> {
    verify_phase35_recursive_compression_target_manifest(manifest)?;
    let expected =
        phase35_prepare_recursive_compression_target_manifest(phase32, phase33, phase34)?;
    if manifest != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 35 recursive-compression target manifest does not match the recomputed Phase 32 + Phase 33 + Phase 34 source artifacts".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase36_recursive_verifier_harness_receipt(
    receipt: &Phase36RecursiveVerifierHarnessReceipt,
) -> Result<()> {
    if receipt.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires `stwo` backend, got `{}`",
            receipt.proof_backend
        )));
    }
    if receipt.receipt_version != STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt version `{}` does not match expected `{}`",
            receipt.receipt_version, STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36
        )));
    }
    if receipt.semantic_scope != STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt scope `{}` does not match expected `{}`",
            receipt.semantic_scope, STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36
        )));
    }
    if receipt.verifier_harness != STWO_RECURSIVE_VERIFIER_HARNESS_KIND_PHASE36 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires verifier harness `{}`, got `{}`",
            STWO_RECURSIVE_VERIFIER_HARNESS_KIND_PHASE36, receipt.verifier_harness
        )));
    }
    if receipt.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, receipt.proof_backend_version
        )));
    }
    if receipt.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, receipt.statement_version
        )));
    }
    if receipt.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, receipt.step_relation
        )));
    }
    if receipt.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, receipt.required_recursion_posture
        )));
    }
    if receipt.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt must not claim recursive verification"
                .to_string(),
        ));
    }
    if receipt.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if !receipt.target_manifest_verified {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt must record target_manifest_verified=true"
                .to_string(),
        ));
    }
    if !receipt.source_binding_verified {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt must record source_binding_verified=true"
                .to_string(),
        ));
    }
    if receipt.phase35_manifest_version
        != STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires Phase 35 manifest version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35,
            receipt.phase35_manifest_version
        )));
    }
    if receipt.phase35_semantic_scope != STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt requires Phase 35 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35,
            receipt.phase35_semantic_scope
        )));
    }
    if receipt.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt requires at least one decode step"
                .to_string(),
        ));
    }
    if !phase36_receipt_flag_surface_is_valid(
        receipt.recursive_verification_claimed,
        receipt.cryptographic_compression_claimed,
        receipt.target_manifest_verified,
        receipt.source_binding_verified,
        receipt.total_steps,
    ) {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt flag surface is invalid".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase35_recursive_target_manifest_commitment",
            receipt
                .phase35_recursive_target_manifest_commitment
                .as_str(),
        ),
        (
            "phase32_recursive_statement_contract_commitment",
            receipt
                .phase32_recursive_statement_contract_commitment
                .as_str(),
        ),
        (
            "phase33_recursive_public_inputs_commitment",
            receipt.phase33_recursive_public_inputs_commitment.as_str(),
        ),
        (
            "phase34_shared_lookup_public_inputs_commitment",
            receipt
                .phase34_shared_lookup_public_inputs_commitment
                .as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            receipt.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            receipt.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "chain_start_boundary_commitment",
            receipt.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            receipt.chain_end_boundary_commitment.as_str(),
        ),
        (
            "input_lookup_rows_commitments_commitment",
            receipt.input_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "output_lookup_rows_commitments_commitment",
            receipt.output_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "shared_lookup_artifact_commitments_commitment",
            receipt
                .shared_lookup_artifact_commitments_commitment
                .as_str(),
        ),
        (
            "static_lookup_registry_commitments_commitment",
            receipt
                .static_lookup_registry_commitments_commitment
                .as_str(),
        ),
        (
            "recursive_verifier_harness_receipt_commitment",
            receipt
                .recursive_verifier_harness_receipt_commitment
                .as_str(),
        ),
    ] {
        if value.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 36 recursive verifier harness receipt `{label}` must be non-empty"
            )));
        }
    }

    let expected = commit_phase36_recursive_verifier_harness_receipt(receipt)?;
    if receipt.recursive_verifier_harness_receipt_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt commitment `{}` does not match recomputed `{}`",
            receipt.recursive_verifier_harness_receipt_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase36_recursive_verifier_harness_receipt_against_sources(
    receipt: &Phase36RecursiveVerifierHarnessReceipt,
    target: &Phase35RecursiveCompressionTargetManifest,
    phase32: &Phase32RecursiveCompressionStatementContract,
    phase33: &Phase33RecursiveCompressionPublicInputManifest,
    phase34: &Phase34RecursiveCompressionSharedLookupManifest,
) -> Result<()> {
    verify_phase36_recursive_verifier_harness_receipt(receipt)?;
    let expected =
        phase36_prepare_recursive_verifier_harness_receipt(target, phase32, phase33, phase34)?;
    if receipt != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 36 recursive verifier harness receipt does not match the recomputed Phase 35 target + Phase 32 + Phase 33 + Phase 34 source artifacts".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase37_recursive_artifact_chain_harness_receipt(
    receipt: &Phase37RecursiveArtifactChainHarnessReceipt,
) -> Result<()> {
    if receipt.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires `stwo` backend, got `{}`",
            receipt.proof_backend
        )));
    }
    if receipt.receipt_version != STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt version `{}` does not match expected `{}`",
            receipt.receipt_version,
            STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37
        )));
    }
    if receipt.semantic_scope != STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt scope `{}` does not match expected `{}`",
            receipt.semantic_scope,
            STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37
        )));
    }
    if receipt.verifier_harness != STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_KIND_PHASE37 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires verifier harness `{}`, got `{}`",
            STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_KIND_PHASE37, receipt.verifier_harness
        )));
    }
    if receipt.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, receipt.proof_backend_version
        )));
    }
    if receipt.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, receipt.statement_version
        )));
    }
    if receipt.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, receipt.step_relation
        )));
    }
    if receipt.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, receipt.required_recursion_posture
        )));
    }
    if receipt.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 37 recursive artifact-chain harness receipt must not claim recursive verification"
                .to_string(),
        ));
    }
    if receipt.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 37 recursive artifact-chain harness receipt must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if receipt.phase29_contract_version != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires Phase 29 contract version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
            receipt.phase29_contract_version
        )));
    }
    if receipt.phase29_semantic_scope != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires Phase 29 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
            receipt.phase29_semantic_scope
        )));
    }
    if receipt.phase30_manifest_version != STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires Phase 30 manifest version `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
            receipt.phase30_manifest_version
        )));
    }
    if receipt.phase30_semantic_scope != STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt requires Phase 30 semantic scope `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
            receipt.phase30_semantic_scope
        )));
    }
    for (label, verified) in [
        (
            "phase29_input_contract_verified",
            receipt.phase29_input_contract_verified,
        ),
        (
            "phase30_step_envelope_manifest_verified",
            receipt.phase30_step_envelope_manifest_verified,
        ),
        (
            "phase31_decode_boundary_bridge_verified",
            receipt.phase31_decode_boundary_bridge_verified,
        ),
        (
            "phase32_statement_contract_verified",
            receipt.phase32_statement_contract_verified,
        ),
        (
            "phase33_public_inputs_verified",
            receipt.phase33_public_inputs_verified,
        ),
        (
            "phase34_shared_lookup_verified",
            receipt.phase34_shared_lookup_verified,
        ),
        (
            "phase35_target_manifest_verified",
            receipt.phase35_target_manifest_verified,
        ),
        (
            "phase36_verifier_harness_receipt_verified",
            receipt.phase36_verifier_harness_receipt_verified,
        ),
        ("source_binding_verified", receipt.source_binding_verified),
    ] {
        if !verified {
            return Err(VmError::InvalidConfig(format!(
                "Phase 37 recursive artifact-chain harness receipt must record {label}=true"
            )));
        }
    }
    if receipt.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 37 recursive artifact-chain harness receipt requires at least one decode step"
                .to_string(),
        ));
    }
    if !phase37_receipt_flag_surface_is_valid(
        receipt.recursive_verification_claimed,
        receipt.cryptographic_compression_claimed,
        &[
            receipt.phase29_input_contract_verified,
            receipt.phase30_step_envelope_manifest_verified,
            receipt.phase31_decode_boundary_bridge_verified,
            receipt.phase32_statement_contract_verified,
            receipt.phase33_public_inputs_verified,
            receipt.phase34_shared_lookup_verified,
            receipt.phase35_target_manifest_verified,
            receipt.phase36_verifier_harness_receipt_verified,
            receipt.source_binding_verified,
        ],
        receipt.total_steps,
    ) {
        return Err(VmError::InvalidConfig(
            "Phase 37 recursive artifact-chain harness receipt flag surface is invalid".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase29_input_contract_commitment",
            receipt.phase29_input_contract_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            receipt.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            receipt.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "phase31_decode_boundary_bridge_commitment",
            receipt.phase31_decode_boundary_bridge_commitment.as_str(),
        ),
        (
            "phase32_recursive_statement_contract_commitment",
            receipt
                .phase32_recursive_statement_contract_commitment
                .as_str(),
        ),
        (
            "phase33_recursive_public_inputs_commitment",
            receipt.phase33_recursive_public_inputs_commitment.as_str(),
        ),
        (
            "phase34_shared_lookup_public_inputs_commitment",
            receipt
                .phase34_shared_lookup_public_inputs_commitment
                .as_str(),
        ),
        (
            "phase35_recursive_target_manifest_commitment",
            receipt
                .phase35_recursive_target_manifest_commitment
                .as_str(),
        ),
        (
            "phase36_recursive_verifier_harness_receipt_commitment",
            receipt
                .phase36_recursive_verifier_harness_receipt_commitment
                .as_str(),
        ),
        (
            "chain_start_boundary_commitment",
            receipt.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            receipt.chain_end_boundary_commitment.as_str(),
        ),
        (
            "source_template_commitment",
            receipt.source_template_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            receipt.aggregation_template_commitment.as_str(),
        ),
        (
            "input_lookup_rows_commitments_commitment",
            receipt.input_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "output_lookup_rows_commitments_commitment",
            receipt.output_lookup_rows_commitments_commitment.as_str(),
        ),
        (
            "shared_lookup_artifact_commitments_commitment",
            receipt
                .shared_lookup_artifact_commitments_commitment
                .as_str(),
        ),
        (
            "static_lookup_registry_commitments_commitment",
            receipt
                .static_lookup_registry_commitments_commitment
                .as_str(),
        ),
        (
            "recursive_artifact_chain_harness_receipt_commitment",
            receipt
                .recursive_artifact_chain_harness_receipt_commitment
                .as_str(),
        ),
    ] {
        phase37_require_hash32(label, value)?;
    }

    let expected = commit_phase37_recursive_artifact_chain_harness_receipt(receipt)?;
    if receipt.recursive_artifact_chain_harness_receipt_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt commitment `{}` does not match recomputed `{}`",
            receipt.recursive_artifact_chain_harness_receipt_commitment, expected
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase37_recursive_artifact_chain_harness_receipt_against_sources(
    receipt: &Phase37RecursiveArtifactChainHarnessReceipt,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase37_recursive_artifact_chain_harness_receipt(receipt)?;
    let expected = phase37_prepare_recursive_artifact_chain_harness_receipt(contract, phase30)?;
    if receipt != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 37 recursive artifact-chain harness receipt does not match the recomputed Phase 29 + Phase 30 source artifacts".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase38_segment_from_phase37_receipt(
    segment_index: usize,
    step_start: usize,
    receipt: &Phase37RecursiveArtifactChainHarnessReceipt,
) -> Result<Phase38Paper3CompositionSegment> {
    let step_end = step_start.checked_add(receipt.total_steps).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype step interval overflowed usize".to_string(),
        )
    })?;
    Ok(Phase38Paper3CompositionSegment {
        segment_index,
        step_start,
        step_end,
        total_steps: receipt.total_steps,
        phase37_receipt_commitment: receipt
            .recursive_artifact_chain_harness_receipt_commitment
            .clone(),
        phase30_source_chain_commitment: receipt.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: receipt.phase30_step_envelopes_commitment.clone(),
        chain_start_boundary_commitment: receipt.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: receipt.chain_end_boundary_commitment.clone(),
        phase34_shared_lookup_public_inputs_commitment: receipt
            .phase34_shared_lookup_public_inputs_commitment
            .clone(),
        input_lookup_rows_commitments_commitment: receipt
            .input_lookup_rows_commitments_commitment
            .clone(),
        output_lookup_rows_commitments_commitment: receipt
            .output_lookup_rows_commitments_commitment
            .clone(),
        shared_lookup_artifact_commitments_commitment: receipt
            .shared_lookup_artifact_commitments_commitment
            .clone(),
        static_lookup_registry_commitments_commitment: receipt
            .static_lookup_registry_commitments_commitment
            .clone(),
    })
}

#[cfg(feature = "stwo-backend")]
fn phase38_shared_lookup_identity_matches(
    left: &Phase38Paper3CompositionSegment,
    right: &Phase38Paper3CompositionSegment,
) -> bool {
    left.phase34_shared_lookup_public_inputs_commitment
        == right.phase34_shared_lookup_public_inputs_commitment
        && left.input_lookup_rows_commitments_commitment
            == right.input_lookup_rows_commitments_commitment
        && left.output_lookup_rows_commitments_commitment
            == right.output_lookup_rows_commitments_commitment
        && left.shared_lookup_artifact_commitments_commitment
            == right.shared_lookup_artifact_commitments_commitment
        && left.static_lookup_registry_commitments_commitment
            == right.static_lookup_registry_commitments_commitment
}

#[cfg(feature = "stwo-backend")]
pub fn phase38_prepare_paper3_composition_prototype(
    receipts: &[Phase37RecursiveArtifactChainHarnessReceipt],
) -> Result<Phase38Paper3CompositionPrototype> {
    let first = receipts.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype requires at least two Phase 37 receipts"
                .to_string(),
        )
    })?;
    if receipts.len() < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype requires at least two Phase 37 receipts"
                .to_string(),
        ));
    }

    verify_phase37_recursive_artifact_chain_harness_receipt(first)?;
    let mut segments: Vec<Phase38Paper3CompositionSegment> = Vec::with_capacity(receipts.len());
    let mut cursor = 0usize;
    for (index, receipt) in receipts.iter().enumerate() {
        verify_phase37_recursive_artifact_chain_harness_receipt(receipt)?;
        if receipt.proof_backend != first.proof_backend
            || receipt.proof_backend_version != first.proof_backend_version
            || receipt.statement_version != first.statement_version
            || receipt.step_relation != first.step_relation
            || receipt.required_recursion_posture != first.required_recursion_posture
        {
            return Err(VmError::InvalidConfig(
                "Phase 38 Paper 3 composition prototype requires all Phase 37 receipts to share the same statement header".to_string(),
            ));
        }
        if receipt.recursive_verification_claimed || receipt.cryptographic_compression_claimed {
            return Err(VmError::InvalidConfig(
                "Phase 38 Paper 3 composition prototype must not ingest receipts that claim recursive verification or cryptographic compression".to_string(),
            ));
        }

        let segment = phase38_segment_from_phase37_receipt(index, cursor, receipt)?;
        if let Some(previous) = segments.last() {
            if segment.chain_start_boundary_commitment != previous.chain_end_boundary_commitment {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype boundary gap between segment {} end `{}` and segment {} start `{}`",
                    previous.segment_index,
                    previous.chain_end_boundary_commitment,
                    segment.segment_index,
                    segment.chain_start_boundary_commitment
                )));
            }
            if !phase38_shared_lookup_identity_matches(previous, &segment) {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype shared lookup identity drift at segment {}",
                    segment.segment_index
                )));
            }
        }
        cursor = segment.step_end;
        segments.push(segment);
    }

    let total_steps = cursor;
    let naive_per_step_package_count = total_steps;
    let composed_segment_package_count = segments.len();
    let package_count_delta = naive_per_step_package_count
        .checked_sub(composed_segment_package_count)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 38 Paper 3 composition prototype package-count baseline underflowed"
                    .to_string(),
            )
        })?;
    let shared_lookup_identity_commitment = commit_phase38_shared_lookup_identity(&segments[0])?;
    let segment_list_commitment = commit_phase38_segment_list(&segments)?;
    let mut prototype = Phase38Paper3CompositionPrototype {
        proof_backend: StarkProofBackend::Stwo,
        prototype_version: STWO_PAPER3_COMPOSITION_PROTOTYPE_VERSION_PHASE38.to_string(),
        semantic_scope: STWO_PAPER3_COMPOSITION_PROTOTYPE_SCOPE_PHASE38.to_string(),
        proof_backend_version: first.proof_backend_version.clone(),
        statement_version: first.statement_version.clone(),
        required_recursion_posture: first.required_recursion_posture.clone(),
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        segment_count: composed_segment_package_count,
        total_steps,
        chain_start_boundary_commitment: segments[0].chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: segments
            .last()
            .expect("non-empty segments")
            .chain_end_boundary_commitment
            .clone(),
        shared_lookup_identity_commitment,
        segment_list_commitment,
        naive_per_step_package_count,
        composed_segment_package_count,
        package_count_delta,
        segments,
        composition_commitment: String::new(),
    };
    prototype.composition_commitment = commit_phase38_paper3_composition_prototype(&prototype)?;
    verify_phase38_paper3_composition_prototype(&prototype)?;
    Ok(prototype)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase38_paper3_composition_prototype(
    prototype: &Phase38Paper3CompositionPrototype,
) -> Result<()> {
    if prototype.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype requires `stwo` backend, got `{}`",
            prototype.proof_backend
        )));
    }
    if prototype.prototype_version != STWO_PAPER3_COMPOSITION_PROTOTYPE_VERSION_PHASE38 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype version `{}` does not match expected `{}`",
            prototype.prototype_version, STWO_PAPER3_COMPOSITION_PROTOTYPE_VERSION_PHASE38
        )));
    }
    if prototype.semantic_scope != STWO_PAPER3_COMPOSITION_PROTOTYPE_SCOPE_PHASE38 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype scope `{}` does not match expected `{}`",
            prototype.semantic_scope, STWO_PAPER3_COMPOSITION_PROTOTYPE_SCOPE_PHASE38
        )));
    }
    if prototype.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, prototype.proof_backend_version
        )));
    }
    if prototype.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, prototype.statement_version
        )));
    }
    if prototype.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, prototype.required_recursion_posture
        )));
    }
    if prototype.recursive_verification_claimed || prototype.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype must not claim recursive verification or cryptographic compression".to_string(),
        ));
    }
    if prototype.segment_count != prototype.segments.len() || prototype.segment_count < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype segment count must match at least two segments"
                .to_string(),
        ));
    }
    if prototype.composed_segment_package_count != prototype.segment_count {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype composed package count must equal segment count"
                .to_string(),
        ));
    }
    if prototype.naive_per_step_package_count != prototype.total_steps {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype naive baseline must equal total steps"
                .to_string(),
        ));
    }
    let expected_delta = prototype
        .naive_per_step_package_count
        .checked_sub(prototype.composed_segment_package_count)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 38 Paper 3 composition prototype package-count baseline underflowed"
                    .to_string(),
            )
        })?;
    if prototype.package_count_delta != expected_delta {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype package-count delta `{}` does not match recomputed `{}`",
            prototype.package_count_delta, expected_delta
        )));
    }
    for (label, value) in [
        (
            "chain_start_boundary_commitment",
            prototype.chain_start_boundary_commitment.as_str(),
        ),
        (
            "chain_end_boundary_commitment",
            prototype.chain_end_boundary_commitment.as_str(),
        ),
        (
            "shared_lookup_identity_commitment",
            prototype.shared_lookup_identity_commitment.as_str(),
        ),
        (
            "segment_list_commitment",
            prototype.segment_list_commitment.as_str(),
        ),
        (
            "composition_commitment",
            prototype.composition_commitment.as_str(),
        ),
    ] {
        phase38_require_hash32(label, value)?;
    }

    let mut cursor = 0usize;
    let mut previous_end: Option<&str> = None;
    for (index, segment) in prototype.segments.iter().enumerate() {
        if segment.segment_index != index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment index `{}` does not match position `{}`",
                segment.segment_index, index
            )));
        }
        if segment.total_steps == 0 {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment {index} must contain at least one step"
            )));
        }
        if segment.step_start != cursor {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment {index} starts at `{}` but expected `{cursor}`",
                segment.step_start
            )));
        }
        let expected_end = cursor.checked_add(segment.total_steps).ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 38 Paper 3 composition prototype step interval overflowed usize".to_string(),
            )
        })?;
        if segment.step_end != expected_end {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment {index} ends at `{}` but expected `{expected_end}`",
                segment.step_end
            )));
        }
        if let Some(previous) = previous_end {
            if segment.chain_start_boundary_commitment != previous {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype boundary gap before segment {index}: previous end `{previous}` vs start `{}`",
                    segment.chain_start_boundary_commitment
                )));
            }
        }
        if index > 0 && !phase38_shared_lookup_identity_matches(&prototype.segments[0], segment) {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype shared lookup identity drift at segment {index}"
            )));
        }
        for (label, value) in [
            (
                "phase37_receipt_commitment",
                segment.phase37_receipt_commitment.as_str(),
            ),
            (
                "phase30_source_chain_commitment",
                segment.phase30_source_chain_commitment.as_str(),
            ),
            (
                "phase30_step_envelopes_commitment",
                segment.phase30_step_envelopes_commitment.as_str(),
            ),
            (
                "chain_start_boundary_commitment",
                segment.chain_start_boundary_commitment.as_str(),
            ),
            (
                "chain_end_boundary_commitment",
                segment.chain_end_boundary_commitment.as_str(),
            ),
            (
                "phase34_shared_lookup_public_inputs_commitment",
                segment
                    .phase34_shared_lookup_public_inputs_commitment
                    .as_str(),
            ),
            (
                "input_lookup_rows_commitments_commitment",
                segment.input_lookup_rows_commitments_commitment.as_str(),
            ),
            (
                "output_lookup_rows_commitments_commitment",
                segment.output_lookup_rows_commitments_commitment.as_str(),
            ),
            (
                "shared_lookup_artifact_commitments_commitment",
                segment
                    .shared_lookup_artifact_commitments_commitment
                    .as_str(),
            ),
            (
                "static_lookup_registry_commitments_commitment",
                segment
                    .static_lookup_registry_commitments_commitment
                    .as_str(),
            ),
        ] {
            phase38_require_hash32(label, value)?;
        }
        cursor = expected_end;
        previous_end = Some(&segment.chain_end_boundary_commitment);
    }
    if prototype.total_steps != cursor {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype total steps `{}` does not match segment sum `{cursor}`",
            prototype.total_steps
        )));
    }
    if prototype.chain_start_boundary_commitment
        != prototype.segments[0].chain_start_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype start boundary does not match first segment"
                .to_string(),
        ));
    }
    if prototype.chain_end_boundary_commitment
        != prototype
            .segments
            .last()
            .expect("non-empty segments")
            .chain_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype end boundary does not match last segment"
                .to_string(),
        ));
    }

    let expected_shared_lookup_identity =
        commit_phase38_shared_lookup_identity(&prototype.segments[0])?;
    if prototype.shared_lookup_identity_commitment != expected_shared_lookup_identity {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype shared lookup identity commitment `{}` does not match recomputed `{}`",
            prototype.shared_lookup_identity_commitment, expected_shared_lookup_identity
        )));
    }
    let expected_segment_list = commit_phase38_segment_list(&prototype.segments)?;
    if prototype.segment_list_commitment != expected_segment_list {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype segment-list commitment `{}` does not match recomputed `{}`",
            prototype.segment_list_commitment, expected_segment_list
        )));
    }
    let expected_composition = commit_phase38_paper3_composition_prototype(prototype)?;
    if prototype.composition_commitment != expected_composition {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype commitment `{}` does not match recomputed `{}`",
            prototype.composition_commitment, expected_composition
        )));
    }

    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase31_recursive_compression_decode_boundary_manifest_json(
    json: &str,
) -> Result<Phase31RecursiveCompressionDecodeBoundaryManifest> {
    if json.len() > MAX_PHASE31_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 31 recursive-compression decode-boundary manifest JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE31_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase31_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase32_recursive_compression_statement_contract_json(
    json: &str,
) -> Result<Phase32RecursiveCompressionStatementContract> {
    if json.len() > MAX_PHASE32_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 32 recursive-compression statement contract JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE32_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase32_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase33_recursive_compression_public_input_manifest_json(
    json: &str,
) -> Result<Phase33RecursiveCompressionPublicInputManifest> {
    if json.len() > MAX_PHASE33_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 33 recursive-compression public-input manifest JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE33_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase33_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase34_recursive_compression_shared_lookup_manifest_json(
    json: &str,
) -> Result<Phase34RecursiveCompressionSharedLookupManifest> {
    if json.len() > MAX_PHASE34_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 34 recursive-compression shared-lookup manifest JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE34_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase34_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase35_recursive_compression_target_manifest_json(
    json: &str,
) -> Result<Phase35RecursiveCompressionTargetManifest> {
    if json.len() > MAX_PHASE35_RECURSIVE_COMPRESSION_TARGET_MANIFEST_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 35 recursive-compression target manifest JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE35_RECURSIVE_COMPRESSION_TARGET_MANIFEST_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase35_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase36_recursive_verifier_harness_receipt_json(
    json: &str,
) -> Result<Phase36RecursiveVerifierHarnessReceipt> {
    if json.len() > MAX_PHASE36_RECURSIVE_VERIFIER_HARNESS_RECEIPT_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 36 recursive verifier harness receipt JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE36_RECURSIVE_VERIFIER_HARNESS_RECEIPT_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase36_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase37_recursive_artifact_chain_harness_receipt_json(
    json: &str,
) -> Result<Phase37RecursiveArtifactChainHarnessReceipt> {
    if json.len() > MAX_PHASE37_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 37 recursive artifact-chain harness receipt JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE37_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase37_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase31_recursive_compression_decode_boundary_manifest(
    path: &Path,
) -> Result<Phase31RecursiveCompressionDecodeBoundaryManifest> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE31_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_JSON_BYTES,
        "Phase 31 recursive-compression decode-boundary manifest",
    )?;
    serde_json::from_slice(&bytes).map_err(phase31_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase32_recursive_compression_statement_contract(
    path: &Path,
) -> Result<Phase32RecursiveCompressionStatementContract> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE32_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_JSON_BYTES,
        "Phase 32 recursive-compression statement contract",
    )?;
    serde_json::from_slice(&bytes).map_err(phase32_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase33_recursive_compression_public_input_manifest(
    path: &Path,
) -> Result<Phase33RecursiveCompressionPublicInputManifest> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE33_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_JSON_BYTES,
        "Phase 33 recursive-compression public-input manifest",
    )?;
    serde_json::from_slice(&bytes).map_err(phase33_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase34_recursive_compression_shared_lookup_manifest(
    path: &Path,
) -> Result<Phase34RecursiveCompressionSharedLookupManifest> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE34_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_JSON_BYTES,
        "Phase 34 recursive-compression shared-lookup manifest",
    )?;
    serde_json::from_slice(&bytes).map_err(phase34_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase35_recursive_compression_target_manifest(
    path: &Path,
) -> Result<Phase35RecursiveCompressionTargetManifest> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE35_RECURSIVE_COMPRESSION_TARGET_MANIFEST_JSON_BYTES,
        "Phase 35 recursive-compression target manifest",
    )?;
    serde_json::from_slice(&bytes).map_err(phase35_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase36_recursive_verifier_harness_receipt(
    path: &Path,
) -> Result<Phase36RecursiveVerifierHarnessReceipt> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE36_RECURSIVE_VERIFIER_HARNESS_RECEIPT_JSON_BYTES,
        "Phase 36 recursive verifier harness receipt",
    )?;
    serde_json::from_slice(&bytes).map_err(phase36_json_error)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase37_recursive_artifact_chain_harness_receipt(
    path: &Path,
) -> Result<Phase37RecursiveArtifactChainHarnessReceipt> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE37_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_JSON_BYTES,
        "Phase 37 recursive artifact-chain harness receipt",
    )?;
    serde_json::from_slice(&bytes).map_err(phase37_json_error)
}

#[cfg(feature = "stwo-backend")]
fn phase31_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase32_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase33_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase34_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase35_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase36_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase37_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase31_recursive_compression_decode_boundary_manifest(
    manifest: &Phase31RecursiveCompressionDecodeBoundaryManifest,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 31 decode-boundary commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase31-decode-boundary");
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, manifest.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, manifest.cryptographic_compression_claimed);
    phase29_update_len_prefixed(&mut hasher, manifest.phase29_contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase29_semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase29_contract_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase30_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase30_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, manifest.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, manifest.source_template_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.aggregation_template_commitment.as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 31 decode-boundary commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase32_recursive_compression_statement_contract(
    contract: &Phase32RecursiveCompressionStatementContract,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 32 recursive-compression statement contract commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase32-statement-contract");
    phase29_update_len_prefixed(&mut hasher, contract.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, contract.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, contract.cryptographic_compression_claimed);
    phase29_update_len_prefixed(&mut hasher, contract.phase31_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, contract.phase31_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        contract
            .phase31_decode_boundary_bridge_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        contract.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        contract.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, contract.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        contract.chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        contract.chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, contract.source_template_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        contract.aggregation_template_commitment.as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 32 recursive-compression statement contract commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase33_update_public_input_lane(
    hasher: &mut Blake2bVar,
    manifest: &Phase33RecursiveCompressionPublicInputManifest,
    lane: Phase33PublicInputLane,
) {
    match phase33_public_input_lane_payload(manifest, lane) {
        Phase33PublicInputLanePayload::Bytes(value) => {
            phase29_update_len_prefixed(hasher, value.as_bytes());
        }
        Phase33PublicInputLanePayload::Usize(value) => {
            phase29_update_usize(hasher, value);
        }
    }
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase33_recursive_compression_public_input_manifest(
    manifest: &Phase33RecursiveCompressionPublicInputManifest,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 33 recursive-compression public-input manifest commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase33-public-input-manifest");
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, manifest.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, manifest.cryptographic_compression_claimed);
    phase29_update_len_prefixed(&mut hasher, manifest.phase32_contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase32_semantic_scope.as_bytes());
    for lane in PHASE33_PUBLIC_INPUT_LANES {
        phase33_update_public_input_lane(&mut hasher, manifest, lane);
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 33 recursive-compression public-input manifest commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase34_recursive_compression_shared_lookup_manifest(
    manifest: &Phase34RecursiveCompressionSharedLookupManifest,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 34 recursive-compression shared-lookup manifest commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase34-shared-lookup-manifest");
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, manifest.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, manifest.cryptographic_compression_claimed);
    phase29_update_len_prefixed(&mut hasher, manifest.phase33_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase33_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .phase33_recursive_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, manifest.phase30_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase30_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, manifest.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.input_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .output_lookup_rows_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .shared_lookup_artifact_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .static_lookup_registry_commitments_commitment
            .as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 34 recursive-compression shared-lookup manifest commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase35_recursive_compression_target_manifest(
    manifest: &Phase35RecursiveCompressionTargetManifest,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 35 recursive-compression target manifest commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase35-recursive-target-manifest");
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, manifest.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, manifest.cryptographic_compression_claimed);
    phase29_update_len_prefixed(&mut hasher, manifest.phase32_contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase32_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .phase32_recursive_statement_contract_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, manifest.phase33_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase33_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .phase33_recursive_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, manifest.phase34_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, manifest.phase34_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .phase34_shared_lookup_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_usize(&mut hasher, manifest.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, manifest.source_template_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.aggregation_template_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest.input_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .output_lookup_rows_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .shared_lookup_artifact_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        manifest
            .static_lookup_registry_commitments_commitment
            .as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 35 recursive-compression target manifest commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase36_recursive_verifier_harness_receipt(
    receipt: &Phase36RecursiveVerifierHarnessReceipt,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 36 recursive verifier harness receipt commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase36-recursive-verifier-harness-receipt");
    phase29_update_len_prefixed(&mut hasher, receipt.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.receipt_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.verifier_harness.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, receipt.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, receipt.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, receipt.target_manifest_verified);
    phase29_update_bool(&mut hasher, receipt.source_binding_verified);
    phase29_update_len_prefixed(&mut hasher, receipt.phase35_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.phase35_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase35_recursive_target_manifest_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase32_recursive_statement_contract_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase33_recursive_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase34_shared_lookup_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_usize(&mut hasher, receipt.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.input_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.output_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .shared_lookup_artifact_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .static_lookup_registry_commitments_commitment
            .as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 36 recursive verifier harness receipt commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase37_recursive_artifact_chain_harness_receipt(
    receipt: &Phase37RecursiveArtifactChainHarnessReceipt,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 37 recursive artifact-chain harness receipt commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase37-recursive-artifact-chain-harness-receipt",
    );
    phase29_update_len_prefixed(&mut hasher, receipt.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.receipt_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.verifier_harness.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, receipt.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, receipt.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, receipt.phase29_input_contract_verified);
    phase29_update_bool(&mut hasher, receipt.phase30_step_envelope_manifest_verified);
    phase29_update_bool(&mut hasher, receipt.phase31_decode_boundary_bridge_verified);
    phase29_update_bool(&mut hasher, receipt.phase32_statement_contract_verified);
    phase29_update_bool(&mut hasher, receipt.phase33_public_inputs_verified);
    phase29_update_bool(&mut hasher, receipt.phase34_shared_lookup_verified);
    phase29_update_bool(&mut hasher, receipt.phase35_target_manifest_verified);
    phase29_update_bool(
        &mut hasher,
        receipt.phase36_verifier_harness_receipt_verified,
    );
    phase29_update_bool(&mut hasher, receipt.source_binding_verified);
    phase29_update_len_prefixed(&mut hasher, receipt.phase29_contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.phase29_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.phase29_input_contract_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, receipt.phase30_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, receipt.phase30_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.phase31_decode_boundary_bridge_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase32_recursive_statement_contract_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase33_recursive_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase34_shared_lookup_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase35_recursive_target_manifest_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .phase36_recursive_verifier_harness_receipt_commitment
            .as_bytes(),
    );
    phase29_update_usize(&mut hasher, receipt.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, receipt.source_template_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.aggregation_template_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.input_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt.output_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .shared_lookup_artifact_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        receipt
            .static_lookup_registry_commitments_commitment
            .as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 37 recursive artifact-chain harness receipt commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn commit_phase38_shared_lookup_identity(
    segment: &Phase38Paper3CompositionSegment,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 38 shared lookup identity commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase38-paper3-shared-lookup-identity");
    phase29_update_len_prefixed(
        &mut hasher,
        segment
            .phase34_shared_lookup_public_inputs_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        segment.input_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        segment.output_lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        segment
            .shared_lookup_artifact_commitments_commitment
            .as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        segment
            .static_lookup_registry_commitments_commitment
            .as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 38 shared lookup identity commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn commit_phase38_segment_list(segments: &[Phase38Paper3CompositionSegment]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 38 segment-list commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase38-paper3-composition-segment-list");
    phase29_update_usize(&mut hasher, segments.len());
    for segment in segments {
        phase29_update_usize(&mut hasher, segment.segment_index);
        phase29_update_usize(&mut hasher, segment.step_start);
        phase29_update_usize(&mut hasher, segment.step_end);
        phase29_update_usize(&mut hasher, segment.total_steps);
        phase29_update_len_prefixed(&mut hasher, segment.phase37_receipt_commitment.as_bytes());
        phase29_update_len_prefixed(
            &mut hasher,
            segment.phase30_source_chain_commitment.as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment.phase30_step_envelopes_commitment.as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment.chain_start_boundary_commitment.as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment.chain_end_boundary_commitment.as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment
                .phase34_shared_lookup_public_inputs_commitment
                .as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment.input_lookup_rows_commitments_commitment.as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment.output_lookup_rows_commitments_commitment.as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment
                .shared_lookup_artifact_commitments_commitment
                .as_bytes(),
        );
        phase29_update_len_prefixed(
            &mut hasher,
            segment
                .static_lookup_registry_commitments_commitment
                .as_bytes(),
        );
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 38 segment-list commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase38_paper3_composition_prototype(
    prototype: &Phase38Paper3CompositionPrototype,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 38 Paper 3 composition prototype commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase38-paper3-composition-prototype");
    phase29_update_len_prefixed(&mut hasher, prototype.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, prototype.prototype_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, prototype.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, prototype.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, prototype.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, prototype.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, prototype.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, prototype.cryptographic_compression_claimed);
    phase29_update_usize(&mut hasher, prototype.segment_count);
    phase29_update_usize(&mut hasher, prototype.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        prototype.chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        prototype.chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        prototype.shared_lookup_identity_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, prototype.segment_list_commitment.as_bytes());
    phase29_update_usize(&mut hasher, prototype.naive_per_step_package_count);
    phase29_update_usize(&mut hasher, prototype.composed_segment_package_count);
    phase29_update_usize(&mut hasher, prototype.package_count_delta);
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 38 Paper 3 composition prototype commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase34_commit_ordered_commitment_list<'a>(
    domain: &[u8],
    commitments: impl IntoIterator<Item = &'a str>,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 34 ordered commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, domain);
    let values = commitments.into_iter().collect::<Vec<_>>();
    phase29_update_usize(&mut hasher, values.len());
    for value in values {
        phase29_update_len_prefixed(&mut hasher, value.as_bytes());
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 34 ordered commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::assembly::parse_program;
    use crate::proof::{
        production_v1_stark_options, CLAIM_SEMANTIC_SCOPE_V1, CLAIM_STATEMENT_VERSION_V1,
    };
    use crate::state::MachineState;
    #[cfg(feature = "stwo-backend")]
    use crate::stwo_backend::{
        phase12_default_decoding_layout, phase30_prepare_decoding_step_proof_envelope_manifest,
        prove_phase12_decoding_demo_for_layout,
        STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31,
        STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31,
    };
    use crate::Attention2DMode;

    fn sample_proof(program_source: &str, program_hash: &str) -> VanillaStarkExecutionProof {
        let program = parse_program(program_source).expect("parse");
        VanillaStarkExecutionProof {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: "stwo-phase7-gemma-block-v1".to_string(),
            stwo_auxiliary: None,
            claim: crate::proof::VanillaStarkExecutionClaim {
                statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
                semantic_scope: CLAIM_SEMANTIC_SCOPE_V1.to_string(),
                program,
                attention_mode: Attention2DMode::AverageHard,
                transformer_config: None,
                steps: 3,
                final_state: MachineState::with_memory(vec![0, 0, 0, 0]),
                options: production_v1_stark_options(),
                equivalence: None,
                commitments: Some(ExecutionClaimCommitments {
                    scheme_version: "v1".to_string(),
                    hash_function: "blake2b-256".to_string(),
                    program_hash: program_hash.to_string(),
                    transformer_config_hash: "cfg".to_string(),
                    deterministic_model_hash: "model".to_string(),
                    stark_options_hash: "opts".to_string(),
                    prover_build_info: "build".to_string(),
                    prover_build_hash: "buildhash".to_string(),
                }),
            },
            proof: vec![1, 2, 3],
        }
    }

    #[test]
    fn phase6_recursion_batch_manifest_accepts_compatible_stwo_proofs() {
        let proofs = vec![
            sample_proof(".memory 4\nLOADI 1\nHALT\n", "hash-a"),
            sample_proof(".memory 4\nLOADI 2\nHALT\n", "hash-b"),
        ];
        let manifest = phase6_prepare_recursion_batch(&proofs).expect("prepare batch");
        assert_eq!(manifest.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(manifest.total_proofs, 2);
        assert_eq!(manifest.total_steps, 6);
        assert_eq!(manifest.total_proof_bytes, 6);
        assert_eq!(manifest.entries[0].commitment_program_hash, "hash-a");
        assert_eq!(manifest.entries[1].commitment_program_hash, "hash-b");
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase29_contract() -> Phase29RecursiveCompressionInputContract {
        let mut contract = Phase29RecursiveCompressionInputContract {
            proof_backend: StarkProofBackend::Stwo,
            contract_version: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29.to_string(),
            semantic_scope: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29.to_string(),
            phase28_artifact_version:
                STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28
                    .to_string(),
            phase28_semantic_scope:
                STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28
                    .to_string(),
            phase28_proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
                .to_string(),
            statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
            required_recursion_posture: STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE.to_string(),
            recursive_verification_claimed: false,
            cryptographic_compression_claimed: false,
            phase28_bounded_aggregation_arity: 2,
            phase28_member_count: 2,
            phase28_member_summaries: 2,
            phase28_nested_members: 2,
            total_phase26_members: 4,
            total_phase25_members: 8,
            max_nested_chain_arity: 2,
            max_nested_fold_arity: 2,
            total_matrices: 16,
            total_layouts: 16,
            total_rollups: 8,
            total_segments: 8,
            total_steps: 32,
            lookup_delta_entries: 12,
            max_lookup_frontier_entries: 4,
            source_template_commitment: "a".repeat(64),
            global_start_state_commitment: "phase28-start".to_string(),
            global_end_state_commitment: "phase28-end".to_string(),
            aggregation_template_commitment: "b".repeat(64),
            aggregated_chained_folded_interval_accumulator_commitment:
                "phase28-aggregate-accumulator".to_string(),
            input_contract_commitment: String::new(),
        };
        contract.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&contract)
                .expect("commit Phase 29 contract");
        contract
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase30_manifest() -> Phase30DecodingStepProofEnvelopeManifest {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout(&layout).expect("phase12 demo");
        phase30_prepare_decoding_step_proof_envelope_manifest(&chain).expect("phase30 manifest")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase31_manifest() -> Phase31RecursiveCompressionDecodeBoundaryManifest {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
            .expect("prepare phase31 manifest")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase32_contract() -> Phase32RecursiveCompressionStatementContract {
        let manifest = sample_phase31_manifest();
        phase32_prepare_recursive_compression_statement_contract(&manifest)
            .expect("prepare phase32 contract")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase33_manifest() -> Phase33RecursiveCompressionPublicInputManifest {
        let contract = sample_phase32_contract();
        phase33_prepare_recursive_compression_public_input_manifest(&contract)
            .expect("prepare phase33 manifest")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase34_manifest() -> Phase34RecursiveCompressionSharedLookupManifest {
        let phase30 = sample_phase30_manifest();
        let public_inputs = sample_phase33_manifest();
        phase34_prepare_recursive_compression_shared_lookup_manifest(&public_inputs, &phase30)
            .expect("prepare phase34 manifest")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase35_manifest() -> Phase35RecursiveCompressionTargetManifest {
        let phase32 = sample_phase32_contract();
        let phase33 = sample_phase33_manifest();
        let phase34 = sample_phase34_manifest();
        phase35_prepare_recursive_compression_target_manifest(&phase32, &phase33, &phase34)
            .expect("prepare phase35 manifest")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase36_receipt() -> Phase36RecursiveVerifierHarnessReceipt {
        let phase32 = sample_phase32_contract();
        let phase33 = sample_phase33_manifest();
        let phase34 = sample_phase34_manifest();
        let target =
            phase35_prepare_recursive_compression_target_manifest(&phase32, &phase33, &phase34)
                .expect("prepare phase35 manifest");
        phase36_prepare_recursive_verifier_harness_receipt(&target, &phase32, &phase33, &phase34)
            .expect("prepare phase36 receipt")
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase37_receipt() -> Phase37RecursiveArtifactChainHarnessReceipt {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        phase37_prepare_recursive_artifact_chain_harness_receipt(&contract, &phase30)
            .expect("prepare phase37 receipt")
    }

    #[cfg(feature = "stwo-backend")]
    fn phase38_test_hash32(hex: char) -> String {
        hex.to_string().repeat(64)
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase37_segment_receipt(
        start: &str,
        end: &str,
        total_steps: usize,
        source_chain: &str,
        step_envelopes: &str,
    ) -> Phase37RecursiveArtifactChainHarnessReceipt {
        let mut receipt = sample_phase37_receipt();
        receipt.total_steps = total_steps;
        receipt.chain_start_boundary_commitment = start.to_string();
        receipt.chain_end_boundary_commitment = end.to_string();
        receipt.phase30_source_chain_commitment = source_chain.to_string();
        receipt.phase30_step_envelopes_commitment = step_envelopes.to_string();
        receipt.recursive_artifact_chain_harness_receipt_commitment =
            commit_phase37_recursive_artifact_chain_harness_receipt(&receipt)
                .expect("recommit phase37 segment receipt");
        verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)
            .expect("verify phase37 segment receipt");
        receipt
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase38_segment_receipts() -> Vec<Phase37RecursiveArtifactChainHarnessReceipt> {
        let start = phase38_test_hash32('a');
        let mid = phase38_test_hash32('b');
        let end = phase38_test_hash32('c');
        vec![
            sample_phase37_segment_receipt(
                &start,
                &mid,
                2,
                &phase38_test_hash32('1'),
                &phase38_test_hash32('2'),
            ),
            sample_phase37_segment_receipt(
                &mid,
                &end,
                3,
                &phase38_test_hash32('3'),
                &phase38_test_hash32('4'),
            ),
        ]
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase29_contract_for_phase30(
        manifest: &Phase30DecodingStepProofEnvelopeManifest,
    ) -> Phase29RecursiveCompressionInputContract {
        let mut contract = sample_phase29_contract();
        contract.phase28_proof_backend_version = manifest.proof_backend_version.clone();
        contract.statement_version = manifest.statement_version.clone();
        contract.total_steps = manifest.total_steps;
        contract.global_start_state_commitment = manifest.chain_start_boundary_commitment.clone();
        contract.global_end_state_commitment = manifest.chain_end_boundary_commitment.clone();
        contract.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&contract)
                .expect("recommit phase29 contract");
        contract
    }

    #[cfg(feature = "stwo-backend")]
    fn empty_phase28_shell(
    ) -> Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest {
        Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest {
            proof_backend: StarkProofBackend::Stwo,
            artifact_version:
                STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28
                    .to_string(),
            semantic_scope:
                STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28
                    .to_string(),
            proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
            recursion_posture: STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE.to_string(),
            recursive_verification_claimed: false,
            cryptographic_compression_claimed: false,
            bounded_aggregation_arity: 2,
            member_count: 0,
            total_phase26_members: 0,
            total_phase25_members: 0,
            max_nested_chain_arity: 0,
            max_nested_fold_arity: 0,
            total_matrices: 0,
            total_layouts: 0,
            total_rollups: 0,
            total_segments: 0,
            total_steps: 0,
            lookup_delta_entries: 0,
            max_lookup_frontier_entries: 0,
            source_template_commitment: "phase28-source-template".to_string(),
            global_start_state_commitment: "phase28-start".to_string(),
            global_end_state_commitment: "phase28-end".to_string(),
            aggregation_template_commitment: "phase28-aggregation-template".to_string(),
            aggregated_chained_folded_interval_accumulator_commitment:
                "phase28-aggregate-accumulator".to_string(),
            member_summaries: Vec::new(),
            members: Vec::new(),
        }
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_accepts_committed_shape() {
        let contract = sample_phase29_contract();
        verify_phase29_recursive_compression_input_contract(&contract)
            .expect("verify Phase 29 contract");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_rejects_recursive_claim() {
        let mut contract = sample_phase29_contract();
        contract.recursive_verification_claimed = true;
        let err = verify_phase29_recursive_compression_input_contract(&contract)
            .expect_err("recursive claim must be rejected");
        assert!(err
            .to_string()
            .contains("must not claim recursive verification"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_rejects_compression_claim() {
        let mut contract = sample_phase29_contract();
        contract.cryptographic_compression_claimed = true;
        let err = verify_phase29_recursive_compression_input_contract(&contract)
            .expect_err("compression claim must be rejected");
        assert!(err
            .to_string()
            .contains("must not claim cryptographic compression"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_rejects_empty_commitments() {
        let mut contract = sample_phase29_contract();
        contract.source_template_commitment.clear();
        let err = verify_phase29_recursive_compression_input_contract(&contract)
            .expect_err("empty source commitment must be rejected");
        assert!(err.to_string().contains("source_template_commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_rejects_tampered_commitment() {
        let mut contract = sample_phase29_contract();
        contract.total_steps += 1;
        let err = verify_phase29_recursive_compression_input_contract(&contract)
            .expect_err("tampered contract must be rejected");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_rejects_wrong_phase28_dialect() {
        let mut contract = sample_phase29_contract();
        contract.phase28_proof_backend_version = "unsupported-stwo-dialect".to_string();
        let err = verify_phase29_recursive_compression_input_contract(&contract)
            .expect_err("wrong Phase 28 dialect must be rejected");
        assert!(err
            .to_string()
            .contains("requires Phase 28 proof backend version"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_rejects_wrong_statement_version() {
        let mut contract = sample_phase29_contract();
        contract.statement_version = "unsupported-statement".to_string();
        let err = verify_phase29_recursive_compression_input_contract(&contract)
            .expect_err("wrong statement version must be rejected");
        assert!(err.to_string().contains("requires statement version"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_deserialization_verifies_contract() {
        let contract = sample_phase29_contract();
        let json = serde_json::to_string(&contract).expect("serialize contract");
        let parsed =
            parse_phase29_recursive_compression_input_contract_json(&json).expect("parse contract");
        assert_eq!(parsed, contract);

        let mut tampered = serde_json::to_value(&contract).expect("serialize value");
        tampered["total_steps"] = serde_json::json!(contract.total_steps + 1);
        let err = serde_json::from_value::<Phase29RecursiveCompressionInputContract>(tampered)
            .expect_err("tampered deserialized contract must be rejected");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_parse_reports_validation_error_as_invalid_config(
    ) {
        let contract = sample_phase29_contract();
        let mut tampered = serde_json::to_value(&contract).expect("serialize value");
        tampered["total_steps"] = serde_json::json!(contract.total_steps + 1);
        let json = serde_json::to_string(&tampered).expect("tampered json");

        let err = parse_phase29_recursive_compression_input_contract_json(&json)
            .expect_err("validation failure must surface as invalid config");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_recursive_compression_input_contract_parse_rejects_unknown_fields() {
        let contract = sample_phase29_contract();
        let mut value = serde_json::to_value(&contract).expect("serialize value");
        value["unexpected_phase29_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase29_recursive_compression_input_contract_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_parse_recursive_compression_input_contract_reports_malformed_json_as_invalid_config()
    {
        let err = parse_phase29_recursive_compression_input_contract_json("{")
            .expect_err("malformed JSON must fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_parse_recursive_compression_input_contract_rejects_oversized_json() {
        let json = " ".repeat(MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES + 1);
        let err = parse_phase29_recursive_compression_input_contract_json(&json)
            .expect_err("oversized JSON must fail before serde parsing");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_load_recursive_compression_input_contract_reports_malformed_json_as_invalid_config()
    {
        use std::io::Write;

        let mut temp = tempfile::NamedTempFile::new().expect("create temp file");
        temp.write_all(b"{").expect("write malformed JSON");

        let err = load_phase29_recursive_compression_input_contract(temp.path())
            .expect_err("malformed Phase 29 contract should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_load_recursive_compression_input_contract_rejects_oversized_file() {
        let path = std::env::temp_dir().join(format!(
            "phase29-recursive-compression-input-contract-oversized-{}.json",
            std::process::id()
        ));
        std::fs::write(
            &path,
            vec![b'x'; MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES + 1],
        )
        .expect("write");

        let err = load_phase29_recursive_compression_input_contract(&path)
            .expect_err("oversized Phase 29 contract should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
        let _ = std::fs::remove_file(path);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_load_recursive_compression_input_contract_rejects_oversized_gzip_file() {
        use flate2::{write::GzEncoder, Compression};
        use std::io::Write;

        let path = std::env::temp_dir().join(format!(
            "phase29-recursive-compression-input-contract-oversized-{}.json.gz",
            std::process::id()
        ));
        let mut encoder = GzEncoder::new(Vec::new(), Compression::none());
        let payload = vec![b'x'; MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES];
        encoder.write_all(&payload).expect("write gzip payload");
        let bytes = encoder.finish().expect("finish gzip payload");
        assert!(
            bytes.len() > MAX_PHASE29_RECURSIVE_COMPRESSION_INPUT_CONTRACT_JSON_BYTES,
            "gzip fixture must exceed the compressed-byte budget"
        );
        std::fs::write(&path, bytes).expect("write");

        let err = load_phase29_recursive_compression_input_contract(&path)
            .expect_err("oversized compressed Phase 29 contract should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
        let _ = std::fs::remove_file(path);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_load_recursive_compression_input_contract_rejects_non_regular_file() {
        let path = std::env::temp_dir().join(format!(
            "phase29-recursive-compression-input-contract-dir-{}",
            std::process::id()
        ));
        std::fs::create_dir_all(&path).expect("create dir");

        let err = load_phase29_recursive_compression_input_contract(&path)
            .expect_err("directory path should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("is not a regular file"));
        let _ = std::fs::remove_dir_all(path);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_prepare_rejects_phase28_recursive_claim_before_contract_derivation() {
        let mut phase28 = empty_phase28_shell();
        phase28.recursive_verification_claimed = true;
        let err = phase29_prepare_recursive_compression_input_contract(&phase28)
            .expect_err("recursive Phase 28 claim must be rejected");
        assert!(err
            .to_string()
            .contains("must not claim recursive verification"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase29_prepare_rejects_phase28_synthetic_shell_without_nested_members() {
        let phase28 = empty_phase28_shell();
        let err = phase29_prepare_recursive_compression_input_contract(&phase28)
            .expect_err("empty Phase 28 shell must be rejected");
        assert!(err
            .to_string()
            .contains("must contain at least two members"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase31_decode_boundary_manifest_accepts_matching_phase29_and_phase30_sources() {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        let manifest =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
                .expect("prepare phase31 manifest");
        assert_eq!(manifest.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31
        );
        assert_eq!(
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31
        );
        assert_eq!(
            manifest.phase29_contract_commitment,
            contract.input_contract_commitment
        );
        assert_eq!(
            manifest.phase30_step_envelopes_commitment,
            phase30.step_envelopes_commitment
        );
        assert_eq!(
            manifest.chain_start_boundary_commitment,
            phase30.chain_start_boundary_commitment
        );
        assert_eq!(
            manifest.chain_end_boundary_commitment,
            phase30.chain_end_boundary_commitment
        );
        verify_phase31_recursive_compression_decode_boundary_manifest(&manifest)
            .expect("verify phase31 manifest");
        verify_phase31_recursive_compression_decode_boundary_manifest_against_sources(
            &manifest, &contract, &phase30,
        )
        .expect("verify phase31 manifest against sources");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase31_decode_boundary_manifest_rejects_step_count_mismatch() {
        let phase30 = sample_phase30_manifest();
        let mut contract = sample_phase29_contract_for_phase30(&phase30);
        contract.total_steps += 1;
        contract.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&contract)
                .expect("recommit mismatched phase29 contract");
        let err =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
                .expect_err("step-count mismatch must fail");
        assert!(err.to_string().contains("matching total_steps"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase31_decode_boundary_manifest_rejects_boundary_mismatch() {
        let phase30 = sample_phase30_manifest();
        let mut contract = sample_phase29_contract_for_phase30(&phase30);
        contract.global_start_state_commitment = "tampered-start-boundary".to_string();
        contract.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&contract)
                .expect("recommit mismatched boundary contract");
        let err =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
                .expect_err("boundary mismatch must fail");
        assert!(err.to_string().contains(
            "global_start_state_commitment to match the Phase 30 chain_start_boundary_commitment"
        ));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase31_decode_boundary_manifest_rejects_tampered_commitment() {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        let mut manifest =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
                .expect("prepare phase31 manifest");
        manifest.total_steps += 1;
        let err = verify_phase31_recursive_compression_decode_boundary_manifest(&manifest)
            .expect_err("tampered phase31 manifest must fail");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase31_decode_boundary_manifest_deserialization_verifies_manifest() {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        let manifest =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
                .expect("prepare phase31 manifest");
        let json = serde_json::to_string(&manifest).expect("serialize phase31 manifest");
        let parsed = parse_phase31_recursive_compression_decode_boundary_manifest_json(&json)
            .expect("parse phase31 manifest");
        assert_eq!(parsed, manifest);

        let mut tampered = serde_json::to_value(&manifest).expect("serialize phase31 value");
        tampered["decode_boundary_bridge_commitment"] = serde_json::json!("0".repeat(64));
        let err =
            serde_json::from_value::<Phase31RecursiveCompressionDecodeBoundaryManifest>(tampered)
                .expect_err("tampered phase31 manifest must be rejected");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase31_decode_boundary_manifest_parse_rejects_unknown_fields() {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        let manifest =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&contract, &phase30)
                .expect("prepare phase31 manifest");
        let mut value = serde_json::to_value(&manifest).expect("serialize phase31 value");
        value["unexpected_phase31_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase31_recursive_compression_decode_boundary_manifest_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase32_recursive_statement_contract_accepts_matching_phase31_source() {
        let manifest = sample_phase31_manifest();
        let contract = phase32_prepare_recursive_compression_statement_contract(&manifest)
            .expect("prepare phase32 contract");
        assert_eq!(contract.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            contract.contract_version,
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32
        );
        assert_eq!(
            contract.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32
        );
        assert_eq!(
            contract.phase31_decode_boundary_bridge_commitment,
            manifest.decode_boundary_bridge_commitment
        );
        assert_eq!(
            contract.phase30_step_envelopes_commitment,
            manifest.phase30_step_envelopes_commitment
        );
        verify_phase32_recursive_compression_statement_contract(&contract)
            .expect("verify phase32 contract");
        verify_phase32_recursive_compression_statement_contract_against_phase31(
            &contract, &manifest,
        )
        .expect("verify phase32 contract against phase31");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase32_recursive_statement_contract_rejects_tampered_commitment() {
        let manifest = sample_phase31_manifest();
        let mut contract = phase32_prepare_recursive_compression_statement_contract(&manifest)
            .expect("prepare phase32 contract");
        contract.total_steps += 1;
        let err = verify_phase32_recursive_compression_statement_contract(&contract)
            .expect_err("tampered phase32 contract must fail");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase32_recursive_statement_contract_deserialization_verifies_contract() {
        let manifest = sample_phase31_manifest();
        let contract = phase32_prepare_recursive_compression_statement_contract(&manifest)
            .expect("prepare phase32 contract");
        let json = serde_json::to_string(&contract).expect("serialize phase32 contract");
        let parsed = parse_phase32_recursive_compression_statement_contract_json(&json)
            .expect("parse phase32 contract");
        assert_eq!(parsed, contract);

        let mut tampered = serde_json::to_value(&contract).expect("serialize phase32 value");
        tampered["recursive_statement_contract_commitment"] = serde_json::json!("0".repeat(64));
        let err = serde_json::from_value::<Phase32RecursiveCompressionStatementContract>(tampered)
            .expect_err("tampered phase32 contract must be rejected");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase32_recursive_statement_contract_parse_rejects_unknown_fields() {
        let manifest = sample_phase31_manifest();
        let contract = phase32_prepare_recursive_compression_statement_contract(&manifest)
            .expect("prepare phase32 contract");
        let mut value = serde_json::to_value(&contract).expect("serialize phase32 value");
        value["unexpected_phase32_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase32_recursive_compression_statement_contract_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase33_recursive_public_input_manifest_accepts_matching_phase32_source() {
        let contract = sample_phase32_contract();
        let manifest = phase33_prepare_recursive_compression_public_input_manifest(&contract)
            .expect("prepare phase33 manifest");
        assert_eq!(manifest.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33
        );
        assert_eq!(
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33
        );
        assert_eq!(
            manifest.phase32_recursive_statement_contract_commitment,
            contract.recursive_statement_contract_commitment
        );
        verify_phase33_recursive_compression_public_input_manifest(&manifest)
            .expect("verify phase33 manifest");
        verify_phase33_recursive_compression_public_input_manifest_against_phase32(
            &manifest, &contract,
        )
        .expect("verify phase33 manifest against phase32");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase33_recursive_public_input_manifest_rejects_tampered_commitment() {
        let contract = sample_phase32_contract();
        let mut manifest = phase33_prepare_recursive_compression_public_input_manifest(&contract)
            .expect("prepare phase33 manifest");
        manifest.total_steps += 1;
        let err = verify_phase33_recursive_compression_public_input_manifest(&manifest)
            .expect_err("tampered phase33 manifest must fail");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase33_recursive_public_input_manifest_deserialization_verifies_manifest() {
        let contract = sample_phase32_contract();
        let manifest = phase33_prepare_recursive_compression_public_input_manifest(&contract)
            .expect("prepare phase33 manifest");
        let json = serde_json::to_string(&manifest).expect("serialize phase33 manifest");
        let parsed = parse_phase33_recursive_compression_public_input_manifest_json(&json)
            .expect("parse phase33 manifest");
        assert_eq!(parsed, manifest);

        let mut tampered = serde_json::to_value(&manifest).expect("serialize phase33 value");
        tampered["recursive_public_inputs_commitment"] = serde_json::json!("0".repeat(64));
        let err =
            serde_json::from_value::<Phase33RecursiveCompressionPublicInputManifest>(tampered)
                .expect_err("tampered phase33 manifest must be rejected");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase33_recursive_public_input_manifest_parse_rejects_unknown_fields() {
        let contract = sample_phase32_contract();
        let manifest = phase33_prepare_recursive_compression_public_input_manifest(&contract)
            .expect("prepare phase33 manifest");
        let mut value = serde_json::to_value(&manifest).expect("serialize phase33 value");
        value["unexpected_phase33_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase33_recursive_compression_public_input_manifest_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase34_recursive_shared_lookup_manifest_accepts_matching_phase33_and_phase30_sources() {
        let phase30 = sample_phase30_manifest();
        let public_inputs = sample_phase33_manifest();
        let manifest =
            phase34_prepare_recursive_compression_shared_lookup_manifest(&public_inputs, &phase30)
                .expect("prepare phase34 manifest");
        assert_eq!(manifest.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34
        );
        assert_eq!(
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34
        );
        assert_eq!(
            manifest.phase33_recursive_public_inputs_commitment,
            public_inputs.recursive_public_inputs_commitment
        );
        verify_phase34_recursive_compression_shared_lookup_manifest(&manifest)
            .expect("verify phase34 manifest");
        verify_phase34_recursive_compression_shared_lookup_manifest_against_sources(
            &manifest,
            &public_inputs,
            &phase30,
        )
        .expect("verify phase34 manifest against sources");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase34_recursive_shared_lookup_manifest_rejects_tampered_commitment() {
        let phase30 = sample_phase30_manifest();
        let public_inputs = sample_phase33_manifest();
        let mut manifest =
            phase34_prepare_recursive_compression_shared_lookup_manifest(&public_inputs, &phase30)
                .expect("prepare phase34 manifest");
        manifest.shared_lookup_artifact_commitments_commitment = "0".repeat(64);
        let err = verify_phase34_recursive_compression_shared_lookup_manifest(&manifest)
            .expect_err("tampered phase34 manifest must fail");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase34_recursive_shared_lookup_manifest_deserialization_verifies_manifest() {
        let phase30 = sample_phase30_manifest();
        let public_inputs = sample_phase33_manifest();
        let manifest =
            phase34_prepare_recursive_compression_shared_lookup_manifest(&public_inputs, &phase30)
                .expect("prepare phase34 manifest");
        let json = serde_json::to_string(&manifest).expect("serialize phase34 manifest");
        let parsed = parse_phase34_recursive_compression_shared_lookup_manifest_json(&json)
            .expect("parse phase34 manifest");
        assert_eq!(parsed, manifest);

        let mut tampered = serde_json::to_value(&manifest).expect("serialize phase34 value");
        tampered["shared_lookup_public_inputs_commitment"] = serde_json::json!("0".repeat(64));
        let err =
            serde_json::from_value::<Phase34RecursiveCompressionSharedLookupManifest>(tampered)
                .expect_err("tampered phase34 manifest must be rejected");
        assert!(err.to_string().contains("commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase34_recursive_shared_lookup_manifest_parse_rejects_unknown_fields() {
        let phase30 = sample_phase30_manifest();
        let public_inputs = sample_phase33_manifest();
        let manifest =
            phase34_prepare_recursive_compression_shared_lookup_manifest(&public_inputs, &phase30)
                .expect("prepare phase34 manifest");
        let mut value = serde_json::to_value(&manifest).expect("serialize phase34 value");
        value["unexpected_phase34_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase34_recursive_compression_shared_lookup_manifest_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase35_recursive_target_manifest_accepts_matching_sources() {
        let phase32 = sample_phase32_contract();
        let phase33 = sample_phase33_manifest();
        let phase34 = sample_phase34_manifest();
        let manifest =
            phase35_prepare_recursive_compression_target_manifest(&phase32, &phase33, &phase34)
                .expect("prepare phase35 manifest");
        assert_eq!(manifest.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            manifest.manifest_version,
            STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35
        );
        assert_eq!(
            manifest.semantic_scope,
            STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35
        );
        assert_eq!(
            manifest.phase32_recursive_statement_contract_commitment,
            phase32.recursive_statement_contract_commitment
        );
        assert_eq!(
            manifest.phase33_recursive_public_inputs_commitment,
            phase33.recursive_public_inputs_commitment
        );
        assert_eq!(
            manifest.phase34_shared_lookup_public_inputs_commitment,
            phase34.shared_lookup_public_inputs_commitment
        );
        verify_phase35_recursive_compression_target_manifest(&manifest)
            .expect("verify phase35 manifest");
        verify_phase35_recursive_compression_target_manifest_against_sources(
            &manifest, &phase32, &phase33, &phase34,
        )
        .expect("verify phase35 manifest against sources");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase35_recursive_target_manifest_rejects_tampered_commitment() {
        let mut manifest = sample_phase35_manifest();
        manifest.recursive_target_manifest_commitment = "00".repeat(32);
        let err = verify_phase35_recursive_compression_target_manifest(&manifest)
            .expect_err("tampered phase35 manifest must fail");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase35_recursive_target_manifest_deserialization_verifies_manifest() {
        let manifest = sample_phase35_manifest();
        let json = serde_json::to_string(&manifest).expect("serialize phase35 manifest");
        let parsed = parse_phase35_recursive_compression_target_manifest_json(&json)
            .expect("parse phase35 manifest");
        assert_eq!(parsed, manifest);

        let mut tampered = serde_json::to_value(&manifest).expect("serialize phase35 value");
        tampered["recursive_target_manifest_commitment"] = serde_json::json!("0".repeat(64));
        let err = serde_json::from_value::<Phase35RecursiveCompressionTargetManifest>(tampered)
            .expect_err("tampered phase35 manifest must be rejected");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase35_recursive_target_manifest_parse_rejects_unknown_fields() {
        let manifest = sample_phase35_manifest();
        let mut value = serde_json::to_value(&manifest).expect("serialize phase35 value");
        value["unexpected_phase35_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase35_recursive_compression_target_manifest_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_recursive_verifier_harness_receipt_accepts_matching_sources() {
        let phase32 = sample_phase32_contract();
        let phase33 = sample_phase33_manifest();
        let phase34 = sample_phase34_manifest();
        let target =
            phase35_prepare_recursive_compression_target_manifest(&phase32, &phase33, &phase34)
                .expect("prepare phase35 manifest");
        let receipt = phase36_prepare_recursive_verifier_harness_receipt(
            &target, &phase32, &phase33, &phase34,
        )
        .expect("prepare phase36 receipt");

        assert_eq!(receipt.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            receipt.receipt_version,
            STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36
        );
        assert_eq!(
            receipt.semantic_scope,
            STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36
        );
        assert_eq!(
            receipt.phase35_recursive_target_manifest_commitment,
            target.recursive_target_manifest_commitment
        );
        assert!(!receipt.recursive_verification_claimed);
        assert!(!receipt.cryptographic_compression_claimed);
        assert!(receipt.target_manifest_verified);
        assert!(receipt.source_binding_verified);
        verify_phase36_recursive_verifier_harness_receipt(&receipt)
            .expect("verify phase36 receipt");
        verify_phase36_recursive_verifier_harness_receipt_against_sources(
            &receipt, &target, &phase32, &phase33, &phase34,
        )
        .expect("verify phase36 receipt against sources");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_recursive_verifier_harness_receipt_rejects_recursive_claim() {
        let mut receipt = sample_phase36_receipt();
        receipt.recursive_verification_claimed = true;
        receipt.recursive_verifier_harness_receipt_commitment =
            commit_phase36_recursive_verifier_harness_receipt(&receipt)
                .expect("recommit phase36 receipt");
        let err = verify_phase36_recursive_verifier_harness_receipt(&receipt)
            .expect_err("recursive claim must fail");
        assert!(err
            .to_string()
            .contains("must not claim recursive verification"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_recursive_verifier_harness_receipt_rejects_tampered_commitment() {
        let mut receipt = sample_phase36_receipt();
        receipt.recursive_verifier_harness_receipt_commitment = "00".repeat(32);
        let err = verify_phase36_recursive_verifier_harness_receipt(&receipt)
            .expect_err("tampered phase36 receipt must fail");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_recursive_verifier_harness_receipt_deserialization_verifies_receipt() {
        let receipt = sample_phase36_receipt();
        let json = serde_json::to_string(&receipt).expect("serialize phase36 receipt");
        let parsed = parse_phase36_recursive_verifier_harness_receipt_json(&json)
            .expect("parse phase36 receipt");
        assert_eq!(parsed, receipt);

        let mut tampered = serde_json::to_value(&receipt).expect("serialize phase36 value");
        tampered["recursive_verifier_harness_receipt_commitment"] =
            serde_json::json!("0".repeat(64));
        let err = serde_json::from_value::<Phase36RecursiveVerifierHarnessReceipt>(tampered)
            .expect_err("tampered phase36 receipt must be rejected");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_recursive_verifier_harness_receipt_parse_rejects_unknown_fields() {
        let receipt = sample_phase36_receipt();
        let mut value = serde_json::to_value(&receipt).expect("serialize phase36 value");
        value["unexpected_phase36_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase36_recursive_verifier_harness_receipt_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_parse_recursive_verifier_harness_receipt_reports_malformed_json_as_invalid_config() {
        let err = parse_phase36_recursive_verifier_harness_receipt_json("{")
            .expect_err("malformed Phase 36 receipt JSON must fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_parse_recursive_verifier_harness_receipt_rejects_oversized_json() {
        let json = " ".repeat(MAX_PHASE36_RECURSIVE_VERIFIER_HARNESS_RECEIPT_JSON_BYTES + 1);
        let err = parse_phase36_recursive_verifier_harness_receipt_json(&json)
            .expect_err("oversized Phase 36 receipt JSON must fail before serde parsing");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_load_recursive_verifier_harness_receipt_rejects_oversized_file() {
        let path = std::env::temp_dir().join(format!(
            "phase36-recursive-verifier-harness-receipt-oversized-{}.json",
            std::process::id()
        ));
        std::fs::write(
            &path,
            vec![b'x'; MAX_PHASE36_RECURSIVE_VERIFIER_HARNESS_RECEIPT_JSON_BYTES + 1],
        )
        .expect("write oversized Phase 36 receipt");

        let err = load_phase36_recursive_verifier_harness_receipt(&path)
            .expect_err("oversized Phase 36 receipt should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
        let _ = std::fs::remove_file(path);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase36_load_recursive_verifier_harness_receipt_rejects_non_regular_file() {
        let path = std::env::temp_dir().join(format!(
            "phase36-recursive-verifier-harness-receipt-dir-{}",
            std::process::id()
        ));
        std::fs::create_dir_all(&path).expect("create Phase 36 receipt test dir");

        let err = load_phase36_recursive_verifier_harness_receipt(&path)
            .expect_err("directory path should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("is not a regular file"));
        let _ = std::fs::remove_dir_all(path);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_recursive_artifact_chain_harness_receipt_accepts_matching_sources() {
        let phase30 = sample_phase30_manifest();
        let contract = sample_phase29_contract_for_phase30(&phase30);
        let receipt = phase37_prepare_recursive_artifact_chain_harness_receipt(&contract, &phase30)
            .expect("prepare phase37 receipt");

        assert_eq!(receipt.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            receipt.receipt_version,
            STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37
        );
        assert_eq!(
            receipt.semantic_scope,
            STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37
        );
        assert_eq!(
            receipt.phase29_input_contract_commitment,
            contract.input_contract_commitment
        );
        assert_eq!(
            receipt.phase30_step_envelopes_commitment,
            phase30.step_envelopes_commitment
        );
        assert!(receipt.phase29_input_contract_verified);
        assert!(receipt.phase30_step_envelope_manifest_verified);
        assert!(receipt.phase31_decode_boundary_bridge_verified);
        assert!(receipt.phase32_statement_contract_verified);
        assert!(receipt.phase33_public_inputs_verified);
        assert!(receipt.phase34_shared_lookup_verified);
        assert!(receipt.phase35_target_manifest_verified);
        assert!(receipt.phase36_verifier_harness_receipt_verified);
        assert!(receipt.source_binding_verified);
        assert!(!receipt.recursive_verification_claimed);
        assert!(!receipt.cryptographic_compression_claimed);
        verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)
            .expect("verify phase37 receipt");
        verify_phase37_recursive_artifact_chain_harness_receipt_against_sources(
            &receipt, &contract, &phase30,
        )
        .expect("verify phase37 receipt against sources");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_recursive_artifact_chain_harness_receipt_rejects_recursive_claim() {
        let mut receipt = sample_phase37_receipt();
        receipt.recursive_verification_claimed = true;
        receipt.recursive_artifact_chain_harness_receipt_commitment =
            commit_phase37_recursive_artifact_chain_harness_receipt(&receipt)
                .expect("recommit phase37 receipt");
        let err = verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)
            .expect_err("recursive claim must fail");
        assert!(err
            .to_string()
            .contains("must not claim recursive verification"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_recursive_artifact_chain_harness_receipt_rejects_tampered_commitment() {
        let mut receipt = sample_phase37_receipt();
        receipt.recursive_artifact_chain_harness_receipt_commitment = "00".repeat(32);
        let err = verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)
            .expect_err("tampered phase37 receipt must fail");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_recursive_artifact_chain_harness_receipt_rejects_malformed_commitment_field() {
        let mut receipt = sample_phase37_receipt();
        receipt.phase35_recursive_target_manifest_commitment = "not-a-hash".to_string();
        receipt.recursive_artifact_chain_harness_receipt_commitment =
            commit_phase37_recursive_artifact_chain_harness_receipt(&receipt)
                .expect("recommit malformed phase37 receipt");

        let err = verify_phase37_recursive_artifact_chain_harness_receipt(&receipt)
            .expect_err("self-consistent malformed phase37 receipt must fail");
        assert!(err
            .to_string()
            .contains("phase35_recursive_target_manifest_commitment"));
        assert!(err.to_string().contains("32-byte lowercase hex"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_recursive_artifact_chain_harness_receipt_deserialization_verifies_receipt() {
        let receipt = sample_phase37_receipt();
        let json = serde_json::to_string(&receipt).expect("serialize phase37 receipt");
        let parsed = parse_phase37_recursive_artifact_chain_harness_receipt_json(&json)
            .expect("parse phase37 receipt");
        assert_eq!(parsed, receipt);

        let mut tampered = serde_json::to_value(&receipt).expect("serialize phase37 value");
        tampered["recursive_artifact_chain_harness_receipt_commitment"] =
            serde_json::json!("0".repeat(64));
        let err = serde_json::from_value::<Phase37RecursiveArtifactChainHarnessReceipt>(tampered)
            .expect_err("tampered phase37 receipt must be rejected");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_recursive_artifact_chain_harness_receipt_parse_rejects_unknown_fields() {
        let receipt = sample_phase37_receipt();
        let mut value = serde_json::to_value(&receipt).expect("serialize phase37 value");
        value["unexpected_phase37_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase37_recursive_artifact_chain_harness_receipt_json(&json)
            .expect_err("unknown fields must be rejected");
        assert!(matches!(err, VmError::InvalidConfig(_)));
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_accepts_contiguous_shared_lookup_segments() {
        let receipts = sample_phase38_segment_receipts();
        let prototype = phase38_prepare_paper3_composition_prototype(&receipts)
            .expect("prepare Phase 38 composition prototype");

        assert_eq!(prototype.segment_count, 2);
        assert_eq!(prototype.total_steps, 5);
        assert_eq!(prototype.naive_per_step_package_count, 5);
        assert_eq!(prototype.composed_segment_package_count, 2);
        assert_eq!(prototype.package_count_delta, 3);
        assert_eq!(prototype.segments[0].step_start, 0);
        assert_eq!(prototype.segments[0].step_end, 2);
        assert_eq!(prototype.segments[1].step_start, 2);
        assert_eq!(prototype.segments[1].step_end, 5);
        assert_eq!(
            prototype.segments[0].chain_end_boundary_commitment,
            prototype.segments[1].chain_start_boundary_commitment
        );
        assert!(!prototype.recursive_verification_claimed);
        assert!(!prototype.cryptographic_compression_claimed);
        verify_phase38_paper3_composition_prototype(&prototype)
            .expect("verify Phase 38 composition prototype");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_boundary_gap() {
        let mut receipts = sample_phase38_segment_receipts();
        receipts[1].chain_start_boundary_commitment = phase38_test_hash32('d');
        receipts[1].recursive_artifact_chain_harness_receipt_commitment =
            commit_phase37_recursive_artifact_chain_harness_receipt(&receipts[1])
                .expect("recommit boundary-gap receipt");

        let err = phase38_prepare_paper3_composition_prototype(&receipts)
            .expect_err("boundary gap must fail");
        assert!(err.to_string().contains("boundary gap"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_shared_lookup_identity_drift() {
        let mut receipts = sample_phase38_segment_receipts();
        receipts[1].phase34_shared_lookup_public_inputs_commitment = phase38_test_hash32('e');
        receipts[1].recursive_artifact_chain_harness_receipt_commitment =
            commit_phase37_recursive_artifact_chain_harness_receipt(&receipts[1])
                .expect("recommit lookup-drift receipt");

        let err = phase38_prepare_paper3_composition_prototype(&receipts)
            .expect_err("shared lookup drift must fail");
        assert!(err.to_string().contains("shared lookup identity drift"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_tampered_baseline() {
        let receipts = sample_phase38_segment_receipts();
        let mut prototype = phase38_prepare_paper3_composition_prototype(&receipts)
            .expect("prepare Phase 38 composition prototype");
        prototype.package_count_delta += 1;
        prototype.composition_commitment = commit_phase38_paper3_composition_prototype(&prototype)
            .expect("recommit tampered baseline");

        let err = verify_phase38_paper3_composition_prototype(&prototype)
            .expect_err("tampered package-count baseline must fail");
        assert!(err.to_string().contains("package-count delta"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_deserialization_verifies_prototype() {
        let receipts = sample_phase38_segment_receipts();
        let prototype = phase38_prepare_paper3_composition_prototype(&receipts)
            .expect("prepare Phase 38 composition prototype");
        let json = serde_json::to_string(&prototype).expect("serialize phase38 prototype");
        let parsed: Phase38Paper3CompositionPrototype =
            serde_json::from_str(&json).expect("parse phase38 prototype");
        assert_eq!(parsed, prototype);

        let mut tampered = serde_json::to_value(&prototype).expect("serialize phase38 value");
        tampered["composition_commitment"] = serde_json::json!("0".repeat(64));
        let err = serde_json::from_value::<Phase38Paper3CompositionPrototype>(tampered)
            .expect_err("tampered Phase 38 commitment must be rejected");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_deserialization_rejects_unknown_fields() {
        let receipts = sample_phase38_segment_receipts();
        let prototype = phase38_prepare_paper3_composition_prototype(&receipts)
            .expect("prepare Phase 38 composition prototype");
        let mut value = serde_json::to_value(&prototype).expect("serialize phase38 value");
        value["unexpected_phase38_field"] = serde_json::json!(true);

        let err = serde_json::from_value::<Phase38Paper3CompositionPrototype>(value)
            .expect_err("unknown Phase 38 fields must be rejected");
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_parse_recursive_artifact_chain_harness_receipt_reports_malformed_json_as_invalid_config(
    ) {
        let err = parse_phase37_recursive_artifact_chain_harness_receipt_json("{")
            .expect_err("malformed Phase 37 receipt JSON must fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_parse_recursive_artifact_chain_harness_receipt_rejects_oversized_json() {
        let json = " ".repeat(MAX_PHASE37_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_JSON_BYTES + 1);
        let err = parse_phase37_recursive_artifact_chain_harness_receipt_json(&json)
            .expect_err("oversized Phase 37 receipt JSON must fail before serde parsing");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_load_recursive_artifact_chain_harness_receipt_rejects_oversized_file() {
        let path = std::env::temp_dir().join(format!(
            "phase37-recursive-artifact-chain-harness-receipt-oversized-{}.json",
            std::process::id()
        ));
        std::fs::write(
            &path,
            vec![b'x'; MAX_PHASE37_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_JSON_BYTES + 1],
        )
        .expect("write oversized Phase 37 receipt");

        let err = load_phase37_recursive_artifact_chain_harness_receipt(&path)
            .expect_err("oversized Phase 37 receipt should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
        let _ = std::fs::remove_file(path);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase37_load_recursive_artifact_chain_harness_receipt_rejects_non_regular_file() {
        let path = std::env::temp_dir().join(format!(
            "phase37-recursive-artifact-chain-harness-receipt-dir-{}",
            std::process::id()
        ));
        std::fs::create_dir_all(&path).expect("create Phase 37 receipt test dir");

        let err = load_phase37_recursive_artifact_chain_harness_receipt(&path)
            .expect_err("directory path should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("is not a regular file"));
        let _ = std::fs::remove_dir_all(path);
    }
}
