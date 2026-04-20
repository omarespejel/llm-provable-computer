use serde::{Deserialize, Serialize};
#[cfg(feature = "stwo-backend")]
use std::path::Path;

use crate::error::{Result, VmError};
use crate::proof::{ExecutionClaimCommitments, StarkProofBackend, VanillaStarkExecutionProof};

#[cfg(feature = "stwo-backend")]
use super::decoding::{
    commit_phase12_public_state, commit_phase14_public_state, commit_phase23_boundary_state,
    phase14_prepare_decoding_chain, phase28_global_boundary_preimage_states,
    read_json_bytes_with_limit, verify_phase12_decoding_chain, verify_phase14_decoding_chain,
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation,
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase30_decoding_step_proof_envelope_manifest,
    verify_phase30_decoding_step_proof_envelope_manifest_against_chain,
    Phase12DecodingChainManifest, Phase12DecodingState, Phase14DecodingState,
    Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    Phase30DecodingStepProofEnvelopeManifest,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
    STWO_DECODING_STATE_VERSION_PHASE12, STWO_DECODING_STATE_VERSION_PHASE14,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
};
#[cfg(feature = "stwo-backend")]
use super::history_replay_projection_prover::{
    derive_phase43_history_replay_projection_compact_verifier_inputs,
    derive_phase44d_history_replay_projection_terminal_boundary_logup_closure,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance,
    Phase43HistoryReplayProjectionCompactProofEnvelope,
    Phase43HistoryReplayProjectionTerminalBoundaryClaim,
    Phase44DHistoryReplayProjectionExternalSourceRootAcceptance,
    Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_VERIFIER_INPUTS_VERSION_PHASE46,
    STWO_HISTORY_REPLAY_PROJECTION_EXTERNAL_SOURCE_ROOT_ACCEPTANCE_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_LOGUP_CLOSURE_VERSION_PHASE44D,
};
#[cfg(feature = "stwo-backend")]
use super::STWO_BACKEND_VERSION_PHASE12;
#[cfg(feature = "stwo-backend")]
use crate::config::TransformerVmConfig;
#[cfg(feature = "stwo-backend")]
use crate::model::{INPUT_DIM, OUTPUT_DIM};
#[cfg(feature = "stwo-backend")]
use crate::proof::CLAIM_STATEMENT_VERSION_V1;
#[cfg(feature = "stwo-backend")]
use ark_ff::Zero;
#[cfg(feature = "stwo-backend")]
use blake2::{
    digest::{Update, VariableOutput},
    Blake2bVar,
};
#[cfg(feature = "stwo-backend")]
use stwo::core::channel::Blake2sM31Channel;
#[cfg(feature = "stwo-backend")]
use stwo::core::circle::{CirclePoint, SECURE_FIELD_CIRCLE_ORDER};
#[cfg(feature = "stwo-backend")]
use stwo::core::fields::m31::BaseField;
#[cfg(feature = "stwo-backend")]
use stwo::core::fields::qm31::SecureField;
#[cfg(feature = "stwo-backend")]
use stwo::core::pcs::quotients::CommitmentSchemeProof;
#[cfg(feature = "stwo-backend")]
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig, TreeVec};
#[cfg(feature = "stwo-backend")]
use stwo::core::poly::circle::CanonicCoset;
#[cfg(feature = "stwo-backend")]
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
#[cfg(feature = "stwo-backend")]
use stwo::prover::backend::cpu::CpuBackend;
#[cfg(feature = "stwo-backend")]
use stwo::prover::backend::{Col, Column};
#[cfg(feature = "stwo-backend")]
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
#[cfg(feature = "stwo-backend")]
use stwo::prover::poly::{BitReversedOrder, NaturalOrder};
#[cfg(feature = "stwo-backend")]
use stwo::prover::CommitmentSchemeProver;

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
const PHASE31_START_BOUNDARY_MISMATCH_ERROR: &str =
    "Phase 31 decode-boundary manifest requires Phase 29 global_start_state_commitment to match the Phase 30 chain_start_boundary_commitment";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41: &str =
    "stwo-phase41-boundary-translation-witness-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41: &str =
    "stwo_execution_parameterized_boundary_translation_witness";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_TRANSLATION_RULE_PHASE41: &str =
    "explicit-phase29-phase30-boundary-pair-v1";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE41_BOUNDARY_TRANSLATION_WITNESS_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_PREIMAGE_EVIDENCE_VERSION_PHASE42: &str =
    "phase42-boundary-preimage-evidence-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_PREIMAGE_RELATION_PHASE42: &str = "hash_preimage_relation";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42: usize = 180;
#[cfg(feature = "stwo-backend")]
const MAX_PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_VERSION_PHASE42: &str =
    "phase42-boundary-history-equivalence-witness-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42: &str = "deterministic_transform";
#[cfg(feature = "stwo-backend")]
pub const STWO_BOUNDARY_HISTORY_EQUIVALENCE_RULE_PHASE42: &str =
    "phase12-chain-replay-to-phase14-chunked-history-v1";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE42_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43: &str = "phase43-history-replay-trace-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43: &str = "normalized_replay_trace";
#[cfg(feature = "stwo-backend")]
pub const STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43: &str =
    "phase12-chain-to-phase14-chunked-history-trace-v1";
#[cfg(feature = "stwo-backend")]
const MAX_PHASE43_HISTORY_REPLAY_TRACE_JSON_BYTES: usize = 8 * 1024 * 1024;
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
#[cfg(feature = "stwo-backend")]
const MAX_PHASE38_PAPER3_COMPOSITION_PROTOTYPE_JSON_BYTES: usize = 1024 * 1024;
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_VERSION_PHASE44D: &str =
    "phase44d-recursive-verifier-public-output-handoff-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_SCOPE_PHASE44D: &str =
    "phase44d_source_chain_public_output_recursive_verifier_handoff";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_VERSION_PHASE44D: &str =
    "phase44d-recursive-verifier-public-output-aggregation-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_SCOPE_PHASE44D: &str =
    "phase44d_source_chain_public_output_recursive_verifier_aggregation";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_VERSION_PHASE45: &str =
    "phase45-recursive-verifier-public-input-bridge-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_SCOPE_PHASE45: &str =
    "phase45_phase44d_source_output_ordered_recursive_public_inputs";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_VERSION_PHASE46: &str =
    "phase46-stwo-proof-adapter-receipt-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_SCOPE_PHASE46: &str =
    "phase46_phase45_public_inputs_to_stwo_verifier_inputs_adapter";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_VERSION_PHASE47: &str =
    "phase47-recursive-verifier-wrapper-candidate-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_SCOPE_PHASE47: &str =
    "phase47_phase46_stwo_receipt_recursive_wrapper_candidate";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_VERSION_PHASE48: &str =
    "phase48-recursive-proof-wrapper-attempt-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_SCOPE_PHASE48: &str =
    "phase48_phase47_actual_recursive_proof_wrapper_kill_step";
#[cfg(feature = "stwo-backend")]
pub const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_VERSION_PHASE49: &str =
    "phase49-layerwise-tensor-claim-propagation-contract-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_SCOPE_PHASE49: &str =
    "phase49_phase48_no_go_layerwise_tensor_claim_propagation_pivot";
#[cfg(feature = "stwo-backend")]
pub const STWO_TENSOR_COMMITMENT_CLAIM_VERSION_PHASE50: &str = "phase50-tensor-commitment-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_TENSOR_COMMITMENT_CLAIM_SCOPE_PHASE50: &str =
    "phase50_transformer_native_tensor_commitment_claim";
#[cfg(feature = "stwo-backend")]
pub const STWO_LAYER_IO_CLAIM_VERSION_PHASE50: &str = "phase50-layer-io-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_LAYER_IO_CLAIM_SCOPE_PHASE50: &str =
    "phase50_phase49_tensor_claim_to_first_layer_io_surface";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_RELATION_CLAIM_VERSION_PHASE51: &str =
    "phase51-first-layer-relation-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_RELATION_CLAIM_SCOPE_PHASE51: &str =
    "phase51_phase50_first_gated_feed_forward_relation_claim";
#[cfg(feature = "stwo-backend")]
pub const STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_VERSION_PHASE52: &str =
    "phase52-tensor-endpoint-evaluation-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_SCOPE_PHASE52: &str =
    "phase52_raw_tensor_public_mle_endpoint_evaluation";
#[cfg(feature = "stwo-backend")]
pub const STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_VERSION_PHASE52: &str =
    "phase52-layer-endpoint-anchoring-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_SCOPE_PHASE52: &str =
    "phase52_phase51_raw_input_output_endpoint_anchoring";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_VERSION_PHASE53: &str =
    "phase53-first-layer-relation-benchmark-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_SCOPE_PHASE53: &str =
    "phase53_phase52_stwo_ml_sumcheck_surface_benchmark";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_VERSION_PHASE54: &str =
    "phase54-first-layer-sumcheck-skeleton-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_SCOPE_PHASE54: &str =
    "phase54_phase53_typed_sumcheck_proof_skeleton";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_VERSION_PHASE55: &str =
    "phase55-first-layer-compression-effectiveness-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_SCOPE_PHASE55: &str =
    "phase55_phase54_tensor_route_surface_effectiveness_benchmark";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_VERSION_PHASE56: &str =
    "phase56-first-layer-executable-sumcheck-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_SCOPE_PHASE56: &str =
    "phase56_phase54_executable_sumcheck_round_verifier";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_VERSION_PHASE57: &str =
    "phase57-first-layer-mle-opening-verifier-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_SCOPE_PHASE57: &str =
    "phase57_phase56_mle_opening_receipt_verifier_and_bytes";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_VERSION_PHASE58: &str =
    "phase58-first-layer-witness-pcs-opening-claim-v1";
#[cfg(feature = "stwo-backend")]
pub const STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_SCOPE_PHASE58: &str =
    "phase58_phase57_witness_bound_stwo_pcs_opening_proofs";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_KIND_PHASE44D: &str =
    "source-chain-public-output-boundary-verifier-v1";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_COMPLEXITY_PHASE44D: &str = "O(boundary_width)";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_COMPLEXITY_PHASE45: &str = "O(boundary_width)";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_COMPLEXITY_PHASE46: &str =
    "O(boundary_width + stwo_proof_size)";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_COMPLEXITY_PHASE47: &str =
    "O(phase46_receipt + stwo_proof_surface)";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_DECISION_PHASE47: &str =
    "candidate_ready_for_recursive_wrapper_benchmark";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_NEXT_STEP_PHASE47: &str =
    "implement_actual_recursive_verifier_proof_or_pivot_if_full_replay_returns";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_DECISION_PHASE48: &str =
    "no_go_missing_phase43_projection_cairo_air_recursive_verifier";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_NEXT_STEP_PHASE48: &str =
    "pivot_to_layerwise_tensor_claim_propagation_or_implement_phase43_projection_cairo_air_verifier";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_COMPACT_PROOF_CHANNEL_PHASE48: &str = "Blake2sM31";
#[cfg(feature = "stwo-backend")]
const STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_RECURSIVE_CHANNEL_PHASE48: &str = "Poseidon252";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_ROUTE_SOURCE_PHASE49: &str =
    "phase48_no_go_missing_phase43_projection_cairo_air";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_ROUTE_TARGET_PHASE49: &str =
    "layerwise_tensor_claim_propagation";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_GRANULARITY_PHASE49: &str = "layerwise_tensor_io";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_PROPAGATION_RULE_PHASE49: &str =
    "input_tensor_commitment_to_output_tensor_commitment_per_layer";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_COMPOSITION_PHASE49: &str =
    "composition_accumulator_over_ordered_layer_claims";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_COMPLEXITY_PHASE49: &str = "O(layer_claim_surface)";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_DECISION_PHASE49: &str =
    "pivot_started_layerwise_tensor_claim_propagation";
#[cfg(feature = "stwo-backend")]
const STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_NEXT_STEP_PHASE49: &str =
    "define_tensor_commitment_scheme_and_first_layer_io_claim";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_COMMITMENT_SCHEME_PHASE50: &str =
    "m31_tensor_mle_commitment_root_placeholder_phase50";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_ELEMENT_FIELD_PHASE50: &str = "M31";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_MEMORY_LAYOUT_PHASE50: &str = "padded_row_major_mle_order";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_QUANTIZATION_PHASE50: &str = "m31_native_no_scale";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_PADDING_RULE_PHASE50: &str = "pad_to_next_power_of_two_for_mle";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_IO_RELATION_KIND_PHASE50: &str = "first_gated_feed_forward_layer_io_surface";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_IO_RELATION_RULE_PHASE50: &str =
    "phase50_bind_input_output_tensor_claims_pending_phase51_sumcheck";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_IO_PROPAGATION_DIRECTION_PHASE50: &str = "output_claim_back_to_input_claim";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_IO_ENDPOINT_ANCHORING_RULE_PHASE50: &str =
    "phase52_required_raw_input_output_mle_endpoint_anchoring";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_IO_COMPLEXITY_PHASE50: &str = "O(layer_io_claim_surface)";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_IO_NEXT_STEP_PHASE50: &str =
    "implement_phase51_first_gated_feed_forward_sumcheck_relation";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_KIND_PHASE51: &str = "gated_feed_forward_relation";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_RULE_PHASE51: &str =
    "gate_affine_value_affine_hadamard_output_affine";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_FIELD_PHASE51: &str = "M31";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_PARAMETER_COMMITMENT_SCHEME_PHASE51: &str =
    "phase52_required_model_weight_super_root_or_opening";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_COMPLEXITY_PHASE51: &str = "O(first_layer_relation_claim_surface)";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_NEXT_STEP_PHASE51: &str =
    "implement_phase52_endpoint_mle_anchoring_or_phase53_sumcheck_benchmark";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_ENDPOINT_CHALLENGE_DERIVATION_PHASE52: &str =
    "blake2b256_phase52_relation_commitment_role_index_to_m31_point";
#[cfg(feature = "stwo-backend")]
const STWO_TENSOR_ENDPOINT_EVALUATION_RULE_PHASE52: &str =
    "padded_univariate_indexed_multilinear_extension";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_ENDPOINT_ANCHORING_COMPLEXITY_PHASE52: &str = "O(public_endpoint_width)";
#[cfg(feature = "stwo-backend")]
const STWO_LAYER_ENDPOINT_ANCHORING_NEXT_STEP_PHASE52: &str =
    "implement_phase53_sumcheck_benchmark_for_gated_feed_forward_relation";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_BENCHMARK_STWO_ML_REFERENCE_PHASE53: &str =
    "local_stwo_ml_matmul_log_inner_dimension_sumcheck_gkr_layer_reduction";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_BENCHMARK_PARAMETER_BINDING_SCHEME_PHASE53: &str =
    "phase53_parameter_surface_commitment_placeholder_pending_weight_mle_openings";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_BENCHMARK_COMPLEXITY_PHASE53: &str =
    "O(public_endpoint_width + planned_sumcheck_rounds + constant_openings)";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_BENCHMARK_STATUS_PHASE53: &str =
    "continue_to_sumcheck_prototype_no_compression_claim_yet";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_RELATION_BENCHMARK_NEXT_STEP_PHASE53: &str =
    "implement_phase54_actual_first_layer_sumcheck_proof_and_model_weight_openings";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_SUMCHECK_SKELETON_TRANSCRIPT_PROTOCOL_PHASE54: &str =
    "stwo_ml_poseidon_sumcheck_transcript_order_skeleton";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_SUMCHECK_SKELETON_PARAMETER_OPENING_SCHEME_PHASE54: &str =
    "typed_mle_opening_receipt_placeholder_pending_actual_merkle_opening";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_SUMCHECK_SKELETON_COMPLEXITY_PHASE54: &str =
    "O(sumcheck_round_polynomials + mle_opening_receipts)";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_SUMCHECK_SKELETON_STATUS_PHASE54: &str =
    "typed_proof_skeleton_ready_pending_executable_sumcheck_verifier";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_SUMCHECK_SKELETON_NEXT_STEP_PHASE54: &str =
    "implement_phase55_surface_measurement_then_phase56_executable_sumcheck_verifier";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_MEASUREMENT_PHASE55: &str =
    "first_layer_tensor_route_surface_proxy_vs_vm_replay_proxy";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_DECISION_PHASE55: &str =
    "go_phase56_executable_sumcheck_verifier_measurement";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_NEXT_STEP_PHASE55: &str =
    "implement_phase56_executable_first_layer_sumcheck_verifier_and_measured_proof_bytes";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_TRANSCRIPT_PROTOCOL_PHASE56: &str =
    "blake2b_m31_executable_sumcheck_round_challenges_phase56";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_TERMINAL_RULE_PHASE56: &str =
    "terminal_sum_equals_final_eval_product";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_COMPLEXITY_PHASE56: &str =
    "O(sumcheck_round_polynomial_coefficients + final_evaluations)";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_STATUS_PHASE56: &str =
    "executable_round_polynomial_verifier_available_pending_mle_openings";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_NEXT_STEP_PHASE56: &str =
    "implement_phase57_mle_opening_verifier_and_measured_proof_bytes";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_SCHEME_PHASE57: &str =
    "phase57_deterministic_m31_mle_opening_receipt_verifier";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_COMPLEXITY_PHASE57: &str =
    "O(mle_opening_receipts + opening_point_dimensions)";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_STATUS_PHASE57: &str =
    "mle_opening_receipt_verifier_available_pending_pcs_opening_proofs";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_NEXT_STEP_PHASE57: &str =
    "implement_phase58_relation_witness_binding_and_real_pcs_opening_proofs";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_WITNESS_PCS_OPENING_SCHEME_PHASE58: &str =
    "phase58_raw_witness_mle_recomputation_plus_stwo_pcs_opening";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_WITNESS_PCS_OPENING_COMPLEXITY_PHASE58: &str =
    "O(raw_opening_witness_width + stwo_pcs_opening_verifier)";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_WITNESS_PCS_OPENING_STATUS_PHASE58: &str =
    "witness_bound_pcs_opening_proofs_available_pending_relation_witness_integration";
#[cfg(feature = "stwo-backend")]
const STWO_FIRST_LAYER_WITNESS_PCS_OPENING_NEXT_STEP_PHASE58: &str =
    "integrate_phase58_openings_into_full_first_layer_relation_witness_and_recursive_aggregation";
#[cfg(feature = "stwo-backend")]
const PHASE58_MAX_PCS_LIFTING_LOG_SIZE: u32 = 64;
#[cfg(feature = "stwo-backend")]
const PHASE44D_M31_MODULUS: u32 = (1u32 << 31) - 1;

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
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Phase41BoundaryTranslationWitness {
    pub proof_backend: StarkProofBackend,
    pub witness_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub derivation_proof_claimed: bool,
    pub translation_rule: String,
    pub phase29_contract_version: String,
    pub phase29_semantic_scope: String,
    pub phase29_contract_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub phase29_global_start_state_commitment: String,
    pub phase29_global_end_state_commitment: String,
    pub phase30_chain_start_boundary_commitment: String,
    pub phase30_chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub boundary_domains_differ: bool,
    pub start_boundary_translation_commitment: String,
    pub end_boundary_translation_commitment: String,
    pub boundary_translation_witness_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase41BoundaryTranslationWitnessArtifact {
    pub proof_backend: StarkProofBackend,
    pub witness_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub step_relation: String,
    pub required_recursion_posture: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub derivation_proof_claimed: bool,
    pub translation_rule: String,
    pub phase29_contract_version: String,
    pub phase29_semantic_scope: String,
    pub phase29_contract_commitment: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub phase29_global_start_state_commitment: String,
    pub phase29_global_end_state_commitment: String,
    pub phase30_chain_start_boundary_commitment: String,
    pub phase30_chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
    pub boundary_domains_differ: bool,
    pub start_boundary_translation_commitment: String,
    pub end_boundary_translation_commitment: String,
    pub boundary_translation_witness_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase42BoundaryPreimageEvidence {
    pub issue: usize,
    pub evidence_version: String,
    pub relation_outcome: String,
    pub phase12_start_state: Phase12DecodingState,
    pub phase12_end_state: Phase12DecodingState,
    pub phase14_start_state: Phase14DecodingState,
    pub phase14_end_state: Phase14DecodingState,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase42BoundaryHistoryEquivalenceWitness {
    pub issue: usize,
    pub witness_version: String,
    pub relation_outcome: String,
    pub transform_rule: String,
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub phase29_contract_commitment: String,
    pub phase28_aggregate_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub layout_commitment: String,
    pub rolling_kv_pairs: usize,
    pub pair_width: usize,
    pub phase12_start_public_state_commitment: String,
    pub phase12_end_public_state_commitment: String,
    pub phase14_start_boundary_commitment: String,
    pub phase14_end_boundary_commitment: String,
    pub phase12_start_history_commitment: String,
    pub phase12_end_history_commitment: String,
    pub phase14_start_history_commitment: String,
    pub phase14_end_history_commitment: String,
    pub initial_kv_cache_commitment: String,
    pub appended_pairs_commitment: String,
    pub appended_pair_count: usize,
    pub lookup_rows_commitments_commitment: String,
    pub lookup_rows_commitment_count: usize,
    pub full_history_replay_required: bool,
    pub cryptographic_compression_claimed: bool,
    pub witness_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayTraceRow {
    pub step_index: usize,
    pub appended_pair: Vec<i16>,
    pub input_lookup_rows_commitment: String,
    pub output_lookup_rows_commitment: String,
    pub phase30_step_envelope_commitment: String,
    pub phase12_from_state: Phase12DecodingState,
    pub phase12_to_state: Phase12DecodingState,
    pub phase14_from_state: Phase14DecodingState,
    pub phase14_to_state: Phase14DecodingState,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayTrace {
    pub issue: usize,
    pub trace_version: String,
    pub relation_outcome: String,
    pub transform_rule: String,
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub phase42_witness_commitment: String,
    pub phase29_contract_commitment: String,
    pub phase28_aggregate_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub layout_commitment: String,
    pub rolling_kv_pairs: usize,
    pub pair_width: usize,
    pub phase12_start_public_state_commitment: String,
    pub phase12_end_public_state_commitment: String,
    pub phase14_start_boundary_commitment: String,
    pub phase14_end_boundary_commitment: String,
    pub phase12_start_history_commitment: String,
    pub phase12_end_history_commitment: String,
    pub phase14_start_history_commitment: String,
    pub phase14_end_history_commitment: String,
    pub initial_kv_cache_commitment: String,
    pub appended_pairs_commitment: String,
    pub lookup_rows_commitments_commitment: String,
    pub rows: Vec<Phase43HistoryReplayTraceRow>,
    pub full_history_replay_required: bool,
    pub cryptographic_compression_claimed: bool,
    pub stwo_air_proof_claimed: bool,
    pub trace_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DRecursiveVerifierPublicOutputHandoff {
    pub proof_backend: StarkProofBackend,
    pub handoff_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub compact_claim_version: String,
    pub compact_semantic_scope: String,
    pub compact_source_binding: String,
    pub compact_envelope_commitment: String,
    pub compact_proof_size_bytes: usize,
    pub source_chain_public_output_boundary_version: String,
    pub source_surface_version: String,
    pub source_chain_public_output_boundary_commitment: String,
    pub source_emission_public_output_commitment: String,
    pub emitted_root_artifact_commitment: String,
    pub source_root_acceptance_commitment: String,
    pub emitted_canonical_source_root: String,
    pub source_root_preimage_commitment: String,
    pub compact_projection_trace_root: String,
    pub compact_preprocessed_trace_root: String,
    pub terminal_boundary_commitment: String,
    pub terminal_boundary_logup_statement_commitment: String,
    pub terminal_boundary_public_logup_sum_limbs: Vec<u32>,
    pub terminal_boundary_component_claimed_sum_limbs: Vec<u32>,
    pub terminal_boundary_logup_closure_commitment: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub public_output_boundary_verified: bool,
    pub compact_envelope_verified: bool,
    pub source_root_acceptance_verified: bool,
    pub terminal_boundary_logup_closure_verified: bool,
    pub final_useful_compression_boundary: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub verifier_requires_phase43_trace: bool,
    pub verifier_requires_phase30_manifest: bool,
    pub verifier_embeds_expected_rows: bool,
    pub verifier_side_complexity: String,
    pub handoff_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DRecursiveVerifierPublicOutputAggregation {
    pub proof_backend: StarkProofBackend,
    pub aggregation_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub handoff_count: usize,
    pub total_steps: usize,
    pub handoff_commitments: Vec<String>,
    pub source_chain_public_output_boundary_commitments: Vec<String>,
    pub compact_envelope_commitments: Vec<String>,
    pub terminal_boundary_logup_closure_commitments: Vec<String>,
    pub handoff_list_commitment: String,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub verifier_requires_phase43_trace: bool,
    pub verifier_requires_phase30_manifest: bool,
    pub verifier_embeds_expected_rows: bool,
    pub verifier_side_complexity: String,
    pub aggregation_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase45RecursiveVerifierPublicInputLane {
    pub index: usize,
    pub label: String,
    pub value_kind: String,
    pub value: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase45RecursiveVerifierPublicInputBridge {
    pub proof_backend: StarkProofBackend,
    pub bridge_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub handoff_version: String,
    pub source_chain_public_output_boundary_version: String,
    pub terminal_boundary_logup_closure_version: String,
    pub handoff_commitment: String,
    pub source_chain_public_output_boundary_commitment: String,
    pub compact_envelope_commitment: String,
    pub terminal_boundary_logup_closure_commitment: String,
    pub ordered_public_input_lanes: Vec<Phase45RecursiveVerifierPublicInputLane>,
    pub ordered_public_inputs_commitment: String,
    pub public_input_count: usize,
    pub public_output_boundary_verified: bool,
    pub compact_envelope_verified: bool,
    pub terminal_boundary_logup_closure_verified: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub verifier_requires_phase43_trace: bool,
    pub verifier_requires_phase30_manifest: bool,
    pub verifier_embeds_expected_rows: bool,
    pub verifier_side_complexity: String,
    pub bridge_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase46StwoProofAdapterReceipt {
    pub proof_backend: StarkProofBackend,
    pub receipt_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub bridge_version: String,
    pub bridge_commitment: String,
    pub ordered_public_inputs_commitment: String,
    pub public_input_count: usize,
    pub compact_envelope_commitment: String,
    pub compact_claim_version: String,
    pub compact_semantic_scope: String,
    pub compact_verifier_inputs_version: String,
    pub compact_verifier_inputs_commitment: String,
    pub compact_proof_size_bytes: usize,
    pub preprocessed_trace_root: String,
    pub projection_trace_root: String,
    pub interaction_trace_root: String,
    pub proof_commitment_roots: Vec<String>,
    pub preprocessed_trace_log_sizes: Vec<u32>,
    pub projection_trace_log_sizes: Vec<u32>,
    pub interaction_trace_log_sizes: Vec<u32>,
    pub pcs_pow_bits: u32,
    pub pcs_fri_log_blowup_factor: u32,
    pub pcs_fri_n_queries: usize,
    pub pcs_fri_log_last_layer_degree_bound: u32,
    pub pcs_fri_fold_step: u32,
    pub pcs_lifting_log_size: Option<u32>,
    pub proof_commitment_count: usize,
    pub sampled_values_tree_count: usize,
    pub decommitment_tree_count: usize,
    pub queried_values_tree_count: usize,
    pub proof_of_work: u64,
    pub terminal_boundary_interaction_claim_commitment: String,
    pub terminal_boundary_public_logup_sum_limbs: Vec<u32>,
    pub terminal_boundary_component_claimed_sum_limbs: Vec<u32>,
    pub public_plus_component_sum_is_zero: bool,
    pub phase45_bridge_verified: bool,
    pub compact_envelope_verified: bool,
    pub stwo_core_verify_succeeded: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub verifier_requires_phase43_trace: bool,
    pub verifier_requires_phase30_manifest: bool,
    pub verifier_embeds_expected_rows: bool,
    pub verifier_side_complexity: String,
    pub adapter_receipt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase47RecursiveVerifierWrapperCandidate {
    pub proof_backend: StarkProofBackend,
    pub candidate_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub adapter_receipt_version: String,
    pub adapter_receipt_commitment: String,
    pub compact_verifier_inputs_commitment: String,
    pub compact_envelope_commitment: String,
    pub bridge_commitment: String,
    pub ordered_public_inputs_commitment: String,
    pub proof_commitment_roots_commitment: String,
    pub proof_commitment_roots: Vec<String>,
    pub proof_commitment_count: usize,
    pub compact_proof_size_bytes: usize,
    pub public_input_count: usize,
    pub verifier_surface_unit_count: usize,
    pub preprocessed_trace_log_size_count: usize,
    pub projection_trace_log_size_count: usize,
    pub interaction_trace_log_size_count: usize,
    pub terminal_boundary_logup_limb_count: usize,
    pub phase46_receipt_verified: bool,
    pub stwo_core_verify_succeeded: bool,
    pub terminal_logup_closed: bool,
    pub consumes_phase46_receipt_only: bool,
    pub wrapper_requires_phase43_trace: bool,
    pub wrapper_requires_phase30_manifest: bool,
    pub wrapper_embeds_expected_rows: bool,
    pub recursive_proof_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub verifier_side_complexity: String,
    pub decision: String,
    pub required_next_step: String,
    pub candidate_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase48RecursiveProofWrapperAttempt {
    pub proof_backend: StarkProofBackend,
    pub attempt_version: String,
    pub semantic_scope: String,
    pub verifier_harness: String,
    pub phase47_candidate_version: String,
    pub phase47_candidate_commitment: String,
    pub phase46_adapter_receipt_commitment: String,
    pub compact_verifier_inputs_commitment: String,
    pub compact_envelope_commitment: String,
    pub phase47_candidate_verified: bool,
    pub local_stwo_core_verifier_detected: bool,
    pub local_stwo_cairo_verifier_core_detected: bool,
    pub local_stwo_cairo_air_verifier_detected: bool,
    pub local_phase43_projection_cairo_air_detected: bool,
    pub compact_proof_channel: String,
    pub recursive_verifier_channel: String,
    pub channel_mismatch_requires_reproving_or_adapter: bool,
    pub actual_recursive_wrapper_available: bool,
    pub recursive_proof_constructed: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub wrapper_requires_phase43_trace: bool,
    pub wrapper_requires_phase30_manifest: bool,
    pub wrapper_embeds_expected_rows: bool,
    pub blocking_reasons: Vec<String>,
    pub decision: String,
    pub required_next_step: String,
    pub attempt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase49LayerwiseTensorClaimPropagationContract {
    pub proof_backend: StarkProofBackend,
    pub contract_version: String,
    pub semantic_scope: String,
    pub source_phase48_attempt_version: String,
    pub source_phase48_attempt_commitment: String,
    pub source_phase48_decision: String,
    pub source_phase48_required_next_step: String,
    pub vm_manifest_route_blocked: bool,
    pub route_source: String,
    pub route_target: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub claim_granularity: String,
    pub propagation_rule: String,
    pub composition_strategy: String,
    pub input_tensor_width: usize,
    pub output_tensor_width: usize,
    pub attention_head_dim: usize,
    pub layer_count_bound_mode: String,
    pub tensor_commitment_scheme: String,
    pub layer_io_claim_object: String,
    pub attention_claim_object: String,
    pub mlp_claim_object: String,
    pub normalization_claim_object: String,
    pub residual_claim_object: String,
    pub composition_accumulator_object: String,
    pub target_requires_full_vm_replay: bool,
    pub target_requires_phase43_trace: bool,
    pub target_requires_phase30_manifest: bool,
    pub target_requires_phase43_projection_cairo_air: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub actual_layerwise_proof_available: bool,
    pub compression_benchmark_available: bool,
    pub required_components: Vec<String>,
    pub open_blockers: Vec<String>,
    pub verifier_side_complexity: String,
    pub decision: String,
    pub required_next_step: String,
    pub contract_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase50TensorCommitmentClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub tensor_role: String,
    pub tensor_name: String,
    pub element_field: String,
    pub memory_layout: String,
    pub quantization: String,
    pub tensor_rank: usize,
    pub tensor_shape: Vec<usize>,
    pub logical_element_count: usize,
    pub padded_element_count: usize,
    pub padding_rule: String,
    pub commitment_scheme: String,
    pub commitment_root: String,
    pub mle_evaluation_claim_status: String,
    pub raw_endpoint_anchor_required: bool,
    pub raw_endpoint_anchor_available: bool,
    pub full_vm_replay_required: bool,
    pub phase43_trace_required: bool,
    pub phase30_manifest_required: bool,
    pub transcript_order: Vec<String>,
    pub tensor_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase50LayerIoClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase49_contract_version: String,
    pub source_phase49_contract_commitment: String,
    pub source_phase49_decision: String,
    pub source_phase49_required_next_step: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub layer_index: usize,
    pub layer_name: String,
    pub layer_kind: String,
    pub input_tensor_claim: Phase50TensorCommitmentClaim,
    pub output_tensor_claim: Phase50TensorCommitmentClaim,
    pub relation_claim_kind: String,
    pub relation_rule: String,
    pub propagation_direction: String,
    pub endpoint_anchoring_rule: String,
    pub claim_surface_unit_count: usize,
    pub verifier_side_complexity: String,
    pub transcript_order: Vec<String>,
    pub requires_full_vm_replay: bool,
    pub requires_phase43_trace: bool,
    pub requires_phase30_manifest: bool,
    pub requires_phase43_projection_cairo_air: bool,
    pub raw_endpoint_anchor_available: bool,
    pub sumcheck_proof_available: bool,
    pub logup_proof_available: bool,
    pub actual_layer_relation_proof_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub required_next_step: String,
    pub layer_io_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase51FirstLayerRelationClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase50_layer_io_claim_version: String,
    pub source_phase50_layer_io_claim_commitment: String,
    pub source_phase49_contract_commitment: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub relation_kind: String,
    pub relation_rule: String,
    pub relation_field: String,
    pub layer_index: usize,
    pub input_width: usize,
    pub hidden_width: usize,
    pub output_width: usize,
    pub gate_projection_shape: Vec<usize>,
    pub value_projection_shape: Vec<usize>,
    pub hidden_product_shape: Vec<usize>,
    pub output_projection_shape: Vec<usize>,
    pub gate_bias_len: usize,
    pub value_bias_len: usize,
    pub output_bias_len: usize,
    pub operation_graph_order: Vec<String>,
    pub parameter_commitment_scheme: String,
    pub parameter_surface_unit_count: usize,
    pub activation_surface_unit_count: usize,
    pub claim_surface_unit_count: usize,
    pub vm_step_replay_required: bool,
    pub phase43_trace_required: bool,
    pub phase30_manifest_required: bool,
    pub raw_endpoint_anchor_available: bool,
    pub parameter_commitments_available: bool,
    pub affine_sumcheck_claim_available: bool,
    pub hadamard_product_claim_available: bool,
    pub actual_relation_proof_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub verifier_side_complexity: String,
    pub transcript_order: Vec<String>,
    pub required_next_step: String,
    pub relation_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase52TensorEndpointEvaluationClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase50_tensor_claim_commitment: String,
    pub source_phase51_relation_claim_commitment: String,
    pub endpoint_role: String,
    pub tensor_name: String,
    pub element_field: String,
    pub tensor_shape: Vec<usize>,
    pub logical_element_count: usize,
    pub padded_element_count: usize,
    pub raw_tensor_values: Vec<u32>,
    pub raw_tensor_commitment: String,
    pub mle_point: Vec<u32>,
    pub mle_value: u32,
    pub challenge_derivation: String,
    pub evaluation_rule: String,
    pub transcript_order: Vec<String>,
    pub verifier_derived_from_raw_tensor: bool,
    pub commitment_opening_proof_available: bool,
    pub requires_full_vm_replay: bool,
    pub requires_phase43_trace: bool,
    pub requires_phase30_manifest: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub endpoint_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase52LayerEndpointAnchoringClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase51_relation_claim_version: String,
    pub source_phase51_relation_claim_commitment: String,
    pub source_phase50_layer_io_claim_commitment: String,
    pub input_endpoint_claim: Phase52TensorEndpointEvaluationClaim,
    pub output_endpoint_claim: Phase52TensorEndpointEvaluationClaim,
    pub endpoint_count: usize,
    pub public_endpoint_width: usize,
    pub verifier_side_complexity: String,
    pub transcript_order: Vec<String>,
    pub endpoint_anchoring_available: bool,
    pub actual_layer_relation_proof_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub required_next_step: String,
    pub anchoring_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase53FirstLayerRelationBenchmarkClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase52_anchoring_claim_commitment: String,
    pub source_phase51_relation_claim_commitment: String,
    pub source_phase50_layer_io_claim_commitment: String,
    pub relation_kind: String,
    pub relation_rule: String,
    pub relation_field: String,
    pub layer_index: usize,
    pub input_width: usize,
    pub hidden_width: usize,
    pub output_width: usize,
    pub gate_matmul_shape: Vec<usize>,
    pub value_matmul_shape: Vec<usize>,
    pub output_matmul_shape: Vec<usize>,
    pub gate_matmul_inner_rounds: usize,
    pub value_matmul_inner_rounds: usize,
    pub output_matmul_inner_rounds: usize,
    pub hadamard_eq_sumcheck_rounds: usize,
    pub planned_sumcheck_round_count: usize,
    pub matmul_round_polynomial_coefficient_count: usize,
    pub hadamard_round_polynomial_coefficient_count: usize,
    pub final_evaluation_count: usize,
    pub estimated_sumcheck_surface_unit_count: usize,
    pub gate_affine_mul_terms: usize,
    pub value_affine_mul_terms: usize,
    pub output_affine_mul_terms: usize,
    pub total_affine_mul_terms: usize,
    pub bias_term_count: usize,
    pub hadamard_term_count: usize,
    pub naive_relation_arithmetic_term_count: usize,
    pub parameter_surface_unit_count: usize,
    pub activation_surface_unit_count: usize,
    pub endpoint_public_width: usize,
    pub tensor_route_claim_surface_unit_count: usize,
    pub verifier_side_complexity: String,
    pub benchmark_status: String,
    pub stwo_ml_reference: String,
    pub parameter_binding_scheme: String,
    pub parameter_binding_commitment: String,
    pub transcript_order: Vec<String>,
    pub endpoint_anchor_available: bool,
    pub parameter_opening_proof_available: bool,
    pub affine_sumcheck_proof_available: bool,
    pub hadamard_product_proof_available: bool,
    pub actual_relation_proof_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub required_next_step: String,
    pub benchmark_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase54SumcheckComponentSkeleton {
    pub proof_backend: StarkProofBackend,
    pub source_phase53_benchmark_claim_commitment: String,
    pub component_name: String,
    pub component_kind: String,
    pub relation_field: String,
    pub component_shape: Vec<usize>,
    pub inner_or_domain_width: usize,
    pub padded_inner_or_domain_width: usize,
    pub round_count: usize,
    pub round_polynomial_degree: usize,
    pub round_polynomial_coefficient_count: usize,
    pub final_evaluation_count: usize,
    pub runtime_tensor_opening_count: usize,
    pub parameter_opening_count: usize,
    pub transcript_protocol: String,
    pub round_polynomial_commitment: String,
    pub final_evaluation_commitment: String,
    pub opening_receipt_commitment: String,
    pub typed_proof_skeleton_available: bool,
    pub actual_round_polynomial_values_available: bool,
    pub actual_opening_proofs_available: bool,
    pub cryptographic_soundness_claimed: bool,
    pub component_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase54ParameterOpeningSkeleton {
    pub proof_backend: StarkProofBackend,
    pub source_phase53_benchmark_claim_commitment: String,
    pub source_phase53_parameter_binding_commitment: String,
    pub parameter_name: String,
    pub parameter_role: String,
    pub tensor_shape: Vec<usize>,
    pub logical_element_count: usize,
    pub padded_element_count: usize,
    pub opening_point_dimension: usize,
    pub opening_value_count: usize,
    pub opening_scheme: String,
    pub opening_receipt_commitment: String,
    pub opening_proof_available: bool,
    pub cryptographic_soundness_claimed: bool,
    pub parameter_opening_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase54FirstLayerSumcheckSkeletonClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase53_benchmark_claim_commitment: String,
    pub source_phase52_anchoring_claim_commitment: String,
    pub source_phase51_relation_claim_commitment: String,
    pub source_phase50_layer_io_claim_commitment: String,
    pub source_phase53_parameter_binding_commitment: String,
    pub component_claims: Vec<Phase54SumcheckComponentSkeleton>,
    pub parameter_opening_claims: Vec<Phase54ParameterOpeningSkeleton>,
    pub component_count: usize,
    pub parameter_opening_count: usize,
    pub total_round_count: usize,
    pub total_round_polynomial_coefficient_count: usize,
    pub total_final_evaluation_count: usize,
    pub total_runtime_tensor_opening_count: usize,
    pub total_parameter_opening_count: usize,
    pub total_mle_opening_claim_count: usize,
    pub typed_proof_object_surface_unit_count: usize,
    pub phase53_estimated_sumcheck_surface_unit_count: usize,
    pub endpoint_public_width: usize,
    pub verifier_side_complexity: String,
    pub skeleton_status: String,
    pub transcript_order: Vec<String>,
    pub typed_sumcheck_skeleton_available: bool,
    pub actual_sumcheck_verifier_available: bool,
    pub actual_parameter_opening_verifier_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub required_next_step: String,
    pub skeleton_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase55FirstLayerCompressionEffectivenessClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase54_skeleton_claim_commitment: String,
    pub source_phase53_benchmark_claim_commitment: String,
    pub measurement_kind: String,
    pub naive_relation_arithmetic_term_count: usize,
    pub parameter_surface_unit_count: usize,
    pub endpoint_public_width: usize,
    pub vm_replay_surface_proxy_unit_count: usize,
    pub tensor_proof_skeleton_surface_unit_count: usize,
    pub tensor_sumcheck_round_count: usize,
    pub tensor_round_polynomial_coefficient_count: usize,
    pub tensor_mle_opening_claim_count: usize,
    pub tensor_component_count: usize,
    pub tensor_parameter_opening_count: usize,
    pub tensor_to_vm_surface_proxy_basis_points: usize,
    pub surface_proxy_reduction_basis_points: usize,
    pub verifier_surface_is_smaller_than_vm_proxy: bool,
    pub positive_breakthrough_signal: bool,
    pub actual_proof_byte_benchmark_available: bool,
    pub executable_sumcheck_verifier_available: bool,
    pub breakthrough_claimed: bool,
    pub paper_ready: bool,
    pub decision: String,
    pub required_next_step: String,
    pub transcript_order: Vec<String>,
    pub effectiveness_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase56RoundPolynomial {
    pub round_index: usize,
    pub degree: usize,
    pub coefficients: Vec<u32>,
    pub polynomial_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase56ExecutableSumcheckComponentProof {
    pub proof_backend: StarkProofBackend,
    pub source_phase54_component_claim_commitment: String,
    pub component_name: String,
    pub component_kind: String,
    pub relation_field: String,
    pub round_count: usize,
    pub round_polynomial_degree: usize,
    pub claimed_sum: u32,
    pub round_polynomials: Vec<Phase56RoundPolynomial>,
    pub derived_challenges: Vec<u32>,
    pub final_evaluations: Vec<u32>,
    pub terminal_sum: u32,
    pub terminal_check_rule: String,
    pub transcript_protocol: String,
    pub executable_round_check_available: bool,
    pub mle_opening_verifier_available: bool,
    pub relation_witness_binding_available: bool,
    pub cryptographic_soundness_claimed: bool,
    pub component_proof_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase56FirstLayerExecutableSumcheckClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase54_skeleton_claim_commitment: String,
    pub source_phase53_benchmark_claim_commitment: String,
    pub component_proofs: Vec<Phase56ExecutableSumcheckComponentProof>,
    pub component_count: usize,
    pub total_round_count: usize,
    pub total_round_polynomial_count: usize,
    pub total_round_polynomial_coefficient_count: usize,
    pub total_final_evaluation_count: usize,
    pub executable_round_check_count: usize,
    pub terminal_check_count: usize,
    pub phase54_typed_proof_object_surface_unit_count: usize,
    pub executable_verifier_surface_unit_count: usize,
    pub surface_delta_from_phase54: usize,
    pub verifier_side_complexity: String,
    pub executable_status: String,
    pub transcript_order: Vec<String>,
    pub executable_sumcheck_round_verifier_available: bool,
    pub executable_mle_opening_verifier_available: bool,
    pub relation_witness_binding_available: bool,
    pub actual_proof_byte_benchmark_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub required_next_step: String,
    pub executable_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase57MleOpeningVerificationReceipt {
    pub proof_backend: StarkProofBackend,
    pub source_phase56_executable_claim_commitment: String,
    pub source_phase54_opening_claim_commitment: String,
    pub opening_name: String,
    pub opening_kind: String,
    pub opening_scheme: String,
    pub tensor_shape: Vec<usize>,
    pub logical_element_count: usize,
    pub padded_element_count: usize,
    pub opening_point_dimension: usize,
    pub opening_point: Vec<u32>,
    pub opened_value: u32,
    pub opening_root_commitment: String,
    pub opening_transcript_commitment: String,
    pub measured_payload_bytes: usize,
    pub executable_opening_check_available: bool,
    pub pcs_opening_proof_available: bool,
    pub relation_witness_binding_available: bool,
    pub cryptographic_soundness_claimed: bool,
    pub opening_receipt_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase57FirstLayerMleOpeningVerifierClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase56_executable_claim_commitment: String,
    pub source_phase54_skeleton_claim_commitment: String,
    pub opening_receipts: Vec<Phase57MleOpeningVerificationReceipt>,
    pub opening_receipt_count: usize,
    pub runtime_tensor_opening_count: usize,
    pub parameter_opening_count: usize,
    pub total_opening_point_dimension: usize,
    pub measured_opening_receipt_payload_bytes: usize,
    pub phase56_executable_verifier_surface_unit_count: usize,
    pub opening_verifier_surface_unit_count: usize,
    pub combined_verifier_surface_unit_count: usize,
    pub surface_delta_from_phase56: usize,
    pub verifier_side_complexity: String,
    pub verifier_status: String,
    pub transcript_order: Vec<String>,
    pub executable_mle_opening_verifier_available: bool,
    pub typed_opening_receipt_byte_measurement_available: bool,
    pub pcs_opening_proof_available: bool,
    pub relation_witness_binding_available: bool,
    pub actual_proof_byte_benchmark_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub breakthrough_claimed: bool,
    pub paper_ready: bool,
    pub required_next_step: String,
    pub opening_verifier_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase58WitnessBoundPcsOpening {
    pub proof_backend: StarkProofBackend,
    pub source_phase57_opening_receipt_commitment: String,
    pub source_phase56_executable_claim_commitment: String,
    pub source_phase54_opening_claim_commitment: String,
    pub opening_name: String,
    pub opening_kind: String,
    pub opening_scheme: String,
    pub tensor_shape: Vec<usize>,
    pub logical_element_count: usize,
    pub padded_element_count: usize,
    pub opening_point_dimension: usize,
    pub opening_point: Vec<u32>,
    pub opened_value: u32,
    pub raw_witness_values: Vec<u32>,
    pub raw_witness_commitment: String,
    pub adjusted_witness_index: usize,
    pub adjusted_witness_basis_weight: u32,
    pub recomputed_mle_value: u32,
    pub pcs_column_log_size: u32,
    pub pcs_lifting_log_size: u32,
    pub pcs_opening_point_index: u64,
    pub pcs_sampled_value_limbs: Vec<u32>,
    pub pcs_sampled_value_commitment: String,
    pub measured_witness_bytes: usize,
    pub opening_witness_binding_available: bool,
    pub pcs_opening_proof_available: bool,
    pub cryptographic_opening_soundness_claimed: bool,
    pub full_relation_soundness_claimed: bool,
    pub opening_proof_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase58FirstLayerWitnessPcsOpeningClaim {
    pub proof_backend: StarkProofBackend,
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_phase57_opening_verifier_claim_commitment: String,
    pub source_phase56_executable_claim_commitment: String,
    pub source_phase54_skeleton_claim_commitment: String,
    pub opening_proofs: Vec<Phase58WitnessBoundPcsOpening>,
    pub opening_proof_count: usize,
    pub runtime_tensor_opening_count: usize,
    pub parameter_opening_count: usize,
    pub total_raw_witness_element_count: usize,
    pub total_padded_witness_element_count: usize,
    pub total_opening_point_dimension: usize,
    pub max_pcs_column_log_size: u32,
    pub pcs_lifting_log_size: u32,
    pub pcs_column_log_sizes: Vec<u32>,
    pub pcs_opening_point_indices: Vec<u64>,
    pub pcs_proof: Vec<u8>,
    pub pcs_proof_commitment: String,
    pub measured_opening_witness_bytes: usize,
    pub measured_pcs_proof_bytes: usize,
    pub phase57_opening_verifier_surface_unit_count: usize,
    pub witness_binding_surface_unit_count: usize,
    pub combined_verifier_surface_unit_count: usize,
    pub surface_delta_from_phase57: usize,
    pub verifier_side_complexity: String,
    pub verifier_status: String,
    pub transcript_order: Vec<String>,
    pub executable_mle_opening_verifier_available: bool,
    pub opening_witness_binding_available: bool,
    pub pcs_opening_proof_available: bool,
    pub relation_witness_binding_available: bool,
    pub full_layer_relation_witness_available: bool,
    pub actual_proof_byte_benchmark_available: bool,
    pub recursive_verification_claimed: bool,
    pub cryptographic_compression_claimed: bool,
    pub breakthrough_claimed: bool,
    pub paper_ready: bool,
    pub required_next_step: String,
    pub witness_pcs_opening_claim_commitment: String,
}

#[cfg(feature = "stwo-backend")]
#[derive(Serialize, Deserialize)]
struct Phase58PcsOpeningProofPayload {
    proof: CommitmentSchemeProof<Blake2sM31MerkleHasher>,
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
#[serde(try_from = "Phase38Paper3CompositionSourceUnchecked")]
pub struct Phase38Paper3CompositionSource {
    pub phase29_contract: Phase29RecursiveCompressionInputContract,
    pub phase30_manifest: Phase30DecodingStepProofEnvelopeManifest,
    pub phase37_receipt: Phase37RecursiveArtifactChainHarnessReceipt,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Phase38Paper3CompositionSourceUnchecked {
    pub phase29_contract: Phase29RecursiveCompressionInputContract,
    pub phase30_manifest: Phase30DecodingStepProofEnvelopeManifest,
    pub phase37_receipt: Phase37RecursiveArtifactChainHarnessReceipt,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "Phase38Paper3CompositionSegmentUnchecked")]
pub struct Phase38Paper3CompositionSegment {
    pub segment_index: usize,
    pub step_start: usize,
    pub step_end: usize,
    pub total_steps: usize,
    pub phase29_contract: Phase29RecursiveCompressionInputContract,
    pub phase30_manifest: Phase30DecodingStepProofEnvelopeManifest,
    pub phase37_receipt: Phase37RecursiveArtifactChainHarnessReceipt,
    pub phase37_receipt_commitment: String,
    pub lookup_identity_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
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
    pub phase29_contract: Phase29RecursiveCompressionInputContract,
    pub phase30_manifest: Phase30DecodingStepProofEnvelopeManifest,
    pub phase37_receipt: Phase37RecursiveArtifactChainHarnessReceipt,
    pub phase37_receipt_commitment: String,
    pub lookup_identity_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub chain_start_boundary_commitment: String,
    pub chain_end_boundary_commitment: String,
    pub source_template_commitment: String,
    pub aggregation_template_commitment: String,
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
impl TryFrom<Phase38Paper3CompositionSourceUnchecked> for Phase38Paper3CompositionSource {
    type Error = VmError;

    fn try_from(unchecked: Phase38Paper3CompositionSourceUnchecked) -> Result<Self> {
        let source = Self {
            phase29_contract: unchecked.phase29_contract,
            phase30_manifest: unchecked.phase30_manifest,
            phase37_receipt: unchecked.phase37_receipt,
        };
        verify_phase37_recursive_artifact_chain_harness_receipt_against_sources(
            &source.phase37_receipt,
            &source.phase29_contract,
            &source.phase30_manifest,
        )?;
        Ok(source)
    }
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
            phase29_contract: unchecked.phase29_contract,
            phase30_manifest: unchecked.phase30_manifest,
            phase37_receipt: unchecked.phase37_receipt,
            phase37_receipt_commitment: unchecked.phase37_receipt_commitment,
            lookup_identity_commitment: unchecked.lookup_identity_commitment,
            phase30_source_chain_commitment: unchecked.phase30_source_chain_commitment,
            phase30_step_envelopes_commitment: unchecked.phase30_step_envelopes_commitment,
            chain_start_boundary_commitment: unchecked.chain_start_boundary_commitment,
            chain_end_boundary_commitment: unchecked.chain_end_boundary_commitment,
            source_template_commitment: unchecked.source_template_commitment,
            aggregation_template_commitment: unchecked.aggregation_template_commitment,
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
                "lookup_identity_commitment",
                segment.lookup_identity_commitment.as_str(),
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
                "source_template_commitment",
                segment.source_template_commitment.as_str(),
            ),
            (
                "aggregation_template_commitment",
                segment.aggregation_template_commitment.as_str(),
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
        if segment.total_steps == 0 {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment {} must contain at least one step",
                segment.segment_index
            )));
        }
        let span = segment
            .step_end
            .checked_sub(segment.step_start)
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype segment {} step interval is reversed",
                    segment.segment_index
                ))
            })?;
        if span != segment.total_steps {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment {} spans `{span}` steps but declares `{}`",
                segment.segment_index, segment.total_steps
            )));
        }
        let expected_end = segment
            .step_start
            .checked_add(segment.total_steps)
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype segment {} step interval overflowed usize",
                    segment.segment_index
                ))
            })?;
        if segment.step_end != expected_end {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype segment {} ends at `{}` but expected `{expected_end}`",
                segment.segment_index, segment.step_end
            )));
        }
        phase38_verify_segment_receipt_binding(&segment)?;
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
fn phase41_witness_from_artifact(
    artifact: Phase41BoundaryTranslationWitnessArtifact,
) -> Result<Phase41BoundaryTranslationWitness> {
    let witness = Phase41BoundaryTranslationWitness {
        proof_backend: artifact.proof_backend,
        witness_version: artifact.witness_version,
        semantic_scope: artifact.semantic_scope,
        proof_backend_version: artifact.proof_backend_version,
        statement_version: artifact.statement_version,
        step_relation: artifact.step_relation,
        required_recursion_posture: artifact.required_recursion_posture,
        recursive_verification_claimed: artifact.recursive_verification_claimed,
        cryptographic_compression_claimed: artifact.cryptographic_compression_claimed,
        derivation_proof_claimed: artifact.derivation_proof_claimed,
        translation_rule: artifact.translation_rule,
        phase29_contract_version: artifact.phase29_contract_version,
        phase29_semantic_scope: artifact.phase29_semantic_scope,
        phase29_contract_commitment: artifact.phase29_contract_commitment,
        phase30_manifest_version: artifact.phase30_manifest_version,
        phase30_semantic_scope: artifact.phase30_semantic_scope,
        phase30_source_chain_commitment: artifact.phase30_source_chain_commitment,
        phase30_step_envelopes_commitment: artifact.phase30_step_envelopes_commitment,
        total_steps: artifact.total_steps,
        phase29_global_start_state_commitment: artifact.phase29_global_start_state_commitment,
        phase29_global_end_state_commitment: artifact.phase29_global_end_state_commitment,
        phase30_chain_start_boundary_commitment: artifact.phase30_chain_start_boundary_commitment,
        phase30_chain_end_boundary_commitment: artifact.phase30_chain_end_boundary_commitment,
        source_template_commitment: artifact.source_template_commitment,
        aggregation_template_commitment: artifact.aggregation_template_commitment,
        boundary_domains_differ: artifact.boundary_domains_differ,
        start_boundary_translation_commitment: artifact.start_boundary_translation_commitment,
        end_boundary_translation_commitment: artifact.end_boundary_translation_commitment,
        boundary_translation_witness_commitment: artifact.boundary_translation_witness_commitment,
    };
    verify_phase41_boundary_translation_witness(&witness)?;
    Ok(witness)
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
            PHASE31_START_BOUNDARY_MISMATCH_ERROR.to_string(),
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
fn phase41_require_hash32(label: &str, value: &str) -> Result<()> {
    if !phase37_is_hash32_lower_hex(value) {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn commit_phase41_boundary_translation_pair(
    boundary_label: &str,
    phase29_boundary_commitment: &str,
    phase30_boundary_commitment: &str,
    witness: &Phase41BoundaryTranslationWitness,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 41 boundary-pair commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase41-boundary-translation-pair");
    phase29_update_len_prefixed(&mut hasher, boundary_label.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.translation_rule.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase29_contract_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, witness.total_steps);
    phase29_update_len_prefixed(&mut hasher, phase29_boundary_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, phase30_boundary_commitment.as_bytes());
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 41 boundary-pair commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase41_boundary_translation_witness(
    witness: &Phase41BoundaryTranslationWitness,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 41 boundary-translation witness commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase41-boundary-translation-witness");
    phase29_update_len_prefixed(&mut hasher, witness.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.witness_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.step_relation.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.required_recursion_posture.as_bytes());
    phase29_update_bool(&mut hasher, witness.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, witness.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, witness.derivation_proof_claimed);
    phase29_update_len_prefixed(&mut hasher, witness.translation_rule.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase29_contract_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase29_semantic_scope.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase29_contract_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase30_manifest_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase30_semantic_scope.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, witness.total_steps);
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase29_global_start_state_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase29_global_end_state_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_chain_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_chain_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, witness.source_template_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        witness.aggregation_template_commitment.as_bytes(),
    );
    phase29_update_bool(&mut hasher, witness.boundary_domains_differ);
    phase29_update_len_prefixed(
        &mut hasher,
        witness.start_boundary_translation_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.end_boundary_translation_commitment.as_bytes(),
    );
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 41 boundary-translation witness commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn phase41_prepare_boundary_translation_witness(
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase41BoundaryTranslationWitness> {
    verify_phase29_recursive_compression_input_contract(contract)?;
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;
    if contract.phase28_proof_backend_version != phase30.proof_backend_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires matching proof backend version between Phase 29 (`{}`) and Phase 30 (`{}`)",
            contract.phase28_proof_backend_version, phase30.proof_backend_version
        )));
    }
    if contract.statement_version != phase30.statement_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires matching statement version between Phase 29 (`{}`) and Phase 30 (`{}`)",
            contract.statement_version, phase30.statement_version
        )));
    }
    if contract.total_steps != phase30.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires matching total_steps between Phase 29 ({}) and Phase 30 ({})",
            contract.total_steps, phase30.total_steps
        )));
    }
    if contract.global_start_state_commitment == phase30.chain_start_boundary_commitment
        && contract.global_end_state_commitment == phase30.chain_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness requires at least one differing Phase29/Phase30 boundary; use Phase31 direct binding when both boundaries already match".to_string(),
        ));
    }

    let mut witness = Phase41BoundaryTranslationWitness {
        proof_backend: StarkProofBackend::Stwo,
        witness_version: STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41.to_string(),
        semantic_scope: STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41.to_string(),
        proof_backend_version: contract.phase28_proof_backend_version.clone(),
        statement_version: contract.statement_version.clone(),
        step_relation: STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30.to_string(),
        required_recursion_posture: contract.required_recursion_posture.clone(),
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        derivation_proof_claimed: false,
        translation_rule: STWO_BOUNDARY_TRANSLATION_RULE_PHASE41.to_string(),
        phase29_contract_version: contract.contract_version.clone(),
        phase29_semantic_scope: contract.semantic_scope.clone(),
        phase29_contract_commitment: contract.input_contract_commitment.clone(),
        phase30_manifest_version: phase30.manifest_version.clone(),
        phase30_semantic_scope: phase30.semantic_scope.clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        total_steps: phase30.total_steps,
        phase29_global_start_state_commitment: contract.global_start_state_commitment.clone(),
        phase29_global_end_state_commitment: contract.global_end_state_commitment.clone(),
        phase30_chain_start_boundary_commitment: phase30.chain_start_boundary_commitment.clone(),
        phase30_chain_end_boundary_commitment: phase30.chain_end_boundary_commitment.clone(),
        source_template_commitment: contract.source_template_commitment.clone(),
        aggregation_template_commitment: contract.aggregation_template_commitment.clone(),
        boundary_domains_differ: true,
        start_boundary_translation_commitment: String::new(),
        end_boundary_translation_commitment: String::new(),
        boundary_translation_witness_commitment: String::new(),
    };
    witness.start_boundary_translation_commitment = commit_phase41_boundary_translation_pair(
        "start",
        &witness.phase29_global_start_state_commitment,
        &witness.phase30_chain_start_boundary_commitment,
        &witness,
    )?;
    witness.end_boundary_translation_commitment = commit_phase41_boundary_translation_pair(
        "end",
        &witness.phase29_global_end_state_commitment,
        &witness.phase30_chain_end_boundary_commitment,
        &witness,
    )?;
    witness.boundary_translation_witness_commitment =
        commit_phase41_boundary_translation_witness(&witness)?;
    verify_phase41_boundary_translation_witness(&witness)?;
    Ok(witness)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase41_boundary_translation_witness(
    witness: &Phase41BoundaryTranslationWitness,
) -> Result<()> {
    if witness.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires `stwo` backend, got `{}`",
            witness.proof_backend
        )));
    }
    if witness.witness_version != STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness version `{}` does not match expected `{}`",
            witness.witness_version, STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41
        )));
    }
    if witness.semantic_scope != STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness scope `{}` does not match expected `{}`",
            witness.semantic_scope, STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41
        )));
    }
    if witness.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, witness.proof_backend_version
        )));
    }
    if witness.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, witness.statement_version
        )));
    }
    if witness.step_relation != STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires step relation `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, witness.step_relation
        )));
    }
    if witness.required_recursion_posture != STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires recursion posture `{}`, got `{}`",
            STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE, witness.required_recursion_posture
        )));
    }
    if witness.recursive_verification_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness must not claim recursive verification"
                .to_string(),
        ));
    }
    if witness.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness must not claim cryptographic compression"
                .to_string(),
        ));
    }
    if witness.derivation_proof_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness must not claim proof-level derivation"
                .to_string(),
        ));
    }
    if witness.translation_rule != STWO_BOUNDARY_TRANSLATION_RULE_PHASE41 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness rule `{}` does not match expected `{}`",
            witness.translation_rule, STWO_BOUNDARY_TRANSLATION_RULE_PHASE41
        )));
    }
    if witness.phase29_contract_version != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires Phase 29 contract version `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
            witness.phase29_contract_version
        )));
    }
    if witness.phase29_semantic_scope != STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires Phase 29 semantic scope `{}`, got `{}`",
            STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29, witness.phase29_semantic_scope
        )));
    }
    if witness.phase30_manifest_version != STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires Phase 30 manifest version `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30, witness.phase30_manifest_version
        )));
    }
    if witness.phase30_semantic_scope != STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness requires Phase 30 semantic scope `{}`, got `{}`",
            STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30, witness.phase30_semantic_scope
        )));
    }
    if witness.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness requires at least one decode step".to_string(),
        ));
    }
    if !witness.boundary_domains_differ {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness requires boundary_domains_differ=true"
                .to_string(),
        ));
    }
    if witness.phase29_global_start_state_commitment
        == witness.phase30_chain_start_boundary_commitment
        && witness.phase29_global_end_state_commitment
            == witness.phase30_chain_end_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness must bind at least one differing Phase29 and Phase30 boundary".to_string(),
        ));
    }

    for (label, value) in [
        (
            "phase29_contract_commitment",
            witness.phase29_contract_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            witness.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            witness.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "phase29_global_start_state_commitment",
            witness.phase29_global_start_state_commitment.as_str(),
        ),
        (
            "phase29_global_end_state_commitment",
            witness.phase29_global_end_state_commitment.as_str(),
        ),
        (
            "phase30_chain_start_boundary_commitment",
            witness.phase30_chain_start_boundary_commitment.as_str(),
        ),
        (
            "phase30_chain_end_boundary_commitment",
            witness.phase30_chain_end_boundary_commitment.as_str(),
        ),
        (
            "source_template_commitment",
            witness.source_template_commitment.as_str(),
        ),
        (
            "aggregation_template_commitment",
            witness.aggregation_template_commitment.as_str(),
        ),
        (
            "start_boundary_translation_commitment",
            witness.start_boundary_translation_commitment.as_str(),
        ),
        (
            "end_boundary_translation_commitment",
            witness.end_boundary_translation_commitment.as_str(),
        ),
        (
            "boundary_translation_witness_commitment",
            witness.boundary_translation_witness_commitment.as_str(),
        ),
    ] {
        phase41_require_hash32(label, value)?;
    }

    let expected_start = commit_phase41_boundary_translation_pair(
        "start",
        &witness.phase29_global_start_state_commitment,
        &witness.phase30_chain_start_boundary_commitment,
        witness,
    )?;
    if witness.start_boundary_translation_commitment != expected_start {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 start-boundary translation commitment `{}` does not match recomputed `{}`",
            witness.start_boundary_translation_commitment, expected_start
        )));
    }
    let expected_end = commit_phase41_boundary_translation_pair(
        "end",
        &witness.phase29_global_end_state_commitment,
        &witness.phase30_chain_end_boundary_commitment,
        witness,
    )?;
    if witness.end_boundary_translation_commitment != expected_end {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 end-boundary translation commitment `{}` does not match recomputed `{}`",
            witness.end_boundary_translation_commitment, expected_end
        )));
    }
    let expected = commit_phase41_boundary_translation_witness(witness)?;
    if witness.boundary_translation_witness_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness commitment `{}` does not match recomputed `{}`",
            witness.boundary_translation_witness_commitment, expected
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase41_boundary_translation_witness_against_sources(
    witness: &Phase41BoundaryTranslationWitness,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase41_boundary_translation_witness(witness)?;
    let expected = phase41_prepare_boundary_translation_witness(contract, phase30)?;
    if witness != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 41 boundary-translation witness does not match the recomputed Phase 29 + Phase 30 source artifacts".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn phase42_prepare_boundary_preimage_evidence(
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase42BoundaryPreimageEvidence> {
    phase42_verify_source_stack(chain, phase28, contract, phase30)?;
    let first_step = chain.steps.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence requires a Phase 12 chain with at least one step"
                .to_string(),
        )
    })?;
    let last_step = chain
        .steps
        .last()
        .expect("checked non-empty Phase 12 chain");
    let (phase14_start_state, phase14_end_state) =
        phase28_global_boundary_preimage_states(phase28)?;

    let evidence = Phase42BoundaryPreimageEvidence {
        issue: STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
        evidence_version: STWO_BOUNDARY_PREIMAGE_EVIDENCE_VERSION_PHASE42.to_string(),
        relation_outcome: STWO_BOUNDARY_PREIMAGE_RELATION_PHASE42.to_string(),
        phase12_start_state: first_step.from_state.clone(),
        phase12_end_state: last_step.to_state.clone(),
        phase14_start_state,
        phase14_end_state,
    };
    verify_phase42_boundary_preimage_evidence_against_sources(
        &evidence, chain, phase28, contract, phase30,
    )?;
    Ok(evidence)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase42_boundary_preimage_evidence(
    evidence: &Phase42BoundaryPreimageEvidence,
) -> Result<()> {
    if evidence.issue != STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence must reference Issue #{}, got #{}",
            STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42, evidence.issue
        )));
    }
    if evidence.evidence_version != STWO_BOUNDARY_PREIMAGE_EVIDENCE_VERSION_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence version `{}` does not match expected `{}`",
            evidence.evidence_version, STWO_BOUNDARY_PREIMAGE_EVIDENCE_VERSION_PHASE42
        )));
    }
    if evidence.relation_outcome != STWO_BOUNDARY_PREIMAGE_RELATION_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence relation `{}` does not match expected `{}`",
            evidence.relation_outcome, STWO_BOUNDARY_PREIMAGE_RELATION_PHASE42
        )));
    }

    phase42_verify_phase12_state("phase12_start_state", &evidence.phase12_start_state)?;
    phase42_verify_phase12_state("phase12_end_state", &evidence.phase12_end_state)?;
    phase42_verify_phase14_state("phase14_start_state", &evidence.phase14_start_state)?;
    phase42_verify_phase14_state("phase14_end_state", &evidence.phase14_end_state)?;
    phase42_shared_core_matches(
        "start",
        &evidence.phase12_start_state,
        &evidence.phase14_start_state,
    )?;
    phase42_shared_core_matches(
        "end",
        &evidence.phase12_end_state,
        &evidence.phase14_end_state,
    )?;
    if evidence.phase12_start_state.step_index != 0 || evidence.phase14_start_state.step_index != 0
    {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence start states must have step_index=0".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase42_boundary_preimage_evidence_against_sources(
    evidence: &Phase42BoundaryPreimageEvidence,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase42_boundary_preimage_evidence(evidence)?;
    phase42_verify_source_stack(chain, phase28, contract, phase30)?;

    let first_step = chain.steps.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence source binding requires a non-empty Phase 12 chain"
                .to_string(),
        )
    })?;
    let last_step = chain
        .steps
        .last()
        .expect("checked non-empty Phase 12 chain");
    if evidence.phase12_start_state != first_step.from_state {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence phase12_start_state does not match the Phase 12 chain start state"
                .to_string(),
        ));
    }
    if evidence.phase12_end_state != last_step.to_state {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence phase12_end_state does not match the Phase 12 chain end state"
                .to_string(),
        ));
    }

    let (phase14_start_state, phase14_end_state) =
        phase28_global_boundary_preimage_states(phase28)?;
    if evidence.phase14_start_state != phase14_start_state {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence phase14_start_state does not match the Phase 28 global start preimage"
                .to_string(),
        ));
    }
    if evidence.phase14_end_state != phase14_end_state {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence phase14_end_state does not match the Phase 28 global end preimage"
                .to_string(),
        ));
    }

    if evidence.phase12_start_state.public_state_commitment
        != phase30.chain_start_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence Phase12 start preimage does not bind the Phase 30 start boundary"
                .to_string(),
        ));
    }
    if evidence.phase12_end_state.public_state_commitment != phase30.chain_end_boundary_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence Phase12 end preimage does not bind the Phase 30 end boundary"
                .to_string(),
        ));
    }
    let phase14_start_boundary = commit_phase23_boundary_state(&evidence.phase14_start_state);
    let phase14_end_boundary = commit_phase23_boundary_state(&evidence.phase14_end_state);
    if phase14_start_boundary != phase28.global_start_state_commitment
        || phase14_start_boundary != contract.global_start_state_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence Phase14 start preimage does not bind the Phase 28/29 start boundary"
                .to_string(),
        ));
    }
    if phase14_end_boundary != phase28.global_end_state_commitment
        || phase14_end_boundary != contract.global_end_state_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence Phase14 end preimage does not bind the Phase 28/29 end boundary"
                .to_string(),
        ));
    }
    if evidence.phase12_end_state.step_index != phase30.total_steps
        || evidence.phase14_end_state.step_index != phase30.total_steps
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence end step_index must equal total_steps {}",
            phase30.total_steps
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase42_boundary_history_equivalence_witness(
    witness: &Phase42BoundaryHistoryEquivalenceWitness,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 42 history-equivalence witness commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase42-boundary-history-equivalence-witness");
    phase29_update_usize(&mut hasher, witness.issue);
    phase29_update_len_prefixed(&mut hasher, witness.witness_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.relation_outcome.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.transform_rule.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.proof_backend.to_string().as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase29_contract_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.phase28_aggregate_commitment.as_bytes());
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_source_chain_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase30_step_envelopes_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, witness.total_steps);
    phase29_update_len_prefixed(&mut hasher, witness.layout_commitment.as_bytes());
    phase29_update_usize(&mut hasher, witness.rolling_kv_pairs);
    phase29_update_usize(&mut hasher, witness.pair_width);
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase12_start_public_state_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase12_end_public_state_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase14_start_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase14_end_boundary_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase12_start_history_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase12_end_history_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase14_start_history_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        witness.phase14_end_history_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(&mut hasher, witness.initial_kv_cache_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, witness.appended_pairs_commitment.as_bytes());
    phase29_update_usize(&mut hasher, witness.appended_pair_count);
    phase29_update_len_prefixed(
        &mut hasher,
        witness.lookup_rows_commitments_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, witness.lookup_rows_commitment_count);
    phase29_update_bool(&mut hasher, witness.full_history_replay_required);
    phase29_update_bool(&mut hasher, witness.cryptographic_compression_claimed);
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 42 history-equivalence witness commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn phase42_prepare_boundary_history_equivalence_witness(
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase42BoundaryHistoryEquivalenceWitness> {
    phase42_verify_source_stack(chain, phase28, contract, phase30)?;

    let first_step = chain.steps.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 42 history-equivalence witness requires a Phase 12 chain with at least one step"
                .to_string(),
        )
    })?;
    let last_step = chain
        .steps
        .last()
        .expect("checked non-empty Phase 12 chain");

    let replayed_phase14 = phase14_prepare_decoding_chain(chain)?;
    verify_phase14_decoding_chain(&replayed_phase14)?;
    let replayed_first_step = replayed_phase14.steps.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 42 history-equivalence witness requires a replayed Phase 14 chain with at least one step"
                .to_string(),
        )
    })?;
    let replayed_last_step = replayed_phase14
        .steps
        .last()
        .expect("checked non-empty Phase 14 chain");
    let replayed_phase14_start_state = replayed_first_step.from_state.clone();
    let replayed_phase14_end_state = replayed_last_step.to_state.clone();
    let (phase28_phase14_start_state, phase28_phase14_end_state) =
        phase28_global_boundary_preimage_states(phase28)?;
    if replayed_phase14_start_state != phase28_phase14_start_state {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness replayed Phase14 start state does not match the Phase28 global start preimage"
                .to_string(),
        ));
    }
    if replayed_phase14_end_state != phase28_phase14_end_state {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness replayed Phase14 end state does not match the Phase28 global end preimage"
                .to_string(),
        ));
    }

    phase42_shared_core_matches_with_history_bridge(
        "start",
        &first_step.from_state,
        &replayed_phase14_start_state,
    )?;
    phase42_shared_core_matches_with_history_bridge(
        "end",
        &last_step.to_state,
        &replayed_phase14_end_state,
    )?;

    let phase14_start_boundary = commit_phase23_boundary_state(&replayed_phase14_start_state);
    let phase14_end_boundary = commit_phase23_boundary_state(&replayed_phase14_end_state);
    if phase14_start_boundary != phase28.global_start_state_commitment
        || phase14_start_boundary != contract.global_start_state_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness replayed Phase14 start state does not bind Phase28/29 start boundary"
                .to_string(),
        ));
    }
    if phase14_end_boundary != phase28.global_end_state_commitment
        || phase14_end_boundary != contract.global_end_state_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness replayed Phase14 end state does not bind Phase28/29 end boundary"
                .to_string(),
        ));
    }

    let (appended_pairs_commitment, appended_pair_count) =
        phase42_commit_source_appended_pairs(chain)?;
    let (lookup_rows_commitments_commitment, lookup_rows_commitment_count) =
        phase42_commit_source_lookup_rows_commitments(chain)?;
    let mut witness = Phase42BoundaryHistoryEquivalenceWitness {
        issue: STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
        witness_version: STWO_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_VERSION_PHASE42.to_string(),
        relation_outcome: STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42.to_string(),
        transform_rule: STWO_BOUNDARY_HISTORY_EQUIVALENCE_RULE_PHASE42.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: phase30.proof_backend_version.clone(),
        statement_version: phase30.statement_version.clone(),
        phase29_contract_commitment: contract.input_contract_commitment.clone(),
        phase28_aggregate_commitment: phase28
            .aggregated_chained_folded_interval_accumulator_commitment
            .clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        total_steps: phase30.total_steps,
        layout_commitment: first_step.from_state.layout_commitment.clone(),
        rolling_kv_pairs: chain.layout.rolling_kv_pairs,
        pair_width: chain.layout.pair_width,
        phase12_start_public_state_commitment: first_step
            .from_state
            .public_state_commitment
            .clone(),
        phase12_end_public_state_commitment: last_step.to_state.public_state_commitment.clone(),
        phase14_start_boundary_commitment: phase14_start_boundary,
        phase14_end_boundary_commitment: phase14_end_boundary,
        phase12_start_history_commitment: first_step.from_state.kv_history_commitment.clone(),
        phase12_end_history_commitment: last_step.to_state.kv_history_commitment.clone(),
        phase14_start_history_commitment: replayed_phase14_start_state.kv_history_commitment,
        phase14_end_history_commitment: replayed_phase14_end_state.kv_history_commitment,
        initial_kv_cache_commitment: first_step.from_state.kv_cache_commitment.clone(),
        appended_pairs_commitment,
        appended_pair_count,
        lookup_rows_commitments_commitment,
        lookup_rows_commitment_count,
        full_history_replay_required: true,
        cryptographic_compression_claimed: false,
        witness_commitment: String::new(),
    };
    witness.witness_commitment = commit_phase42_boundary_history_equivalence_witness(&witness)?;
    verify_phase42_boundary_history_equivalence_witness(&witness)?;
    Ok(witness)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase42_boundary_history_equivalence_witness(
    witness: &Phase42BoundaryHistoryEquivalenceWitness,
) -> Result<()> {
    if witness.issue != STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness must reference Issue #{}, got #{}",
            STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42, witness.issue
        )));
    }
    if witness.witness_version != STWO_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_VERSION_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness version `{}` does not match expected `{}`",
            witness.witness_version, STWO_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_VERSION_PHASE42
        )));
    }
    if witness.relation_outcome != STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness relation `{}` does not match expected `{}`",
            witness.relation_outcome, STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42
        )));
    }
    if witness.transform_rule != STWO_BOUNDARY_HISTORY_EQUIVALENCE_RULE_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness transform rule `{}` does not match expected `{}`",
            witness.transform_rule, STWO_BOUNDARY_HISTORY_EQUIVALENCE_RULE_PHASE42
        )));
    }
    if witness.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness requires `stwo` backend, got `{}`",
            witness.proof_backend
        )));
    }
    if witness.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, witness.proof_backend_version
        )));
    }
    if witness.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, witness.statement_version
        )));
    }
    if witness.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness requires at least one decode step".to_string(),
        ));
    }
    if witness.rolling_kv_pairs == 0 || witness.pair_width == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness requires non-zero layout widths".to_string(),
        ));
    }
    if witness.appended_pair_count != witness.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness appended_pair_count={} must equal total_steps={}",
            witness.appended_pair_count, witness.total_steps
        )));
    }
    let expected_lookup_count = witness.total_steps.checked_add(1).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 42 history-equivalence witness lookup count overflowed".to_string(),
        )
    })?;
    if witness.lookup_rows_commitment_count != expected_lookup_count {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness lookup_rows_commitment_count={} must equal total_steps+1={expected_lookup_count}",
            witness.lookup_rows_commitment_count
        )));
    }
    if !witness.full_history_replay_required {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness must declare full_history_replay_required=true until a compact proof replaces replay"
                .to_string(),
        ));
    }
    if witness.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness must not claim cryptographic compression"
                .to_string(),
        ));
    }
    for (field, value) in [
        (
            "phase29_contract_commitment",
            witness.phase29_contract_commitment.as_str(),
        ),
        (
            "phase28_aggregate_commitment",
            witness.phase28_aggregate_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            witness.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            witness.phase30_step_envelopes_commitment.as_str(),
        ),
        ("layout_commitment", witness.layout_commitment.as_str()),
        (
            "phase12_start_public_state_commitment",
            witness.phase12_start_public_state_commitment.as_str(),
        ),
        (
            "phase12_end_public_state_commitment",
            witness.phase12_end_public_state_commitment.as_str(),
        ),
        (
            "phase14_start_boundary_commitment",
            witness.phase14_start_boundary_commitment.as_str(),
        ),
        (
            "phase14_end_boundary_commitment",
            witness.phase14_end_boundary_commitment.as_str(),
        ),
        (
            "phase12_start_history_commitment",
            witness.phase12_start_history_commitment.as_str(),
        ),
        (
            "phase12_end_history_commitment",
            witness.phase12_end_history_commitment.as_str(),
        ),
        (
            "phase14_start_history_commitment",
            witness.phase14_start_history_commitment.as_str(),
        ),
        (
            "phase14_end_history_commitment",
            witness.phase14_end_history_commitment.as_str(),
        ),
        (
            "initial_kv_cache_commitment",
            witness.initial_kv_cache_commitment.as_str(),
        ),
        (
            "appended_pairs_commitment",
            witness.appended_pairs_commitment.as_str(),
        ),
        (
            "lookup_rows_commitments_commitment",
            witness.lookup_rows_commitments_commitment.as_str(),
        ),
        ("witness_commitment", witness.witness_commitment.as_str()),
    ] {
        phase42_require_hash32(&format!("history_equivalence.{field}"), value)?;
    }
    let expected = commit_phase42_boundary_history_equivalence_witness(witness)?;
    if witness.witness_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness commitment does not match recomputed `{expected}`"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase42_boundary_history_equivalence_witness_against_sources(
    witness: &Phase42BoundaryHistoryEquivalenceWitness,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase42_boundary_history_equivalence_witness(witness)?;
    let expected =
        phase42_prepare_boundary_history_equivalence_witness(chain, phase28, contract, phase30)?;
    if witness != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 42 history-equivalence witness does not match the recomputed Phase12 replay over supplied sources"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase43_history_replay_trace(trace: &Phase43HistoryReplayTrace) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 43 history replay trace commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase43-history-replay-trace");
    phase29_update_usize(&mut hasher, trace.issue);
    let proof_backend = trace.proof_backend.to_string();
    for part in [
        trace.trace_version.as_bytes(),
        trace.relation_outcome.as_bytes(),
        trace.transform_rule.as_bytes(),
        proof_backend.as_bytes(),
        trace.proof_backend_version.as_bytes(),
        trace.statement_version.as_bytes(),
        trace.phase42_witness_commitment.as_bytes(),
        trace.phase29_contract_commitment.as_bytes(),
        trace.phase28_aggregate_commitment.as_bytes(),
        trace.phase30_source_chain_commitment.as_bytes(),
        trace.phase30_step_envelopes_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, trace.total_steps);
    phase29_update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
    phase29_update_usize(&mut hasher, trace.rolling_kv_pairs);
    phase29_update_usize(&mut hasher, trace.pair_width);
    for part in [
        trace.phase12_start_public_state_commitment.as_bytes(),
        trace.phase12_end_public_state_commitment.as_bytes(),
        trace.phase14_start_boundary_commitment.as_bytes(),
        trace.phase14_end_boundary_commitment.as_bytes(),
        trace.phase12_start_history_commitment.as_bytes(),
        trace.phase12_end_history_commitment.as_bytes(),
        trace.phase14_start_history_commitment.as_bytes(),
        trace.phase14_end_history_commitment.as_bytes(),
        trace.initial_kv_cache_commitment.as_bytes(),
        trace.appended_pairs_commitment.as_bytes(),
        trace.lookup_rows_commitments_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, trace.rows.len());
    for row in &trace.rows {
        phase43_update_trace_row(&mut hasher, row);
    }
    phase29_update_bool(&mut hasher, trace.full_history_replay_required);
    phase29_update_bool(&mut hasher, trace.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, trace.stwo_air_proof_claimed);
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 43 history replay trace commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
pub fn phase43_prepare_history_replay_trace(
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase43HistoryReplayTrace> {
    let phase42_witness =
        phase42_prepare_boundary_history_equivalence_witness(chain, phase28, contract, phase30)?;
    let replayed_phase14 = phase14_prepare_decoding_chain(chain)?;
    verify_phase14_decoding_chain(&replayed_phase14)?;
    if replayed_phase14.steps.len() != chain.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 replay trace expected {} replayed Phase14 steps, got {}",
            chain.steps.len(),
            replayed_phase14.steps.len()
        )));
    }
    if phase30.envelopes.len() != chain.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 replay trace expected {} Phase30 envelopes, got {}",
            chain.steps.len(),
            phase30.envelopes.len()
        )));
    }
    let latest_cached_pair_range = chain.layout.latest_cached_pair_range()?;
    let mut rows = Vec::with_capacity(chain.steps.len());
    for (step_index, ((phase12_step, phase14_step), phase30_envelope)) in chain
        .steps
        .iter()
        .zip(replayed_phase14.steps.iter())
        .zip(phase30.envelopes.iter())
        .enumerate()
    {
        if phase30_envelope.step_index != step_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 replay trace Phase30 envelope at row {step_index} has step_index {}",
                phase30_envelope.step_index
            )));
        }
        rows.push(Phase43HistoryReplayTraceRow {
            step_index,
            appended_pair: phase12_step.proof.claim.final_state.memory
                [latest_cached_pair_range.clone()]
            .to_vec(),
            input_lookup_rows_commitment: phase12_step.from_state.lookup_rows_commitment.clone(),
            output_lookup_rows_commitment: phase12_step.to_state.lookup_rows_commitment.clone(),
            phase30_step_envelope_commitment: phase30_envelope.envelope_commitment.clone(),
            phase12_from_state: phase12_step.from_state.clone(),
            phase12_to_state: phase12_step.to_state.clone(),
            phase14_from_state: phase14_step.from_state.clone(),
            phase14_to_state: phase14_step.to_state.clone(),
        });
    }
    let mut trace = Phase43HistoryReplayTrace {
        issue: STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
        trace_version: STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43.to_string(),
        relation_outcome: STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43.to_string(),
        transform_rule: STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: phase42_witness.proof_backend_version,
        statement_version: phase42_witness.statement_version,
        phase42_witness_commitment: phase42_witness.witness_commitment,
        phase29_contract_commitment: phase42_witness.phase29_contract_commitment,
        phase28_aggregate_commitment: phase42_witness.phase28_aggregate_commitment,
        phase30_source_chain_commitment: phase42_witness.phase30_source_chain_commitment,
        phase30_step_envelopes_commitment: phase42_witness.phase30_step_envelopes_commitment,
        total_steps: phase42_witness.total_steps,
        layout_commitment: phase42_witness.layout_commitment,
        rolling_kv_pairs: phase42_witness.rolling_kv_pairs,
        pair_width: phase42_witness.pair_width,
        phase12_start_public_state_commitment: phase42_witness
            .phase12_start_public_state_commitment,
        phase12_end_public_state_commitment: phase42_witness.phase12_end_public_state_commitment,
        phase14_start_boundary_commitment: phase42_witness.phase14_start_boundary_commitment,
        phase14_end_boundary_commitment: phase42_witness.phase14_end_boundary_commitment,
        phase12_start_history_commitment: phase42_witness.phase12_start_history_commitment,
        phase12_end_history_commitment: phase42_witness.phase12_end_history_commitment,
        phase14_start_history_commitment: phase42_witness.phase14_start_history_commitment,
        phase14_end_history_commitment: phase42_witness.phase14_end_history_commitment,
        initial_kv_cache_commitment: phase42_witness.initial_kv_cache_commitment,
        appended_pairs_commitment: phase42_witness.appended_pairs_commitment,
        lookup_rows_commitments_commitment: phase42_witness.lookup_rows_commitments_commitment,
        rows,
        full_history_replay_required: true,
        cryptographic_compression_claimed: false,
        stwo_air_proof_claimed: false,
        trace_commitment: String::new(),
    };
    trace.trace_commitment = commit_phase43_history_replay_trace(&trace)?;
    verify_phase43_history_replay_trace(&trace)?;
    Ok(trace)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase43_history_replay_trace(trace: &Phase43HistoryReplayTrace) -> Result<()> {
    phase43_verify_header(trace)?;
    if trace.total_steps != trace.rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace total_steps={} must equal rows.len()={}",
            trace.total_steps,
            trace.rows.len()
        )));
    }
    if trace.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace requires at least one row".to_string(),
        ));
    }
    let expected_appended_pairs = phase43_commit_trace_appended_pairs(trace)?;
    if trace.appended_pairs_commitment != expected_appended_pairs {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace appended_pairs_commitment does not match recomputed `{expected_appended_pairs}`"
        )));
    }
    let expected_lookup_rows = phase43_commit_trace_lookup_rows_commitments(trace)?;
    if trace.lookup_rows_commitments_commitment != expected_lookup_rows {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace lookup_rows_commitments_commitment does not match recomputed `{expected_lookup_rows}`"
        )));
    }
    let expected_step_envelopes = phase43_commit_trace_phase30_step_envelopes(trace)?;
    if trace.phase30_step_envelopes_commitment != expected_step_envelopes {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace phase30_step_envelopes_commitment does not match recomputed `{expected_step_envelopes}`"
        )));
    }

    for (expected_step, row) in trace.rows.iter().enumerate() {
        phase43_verify_row(trace, expected_step, row)?;
        if let Some(next) = trace.rows.get(expected_step + 1) {
            phase43_require_phase12_link(
                expected_step,
                &row.phase12_to_state,
                &next.phase12_from_state,
            )?;
            phase43_require_phase14_link(
                expected_step,
                &row.phase14_to_state,
                &next.phase14_from_state,
            )?;
        }
    }

    let first = trace.rows.first().expect("checked non-empty trace");
    let last = trace.rows.last().expect("checked non-empty trace");
    if trace.phase12_start_public_state_commitment
        != first.phase12_from_state.public_state_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace Phase12 start commitment does not match first row"
                .to_string(),
        ));
    }
    if trace.phase12_end_public_state_commitment != last.phase12_to_state.public_state_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace Phase12 end commitment does not match last row"
                .to_string(),
        ));
    }
    let expected_start_boundary = commit_phase23_boundary_state(&first.phase14_from_state);
    if trace.phase14_start_boundary_commitment != expected_start_boundary {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace Phase14 start boundary does not match recomputed `{expected_start_boundary}`"
        )));
    }
    let expected_end_boundary = commit_phase23_boundary_state(&last.phase14_to_state);
    if trace.phase14_end_boundary_commitment != expected_end_boundary {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace Phase14 end boundary does not match recomputed `{expected_end_boundary}`"
        )));
    }
    if trace.phase12_start_history_commitment != first.phase12_from_state.kv_history_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace Phase12 start history does not match first row"
                .to_string(),
        ));
    }
    if trace.phase12_end_history_commitment != last.phase12_to_state.kv_history_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace Phase12 end history does not match last row".to_string(),
        ));
    }
    if trace.phase14_start_history_commitment != first.phase14_from_state.kv_history_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace Phase14 start history does not match first row"
                .to_string(),
        ));
    }
    if trace.phase14_end_history_commitment != last.phase14_to_state.kv_history_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace Phase14 end history does not match last row".to_string(),
        ));
    }
    if trace.initial_kv_cache_commitment != first.phase12_from_state.kv_cache_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace initial_kv_cache_commitment does not match first row"
                .to_string(),
        ));
    }
    let expected = commit_phase43_history_replay_trace(trace)?;
    if trace.trace_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace commitment does not match recomputed `{expected}`"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase43_history_replay_trace_against_sources(
    trace: &Phase43HistoryReplayTrace,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase43_history_replay_trace(trace)?;
    let expected = phase43_prepare_history_replay_trace(chain, phase28, contract, phase30)?;
    if trace != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace does not match the recomputed Phase42 full replay over supplied sources"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase43_verify_header(trace: &Phase43HistoryReplayTrace) -> Result<()> {
    if trace.issue != STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace must reference Issue #{}, got #{}",
            STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42, trace.issue
        )));
    }
    if trace.trace_version != STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace version `{}` does not match expected `{}`",
            trace.trace_version, STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43
        )));
    }
    if trace.relation_outcome != STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace relation `{}` does not match expected `{}`",
            trace.relation_outcome, STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43
        )));
    }
    if trace.transform_rule != STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace transform rule `{}` does not match expected `{}`",
            trace.transform_rule, STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43
        )));
    }
    if trace.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace requires `stwo` backend, got `{}`",
            trace.proof_backend
        )));
    }
    if trace.proof_backend_version != STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace requires proof backend version `{}`, got `{}`",
            STWO_BACKEND_VERSION_PHASE12, trace.proof_backend_version
        )));
    }
    if trace.statement_version != CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace requires statement version `{}`, got `{}`",
            CLAIM_STATEMENT_VERSION_V1, trace.statement_version
        )));
    }
    if trace.rolling_kv_pairs == 0 || trace.pair_width == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace requires non-zero layout widths".to_string(),
        ));
    }
    if !trace.full_history_replay_required {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace must declare full_history_replay_required=true until a compact proof replaces replay"
                .to_string(),
        ));
    }
    if trace.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace must not claim cryptographic compression".to_string(),
        ));
    }
    if trace.stwo_air_proof_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 43 history replay trace must not claim a Stwo AIR proof yet".to_string(),
        ));
    }
    for (field, value) in [
        (
            "phase42_witness_commitment",
            trace.phase42_witness_commitment.as_str(),
        ),
        (
            "phase29_contract_commitment",
            trace.phase29_contract_commitment.as_str(),
        ),
        (
            "phase28_aggregate_commitment",
            trace.phase28_aggregate_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            trace.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            trace.phase30_step_envelopes_commitment.as_str(),
        ),
        ("layout_commitment", trace.layout_commitment.as_str()),
        (
            "phase12_start_public_state_commitment",
            trace.phase12_start_public_state_commitment.as_str(),
        ),
        (
            "phase12_end_public_state_commitment",
            trace.phase12_end_public_state_commitment.as_str(),
        ),
        (
            "phase14_start_boundary_commitment",
            trace.phase14_start_boundary_commitment.as_str(),
        ),
        (
            "phase14_end_boundary_commitment",
            trace.phase14_end_boundary_commitment.as_str(),
        ),
        (
            "phase12_start_history_commitment",
            trace.phase12_start_history_commitment.as_str(),
        ),
        (
            "phase12_end_history_commitment",
            trace.phase12_end_history_commitment.as_str(),
        ),
        (
            "phase14_start_history_commitment",
            trace.phase14_start_history_commitment.as_str(),
        ),
        (
            "phase14_end_history_commitment",
            trace.phase14_end_history_commitment.as_str(),
        ),
        (
            "initial_kv_cache_commitment",
            trace.initial_kv_cache_commitment.as_str(),
        ),
        (
            "appended_pairs_commitment",
            trace.appended_pairs_commitment.as_str(),
        ),
        (
            "lookup_rows_commitments_commitment",
            trace.lookup_rows_commitments_commitment.as_str(),
        ),
        ("trace_commitment", trace.trace_commitment.as_str()),
    ] {
        phase43_require_hash32(&format!("history_replay_trace.{field}"), value)?;
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase43_verify_row(
    trace: &Phase43HistoryReplayTrace,
    expected_step: usize,
    row: &Phase43HistoryReplayTraceRow,
) -> Result<()> {
    if row.step_index != expected_step {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} has step_index {}",
            row.step_index
        )));
    }
    if row.appended_pair.len() != trace.pair_width {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} appended_pair has {} values, expected pair_width={}",
            row.appended_pair.len(),
            trace.pair_width
        )));
    }
    for (field, value) in [
        (
            "input_lookup_rows_commitment",
            row.input_lookup_rows_commitment.as_str(),
        ),
        (
            "output_lookup_rows_commitment",
            row.output_lookup_rows_commitment.as_str(),
        ),
        (
            "phase30_step_envelope_commitment",
            row.phase30_step_envelope_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(
            &format!("history_replay_trace.rows[{expected_step}].{field}"),
            value,
        )?;
    }
    phase42_verify_phase12_state(
        &format!("phase43.rows[{expected_step}].phase12_from_state"),
        &row.phase12_from_state,
    )?;
    phase42_verify_phase12_state(
        &format!("phase43.rows[{expected_step}].phase12_to_state"),
        &row.phase12_to_state,
    )?;
    phase42_verify_phase14_state(
        &format!("phase43.rows[{expected_step}].phase14_from_state"),
        &row.phase14_from_state,
    )?;
    phase42_verify_phase14_state(
        &format!("phase43.rows[{expected_step}].phase14_to_state"),
        &row.phase14_to_state,
    )?;
    if row.phase12_from_state.step_index != expected_step
        || row.phase14_from_state.step_index != expected_step
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} from_state step_index mismatch"
        )));
    }
    let expected_to_step = expected_step.checked_add(1).ok_or_else(|| {
        VmError::InvalidConfig("Phase 43 history replay trace step_index overflowed".to_string())
    })?;
    if row.phase12_to_state.step_index != expected_to_step
        || row.phase14_to_state.step_index != expected_to_step
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} to_state step_index mismatch"
        )));
    }
    if row.phase12_from_state.layout_commitment != trace.layout_commitment
        || row.phase12_to_state.layout_commitment != trace.layout_commitment
        || row.phase14_from_state.layout_commitment != trace.layout_commitment
        || row.phase14_to_state.layout_commitment != trace.layout_commitment
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} layout commitment mismatch"
        )));
    }
    if row.input_lookup_rows_commitment != row.phase12_from_state.lookup_rows_commitment
        || row.input_lookup_rows_commitment != row.phase14_from_state.lookup_rows_commitment
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} input_lookup_rows_commitment mismatch"
        )));
    }
    if row.output_lookup_rows_commitment != row.phase12_to_state.lookup_rows_commitment
        || row.output_lookup_rows_commitment != row.phase14_to_state.lookup_rows_commitment
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {expected_step} output_lookup_rows_commitment mismatch"
        )));
    }
    phase42_shared_core_matches_with_history_bridge(
        &format!("phase43 row {expected_step} from"),
        &row.phase12_from_state,
        &row.phase14_from_state,
    )?;
    phase42_shared_core_matches_with_history_bridge(
        &format!("phase43 row {expected_step} to"),
        &row.phase12_to_state,
        &row.phase14_to_state,
    )?;
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase43_require_phase12_link(
    row_index: usize,
    previous: &Phase12DecodingState,
    next: &Phase12DecodingState,
) -> Result<()> {
    if previous.public_state_commitment != next.public_state_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase12 link does not preserve public_state_commitment"
        )));
    }
    if previous.persistent_state_commitment != next.persistent_state_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase12 link does not preserve persistent_state_commitment"
        )));
    }
    if previous.kv_cache_commitment != next.kv_cache_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase12 link does not preserve kv_cache_commitment"
        )));
    }
    if previous.position != next.position {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase12 link does not preserve position"
        )));
    }
    if previous.kv_history_commitment != next.kv_history_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase12 link does not preserve kv_history_commitment"
        )));
    }
    if previous.kv_history_length != next.kv_history_length {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase12 link does not preserve kv_history_length"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase43_require_phase14_link(
    row_index: usize,
    previous: &Phase14DecodingState,
    next: &Phase14DecodingState,
) -> Result<()> {
    if previous.public_state_commitment != next.public_state_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve public_state_commitment"
        )));
    }
    if previous.persistent_state_commitment != next.persistent_state_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve persistent_state_commitment"
        )));
    }
    if previous.kv_cache_commitment != next.kv_cache_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_cache_commitment"
        )));
    }
    if previous.position != next.position {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve position"
        )));
    }
    if previous.kv_history_commitment != next.kv_history_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_commitment"
        )));
    }
    if previous.kv_history_length != next.kv_history_length {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_length"
        )));
    }
    if previous.kv_history_sealed_commitment != next.kv_history_sealed_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_sealed_commitment"
        )));
    }
    if previous.kv_history_sealed_chunks != next.kv_history_sealed_chunks {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_sealed_chunks"
        )));
    }
    if previous.kv_history_open_chunk_commitment != next.kv_history_open_chunk_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_open_chunk_commitment"
        )));
    }
    if previous.kv_history_open_chunk_pairs != next.kv_history_open_chunk_pairs {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_open_chunk_pairs"
        )));
    }
    if previous.kv_history_frontier_commitment != next.kv_history_frontier_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_frontier_commitment"
        )));
    }
    if previous.kv_history_frontier_pairs != next.kv_history_frontier_pairs {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve kv_history_frontier_pairs"
        )));
    }
    if previous.lookup_transcript_commitment != next.lookup_transcript_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve lookup_transcript_commitment"
        )));
    }
    if previous.lookup_transcript_entries != next.lookup_transcript_entries {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve lookup_transcript_entries"
        )));
    }
    if previous.lookup_frontier_commitment != next.lookup_frontier_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve lookup_frontier_commitment"
        )));
    }
    if previous.lookup_frontier_entries != next.lookup_frontier_entries {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace row {row_index} Phase14 link does not preserve lookup_frontier_entries"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase43_commit_trace_appended_pairs(trace: &Phase43HistoryReplayTrace) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 43 appended-pairs commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase42-source-appended-pairs");
    phase29_update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
    phase29_update_usize(&mut hasher, trace.pair_width);
    phase29_update_usize(&mut hasher, trace.rows.len());
    for (step_index, row) in trace.rows.iter().enumerate() {
        if row.appended_pair.len() != trace.pair_width {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 appended pair {step_index} has {} values, expected pair_width={}",
                row.appended_pair.len(),
                trace.pair_width
            )));
        }
        phase29_update_usize(&mut hasher, step_index);
        for value in &row.appended_pair {
            hasher.update(&value.to_le_bytes());
        }
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 43 appended-pairs commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase43_commit_trace_lookup_rows_commitments(
    trace: &Phase43HistoryReplayTrace,
) -> Result<String> {
    let first = trace.rows.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 43 lookup-row commitment requires a non-empty trace".to_string(),
        )
    })?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 43 lookup-row replay commitment hash: {err}"
        ))
    })?;
    let commitment_count = trace.rows.len().checked_add(1).ok_or_else(|| {
        VmError::InvalidConfig("Phase 43 lookup-row commitment count overflowed".to_string())
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase42-source-lookup-rows");
    phase29_update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
    phase29_update_usize(&mut hasher, commitment_count);
    phase43_hash_lookup_row_commitment(&mut hasher, 0, &first.input_lookup_rows_commitment)?;
    for (index, row) in trace.rows.iter().enumerate() {
        phase43_hash_lookup_row_commitment(
            &mut hasher,
            index + 1,
            &row.output_lookup_rows_commitment,
        )?;
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 43 lookup-row replay commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase43_hash_lookup_row_commitment(
    hasher: &mut Blake2bVar,
    index: usize,
    commitment: &str,
) -> Result<()> {
    phase43_require_hash32(
        &format!("history_replay_trace.lookup_rows[{index}]"),
        commitment,
    )?;
    phase29_update_usize(hasher, index);
    phase29_update_len_prefixed(hasher, commitment.as_bytes());
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase43_commit_trace_phase30_step_envelopes(
    trace: &Phase43HistoryReplayTrace,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 43 Phase30 envelope-list commitment hash: {err}"
        ))
    })?;
    hasher.update(STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30.as_bytes());
    hasher.update(b"step-envelope-list");
    hasher.update(&(trace.rows.len() as u64).to_le_bytes());
    for (index, row) in trace.rows.iter().enumerate() {
        phase43_require_hash32(
            &format!("history_replay_trace.phase30_step_envelopes[{index}]"),
            &row.phase30_step_envelope_commitment,
        )?;
        hasher.update(row.phase30_step_envelope_commitment.as_bytes());
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 43 Phase30 envelope-list commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase43_update_trace_row(hasher: &mut Blake2bVar, row: &Phase43HistoryReplayTraceRow) {
    phase29_update_usize(hasher, row.step_index);
    phase29_update_usize(hasher, row.appended_pair.len());
    for value in &row.appended_pair {
        hasher.update(&value.to_le_bytes());
    }
    for part in [
        row.input_lookup_rows_commitment.as_bytes(),
        row.output_lookup_rows_commitment.as_bytes(),
        row.phase30_step_envelope_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(hasher, part);
    }
    phase43_update_phase12_state(hasher, &row.phase12_from_state);
    phase43_update_phase12_state(hasher, &row.phase12_to_state);
    phase43_update_phase14_state(hasher, &row.phase14_from_state);
    phase43_update_phase14_state(hasher, &row.phase14_to_state);
}

#[cfg(feature = "stwo-backend")]
fn phase43_update_phase12_state(hasher: &mut Blake2bVar, state: &Phase12DecodingState) {
    for part in [
        state.state_version.as_bytes(),
        state.layout_commitment.as_bytes(),
        state.persistent_state_commitment.as_bytes(),
        state.kv_history_commitment.as_bytes(),
        state.kv_cache_commitment.as_bytes(),
        state.incoming_token_commitment.as_bytes(),
        state.query_commitment.as_bytes(),
        state.output_commitment.as_bytes(),
        state.lookup_rows_commitment.as_bytes(),
        state.public_state_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(hasher, part);
    }
    phase29_update_usize(hasher, state.step_index);
    hasher.update(&state.position.to_le_bytes());
    phase29_update_usize(hasher, state.kv_history_length);
}

#[cfg(feature = "stwo-backend")]
fn phase43_update_phase14_state(hasher: &mut Blake2bVar, state: &Phase14DecodingState) {
    for part in [
        state.state_version.as_bytes(),
        state.layout_commitment.as_bytes(),
        state.persistent_state_commitment.as_bytes(),
        state.kv_history_commitment.as_bytes(),
        state.kv_history_sealed_commitment.as_bytes(),
        state.kv_history_open_chunk_commitment.as_bytes(),
        state.kv_history_frontier_commitment.as_bytes(),
        state.lookup_transcript_commitment.as_bytes(),
        state.lookup_frontier_commitment.as_bytes(),
        state.kv_cache_commitment.as_bytes(),
        state.incoming_token_commitment.as_bytes(),
        state.query_commitment.as_bytes(),
        state.output_commitment.as_bytes(),
        state.lookup_rows_commitment.as_bytes(),
        state.public_state_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(hasher, part);
    }
    phase29_update_usize(hasher, state.step_index);
    hasher.update(&state.position.to_le_bytes());
    phase29_update_usize(hasher, state.kv_history_length);
    phase29_update_usize(hasher, state.kv_history_chunk_size);
    phase29_update_usize(hasher, state.kv_history_sealed_chunks);
    phase29_update_usize(hasher, state.kv_history_open_chunk_pairs);
    phase29_update_usize(hasher, state.kv_history_frontier_pairs);
    phase29_update_usize(hasher, state.lookup_transcript_entries);
    phase29_update_usize(hasher, state.lookup_frontier_entries);
}

#[cfg(feature = "stwo-backend")]
fn phase43_require_hash32(label: &str, value: &str) -> Result<()> {
    if !phase37_is_hash32_lower_hex(value) {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase44d_recursive_verifier_public_output_handoff(
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D recursive-verifier public-output handoff hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase44d-recursive-verifier-public-output-handoff",
    );
    phase29_update_len_prefixed(&mut hasher, handoff.proof_backend.to_string().as_bytes());
    for part in [
        handoff.handoff_version.as_bytes(),
        handoff.semantic_scope.as_bytes(),
        handoff.verifier_harness.as_bytes(),
        handoff.proof_backend_version.as_bytes(),
        handoff.statement_version.as_bytes(),
        handoff.compact_claim_version.as_bytes(),
        handoff.compact_semantic_scope.as_bytes(),
        handoff.compact_source_binding.as_bytes(),
        handoff.compact_envelope_commitment.as_bytes(),
        handoff
            .source_chain_public_output_boundary_version
            .as_bytes(),
        handoff.source_surface_version.as_bytes(),
        handoff
            .source_chain_public_output_boundary_commitment
            .as_bytes(),
        handoff.source_emission_public_output_commitment.as_bytes(),
        handoff.emitted_root_artifact_commitment.as_bytes(),
        handoff.source_root_acceptance_commitment.as_bytes(),
        handoff.emitted_canonical_source_root.as_bytes(),
        handoff.source_root_preimage_commitment.as_bytes(),
        handoff.compact_projection_trace_root.as_bytes(),
        handoff.compact_preprocessed_trace_root.as_bytes(),
        handoff.terminal_boundary_commitment.as_bytes(),
        handoff
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
        handoff
            .terminal_boundary_logup_closure_commitment
            .as_bytes(),
        handoff.phase43_trace_commitment.as_bytes(),
        handoff.phase43_trace_version.as_bytes(),
        handoff.phase30_manifest_version.as_bytes(),
        handoff.phase30_semantic_scope.as_bytes(),
        handoff.phase30_source_chain_commitment.as_bytes(),
        handoff.phase30_step_envelopes_commitment.as_bytes(),
        handoff.verifier_side_complexity.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, handoff.compact_proof_size_bytes);
    phase44d_update_u32_vec(
        &mut hasher,
        &handoff.terminal_boundary_public_logup_sum_limbs,
    );
    phase44d_update_u32_vec(
        &mut hasher,
        &handoff.terminal_boundary_component_claimed_sum_limbs,
    );
    phase29_update_usize(&mut hasher, handoff.total_steps);
    phase29_update_usize(&mut hasher, handoff.pair_width);
    phase29_update_usize(&mut hasher, handoff.projection_row_count);
    phase29_update_usize(&mut hasher, handoff.projection_column_count);
    phase29_update_bool(&mut hasher, handoff.public_output_boundary_verified);
    phase29_update_bool(&mut hasher, handoff.compact_envelope_verified);
    phase29_update_bool(&mut hasher, handoff.source_root_acceptance_verified);
    phase29_update_bool(
        &mut hasher,
        handoff.terminal_boundary_logup_closure_verified,
    );
    phase29_update_bool(&mut hasher, handoff.final_useful_compression_boundary);
    phase29_update_bool(&mut hasher, handoff.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, handoff.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, handoff.verifier_requires_phase43_trace);
    phase29_update_bool(&mut hasher, handoff.verifier_requires_phase30_manifest);
    phase29_update_bool(&mut hasher, handoff.verifier_embeds_expected_rows);
    phase44d_finalize_hash(hasher, "Phase 44D recursive-verifier public-output handoff")
}

#[cfg(feature = "stwo-backend")]
pub fn phase44d_prepare_recursive_verifier_public_output_handoff(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase44DRecursiveVerifierPublicOutputHandoff> {
    let acceptance =
        verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
            boundary,
            compact_envelope,
        )?;
    let compact_envelope_commitment = phase44d_commit_compact_envelope_reference(compact_envelope)?;
    let source_root_acceptance_commitment =
        phase44d_commit_source_root_acceptance_reference(&acceptance)?;
    let source_emission = &boundary.source_emission_public_output.source_emission;
    let source_claim = &source_emission.source_claim;
    let terminal_boundary_logup_closure =
        derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(
            source_claim,
            compact_envelope,
        )?;
    let mut handoff = Phase44DRecursiveVerifierPublicOutputHandoff {
        proof_backend: compact_envelope.claim.proof_backend.clone(),
        handoff_version: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_VERSION_PHASE44D.to_string(),
        semantic_scope: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_SCOPE_PHASE44D.to_string(),
        verifier_harness: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_KIND_PHASE44D.to_string(),
        proof_backend_version: compact_envelope.claim.proof_backend_version.clone(),
        statement_version: compact_envelope.claim.statement_version.clone(),
        compact_claim_version: compact_envelope.claim.claim_version.clone(),
        compact_semantic_scope: compact_envelope.claim.semantic_scope.clone(),
        compact_source_binding: compact_envelope.claim.source_binding.clone(),
        compact_envelope_commitment,
        compact_proof_size_bytes: compact_envelope.proof.len(),
        source_chain_public_output_boundary_version: boundary.boundary_version.clone(),
        source_surface_version: boundary.source_surface_version.clone(),
        source_chain_public_output_boundary_commitment: boundary
            .source_chain_public_output_boundary_commitment
            .clone(),
        source_emission_public_output_commitment: boundary
            .source_emission_public_output
            .public_output_commitment
            .clone(),
        emitted_root_artifact_commitment: source_emission
            .emitted_root_artifact
            .artifact_commitment
            .clone(),
        source_root_acceptance_commitment,
        emitted_canonical_source_root: acceptance.emitted_canonical_source_root.clone(),
        source_root_preimage_commitment: acceptance.source_root_preimage_commitment.clone(),
        compact_projection_trace_root: acceptance.compact_projection_trace_root.clone(),
        compact_preprocessed_trace_root: acceptance.compact_preprocessed_trace_root.clone(),
        terminal_boundary_commitment: source_claim
            .terminal_boundary
            .terminal_boundary_commitment
            .clone(),
        terminal_boundary_logup_statement_commitment: acceptance
            .terminal_boundary_logup_statement_commitment
            .clone(),
        terminal_boundary_public_logup_sum_limbs: source_claim
            .terminal_boundary_public_logup_sum_limbs
            .clone(),
        terminal_boundary_component_claimed_sum_limbs: terminal_boundary_logup_closure
            .terminal_boundary_component_claimed_sum_limbs
            .clone(),
        terminal_boundary_logup_closure_commitment: terminal_boundary_logup_closure
            .closure_commitment
            .clone(),
        phase43_trace_commitment: boundary.phase43_trace_commitment.clone(),
        phase43_trace_version: boundary.phase43_trace_version.clone(),
        phase30_manifest_version: boundary.phase30_manifest_version.clone(),
        phase30_semantic_scope: boundary.phase30_semantic_scope.clone(),
        phase30_source_chain_commitment: boundary.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: boundary.phase30_step_envelopes_commitment.clone(),
        total_steps: boundary.total_steps,
        pair_width: boundary.pair_width,
        projection_row_count: boundary.projection_row_count,
        projection_column_count: boundary.projection_column_count,
        public_output_boundary_verified: true,
        compact_envelope_verified: true,
        source_root_acceptance_verified: true,
        terminal_boundary_logup_closure_verified: true,
        final_useful_compression_boundary: acceptance.final_useful_compression_boundary,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        verifier_requires_phase43_trace: false,
        verifier_requires_phase30_manifest: false,
        verifier_embeds_expected_rows: false,
        verifier_side_complexity: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_COMPLEXITY_PHASE44D
            .to_string(),
        handoff_commitment: String::new(),
    };
    handoff.handoff_commitment =
        commit_phase44d_recursive_verifier_public_output_handoff(&handoff)?;
    verify_phase44d_recursive_verifier_public_output_handoff(&handoff)?;
    Ok(handoff)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase44d_recursive_verifier_public_output_handoff(
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
) -> Result<()> {
    if handoff.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D recursive-verifier public-output handoff requires `stwo` backend, got `{}`",
            handoff.proof_backend
        )));
    }
    if handoff.handoff_version != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_VERSION_PHASE44D {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D recursive-verifier public-output handoff version `{}` does not match expected `{}`",
            handoff.handoff_version,
            STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_VERSION_PHASE44D
        )));
    }
    if handoff.semantic_scope != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_SCOPE_PHASE44D {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D recursive-verifier public-output handoff scope `{}` does not match expected `{}`",
            handoff.semantic_scope,
            STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_SCOPE_PHASE44D
        )));
    }
    if handoff.verifier_harness != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_KIND_PHASE44D {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D recursive-verifier public-output handoff harness `{}` does not match expected `{}`",
            handoff.verifier_harness,
            STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_KIND_PHASE44D
        )));
    }
    if handoff.compact_claim_version != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff compact claim version drift"
                .to_string(),
        ));
    }
    if handoff.compact_semantic_scope
        != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff compact semantic scope drift"
                .to_string(),
        ));
    }
    if handoff.compact_source_binding
        != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff compact source binding drift"
                .to_string(),
        ));
    }
    if handoff.source_chain_public_output_boundary_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff source boundary version drift"
                .to_string(),
        ));
    }
    if handoff.source_surface_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff source surface version drift"
                .to_string(),
        ));
    }
    if !handoff.public_output_boundary_verified
        || !handoff.compact_envelope_verified
        || !handoff.source_root_acceptance_verified
        || !handoff.terminal_boundary_logup_closure_verified
        || !handoff.final_useful_compression_boundary
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff must carry verified boundary, compact envelope, source-root acceptance, and terminal LogUp closure"
                .to_string(),
        ));
    }
    if handoff.recursive_verification_claimed || handoff.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff must not claim recursive verification or cryptographic compression"
                .to_string(),
        ));
    }
    if handoff.verifier_requires_phase43_trace
        || handoff.verifier_requires_phase30_manifest
        || handoff.verifier_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff must remain boundary-width and must not require full trace, Phase30 manifest, or expected rows"
                .to_string(),
        ));
    }
    if handoff.verifier_side_complexity != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_COMPLEXITY_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D recursive-verifier public-output handoff complexity `{}` does not match expected `{}`",
            handoff.verifier_side_complexity,
            STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_COMPLEXITY_PHASE44D
        )));
    }
    if handoff.total_steps == 0
        || handoff.pair_width == 0
        || handoff.projection_row_count == 0
        || handoff.projection_column_count == 0
        || handoff.compact_proof_size_bytes == 0
        || handoff.terminal_boundary_public_logup_sum_limbs.is_empty()
        || handoff
            .terminal_boundary_component_claimed_sum_limbs
            .is_empty()
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff carries an empty shape field"
                .to_string(),
        ));
    }
    let public_sum = phase44d_secure_field_from_limbs(
        "terminal_boundary_public_logup_sum_limbs",
        &handoff.terminal_boundary_public_logup_sum_limbs,
    )?;
    let component_sum = phase44d_secure_field_from_limbs(
        "terminal_boundary_component_claimed_sum_limbs",
        &handoff.terminal_boundary_component_claimed_sum_limbs,
    )?;
    if public_sum + component_sum != SecureField::zero() {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff terminal LogUp public sum does not cancel component claimed sum"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "compact_envelope_commitment",
            handoff.compact_envelope_commitment.as_str(),
        ),
        (
            "source_chain_public_output_boundary_commitment",
            handoff
                .source_chain_public_output_boundary_commitment
                .as_str(),
        ),
        (
            "source_emission_public_output_commitment",
            handoff.source_emission_public_output_commitment.as_str(),
        ),
        (
            "emitted_root_artifact_commitment",
            handoff.emitted_root_artifact_commitment.as_str(),
        ),
        (
            "source_root_acceptance_commitment",
            handoff.source_root_acceptance_commitment.as_str(),
        ),
        (
            "emitted_canonical_source_root",
            handoff.emitted_canonical_source_root.as_str(),
        ),
        (
            "source_root_preimage_commitment",
            handoff.source_root_preimage_commitment.as_str(),
        ),
        (
            "compact_projection_trace_root",
            handoff.compact_projection_trace_root.as_str(),
        ),
        (
            "compact_preprocessed_trace_root",
            handoff.compact_preprocessed_trace_root.as_str(),
        ),
        (
            "terminal_boundary_commitment",
            handoff.terminal_boundary_commitment.as_str(),
        ),
        (
            "terminal_boundary_logup_statement_commitment",
            handoff
                .terminal_boundary_logup_statement_commitment
                .as_str(),
        ),
        (
            "terminal_boundary_logup_closure_commitment",
            handoff.terminal_boundary_logup_closure_commitment.as_str(),
        ),
        (
            "phase43_trace_commitment",
            handoff.phase43_trace_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            handoff.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            handoff.phase30_step_envelopes_commitment.as_str(),
        ),
        ("handoff_commitment", handoff.handoff_commitment.as_str()),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected = commit_phase44d_recursive_verifier_public_output_handoff(handoff)?;
    if handoff.handoff_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff commitment does not match handoff fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<()> {
    verify_phase44d_recursive_verifier_public_output_handoff(handoff)?;
    let expected =
        phase44d_prepare_recursive_verifier_public_output_handoff(boundary, compact_envelope)?;
    if handoff != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output handoff does not match the verified source-chain boundary and compact envelope"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase44d_recursive_verifier_public_output_aggregation(
    aggregation: &Phase44DRecursiveVerifierPublicOutputAggregation,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D recursive-verifier public-output aggregation hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase44d-recursive-verifier-public-output-aggregation",
    );
    phase29_update_len_prefixed(
        &mut hasher,
        aggregation.proof_backend.to_string().as_bytes(),
    );
    for part in [
        aggregation.aggregation_version.as_bytes(),
        aggregation.semantic_scope.as_bytes(),
        aggregation.verifier_harness.as_bytes(),
        aggregation.proof_backend_version.as_bytes(),
        aggregation.statement_version.as_bytes(),
        aggregation.handoff_list_commitment.as_bytes(),
        aggregation.verifier_side_complexity.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, aggregation.handoff_count);
    phase29_update_usize(&mut hasher, aggregation.total_steps);
    phase44d_update_hash_vec(&mut hasher, &aggregation.handoff_commitments);
    phase44d_update_hash_vec(
        &mut hasher,
        &aggregation.source_chain_public_output_boundary_commitments,
    );
    phase44d_update_hash_vec(&mut hasher, &aggregation.compact_envelope_commitments);
    phase44d_update_hash_vec(
        &mut hasher,
        &aggregation.terminal_boundary_logup_closure_commitments,
    );
    phase29_update_bool(&mut hasher, aggregation.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, aggregation.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, aggregation.verifier_requires_phase43_trace);
    phase29_update_bool(&mut hasher, aggregation.verifier_requires_phase30_manifest);
    phase29_update_bool(&mut hasher, aggregation.verifier_embeds_expected_rows);
    phase44d_finalize_hash(
        hasher,
        "Phase 44D recursive-verifier public-output aggregation",
    )
}

#[cfg(feature = "stwo-backend")]
pub fn phase44d_prepare_recursive_verifier_public_output_aggregation(
    handoffs: &[Phase44DRecursiveVerifierPublicOutputHandoff],
) -> Result<Phase44DRecursiveVerifierPublicOutputAggregation> {
    let first = handoffs.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation requires at least one handoff"
                .to_string(),
        )
    })?;
    let mut total_steps = 0usize;
    let mut handoff_commitments = Vec::with_capacity(handoffs.len());
    let mut source_chain_public_output_boundary_commitments = Vec::with_capacity(handoffs.len());
    let mut compact_envelope_commitments = Vec::with_capacity(handoffs.len());
    let mut terminal_boundary_logup_closure_commitments = Vec::with_capacity(handoffs.len());
    for (index, handoff) in handoffs.iter().enumerate() {
        verify_phase44d_recursive_verifier_public_output_handoff(handoff)?;
        if handoff.proof_backend != first.proof_backend
            || handoff.verifier_harness != first.verifier_harness
            || handoff.proof_backend_version != first.proof_backend_version
            || handoff.statement_version != first.statement_version
            || handoff.compact_claim_version != first.compact_claim_version
            || handoff.source_chain_public_output_boundary_version
                != first.source_chain_public_output_boundary_version
            || handoff.source_surface_version != first.source_surface_version
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44D recursive-verifier public-output aggregation handoff {index} has incompatible verifier header"
            )));
        }
        total_steps += handoff.total_steps;
        handoff_commitments.push(handoff.handoff_commitment.clone());
        source_chain_public_output_boundary_commitments.push(
            handoff
                .source_chain_public_output_boundary_commitment
                .clone(),
        );
        compact_envelope_commitments.push(handoff.compact_envelope_commitment.clone());
        terminal_boundary_logup_closure_commitments
            .push(handoff.terminal_boundary_logup_closure_commitment.clone());
    }
    let handoff_list_commitment =
        phase44d_commit_recursive_verifier_handoff_list(&handoff_commitments)?;
    let mut aggregation = Phase44DRecursiveVerifierPublicOutputAggregation {
        proof_backend: first.proof_backend.clone(),
        aggregation_version: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_VERSION_PHASE44D
            .to_string(),
        semantic_scope: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_SCOPE_PHASE44D
            .to_string(),
        verifier_harness: first.verifier_harness.clone(),
        proof_backend_version: first.proof_backend_version.clone(),
        statement_version: first.statement_version.clone(),
        handoff_count: handoffs.len(),
        total_steps,
        handoff_commitments,
        source_chain_public_output_boundary_commitments,
        compact_envelope_commitments,
        terminal_boundary_logup_closure_commitments,
        handoff_list_commitment,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        verifier_requires_phase43_trace: false,
        verifier_requires_phase30_manifest: false,
        verifier_embeds_expected_rows: false,
        verifier_side_complexity: STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_COMPLEXITY_PHASE44D
            .to_string(),
        aggregation_commitment: String::new(),
    };
    aggregation.aggregation_commitment =
        commit_phase44d_recursive_verifier_public_output_aggregation(&aggregation)?;
    verify_phase44d_recursive_verifier_public_output_aggregation(&aggregation)?;
    Ok(aggregation)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase44d_recursive_verifier_public_output_aggregation(
    aggregation: &Phase44DRecursiveVerifierPublicOutputAggregation,
) -> Result<()> {
    if aggregation.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D recursive-verifier public-output aggregation requires `stwo` backend, got `{}`",
            aggregation.proof_backend
        )));
    }
    if aggregation.aggregation_version
        != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation version drift".to_string(),
        ));
    }
    if aggregation.semantic_scope
        != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_SCOPE_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation scope drift".to_string(),
        ));
    }
    if aggregation.verifier_harness != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_KIND_PHASE44D {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation harness drift".to_string(),
        ));
    }
    if aggregation.recursive_verification_claimed || aggregation.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation must not claim recursive verification or cryptographic compression"
                .to_string(),
        ));
    }
    if aggregation.verifier_requires_phase43_trace
        || aggregation.verifier_requires_phase30_manifest
        || aggregation.verifier_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation must remain boundary-width and must not require full trace, Phase30 manifest, or expected rows"
                .to_string(),
        ));
    }
    if aggregation.verifier_side_complexity
        != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_COMPLEXITY_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation complexity drift".to_string(),
        ));
    }
    if aggregation.handoff_count == 0
        || aggregation.handoff_count != aggregation.handoff_commitments.len()
        || aggregation.handoff_count
            != aggregation
                .source_chain_public_output_boundary_commitments
                .len()
        || aggregation.handoff_count != aggregation.compact_envelope_commitments.len()
        || aggregation.handoff_count
            != aggregation
                .terminal_boundary_logup_closure_commitments
                .len()
        || aggregation.total_steps == 0
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation has inconsistent counts"
                .to_string(),
        ));
    }
    for (label, values) in [
        (
            "handoff_commitments",
            aggregation.handoff_commitments.as_slice(),
        ),
        (
            "source_chain_public_output_boundary_commitments",
            aggregation
                .source_chain_public_output_boundary_commitments
                .as_slice(),
        ),
        (
            "compact_envelope_commitments",
            aggregation.compact_envelope_commitments.as_slice(),
        ),
        (
            "terminal_boundary_logup_closure_commitments",
            aggregation
                .terminal_boundary_logup_closure_commitments
                .as_slice(),
        ),
    ] {
        for (index, value) in values.iter().enumerate() {
            phase43_require_hash32(&format!("{label}[{index}]"), value)?;
        }
    }
    phase43_require_hash32(
        "handoff_list_commitment",
        &aggregation.handoff_list_commitment,
    )?;
    phase43_require_hash32(
        "aggregation_commitment",
        &aggregation.aggregation_commitment,
    )?;
    let expected_list =
        phase44d_commit_recursive_verifier_handoff_list(&aggregation.handoff_commitments)?;
    if aggregation.handoff_list_commitment != expected_list {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation handoff list commitment does not match handoff commitments"
                .to_string(),
        ));
    }
    let expected = commit_phase44d_recursive_verifier_public_output_aggregation(aggregation)?;
    if aggregation.aggregation_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 44D recursive-verifier public-output aggregation commitment does not match aggregation fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase45_recursive_verifier_public_inputs(
    lanes: &[Phase45RecursiveVerifierPublicInputLane],
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 45 recursive-verifier public-input hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase45-recursive-verifier-public-inputs");
    phase29_update_usize(&mut hasher, lanes.len());
    for lane in lanes {
        phase29_update_usize(&mut hasher, lane.index);
        phase29_update_len_prefixed(&mut hasher, lane.label.as_bytes());
        phase29_update_len_prefixed(&mut hasher, lane.value_kind.as_bytes());
        phase29_update_len_prefixed(&mut hasher, lane.value.as_bytes());
    }
    phase44d_finalize_hash(hasher, "Phase 45 recursive-verifier public inputs")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase45_recursive_verifier_public_input_bridge(
    bridge: &Phase45RecursiveVerifierPublicInputBridge,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 45 recursive-verifier public-input bridge hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase45-recursive-verifier-public-input-bridge",
    );
    phase29_update_len_prefixed(&mut hasher, bridge.proof_backend.to_string().as_bytes());
    for part in [
        bridge.bridge_version.as_bytes(),
        bridge.semantic_scope.as_bytes(),
        bridge.verifier_harness.as_bytes(),
        bridge.handoff_version.as_bytes(),
        bridge
            .source_chain_public_output_boundary_version
            .as_bytes(),
        bridge.terminal_boundary_logup_closure_version.as_bytes(),
        bridge.handoff_commitment.as_bytes(),
        bridge
            .source_chain_public_output_boundary_commitment
            .as_bytes(),
        bridge.compact_envelope_commitment.as_bytes(),
        bridge.terminal_boundary_logup_closure_commitment.as_bytes(),
        bridge.ordered_public_inputs_commitment.as_bytes(),
        bridge.verifier_side_complexity.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, bridge.public_input_count);
    phase29_update_bool(&mut hasher, bridge.public_output_boundary_verified);
    phase29_update_bool(&mut hasher, bridge.compact_envelope_verified);
    phase29_update_bool(&mut hasher, bridge.terminal_boundary_logup_closure_verified);
    phase29_update_bool(&mut hasher, bridge.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, bridge.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, bridge.verifier_requires_phase43_trace);
    phase29_update_bool(&mut hasher, bridge.verifier_requires_phase30_manifest);
    phase29_update_bool(&mut hasher, bridge.verifier_embeds_expected_rows);
    phase44d_finalize_hash(hasher, "Phase 45 recursive-verifier public-input bridge")
}

#[cfg(feature = "stwo-backend")]
pub fn phase45_prepare_recursive_verifier_public_input_bridge(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
) -> Result<Phase45RecursiveVerifierPublicInputBridge> {
    verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
        handoff,
        boundary,
        compact_envelope,
    )?;
    let source_claim = &boundary
        .source_emission_public_output
        .source_emission
        .source_claim;
    let terminal_boundary_logup_closure =
        derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(
            source_claim,
            compact_envelope,
        )?;
    if handoff.terminal_boundary_logup_closure_commitment
        != terminal_boundary_logup_closure.closure_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge handoff terminal LogUp closure commitment drift"
                .to_string(),
        ));
    }
    let compact_envelope_commitment = phase44d_commit_compact_envelope_reference(compact_envelope)?;
    let ordered_public_input_lanes = phase45_ordered_public_input_lanes(
        boundary,
        compact_envelope,
        handoff,
        &terminal_boundary_logup_closure,
    )?;
    let ordered_public_inputs_commitment =
        commit_phase45_recursive_verifier_public_inputs(&ordered_public_input_lanes)?;
    let mut bridge = Phase45RecursiveVerifierPublicInputBridge {
        proof_backend: handoff.proof_backend.clone(),
        bridge_version: STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_VERSION_PHASE45.to_string(),
        semantic_scope: STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_SCOPE_PHASE45.to_string(),
        verifier_harness: handoff.verifier_harness.clone(),
        handoff_version: handoff.handoff_version.clone(),
        source_chain_public_output_boundary_version: boundary.boundary_version.clone(),
        terminal_boundary_logup_closure_version: terminal_boundary_logup_closure
            .closure_version
            .clone(),
        handoff_commitment: handoff.handoff_commitment.clone(),
        source_chain_public_output_boundary_commitment: boundary
            .source_chain_public_output_boundary_commitment
            .clone(),
        compact_envelope_commitment,
        terminal_boundary_logup_closure_commitment: terminal_boundary_logup_closure
            .closure_commitment
            .clone(),
        public_input_count: ordered_public_input_lanes.len(),
        ordered_public_input_lanes,
        ordered_public_inputs_commitment,
        public_output_boundary_verified: true,
        compact_envelope_verified: true,
        terminal_boundary_logup_closure_verified: true,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        verifier_requires_phase43_trace: false,
        verifier_requires_phase30_manifest: false,
        verifier_embeds_expected_rows: false,
        verifier_side_complexity: STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_COMPLEXITY_PHASE45
            .to_string(),
        bridge_commitment: String::new(),
    };
    bridge.bridge_commitment = commit_phase45_recursive_verifier_public_input_bridge(&bridge)?;
    verify_phase45_recursive_verifier_public_input_bridge(&bridge)?;
    Ok(bridge)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase45_recursive_verifier_public_input_bridge(
    bridge: &Phase45RecursiveVerifierPublicInputBridge,
) -> Result<()> {
    if bridge.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge requires `stwo` backend".to_string(),
        ));
    }
    if bridge.bridge_version != STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_VERSION_PHASE45 {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge version drift".to_string(),
        ));
    }
    if bridge.semantic_scope != STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_SCOPE_PHASE45 {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge semantic scope drift".to_string(),
        ));
    }
    if bridge.handoff_version != STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_VERSION_PHASE44D {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge handoff version drift".to_string(),
        ));
    }
    if bridge.source_chain_public_output_boundary_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge source boundary version drift".to_string(),
        ));
    }
    if bridge.terminal_boundary_logup_closure_version
        != STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_LOGUP_CLOSURE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge terminal LogUp closure version drift".to_string(),
        ));
    }
    if !bridge.public_output_boundary_verified
        || !bridge.compact_envelope_verified
        || !bridge.terminal_boundary_logup_closure_verified
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge must carry verified boundary, compact envelope, and terminal LogUp closure"
                .to_string(),
        ));
    }
    if bridge.recursive_verification_claimed || bridge.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge must not claim recursive verification or compression"
                .to_string(),
        ));
    }
    if bridge.verifier_requires_phase43_trace
        || bridge.verifier_requires_phase30_manifest
        || bridge.verifier_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge must remain boundary-width and must not require full replay inputs"
                .to_string(),
        ));
    }
    if bridge.verifier_side_complexity
        != STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_COMPLEXITY_PHASE45
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge complexity drift".to_string(),
        ));
    }
    if bridge.public_input_count != bridge.ordered_public_input_lanes.len()
        || bridge.public_input_count != PHASE45_PUBLIC_INPUT_LANE_LABELS.len()
    {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge has non-canonical public-input count".to_string(),
        ));
    }
    for (index, lane) in bridge.ordered_public_input_lanes.iter().enumerate() {
        if lane.index != index || lane.label != PHASE45_PUBLIC_INPUT_LANE_LABELS[index] {
            return Err(VmError::InvalidConfig(
                "Phase 45 public-input bridge lane order is not canonical".to_string(),
            ));
        }
        if lane.value_kind.is_empty() || lane.value.is_empty() {
            return Err(VmError::InvalidConfig(
                "Phase 45 public-input bridge lane carries an empty value".to_string(),
            ));
        }
    }
    for (label, value) in [
        ("handoff_commitment", bridge.handoff_commitment.as_str()),
        (
            "source_chain_public_output_boundary_commitment",
            bridge
                .source_chain_public_output_boundary_commitment
                .as_str(),
        ),
        (
            "compact_envelope_commitment",
            bridge.compact_envelope_commitment.as_str(),
        ),
        (
            "terminal_boundary_logup_closure_commitment",
            bridge.terminal_boundary_logup_closure_commitment.as_str(),
        ),
        (
            "ordered_public_inputs_commitment",
            bridge.ordered_public_inputs_commitment.as_str(),
        ),
        ("bridge_commitment", bridge.bridge_commitment.as_str()),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected_inputs =
        commit_phase45_recursive_verifier_public_inputs(&bridge.ordered_public_input_lanes)?;
    if bridge.ordered_public_inputs_commitment != expected_inputs {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge ordered public-input commitment drift".to_string(),
        ));
    }
    let expected_bridge = commit_phase45_recursive_verifier_public_input_bridge(bridge)?;
    if bridge.bridge_commitment != expected_bridge {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge commitment does not match bridge fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase45_recursive_verifier_public_input_bridge_against_sources(
    bridge: &Phase45RecursiveVerifierPublicInputBridge,
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
) -> Result<()> {
    verify_phase45_recursive_verifier_public_input_bridge(bridge)?;
    let expected = phase45_prepare_recursive_verifier_public_input_bridge(
        boundary,
        compact_envelope,
        handoff,
    )?;
    if bridge != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge does not match the verified Phase44D boundary, compact envelope, and handoff"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase46_stwo_proof_adapter_receipt(
    receipt: &Phase46StwoProofAdapterReceipt,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 46 Stwo proof-adapter receipt hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase46-stwo-proof-adapter-receipt");
    phase29_update_len_prefixed(&mut hasher, receipt.proof_backend.to_string().as_bytes());
    for part in [
        receipt.receipt_version.as_bytes(),
        receipt.semantic_scope.as_bytes(),
        receipt.verifier_harness.as_bytes(),
        receipt.bridge_version.as_bytes(),
        receipt.bridge_commitment.as_bytes(),
        receipt.ordered_public_inputs_commitment.as_bytes(),
        receipt.compact_envelope_commitment.as_bytes(),
        receipt.compact_claim_version.as_bytes(),
        receipt.compact_semantic_scope.as_bytes(),
        receipt.compact_verifier_inputs_version.as_bytes(),
        receipt.compact_verifier_inputs_commitment.as_bytes(),
        receipt.preprocessed_trace_root.as_bytes(),
        receipt.projection_trace_root.as_bytes(),
        receipt.interaction_trace_root.as_bytes(),
        receipt
            .terminal_boundary_interaction_claim_commitment
            .as_bytes(),
        receipt.verifier_side_complexity.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, receipt.proof_commitment_roots.len());
    for root in &receipt.proof_commitment_roots {
        phase29_update_len_prefixed(&mut hasher, root.as_bytes());
    }
    phase29_update_usize(&mut hasher, receipt.public_input_count);
    phase29_update_usize(&mut hasher, receipt.compact_proof_size_bytes);
    phase44d_update_u32_vec(&mut hasher, &receipt.preprocessed_trace_log_sizes);
    phase44d_update_u32_vec(&mut hasher, &receipt.projection_trace_log_sizes);
    phase44d_update_u32_vec(&mut hasher, &receipt.interaction_trace_log_sizes);
    hasher.update(&receipt.pcs_pow_bits.to_le_bytes());
    hasher.update(&receipt.pcs_fri_log_blowup_factor.to_le_bytes());
    phase29_update_usize(&mut hasher, receipt.pcs_fri_n_queries);
    hasher.update(&receipt.pcs_fri_log_last_layer_degree_bound.to_le_bytes());
    hasher.update(&receipt.pcs_fri_fold_step.to_le_bytes());
    phase29_update_bool(&mut hasher, receipt.pcs_lifting_log_size.is_some());
    if let Some(lifting_log_size) = receipt.pcs_lifting_log_size {
        hasher.update(&lifting_log_size.to_le_bytes());
    }
    phase29_update_usize(&mut hasher, receipt.proof_commitment_count);
    phase29_update_usize(&mut hasher, receipt.sampled_values_tree_count);
    phase29_update_usize(&mut hasher, receipt.decommitment_tree_count);
    phase29_update_usize(&mut hasher, receipt.queried_values_tree_count);
    hasher.update(&receipt.proof_of_work.to_le_bytes());
    phase44d_update_u32_vec(
        &mut hasher,
        &receipt.terminal_boundary_public_logup_sum_limbs,
    );
    phase44d_update_u32_vec(
        &mut hasher,
        &receipt.terminal_boundary_component_claimed_sum_limbs,
    );
    phase29_update_bool(&mut hasher, receipt.public_plus_component_sum_is_zero);
    phase29_update_bool(&mut hasher, receipt.phase45_bridge_verified);
    phase29_update_bool(&mut hasher, receipt.compact_envelope_verified);
    phase29_update_bool(&mut hasher, receipt.stwo_core_verify_succeeded);
    phase29_update_bool(&mut hasher, receipt.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, receipt.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, receipt.verifier_requires_phase43_trace);
    phase29_update_bool(&mut hasher, receipt.verifier_requires_phase30_manifest);
    phase29_update_bool(&mut hasher, receipt.verifier_embeds_expected_rows);
    phase44d_finalize_hash(hasher, "Phase 46 Stwo proof-adapter receipt")
}

#[cfg(feature = "stwo-backend")]
pub fn phase46_prepare_stwo_proof_adapter_receipt(
    bridge: &Phase45RecursiveVerifierPublicInputBridge,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase46StwoProofAdapterReceipt> {
    verify_phase45_recursive_verifier_public_input_bridge(bridge)?;
    let compact_envelope_commitment = phase44d_commit_compact_envelope_reference(compact_envelope)?;
    if bridge.compact_envelope_commitment != compact_envelope_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt bridge compact envelope commitment drift"
                .to_string(),
        ));
    }
    let verifier_inputs =
        derive_phase43_history_replay_projection_compact_verifier_inputs(compact_envelope)?;
    phase46_check_bridge_lane(
        bridge,
        "compact_projection_trace_root",
        &verifier_inputs.projection_trace_root,
    )?;
    phase46_check_bridge_lane(
        bridge,
        "compact_preprocessed_trace_root",
        &verifier_inputs.preprocessed_trace_root,
    )?;
    phase46_check_bridge_lane(
        bridge,
        "terminal_boundary_public_logup_sum_limbs",
        &phase45_join_u32_limbs(&verifier_inputs.terminal_boundary_public_logup_sum_limbs),
    )?;
    phase46_check_bridge_lane(
        bridge,
        "terminal_boundary_component_claimed_sum_limbs",
        &phase45_join_u32_limbs(
            &verifier_inputs
                .terminal_boundary_interaction_claim
                .claimed_sum_limbs,
        ),
    )?;
    let mut receipt = Phase46StwoProofAdapterReceipt {
        proof_backend: StarkProofBackend::Stwo,
        receipt_version: STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_VERSION_PHASE46.to_string(),
        semantic_scope: STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_SCOPE_PHASE46.to_string(),
        verifier_harness: bridge.verifier_harness.clone(),
        bridge_version: bridge.bridge_version.clone(),
        bridge_commitment: bridge.bridge_commitment.clone(),
        ordered_public_inputs_commitment: bridge.ordered_public_inputs_commitment.clone(),
        public_input_count: bridge.public_input_count,
        compact_envelope_commitment,
        compact_claim_version: compact_envelope.claim.claim_version.clone(),
        compact_semantic_scope: compact_envelope.claim.semantic_scope.clone(),
        compact_verifier_inputs_version: verifier_inputs.verifier_inputs_version.clone(),
        compact_verifier_inputs_commitment: verifier_inputs.verifier_inputs_commitment.clone(),
        compact_proof_size_bytes: compact_envelope.proof.len(),
        preprocessed_trace_root: verifier_inputs.preprocessed_trace_root.clone(),
        projection_trace_root: verifier_inputs.projection_trace_root.clone(),
        interaction_trace_root: verifier_inputs.interaction_trace_root.clone(),
        proof_commitment_roots: verifier_inputs.proof_commitment_roots.clone(),
        preprocessed_trace_log_sizes: verifier_inputs.preprocessed_trace_log_sizes.clone(),
        projection_trace_log_sizes: verifier_inputs.projection_trace_log_sizes.clone(),
        interaction_trace_log_sizes: verifier_inputs.interaction_trace_log_sizes.clone(),
        pcs_pow_bits: verifier_inputs.pcs_pow_bits,
        pcs_fri_log_blowup_factor: verifier_inputs.pcs_fri_log_blowup_factor,
        pcs_fri_n_queries: verifier_inputs.pcs_fri_n_queries,
        pcs_fri_log_last_layer_degree_bound: verifier_inputs.pcs_fri_log_last_layer_degree_bound,
        pcs_fri_fold_step: verifier_inputs.pcs_fri_fold_step,
        pcs_lifting_log_size: verifier_inputs.pcs_lifting_log_size,
        proof_commitment_count: verifier_inputs.proof_commitment_count,
        sampled_values_tree_count: verifier_inputs.sampled_values_tree_count,
        decommitment_tree_count: verifier_inputs.decommitment_tree_count,
        queried_values_tree_count: verifier_inputs.queried_values_tree_count,
        proof_of_work: verifier_inputs.proof_of_work,
        terminal_boundary_interaction_claim_commitment: verifier_inputs
            .terminal_boundary_interaction_claim
            .interaction_claim_commitment
            .clone(),
        terminal_boundary_public_logup_sum_limbs: verifier_inputs
            .terminal_boundary_public_logup_sum_limbs
            .clone(),
        terminal_boundary_component_claimed_sum_limbs: verifier_inputs
            .terminal_boundary_interaction_claim
            .claimed_sum_limbs
            .clone(),
        public_plus_component_sum_is_zero: verifier_inputs.public_plus_component_sum_is_zero,
        phase45_bridge_verified: true,
        compact_envelope_verified: true,
        stwo_core_verify_succeeded: verifier_inputs.stwo_core_verify_succeeded,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        verifier_requires_phase43_trace: false,
        verifier_requires_phase30_manifest: false,
        verifier_embeds_expected_rows: false,
        verifier_side_complexity: STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_COMPLEXITY_PHASE46
            .to_string(),
        adapter_receipt_commitment: String::new(),
    };
    receipt.adapter_receipt_commitment = commit_phase46_stwo_proof_adapter_receipt(&receipt)?;
    verify_phase46_stwo_proof_adapter_receipt(&receipt)?;
    Ok(receipt)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase46_stwo_proof_adapter_receipt(
    receipt: &Phase46StwoProofAdapterReceipt,
) -> Result<()> {
    if receipt.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt requires `stwo` backend".to_string(),
        ));
    }
    if receipt.receipt_version != STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_VERSION_PHASE46 {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt version drift".to_string(),
        ));
    }
    if receipt.semantic_scope != STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_SCOPE_PHASE46 {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt semantic scope drift".to_string(),
        ));
    }
    if receipt.bridge_version != STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_VERSION_PHASE45 {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt bridge version drift".to_string(),
        ));
    }
    if receipt.compact_claim_version != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44
        || receipt.compact_semantic_scope
            != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44
    {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt compact claim metadata drift".to_string(),
        ));
    }
    if receipt.compact_verifier_inputs_version
        != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_VERIFIER_INPUTS_VERSION_PHASE46
    {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt compact verifier-input version drift".to_string(),
        ));
    }
    if !receipt.phase45_bridge_verified
        || !receipt.compact_envelope_verified
        || !receipt.stwo_core_verify_succeeded
        || !receipt.public_plus_component_sum_is_zero
    {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt must carry verified bridge, compact envelope, Stwo proof, and LogUp closure"
                .to_string(),
        ));
    }
    if receipt.recursive_verification_claimed || receipt.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt must not claim recursive verification or cryptographic compression"
                .to_string(),
        ));
    }
    if receipt.verifier_requires_phase43_trace
        || receipt.verifier_requires_phase30_manifest
        || receipt.verifier_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt must not reintroduce replay inputs".to_string(),
        ));
    }
    if receipt.verifier_side_complexity
        != STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_COMPLEXITY_PHASE46
    {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt complexity drift".to_string(),
        ));
    }
    for (label, value) in [
        ("bridge_commitment", receipt.bridge_commitment.as_str()),
        (
            "ordered_public_inputs_commitment",
            receipt.ordered_public_inputs_commitment.as_str(),
        ),
        (
            "compact_envelope_commitment",
            receipt.compact_envelope_commitment.as_str(),
        ),
        (
            "compact_verifier_inputs_commitment",
            receipt.compact_verifier_inputs_commitment.as_str(),
        ),
        (
            "preprocessed_trace_root",
            receipt.preprocessed_trace_root.as_str(),
        ),
        (
            "projection_trace_root",
            receipt.projection_trace_root.as_str(),
        ),
        (
            "interaction_trace_root",
            receipt.interaction_trace_root.as_str(),
        ),
        (
            "terminal_boundary_interaction_claim_commitment",
            receipt
                .terminal_boundary_interaction_claim_commitment
                .as_str(),
        ),
        (
            "adapter_receipt_commitment",
            receipt.adapter_receipt_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if receipt.proof_commitment_count < 3
        || receipt.proof_commitment_roots.len() != receipt.proof_commitment_count
        || receipt.compact_proof_size_bytes == 0
        || receipt.preprocessed_trace_log_sizes.is_empty()
        || receipt.projection_trace_log_sizes.is_empty()
        || receipt.interaction_trace_log_sizes.is_empty()
    {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt carries an empty verifier-input shape".to_string(),
        ));
    }
    for (index, root) in receipt.proof_commitment_roots.iter().enumerate() {
        phase43_require_hash32(&format!("proof_commitment_roots[{index}]"), root)?;
    }
    let public_sum = phase44d_secure_field_from_limbs(
        "phase46_terminal_boundary_public_logup_sum_limbs",
        &receipt.terminal_boundary_public_logup_sum_limbs,
    )?;
    let component_sum = phase44d_secure_field_from_limbs(
        "phase46_terminal_boundary_component_claimed_sum_limbs",
        &receipt.terminal_boundary_component_claimed_sum_limbs,
    )?;
    if public_sum + component_sum != SecureField::zero() {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt terminal LogUp public sum does not cancel component claimed sum"
                .to_string(),
        ));
    }
    let expected = commit_phase46_stwo_proof_adapter_receipt(receipt)?;
    if receipt.adapter_receipt_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt commitment does not match receipt fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase46_stwo_proof_adapter_receipt_against_sources(
    receipt: &Phase46StwoProofAdapterReceipt,
    bridge: &Phase45RecursiveVerifierPublicInputBridge,
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
) -> Result<()> {
    verify_phase45_recursive_verifier_public_input_bridge_against_sources(
        bridge,
        boundary,
        compact_envelope,
        handoff,
    )?;
    let expected = phase46_prepare_stwo_proof_adapter_receipt(bridge, compact_envelope)?;
    if receipt != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 46 Stwo proof-adapter receipt does not match verified Phase45 bridge and compact Stwo envelope"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase47_proof_commitment_roots(roots: &[String]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 47 proof commitment roots hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase47-proof-commitment-roots");
    phase29_update_usize(&mut hasher, roots.len());
    for (index, root) in roots.iter().enumerate() {
        phase43_require_hash32(&format!("phase47_proof_commitment_roots[{index}]"), root)?;
        phase29_update_len_prefixed(&mut hasher, root.as_bytes());
    }
    phase44d_finalize_hash(hasher, "Phase 47 proof commitment roots")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase47_recursive_verifier_wrapper_candidate(
    candidate: &Phase47RecursiveVerifierWrapperCandidate,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 47 recursive-verifier wrapper candidate hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase47-recursive-verifier-wrapper-candidate");
    phase29_update_len_prefixed(&mut hasher, candidate.proof_backend.to_string().as_bytes());
    for part in [
        candidate.candidate_version.as_bytes(),
        candidate.semantic_scope.as_bytes(),
        candidate.verifier_harness.as_bytes(),
        candidate.adapter_receipt_version.as_bytes(),
        candidate.adapter_receipt_commitment.as_bytes(),
        candidate.compact_verifier_inputs_commitment.as_bytes(),
        candidate.compact_envelope_commitment.as_bytes(),
        candidate.bridge_commitment.as_bytes(),
        candidate.ordered_public_inputs_commitment.as_bytes(),
        candidate.proof_commitment_roots_commitment.as_bytes(),
        candidate.verifier_side_complexity.as_bytes(),
        candidate.decision.as_bytes(),
        candidate.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, candidate.proof_commitment_roots.len());
    for root in &candidate.proof_commitment_roots {
        phase29_update_len_prefixed(&mut hasher, root.as_bytes());
    }
    phase29_update_usize(&mut hasher, candidate.proof_commitment_count);
    phase29_update_usize(&mut hasher, candidate.compact_proof_size_bytes);
    phase29_update_usize(&mut hasher, candidate.public_input_count);
    phase29_update_usize(&mut hasher, candidate.verifier_surface_unit_count);
    phase29_update_usize(&mut hasher, candidate.preprocessed_trace_log_size_count);
    phase29_update_usize(&mut hasher, candidate.projection_trace_log_size_count);
    phase29_update_usize(&mut hasher, candidate.interaction_trace_log_size_count);
    phase29_update_usize(&mut hasher, candidate.terminal_boundary_logup_limb_count);
    phase29_update_bool(&mut hasher, candidate.phase46_receipt_verified);
    phase29_update_bool(&mut hasher, candidate.stwo_core_verify_succeeded);
    phase29_update_bool(&mut hasher, candidate.terminal_logup_closed);
    phase29_update_bool(&mut hasher, candidate.consumes_phase46_receipt_only);
    phase29_update_bool(&mut hasher, candidate.wrapper_requires_phase43_trace);
    phase29_update_bool(&mut hasher, candidate.wrapper_requires_phase30_manifest);
    phase29_update_bool(&mut hasher, candidate.wrapper_embeds_expected_rows);
    phase29_update_bool(&mut hasher, candidate.recursive_proof_available);
    phase29_update_bool(&mut hasher, candidate.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, candidate.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 47 recursive-verifier wrapper candidate")
}

#[cfg(feature = "stwo-backend")]
pub fn phase47_prepare_recursive_verifier_wrapper_candidate(
    receipt: &Phase46StwoProofAdapterReceipt,
) -> Result<Phase47RecursiveVerifierWrapperCandidate> {
    verify_phase46_stwo_proof_adapter_receipt(receipt)?;
    let proof_commitment_roots_commitment =
        commit_phase47_proof_commitment_roots(&receipt.proof_commitment_roots)?;
    let terminal_boundary_logup_limb_count = receipt.terminal_boundary_public_logup_sum_limbs.len()
        + receipt.terminal_boundary_component_claimed_sum_limbs.len();
    let verifier_surface_unit_count = receipt.public_input_count
        + receipt.proof_commitment_roots.len()
        + receipt.preprocessed_trace_log_sizes.len()
        + receipt.projection_trace_log_sizes.len()
        + receipt.interaction_trace_log_sizes.len()
        + terminal_boundary_logup_limb_count;
    let mut candidate = Phase47RecursiveVerifierWrapperCandidate {
        proof_backend: StarkProofBackend::Stwo,
        candidate_version: STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_VERSION_PHASE47.to_string(),
        semantic_scope: STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_SCOPE_PHASE47.to_string(),
        verifier_harness: receipt.verifier_harness.clone(),
        adapter_receipt_version: receipt.receipt_version.clone(),
        adapter_receipt_commitment: receipt.adapter_receipt_commitment.clone(),
        compact_verifier_inputs_commitment: receipt.compact_verifier_inputs_commitment.clone(),
        compact_envelope_commitment: receipt.compact_envelope_commitment.clone(),
        bridge_commitment: receipt.bridge_commitment.clone(),
        ordered_public_inputs_commitment: receipt.ordered_public_inputs_commitment.clone(),
        proof_commitment_roots_commitment,
        proof_commitment_roots: receipt.proof_commitment_roots.clone(),
        proof_commitment_count: receipt.proof_commitment_count,
        compact_proof_size_bytes: receipt.compact_proof_size_bytes,
        public_input_count: receipt.public_input_count,
        verifier_surface_unit_count,
        preprocessed_trace_log_size_count: receipt.preprocessed_trace_log_sizes.len(),
        projection_trace_log_size_count: receipt.projection_trace_log_sizes.len(),
        interaction_trace_log_size_count: receipt.interaction_trace_log_sizes.len(),
        terminal_boundary_logup_limb_count,
        phase46_receipt_verified: true,
        stwo_core_verify_succeeded: receipt.stwo_core_verify_succeeded,
        terminal_logup_closed: receipt.public_plus_component_sum_is_zero,
        consumes_phase46_receipt_only: true,
        wrapper_requires_phase43_trace: false,
        wrapper_requires_phase30_manifest: false,
        wrapper_embeds_expected_rows: false,
        recursive_proof_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        verifier_side_complexity: STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_COMPLEXITY_PHASE47
            .to_string(),
        decision: STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_DECISION_PHASE47.to_string(),
        required_next_step: STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_NEXT_STEP_PHASE47.to_string(),
        candidate_commitment: String::new(),
    };
    candidate.candidate_commitment =
        commit_phase47_recursive_verifier_wrapper_candidate(&candidate)?;
    verify_phase47_recursive_verifier_wrapper_candidate(&candidate)?;
    Ok(candidate)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase47_recursive_verifier_wrapper_candidate(
    candidate: &Phase47RecursiveVerifierWrapperCandidate,
) -> Result<()> {
    if candidate.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate requires `stwo` backend".to_string(),
        ));
    }
    if candidate.candidate_version != STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_VERSION_PHASE47 {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate version drift".to_string(),
        ));
    }
    if candidate.semantic_scope != STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_SCOPE_PHASE47 {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate semantic scope drift".to_string(),
        ));
    }
    if candidate.adapter_receipt_version
        != STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_VERSION_PHASE46
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate adapter receipt version drift"
                .to_string(),
        ));
    }
    if !candidate.phase46_receipt_verified
        || !candidate.stwo_core_verify_succeeded
        || !candidate.terminal_logup_closed
        || !candidate.consumes_phase46_receipt_only
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate must carry verified Phase46, Stwo, LogUp, and receipt-only flags"
                .to_string(),
        ));
    }
    if candidate.wrapper_requires_phase43_trace
        || candidate.wrapper_requires_phase30_manifest
        || candidate.wrapper_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate must not reintroduce replay inputs"
                .to_string(),
        ));
    }
    if candidate.recursive_proof_available
        || candidate.recursive_verification_claimed
        || candidate.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate must not claim a recursive proof or cryptographic compression"
                .to_string(),
        ));
    }
    if candidate.verifier_side_complexity
        != STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_COMPLEXITY_PHASE47
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate complexity drift".to_string(),
        ));
    }
    if candidate.decision != STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_DECISION_PHASE47
        || candidate.required_next_step
            != STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_NEXT_STEP_PHASE47
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate decision drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "adapter_receipt_commitment",
            candidate.adapter_receipt_commitment.as_str(),
        ),
        (
            "compact_verifier_inputs_commitment",
            candidate.compact_verifier_inputs_commitment.as_str(),
        ),
        (
            "compact_envelope_commitment",
            candidate.compact_envelope_commitment.as_str(),
        ),
        ("bridge_commitment", candidate.bridge_commitment.as_str()),
        (
            "ordered_public_inputs_commitment",
            candidate.ordered_public_inputs_commitment.as_str(),
        ),
        (
            "proof_commitment_roots_commitment",
            candidate.proof_commitment_roots_commitment.as_str(),
        ),
        (
            "candidate_commitment",
            candidate.candidate_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if candidate.proof_commitment_count < 3
        || candidate.proof_commitment_roots.len() != candidate.proof_commitment_count
        || candidate.compact_proof_size_bytes == 0
        || candidate.public_input_count == 0
        || candidate.preprocessed_trace_log_size_count == 0
        || candidate.projection_trace_log_size_count == 0
        || candidate.interaction_trace_log_size_count == 0
        || candidate.terminal_boundary_logup_limb_count == 0
    {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate carries an empty verifier surface"
                .to_string(),
        ));
    }
    let expected_roots_commitment =
        commit_phase47_proof_commitment_roots(&candidate.proof_commitment_roots)?;
    if candidate.proof_commitment_roots_commitment != expected_roots_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate proof commitment roots commitment drift"
                .to_string(),
        ));
    }
    let expected_surface_unit_count = candidate.public_input_count
        + candidate.proof_commitment_roots.len()
        + candidate.preprocessed_trace_log_size_count
        + candidate.projection_trace_log_size_count
        + candidate.interaction_trace_log_size_count
        + candidate.terminal_boundary_logup_limb_count;
    if candidate.verifier_surface_unit_count != expected_surface_unit_count {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate verifier surface unit count drift"
                .to_string(),
        ));
    }
    let expected = commit_phase47_recursive_verifier_wrapper_candidate(candidate)?;
    if candidate.candidate_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate commitment does not match candidate fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase47_recursive_verifier_wrapper_candidate_against_phase46(
    candidate: &Phase47RecursiveVerifierWrapperCandidate,
    receipt: &Phase46StwoProofAdapterReceipt,
) -> Result<()> {
    verify_phase46_stwo_proof_adapter_receipt(receipt)?;
    let expected = phase47_prepare_recursive_verifier_wrapper_candidate(receipt)?;
    if candidate != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 47 recursive-verifier wrapper candidate does not match verified Phase46 receipt"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase48_recursive_proof_wrapper_attempt(
    attempt: &Phase48RecursiveProofWrapperAttempt,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 48 recursive proof-wrapper attempt hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase48-recursive-proof-wrapper-attempt");
    phase29_update_len_prefixed(&mut hasher, attempt.proof_backend.to_string().as_bytes());
    for part in [
        attempt.attempt_version.as_bytes(),
        attempt.semantic_scope.as_bytes(),
        attempt.verifier_harness.as_bytes(),
        attempt.phase47_candidate_version.as_bytes(),
        attempt.phase47_candidate_commitment.as_bytes(),
        attempt.phase46_adapter_receipt_commitment.as_bytes(),
        attempt.compact_verifier_inputs_commitment.as_bytes(),
        attempt.compact_envelope_commitment.as_bytes(),
        attempt.compact_proof_channel.as_bytes(),
        attempt.recursive_verifier_channel.as_bytes(),
        attempt.decision.as_bytes(),
        attempt.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_bool(&mut hasher, attempt.phase47_candidate_verified);
    phase29_update_bool(&mut hasher, attempt.local_stwo_core_verifier_detected);
    phase29_update_bool(&mut hasher, attempt.local_stwo_cairo_verifier_core_detected);
    phase29_update_bool(&mut hasher, attempt.local_stwo_cairo_air_verifier_detected);
    phase29_update_bool(
        &mut hasher,
        attempt.local_phase43_projection_cairo_air_detected,
    );
    phase29_update_bool(
        &mut hasher,
        attempt.channel_mismatch_requires_reproving_or_adapter,
    );
    phase29_update_bool(&mut hasher, attempt.actual_recursive_wrapper_available);
    phase29_update_bool(&mut hasher, attempt.recursive_proof_constructed);
    phase29_update_bool(&mut hasher, attempt.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, attempt.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, attempt.wrapper_requires_phase43_trace);
    phase29_update_bool(&mut hasher, attempt.wrapper_requires_phase30_manifest);
    phase29_update_bool(&mut hasher, attempt.wrapper_embeds_expected_rows);
    phase29_update_usize(&mut hasher, attempt.blocking_reasons.len());
    for reason in &attempt.blocking_reasons {
        phase29_update_len_prefixed(&mut hasher, reason.as_bytes());
    }
    phase44d_finalize_hash(hasher, "Phase 48 recursive proof-wrapper attempt")
}

#[cfg(feature = "stwo-backend")]
pub fn phase48_prepare_recursive_proof_wrapper_attempt(
    candidate: &Phase47RecursiveVerifierWrapperCandidate,
) -> Result<Phase48RecursiveProofWrapperAttempt> {
    verify_phase47_recursive_verifier_wrapper_candidate(candidate)?;
    let blocking_reasons = vec![
        "local Stwo Rust verifier is out-of-circuit and verifies a proof directly, not recursively"
            .to_string(),
        "local stwo_cairo_verifier exposes generic verifier core and Cairo AIR, but no Phase43 projection AIR verifier"
            .to_string(),
        "current compact VM proof is Blake2sM31 while the recursive-friendly Stwo-Cairo prover path is Poseidon252-oriented"
            .to_string(),
    ];
    let mut attempt = Phase48RecursiveProofWrapperAttempt {
        proof_backend: StarkProofBackend::Stwo,
        attempt_version: STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_VERSION_PHASE48.to_string(),
        semantic_scope: STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_SCOPE_PHASE48.to_string(),
        verifier_harness: candidate.verifier_harness.clone(),
        phase47_candidate_version: candidate.candidate_version.clone(),
        phase47_candidate_commitment: candidate.candidate_commitment.clone(),
        phase46_adapter_receipt_commitment: candidate.adapter_receipt_commitment.clone(),
        compact_verifier_inputs_commitment: candidate.compact_verifier_inputs_commitment.clone(),
        compact_envelope_commitment: candidate.compact_envelope_commitment.clone(),
        phase47_candidate_verified: true,
        local_stwo_core_verifier_detected: true,
        local_stwo_cairo_verifier_core_detected: true,
        local_stwo_cairo_air_verifier_detected: true,
        local_phase43_projection_cairo_air_detected: false,
        compact_proof_channel: STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_COMPACT_PROOF_CHANNEL_PHASE48
            .to_string(),
        recursive_verifier_channel: STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_RECURSIVE_CHANNEL_PHASE48
            .to_string(),
        channel_mismatch_requires_reproving_or_adapter: true,
        actual_recursive_wrapper_available: false,
        recursive_proof_constructed: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        wrapper_requires_phase43_trace: false,
        wrapper_requires_phase30_manifest: false,
        wrapper_embeds_expected_rows: false,
        blocking_reasons,
        decision: STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_DECISION_PHASE48.to_string(),
        required_next_step: STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_NEXT_STEP_PHASE48.to_string(),
        attempt_commitment: String::new(),
    };
    attempt.attempt_commitment = commit_phase48_recursive_proof_wrapper_attempt(&attempt)?;
    verify_phase48_recursive_proof_wrapper_attempt(&attempt)?;
    Ok(attempt)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase48_recursive_proof_wrapper_attempt(
    attempt: &Phase48RecursiveProofWrapperAttempt,
) -> Result<()> {
    if attempt.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt requires `stwo` backend".to_string(),
        ));
    }
    if attempt.attempt_version != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_VERSION_PHASE48 {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt version drift".to_string(),
        ));
    }
    if attempt.semantic_scope != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_SCOPE_PHASE48 {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt semantic scope drift".to_string(),
        ));
    }
    if attempt.phase47_candidate_version
        != STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_VERSION_PHASE47
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt Phase47 candidate version drift".to_string(),
        ));
    }
    if !attempt.phase47_candidate_verified
        || !attempt.local_stwo_core_verifier_detected
        || !attempt.local_stwo_cairo_verifier_core_detected
        || !attempt.local_stwo_cairo_air_verifier_detected
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt requires verified Phase47 and detected Stwo verifier surfaces"
                .to_string(),
        ));
    }
    if attempt.local_phase43_projection_cairo_air_detected
        || attempt.actual_recursive_wrapper_available
        || attempt.recursive_proof_constructed
        || attempt.recursive_verification_claimed
        || attempt.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt must not claim unavailable recursive compression"
                .to_string(),
        ));
    }
    if attempt.wrapper_requires_phase43_trace
        || attempt.wrapper_requires_phase30_manifest
        || attempt.wrapper_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt must not reintroduce replay inputs"
                .to_string(),
        ));
    }
    if attempt.compact_proof_channel
        != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_COMPACT_PROOF_CHANNEL_PHASE48
        || attempt.recursive_verifier_channel
            != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_RECURSIVE_CHANNEL_PHASE48
        || !attempt.channel_mismatch_requires_reproving_or_adapter
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt channel compatibility drift".to_string(),
        ));
    }
    if attempt.decision != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_DECISION_PHASE48
        || attempt.required_next_step != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_NEXT_STEP_PHASE48
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt decision drift".to_string(),
        ));
    }
    if attempt.blocking_reasons.len() < 3
        || !attempt
            .blocking_reasons
            .iter()
            .any(|reason| reason.contains("Phase43 projection AIR verifier"))
    {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt must record the missing Phase43 Cairo AIR blocker"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase47_candidate_commitment",
            attempt.phase47_candidate_commitment.as_str(),
        ),
        (
            "phase46_adapter_receipt_commitment",
            attempt.phase46_adapter_receipt_commitment.as_str(),
        ),
        (
            "compact_verifier_inputs_commitment",
            attempt.compact_verifier_inputs_commitment.as_str(),
        ),
        (
            "compact_envelope_commitment",
            attempt.compact_envelope_commitment.as_str(),
        ),
        ("attempt_commitment", attempt.attempt_commitment.as_str()),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected = commit_phase48_recursive_proof_wrapper_attempt(attempt)?;
    if attempt.attempt_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt commitment does not match attempt fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase48_recursive_proof_wrapper_attempt_against_phase47(
    attempt: &Phase48RecursiveProofWrapperAttempt,
    candidate: &Phase47RecursiveVerifierWrapperCandidate,
) -> Result<()> {
    verify_phase47_recursive_verifier_wrapper_candidate(candidate)?;
    let expected = phase48_prepare_recursive_proof_wrapper_attempt(candidate)?;
    if attempt != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 48 recursive proof-wrapper attempt does not match verified Phase47 candidate"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase49_layerwise_tensor_claim_propagation_contract(
    contract: &Phase49LayerwiseTensorClaimPropagationContract,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 49 layerwise tensor-claim propagation contract hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase49-layerwise-tensor-claim-propagation-contract",
    );
    phase29_update_len_prefixed(&mut hasher, contract.proof_backend.to_string().as_bytes());
    for part in [
        contract.contract_version.as_bytes(),
        contract.semantic_scope.as_bytes(),
        contract.source_phase48_attempt_version.as_bytes(),
        contract.source_phase48_attempt_commitment.as_bytes(),
        contract.source_phase48_decision.as_bytes(),
        contract.source_phase48_required_next_step.as_bytes(),
        contract.route_source.as_bytes(),
        contract.route_target.as_bytes(),
        contract.proof_backend_version.as_bytes(),
        contract.statement_version.as_bytes(),
        contract.claim_granularity.as_bytes(),
        contract.propagation_rule.as_bytes(),
        contract.composition_strategy.as_bytes(),
        contract.layer_count_bound_mode.as_bytes(),
        contract.tensor_commitment_scheme.as_bytes(),
        contract.layer_io_claim_object.as_bytes(),
        contract.attention_claim_object.as_bytes(),
        contract.mlp_claim_object.as_bytes(),
        contract.normalization_claim_object.as_bytes(),
        contract.residual_claim_object.as_bytes(),
        contract.composition_accumulator_object.as_bytes(),
        contract.verifier_side_complexity.as_bytes(),
        contract.decision.as_bytes(),
        contract.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, contract.input_tensor_width);
    phase29_update_usize(&mut hasher, contract.output_tensor_width);
    phase29_update_usize(&mut hasher, contract.attention_head_dim);
    phase29_update_bool(&mut hasher, contract.vm_manifest_route_blocked);
    phase29_update_bool(&mut hasher, contract.target_requires_full_vm_replay);
    phase29_update_bool(&mut hasher, contract.target_requires_phase43_trace);
    phase29_update_bool(&mut hasher, contract.target_requires_phase30_manifest);
    phase29_update_bool(
        &mut hasher,
        contract.target_requires_phase43_projection_cairo_air,
    );
    phase29_update_bool(&mut hasher, contract.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, contract.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, contract.actual_layerwise_proof_available);
    phase29_update_bool(&mut hasher, contract.compression_benchmark_available);
    phase44d_update_hash_vec(&mut hasher, &contract.required_components);
    phase44d_update_hash_vec(&mut hasher, &contract.open_blockers);
    phase44d_finalize_hash(
        hasher,
        "Phase 49 layerwise tensor-claim propagation contract",
    )
}

#[cfg(feature = "stwo-backend")]
pub fn phase49_prepare_layerwise_tensor_claim_propagation_contract(
    attempt: &Phase48RecursiveProofWrapperAttempt,
) -> Result<Phase49LayerwiseTensorClaimPropagationContract> {
    verify_phase48_recursive_proof_wrapper_attempt(attempt)?;
    let required_components = vec![
        "tensor_commitment_scheme".to_string(),
        "layer_io_claim".to_string(),
        "attention_relation_claim".to_string(),
        "gated_feed_forward_relation_claim".to_string(),
        "normalization_relation_claim_if_present".to_string(),
        "residual_relation_claim_if_present".to_string(),
        "ordered_layer_claim_composition_accumulator".to_string(),
    ];
    let open_blockers = vec![
        "select a field-compatible tensor commitment scheme for layer activations".to_string(),
        "define first-layer input/output claim fields and transcript order".to_string(),
        "define per-layer Stwo AIR or lookup relation for attention and gated feed-forward"
            .to_string(),
        "define ordered layer-claim composition accumulator and benchmark verifier complexity"
            .to_string(),
    ];
    let mut contract = Phase49LayerwiseTensorClaimPropagationContract {
        proof_backend: StarkProofBackend::Stwo,
        contract_version: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_VERSION_PHASE49.to_string(),
        semantic_scope: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_SCOPE_PHASE49.to_string(),
        source_phase48_attempt_version: attempt.attempt_version.clone(),
        source_phase48_attempt_commitment: attempt.attempt_commitment.clone(),
        source_phase48_decision: attempt.decision.clone(),
        source_phase48_required_next_step: attempt.required_next_step.clone(),
        vm_manifest_route_blocked: true,
        route_source: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_ROUTE_SOURCE_PHASE49.to_string(),
        route_target: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_ROUTE_TARGET_PHASE49.to_string(),
        proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
        claim_granularity: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_GRANULARITY_PHASE49.to_string(),
        propagation_rule: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_PROPAGATION_RULE_PHASE49.to_string(),
        composition_strategy: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_COMPOSITION_PHASE49.to_string(),
        input_tensor_width: INPUT_DIM,
        output_tensor_width: OUTPUT_DIM,
        attention_head_dim: 2,
        layer_count_bound_mode: "model_config_num_layers".to_string(),
        tensor_commitment_scheme: "pending_phase50_tensor_commitment_scheme".to_string(),
        layer_io_claim_object: "pending_phase50_layer_io_claim".to_string(),
        attention_claim_object: "pending_attention_relation_claim".to_string(),
        mlp_claim_object: "pending_gated_feed_forward_relation_claim".to_string(),
        normalization_claim_object: "pending_normalization_relation_claim_if_present".to_string(),
        residual_claim_object: "pending_residual_relation_claim_if_present".to_string(),
        composition_accumulator_object: "pending_ordered_layer_claim_accumulator".to_string(),
        target_requires_full_vm_replay: false,
        target_requires_phase43_trace: false,
        target_requires_phase30_manifest: false,
        target_requires_phase43_projection_cairo_air: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        actual_layerwise_proof_available: false,
        compression_benchmark_available: false,
        required_components,
        open_blockers,
        verifier_side_complexity: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_COMPLEXITY_PHASE49
            .to_string(),
        decision: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_DECISION_PHASE49.to_string(),
        required_next_step: STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_NEXT_STEP_PHASE49.to_string(),
        contract_commitment: String::new(),
    };
    contract.contract_commitment =
        commit_phase49_layerwise_tensor_claim_propagation_contract(&contract)?;
    verify_phase49_layerwise_tensor_claim_propagation_contract(&contract)?;
    Ok(contract)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase49_layerwise_tensor_claim_propagation_contract(
    contract: &Phase49LayerwiseTensorClaimPropagationContract,
) -> Result<()> {
    if contract.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract requires `stwo` backend".to_string(),
        ));
    }
    if contract.contract_version != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_VERSION_PHASE49 {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract version drift".to_string(),
        ));
    }
    if contract.semantic_scope != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_SCOPE_PHASE49 {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract semantic scope drift".to_string(),
        ));
    }
    if contract.source_phase48_attempt_version
        != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_VERSION_PHASE48
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract source Phase48 version drift".to_string(),
        ));
    }
    if !contract.vm_manifest_route_blocked
        || contract.source_phase48_decision != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_DECISION_PHASE48
        || contract.source_phase48_required_next_step
            != STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_NEXT_STEP_PHASE48
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract must be sourced from the Phase48 no-go decision"
                .to_string(),
        ));
    }
    if contract.route_source != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_ROUTE_SOURCE_PHASE49
        || contract.route_target != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_ROUTE_TARGET_PHASE49
        || contract.claim_granularity != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_GRANULARITY_PHASE49
        || contract.propagation_rule
            != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_PROPAGATION_RULE_PHASE49
        || contract.composition_strategy != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_COMPOSITION_PHASE49
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract route or propagation rule drift".to_string(),
        ));
    }
    if contract.input_tensor_width != INPUT_DIM
        || contract.output_tensor_width != OUTPUT_DIM
        || contract.attention_head_dim != 2
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract VM tensor surface drift".to_string(),
        ));
    }
    if contract.target_requires_full_vm_replay
        || contract.target_requires_phase43_trace
        || contract.target_requires_phase30_manifest
        || contract.target_requires_phase43_projection_cairo_air
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract must not reintroduce VM-manifest replay inputs"
                .to_string(),
        ));
    }
    if contract.recursive_verification_claimed
        || contract.cryptographic_compression_claimed
        || contract.actual_layerwise_proof_available
        || contract.compression_benchmark_available
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract must not claim unavailable layerwise compression"
                .to_string(),
        ));
    }
    if contract.required_components.len() < 7
        || !contract
            .required_components
            .iter()
            .any(|component| component == "tensor_commitment_scheme")
        || !contract
            .required_components
            .iter()
            .any(|component| component == "ordered_layer_claim_composition_accumulator")
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract missing required components".to_string(),
        ));
    }
    if contract.open_blockers.len() < 3
        || !contract
            .open_blockers
            .iter()
            .any(|blocker| blocker.contains("tensor commitment scheme"))
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract must retain tensor commitment blockers"
                .to_string(),
        ));
    }
    if contract.verifier_side_complexity != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_COMPLEXITY_PHASE49
        || contract.decision != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_DECISION_PHASE49
        || contract.required_next_step != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_NEXT_STEP_PHASE49
    {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract decision or complexity drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "source_phase48_attempt_commitment",
            contract.source_phase48_attempt_commitment.as_str(),
        ),
        ("contract_commitment", contract.contract_commitment.as_str()),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected = commit_phase49_layerwise_tensor_claim_propagation_contract(contract)?;
    if contract.contract_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract commitment does not match contract fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase49_layerwise_tensor_claim_propagation_contract_against_phase48(
    contract: &Phase49LayerwiseTensorClaimPropagationContract,
    attempt: &Phase48RecursiveProofWrapperAttempt,
) -> Result<()> {
    verify_phase48_recursive_proof_wrapper_attempt(attempt)?;
    let expected = phase49_prepare_layerwise_tensor_claim_propagation_contract(attempt)?;
    if contract != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 49 layerwise tensor-claim contract does not match verified Phase48 no-go attempt"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase50_tensor_commitment_claim(
    claim: &Phase50TensorCommitmentClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 50 tensor commitment claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase50-tensor-commitment-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.tensor_role.as_bytes(),
        claim.tensor_name.as_bytes(),
        claim.element_field.as_bytes(),
        claim.memory_layout.as_bytes(),
        claim.quantization.as_bytes(),
        claim.padding_rule.as_bytes(),
        claim.commitment_scheme.as_bytes(),
        claim.commitment_root.as_bytes(),
        claim.mle_evaluation_claim_status.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, claim.tensor_rank);
    phase44d_update_usize_vec(&mut hasher, &claim.tensor_shape);
    phase29_update_usize(&mut hasher, claim.logical_element_count);
    phase29_update_usize(&mut hasher, claim.padded_element_count);
    phase29_update_bool(&mut hasher, claim.raw_endpoint_anchor_required);
    phase29_update_bool(&mut hasher, claim.raw_endpoint_anchor_available);
    phase29_update_bool(&mut hasher, claim.full_vm_replay_required);
    phase29_update_bool(&mut hasher, claim.phase43_trace_required);
    phase29_update_bool(&mut hasher, claim.phase30_manifest_required);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase44d_finalize_hash(hasher, "Phase 50 tensor commitment claim")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase50_layer_io_claim(claim: &Phase50LayerIoClaim) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 50 layer IO claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase50-layer-io-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase49_contract_version.as_bytes(),
        claim.source_phase49_contract_commitment.as_bytes(),
        claim.source_phase49_decision.as_bytes(),
        claim.source_phase49_required_next_step.as_bytes(),
        claim.proof_backend_version.as_bytes(),
        claim.statement_version.as_bytes(),
        claim.layer_name.as_bytes(),
        claim.layer_kind.as_bytes(),
        claim.input_tensor_claim.tensor_claim_commitment.as_bytes(),
        claim.output_tensor_claim.tensor_claim_commitment.as_bytes(),
        claim.relation_claim_kind.as_bytes(),
        claim.relation_rule.as_bytes(),
        claim.propagation_direction.as_bytes(),
        claim.endpoint_anchoring_rule.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, claim.layer_index);
    phase29_update_usize(&mut hasher, claim.claim_surface_unit_count);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.requires_full_vm_replay);
    phase29_update_bool(&mut hasher, claim.requires_phase43_trace);
    phase29_update_bool(&mut hasher, claim.requires_phase30_manifest);
    phase29_update_bool(&mut hasher, claim.requires_phase43_projection_cairo_air);
    phase29_update_bool(&mut hasher, claim.raw_endpoint_anchor_available);
    phase29_update_bool(&mut hasher, claim.sumcheck_proof_available);
    phase29_update_bool(&mut hasher, claim.logup_proof_available);
    phase29_update_bool(&mut hasher, claim.actual_layer_relation_proof_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 50 layer IO claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase50_prepare_tensor_commitment_claim(
    tensor_role: &str,
    tensor_name: &str,
    tensor_shape: Vec<usize>,
    commitment_root: &str,
    raw_endpoint_anchor_required: bool,
    raw_endpoint_anchor_available: bool,
) -> Result<Phase50TensorCommitmentClaim> {
    let logical_element_count = phase50_tensor_element_count(&tensor_shape)?;
    let padded_element_count = phase50_next_power_of_two(logical_element_count)?;
    let mut claim = Phase50TensorCommitmentClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_TENSOR_COMMITMENT_CLAIM_VERSION_PHASE50.to_string(),
        semantic_scope: STWO_TENSOR_COMMITMENT_CLAIM_SCOPE_PHASE50.to_string(),
        tensor_role: tensor_role.to_string(),
        tensor_name: tensor_name.to_string(),
        element_field: STWO_TENSOR_ELEMENT_FIELD_PHASE50.to_string(),
        memory_layout: STWO_TENSOR_MEMORY_LAYOUT_PHASE50.to_string(),
        quantization: STWO_TENSOR_QUANTIZATION_PHASE50.to_string(),
        tensor_rank: tensor_shape.len(),
        tensor_shape,
        logical_element_count,
        padded_element_count,
        padding_rule: STWO_TENSOR_PADDING_RULE_PHASE50.to_string(),
        commitment_scheme: STWO_TENSOR_COMMITMENT_SCHEME_PHASE50.to_string(),
        commitment_root: commitment_root.to_string(),
        mle_evaluation_claim_status: "pending_phase52_endpoint_mle_evaluation".to_string(),
        raw_endpoint_anchor_required,
        raw_endpoint_anchor_available,
        full_vm_replay_required: false,
        phase43_trace_required: false,
        phase30_manifest_required: false,
        transcript_order: phase50_tensor_transcript_order(),
        tensor_claim_commitment: String::new(),
    };
    claim.tensor_claim_commitment = commit_phase50_tensor_commitment_claim(&claim)?;
    verify_phase50_tensor_commitment_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn phase50_prepare_layer_io_claim(
    contract: &Phase49LayerwiseTensorClaimPropagationContract,
) -> Result<Phase50LayerIoClaim> {
    verify_phase49_layerwise_tensor_claim_propagation_contract(contract)?;
    let input_root =
        phase50_derive_tensor_root(contract, "layer_input", &[contract.input_tensor_width])?;
    let output_root =
        phase50_derive_tensor_root(contract, "layer_output", &[contract.output_tensor_width])?;
    let input_tensor_claim = phase50_prepare_tensor_commitment_claim(
        "layer_input",
        "phase50_layer0_input_activation",
        vec![contract.input_tensor_width],
        &input_root,
        true,
        false,
    )?;
    let output_tensor_claim = phase50_prepare_tensor_commitment_claim(
        "layer_output",
        "phase50_layer0_output_activation",
        vec![contract.output_tensor_width],
        &output_root,
        true,
        false,
    )?;
    let mut claim = Phase50LayerIoClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_LAYER_IO_CLAIM_VERSION_PHASE50.to_string(),
        semantic_scope: STWO_LAYER_IO_CLAIM_SCOPE_PHASE50.to_string(),
        source_phase49_contract_version: contract.contract_version.clone(),
        source_phase49_contract_commitment: contract.contract_commitment.clone(),
        source_phase49_decision: contract.decision.clone(),
        source_phase49_required_next_step: contract.required_next_step.clone(),
        proof_backend_version: contract.proof_backend_version.clone(),
        statement_version: contract.statement_version.clone(),
        layer_index: 0,
        layer_name: "phase50_first_transformer_vm_gated_ff_surface".to_string(),
        layer_kind: "gated_feed_forward".to_string(),
        input_tensor_claim,
        output_tensor_claim,
        relation_claim_kind: STWO_LAYER_IO_RELATION_KIND_PHASE50.to_string(),
        relation_rule: STWO_LAYER_IO_RELATION_RULE_PHASE50.to_string(),
        propagation_direction: STWO_LAYER_IO_PROPAGATION_DIRECTION_PHASE50.to_string(),
        endpoint_anchoring_rule: STWO_LAYER_IO_ENDPOINT_ANCHORING_RULE_PHASE50.to_string(),
        claim_surface_unit_count: contract.input_tensor_width + contract.output_tensor_width,
        verifier_side_complexity: STWO_LAYER_IO_COMPLEXITY_PHASE50.to_string(),
        transcript_order: phase50_layer_io_transcript_order(),
        requires_full_vm_replay: false,
        requires_phase43_trace: false,
        requires_phase30_manifest: false,
        requires_phase43_projection_cairo_air: false,
        raw_endpoint_anchor_available: false,
        sumcheck_proof_available: false,
        logup_proof_available: false,
        actual_layer_relation_proof_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        required_next_step: STWO_LAYER_IO_NEXT_STEP_PHASE50.to_string(),
        layer_io_claim_commitment: String::new(),
    };
    claim.layer_io_claim_commitment = commit_phase50_layer_io_claim(&claim)?;
    verify_phase50_layer_io_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase50_tensor_commitment_claim(claim: &Phase50TensorCommitmentClaim) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_TENSOR_COMMITMENT_CLAIM_VERSION_PHASE50
        || claim.semantic_scope != STWO_TENSOR_COMMITMENT_CLAIM_SCOPE_PHASE50
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim version or semantic scope drift".to_string(),
        ));
    }
    if claim.tensor_role.is_empty() || claim.tensor_name.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim requires typed role and name".to_string(),
        ));
    }
    if claim.element_field != STWO_TENSOR_ELEMENT_FIELD_PHASE50
        || claim.memory_layout != STWO_TENSOR_MEMORY_LAYOUT_PHASE50
        || claim.quantization != STWO_TENSOR_QUANTIZATION_PHASE50
        || claim.padding_rule != STWO_TENSOR_PADDING_RULE_PHASE50
        || claim.commitment_scheme != STWO_TENSOR_COMMITMENT_SCHEME_PHASE50
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim field, layout, padding, or scheme drift".to_string(),
        ));
    }
    if claim.tensor_rank == 0 || claim.tensor_rank != claim.tensor_shape.len() {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim rank does not match shape".to_string(),
        ));
    }
    let logical_element_count = phase50_tensor_element_count(&claim.tensor_shape)?;
    let padded_element_count = phase50_next_power_of_two(logical_element_count)?;
    if claim.logical_element_count != logical_element_count
        || claim.padded_element_count != padded_element_count
        || !claim.padded_element_count.is_power_of_two()
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim element counts or padding drift".to_string(),
        ));
    }
    phase43_require_hash32("phase50_tensor_commitment_root", &claim.commitment_root)?;
    if claim.mle_evaluation_claim_status != "pending_phase52_endpoint_mle_evaluation" {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim must leave MLE endpoint evaluation pending Phase52"
                .to_string(),
        ));
    }
    if !claim.raw_endpoint_anchor_required {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim must require endpoint anchoring".to_string(),
        ));
    }
    if claim.full_vm_replay_required
        || claim.phase43_trace_required
        || claim.phase30_manifest_required
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim must not require VM replay artifacts".to_string(),
        ));
    }
    if claim.transcript_order != phase50_tensor_transcript_order() {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim transcript order drift".to_string(),
        ));
    }
    phase43_require_hash32(
        "phase50_tensor_claim_commitment",
        &claim.tensor_claim_commitment,
    )?;
    let expected = commit_phase50_tensor_commitment_claim(claim)?;
    if claim.tensor_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim commitment does not match claim fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase50_layer_io_claim(claim: &Phase50LayerIoClaim) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_LAYER_IO_CLAIM_VERSION_PHASE50
        || claim.semantic_scope != STWO_LAYER_IO_CLAIM_SCOPE_PHASE50
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim version or semantic scope drift".to_string(),
        ));
    }
    if claim.source_phase49_contract_version != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_VERSION_PHASE49
        || claim.source_phase49_decision != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_DECISION_PHASE49
        || claim.source_phase49_required_next_step
            != STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_NEXT_STEP_PHASE49
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim must be sourced from the Phase49 tensor-claim contract"
                .to_string(),
        ));
    }
    if claim.proof_backend_version != STWO_BACKEND_VERSION_PHASE12
        || claim.statement_version != CLAIM_STATEMENT_VERSION_V1
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim backend or statement version drift".to_string(),
        ));
    }
    phase43_require_hash32(
        "phase50_source_phase49_contract_commitment",
        &claim.source_phase49_contract_commitment,
    )?;
    verify_phase50_tensor_commitment_claim(&claim.input_tensor_claim)?;
    verify_phase50_tensor_commitment_claim(&claim.output_tensor_claim)?;
    if claim.layer_index != 0
        || claim.layer_name != "phase50_first_transformer_vm_gated_ff_surface"
        || claim.layer_kind != "gated_feed_forward"
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim first-layer identity drift".to_string(),
        ));
    }
    if claim.input_tensor_claim.tensor_role != "layer_input"
        || claim.output_tensor_claim.tensor_role != "layer_output"
        || claim.input_tensor_claim.tensor_shape != vec![INPUT_DIM]
        || claim.output_tensor_claim.tensor_shape != vec![OUTPUT_DIM]
        || claim.claim_surface_unit_count != INPUT_DIM + OUTPUT_DIM
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim tensor surface drift".to_string(),
        ));
    }
    if claim.relation_claim_kind != STWO_LAYER_IO_RELATION_KIND_PHASE50
        || claim.relation_rule != STWO_LAYER_IO_RELATION_RULE_PHASE50
        || claim.propagation_direction != STWO_LAYER_IO_PROPAGATION_DIRECTION_PHASE50
        || claim.endpoint_anchoring_rule != STWO_LAYER_IO_ENDPOINT_ANCHORING_RULE_PHASE50
        || claim.verifier_side_complexity != STWO_LAYER_IO_COMPLEXITY_PHASE50
        || claim.required_next_step != STWO_LAYER_IO_NEXT_STEP_PHASE50
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim relation, anchoring, or next-step drift".to_string(),
        ));
    }
    if claim.transcript_order != phase50_layer_io_transcript_order() {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim transcript order drift".to_string(),
        ));
    }
    if claim.requires_full_vm_replay
        || claim.requires_phase43_trace
        || claim.requires_phase30_manifest
        || claim.requires_phase43_projection_cairo_air
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim must not reintroduce VM replay artifacts".to_string(),
        ));
    }
    if claim.raw_endpoint_anchor_available
        || claim.input_tensor_claim.raw_endpoint_anchor_available
        || claim.output_tensor_claim.raw_endpoint_anchor_available
        || claim.sumcheck_proof_available
        || claim.logup_proof_available
        || claim.actual_layer_relation_proof_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim must not claim unavailable tensor proof evidence".to_string(),
        ));
    }
    phase43_require_hash32(
        "phase50_layer_io_claim_commitment",
        &claim.layer_io_claim_commitment,
    )?;
    let expected = commit_phase50_layer_io_claim(claim)?;
    if claim.layer_io_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim commitment does not match claim fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase50_layer_io_claim_against_phase49(
    claim: &Phase50LayerIoClaim,
    contract: &Phase49LayerwiseTensorClaimPropagationContract,
) -> Result<()> {
    verify_phase49_layerwise_tensor_claim_propagation_contract(contract)?;
    let expected = phase50_prepare_layer_io_claim(contract)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 50 layer IO claim does not match verified Phase49 tensor-claim contract"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase51_first_layer_relation_claim(
    claim: &Phase51FirstLayerRelationClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 51 first-layer relation claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase51-first-layer-relation-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase50_layer_io_claim_version.as_bytes(),
        claim.source_phase50_layer_io_claim_commitment.as_bytes(),
        claim.source_phase49_contract_commitment.as_bytes(),
        claim.proof_backend_version.as_bytes(),
        claim.statement_version.as_bytes(),
        claim.relation_kind.as_bytes(),
        claim.relation_rule.as_bytes(),
        claim.relation_field.as_bytes(),
        claim.parameter_commitment_scheme.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, claim.layer_index);
    phase29_update_usize(&mut hasher, claim.input_width);
    phase29_update_usize(&mut hasher, claim.hidden_width);
    phase29_update_usize(&mut hasher, claim.output_width);
    phase44d_update_usize_vec(&mut hasher, &claim.gate_projection_shape);
    phase44d_update_usize_vec(&mut hasher, &claim.value_projection_shape);
    phase44d_update_usize_vec(&mut hasher, &claim.hidden_product_shape);
    phase44d_update_usize_vec(&mut hasher, &claim.output_projection_shape);
    phase29_update_usize(&mut hasher, claim.gate_bias_len);
    phase29_update_usize(&mut hasher, claim.value_bias_len);
    phase29_update_usize(&mut hasher, claim.output_bias_len);
    phase44d_update_hash_vec(&mut hasher, &claim.operation_graph_order);
    phase29_update_usize(&mut hasher, claim.parameter_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.activation_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.claim_surface_unit_count);
    phase29_update_bool(&mut hasher, claim.vm_step_replay_required);
    phase29_update_bool(&mut hasher, claim.phase43_trace_required);
    phase29_update_bool(&mut hasher, claim.phase30_manifest_required);
    phase29_update_bool(&mut hasher, claim.raw_endpoint_anchor_available);
    phase29_update_bool(&mut hasher, claim.parameter_commitments_available);
    phase29_update_bool(&mut hasher, claim.affine_sumcheck_claim_available);
    phase29_update_bool(&mut hasher, claim.hadamard_product_claim_available);
    phase29_update_bool(&mut hasher, claim.actual_relation_proof_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase44d_finalize_hash(hasher, "Phase 51 first-layer relation claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase51_prepare_first_layer_relation_claim(
    layer_io_claim: &Phase50LayerIoClaim,
) -> Result<Phase51FirstLayerRelationClaim> {
    verify_phase50_layer_io_claim(layer_io_claim)?;
    let config = TransformerVmConfig::percepta_reference();
    config.validate()?;
    let hidden_width = config.ff_dim;
    let parameter_surface_unit_count = (2 * hidden_width * INPUT_DIM)
        + (OUTPUT_DIM * hidden_width)
        + (2 * hidden_width)
        + OUTPUT_DIM;
    let activation_surface_unit_count = INPUT_DIM + (3 * hidden_width) + OUTPUT_DIM;
    let mut claim = Phase51FirstLayerRelationClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_RELATION_CLAIM_VERSION_PHASE51.to_string(),
        semantic_scope: STWO_FIRST_LAYER_RELATION_CLAIM_SCOPE_PHASE51.to_string(),
        source_phase50_layer_io_claim_version: layer_io_claim.claim_version.clone(),
        source_phase50_layer_io_claim_commitment: layer_io_claim.layer_io_claim_commitment.clone(),
        source_phase49_contract_commitment: layer_io_claim
            .source_phase49_contract_commitment
            .clone(),
        proof_backend_version: layer_io_claim.proof_backend_version.clone(),
        statement_version: layer_io_claim.statement_version.clone(),
        relation_kind: STWO_FIRST_LAYER_RELATION_KIND_PHASE51.to_string(),
        relation_rule: STWO_FIRST_LAYER_RELATION_RULE_PHASE51.to_string(),
        relation_field: STWO_FIRST_LAYER_RELATION_FIELD_PHASE51.to_string(),
        layer_index: layer_io_claim.layer_index,
        input_width: INPUT_DIM,
        hidden_width,
        output_width: OUTPUT_DIM,
        gate_projection_shape: vec![hidden_width, INPUT_DIM],
        value_projection_shape: vec![hidden_width, INPUT_DIM],
        hidden_product_shape: vec![hidden_width],
        output_projection_shape: vec![OUTPUT_DIM, hidden_width],
        gate_bias_len: hidden_width,
        value_bias_len: hidden_width,
        output_bias_len: OUTPUT_DIM,
        operation_graph_order: phase51_operation_graph_order(),
        parameter_commitment_scheme: STWO_FIRST_LAYER_RELATION_PARAMETER_COMMITMENT_SCHEME_PHASE51
            .to_string(),
        parameter_surface_unit_count,
        activation_surface_unit_count,
        claim_surface_unit_count: layer_io_claim.claim_surface_unit_count + hidden_width,
        vm_step_replay_required: false,
        phase43_trace_required: false,
        phase30_manifest_required: false,
        raw_endpoint_anchor_available: false,
        parameter_commitments_available: false,
        affine_sumcheck_claim_available: false,
        hadamard_product_claim_available: false,
        actual_relation_proof_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        verifier_side_complexity: STWO_FIRST_LAYER_RELATION_COMPLEXITY_PHASE51.to_string(),
        transcript_order: phase51_relation_transcript_order(),
        required_next_step: STWO_FIRST_LAYER_RELATION_NEXT_STEP_PHASE51.to_string(),
        relation_claim_commitment: String::new(),
    };
    claim.relation_claim_commitment = commit_phase51_first_layer_relation_claim(&claim)?;
    verify_phase51_first_layer_relation_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase51_first_layer_relation_claim(
    claim: &Phase51FirstLayerRelationClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_RELATION_CLAIM_VERSION_PHASE51
        || claim.semantic_scope != STWO_FIRST_LAYER_RELATION_CLAIM_SCOPE_PHASE51
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim version or semantic scope drift".to_string(),
        ));
    }
    if claim.source_phase50_layer_io_claim_version != STWO_LAYER_IO_CLAIM_VERSION_PHASE50 {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim source Phase50 version drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase51_source_phase50_layer_io_claim_commitment",
            claim.source_phase50_layer_io_claim_commitment.as_str(),
        ),
        (
            "phase51_source_phase49_contract_commitment",
            claim.source_phase49_contract_commitment.as_str(),
        ),
        (
            "phase51_relation_claim_commitment",
            claim.relation_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if claim.proof_backend_version != STWO_BACKEND_VERSION_PHASE12
        || claim.statement_version != CLAIM_STATEMENT_VERSION_V1
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim backend or statement version drift".to_string(),
        ));
    }
    if claim.relation_kind != STWO_FIRST_LAYER_RELATION_KIND_PHASE51
        || claim.relation_rule != STWO_FIRST_LAYER_RELATION_RULE_PHASE51
        || claim.relation_field != STWO_FIRST_LAYER_RELATION_FIELD_PHASE51
        || claim.parameter_commitment_scheme
            != STWO_FIRST_LAYER_RELATION_PARAMETER_COMMITMENT_SCHEME_PHASE51
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation kind, rule, field, or parameter scheme drift"
                .to_string(),
        ));
    }
    let config = TransformerVmConfig::percepta_reference();
    config.validate()?;
    let hidden_width = config.ff_dim;
    if claim.layer_index != 0
        || claim.input_width != INPUT_DIM
        || claim.hidden_width != hidden_width
        || claim.output_width != OUTPUT_DIM
        || claim.gate_projection_shape != vec![hidden_width, INPUT_DIM]
        || claim.value_projection_shape != vec![hidden_width, INPUT_DIM]
        || claim.hidden_product_shape != vec![hidden_width]
        || claim.output_projection_shape != vec![OUTPUT_DIM, hidden_width]
        || claim.gate_bias_len != hidden_width
        || claim.value_bias_len != hidden_width
        || claim.output_bias_len != OUTPUT_DIM
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim gated-FF shape drift".to_string(),
        ));
    }
    if claim.operation_graph_order != phase51_operation_graph_order() {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim operation graph order drift".to_string(),
        ));
    }
    let expected_parameter_surface = (2 * hidden_width * INPUT_DIM)
        + (OUTPUT_DIM * hidden_width)
        + (2 * hidden_width)
        + OUTPUT_DIM;
    let expected_activation_surface = INPUT_DIM + (3 * hidden_width) + OUTPUT_DIM;
    let expected_claim_surface = INPUT_DIM + OUTPUT_DIM + hidden_width;
    if claim.parameter_surface_unit_count != expected_parameter_surface
        || claim.activation_surface_unit_count != expected_activation_surface
        || claim.claim_surface_unit_count != expected_claim_surface
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim surface accounting drift".to_string(),
        ));
    }
    if claim.vm_step_replay_required
        || claim.phase43_trace_required
        || claim.phase30_manifest_required
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim must not require VM replay artifacts".to_string(),
        ));
    }
    if claim.raw_endpoint_anchor_available
        || claim.parameter_commitments_available
        || claim.affine_sumcheck_claim_available
        || claim.hadamard_product_claim_available
        || claim.actual_relation_proof_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim must not claim unavailable proof evidence"
                .to_string(),
        ));
    }
    if claim.verifier_side_complexity != STWO_FIRST_LAYER_RELATION_COMPLEXITY_PHASE51
        || claim.transcript_order != phase51_relation_transcript_order()
        || claim.required_next_step != STWO_FIRST_LAYER_RELATION_NEXT_STEP_PHASE51
    {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim transcript, complexity, or next-step drift"
                .to_string(),
        ));
    }
    let expected = commit_phase51_first_layer_relation_claim(claim)?;
    if claim.relation_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim commitment does not match claim fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase51_first_layer_relation_claim_against_phase50(
    claim: &Phase51FirstLayerRelationClaim,
    layer_io_claim: &Phase50LayerIoClaim,
) -> Result<()> {
    verify_phase50_layer_io_claim(layer_io_claim)?;
    let expected = phase51_prepare_first_layer_relation_claim(layer_io_claim)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 51 first-layer relation claim does not match verified Phase50 layer IO claim"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase52_tensor_endpoint_evaluation_claim(
    claim: &Phase52TensorEndpointEvaluationClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 52 tensor endpoint evaluation claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase52-tensor-endpoint-evaluation-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase50_tensor_claim_commitment.as_bytes(),
        claim.source_phase51_relation_claim_commitment.as_bytes(),
        claim.endpoint_role.as_bytes(),
        claim.tensor_name.as_bytes(),
        claim.element_field.as_bytes(),
        claim.raw_tensor_commitment.as_bytes(),
        claim.challenge_derivation.as_bytes(),
        claim.evaluation_rule.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase44d_update_usize_vec(&mut hasher, &claim.tensor_shape);
    phase29_update_usize(&mut hasher, claim.logical_element_count);
    phase29_update_usize(&mut hasher, claim.padded_element_count);
    phase44d_update_u32_vec(&mut hasher, &claim.raw_tensor_values);
    phase44d_update_u32_vec(&mut hasher, &claim.mle_point);
    hasher.update(&claim.mle_value.to_le_bytes());
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.verifier_derived_from_raw_tensor);
    phase29_update_bool(&mut hasher, claim.commitment_opening_proof_available);
    phase29_update_bool(&mut hasher, claim.requires_full_vm_replay);
    phase29_update_bool(&mut hasher, claim.requires_phase43_trace);
    phase29_update_bool(&mut hasher, claim.requires_phase30_manifest);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 52 tensor endpoint evaluation claim")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase52_layer_endpoint_anchoring_claim(
    claim: &Phase52LayerEndpointAnchoringClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 52 layer endpoint anchoring claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase52-layer-endpoint-anchoring-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase51_relation_claim_version.as_bytes(),
        claim.source_phase51_relation_claim_commitment.as_bytes(),
        claim.source_phase50_layer_io_claim_commitment.as_bytes(),
        claim
            .input_endpoint_claim
            .endpoint_claim_commitment
            .as_bytes(),
        claim
            .output_endpoint_claim
            .endpoint_claim_commitment
            .as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, claim.endpoint_count);
    phase29_update_usize(&mut hasher, claim.public_endpoint_width);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.endpoint_anchoring_available);
    phase29_update_bool(&mut hasher, claim.actual_layer_relation_proof_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 52 layer endpoint anchoring claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase52_prepare_tensor_endpoint_evaluation_claim(
    tensor_claim: &Phase50TensorCommitmentClaim,
    relation_claim: &Phase51FirstLayerRelationClaim,
    endpoint_role: &str,
    raw_tensor_values: Vec<u32>,
) -> Result<Phase52TensorEndpointEvaluationClaim> {
    verify_phase50_tensor_commitment_claim(tensor_claim)?;
    verify_phase51_first_layer_relation_claim(relation_claim)?;
    if endpoint_role != tensor_claim.tensor_role {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint role must match the Phase50 tensor claim role".to_string(),
        ));
    }
    phase52_validate_m31_values("raw_tensor_values", &raw_tensor_values)?;
    let raw_tensor_commitment = phase52_commit_raw_tensor_values(&raw_tensor_values)?;
    let mle_point = phase52_derive_mle_point(
        &relation_claim.relation_claim_commitment,
        endpoint_role,
        tensor_claim.padded_element_count,
    )?;
    let mle_value = phase52_evaluate_padded_mle(&raw_tensor_values, &mle_point)?;
    let mut claim = Phase52TensorEndpointEvaluationClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_VERSION_PHASE52.to_string(),
        semantic_scope: STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_SCOPE_PHASE52.to_string(),
        source_phase50_tensor_claim_commitment: tensor_claim.tensor_claim_commitment.clone(),
        source_phase51_relation_claim_commitment: relation_claim.relation_claim_commitment.clone(),
        endpoint_role: endpoint_role.to_string(),
        tensor_name: tensor_claim.tensor_name.clone(),
        element_field: STWO_TENSOR_ELEMENT_FIELD_PHASE50.to_string(),
        tensor_shape: tensor_claim.tensor_shape.clone(),
        logical_element_count: tensor_claim.logical_element_count,
        padded_element_count: tensor_claim.padded_element_count,
        raw_tensor_values,
        raw_tensor_commitment,
        mle_point,
        mle_value,
        challenge_derivation: STWO_TENSOR_ENDPOINT_CHALLENGE_DERIVATION_PHASE52.to_string(),
        evaluation_rule: STWO_TENSOR_ENDPOINT_EVALUATION_RULE_PHASE52.to_string(),
        transcript_order: phase52_endpoint_transcript_order(),
        verifier_derived_from_raw_tensor: true,
        commitment_opening_proof_available: false,
        requires_full_vm_replay: false,
        requires_phase43_trace: false,
        requires_phase30_manifest: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        endpoint_claim_commitment: String::new(),
    };
    claim.endpoint_claim_commitment = commit_phase52_tensor_endpoint_evaluation_claim(&claim)?;
    verify_phase52_tensor_endpoint_evaluation_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn phase52_prepare_layer_endpoint_anchoring_claim(
    layer_io_claim: &Phase50LayerIoClaim,
    relation_claim: &Phase51FirstLayerRelationClaim,
    raw_input_tensor_values: Vec<u32>,
    raw_output_tensor_values: Vec<u32>,
) -> Result<Phase52LayerEndpointAnchoringClaim> {
    verify_phase51_first_layer_relation_claim_against_phase50(relation_claim, layer_io_claim)?;
    let input_endpoint_claim = phase52_prepare_tensor_endpoint_evaluation_claim(
        &layer_io_claim.input_tensor_claim,
        relation_claim,
        "layer_input",
        raw_input_tensor_values,
    )?;
    let output_endpoint_claim = phase52_prepare_tensor_endpoint_evaluation_claim(
        &layer_io_claim.output_tensor_claim,
        relation_claim,
        "layer_output",
        raw_output_tensor_values,
    )?;
    let mut claim = Phase52LayerEndpointAnchoringClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_VERSION_PHASE52.to_string(),
        semantic_scope: STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_SCOPE_PHASE52.to_string(),
        source_phase51_relation_claim_version: relation_claim.claim_version.clone(),
        source_phase51_relation_claim_commitment: relation_claim.relation_claim_commitment.clone(),
        source_phase50_layer_io_claim_commitment: layer_io_claim.layer_io_claim_commitment.clone(),
        endpoint_count: 2,
        public_endpoint_width: input_endpoint_claim.raw_tensor_values.len()
            + output_endpoint_claim.raw_tensor_values.len(),
        input_endpoint_claim,
        output_endpoint_claim,
        verifier_side_complexity: STWO_LAYER_ENDPOINT_ANCHORING_COMPLEXITY_PHASE52.to_string(),
        transcript_order: phase52_layer_endpoint_transcript_order(),
        endpoint_anchoring_available: true,
        actual_layer_relation_proof_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        required_next_step: STWO_LAYER_ENDPOINT_ANCHORING_NEXT_STEP_PHASE52.to_string(),
        anchoring_claim_commitment: String::new(),
    };
    claim.anchoring_claim_commitment = commit_phase52_layer_endpoint_anchoring_claim(&claim)?;
    verify_phase52_layer_endpoint_anchoring_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase52_tensor_endpoint_evaluation_claim(
    claim: &Phase52TensorEndpointEvaluationClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_VERSION_PHASE52
        || claim.semantic_scope != STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_SCOPE_PHASE52
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim version or semantic scope drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase52_source_phase50_tensor_claim_commitment",
            claim.source_phase50_tensor_claim_commitment.as_str(),
        ),
        (
            "phase52_source_phase51_relation_claim_commitment",
            claim.source_phase51_relation_claim_commitment.as_str(),
        ),
        (
            "phase52_raw_tensor_commitment",
            claim.raw_tensor_commitment.as_str(),
        ),
        (
            "phase52_endpoint_claim_commitment",
            claim.endpoint_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if claim.endpoint_role != "layer_input" && claim.endpoint_role != "layer_output" {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim endpoint role drift".to_string(),
        ));
    }
    if claim.element_field != STWO_TENSOR_ELEMENT_FIELD_PHASE50
        || claim.challenge_derivation != STWO_TENSOR_ENDPOINT_CHALLENGE_DERIVATION_PHASE52
        || claim.evaluation_rule != STWO_TENSOR_ENDPOINT_EVALUATION_RULE_PHASE52
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim field or evaluation rule drift".to_string(),
        ));
    }
    let logical_element_count = phase50_tensor_element_count(&claim.tensor_shape)?;
    let padded_element_count = phase50_next_power_of_two(logical_element_count)?;
    if claim.logical_element_count != logical_element_count
        || claim.padded_element_count != padded_element_count
        || claim.raw_tensor_values.len() != logical_element_count
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim shape or raw tensor length drift"
                .to_string(),
        ));
    }
    phase52_validate_m31_values("raw_tensor_values", &claim.raw_tensor_values)?;
    phase52_validate_m31_values("mle_point", &claim.mle_point)?;
    if claim.mle_value >= PHASE44D_M31_MODULUS {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim MLE value exceeds M31 capacity".to_string(),
        ));
    }
    let expected_raw_commitment = phase52_commit_raw_tensor_values(&claim.raw_tensor_values)?;
    if claim.raw_tensor_commitment != expected_raw_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim raw tensor commitment drift".to_string(),
        ));
    }
    let expected_point = phase52_derive_mle_point(
        &claim.source_phase51_relation_claim_commitment,
        &claim.endpoint_role,
        claim.padded_element_count,
    )?;
    if claim.mle_point != expected_point {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim MLE challenge point drift".to_string(),
        ));
    }
    let expected_mle_value =
        phase52_evaluate_padded_mle(&claim.raw_tensor_values, &claim.mle_point)?;
    if claim.mle_value != expected_mle_value {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim MLE value drift".to_string(),
        ));
    }
    if claim.transcript_order != phase52_endpoint_transcript_order() {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim transcript order drift".to_string(),
        ));
    }
    if !claim.verifier_derived_from_raw_tensor
        || claim.commitment_opening_proof_available
        || claim.requires_full_vm_replay
        || claim.requires_phase43_trace
        || claim.requires_phase30_manifest
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim must stay raw-endpoint-derived without false proof claims"
                .to_string(),
        ));
    }
    let expected = commit_phase52_tensor_endpoint_evaluation_claim(claim)?;
    if claim.endpoint_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 52 tensor endpoint evaluation claim commitment does not match claim fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase52_layer_endpoint_anchoring_claim(
    claim: &Phase52LayerEndpointAnchoringClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_VERSION_PHASE52
        || claim.semantic_scope != STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_SCOPE_PHASE52
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim version or semantic scope drift".to_string(),
        ));
    }
    if claim.source_phase51_relation_claim_version
        != STWO_FIRST_LAYER_RELATION_CLAIM_VERSION_PHASE51
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim source Phase51 version drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase52_source_phase51_relation_claim_commitment",
            claim.source_phase51_relation_claim_commitment.as_str(),
        ),
        (
            "phase52_source_phase50_layer_io_claim_commitment",
            claim.source_phase50_layer_io_claim_commitment.as_str(),
        ),
        (
            "phase52_anchoring_claim_commitment",
            claim.anchoring_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    verify_phase52_tensor_endpoint_evaluation_claim(&claim.input_endpoint_claim)?;
    verify_phase52_tensor_endpoint_evaluation_claim(&claim.output_endpoint_claim)?;
    if claim.input_endpoint_claim.endpoint_role != "layer_input"
        || claim.output_endpoint_claim.endpoint_role != "layer_output"
        || claim
            .input_endpoint_claim
            .source_phase51_relation_claim_commitment
            != claim.source_phase51_relation_claim_commitment
        || claim
            .output_endpoint_claim
            .source_phase51_relation_claim_commitment
            != claim.source_phase51_relation_claim_commitment
        || claim.input_endpoint_claim.tensor_shape != vec![INPUT_DIM]
        || claim.output_endpoint_claim.tensor_shape != vec![OUTPUT_DIM]
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim endpoint role or shape drift".to_string(),
        ));
    }
    if claim.endpoint_count != 2
        || claim.public_endpoint_width != INPUT_DIM + OUTPUT_DIM
        || claim.verifier_side_complexity != STWO_LAYER_ENDPOINT_ANCHORING_COMPLEXITY_PHASE52
        || claim.transcript_order != phase52_layer_endpoint_transcript_order()
        || claim.required_next_step != STWO_LAYER_ENDPOINT_ANCHORING_NEXT_STEP_PHASE52
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim surface, transcript, or next-step drift"
                .to_string(),
        ));
    }
    if !claim.endpoint_anchoring_available
        || claim.actual_layer_relation_proof_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim must anchor endpoints without false proof claims"
                .to_string(),
        ));
    }
    let expected = commit_phase52_layer_endpoint_anchoring_claim(claim)?;
    if claim.anchoring_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim commitment does not match claim fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase52_layer_endpoint_anchoring_claim_against_phase51(
    claim: &Phase52LayerEndpointAnchoringClaim,
    layer_io_claim: &Phase50LayerIoClaim,
    relation_claim: &Phase51FirstLayerRelationClaim,
) -> Result<()> {
    verify_phase51_first_layer_relation_claim_against_phase50(relation_claim, layer_io_claim)?;
    let expected = phase52_prepare_layer_endpoint_anchoring_claim(
        layer_io_claim,
        relation_claim,
        claim.input_endpoint_claim.raw_tensor_values.clone(),
        claim.output_endpoint_claim.raw_tensor_values.clone(),
    )?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 52 layer endpoint anchoring claim does not match verified Phase51 relation and raw endpoints"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase53_first_layer_relation_benchmark_claim(
    claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 53 first-layer relation benchmark claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase53-first-layer-relation-benchmark-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase52_anchoring_claim_commitment.as_bytes(),
        claim.source_phase51_relation_claim_commitment.as_bytes(),
        claim.source_phase50_layer_io_claim_commitment.as_bytes(),
        claim.relation_kind.as_bytes(),
        claim.relation_rule.as_bytes(),
        claim.relation_field.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.benchmark_status.as_bytes(),
        claim.stwo_ml_reference.as_bytes(),
        claim.parameter_binding_scheme.as_bytes(),
        claim.parameter_binding_commitment.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, claim.layer_index);
    phase29_update_usize(&mut hasher, claim.input_width);
    phase29_update_usize(&mut hasher, claim.hidden_width);
    phase29_update_usize(&mut hasher, claim.output_width);
    phase44d_update_usize_vec(&mut hasher, &claim.gate_matmul_shape);
    phase44d_update_usize_vec(&mut hasher, &claim.value_matmul_shape);
    phase44d_update_usize_vec(&mut hasher, &claim.output_matmul_shape);
    phase29_update_usize(&mut hasher, claim.gate_matmul_inner_rounds);
    phase29_update_usize(&mut hasher, claim.value_matmul_inner_rounds);
    phase29_update_usize(&mut hasher, claim.output_matmul_inner_rounds);
    phase29_update_usize(&mut hasher, claim.hadamard_eq_sumcheck_rounds);
    phase29_update_usize(&mut hasher, claim.planned_sumcheck_round_count);
    phase29_update_usize(&mut hasher, claim.matmul_round_polynomial_coefficient_count);
    phase29_update_usize(
        &mut hasher,
        claim.hadamard_round_polynomial_coefficient_count,
    );
    phase29_update_usize(&mut hasher, claim.final_evaluation_count);
    phase29_update_usize(&mut hasher, claim.estimated_sumcheck_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.gate_affine_mul_terms);
    phase29_update_usize(&mut hasher, claim.value_affine_mul_terms);
    phase29_update_usize(&mut hasher, claim.output_affine_mul_terms);
    phase29_update_usize(&mut hasher, claim.total_affine_mul_terms);
    phase29_update_usize(&mut hasher, claim.bias_term_count);
    phase29_update_usize(&mut hasher, claim.hadamard_term_count);
    phase29_update_usize(&mut hasher, claim.naive_relation_arithmetic_term_count);
    phase29_update_usize(&mut hasher, claim.parameter_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.activation_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.endpoint_public_width);
    phase29_update_usize(&mut hasher, claim.tensor_route_claim_surface_unit_count);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.endpoint_anchor_available);
    phase29_update_bool(&mut hasher, claim.parameter_opening_proof_available);
    phase29_update_bool(&mut hasher, claim.affine_sumcheck_proof_available);
    phase29_update_bool(&mut hasher, claim.hadamard_product_proof_available);
    phase29_update_bool(&mut hasher, claim.actual_relation_proof_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 53 first-layer relation benchmark claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase53_prepare_first_layer_relation_benchmark_claim(
    anchoring_claim: &Phase52LayerEndpointAnchoringClaim,
    relation_claim: &Phase51FirstLayerRelationClaim,
) -> Result<Phase53FirstLayerRelationBenchmarkClaim> {
    verify_phase52_layer_endpoint_anchoring_claim(anchoring_claim)?;
    verify_phase51_first_layer_relation_claim(relation_claim)?;
    if anchoring_claim.source_phase51_relation_claim_commitment
        != relation_claim.relation_claim_commitment
        || anchoring_claim.source_phase50_layer_io_claim_commitment
            != relation_claim.source_phase50_layer_io_claim_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 benchmark claim requires Phase52 anchoring to match the Phase51 relation"
                .to_string(),
        ));
    }

    let gate_matmul_inner_rounds = phase53_padded_log2(relation_claim.input_width)?;
    let value_matmul_inner_rounds = phase53_padded_log2(relation_claim.input_width)?;
    let output_matmul_inner_rounds = phase53_padded_log2(relation_claim.hidden_width)?;
    let hadamard_eq_sumcheck_rounds = phase53_padded_log2(relation_claim.hidden_width)?;
    let planned_sumcheck_round_count = gate_matmul_inner_rounds
        + value_matmul_inner_rounds
        + output_matmul_inner_rounds
        + hadamard_eq_sumcheck_rounds;
    let matmul_round_polynomial_coefficient_count =
        3 * (gate_matmul_inner_rounds + value_matmul_inner_rounds + output_matmul_inner_rounds);
    let hadamard_round_polynomial_coefficient_count = 4 * hadamard_eq_sumcheck_rounds;
    let final_evaluation_count = 8;
    let estimated_sumcheck_surface_unit_count = matmul_round_polynomial_coefficient_count
        + hadamard_round_polynomial_coefficient_count
        + final_evaluation_count;
    let gate_affine_mul_terms = relation_claim.input_width * relation_claim.hidden_width;
    let value_affine_mul_terms = relation_claim.input_width * relation_claim.hidden_width;
    let output_affine_mul_terms = relation_claim.hidden_width * relation_claim.output_width;
    let total_affine_mul_terms =
        gate_affine_mul_terms + value_affine_mul_terms + output_affine_mul_terms;
    let bias_term_count = relation_claim.gate_bias_len
        + relation_claim.value_bias_len
        + relation_claim.output_bias_len;
    let hadamard_term_count = relation_claim.hidden_width;
    let naive_relation_arithmetic_term_count =
        total_affine_mul_terms + bias_term_count + hadamard_term_count;

    let mut claim = Phase53FirstLayerRelationBenchmarkClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_VERSION_PHASE53.to_string(),
        semantic_scope: STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_SCOPE_PHASE53.to_string(),
        source_phase52_anchoring_claim_commitment: anchoring_claim
            .anchoring_claim_commitment
            .clone(),
        source_phase51_relation_claim_commitment: relation_claim.relation_claim_commitment.clone(),
        source_phase50_layer_io_claim_commitment: relation_claim
            .source_phase50_layer_io_claim_commitment
            .clone(),
        relation_kind: relation_claim.relation_kind.clone(),
        relation_rule: relation_claim.relation_rule.clone(),
        relation_field: relation_claim.relation_field.clone(),
        layer_index: relation_claim.layer_index,
        input_width: relation_claim.input_width,
        hidden_width: relation_claim.hidden_width,
        output_width: relation_claim.output_width,
        gate_matmul_shape: vec![1, relation_claim.input_width, relation_claim.hidden_width],
        value_matmul_shape: vec![1, relation_claim.input_width, relation_claim.hidden_width],
        output_matmul_shape: vec![1, relation_claim.hidden_width, relation_claim.output_width],
        gate_matmul_inner_rounds,
        value_matmul_inner_rounds,
        output_matmul_inner_rounds,
        hadamard_eq_sumcheck_rounds,
        planned_sumcheck_round_count,
        matmul_round_polynomial_coefficient_count,
        hadamard_round_polynomial_coefficient_count,
        final_evaluation_count,
        estimated_sumcheck_surface_unit_count,
        gate_affine_mul_terms,
        value_affine_mul_terms,
        output_affine_mul_terms,
        total_affine_mul_terms,
        bias_term_count,
        hadamard_term_count,
        naive_relation_arithmetic_term_count,
        parameter_surface_unit_count: relation_claim.parameter_surface_unit_count,
        activation_surface_unit_count: relation_claim.activation_surface_unit_count,
        endpoint_public_width: anchoring_claim.public_endpoint_width,
        tensor_route_claim_surface_unit_count: anchoring_claim.public_endpoint_width
            + estimated_sumcheck_surface_unit_count,
        verifier_side_complexity: STWO_FIRST_LAYER_RELATION_BENCHMARK_COMPLEXITY_PHASE53
            .to_string(),
        benchmark_status: STWO_FIRST_LAYER_RELATION_BENCHMARK_STATUS_PHASE53.to_string(),
        stwo_ml_reference: STWO_FIRST_LAYER_RELATION_BENCHMARK_STWO_ML_REFERENCE_PHASE53
            .to_string(),
        parameter_binding_scheme:
            STWO_FIRST_LAYER_RELATION_BENCHMARK_PARAMETER_BINDING_SCHEME_PHASE53.to_string(),
        parameter_binding_commitment: phase53_derive_parameter_binding_commitment(relation_claim)?,
        transcript_order: phase53_benchmark_transcript_order(),
        endpoint_anchor_available: true,
        parameter_opening_proof_available: false,
        affine_sumcheck_proof_available: false,
        hadamard_product_proof_available: false,
        actual_relation_proof_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        required_next_step: STWO_FIRST_LAYER_RELATION_BENCHMARK_NEXT_STEP_PHASE53.to_string(),
        benchmark_claim_commitment: String::new(),
    };
    claim.benchmark_claim_commitment = commit_phase53_first_layer_relation_benchmark_claim(&claim)?;
    verify_phase53_first_layer_relation_benchmark_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase53_first_layer_relation_benchmark_claim(
    claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_VERSION_PHASE53
        || claim.semantic_scope != STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_SCOPE_PHASE53
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim version or semantic scope drift"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase53_source_phase52_anchoring_claim_commitment",
            claim.source_phase52_anchoring_claim_commitment.as_str(),
        ),
        (
            "phase53_source_phase51_relation_claim_commitment",
            claim.source_phase51_relation_claim_commitment.as_str(),
        ),
        (
            "phase53_source_phase50_layer_io_claim_commitment",
            claim.source_phase50_layer_io_claim_commitment.as_str(),
        ),
        (
            "phase53_parameter_binding_commitment",
            claim.parameter_binding_commitment.as_str(),
        ),
        (
            "phase53_benchmark_claim_commitment",
            claim.benchmark_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if claim.relation_kind != STWO_FIRST_LAYER_RELATION_KIND_PHASE51
        || claim.relation_rule != STWO_FIRST_LAYER_RELATION_RULE_PHASE51
        || claim.relation_field != STWO_FIRST_LAYER_RELATION_FIELD_PHASE51
        || claim.layer_index != 0
        || claim.input_width != INPUT_DIM
        || claim.output_width != OUTPUT_DIM
        || claim.hidden_width != TransformerVmConfig::percepta_reference().ff_dim
        || claim.gate_matmul_shape != vec![1, INPUT_DIM, claim.hidden_width]
        || claim.value_matmul_shape != vec![1, INPUT_DIM, claim.hidden_width]
        || claim.output_matmul_shape != vec![1, claim.hidden_width, OUTPUT_DIM]
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim relation shape drift".to_string(),
        ));
    }

    let expected_gate_rounds = phase53_padded_log2(INPUT_DIM)?;
    let expected_value_rounds = phase53_padded_log2(INPUT_DIM)?;
    let expected_output_rounds = phase53_padded_log2(claim.hidden_width)?;
    let expected_hadamard_rounds = phase53_padded_log2(claim.hidden_width)?;
    let expected_planned_rounds = expected_gate_rounds
        + expected_value_rounds
        + expected_output_rounds
        + expected_hadamard_rounds;
    let expected_matmul_coefficients =
        3 * (expected_gate_rounds + expected_value_rounds + expected_output_rounds);
    let expected_hadamard_coefficients = 4 * expected_hadamard_rounds;
    let expected_final_evaluations = 8;
    let expected_sumcheck_surface =
        expected_matmul_coefficients + expected_hadamard_coefficients + expected_final_evaluations;
    if claim.gate_matmul_inner_rounds != expected_gate_rounds
        || claim.value_matmul_inner_rounds != expected_value_rounds
        || claim.output_matmul_inner_rounds != expected_output_rounds
        || claim.hadamard_eq_sumcheck_rounds != expected_hadamard_rounds
        || claim.planned_sumcheck_round_count != expected_planned_rounds
        || claim.matmul_round_polynomial_coefficient_count != expected_matmul_coefficients
        || claim.hadamard_round_polynomial_coefficient_count != expected_hadamard_coefficients
        || claim.final_evaluation_count != expected_final_evaluations
        || claim.estimated_sumcheck_surface_unit_count != expected_sumcheck_surface
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim sumcheck surface drift".to_string(),
        ));
    }

    let expected_gate_terms = INPUT_DIM * claim.hidden_width;
    let expected_value_terms = INPUT_DIM * claim.hidden_width;
    let expected_output_terms = claim.hidden_width * OUTPUT_DIM;
    let expected_total_affine_terms =
        expected_gate_terms + expected_value_terms + expected_output_terms;
    let expected_bias_terms = (2 * claim.hidden_width) + OUTPUT_DIM;
    let expected_hadamard_terms = claim.hidden_width;
    let expected_naive_terms =
        expected_total_affine_terms + expected_bias_terms + expected_hadamard_terms;
    if claim.gate_affine_mul_terms != expected_gate_terms
        || claim.value_affine_mul_terms != expected_value_terms
        || claim.output_affine_mul_terms != expected_output_terms
        || claim.total_affine_mul_terms != expected_total_affine_terms
        || claim.bias_term_count != expected_bias_terms
        || claim.hadamard_term_count != expected_hadamard_terms
        || claim.naive_relation_arithmetic_term_count != expected_naive_terms
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim relation arithmetic drift".to_string(),
        ));
    }
    if claim.parameter_surface_unit_count != expected_total_affine_terms + expected_bias_terms
        || claim.activation_surface_unit_count != INPUT_DIM + (3 * claim.hidden_width) + OUTPUT_DIM
        || claim.endpoint_public_width != INPUT_DIM + OUTPUT_DIM
        || claim.tensor_route_claim_surface_unit_count
            != claim.endpoint_public_width + claim.estimated_sumcheck_surface_unit_count
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim accounting surface drift".to_string(),
        ));
    }
    if claim.verifier_side_complexity != STWO_FIRST_LAYER_RELATION_BENCHMARK_COMPLEXITY_PHASE53
        || claim.benchmark_status != STWO_FIRST_LAYER_RELATION_BENCHMARK_STATUS_PHASE53
        || claim.stwo_ml_reference != STWO_FIRST_LAYER_RELATION_BENCHMARK_STWO_ML_REFERENCE_PHASE53
        || claim.parameter_binding_scheme
            != STWO_FIRST_LAYER_RELATION_BENCHMARK_PARAMETER_BINDING_SCHEME_PHASE53
        || claim.transcript_order != phase53_benchmark_transcript_order()
        || claim.required_next_step != STWO_FIRST_LAYER_RELATION_BENCHMARK_NEXT_STEP_PHASE53
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim transcript, reference, or next-step drift"
                .to_string(),
        ));
    }
    if !claim.endpoint_anchor_available
        || claim.parameter_opening_proof_available
        || claim.affine_sumcheck_proof_available
        || claim.hadamard_product_proof_available
        || claim.actual_relation_proof_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim must not claim unavailable proof evidence"
                .to_string(),
        ));
    }
    let expected = commit_phase53_first_layer_relation_benchmark_claim(claim)?;
    if claim.benchmark_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim commitment does not match claim fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase53_first_layer_relation_benchmark_claim_against_phase52(
    claim: &Phase53FirstLayerRelationBenchmarkClaim,
    anchoring_claim: &Phase52LayerEndpointAnchoringClaim,
    relation_claim: &Phase51FirstLayerRelationClaim,
) -> Result<()> {
    let expected =
        phase53_prepare_first_layer_relation_benchmark_claim(anchoring_claim, relation_claim)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 53 first-layer relation benchmark claim does not match verified Phase52 anchoring and Phase51 relation"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase54_sumcheck_component_skeleton(
    component: &Phase54SumcheckComponentSkeleton,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 54 sumcheck component skeleton hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase54-sumcheck-component-skeleton");
    phase29_update_len_prefixed(&mut hasher, component.proof_backend.to_string().as_bytes());
    for part in [
        component
            .source_phase53_benchmark_claim_commitment
            .as_bytes(),
        component.component_name.as_bytes(),
        component.component_kind.as_bytes(),
        component.relation_field.as_bytes(),
        component.transcript_protocol.as_bytes(),
        component.round_polynomial_commitment.as_bytes(),
        component.final_evaluation_commitment.as_bytes(),
        component.opening_receipt_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase44d_update_usize_vec(&mut hasher, &component.component_shape);
    phase29_update_usize(&mut hasher, component.inner_or_domain_width);
    phase29_update_usize(&mut hasher, component.padded_inner_or_domain_width);
    phase29_update_usize(&mut hasher, component.round_count);
    phase29_update_usize(&mut hasher, component.round_polynomial_degree);
    phase29_update_usize(&mut hasher, component.round_polynomial_coefficient_count);
    phase29_update_usize(&mut hasher, component.final_evaluation_count);
    phase29_update_usize(&mut hasher, component.runtime_tensor_opening_count);
    phase29_update_usize(&mut hasher, component.parameter_opening_count);
    phase29_update_bool(&mut hasher, component.typed_proof_skeleton_available);
    phase29_update_bool(
        &mut hasher,
        component.actual_round_polynomial_values_available,
    );
    phase29_update_bool(&mut hasher, component.actual_opening_proofs_available);
    phase29_update_bool(&mut hasher, component.cryptographic_soundness_claimed);
    phase44d_finalize_hash(hasher, "Phase 54 sumcheck component skeleton")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase54_parameter_opening_skeleton(
    opening: &Phase54ParameterOpeningSkeleton,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 54 parameter opening skeleton hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase54-parameter-opening-skeleton");
    phase29_update_len_prefixed(&mut hasher, opening.proof_backend.to_string().as_bytes());
    for part in [
        opening.source_phase53_benchmark_claim_commitment.as_bytes(),
        opening
            .source_phase53_parameter_binding_commitment
            .as_bytes(),
        opening.parameter_name.as_bytes(),
        opening.parameter_role.as_bytes(),
        opening.opening_scheme.as_bytes(),
        opening.opening_receipt_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase44d_update_usize_vec(&mut hasher, &opening.tensor_shape);
    phase29_update_usize(&mut hasher, opening.logical_element_count);
    phase29_update_usize(&mut hasher, opening.padded_element_count);
    phase29_update_usize(&mut hasher, opening.opening_point_dimension);
    phase29_update_usize(&mut hasher, opening.opening_value_count);
    phase29_update_bool(&mut hasher, opening.opening_proof_available);
    phase29_update_bool(&mut hasher, opening.cryptographic_soundness_claimed);
    phase44d_finalize_hash(hasher, "Phase 54 parameter opening skeleton")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase54_first_layer_sumcheck_skeleton_claim(
    claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 54 first-layer sumcheck skeleton claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase54-first-layer-sumcheck-skeleton-claim");
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase53_benchmark_claim_commitment.as_bytes(),
        claim.source_phase52_anchoring_claim_commitment.as_bytes(),
        claim.source_phase51_relation_claim_commitment.as_bytes(),
        claim.source_phase50_layer_io_claim_commitment.as_bytes(),
        claim.source_phase53_parameter_binding_commitment.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.skeleton_status.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    for component in &claim.component_claims {
        phase29_update_len_prefixed(&mut hasher, component.component_claim_commitment.as_bytes());
    }
    for opening in &claim.parameter_opening_claims {
        phase29_update_len_prefixed(
            &mut hasher,
            opening.parameter_opening_claim_commitment.as_bytes(),
        );
    }
    phase29_update_usize(&mut hasher, claim.component_count);
    phase29_update_usize(&mut hasher, claim.parameter_opening_count);
    phase29_update_usize(&mut hasher, claim.total_round_count);
    phase29_update_usize(&mut hasher, claim.total_round_polynomial_coefficient_count);
    phase29_update_usize(&mut hasher, claim.total_final_evaluation_count);
    phase29_update_usize(&mut hasher, claim.total_runtime_tensor_opening_count);
    phase29_update_usize(&mut hasher, claim.total_parameter_opening_count);
    phase29_update_usize(&mut hasher, claim.total_mle_opening_claim_count);
    phase29_update_usize(&mut hasher, claim.typed_proof_object_surface_unit_count);
    phase29_update_usize(
        &mut hasher,
        claim.phase53_estimated_sumcheck_surface_unit_count,
    );
    phase29_update_usize(&mut hasher, claim.endpoint_public_width);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.typed_sumcheck_skeleton_available);
    phase29_update_bool(&mut hasher, claim.actual_sumcheck_verifier_available);
    phase29_update_bool(
        &mut hasher,
        claim.actual_parameter_opening_verifier_available,
    );
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 54 first-layer sumcheck skeleton claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase54_prepare_first_layer_sumcheck_skeleton_claim(
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<Phase54FirstLayerSumcheckSkeletonClaim> {
    verify_phase53_first_layer_relation_benchmark_claim(phase53_claim)?;
    let component_claims = phase54_prepare_sumcheck_component_skeletons(phase53_claim)?;
    let parameter_opening_claims = phase54_prepare_parameter_opening_skeletons(phase53_claim)?;
    let component_count = component_claims.len();
    let parameter_opening_count = parameter_opening_claims.len();
    let total_round_count = component_claims
        .iter()
        .map(|component| component.round_count)
        .sum();
    let total_round_polynomial_coefficient_count = component_claims
        .iter()
        .map(|component| component.round_polynomial_coefficient_count)
        .sum();
    let total_final_evaluation_count = component_claims
        .iter()
        .map(|component| component.final_evaluation_count)
        .sum();
    let total_runtime_tensor_opening_count = component_claims
        .iter()
        .map(|component| component.runtime_tensor_opening_count)
        .sum();
    let total_parameter_opening_count = component_claims
        .iter()
        .map(|component| component.parameter_opening_count)
        .sum();
    let total_mle_opening_claim_count =
        total_runtime_tensor_opening_count + total_parameter_opening_count;
    let typed_proof_object_surface_unit_count = total_round_polynomial_coefficient_count
        + total_final_evaluation_count
        + total_mle_opening_claim_count
        + component_count
        + parameter_opening_count;
    let mut claim = Phase54FirstLayerSumcheckSkeletonClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_VERSION_PHASE54.to_string(),
        semantic_scope: STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_SCOPE_PHASE54.to_string(),
        source_phase53_benchmark_claim_commitment: phase53_claim.benchmark_claim_commitment.clone(),
        source_phase52_anchoring_claim_commitment: phase53_claim
            .source_phase52_anchoring_claim_commitment
            .clone(),
        source_phase51_relation_claim_commitment: phase53_claim
            .source_phase51_relation_claim_commitment
            .clone(),
        source_phase50_layer_io_claim_commitment: phase53_claim
            .source_phase50_layer_io_claim_commitment
            .clone(),
        source_phase53_parameter_binding_commitment: phase53_claim
            .parameter_binding_commitment
            .clone(),
        component_claims,
        parameter_opening_claims,
        component_count,
        parameter_opening_count,
        total_round_count,
        total_round_polynomial_coefficient_count,
        total_final_evaluation_count,
        total_runtime_tensor_opening_count,
        total_parameter_opening_count,
        total_mle_opening_claim_count,
        typed_proof_object_surface_unit_count,
        phase53_estimated_sumcheck_surface_unit_count: phase53_claim
            .estimated_sumcheck_surface_unit_count,
        endpoint_public_width: phase53_claim.endpoint_public_width,
        verifier_side_complexity: STWO_FIRST_LAYER_SUMCHECK_SKELETON_COMPLEXITY_PHASE54.to_string(),
        skeleton_status: STWO_FIRST_LAYER_SUMCHECK_SKELETON_STATUS_PHASE54.to_string(),
        transcript_order: phase54_skeleton_transcript_order(),
        typed_sumcheck_skeleton_available: true,
        actual_sumcheck_verifier_available: false,
        actual_parameter_opening_verifier_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        required_next_step: STWO_FIRST_LAYER_SUMCHECK_SKELETON_NEXT_STEP_PHASE54.to_string(),
        skeleton_claim_commitment: String::new(),
    };
    claim.skeleton_claim_commitment = commit_phase54_first_layer_sumcheck_skeleton_claim(&claim)?;
    verify_phase54_first_layer_sumcheck_skeleton_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase54_sumcheck_component_skeleton(
    component: &Phase54SumcheckComponentSkeleton,
) -> Result<()> {
    if component.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 54 sumcheck component skeleton requires `stwo` backend".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase54_component_source_phase53_benchmark_claim_commitment",
            component.source_phase53_benchmark_claim_commitment.as_str(),
        ),
        (
            "phase54_round_polynomial_commitment",
            component.round_polynomial_commitment.as_str(),
        ),
        (
            "phase54_final_evaluation_commitment",
            component.final_evaluation_commitment.as_str(),
        ),
        (
            "phase54_opening_receipt_commitment",
            component.opening_receipt_commitment.as_str(),
        ),
        (
            "phase54_component_claim_commitment",
            component.component_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let (
        expected_kind,
        expected_shape,
        expected_inner_width,
        expected_degree,
        expected_runtime_openings,
        expected_parameter_openings,
    ) = phase54_component_spec(&component.component_name)?;
    let expected_round_count = phase53_padded_log2(expected_inner_width)?;
    let expected_padded_width = phase50_next_power_of_two(expected_inner_width)?;
    if component.component_kind != expected_kind
        || component.relation_field != STWO_FIRST_LAYER_RELATION_FIELD_PHASE51
        || component.component_shape != expected_shape
        || component.inner_or_domain_width != expected_inner_width
        || component.padded_inner_or_domain_width != expected_padded_width
        || component.round_count != expected_round_count
        || component.round_polynomial_degree != expected_degree
        || component.round_polynomial_coefficient_count
            != expected_round_count * (expected_degree + 1)
        || component.final_evaluation_count != 2
        || component.runtime_tensor_opening_count != expected_runtime_openings
        || component.parameter_opening_count != expected_parameter_openings
        || component.transcript_protocol
            != STWO_FIRST_LAYER_SUMCHECK_SKELETON_TRANSCRIPT_PROTOCOL_PHASE54
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 sumcheck component skeleton shape or surface drift".to_string(),
        ));
    }
    let expected_round_commitment = phase54_derive_artifact_commitment(
        &component.source_phase53_benchmark_claim_commitment,
        &component.component_name,
        "round_polynomials",
        &component.component_shape,
        component.round_count,
        component.round_polynomial_degree,
    )?;
    let expected_final_commitment = phase54_derive_artifact_commitment(
        &component.source_phase53_benchmark_claim_commitment,
        &component.component_name,
        "final_evaluations",
        &component.component_shape,
        component.final_evaluation_count,
        component.round_polynomial_degree,
    )?;
    let expected_opening_commitment = phase54_derive_artifact_commitment(
        &component.source_phase53_benchmark_claim_commitment,
        &component.component_name,
        "opening_receipts",
        &component.component_shape,
        component.runtime_tensor_opening_count + component.parameter_opening_count,
        component.round_polynomial_degree,
    )?;
    if component.round_polynomial_commitment != expected_round_commitment
        || component.final_evaluation_commitment != expected_final_commitment
        || component.opening_receipt_commitment != expected_opening_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 sumcheck component skeleton artifact commitment drift".to_string(),
        ));
    }
    if !component.typed_proof_skeleton_available
        || component.actual_round_polynomial_values_available
        || component.actual_opening_proofs_available
        || component.cryptographic_soundness_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 sumcheck component skeleton must stay typed-skeleton-only".to_string(),
        ));
    }
    let expected = commit_phase54_sumcheck_component_skeleton(component)?;
    if component.component_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 54 sumcheck component skeleton commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase54_parameter_opening_skeleton(
    opening: &Phase54ParameterOpeningSkeleton,
) -> Result<()> {
    if opening.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 54 parameter opening skeleton requires `stwo` backend".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase54_parameter_source_phase53_benchmark_claim_commitment",
            opening.source_phase53_benchmark_claim_commitment.as_str(),
        ),
        (
            "phase54_parameter_source_binding_commitment",
            opening.source_phase53_parameter_binding_commitment.as_str(),
        ),
        (
            "phase54_parameter_opening_receipt_commitment",
            opening.opening_receipt_commitment.as_str(),
        ),
        (
            "phase54_parameter_opening_claim_commitment",
            opening.parameter_opening_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let (expected_role, expected_shape) = phase54_parameter_opening_spec(&opening.parameter_name)?;
    let expected_logical_element_count = phase50_tensor_element_count(&expected_shape)?;
    let expected_padded_element_count = phase50_next_power_of_two(expected_logical_element_count)?;
    if opening.parameter_role != expected_role
        || opening.tensor_shape != expected_shape
        || opening.logical_element_count != expected_logical_element_count
        || opening.padded_element_count != expected_padded_element_count
        || opening.opening_point_dimension != phase53_padded_log2(expected_logical_element_count)?
        || opening.opening_value_count != 1
        || opening.opening_scheme
            != STWO_FIRST_LAYER_SUMCHECK_SKELETON_PARAMETER_OPENING_SCHEME_PHASE54
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 parameter opening skeleton shape or opening surface drift".to_string(),
        ));
    }
    let expected_receipt = phase54_derive_artifact_commitment(
        &opening.source_phase53_benchmark_claim_commitment,
        &opening.parameter_name,
        "parameter_opening_receipt",
        &opening.tensor_shape,
        opening.opening_point_dimension,
        opening.opening_value_count,
    )?;
    if opening.opening_receipt_commitment != expected_receipt {
        return Err(VmError::InvalidConfig(
            "Phase 54 parameter opening skeleton receipt commitment drift".to_string(),
        ));
    }
    if opening.opening_proof_available || opening.cryptographic_soundness_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 54 parameter opening skeleton must not claim unavailable opening proof"
                .to_string(),
        ));
    }
    let expected = commit_phase54_parameter_opening_skeleton(opening)?;
    if opening.parameter_opening_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 54 parameter opening skeleton commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase54_first_layer_sumcheck_skeleton_claim(
    claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_VERSION_PHASE54
        || claim.semantic_scope != STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_SCOPE_PHASE54
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim version or semantic scope drift"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase54_source_phase53_benchmark_claim_commitment",
            claim.source_phase53_benchmark_claim_commitment.as_str(),
        ),
        (
            "phase54_source_phase52_anchoring_claim_commitment",
            claim.source_phase52_anchoring_claim_commitment.as_str(),
        ),
        (
            "phase54_source_phase51_relation_claim_commitment",
            claim.source_phase51_relation_claim_commitment.as_str(),
        ),
        (
            "phase54_source_phase50_layer_io_claim_commitment",
            claim.source_phase50_layer_io_claim_commitment.as_str(),
        ),
        (
            "phase54_source_phase53_parameter_binding_commitment",
            claim.source_phase53_parameter_binding_commitment.as_str(),
        ),
        (
            "phase54_skeleton_claim_commitment",
            claim.skeleton_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if claim.component_claims.len() != phase54_component_order().len()
        || claim.parameter_opening_claims.len() != phase54_parameter_opening_order().len()
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim component count drift".to_string(),
        ));
    }
    for (component, expected_name) in claim.component_claims.iter().zip(phase54_component_order()) {
        verify_phase54_sumcheck_component_skeleton(component)?;
        if component.component_name != expected_name
            || component.source_phase53_benchmark_claim_commitment
                != claim.source_phase53_benchmark_claim_commitment
        {
            return Err(VmError::InvalidConfig(
                "Phase 54 first-layer sumcheck skeleton claim component order or source drift"
                    .to_string(),
            ));
        }
    }
    for (opening, expected_name) in claim
        .parameter_opening_claims
        .iter()
        .zip(phase54_parameter_opening_order())
    {
        verify_phase54_parameter_opening_skeleton(opening)?;
        if opening.parameter_name != expected_name
            || opening.source_phase53_benchmark_claim_commitment
                != claim.source_phase53_benchmark_claim_commitment
            || opening.source_phase53_parameter_binding_commitment
                != claim.source_phase53_parameter_binding_commitment
        {
            return Err(VmError::InvalidConfig(
                "Phase 54 first-layer sumcheck skeleton claim parameter opening order or source drift"
                    .to_string(),
            ));
        }
    }
    let component_count = claim.component_claims.len();
    let parameter_opening_count = claim.parameter_opening_claims.len();
    let total_round_count: usize = claim
        .component_claims
        .iter()
        .map(|component| component.round_count)
        .sum();
    let total_round_polynomial_coefficient_count: usize = claim
        .component_claims
        .iter()
        .map(|component| component.round_polynomial_coefficient_count)
        .sum();
    let total_final_evaluation_count: usize = claim
        .component_claims
        .iter()
        .map(|component| component.final_evaluation_count)
        .sum();
    let total_runtime_tensor_opening_count: usize = claim
        .component_claims
        .iter()
        .map(|component| component.runtime_tensor_opening_count)
        .sum();
    let total_parameter_opening_count: usize = claim
        .component_claims
        .iter()
        .map(|component| component.parameter_opening_count)
        .sum();
    let total_mle_opening_claim_count =
        total_runtime_tensor_opening_count + total_parameter_opening_count;
    let typed_proof_object_surface_unit_count = total_round_polynomial_coefficient_count
        + total_final_evaluation_count
        + total_mle_opening_claim_count
        + component_count
        + parameter_opening_count;
    if claim.component_count != component_count
        || claim.parameter_opening_count != parameter_opening_count
        || claim.total_round_count != total_round_count
        || claim.total_round_polynomial_coefficient_count
            != total_round_polynomial_coefficient_count
        || claim.total_final_evaluation_count != total_final_evaluation_count
        || claim.total_runtime_tensor_opening_count != total_runtime_tensor_opening_count
        || claim.total_parameter_opening_count != total_parameter_opening_count
        || claim.total_mle_opening_claim_count != total_mle_opening_claim_count
        || claim.typed_proof_object_surface_unit_count != typed_proof_object_surface_unit_count
        || claim.phase53_estimated_sumcheck_surface_unit_count != 93
        || claim.endpoint_public_width != INPUT_DIM + OUTPUT_DIM
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim surface accounting drift".to_string(),
        ));
    }
    if claim.verifier_side_complexity != STWO_FIRST_LAYER_SUMCHECK_SKELETON_COMPLEXITY_PHASE54
        || claim.skeleton_status != STWO_FIRST_LAYER_SUMCHECK_SKELETON_STATUS_PHASE54
        || claim.transcript_order != phase54_skeleton_transcript_order()
        || claim.required_next_step != STWO_FIRST_LAYER_SUMCHECK_SKELETON_NEXT_STEP_PHASE54
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim transcript, status, or next-step drift"
                .to_string(),
        ));
    }
    if !claim.typed_sumcheck_skeleton_available
        || claim.actual_sumcheck_verifier_available
        || claim.actual_parameter_opening_verifier_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim must not claim unavailable verification or compression"
                .to_string(),
        ));
    }
    let expected = commit_phase54_first_layer_sumcheck_skeleton_claim(claim)?;
    if claim.skeleton_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim commitment does not match fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase54_first_layer_sumcheck_skeleton_claim_against_phase53(
    claim: &Phase54FirstLayerSumcheckSkeletonClaim,
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<()> {
    let expected = phase54_prepare_first_layer_sumcheck_skeleton_claim(phase53_claim)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 54 first-layer sumcheck skeleton claim does not match verified Phase53 benchmark claim"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase55_first_layer_compression_effectiveness_claim(
    claim: &Phase55FirstLayerCompressionEffectivenessClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 55 compression effectiveness claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase55-first-layer-compression-effectiveness-claim",
    );
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase54_skeleton_claim_commitment.as_bytes(),
        claim.source_phase53_benchmark_claim_commitment.as_bytes(),
        claim.measurement_kind.as_bytes(),
        claim.decision.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, claim.naive_relation_arithmetic_term_count);
    phase29_update_usize(&mut hasher, claim.parameter_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.endpoint_public_width);
    phase29_update_usize(&mut hasher, claim.vm_replay_surface_proxy_unit_count);
    phase29_update_usize(&mut hasher, claim.tensor_proof_skeleton_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.tensor_sumcheck_round_count);
    phase29_update_usize(&mut hasher, claim.tensor_round_polynomial_coefficient_count);
    phase29_update_usize(&mut hasher, claim.tensor_mle_opening_claim_count);
    phase29_update_usize(&mut hasher, claim.tensor_component_count);
    phase29_update_usize(&mut hasher, claim.tensor_parameter_opening_count);
    phase29_update_usize(&mut hasher, claim.tensor_to_vm_surface_proxy_basis_points);
    phase29_update_usize(&mut hasher, claim.surface_proxy_reduction_basis_points);
    phase29_update_bool(&mut hasher, claim.verifier_surface_is_smaller_than_vm_proxy);
    phase29_update_bool(&mut hasher, claim.positive_breakthrough_signal);
    phase29_update_bool(&mut hasher, claim.actual_proof_byte_benchmark_available);
    phase29_update_bool(&mut hasher, claim.executable_sumcheck_verifier_available);
    phase29_update_bool(&mut hasher, claim.breakthrough_claimed);
    phase29_update_bool(&mut hasher, claim.paper_ready);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase44d_finalize_hash(hasher, "Phase 55 compression effectiveness claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase55_prepare_first_layer_compression_effectiveness_claim(
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<Phase55FirstLayerCompressionEffectivenessClaim> {
    verify_phase54_first_layer_sumcheck_skeleton_claim_against_phase53(
        phase54_claim,
        phase53_claim,
    )?;
    let vm_replay_surface_proxy_unit_count = phase53_claim
        .naive_relation_arithmetic_term_count
        .checked_add(phase53_claim.parameter_surface_unit_count)
        .and_then(|count| count.checked_add(phase53_claim.endpoint_public_width))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 55 VM replay surface proxy accounting overflow".to_string(),
            )
        })?;
    let tensor_surface = phase54_claim.typed_proof_object_surface_unit_count;
    let tensor_to_vm_surface_proxy_basis_points =
        phase55_ratio_basis_points(tensor_surface, vm_replay_surface_proxy_unit_count)?;
    let surface_proxy_reduction_basis_points = phase55_ratio_basis_points(
        vm_replay_surface_proxy_unit_count.saturating_sub(tensor_surface),
        vm_replay_surface_proxy_unit_count,
    )?;
    let mut claim = Phase55FirstLayerCompressionEffectivenessClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_VERSION_PHASE55.to_string(),
        semantic_scope: STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_SCOPE_PHASE55.to_string(),
        source_phase54_skeleton_claim_commitment: phase54_claim.skeleton_claim_commitment.clone(),
        source_phase53_benchmark_claim_commitment: phase53_claim.benchmark_claim_commitment.clone(),
        measurement_kind: STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_MEASUREMENT_PHASE55
            .to_string(),
        naive_relation_arithmetic_term_count: phase53_claim.naive_relation_arithmetic_term_count,
        parameter_surface_unit_count: phase53_claim.parameter_surface_unit_count,
        endpoint_public_width: phase53_claim.endpoint_public_width,
        vm_replay_surface_proxy_unit_count,
        tensor_proof_skeleton_surface_unit_count: tensor_surface,
        tensor_sumcheck_round_count: phase54_claim.total_round_count,
        tensor_round_polynomial_coefficient_count: phase54_claim
            .total_round_polynomial_coefficient_count,
        tensor_mle_opening_claim_count: phase54_claim.total_mle_opening_claim_count,
        tensor_component_count: phase54_claim.component_count,
        tensor_parameter_opening_count: phase54_claim.parameter_opening_count,
        tensor_to_vm_surface_proxy_basis_points,
        surface_proxy_reduction_basis_points,
        verifier_surface_is_smaller_than_vm_proxy: tensor_surface
            < vm_replay_surface_proxy_unit_count,
        positive_breakthrough_signal: tensor_to_vm_surface_proxy_basis_points < 1_000,
        actual_proof_byte_benchmark_available: false,
        executable_sumcheck_verifier_available: false,
        breakthrough_claimed: false,
        paper_ready: false,
        decision: STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_DECISION_PHASE55.to_string(),
        required_next_step: STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_NEXT_STEP_PHASE55
            .to_string(),
        transcript_order: phase55_effectiveness_transcript_order(),
        effectiveness_claim_commitment: String::new(),
    };
    claim.effectiveness_claim_commitment =
        commit_phase55_first_layer_compression_effectiveness_claim(&claim)?;
    verify_phase55_first_layer_compression_effectiveness_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase55_first_layer_compression_effectiveness_claim(
    claim: &Phase55FirstLayerCompressionEffectivenessClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_VERSION_PHASE55
        || claim.semantic_scope != STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_SCOPE_PHASE55
    {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim version or semantic scope drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase55_source_phase54_skeleton_claim_commitment",
            claim.source_phase54_skeleton_claim_commitment.as_str(),
        ),
        (
            "phase55_source_phase53_benchmark_claim_commitment",
            claim.source_phase53_benchmark_claim_commitment.as_str(),
        ),
        (
            "phase55_effectiveness_claim_commitment",
            claim.effectiveness_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected_vm_proxy = claim
        .naive_relation_arithmetic_term_count
        .checked_add(claim.parameter_surface_unit_count)
        .and_then(|count| count.checked_add(claim.endpoint_public_width))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 55 compression effectiveness claim VM proxy accounting overflow".to_string(),
            )
        })?;
    let expected_tensor_ratio = phase55_ratio_basis_points(
        claim.tensor_proof_skeleton_surface_unit_count,
        expected_vm_proxy,
    )?;
    let expected_reduction_ratio = phase55_ratio_basis_points(
        expected_vm_proxy.saturating_sub(claim.tensor_proof_skeleton_surface_unit_count),
        expected_vm_proxy,
    )?;
    if claim.measurement_kind != STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_MEASUREMENT_PHASE55
        || claim.naive_relation_arithmetic_term_count != 6_558
        || claim.parameter_surface_unit_count != 6_486
        || claim.endpoint_public_width != INPUT_DIM + OUTPUT_DIM
        || claim.vm_replay_surface_proxy_unit_count != expected_vm_proxy
        || claim.tensor_proof_skeleton_surface_unit_count != 114
        || claim.tensor_sumcheck_round_count != 26
        || claim.tensor_round_polynomial_coefficient_count != 85
        || claim.tensor_mle_opening_claim_count != 11
        || claim.tensor_component_count != 4
        || claim.tensor_parameter_opening_count != 6
        || claim.tensor_to_vm_surface_proxy_basis_points != expected_tensor_ratio
        || claim.surface_proxy_reduction_basis_points != expected_reduction_ratio
    {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim surface measurement drift".to_string(),
        ));
    }
    if !claim.verifier_surface_is_smaller_than_vm_proxy
        || !claim.positive_breakthrough_signal
        || claim.actual_proof_byte_benchmark_available
        || claim.executable_sumcheck_verifier_available
        || claim.breakthrough_claimed
        || claim.paper_ready
    {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim must stay positive-signal-only without false breakthrough claims"
                .to_string(),
        ));
    }
    if claim.decision != STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_DECISION_PHASE55
        || claim.required_next_step != STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_NEXT_STEP_PHASE55
        || claim.transcript_order != phase55_effectiveness_transcript_order()
    {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim decision or transcript drift".to_string(),
        ));
    }
    let expected = commit_phase55_first_layer_compression_effectiveness_claim(claim)?;
    if claim.effectiveness_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase55_first_layer_compression_effectiveness_claim_against_phase54(
    claim: &Phase55FirstLayerCompressionEffectivenessClaim,
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<()> {
    let expected =
        phase55_prepare_first_layer_compression_effectiveness_claim(phase54_claim, phase53_claim)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 55 compression effectiveness claim does not match verified Phase54 skeleton and Phase53 benchmark"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase56_round_polynomial(round: &Phase56RoundPolynomial) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 56 round polynomial hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase56-round-polynomial");
    phase29_update_usize(&mut hasher, round.round_index);
    phase29_update_usize(&mut hasher, round.degree);
    phase44d_update_u32_vec(&mut hasher, &round.coefficients);
    phase44d_finalize_hash(hasher, "Phase 56 round polynomial")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase56_executable_sumcheck_component_proof(
    proof: &Phase56ExecutableSumcheckComponentProof,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 56 executable sumcheck component proof hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase56-executable-sumcheck-component-proof");
    phase29_update_len_prefixed(&mut hasher, proof.proof_backend.to_string().as_bytes());
    for part in [
        proof.source_phase54_component_claim_commitment.as_bytes(),
        proof.component_name.as_bytes(),
        proof.component_kind.as_bytes(),
        proof.relation_field.as_bytes(),
        proof.terminal_check_rule.as_bytes(),
        proof.transcript_protocol.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_usize(&mut hasher, proof.round_count);
    phase29_update_usize(&mut hasher, proof.round_polynomial_degree);
    hasher.update(&proof.claimed_sum.to_le_bytes());
    for round in &proof.round_polynomials {
        phase29_update_len_prefixed(&mut hasher, round.polynomial_commitment.as_bytes());
    }
    phase44d_update_u32_vec(&mut hasher, &proof.derived_challenges);
    phase44d_update_u32_vec(&mut hasher, &proof.final_evaluations);
    hasher.update(&proof.terminal_sum.to_le_bytes());
    phase29_update_bool(&mut hasher, proof.executable_round_check_available);
    phase29_update_bool(&mut hasher, proof.mle_opening_verifier_available);
    phase29_update_bool(&mut hasher, proof.relation_witness_binding_available);
    phase29_update_bool(&mut hasher, proof.cryptographic_soundness_claimed);
    phase44d_finalize_hash(hasher, "Phase 56 executable sumcheck component proof")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase56_first_layer_executable_sumcheck_claim(
    claim: &Phase56FirstLayerExecutableSumcheckClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 56 first-layer executable sumcheck claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase56-first-layer-executable-sumcheck-claim",
    );
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase54_skeleton_claim_commitment.as_bytes(),
        claim.source_phase53_benchmark_claim_commitment.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.executable_status.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    for component in &claim.component_proofs {
        phase29_update_len_prefixed(&mut hasher, component.component_proof_commitment.as_bytes());
    }
    phase29_update_usize(&mut hasher, claim.component_count);
    phase29_update_usize(&mut hasher, claim.total_round_count);
    phase29_update_usize(&mut hasher, claim.total_round_polynomial_count);
    phase29_update_usize(&mut hasher, claim.total_round_polynomial_coefficient_count);
    phase29_update_usize(&mut hasher, claim.total_final_evaluation_count);
    phase29_update_usize(&mut hasher, claim.executable_round_check_count);
    phase29_update_usize(&mut hasher, claim.terminal_check_count);
    phase29_update_usize(
        &mut hasher,
        claim.phase54_typed_proof_object_surface_unit_count,
    );
    phase29_update_usize(&mut hasher, claim.executable_verifier_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.surface_delta_from_phase54);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(
        &mut hasher,
        claim.executable_sumcheck_round_verifier_available,
    );
    phase29_update_bool(&mut hasher, claim.executable_mle_opening_verifier_available);
    phase29_update_bool(&mut hasher, claim.relation_witness_binding_available);
    phase29_update_bool(&mut hasher, claim.actual_proof_byte_benchmark_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase44d_finalize_hash(hasher, "Phase 56 first-layer executable sumcheck claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase56_prepare_first_layer_executable_sumcheck_claim(
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<Phase56FirstLayerExecutableSumcheckClaim> {
    verify_phase54_first_layer_sumcheck_skeleton_claim(phase54_claim)?;
    let component_proofs = phase54_claim
        .component_claims
        .iter()
        .map(phase56_prepare_executable_component_proof)
        .collect::<Result<Vec<_>>>()?;
    let component_count = component_proofs.len();
    let total_round_count: usize = component_proofs.iter().map(|proof| proof.round_count).sum();
    let total_round_polynomial_count: usize = component_proofs
        .iter()
        .map(|proof| proof.round_polynomials.len())
        .sum();
    let total_round_polynomial_coefficient_count: usize = component_proofs
        .iter()
        .flat_map(|proof| proof.round_polynomials.iter())
        .map(|round| round.coefficients.len())
        .sum();
    let total_final_evaluation_count: usize = component_proofs
        .iter()
        .map(|proof| proof.final_evaluations.len())
        .sum();
    let executable_round_check_count = total_round_count;
    let terminal_check_count = component_count;
    let executable_verifier_surface_unit_count = total_round_polynomial_coefficient_count
        + total_final_evaluation_count
        + executable_round_check_count
        + terminal_check_count;
    let surface_delta_from_phase54 = executable_verifier_surface_unit_count
        .saturating_sub(phase54_claim.typed_proof_object_surface_unit_count);
    let mut claim = Phase56FirstLayerExecutableSumcheckClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_VERSION_PHASE56.to_string(),
        semantic_scope: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_SCOPE_PHASE56.to_string(),
        source_phase54_skeleton_claim_commitment: phase54_claim.skeleton_claim_commitment.clone(),
        source_phase53_benchmark_claim_commitment: phase54_claim
            .source_phase53_benchmark_claim_commitment
            .clone(),
        component_proofs,
        component_count,
        total_round_count,
        total_round_polynomial_count,
        total_round_polynomial_coefficient_count,
        total_final_evaluation_count,
        executable_round_check_count,
        terminal_check_count,
        phase54_typed_proof_object_surface_unit_count: phase54_claim
            .typed_proof_object_surface_unit_count,
        executable_verifier_surface_unit_count,
        surface_delta_from_phase54,
        verifier_side_complexity: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_COMPLEXITY_PHASE56
            .to_string(),
        executable_status: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_STATUS_PHASE56.to_string(),
        transcript_order: phase56_executable_transcript_order(),
        executable_sumcheck_round_verifier_available: true,
        executable_mle_opening_verifier_available: false,
        relation_witness_binding_available: false,
        actual_proof_byte_benchmark_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        required_next_step: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_NEXT_STEP_PHASE56.to_string(),
        executable_claim_commitment: String::new(),
    };
    claim.executable_claim_commitment =
        commit_phase56_first_layer_executable_sumcheck_claim(&claim)?;
    verify_phase56_first_layer_executable_sumcheck_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase56_executable_sumcheck_component_proof(
    proof: &Phase56ExecutableSumcheckComponentProof,
) -> Result<()> {
    if proof.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck component proof requires `stwo` backend".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase56_source_phase54_component_claim_commitment",
            proof.source_phase54_component_claim_commitment.as_str(),
        ),
        (
            "phase56_component_proof_commitment",
            proof.component_proof_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let (expected_kind, _, expected_inner_width, expected_degree, _, _) =
        phase54_component_spec(&proof.component_name)?;
    if proof.component_kind != expected_kind
        || proof.relation_field != STWO_FIRST_LAYER_RELATION_FIELD_PHASE51
        || proof.round_count != phase53_padded_log2(expected_inner_width)?
        || proof.round_polynomial_degree != expected_degree
        || proof.round_polynomials.len() != proof.round_count
        || proof.derived_challenges.len() != proof.round_count
        || proof.final_evaluations.len() != 2
        || proof.terminal_check_rule != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_TERMINAL_RULE_PHASE56
        || proof.transcript_protocol
            != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_TRANSCRIPT_PROTOCOL_PHASE56
    {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck component proof shape or transcript drift".to_string(),
        ));
    }
    phase52_validate_m31_values("phase56_final_evaluations", &proof.final_evaluations)?;
    if proof.claimed_sum >= PHASE44D_M31_MODULUS || proof.terminal_sum >= PHASE44D_M31_MODULUS {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck component proof sum exceeds M31 capacity".to_string(),
        ));
    }
    let mut current_sum = proof.claimed_sum;
    for (round_index, round) in proof.round_polynomials.iter().enumerate() {
        if round.round_index != round_index
            || round.degree != proof.round_polynomial_degree
            || round.coefficients.len() != proof.round_polynomial_degree + 1
        {
            return Err(VmError::InvalidConfig(
                "Phase 56 executable sumcheck round polynomial shape drift".to_string(),
            ));
        }
        phase52_validate_m31_values("phase56_round_coefficients", &round.coefficients)?;
        let expected_round_commitment = commit_phase56_round_polynomial(round)?;
        if round.polynomial_commitment != expected_round_commitment {
            return Err(VmError::InvalidConfig(
                "Phase 56 executable sumcheck round polynomial commitment drift".to_string(),
            ));
        }
        let round_zero = round.coefficients[0];
        let round_one = phase56_eval_round_polynomial(&round.coefficients, 1)?;
        if phase52_m31_add(round_zero, round_one) != current_sum {
            return Err(VmError::InvalidConfig(
                "Phase 56 executable sumcheck round consistency check failed".to_string(),
            ));
        }
        let expected_challenge = phase56_derive_round_challenge(
            &proof.source_phase54_component_claim_commitment,
            &proof.component_name,
            round_index,
            &round.polynomial_commitment,
        )?;
        if proof.derived_challenges[round_index] != expected_challenge {
            return Err(VmError::InvalidConfig(
                "Phase 56 executable sumcheck challenge derivation drift".to_string(),
            ));
        }
        current_sum = phase56_eval_round_polynomial(&round.coefficients, expected_challenge)?;
    }
    let expected_terminal = phase52_m31_mul(proof.final_evaluations[0], proof.final_evaluations[1]);
    if proof.terminal_sum != current_sum || proof.terminal_sum != expected_terminal {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck terminal check failed".to_string(),
        ));
    }
    if !proof.executable_round_check_available
        || proof.mle_opening_verifier_available
        || proof.relation_witness_binding_available
        || proof.cryptographic_soundness_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck component proof must not claim unavailable opening, witness, or soundness evidence"
                .to_string(),
        ));
    }
    let expected = commit_phase56_executable_sumcheck_component_proof(proof)?;
    if proof.component_proof_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck component proof commitment does not match fields"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase56_first_layer_executable_sumcheck_claim(
    claim: &Phase56FirstLayerExecutableSumcheckClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_VERSION_PHASE56
        || claim.semantic_scope != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_SCOPE_PHASE56
    {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim version or semantic scope drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase56_source_phase54_skeleton_claim_commitment",
            claim.source_phase54_skeleton_claim_commitment.as_str(),
        ),
        (
            "phase56_source_phase53_benchmark_claim_commitment",
            claim.source_phase53_benchmark_claim_commitment.as_str(),
        ),
        (
            "phase56_executable_claim_commitment",
            claim.executable_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if claim.component_proofs.len() != phase54_component_order().len() {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim component count drift".to_string(),
        ));
    }
    for (proof, expected_name) in claim.component_proofs.iter().zip(phase54_component_order()) {
        verify_phase56_executable_sumcheck_component_proof(proof)?;
        if proof.component_name != expected_name {
            return Err(VmError::InvalidConfig(
                "Phase 56 executable sumcheck claim component order drift".to_string(),
            ));
        }
    }
    let component_count = claim.component_proofs.len();
    let total_round_count: usize = claim
        .component_proofs
        .iter()
        .map(|proof| proof.round_count)
        .sum();
    let total_round_polynomial_count: usize = claim
        .component_proofs
        .iter()
        .map(|proof| proof.round_polynomials.len())
        .sum();
    let total_round_polynomial_coefficient_count: usize = claim
        .component_proofs
        .iter()
        .flat_map(|proof| proof.round_polynomials.iter())
        .map(|round| round.coefficients.len())
        .sum();
    let total_final_evaluation_count: usize = claim
        .component_proofs
        .iter()
        .map(|proof| proof.final_evaluations.len())
        .sum();
    let executable_surface = total_round_polynomial_coefficient_count
        + total_final_evaluation_count
        + total_round_count
        + component_count;
    if claim.component_count != component_count
        || claim.total_round_count != total_round_count
        || claim.total_round_polynomial_count != total_round_polynomial_count
        || claim.total_round_polynomial_coefficient_count
            != total_round_polynomial_coefficient_count
        || claim.total_final_evaluation_count != total_final_evaluation_count
        || claim.executable_round_check_count != total_round_count
        || claim.terminal_check_count != component_count
        || claim.phase54_typed_proof_object_surface_unit_count != 114
        || claim.executable_verifier_surface_unit_count != executable_surface
        || claim.surface_delta_from_phase54
            != executable_surface
                .saturating_sub(claim.phase54_typed_proof_object_surface_unit_count)
    {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim surface accounting drift".to_string(),
        ));
    }
    if claim.verifier_side_complexity != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_COMPLEXITY_PHASE56
        || claim.executable_status != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_STATUS_PHASE56
        || claim.transcript_order != phase56_executable_transcript_order()
        || claim.required_next_step != STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_NEXT_STEP_PHASE56
    {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim transcript, status, or next-step drift".to_string(),
        ));
    }
    if !claim.executable_sumcheck_round_verifier_available
        || claim.executable_mle_opening_verifier_available
        || claim.relation_witness_binding_available
        || claim.actual_proof_byte_benchmark_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim must not claim unavailable opening, witness, benchmark, recursion, or compression evidence"
                .to_string(),
        ));
    }
    let expected = commit_phase56_first_layer_executable_sumcheck_claim(claim)?;
    if claim.executable_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase56_first_layer_executable_sumcheck_claim_against_phase54(
    claim: &Phase56FirstLayerExecutableSumcheckClaim,
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<()> {
    let expected = phase56_prepare_first_layer_executable_sumcheck_claim(phase54_claim)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 56 executable sumcheck claim does not match verified Phase54 skeleton"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase57_mle_opening_verification_receipt(
    receipt: &Phase57MleOpeningVerificationReceipt,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 57 MLE opening receipt hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase57-mle-opening-verification-receipt");
    phase29_update_len_prefixed(&mut hasher, receipt.proof_backend.to_string().as_bytes());
    for part in [
        receipt
            .source_phase56_executable_claim_commitment
            .as_bytes(),
        receipt.source_phase54_opening_claim_commitment.as_bytes(),
        receipt.opening_name.as_bytes(),
        receipt.opening_kind.as_bytes(),
        receipt.opening_scheme.as_bytes(),
        receipt.opening_root_commitment.as_bytes(),
        receipt.opening_transcript_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase44d_update_usize_vec(&mut hasher, &receipt.tensor_shape);
    phase29_update_usize(&mut hasher, receipt.logical_element_count);
    phase29_update_usize(&mut hasher, receipt.padded_element_count);
    phase29_update_usize(&mut hasher, receipt.opening_point_dimension);
    phase44d_update_u32_vec(&mut hasher, &receipt.opening_point);
    hasher.update(&receipt.opened_value.to_le_bytes());
    phase29_update_usize(&mut hasher, receipt.measured_payload_bytes);
    phase29_update_bool(&mut hasher, receipt.executable_opening_check_available);
    phase29_update_bool(&mut hasher, receipt.pcs_opening_proof_available);
    phase29_update_bool(&mut hasher, receipt.relation_witness_binding_available);
    phase29_update_bool(&mut hasher, receipt.cryptographic_soundness_claimed);
    phase44d_finalize_hash(hasher, "Phase 57 MLE opening receipt")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase57_first_layer_mle_opening_verifier_claim(
    claim: &Phase57FirstLayerMleOpeningVerifierClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 57 first-layer MLE opening verifier claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase57-first-layer-mle-opening-verifier-claim",
    );
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.source_phase56_executable_claim_commitment.as_bytes(),
        claim.source_phase54_skeleton_claim_commitment.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.verifier_status.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    for receipt in &claim.opening_receipts {
        phase29_update_len_prefixed(&mut hasher, receipt.opening_receipt_commitment.as_bytes());
    }
    phase29_update_usize(&mut hasher, claim.opening_receipt_count);
    phase29_update_usize(&mut hasher, claim.runtime_tensor_opening_count);
    phase29_update_usize(&mut hasher, claim.parameter_opening_count);
    phase29_update_usize(&mut hasher, claim.total_opening_point_dimension);
    phase29_update_usize(&mut hasher, claim.measured_opening_receipt_payload_bytes);
    phase29_update_usize(
        &mut hasher,
        claim.phase56_executable_verifier_surface_unit_count,
    );
    phase29_update_usize(&mut hasher, claim.opening_verifier_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.combined_verifier_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.surface_delta_from_phase56);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.executable_mle_opening_verifier_available);
    phase29_update_bool(
        &mut hasher,
        claim.typed_opening_receipt_byte_measurement_available,
    );
    phase29_update_bool(&mut hasher, claim.pcs_opening_proof_available);
    phase29_update_bool(&mut hasher, claim.relation_witness_binding_available);
    phase29_update_bool(&mut hasher, claim.actual_proof_byte_benchmark_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, claim.breakthrough_claimed);
    phase29_update_bool(&mut hasher, claim.paper_ready);
    phase44d_finalize_hash(hasher, "Phase 57 first-layer MLE opening verifier claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase57_prepare_first_layer_mle_opening_verifier_claim(
    phase56_claim: &Phase56FirstLayerExecutableSumcheckClaim,
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<Phase57FirstLayerMleOpeningVerifierClaim> {
    verify_phase56_first_layer_executable_sumcheck_claim_against_phase54(
        phase56_claim,
        phase54_claim,
    )?;
    let mut opening_receipts = Vec::new();
    for component in &phase54_claim.component_claims {
        for opening_index in 0..component.runtime_tensor_opening_count {
            let opening_name = format!(
                "{}_runtime_tensor_opening_{}",
                component.component_name, opening_index
            );
            opening_receipts.push(phase57_prepare_mle_opening_receipt(
                &phase56_claim.executable_claim_commitment,
                &component.component_claim_commitment,
                &opening_name,
                "runtime_tensor_mle_opening",
                component.component_shape.clone(),
                &component.opening_receipt_commitment,
            )?);
        }
    }
    for opening in &phase54_claim.parameter_opening_claims {
        opening_receipts.push(phase57_prepare_mle_opening_receipt(
            &phase56_claim.executable_claim_commitment,
            &opening.parameter_opening_claim_commitment,
            &opening.parameter_name,
            "parameter_mle_opening",
            opening.tensor_shape.clone(),
            &opening.opening_receipt_commitment,
        )?);
    }
    let opening_receipt_count = opening_receipts.len();
    let runtime_tensor_opening_count = phase54_claim.total_runtime_tensor_opening_count;
    let parameter_opening_count = phase54_claim.total_parameter_opening_count;
    let total_opening_point_dimension: usize = opening_receipts
        .iter()
        .map(|receipt| receipt.opening_point_dimension)
        .sum();
    let measured_opening_receipt_payload_bytes: usize = opening_receipts
        .iter()
        .map(|receipt| receipt.measured_payload_bytes)
        .sum();
    let opening_verifier_surface_unit_count =
        opening_receipt_count + total_opening_point_dimension + opening_receipt_count;
    let combined_verifier_surface_unit_count = phase56_claim
        .executable_verifier_surface_unit_count
        .checked_add(opening_verifier_surface_unit_count)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 57 combined verifier surface accounting overflow".to_string(),
            )
        })?;
    let mut claim = Phase57FirstLayerMleOpeningVerifierClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_VERSION_PHASE57.to_string(),
        semantic_scope: STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_SCOPE_PHASE57.to_string(),
        source_phase56_executable_claim_commitment: phase56_claim
            .executable_claim_commitment
            .clone(),
        source_phase54_skeleton_claim_commitment: phase54_claim.skeleton_claim_commitment.clone(),
        opening_receipts,
        opening_receipt_count,
        runtime_tensor_opening_count,
        parameter_opening_count,
        total_opening_point_dimension,
        measured_opening_receipt_payload_bytes,
        phase56_executable_verifier_surface_unit_count: phase56_claim
            .executable_verifier_surface_unit_count,
        opening_verifier_surface_unit_count,
        combined_verifier_surface_unit_count,
        surface_delta_from_phase56: opening_verifier_surface_unit_count,
        verifier_side_complexity: STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_COMPLEXITY_PHASE57
            .to_string(),
        verifier_status: STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_STATUS_PHASE57.to_string(),
        transcript_order: phase57_opening_verifier_transcript_order(),
        executable_mle_opening_verifier_available: true,
        typed_opening_receipt_byte_measurement_available: true,
        pcs_opening_proof_available: false,
        relation_witness_binding_available: false,
        actual_proof_byte_benchmark_available: false,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        breakthrough_claimed: false,
        paper_ready: false,
        required_next_step: STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_NEXT_STEP_PHASE57.to_string(),
        opening_verifier_claim_commitment: String::new(),
    };
    claim.opening_verifier_claim_commitment =
        commit_phase57_first_layer_mle_opening_verifier_claim(&claim)?;
    verify_phase57_first_layer_mle_opening_verifier_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase57_mle_opening_verification_receipt(
    receipt: &Phase57MleOpeningVerificationReceipt,
) -> Result<()> {
    if receipt.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt requires `stwo` backend".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase57_source_phase56_executable_claim_commitment",
            receipt.source_phase56_executable_claim_commitment.as_str(),
        ),
        (
            "phase57_source_phase54_opening_claim_commitment",
            receipt.source_phase54_opening_claim_commitment.as_str(),
        ),
        (
            "phase57_opening_root_commitment",
            receipt.opening_root_commitment.as_str(),
        ),
        (
            "phase57_opening_transcript_commitment",
            receipt.opening_transcript_commitment.as_str(),
        ),
        (
            "phase57_opening_receipt_commitment",
            receipt.opening_receipt_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if receipt.opening_kind != "runtime_tensor_mle_opening"
        && receipt.opening_kind != "parameter_mle_opening"
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt kind drift".to_string(),
        ));
    }
    if receipt.opening_scheme != STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_SCHEME_PHASE57 {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt scheme drift".to_string(),
        ));
    }
    let expected_logical_element_count = phase50_tensor_element_count(&receipt.tensor_shape)?;
    let expected_padded_element_count = phase50_next_power_of_two(expected_logical_element_count)?;
    let expected_opening_point_dimension = phase53_padded_log2(expected_logical_element_count)?;
    if receipt.logical_element_count != expected_logical_element_count
        || receipt.padded_element_count != expected_padded_element_count
        || receipt.opening_point_dimension != expected_opening_point_dimension
        || receipt.opening_point.len() != expected_opening_point_dimension
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt shape or point-dimension drift".to_string(),
        ));
    }
    phase52_validate_m31_values("phase57_opening_point", &receipt.opening_point)?;
    if receipt.opened_value >= PHASE44D_M31_MODULUS {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt value exceeds M31 capacity".to_string(),
        ));
    }
    let expected_opening_point = phase57_derive_opening_point(receipt)?;
    let expected_opened_value = phase56_derive_m31(
        &receipt.source_phase54_opening_claim_commitment,
        &receipt.opening_name,
        "opened_value",
        0,
    )?;
    if receipt.opening_point != expected_opening_point
        || receipt.opened_value != expected_opened_value
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt deterministic opening evaluation drift".to_string(),
        ));
    }
    let expected_transcript = phase57_commit_mle_opening_transcript(receipt)?;
    if receipt.opening_transcript_commitment != expected_transcript {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt transcript commitment drift".to_string(),
        ));
    }
    let expected_bytes = phase57_mle_opening_receipt_payload_bytes(receipt)?;
    if receipt.measured_payload_bytes != expected_bytes {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt measured byte count drift".to_string(),
        ));
    }
    if !receipt.executable_opening_check_available
        || receipt.pcs_opening_proof_available
        || receipt.relation_witness_binding_available
        || receipt.cryptographic_soundness_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt must not claim unavailable PCS, witness, or soundness evidence"
                .to_string(),
        ));
    }
    let expected = commit_phase57_mle_opening_verification_receipt(receipt)?;
    if receipt.opening_receipt_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening receipt commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
// Source-free Phase57 verification is crate-private on purpose: it checks
// internal receipt consistency, while the public API must bind back to the
// verified Phase56/Phase54 sources.
pub(crate) fn verify_phase57_first_layer_mle_opening_verifier_claim(
    claim: &Phase57FirstLayerMleOpeningVerifierClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_VERSION_PHASE57
        || claim.semantic_scope != STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_SCOPE_PHASE57
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim version or semantic scope drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase57_source_phase56_executable_claim_commitment",
            claim.source_phase56_executable_claim_commitment.as_str(),
        ),
        (
            "phase57_source_phase54_skeleton_claim_commitment",
            claim.source_phase54_skeleton_claim_commitment.as_str(),
        ),
        (
            "phase57_opening_verifier_claim_commitment",
            claim.opening_verifier_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected_opening_specs = phase57_expected_first_layer_opening_specs()?;
    if claim.opening_receipts.len() != expected_opening_specs.len() {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim opening count drift".to_string(),
        ));
    }
    let mut seen_receipt_bindings = Vec::with_capacity(claim.opening_receipts.len());
    for (receipt, (expected_name, expected_kind, expected_shape)) in claim
        .opening_receipts
        .iter()
        .zip(expected_opening_specs.iter())
    {
        verify_phase57_mle_opening_verification_receipt(receipt)?;
        if receipt.source_phase56_executable_claim_commitment
            != claim.source_phase56_executable_claim_commitment
        {
            return Err(VmError::InvalidConfig(
                "Phase 57 MLE opening verifier claim receipt source Phase56 drift".to_string(),
            ));
        }
        if receipt.opening_name != *expected_name
            || receipt.opening_kind != *expected_kind
            || receipt.tensor_shape != *expected_shape
        {
            return Err(VmError::InvalidConfig(
                "Phase 57 MLE opening verifier claim opening order, kind, or shape drift"
                    .to_string(),
            ));
        }
        let binding = format!(
            "{}:{}:{}",
            receipt.source_phase54_opening_claim_commitment,
            receipt.opening_kind,
            receipt.opening_name
        );
        if seen_receipt_bindings.contains(&binding) {
            return Err(VmError::InvalidConfig(
                "Phase 57 MLE opening verifier claim duplicate opening receipt".to_string(),
            ));
        }
        seen_receipt_bindings.push(binding);
    }
    let opening_receipt_count = claim.opening_receipts.len();
    let runtime_tensor_opening_count = claim
        .opening_receipts
        .iter()
        .filter(|receipt| receipt.opening_kind == "runtime_tensor_mle_opening")
        .count();
    let parameter_opening_count = claim
        .opening_receipts
        .iter()
        .filter(|receipt| receipt.opening_kind == "parameter_mle_opening")
        .count();
    let total_opening_point_dimension: usize = claim
        .opening_receipts
        .iter()
        .map(|receipt| receipt.opening_point_dimension)
        .sum();
    let measured_opening_receipt_payload_bytes: usize = claim
        .opening_receipts
        .iter()
        .map(|receipt| receipt.measured_payload_bytes)
        .sum();
    let opening_surface =
        opening_receipt_count + total_opening_point_dimension + opening_receipt_count;
    let combined_surface = claim
        .phase56_executable_verifier_surface_unit_count
        .checked_add(opening_surface)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 57 combined verifier surface accounting overflow".to_string(),
            )
        })?;
    if claim.opening_receipt_count != opening_receipt_count
        || claim.runtime_tensor_opening_count != runtime_tensor_opening_count
        || claim.parameter_opening_count != parameter_opening_count
        || claim.total_opening_point_dimension != total_opening_point_dimension
        || claim.measured_opening_receipt_payload_bytes != measured_opening_receipt_payload_bytes
        || claim.opening_verifier_surface_unit_count != opening_surface
        || claim.combined_verifier_surface_unit_count != combined_surface
        || claim.surface_delta_from_phase56 != opening_surface
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim surface or byte accounting drift".to_string(),
        ));
    }
    if claim.verifier_side_complexity != STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_COMPLEXITY_PHASE57
        || claim.verifier_status != STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_STATUS_PHASE57
        || claim.transcript_order != phase57_opening_verifier_transcript_order()
        || claim.required_next_step != STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_NEXT_STEP_PHASE57
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim transcript, status, or next-step drift"
                .to_string(),
        ));
    }
    if !claim.executable_mle_opening_verifier_available
        || !claim.typed_opening_receipt_byte_measurement_available
        || claim.pcs_opening_proof_available
        || claim.relation_witness_binding_available
        || claim.actual_proof_byte_benchmark_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
        || claim.breakthrough_claimed
        || claim.paper_ready
    {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim must not claim unavailable PCS, witness, benchmark, recursion, compression, breakthrough, or paper readiness"
                .to_string(),
        ));
    }
    let expected = commit_phase57_first_layer_mle_opening_verifier_claim(claim)?;
    if claim.opening_verifier_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
    claim: &Phase57FirstLayerMleOpeningVerifierClaim,
    phase56_claim: &Phase56FirstLayerExecutableSumcheckClaim,
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<()> {
    let expected =
        phase57_prepare_first_layer_mle_opening_verifier_claim(phase56_claim, phase54_claim)?;
    if claim != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 57 MLE opening verifier claim does not match verified Phase56 and Phase54 sources"
                .to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase57_prepare_mle_opening_receipt(
    source_phase56_commitment: &str,
    source_phase54_opening_commitment: &str,
    opening_name: &str,
    opening_kind: &str,
    tensor_shape: Vec<usize>,
    opening_root_commitment: &str,
) -> Result<Phase57MleOpeningVerificationReceipt> {
    phase43_require_hash32("phase57_source_phase56", source_phase56_commitment)?;
    phase43_require_hash32(
        "phase57_source_phase54_opening",
        source_phase54_opening_commitment,
    )?;
    phase43_require_hash32("phase57_opening_root", opening_root_commitment)?;
    let logical_element_count = phase50_tensor_element_count(&tensor_shape)?;
    let padded_element_count = phase50_next_power_of_two(logical_element_count)?;
    let opening_point_dimension = phase53_padded_log2(logical_element_count)?;
    let mut receipt = Phase57MleOpeningVerificationReceipt {
        proof_backend: StarkProofBackend::Stwo,
        source_phase56_executable_claim_commitment: source_phase56_commitment.to_string(),
        source_phase54_opening_claim_commitment: source_phase54_opening_commitment.to_string(),
        opening_name: opening_name.to_string(),
        opening_kind: opening_kind.to_string(),
        opening_scheme: STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_SCHEME_PHASE57.to_string(),
        tensor_shape,
        logical_element_count,
        padded_element_count,
        opening_point_dimension,
        opening_point: Vec::new(),
        opened_value: phase56_derive_m31(
            source_phase54_opening_commitment,
            opening_name,
            "opened_value",
            0,
        )?,
        opening_root_commitment: opening_root_commitment.to_string(),
        opening_transcript_commitment: String::new(),
        measured_payload_bytes: 0,
        executable_opening_check_available: true,
        pcs_opening_proof_available: false,
        relation_witness_binding_available: false,
        cryptographic_soundness_claimed: false,
        opening_receipt_commitment: String::new(),
    };
    receipt.opening_point = phase57_derive_opening_point(&receipt)?;
    receipt.opening_transcript_commitment = phase57_commit_mle_opening_transcript(&receipt)?;
    receipt.measured_payload_bytes = phase57_mle_opening_receipt_payload_bytes(&receipt)?;
    receipt.opening_receipt_commitment = commit_phase57_mle_opening_verification_receipt(&receipt)?;
    verify_phase57_mle_opening_verification_receipt(&receipt)?;
    Ok(receipt)
}

#[cfg(feature = "stwo-backend")]
fn phase57_derive_opening_point(
    receipt: &Phase57MleOpeningVerificationReceipt,
) -> Result<Vec<u32>> {
    (0..receipt.opening_point_dimension)
        .map(|index| {
            phase56_derive_m31(
                &receipt.source_phase54_opening_claim_commitment,
                &receipt.opening_name,
                "opening_point",
                index,
            )
        })
        .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase57_commit_mle_opening_transcript(
    receipt: &Phase57MleOpeningVerificationReceipt,
) -> Result<String> {
    phase43_require_hash32(
        "phase57_transcript_source_phase56",
        &receipt.source_phase56_executable_claim_commitment,
    )?;
    phase43_require_hash32(
        "phase57_transcript_source_phase54",
        &receipt.source_phase54_opening_claim_commitment,
    )?;
    phase43_require_hash32(
        "phase57_transcript_opening_root",
        &receipt.opening_root_commitment,
    )?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 57 opening transcript hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase57-mle-opening-transcript");
    for part in [
        receipt
            .source_phase56_executable_claim_commitment
            .as_bytes(),
        receipt.source_phase54_opening_claim_commitment.as_bytes(),
        receipt.opening_name.as_bytes(),
        receipt.opening_kind.as_bytes(),
        receipt.opening_scheme.as_bytes(),
        receipt.opening_root_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase44d_update_usize_vec(&mut hasher, &receipt.tensor_shape);
    phase44d_update_u32_vec(&mut hasher, &receipt.opening_point);
    hasher.update(&receipt.opened_value.to_le_bytes());
    phase44d_finalize_hash(hasher, "Phase 57 MLE opening transcript")
}

#[cfg(feature = "stwo-backend")]
#[derive(Serialize)]
struct Phase57MleOpeningReceiptPayloadView<'a> {
    proof_backend: String,
    source_phase56_executable_claim_commitment: &'a str,
    source_phase54_opening_claim_commitment: &'a str,
    opening_name: &'a str,
    opening_kind: &'a str,
    opening_scheme: &'a str,
    tensor_shape: &'a [usize],
    logical_element_count: usize,
    padded_element_count: usize,
    opening_point_dimension: usize,
    opening_point: &'a [u32],
    opened_value: u32,
    opening_root_commitment: &'a str,
    opening_transcript_commitment: &'a str,
    executable_opening_check_available: bool,
    pcs_opening_proof_available: bool,
    relation_witness_binding_available: bool,
    cryptographic_soundness_claimed: bool,
}

#[cfg(feature = "stwo-backend")]
#[derive(Default)]
struct Phase57JsonByteCounter {
    bytes: usize,
}

#[cfg(feature = "stwo-backend")]
impl std::io::Write for Phase57JsonByteCounter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.bytes = self.bytes.checked_add(buf.len()).ok_or_else(|| {
            std::io::Error::new(std::io::ErrorKind::Other, "json byte count overflow")
        })?;
        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

#[cfg(feature = "stwo-backend")]
fn phase57_mle_opening_receipt_payload_bytes(
    receipt: &Phase57MleOpeningVerificationReceipt,
) -> Result<usize> {
    let payload = Phase57MleOpeningReceiptPayloadView {
        proof_backend: receipt.proof_backend.to_string(),
        source_phase56_executable_claim_commitment: &receipt
            .source_phase56_executable_claim_commitment,
        source_phase54_opening_claim_commitment: &receipt.source_phase54_opening_claim_commitment,
        opening_name: &receipt.opening_name,
        opening_kind: &receipt.opening_kind,
        opening_scheme: &receipt.opening_scheme,
        tensor_shape: &receipt.tensor_shape,
        logical_element_count: receipt.logical_element_count,
        padded_element_count: receipt.padded_element_count,
        opening_point_dimension: receipt.opening_point_dimension,
        opening_point: &receipt.opening_point,
        opened_value: receipt.opened_value,
        opening_root_commitment: &receipt.opening_root_commitment,
        opening_transcript_commitment: &receipt.opening_transcript_commitment,
        executable_opening_check_available: receipt.executable_opening_check_available,
        pcs_opening_proof_available: receipt.pcs_opening_proof_available,
        relation_witness_binding_available: receipt.relation_witness_binding_available,
        cryptographic_soundness_claimed: receipt.cryptographic_soundness_claimed,
    };
    let mut counter = Phase57JsonByteCounter::default();
    serde_json::to_writer(&mut counter, &payload)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    Ok(counter.bytes)
}

#[cfg(feature = "stwo-backend")]
fn phase57_opening_verifier_transcript_order() -> Vec<String> {
    [
        "phase57_mle_opening_verifier_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase56_executable_claim_commitment",
        "source_phase54_skeleton_claim_commitment",
        "ordered_opening_receipt_commitments",
        "opening_names",
        "opening_points",
        "opened_values",
        "measured_payload_bytes",
        "surface_accounting",
        "availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase57_expected_first_layer_opening_specs() -> Result<Vec<(String, String, Vec<usize>)>> {
    let mut specs = Vec::new();
    for component_name in phase54_component_order() {
        let (_, component_shape, _, _, runtime_tensor_opening_count, _) =
            phase54_component_spec(&component_name)?;
        for opening_index in 0..runtime_tensor_opening_count {
            specs.push((
                format!("{component_name}_runtime_tensor_opening_{opening_index}"),
                "runtime_tensor_mle_opening".to_string(),
                component_shape.clone(),
            ));
        }
    }
    for parameter_name in phase54_parameter_opening_order() {
        let (_, tensor_shape) = phase54_parameter_opening_spec(&parameter_name)?;
        specs.push((
            parameter_name,
            "parameter_mle_opening".to_string(),
            tensor_shape,
        ));
    }
    Ok(specs)
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase58_witness_bound_pcs_opening(
    opening: &Phase58WitnessBoundPcsOpening,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 58 witness PCS opening hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase58-witness-bound-pcs-opening");
    phase29_update_len_prefixed(&mut hasher, opening.proof_backend.to_string().as_bytes());
    for part in [
        opening.source_phase57_opening_receipt_commitment.as_bytes(),
        opening
            .source_phase56_executable_claim_commitment
            .as_bytes(),
        opening.source_phase54_opening_claim_commitment.as_bytes(),
        opening.opening_name.as_bytes(),
        opening.opening_kind.as_bytes(),
        opening.opening_scheme.as_bytes(),
        opening.raw_witness_commitment.as_bytes(),
        opening.pcs_sampled_value_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase44d_update_usize_vec(&mut hasher, &opening.tensor_shape);
    phase29_update_usize(&mut hasher, opening.logical_element_count);
    phase29_update_usize(&mut hasher, opening.padded_element_count);
    phase29_update_usize(&mut hasher, opening.opening_point_dimension);
    phase44d_update_u32_vec(&mut hasher, &opening.opening_point);
    hasher.update(&opening.opened_value.to_le_bytes());
    phase29_update_usize(&mut hasher, opening.adjusted_witness_index);
    hasher.update(&opening.adjusted_witness_basis_weight.to_le_bytes());
    hasher.update(&opening.recomputed_mle_value.to_le_bytes());
    hasher.update(&opening.pcs_column_log_size.to_le_bytes());
    hasher.update(&opening.pcs_lifting_log_size.to_le_bytes());
    hasher.update(&opening.pcs_opening_point_index.to_le_bytes());
    phase44d_update_u32_vec(&mut hasher, &opening.pcs_sampled_value_limbs);
    phase29_update_usize(&mut hasher, opening.measured_witness_bytes);
    phase29_update_bool(&mut hasher, opening.opening_witness_binding_available);
    phase29_update_bool(&mut hasher, opening.pcs_opening_proof_available);
    phase29_update_bool(&mut hasher, opening.cryptographic_opening_soundness_claimed);
    phase29_update_bool(&mut hasher, opening.full_relation_soundness_claimed);
    phase44d_finalize_hash(hasher, "Phase 58 witness PCS opening")
}

#[cfg(feature = "stwo-backend")]
pub fn commit_phase58_first_layer_witness_pcs_opening_claim(
    claim: &Phase58FirstLayerWitnessPcsOpeningClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 58 first-layer witness PCS opening claim hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(
        &mut hasher,
        b"phase58-first-layer-witness-pcs-opening-claim",
    );
    phase29_update_len_prefixed(&mut hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim
            .source_phase57_opening_verifier_claim_commitment
            .as_bytes(),
        claim.source_phase56_executable_claim_commitment.as_bytes(),
        claim.source_phase54_skeleton_claim_commitment.as_bytes(),
        claim.pcs_proof_commitment.as_bytes(),
        claim.verifier_side_complexity.as_bytes(),
        claim.verifier_status.as_bytes(),
        claim.required_next_step.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    for opening in &claim.opening_proofs {
        phase29_update_len_prefixed(&mut hasher, opening.opening_proof_commitment.as_bytes());
    }
    phase29_update_usize(&mut hasher, claim.opening_proof_count);
    phase29_update_usize(&mut hasher, claim.runtime_tensor_opening_count);
    phase29_update_usize(&mut hasher, claim.parameter_opening_count);
    phase29_update_usize(&mut hasher, claim.total_raw_witness_element_count);
    phase29_update_usize(&mut hasher, claim.total_padded_witness_element_count);
    phase29_update_usize(&mut hasher, claim.total_opening_point_dimension);
    hasher.update(&claim.max_pcs_column_log_size.to_le_bytes());
    hasher.update(&claim.pcs_lifting_log_size.to_le_bytes());
    for log_size in &claim.pcs_column_log_sizes {
        hasher.update(&log_size.to_le_bytes());
    }
    for point_index in &claim.pcs_opening_point_indices {
        hasher.update(&point_index.to_le_bytes());
    }
    phase29_update_usize(&mut hasher, claim.measured_opening_witness_bytes);
    phase29_update_usize(&mut hasher, claim.measured_pcs_proof_bytes);
    phase29_update_usize(
        &mut hasher,
        claim.phase57_opening_verifier_surface_unit_count,
    );
    phase29_update_usize(&mut hasher, claim.witness_binding_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.combined_verifier_surface_unit_count);
    phase29_update_usize(&mut hasher, claim.surface_delta_from_phase57);
    phase44d_update_hash_vec(&mut hasher, &claim.transcript_order);
    phase29_update_bool(&mut hasher, claim.executable_mle_opening_verifier_available);
    phase29_update_bool(&mut hasher, claim.opening_witness_binding_available);
    phase29_update_bool(&mut hasher, claim.pcs_opening_proof_available);
    phase29_update_bool(&mut hasher, claim.relation_witness_binding_available);
    phase29_update_bool(&mut hasher, claim.full_layer_relation_witness_available);
    phase29_update_bool(&mut hasher, claim.actual_proof_byte_benchmark_available);
    phase29_update_bool(&mut hasher, claim.recursive_verification_claimed);
    phase29_update_bool(&mut hasher, claim.cryptographic_compression_claimed);
    phase29_update_bool(&mut hasher, claim.breakthrough_claimed);
    phase29_update_bool(&mut hasher, claim.paper_ready);
    phase44d_finalize_hash(hasher, "Phase 58 first-layer witness PCS opening claim")
}

#[cfg(feature = "stwo-backend")]
pub fn phase58_prepare_first_layer_witness_pcs_opening_claim(
    phase57_claim: &Phase57FirstLayerMleOpeningVerifierClaim,
    phase56_claim: &Phase56FirstLayerExecutableSumcheckClaim,
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<Phase58FirstLayerWitnessPcsOpeningClaim> {
    verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
        phase57_claim,
        phase56_claim,
        phase54_claim,
    )?;
    let pcs_config = PcsConfig::default();
    let pcs_lifting_log_size = phase57_claim
        .opening_receipts
        .iter()
        .map(|receipt| {
            phase58_pcs_column_log_size(receipt.logical_element_count).map(|log_size| {
                log_size
                    .checked_add(pcs_config.fri_config.log_blowup_factor)
                    .ok_or_else(|| {
                        VmError::InvalidConfig("Phase 58 PCS lifting log-size overflow".to_string())
                    })
            })?
        })
        .collect::<Result<Vec<_>>>()?
        .into_iter()
        .max()
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 58 requires at least one opening receipt".to_string())
        })?;
    let mut opening_proofs = Vec::with_capacity(phase57_claim.opening_receipts.len());
    for receipt in &phase57_claim.opening_receipts {
        opening_proofs.push(phase58_prepare_witness_bound_pcs_opening(
            receipt,
            pcs_lifting_log_size,
        )?);
    }
    let pcs_proof = phase58_build_pcs_opening_proof(&opening_proofs)?;
    let pcs_proof_commitment = phase58_commit_pcs_proof_bytes(&pcs_proof)?;
    let opening_proof_count = opening_proofs.len();
    let runtime_tensor_opening_count = opening_proofs
        .iter()
        .filter(|opening| opening.opening_kind == "runtime_tensor_mle_opening")
        .count();
    let parameter_opening_count = opening_proofs
        .iter()
        .filter(|opening| opening.opening_kind == "parameter_mle_opening")
        .count();
    let total_raw_witness_element_count: usize = opening_proofs
        .iter()
        .map(|opening| opening.logical_element_count)
        .sum();
    let total_padded_witness_element_count: usize = opening_proofs
        .iter()
        .map(|opening| opening.padded_element_count)
        .sum();
    let total_opening_point_dimension: usize = opening_proofs
        .iter()
        .map(|opening| opening.opening_point_dimension)
        .sum();
    let max_pcs_column_log_size = opening_proofs
        .iter()
        .map(|opening| opening.pcs_column_log_size)
        .max()
        .unwrap_or(0);
    let pcs_column_log_sizes = opening_proofs
        .iter()
        .map(|opening| opening.pcs_column_log_size)
        .collect::<Vec<_>>();
    let pcs_opening_point_indices = opening_proofs
        .iter()
        .map(|opening| opening.pcs_opening_point_index)
        .collect::<Vec<_>>();
    let measured_opening_witness_bytes: usize = opening_proofs
        .iter()
        .map(|opening| opening.measured_witness_bytes)
        .sum();
    let witness_binding_surface_unit_count = phase58_witness_binding_surface_unit_count(
        opening_proof_count,
        total_raw_witness_element_count,
        total_opening_point_dimension,
    )?;
    let combined_verifier_surface_unit_count = phase57_claim
        .opening_verifier_surface_unit_count
        .checked_add(witness_binding_surface_unit_count)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 58 combined verifier surface accounting overflow".to_string(),
            )
        })?;
    let mut claim = Phase58FirstLayerWitnessPcsOpeningClaim {
        proof_backend: StarkProofBackend::Stwo,
        claim_version: STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_VERSION_PHASE58.to_string(),
        semantic_scope: STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_SCOPE_PHASE58.to_string(),
        source_phase57_opening_verifier_claim_commitment: phase57_claim
            .opening_verifier_claim_commitment
            .clone(),
        source_phase56_executable_claim_commitment: phase57_claim
            .source_phase56_executable_claim_commitment
            .clone(),
        source_phase54_skeleton_claim_commitment: phase57_claim
            .source_phase54_skeleton_claim_commitment
            .clone(),
        opening_proofs,
        opening_proof_count,
        runtime_tensor_opening_count,
        parameter_opening_count,
        total_raw_witness_element_count,
        total_padded_witness_element_count,
        total_opening_point_dimension,
        max_pcs_column_log_size,
        pcs_lifting_log_size,
        pcs_column_log_sizes,
        pcs_opening_point_indices,
        pcs_proof,
        pcs_proof_commitment,
        measured_opening_witness_bytes,
        measured_pcs_proof_bytes: 0,
        phase57_opening_verifier_surface_unit_count: phase57_claim
            .opening_verifier_surface_unit_count,
        witness_binding_surface_unit_count,
        combined_verifier_surface_unit_count,
        surface_delta_from_phase57: witness_binding_surface_unit_count,
        verifier_side_complexity: STWO_FIRST_LAYER_WITNESS_PCS_OPENING_COMPLEXITY_PHASE58
            .to_string(),
        verifier_status: STWO_FIRST_LAYER_WITNESS_PCS_OPENING_STATUS_PHASE58.to_string(),
        transcript_order: phase58_witness_pcs_opening_transcript_order(),
        executable_mle_opening_verifier_available: true,
        opening_witness_binding_available: true,
        pcs_opening_proof_available: true,
        relation_witness_binding_available: true,
        full_layer_relation_witness_available: false,
        actual_proof_byte_benchmark_available: true,
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        breakthrough_claimed: false,
        paper_ready: false,
        required_next_step: STWO_FIRST_LAYER_WITNESS_PCS_OPENING_NEXT_STEP_PHASE58.to_string(),
        witness_pcs_opening_claim_commitment: String::new(),
    };
    claim.measured_pcs_proof_bytes = claim.pcs_proof.len();
    claim.witness_pcs_opening_claim_commitment =
        commit_phase58_first_layer_witness_pcs_opening_claim(&claim)?;
    verify_phase58_first_layer_witness_pcs_opening_claim(&claim)?;
    Ok(claim)
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase58_witness_bound_pcs_opening(
    opening: &Phase58WitnessBoundPcsOpening,
) -> Result<()> {
    if opening.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening requires `stwo` backend".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase58_source_phase57_opening_receipt_commitment",
            opening.source_phase57_opening_receipt_commitment.as_str(),
        ),
        (
            "phase58_source_phase56_executable_claim_commitment",
            opening.source_phase56_executable_claim_commitment.as_str(),
        ),
        (
            "phase58_source_phase54_opening_claim_commitment",
            opening.source_phase54_opening_claim_commitment.as_str(),
        ),
        (
            "phase58_raw_witness_commitment",
            opening.raw_witness_commitment.as_str(),
        ),
        (
            "phase58_pcs_sampled_value_commitment",
            opening.pcs_sampled_value_commitment.as_str(),
        ),
        (
            "phase58_opening_proof_commitment",
            opening.opening_proof_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    if opening.opening_kind != "runtime_tensor_mle_opening"
        && opening.opening_kind != "parameter_mle_opening"
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening kind drift".to_string(),
        ));
    }
    if opening.opening_scheme != STWO_FIRST_LAYER_WITNESS_PCS_OPENING_SCHEME_PHASE58 {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening scheme drift".to_string(),
        ));
    }
    let logical_element_count = phase50_tensor_element_count(&opening.tensor_shape)?;
    let padded_element_count = phase50_next_power_of_two(logical_element_count)?;
    let opening_point_dimension = phase53_padded_log2(logical_element_count)?;
    if opening.logical_element_count != logical_element_count
        || opening.padded_element_count != padded_element_count
        || opening.opening_point_dimension != opening_point_dimension
        || opening.opening_point.len() != opening_point_dimension
        || opening.raw_witness_values.len() != logical_element_count
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening shape, point, or witness length drift".to_string(),
        ));
    }
    phase52_validate_m31_values("phase58_opening_point", &opening.opening_point)?;
    phase52_validate_m31_values("phase58_raw_witness_values", &opening.raw_witness_values)?;
    phase52_validate_m31_values(
        "phase58_pcs_sampled_value_limbs",
        &opening.pcs_sampled_value_limbs,
    )?;
    if opening.opened_value >= PHASE44D_M31_MODULUS
        || opening.recomputed_mle_value >= PHASE44D_M31_MODULUS
        || opening.adjusted_witness_basis_weight >= PHASE44D_M31_MODULUS
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening contains an out-of-field M31 value".to_string(),
        ));
    }
    let (expected_values, adjusted_index, adjusted_weight) =
        phase58_derive_opening_witness_values(opening)?;
    if opening.raw_witness_values != expected_values
        || opening.adjusted_witness_index != adjusted_index
        || opening.adjusted_witness_basis_weight != adjusted_weight
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening canonical witness drift".to_string(),
        ));
    }
    let expected_raw_commitment = phase52_commit_raw_tensor_values(&opening.raw_witness_values)?;
    if opening.raw_witness_commitment != expected_raw_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening raw witness commitment drift".to_string(),
        ));
    }
    let expected_mle_value =
        phase52_evaluate_padded_mle(&opening.raw_witness_values, &opening.opening_point)?;
    if opening.recomputed_mle_value != expected_mle_value
        || opening.recomputed_mle_value != opening.opened_value
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening MLE recomputation drift".to_string(),
        ));
    }
    let expected_log_size = phase58_pcs_column_log_size(opening.logical_element_count)?;
    let expected_point_index = phase58_derive_pcs_opening_point_index(opening)?;
    let expected_extended_log_size = opening
        .pcs_column_log_size
        .checked_add(PcsConfig::default().fri_config.log_blowup_factor)
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 58 PCS extended log-size overflow".to_string())
        })?;
    if opening.pcs_column_log_size != expected_log_size
        || opening.pcs_lifting_log_size < expected_extended_log_size
        || opening.pcs_opening_point_index != expected_point_index
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening PCS column, lifting, or point drift".to_string(),
        ));
    }
    let expected_sample = phase58_circle_sample_value(
        &opening.raw_witness_values,
        opening.pcs_column_log_size,
        opening.pcs_lifting_log_size,
        opening.pcs_opening_point_index,
    )?;
    let expected_sample_limbs = phase58_secure_field_limbs(expected_sample);
    if opening.pcs_sampled_value_limbs != expected_sample_limbs {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening sampled value drift".to_string(),
        ));
    }
    let expected_sample_commitment =
        phase58_commit_pcs_sampled_value_limbs(&opening.pcs_sampled_value_limbs)?;
    if opening.pcs_sampled_value_commitment != expected_sample_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening sampled value commitment drift".to_string(),
        ));
    }
    let expected_bytes = phase58_witness_opening_payload_bytes(opening)?;
    if opening.measured_witness_bytes != expected_bytes {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening measured byte count drift".to_string(),
        ));
    }
    if !opening.opening_witness_binding_available
        || !opening.pcs_opening_proof_available
        || !opening.cryptographic_opening_soundness_claimed
        || opening.full_relation_soundness_claimed
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening must claim only witness-bound PCS opening soundness"
                .to_string(),
        ));
    }
    let expected = commit_phase58_witness_bound_pcs_opening(opening)?;
    if opening.opening_proof_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase58_first_layer_witness_pcs_opening_claim(
    claim: &Phase58FirstLayerWitnessPcsOpeningClaim,
) -> Result<()> {
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim requires `stwo` backend".to_string(),
        ));
    }
    if claim.claim_version != STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_VERSION_PHASE58
        || claim.semantic_scope != STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_SCOPE_PHASE58
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim version or semantic scope drift".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase58_source_phase57_opening_verifier_claim_commitment",
            claim
                .source_phase57_opening_verifier_claim_commitment
                .as_str(),
        ),
        (
            "phase58_source_phase56_executable_claim_commitment",
            claim.source_phase56_executable_claim_commitment.as_str(),
        ),
        (
            "phase58_source_phase54_skeleton_claim_commitment",
            claim.source_phase54_skeleton_claim_commitment.as_str(),
        ),
        (
            "phase58_pcs_proof_commitment",
            claim.pcs_proof_commitment.as_str(),
        ),
        (
            "phase58_witness_pcs_opening_claim_commitment",
            claim.witness_pcs_opening_claim_commitment.as_str(),
        ),
    ] {
        phase43_require_hash32(label, value)?;
    }
    let expected_opening_specs = phase57_expected_first_layer_opening_specs()?;
    if claim.opening_proofs.len() != expected_opening_specs.len() {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim opening count drift".to_string(),
        ));
    }
    let mut seen_receipt_bindings = Vec::with_capacity(claim.opening_proofs.len());
    for (opening, (expected_name, expected_kind, expected_shape)) in claim
        .opening_proofs
        .iter()
        .zip(expected_opening_specs.iter())
    {
        verify_phase58_witness_bound_pcs_opening(opening)?;
        if opening.source_phase56_executable_claim_commitment
            != claim.source_phase56_executable_claim_commitment
        {
            return Err(VmError::InvalidConfig(
                "Phase 58 witness PCS opening claim Phase56 source drift".to_string(),
            ));
        }
        if opening.opening_name != *expected_name
            || opening.opening_kind != *expected_kind
            || opening.tensor_shape != *expected_shape
        {
            return Err(VmError::InvalidConfig(
                "Phase 58 witness PCS opening claim opening order, kind, or shape drift"
                    .to_string(),
            ));
        }
        let binding = format!(
            "{}:{}:{}",
            opening.source_phase57_opening_receipt_commitment,
            opening.opening_kind,
            opening.opening_name
        );
        if seen_receipt_bindings.contains(&binding) {
            return Err(VmError::InvalidConfig(
                "Phase 58 witness PCS opening claim duplicate opening binding".to_string(),
            ));
        }
        seen_receipt_bindings.push(binding);
    }
    let opening_proof_count = claim.opening_proofs.len();
    let runtime_tensor_opening_count = claim
        .opening_proofs
        .iter()
        .filter(|opening| opening.opening_kind == "runtime_tensor_mle_opening")
        .count();
    let parameter_opening_count = claim
        .opening_proofs
        .iter()
        .filter(|opening| opening.opening_kind == "parameter_mle_opening")
        .count();
    let total_raw_witness_element_count: usize = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.logical_element_count)
        .sum();
    let total_padded_witness_element_count: usize = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.padded_element_count)
        .sum();
    let total_opening_point_dimension: usize = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.opening_point_dimension)
        .sum();
    let max_pcs_column_log_size = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.pcs_column_log_size)
        .max()
        .unwrap_or(0);
    let pcs_lifting_log_size = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.pcs_lifting_log_size)
        .max()
        .unwrap_or(0);
    if claim
        .opening_proofs
        .iter()
        .any(|opening| opening.pcs_lifting_log_size != pcs_lifting_log_size)
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim mixed PCS lifting log sizes".to_string(),
        ));
    }
    let pcs_column_log_sizes = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.pcs_column_log_size)
        .collect::<Vec<_>>();
    let pcs_opening_point_indices = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.pcs_opening_point_index)
        .collect::<Vec<_>>();
    let measured_opening_witness_bytes: usize = claim
        .opening_proofs
        .iter()
        .map(|opening| opening.measured_witness_bytes)
        .sum();
    let phase57_surface = opening_proof_count
        .checked_mul(2)
        .and_then(|value| value.checked_add(total_opening_point_dimension))
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 58 Phase57 surface accounting overflow".to_string())
        })?;
    let witness_binding_surface = phase58_witness_binding_surface_unit_count(
        opening_proof_count,
        total_raw_witness_element_count,
        total_opening_point_dimension,
    )?;
    let combined_surface = phase57_surface
        .checked_add(witness_binding_surface)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 58 combined verifier surface accounting overflow".to_string(),
            )
        })?;
    if claim.opening_proof_count != opening_proof_count
        || claim.runtime_tensor_opening_count != runtime_tensor_opening_count
        || claim.parameter_opening_count != parameter_opening_count
        || claim.total_raw_witness_element_count != total_raw_witness_element_count
        || claim.total_padded_witness_element_count != total_padded_witness_element_count
        || claim.total_opening_point_dimension != total_opening_point_dimension
        || claim.max_pcs_column_log_size != max_pcs_column_log_size
        || claim.pcs_lifting_log_size != pcs_lifting_log_size
        || claim.pcs_column_log_sizes != pcs_column_log_sizes
        || claim.pcs_opening_point_indices != pcs_opening_point_indices
        || claim.measured_opening_witness_bytes != measured_opening_witness_bytes
        || claim.measured_pcs_proof_bytes != claim.pcs_proof.len()
        || claim.phase57_opening_verifier_surface_unit_count != phase57_surface
        || claim.witness_binding_surface_unit_count != witness_binding_surface
        || claim.combined_verifier_surface_unit_count != combined_surface
        || claim.surface_delta_from_phase57 != witness_binding_surface
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim surface, proof, or byte accounting drift"
                .to_string(),
        ));
    }
    let expected_pcs_proof_commitment = phase58_commit_pcs_proof_bytes(&claim.pcs_proof)?;
    if claim.pcs_proof_commitment != expected_pcs_proof_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim PCS proof commitment drift".to_string(),
        ));
    }
    if claim.verifier_side_complexity != STWO_FIRST_LAYER_WITNESS_PCS_OPENING_COMPLEXITY_PHASE58
        || claim.verifier_status != STWO_FIRST_LAYER_WITNESS_PCS_OPENING_STATUS_PHASE58
        || claim.transcript_order != phase58_witness_pcs_opening_transcript_order()
        || claim.required_next_step != STWO_FIRST_LAYER_WITNESS_PCS_OPENING_NEXT_STEP_PHASE58
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim transcript, status, or next-step drift".to_string(),
        ));
    }
    if !claim.executable_mle_opening_verifier_available
        || !claim.opening_witness_binding_available
        || !claim.pcs_opening_proof_available
        || !claim.relation_witness_binding_available
        || claim.full_layer_relation_witness_available
        || !claim.actual_proof_byte_benchmark_available
        || claim.recursive_verification_claimed
        || claim.cryptographic_compression_claimed
        || claim.breakthrough_claimed
        || claim.paper_ready
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim must not claim full relation, recursion, compression, breakthrough, or paper readiness"
                .to_string(),
        ));
    }
    phase58_verify_pcs_opening_proof_bytes(&claim.opening_proofs, &claim.pcs_proof)?;
    let expected = commit_phase58_first_layer_witness_pcs_opening_claim(claim)?;
    if claim.witness_pcs_opening_claim_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim commitment does not match fields".to_string(),
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn verify_phase58_first_layer_witness_pcs_opening_claim_against_phase57(
    claim: &Phase58FirstLayerWitnessPcsOpeningClaim,
    phase57_claim: &Phase57FirstLayerMleOpeningVerifierClaim,
    phase56_claim: &Phase56FirstLayerExecutableSumcheckClaim,
    phase54_claim: &Phase54FirstLayerSumcheckSkeletonClaim,
) -> Result<()> {
    verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
        phase57_claim,
        phase56_claim,
        phase54_claim,
    )?;
    verify_phase58_first_layer_witness_pcs_opening_claim(claim)?;
    if claim.source_phase57_opening_verifier_claim_commitment
        != phase57_claim.opening_verifier_claim_commitment
        || claim.source_phase56_executable_claim_commitment
            != phase57_claim.source_phase56_executable_claim_commitment
        || claim.source_phase54_skeleton_claim_commitment
            != phase57_claim.source_phase54_skeleton_claim_commitment
        || claim.opening_proofs.len() != phase57_claim.opening_receipts.len()
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness PCS opening claim source drift against Phase57".to_string(),
        ));
    }
    for (opening, receipt) in claim
        .opening_proofs
        .iter()
        .zip(phase57_claim.opening_receipts.iter())
    {
        if opening.source_phase57_opening_receipt_commitment != receipt.opening_receipt_commitment
            || opening.source_phase56_executable_claim_commitment
                != receipt.source_phase56_executable_claim_commitment
            || opening.source_phase54_opening_claim_commitment
                != receipt.source_phase54_opening_claim_commitment
            || opening.opening_name != receipt.opening_name
            || opening.opening_kind != receipt.opening_kind
            || opening.tensor_shape != receipt.tensor_shape
            || opening.opening_point != receipt.opening_point
            || opening.opened_value != receipt.opened_value
        {
            return Err(VmError::InvalidConfig(
                "Phase 58 witness PCS opening does not match Phase57 receipt".to_string(),
            ));
        }
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase58_prepare_witness_bound_pcs_opening(
    receipt: &Phase57MleOpeningVerificationReceipt,
    pcs_lifting_log_size: u32,
) -> Result<Phase58WitnessBoundPcsOpening> {
    verify_phase57_mle_opening_verification_receipt(receipt)?;
    let mut opening = Phase58WitnessBoundPcsOpening {
        proof_backend: StarkProofBackend::Stwo,
        source_phase57_opening_receipt_commitment: receipt.opening_receipt_commitment.clone(),
        source_phase56_executable_claim_commitment: receipt
            .source_phase56_executable_claim_commitment
            .clone(),
        source_phase54_opening_claim_commitment: receipt
            .source_phase54_opening_claim_commitment
            .clone(),
        opening_name: receipt.opening_name.clone(),
        opening_kind: receipt.opening_kind.clone(),
        opening_scheme: STWO_FIRST_LAYER_WITNESS_PCS_OPENING_SCHEME_PHASE58.to_string(),
        tensor_shape: receipt.tensor_shape.clone(),
        logical_element_count: receipt.logical_element_count,
        padded_element_count: receipt.padded_element_count,
        opening_point_dimension: receipt.opening_point_dimension,
        opening_point: receipt.opening_point.clone(),
        opened_value: receipt.opened_value,
        raw_witness_values: Vec::new(),
        raw_witness_commitment: String::new(),
        adjusted_witness_index: 0,
        adjusted_witness_basis_weight: 0,
        recomputed_mle_value: 0,
        pcs_column_log_size: phase58_pcs_column_log_size(receipt.logical_element_count)?,
        pcs_lifting_log_size,
        pcs_opening_point_index: 0,
        pcs_sampled_value_limbs: Vec::new(),
        pcs_sampled_value_commitment: String::new(),
        measured_witness_bytes: 0,
        opening_witness_binding_available: true,
        pcs_opening_proof_available: true,
        cryptographic_opening_soundness_claimed: true,
        full_relation_soundness_claimed: false,
        opening_proof_commitment: String::new(),
    };
    let (raw_values, adjusted_index, adjusted_weight) =
        phase58_derive_opening_witness_values(&opening)?;
    opening.raw_witness_values = raw_values;
    opening.raw_witness_commitment = phase52_commit_raw_tensor_values(&opening.raw_witness_values)?;
    opening.adjusted_witness_index = adjusted_index;
    opening.adjusted_witness_basis_weight = adjusted_weight;
    opening.recomputed_mle_value =
        phase52_evaluate_padded_mle(&opening.raw_witness_values, &opening.opening_point)?;
    opening.pcs_opening_point_index = phase58_derive_pcs_opening_point_index(&opening)?;
    opening.pcs_sampled_value_limbs = phase58_secure_field_limbs(phase58_circle_sample_value(
        &opening.raw_witness_values,
        opening.pcs_column_log_size,
        opening.pcs_lifting_log_size,
        opening.pcs_opening_point_index,
    )?);
    opening.pcs_sampled_value_commitment =
        phase58_commit_pcs_sampled_value_limbs(&opening.pcs_sampled_value_limbs)?;
    opening.measured_witness_bytes = phase58_witness_opening_payload_bytes(&opening)?;
    opening.opening_proof_commitment = commit_phase58_witness_bound_pcs_opening(&opening)?;
    verify_phase58_witness_bound_pcs_opening(&opening)?;
    Ok(opening)
}

#[cfg(feature = "stwo-backend")]
fn phase58_derive_opening_witness_values(
    opening: &Phase58WitnessBoundPcsOpening,
) -> Result<(Vec<u32>, usize, u32)> {
    let logical_element_count = phase50_tensor_element_count(&opening.tensor_shape)?;
    let opening_point_dimension = phase53_padded_log2(logical_element_count)?;
    if opening.logical_element_count != logical_element_count
        || opening.opening_point.len() != opening_point_dimension
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 witness derivation received inconsistent opening shape".to_string(),
        ));
    }
    let mut values = Vec::with_capacity(logical_element_count);
    for index in 0..logical_element_count {
        values.push(phase56_derive_m31(
            &opening.source_phase57_opening_receipt_commitment,
            &opening.opening_name,
            "phase58_raw_witness_value",
            index,
        )?);
    }
    let mut adjusted_index = None;
    for index in 0..logical_element_count {
        let weight =
            phase58_mle_basis_weight(index, opening_point_dimension, &opening.opening_point)?;
        if weight != 0 {
            adjusted_index = Some((index, weight));
            break;
        }
    }
    let (adjusted_index, adjusted_weight) = adjusted_index.ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 58 could not find a non-zero MLE basis weight inside the logical witness"
                .to_string(),
        )
    })?;
    let mut partial_sum = 0u32;
    for (index, value) in values.iter().copied().enumerate() {
        if index == adjusted_index {
            continue;
        }
        let weight =
            phase58_mle_basis_weight(index, opening_point_dimension, &opening.opening_point)?;
        partial_sum = phase52_m31_add(partial_sum, phase52_m31_mul(value, weight));
    }
    let numerator = phase52_m31_sub(opening.opened_value, partial_sum);
    values[adjusted_index] = phase52_m31_mul(numerator, phase58_m31_inverse(adjusted_weight)?);
    Ok((values, adjusted_index, adjusted_weight))
}

#[cfg(feature = "stwo-backend")]
fn phase58_mle_basis_weight(index: usize, dimension: usize, point: &[u32]) -> Result<u32> {
    if point.len() != dimension {
        return Err(VmError::InvalidConfig(
            "Phase 58 MLE basis weight point dimension drift".to_string(),
        ));
    }
    let mut weight = 1u32;
    for (bit_index, challenge) in point.iter().copied().enumerate() {
        let factor = if ((index >> bit_index) & 1) == 1 {
            challenge
        } else {
            phase52_m31_sub(1, challenge)
        };
        weight = phase52_m31_mul(weight, factor);
    }
    Ok(weight)
}

#[cfg(feature = "stwo-backend")]
fn phase58_pcs_column_log_size(logical_element_count: usize) -> Result<u32> {
    u32::try_from(phase53_padded_log2(logical_element_count)?)
        .map_err(|_| VmError::InvalidConfig("Phase 58 PCS column log size exceeds u32".to_string()))
}

#[cfg(feature = "stwo-backend")]
fn phase58_m31_inverse(value: u32) -> Result<u32> {
    if value == 0 || value >= PHASE44D_M31_MODULUS {
        return Err(VmError::InvalidConfig(
            "Phase 58 M31 inverse requires a non-zero field element".to_string(),
        ));
    }
    let mut base = value;
    let mut exp = u64::from(PHASE44D_M31_MODULUS - 2);
    let mut acc = 1u32;
    while exp > 0 {
        if exp & 1 == 1 {
            acc = phase52_m31_mul(acc, base);
        }
        base = phase52_m31_mul(base, base);
        exp >>= 1;
    }
    Ok(acc)
}

#[cfg(feature = "stwo-backend")]
fn phase58_derive_pcs_opening_point_index(opening: &Phase58WitnessBoundPcsOpening) -> Result<u64> {
    phase43_require_hash32(
        "phase58_pcs_point_source_receipt",
        &opening.source_phase57_opening_receipt_commitment,
    )?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 58 PCS point hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase58-pcs-opening-point-index");
    for part in [
        opening.source_phase57_opening_receipt_commitment.as_bytes(),
        opening.opening_name.as_bytes(),
        opening.opening_kind.as_bytes(),
        opening.raw_witness_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!("failed to finalize Phase 58 PCS point hash: {err}"))
    })?;
    let mut index_bytes = [0u8; 8];
    index_bytes.copy_from_slice(&out[..8]);
    Ok(u64::from_le_bytes(index_bytes).saturating_add(1))
}

#[cfg(feature = "stwo-backend")]
fn phase58_circle_point_from_index(index: u64) -> Result<CirclePoint<SecureField>> {
    if index == 0 || u128::from(index) >= SECURE_FIELD_CIRCLE_ORDER {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS opening point index outside the secure circle group".to_string(),
        ));
    }
    Ok(CirclePoint::<SecureField>::get_point(u128::from(index)))
}

#[cfg(feature = "stwo-backend")]
fn phase58_lifted_circle_point(
    log_size: u32,
    lifting_log_size: u32,
    point_index: u64,
) -> Result<CirclePoint<SecureField>> {
    let extended_log_size = log_size
        .checked_add(PcsConfig::default().fri_config.log_blowup_factor)
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 58 PCS extended log-size overflow".to_string())
        })?;
    if lifting_log_size < extended_log_size {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS lifting log size is smaller than the extended column log size"
                .to_string(),
        ));
    }
    if lifting_log_size > PHASE58_MAX_PCS_LIFTING_LOG_SIZE {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS lifting log size exceeds bounded verifier limit".to_string(),
        ));
    }
    Ok(phase58_circle_point_from_index(point_index)?
        .repeated_double(lifting_log_size - extended_log_size))
}

#[cfg(feature = "stwo-backend")]
fn phase58_circle_evaluation_for_witness(
    raw_values: &[u32],
    log_size: u32,
) -> Result<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>> {
    phase52_validate_m31_values("phase58_pcs_raw_values", raw_values)?;
    let row_count = 1usize.checked_shl(log_size).ok_or_else(|| {
        VmError::InvalidConfig("Phase 58 PCS column log size overflow".to_string())
    })?;
    if raw_values.len() > row_count {
        return Err(VmError::InvalidConfig(
            "Phase 58 raw witness exceeds PCS column domain".to_string(),
        ));
    }
    let domain = CanonicCoset::new(log_size).circle_domain();
    let mut column = Col::<CpuBackend, BaseField>::zeros(row_count);
    for (index, value) in raw_values.iter().copied().enumerate() {
        column.set(index, BaseField::from(value));
    }
    Ok(CircleEvaluation::<CpuBackend, BaseField, NaturalOrder>::new(domain, column).bit_reverse())
}

#[cfg(feature = "stwo-backend")]
fn phase58_circle_sample_value(
    raw_values: &[u32],
    log_size: u32,
    lifting_log_size: u32,
    point_index: u64,
) -> Result<SecureField> {
    let point = phase58_lifted_circle_point(log_size, lifting_log_size, point_index)?;
    let evaluation = phase58_circle_evaluation_for_witness(raw_values, log_size)?;
    Ok(evaluation.interpolate().eval_at_point(point))
}

#[cfg(feature = "stwo-backend")]
fn phase58_unlifted_stwo_pcs_api_sample_point(
    opening: &Phase58WitnessBoundPcsOpening,
) -> Result<Vec<CirclePoint<SecureField>>> {
    // S-two's PCS API expects the unlifted OODS point here. Its prover/verifier
    // path lifts each column relative to the committed domain, equivalent to
    // `lifting_log_size - (pcs_column_log_size + fri_log_blowup)`. Phase58 uses
    // that same lifted point only when recomputing the sampled value; pre-lifting
    // this API argument would double-lift it.
    phase58_circle_point_from_index(opening.pcs_opening_point_index).map(|point| vec![point])
}

#[cfg(feature = "stwo-backend")]
fn phase58_secure_field_limbs(value: SecureField) -> Vec<u32> {
    value
        .to_m31_array()
        .into_iter()
        .map(|limb| limb.0)
        .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase58_secure_field_from_limbs(limbs: &[u32]) -> Result<SecureField> {
    if limbs.len() != 4 {
        return Err(VmError::InvalidConfig(
            "Phase 58 secure-field sampled value must have four M31 limbs".to_string(),
        ));
    }
    phase52_validate_m31_values("phase58_secure_field_limbs", limbs)?;
    Ok(SecureField::from_m31_array([
        BaseField::from(limbs[0]),
        BaseField::from(limbs[1]),
        BaseField::from(limbs[2]),
        BaseField::from(limbs[3]),
    ]))
}

#[cfg(feature = "stwo-backend")]
fn phase58_commit_pcs_sampled_value_limbs(limbs: &[u32]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 58 sampled value hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase58-pcs-sampled-value-limbs");
    phase44d_update_u32_vec(&mut hasher, limbs);
    phase44d_finalize_hash(hasher, "Phase 58 PCS sampled value")
}

#[cfg(feature = "stwo-backend")]
fn phase58_commit_pcs_proof_bytes(bytes: &[u8]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 58 PCS proof-byte hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase58-stwo-pcs-opening-proof-bytes");
    phase29_update_usize(&mut hasher, bytes.len());
    phase29_update_len_prefixed(&mut hasher, bytes);
    phase44d_finalize_hash(hasher, "Phase 58 PCS proof bytes")
}

#[cfg(all(feature = "stwo-backend", test))]
pub(crate) fn phase58_commit_pcs_proof_bytes_for_tests(bytes: &[u8]) -> Result<String> {
    phase58_commit_pcs_proof_bytes(bytes)
}

#[cfg(feature = "stwo-backend")]
fn phase58_witness_opening_payload_bytes(opening: &Phase58WitnessBoundPcsOpening) -> Result<usize> {
    let payload = serde_json::json!({
        "proof_backend": opening.proof_backend.to_string(),
        "source_phase57_opening_receipt_commitment": &opening.source_phase57_opening_receipt_commitment,
        "source_phase56_executable_claim_commitment": &opening.source_phase56_executable_claim_commitment,
        "source_phase54_opening_claim_commitment": &opening.source_phase54_opening_claim_commitment,
        "opening_name": &opening.opening_name,
        "opening_kind": &opening.opening_kind,
        "opening_scheme": &opening.opening_scheme,
        "tensor_shape": &opening.tensor_shape,
        "logical_element_count": opening.logical_element_count,
        "padded_element_count": opening.padded_element_count,
        "opening_point_dimension": opening.opening_point_dimension,
        "opening_point": &opening.opening_point,
        "opened_value": opening.opened_value,
        "raw_witness_values": &opening.raw_witness_values,
        "raw_witness_commitment": &opening.raw_witness_commitment,
        "adjusted_witness_index": opening.adjusted_witness_index,
        "adjusted_witness_basis_weight": opening.adjusted_witness_basis_weight,
        "recomputed_mle_value": opening.recomputed_mle_value,
        "pcs_column_log_size": opening.pcs_column_log_size,
        "pcs_lifting_log_size": opening.pcs_lifting_log_size,
        "pcs_opening_point_index": opening.pcs_opening_point_index,
        "pcs_sampled_value_limbs": &opening.pcs_sampled_value_limbs,
        "pcs_sampled_value_commitment": &opening.pcs_sampled_value_commitment,
        "opening_witness_binding_available": opening.opening_witness_binding_available,
        "pcs_opening_proof_available": opening.pcs_opening_proof_available,
        "cryptographic_opening_soundness_claimed": opening.cryptographic_opening_soundness_claimed,
        "full_relation_soundness_claimed": opening.full_relation_soundness_claimed,
    });
    serde_json::to_vec(&payload)
        .map(|bytes| bytes.len())
        .map_err(|err| VmError::Serialization(err.to_string()))
}

#[cfg(feature = "stwo-backend")]
fn phase58_witness_binding_surface_unit_count(
    opening_count: usize,
    total_raw_witness_element_count: usize,
    total_opening_point_dimension: usize,
) -> Result<usize> {
    opening_count
        .checked_mul(3)
        .and_then(|value| value.checked_add(total_opening_point_dimension))
        .and_then(|value| value.checked_add(total_raw_witness_element_count))
        .and_then(|value| value.checked_add(1))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 58 witness-binding surface accounting overflow".to_string(),
            )
        })
}

#[cfg(feature = "stwo-backend")]
fn phase58_witness_pcs_opening_transcript_order() -> Vec<String> {
    [
        "phase58_witness_pcs_opening_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase57_opening_verifier_claim_commitment",
        "ordered_phase57_opening_receipts",
        "canonical_raw_witness_commitments",
        "mle_points_and_recomputed_values",
        "pcs_column_log_sizes",
        "pcs_opening_point_indices",
        "pcs_sampled_values",
        "stwo_pcs_opening_proof_bytes",
        "surface_and_byte_accounting",
        "availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase58_build_pcs_opening_proof(openings: &[Phase58WitnessBoundPcsOpening]) -> Result<Vec<u8>> {
    if openings.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS opening proof requires at least one opening".to_string(),
        ));
    }
    let config = PcsConfig::default();
    let max_log_size = openings
        .iter()
        .map(|opening| opening.pcs_column_log_size)
        .max()
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 58 PCS opening proof has no columns".to_string())
        })?;
    let twiddle_log_size = max_log_size
        .checked_add(config.fri_config.log_blowup_factor)
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 58 PCS twiddle log-size overflow".to_string())
        })?;
    let twiddles =
        CpuBackend::precompute_twiddles(CanonicCoset::new(twiddle_log_size).half_coset());
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();
    let evaluations = openings
        .iter()
        .map(|opening| {
            phase58_circle_evaluation_for_witness(
                &opening.raw_witness_values,
                opening.pcs_column_log_size,
            )
        })
        .collect::<Result<Vec<_>>>()?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(evaluations);
    tree_builder.commit(channel);
    let sampled_points = TreeVec(vec![openings
        .iter()
        .map(phase58_unlifted_stwo_pcs_api_sample_point)
        .collect::<Result<Vec<_>>>()?]);
    let proof = commitment_scheme.prove_values(sampled_points, channel);
    let bytes = serde_json::to_vec(&Phase58PcsOpeningProofPayload { proof: proof.proof })
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    phase58_verify_pcs_opening_proof_bytes(openings, &bytes)?;
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn phase58_verify_pcs_opening_proof_bytes(
    openings: &[Phase58WitnessBoundPcsOpening],
    proof_bytes: &[u8],
) -> Result<()> {
    if openings.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS opening verification requires at least one opening".to_string(),
        ));
    }
    let payload: Phase58PcsOpeningProofPayload = serde_json::from_slice(proof_bytes)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    let proof = payload.proof;
    if proof.commitments.len() != 1
        || proof.sampled_values.0.len() != 1
        || proof.sampled_values.0[0].len() != openings.len()
    {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS proof sampled-value shape drift".to_string(),
        ));
    }
    for (opening, sampled_values) in openings.iter().zip(proof.sampled_values.0[0].iter()) {
        if sampled_values.len() != 1 {
            return Err(VmError::InvalidConfig(
                "Phase 58 PCS proof must contain exactly one sampled value per opening".to_string(),
            ));
        }
        let expected_sample = phase58_circle_sample_value(
            &opening.raw_witness_values,
            opening.pcs_column_log_size,
            opening.pcs_lifting_log_size,
            opening.pcs_opening_point_index,
        )?;
        if sampled_values[0] != expected_sample
            || phase58_secure_field_limbs(sampled_values[0]) != opening.pcs_sampled_value_limbs
            || phase58_secure_field_from_limbs(&opening.pcs_sampled_value_limbs)? != expected_sample
        {
            return Err(VmError::InvalidConfig(
                "Phase 58 PCS proof sampled value does not match witness column".to_string(),
            ));
        }
    }
    let sampled_points = TreeVec(vec![openings
        .iter()
        .map(phase58_unlifted_stwo_pcs_api_sample_point)
        .collect::<Result<Vec<_>>>()?]);
    let log_sizes = openings
        .iter()
        .map(|opening| opening.pcs_column_log_size)
        .collect::<Vec<_>>();
    let config = PcsConfig::default();
    if proof.config != config {
        return Err(VmError::InvalidConfig(
            "Phase 58 PCS proof config drift".to_string(),
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let mut verifier = CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    verifier.commit(proof.commitments[0], &log_sizes, channel);
    verifier
        .verify_values(sampled_points, proof, channel)
        .map_err(|err| {
            VmError::UnsupportedProof(format!(
                "Phase 58 S-two PCS opening verification failed: {err:?}"
            ))
        })?;
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase46_check_bridge_lane(
    bridge: &Phase45RecursiveVerifierPublicInputBridge,
    label: &str,
    expected: &str,
) -> Result<()> {
    let actual = bridge
        .ordered_public_input_lanes
        .iter()
        .find(|lane| lane.label == label)
        .ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "Phase 46 Stwo proof-adapter receipt missing Phase45 lane `{label}`"
            ))
        })?;
    if actual.value != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 46 Stwo proof-adapter receipt Phase45 lane `{label}` does not match compact verifier input"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
const PHASE45_PUBLIC_INPUT_LANE_LABELS: [&str; 24] = [
    "source_chain_public_output_boundary_commitment",
    "source_emission_public_output_commitment",
    "emitted_root_artifact_commitment",
    "compact_envelope_commitment",
    "source_root_acceptance_commitment",
    "terminal_boundary_logup_closure_commitment",
    "emitted_canonical_source_root",
    "source_root_preimage_commitment",
    "phase43_trace_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "projection_commitment",
    "compact_projection_trace_root",
    "compact_preprocessed_trace_root",
    "terminal_boundary_commitment",
    "terminal_boundary_logup_statement_commitment",
    "terminal_boundary_public_logup_sum_limbs",
    "terminal_boundary_component_claimed_sum_limbs",
    "compact_proof_size_bytes",
    "total_steps",
    "pair_width",
    "projection_row_count",
    "projection_column_count",
    "verifier_side_complexity",
];

#[cfg(feature = "stwo-backend")]
fn phase45_ordered_public_input_lanes(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    handoff: &Phase44DRecursiveVerifierPublicOutputHandoff,
    terminal_boundary_logup_closure: &Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure,
) -> Result<Vec<Phase45RecursiveVerifierPublicInputLane>> {
    let acceptance =
        verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
            boundary,
            compact_envelope,
        )?;
    let compact_envelope_commitment = phase44d_commit_compact_envelope_reference(compact_envelope)?;
    let source_root_acceptance_commitment =
        phase44d_commit_source_root_acceptance_reference(&acceptance)?;
    let source_emission = &boundary.source_emission_public_output.source_emission;
    let source_claim = &source_emission.source_claim;
    let raw_lanes = vec![
        (
            "source_chain_public_output_boundary_commitment",
            "hash32",
            boundary
                .source_chain_public_output_boundary_commitment
                .clone(),
        ),
        (
            "source_emission_public_output_commitment",
            "hash32",
            boundary
                .source_emission_public_output
                .public_output_commitment
                .clone(),
        ),
        (
            "emitted_root_artifact_commitment",
            "hash32",
            source_emission
                .emitted_root_artifact
                .artifact_commitment
                .clone(),
        ),
        (
            "compact_envelope_commitment",
            "hash32",
            compact_envelope_commitment,
        ),
        (
            "source_root_acceptance_commitment",
            "hash32",
            source_root_acceptance_commitment,
        ),
        (
            "terminal_boundary_logup_closure_commitment",
            "hash32",
            terminal_boundary_logup_closure.closure_commitment.clone(),
        ),
        (
            "emitted_canonical_source_root",
            "hash32",
            acceptance.emitted_canonical_source_root.clone(),
        ),
        (
            "source_root_preimage_commitment",
            "hash32",
            acceptance.source_root_preimage_commitment.clone(),
        ),
        (
            "phase43_trace_commitment",
            "hash32",
            boundary.phase43_trace_commitment.clone(),
        ),
        (
            "phase30_source_chain_commitment",
            "hash32",
            boundary.phase30_source_chain_commitment.clone(),
        ),
        (
            "phase30_step_envelopes_commitment",
            "hash32",
            boundary.phase30_step_envelopes_commitment.clone(),
        ),
        (
            "projection_commitment",
            "hash32",
            source_claim.projection_commitment.clone(),
        ),
        (
            "compact_projection_trace_root",
            "hash32",
            acceptance.compact_projection_trace_root.clone(),
        ),
        (
            "compact_preprocessed_trace_root",
            "hash32",
            acceptance.compact_preprocessed_trace_root.clone(),
        ),
        (
            "terminal_boundary_commitment",
            "hash32",
            source_claim
                .terminal_boundary
                .terminal_boundary_commitment
                .clone(),
        ),
        (
            "terminal_boundary_logup_statement_commitment",
            "hash32",
            acceptance
                .terminal_boundary_logup_statement_commitment
                .clone(),
        ),
        (
            "terminal_boundary_public_logup_sum_limbs",
            "u32_vec",
            phase45_join_u32_limbs(&source_claim.terminal_boundary_public_logup_sum_limbs),
        ),
        (
            "terminal_boundary_component_claimed_sum_limbs",
            "u32_vec",
            phase45_join_u32_limbs(
                &terminal_boundary_logup_closure.terminal_boundary_component_claimed_sum_limbs,
            ),
        ),
        (
            "compact_proof_size_bytes",
            "usize",
            compact_envelope.proof.len().to_string(),
        ),
        ("total_steps", "usize", boundary.total_steps.to_string()),
        ("pair_width", "usize", boundary.pair_width.to_string()),
        (
            "projection_row_count",
            "usize",
            boundary.projection_row_count.to_string(),
        ),
        (
            "projection_column_count",
            "usize",
            boundary.projection_column_count.to_string(),
        ),
        (
            "verifier_side_complexity",
            "string",
            handoff.verifier_side_complexity.clone(),
        ),
    ];
    if raw_lanes.len() != PHASE45_PUBLIC_INPUT_LANE_LABELS.len() {
        return Err(VmError::InvalidConfig(
            "Phase 45 public-input bridge internal lane count drift".to_string(),
        ));
    }
    let mut lanes = Vec::with_capacity(raw_lanes.len());
    for (index, (label, value_kind, value)) in raw_lanes.into_iter().enumerate() {
        if label != PHASE45_PUBLIC_INPUT_LANE_LABELS[index] {
            return Err(VmError::InvalidConfig(
                "Phase 45 public-input bridge internal lane order drift".to_string(),
            ));
        }
        lanes.push(Phase45RecursiveVerifierPublicInputLane {
            index,
            label: label.to_string(),
            value_kind: value_kind.to_string(),
            value,
        });
    }
    Ok(lanes)
}

#[cfg(feature = "stwo-backend")]
fn phase45_join_u32_limbs(values: &[u32]) -> String {
    values
        .iter()
        .map(u32::to_string)
        .collect::<Vec<_>>()
        .join(",")
}

#[cfg(feature = "stwo-backend")]
fn phase44d_commit_compact_envelope_reference(
    envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D compact envelope reference hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase44d-compact-envelope-reference");
    phase44d_update_compact_claim_reference(&mut hasher, envelope)?;
    phase29_update_usize(&mut hasher, envelope.proof.len());
    hasher.update(&envelope.proof);
    phase44d_finalize_hash(hasher, "Phase 44D compact envelope reference")
}

#[cfg(feature = "stwo-backend")]
fn phase44d_update_compact_claim_reference(
    hasher: &mut Blake2bVar,
    envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<()> {
    let claim = &envelope.claim;
    phase29_update_len_prefixed(&mut *hasher, claim.proof_backend.to_string().as_bytes());
    for part in [
        claim.claim_version.as_bytes(),
        claim.proof_backend_version.as_bytes(),
        claim.statement_version.as_bytes(),
        claim.semantic_scope.as_bytes(),
        claim.phase43_trace_commitment.as_bytes(),
        claim.phase43_trace_version.as_bytes(),
        claim.projection_commitment.as_bytes(),
        claim.stwo_preprocessed_trace_root.as_bytes(),
        claim.stwo_projection_trace_root.as_bytes(),
        claim.source_binding.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut *hasher, part);
    }
    phase29_update_usize(&mut *hasher, claim.total_steps);
    phase29_update_usize(&mut *hasher, claim.pair_width);
    hasher.update(&claim.log_size.to_le_bytes());
    phase29_update_usize(&mut *hasher, claim.projection_row_count);
    phase29_update_usize(&mut *hasher, claim.projection_column_count);
    phase44d_update_u32_vec(&mut *hasher, &claim.preprocessed_trace_log_sizes);
    phase44d_update_u32_vec(&mut *hasher, &claim.projection_trace_log_sizes);
    phase44d_update_terminal_boundary_reference(&mut *hasher, &claim.terminal_boundary);
    phase29_update_bool(&mut *hasher, claim.verifier_requires_full_phase43_trace);
    phase29_update_bool(
        &mut *hasher,
        claim.verifier_embeds_projection_rows_as_constants,
    );
    phase29_update_bool(&mut *hasher, claim.useful_compression_boundary);
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase44d_update_terminal_boundary_reference(
    hasher: &mut Blake2bVar,
    boundary: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) {
    for part in [
        boundary.boundary_version.as_bytes(),
        boundary.phase12_initial_public_state_commitment.as_bytes(),
        boundary.phase12_terminal_public_state_commitment.as_bytes(),
        boundary.phase14_initial_public_state_commitment.as_bytes(),
        boundary.phase14_terminal_public_state_commitment.as_bytes(),
        boundary.initial_input_lookup_rows_commitment.as_bytes(),
        boundary.terminal_output_lookup_rows_commitment.as_bytes(),
        boundary.terminal_boundary_commitment.as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut *hasher, part);
    }
    hasher.update(&boundary.phase12_initial_position.to_le_bytes());
    hasher.update(&boundary.phase12_terminal_position.to_le_bytes());
    hasher.update(&boundary.phase14_initial_position.to_le_bytes());
    hasher.update(&boundary.phase14_terminal_position.to_le_bytes());
    phase29_update_usize(&mut *hasher, boundary.phase12_initial_history_len);
    phase29_update_usize(&mut *hasher, boundary.phase12_terminal_history_len);
    phase29_update_usize(&mut *hasher, boundary.phase14_initial_history_len);
    phase29_update_usize(&mut *hasher, boundary.phase14_terminal_history_len);
}

#[cfg(feature = "stwo-backend")]
fn phase44d_commit_source_root_acceptance_reference(
    acceptance: &Phase44DHistoryReplayProjectionExternalSourceRootAcceptance,
) -> Result<String> {
    if acceptance.acceptance_version
        != STWO_HISTORY_REPLAY_PROJECTION_EXTERNAL_SOURCE_ROOT_ACCEPTANCE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-root acceptance reference version drift".to_string(),
        ));
    }
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D source-root acceptance reference hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase44d-source-root-acceptance-reference");
    for part in [
        acceptance.acceptance_version.as_bytes(),
        acceptance.emitted_canonical_source_root.as_bytes(),
        acceptance.source_claim_canonical_source_root.as_bytes(),
        acceptance.source_root_preimage_commitment.as_bytes(),
        acceptance.compact_projection_trace_root.as_bytes(),
        acceptance.compact_preprocessed_trace_root.as_bytes(),
        acceptance
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
    ] {
        phase29_update_len_prefixed(&mut hasher, part);
    }
    phase29_update_bool(
        &mut hasher,
        acceptance.compact_claim_useful_compression_boundary,
    );
    phase29_update_bool(&mut hasher, acceptance.final_useful_compression_boundary);
    phase44d_finalize_hash(hasher, "Phase 44D source-root acceptance reference")
}

#[cfg(feature = "stwo-backend")]
fn phase44d_commit_recursive_verifier_handoff_list(commitments: &[String]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D recursive-verifier handoff list hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase44d-recursive-verifier-handoff-list");
    phase44d_update_hash_vec(&mut hasher, commitments);
    phase44d_finalize_hash(hasher, "Phase 44D recursive-verifier handoff list")
}

#[cfg(feature = "stwo-backend")]
fn phase44d_update_hash_vec(hasher: &mut Blake2bVar, values: &[String]) {
    phase29_update_usize(&mut *hasher, values.len());
    for value in values {
        phase29_update_len_prefixed(&mut *hasher, value.as_bytes());
    }
}

#[cfg(feature = "stwo-backend")]
fn phase44d_update_u32_vec(hasher: &mut Blake2bVar, values: &[u32]) {
    phase29_update_usize(&mut *hasher, values.len());
    for value in values {
        hasher.update(&value.to_le_bytes());
    }
}

#[cfg(feature = "stwo-backend")]
fn phase44d_update_usize_vec(hasher: &mut Blake2bVar, values: &[usize]) {
    phase29_update_usize(&mut *hasher, values.len());
    for value in values {
        phase29_update_usize(&mut *hasher, *value);
    }
}

#[cfg(feature = "stwo-backend")]
fn phase44d_secure_field_from_limbs(label: &str, limbs: &[u32]) -> Result<SecureField> {
    if limbs.len() != 4 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D `{label}` must have 4 M31 limbs, got {}",
            limbs.len()
        )));
    }
    for limb in limbs {
        if *limb >= PHASE44D_M31_MODULUS {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44D `{label}` limb {limb} exceeds M31 capacity"
            )));
        }
    }
    Ok(SecureField::from_m31_array([
        BaseField::from_u32_unchecked(limbs[0]),
        BaseField::from_u32_unchecked(limbs[1]),
        BaseField::from_u32_unchecked(limbs[2]),
        BaseField::from_u32_unchecked(limbs[3]),
    ]))
}

#[cfg(feature = "stwo-backend")]
fn phase44d_finalize_hash(hasher: Blake2bVar, label: &str) -> Result<String> {
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!("failed to finalize {label} commitment hash: {err}"))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase50_tensor_transcript_order() -> Vec<String> {
    [
        "phase50_domain_tag",
        "claim_version",
        "semantic_scope",
        "tensor_role",
        "tensor_name",
        "element_field",
        "memory_layout",
        "quantization",
        "tensor_shape_len",
        "tensor_shape",
        "logical_element_count",
        "padded_element_count",
        "padding_rule",
        "commitment_scheme",
        "commitment_root",
        "mle_evaluation_claim_status",
        "raw_endpoint_anchor_required",
        "raw_endpoint_anchor_available",
        "vm_replay_flags",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase50_layer_io_transcript_order() -> Vec<String> {
    [
        "phase50_layer_io_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase49_contract_version",
        "source_phase49_contract_commitment",
        "proof_backend_version",
        "statement_version",
        "layer_index",
        "layer_name",
        "layer_kind",
        "input_tensor_claim_commitment",
        "output_tensor_claim_commitment",
        "relation_claim_kind",
        "relation_rule",
        "propagation_direction",
        "endpoint_anchoring_rule",
        "claim_surface_unit_count",
        "proof_availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase51_operation_graph_order() -> Vec<String> {
    [
        "gate_affine",
        "value_affine",
        "hidden_hadamard_product",
        "output_affine",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase51_relation_transcript_order() -> Vec<String> {
    [
        "phase51_relation_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase50_layer_io_claim_commitment",
        "source_phase49_contract_commitment",
        "proof_backend_version",
        "statement_version",
        "relation_kind",
        "relation_rule",
        "relation_field",
        "layer_index",
        "input_width",
        "hidden_width",
        "output_width",
        "gate_projection_shape",
        "value_projection_shape",
        "hidden_product_shape",
        "output_projection_shape",
        "bias_lengths",
        "operation_graph_order",
        "parameter_commitment_scheme",
        "surface_accounting",
        "proof_availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase52_endpoint_transcript_order() -> Vec<String> {
    [
        "phase52_endpoint_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase50_tensor_claim_commitment",
        "source_phase51_relation_claim_commitment",
        "endpoint_role",
        "tensor_name",
        "element_field",
        "tensor_shape",
        "raw_tensor_values",
        "raw_tensor_commitment",
        "mle_point",
        "mle_value",
        "challenge_derivation",
        "evaluation_rule",
        "proof_availability_flags",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase52_layer_endpoint_transcript_order() -> Vec<String> {
    [
        "phase52_layer_endpoint_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase51_relation_claim_commitment",
        "source_phase50_layer_io_claim_commitment",
        "input_endpoint_claim_commitment",
        "output_endpoint_claim_commitment",
        "endpoint_count",
        "public_endpoint_width",
        "endpoint_anchoring_available",
        "proof_availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase53_benchmark_transcript_order() -> Vec<String> {
    [
        "phase53_relation_benchmark_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase52_anchoring_claim_commitment",
        "source_phase51_relation_claim_commitment",
        "source_phase50_layer_io_claim_commitment",
        "relation_kind",
        "relation_rule",
        "relation_field",
        "matmul_shapes",
        "sumcheck_round_surface",
        "relation_arithmetic_surface",
        "parameter_binding_scheme",
        "parameter_binding_commitment",
        "endpoint_public_width",
        "benchmark_status",
        "proof_availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase54_skeleton_transcript_order() -> Vec<String> {
    [
        "phase54_sumcheck_skeleton_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase53_benchmark_claim_commitment",
        "source_phase52_anchoring_claim_commitment",
        "source_phase51_relation_claim_commitment",
        "source_phase50_layer_io_claim_commitment",
        "source_phase53_parameter_binding_commitment",
        "ordered_component_claim_commitments",
        "ordered_parameter_opening_claim_commitments",
        "surface_accounting",
        "proof_availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase55_effectiveness_transcript_order() -> Vec<String> {
    [
        "phase55_effectiveness_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase54_skeleton_claim_commitment",
        "source_phase53_benchmark_claim_commitment",
        "measurement_kind",
        "vm_replay_surface_proxy",
        "tensor_proof_skeleton_surface",
        "surface_proxy_ratios",
        "decision_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase54_component_order() -> Vec<String> {
    [
        "gate_affine_sumcheck",
        "value_affine_sumcheck",
        "hidden_hadamard_eq_sumcheck",
        "output_affine_sumcheck",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase54_parameter_opening_order() -> Vec<String> {
    [
        "gate_weight_mle_opening",
        "gate_bias_mle_opening",
        "value_weight_mle_opening",
        "value_bias_mle_opening",
        "output_weight_mle_opening",
        "output_bias_mle_opening",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase54_component_spec(
    component_name: &str,
) -> Result<(String, Vec<usize>, usize, usize, usize, usize)> {
    let hidden_width = TransformerVmConfig::percepta_reference().ff_dim;
    match component_name {
        "gate_affine_sumcheck" => Ok((
            "matmul_sumcheck".to_string(),
            vec![1, INPUT_DIM, hidden_width],
            INPUT_DIM,
            2,
            1,
            2,
        )),
        "value_affine_sumcheck" => Ok((
            "matmul_sumcheck".to_string(),
            vec![1, INPUT_DIM, hidden_width],
            INPUT_DIM,
            2,
            1,
            2,
        )),
        "hidden_hadamard_eq_sumcheck" => Ok((
            "hadamard_eq_sumcheck".to_string(),
            vec![hidden_width],
            hidden_width,
            3,
            2,
            0,
        )),
        "output_affine_sumcheck" => Ok((
            "matmul_sumcheck".to_string(),
            vec![1, hidden_width, OUTPUT_DIM],
            hidden_width,
            2,
            1,
            2,
        )),
        _ => Err(VmError::InvalidConfig(format!(
            "Phase 54 unknown sumcheck component `{component_name}`"
        ))),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase54_parameter_opening_spec(parameter_name: &str) -> Result<(String, Vec<usize>)> {
    let hidden_width = TransformerVmConfig::percepta_reference().ff_dim;
    match parameter_name {
        "gate_weight_mle_opening" => Ok(("gate_weight".to_string(), vec![INPUT_DIM, hidden_width])),
        "gate_bias_mle_opening" => Ok(("gate_bias".to_string(), vec![hidden_width])),
        "value_weight_mle_opening" => {
            Ok(("value_weight".to_string(), vec![INPUT_DIM, hidden_width]))
        }
        "value_bias_mle_opening" => Ok(("value_bias".to_string(), vec![hidden_width])),
        "output_weight_mle_opening" => {
            Ok(("output_weight".to_string(), vec![hidden_width, OUTPUT_DIM]))
        }
        "output_bias_mle_opening" => Ok(("output_bias".to_string(), vec![OUTPUT_DIM])),
        _ => Err(VmError::InvalidConfig(format!(
            "Phase 54 unknown parameter opening `{parameter_name}`"
        ))),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase54_prepare_sumcheck_component_skeletons(
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<Vec<Phase54SumcheckComponentSkeleton>> {
    phase54_component_order()
        .into_iter()
        .map(|component_name| {
            phase54_prepare_sumcheck_component_skeleton(phase53_claim, &component_name)
        })
        .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase54_prepare_sumcheck_component_skeleton(
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
    component_name: &str,
) -> Result<Phase54SumcheckComponentSkeleton> {
    let (
        component_kind,
        component_shape,
        inner_or_domain_width,
        round_polynomial_degree,
        runtime_tensor_opening_count,
        parameter_opening_count,
    ) = phase54_component_spec(component_name)?;
    let padded_inner_or_domain_width = phase50_next_power_of_two(inner_or_domain_width)?;
    let round_count = phase53_padded_log2(inner_or_domain_width)?;
    let round_polynomial_coefficient_count = round_count * (round_polynomial_degree + 1);
    let final_evaluation_count = 2;
    let round_polynomial_commitment = phase54_derive_artifact_commitment(
        &phase53_claim.benchmark_claim_commitment,
        component_name,
        "round_polynomials",
        &component_shape,
        round_count,
        round_polynomial_degree,
    )?;
    let final_evaluation_commitment = phase54_derive_artifact_commitment(
        &phase53_claim.benchmark_claim_commitment,
        component_name,
        "final_evaluations",
        &component_shape,
        final_evaluation_count,
        round_polynomial_degree,
    )?;
    let opening_receipt_commitment = phase54_derive_artifact_commitment(
        &phase53_claim.benchmark_claim_commitment,
        component_name,
        "opening_receipts",
        &component_shape,
        runtime_tensor_opening_count + parameter_opening_count,
        round_polynomial_degree,
    )?;
    let mut component = Phase54SumcheckComponentSkeleton {
        proof_backend: StarkProofBackend::Stwo,
        source_phase53_benchmark_claim_commitment: phase53_claim.benchmark_claim_commitment.clone(),
        component_name: component_name.to_string(),
        component_kind,
        relation_field: STWO_FIRST_LAYER_RELATION_FIELD_PHASE51.to_string(),
        component_shape,
        inner_or_domain_width,
        padded_inner_or_domain_width,
        round_count,
        round_polynomial_degree,
        round_polynomial_coefficient_count,
        final_evaluation_count,
        runtime_tensor_opening_count,
        parameter_opening_count,
        transcript_protocol: STWO_FIRST_LAYER_SUMCHECK_SKELETON_TRANSCRIPT_PROTOCOL_PHASE54
            .to_string(),
        round_polynomial_commitment,
        final_evaluation_commitment,
        opening_receipt_commitment,
        typed_proof_skeleton_available: true,
        actual_round_polynomial_values_available: false,
        actual_opening_proofs_available: false,
        cryptographic_soundness_claimed: false,
        component_claim_commitment: String::new(),
    };
    component.component_claim_commitment = commit_phase54_sumcheck_component_skeleton(&component)?;
    verify_phase54_sumcheck_component_skeleton(&component)?;
    Ok(component)
}

#[cfg(feature = "stwo-backend")]
fn phase54_prepare_parameter_opening_skeletons(
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
) -> Result<Vec<Phase54ParameterOpeningSkeleton>> {
    phase54_parameter_opening_order()
        .into_iter()
        .map(|parameter_name| {
            phase54_prepare_parameter_opening_skeleton(phase53_claim, &parameter_name)
        })
        .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase54_prepare_parameter_opening_skeleton(
    phase53_claim: &Phase53FirstLayerRelationBenchmarkClaim,
    parameter_name: &str,
) -> Result<Phase54ParameterOpeningSkeleton> {
    let (parameter_role, tensor_shape) = phase54_parameter_opening_spec(parameter_name)?;
    let logical_element_count = phase50_tensor_element_count(&tensor_shape)?;
    let padded_element_count = phase50_next_power_of_two(logical_element_count)?;
    let opening_point_dimension = phase53_padded_log2(logical_element_count)?;
    let opening_value_count = 1;
    let opening_receipt_commitment = phase54_derive_artifact_commitment(
        &phase53_claim.benchmark_claim_commitment,
        parameter_name,
        "parameter_opening_receipt",
        &tensor_shape,
        opening_point_dimension,
        opening_value_count,
    )?;
    let mut opening = Phase54ParameterOpeningSkeleton {
        proof_backend: StarkProofBackend::Stwo,
        source_phase53_benchmark_claim_commitment: phase53_claim.benchmark_claim_commitment.clone(),
        source_phase53_parameter_binding_commitment: phase53_claim
            .parameter_binding_commitment
            .clone(),
        parameter_name: parameter_name.to_string(),
        parameter_role,
        tensor_shape,
        logical_element_count,
        padded_element_count,
        opening_point_dimension,
        opening_value_count,
        opening_scheme: STWO_FIRST_LAYER_SUMCHECK_SKELETON_PARAMETER_OPENING_SCHEME_PHASE54
            .to_string(),
        opening_receipt_commitment,
        opening_proof_available: false,
        cryptographic_soundness_claimed: false,
        parameter_opening_claim_commitment: String::new(),
    };
    opening.parameter_opening_claim_commitment =
        commit_phase54_parameter_opening_skeleton(&opening)?;
    verify_phase54_parameter_opening_skeleton(&opening)?;
    Ok(opening)
}

#[cfg(feature = "stwo-backend")]
fn phase54_derive_artifact_commitment(
    source_claim_commitment: &str,
    item_name: &str,
    artifact_kind: &str,
    shape: &[usize],
    primary_count: usize,
    secondary_count: usize,
) -> Result<String> {
    phase43_require_hash32(
        "phase54_artifact_source_claim_commitment",
        source_claim_commitment,
    )?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 54 artifact commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase54-derived-artifact-commitment");
    phase29_update_len_prefixed(&mut hasher, source_claim_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, item_name.as_bytes());
    phase29_update_len_prefixed(&mut hasher, artifact_kind.as_bytes());
    phase44d_update_usize_vec(&mut hasher, shape);
    phase29_update_usize(&mut hasher, primary_count);
    phase29_update_usize(&mut hasher, secondary_count);
    phase44d_finalize_hash(hasher, "Phase 54 derived artifact commitment")
}

#[cfg(feature = "stwo-backend")]
fn phase55_ratio_basis_points(numerator: usize, denominator: usize) -> Result<usize> {
    if denominator == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 55 ratio denominator must be non-zero".to_string(),
        ));
    }
    numerator
        .checked_mul(10_000)
        .map(|scaled| scaled / denominator)
        .ok_or_else(|| {
            VmError::InvalidConfig("Phase 55 ratio basis-point scaling overflow".to_string())
        })
}

#[cfg(feature = "stwo-backend")]
fn phase56_executable_transcript_order() -> Vec<String> {
    [
        "phase56_executable_sumcheck_domain_tag",
        "claim_version",
        "semantic_scope",
        "source_phase54_skeleton_claim_commitment",
        "source_phase53_benchmark_claim_commitment",
        "ordered_component_proof_commitments",
        "claimed_sums",
        "round_polynomial_coefficients",
        "derived_round_challenges",
        "terminal_evaluations",
        "surface_accounting",
        "proof_availability_flags",
        "required_next_step",
    ]
    .into_iter()
    .map(str::to_string)
    .collect()
}

#[cfg(feature = "stwo-backend")]
fn phase56_prepare_executable_component_proof(
    component: &Phase54SumcheckComponentSkeleton,
) -> Result<Phase56ExecutableSumcheckComponentProof> {
    verify_phase54_sumcheck_component_skeleton(component)?;
    let claimed_sum = phase56_derive_m31(
        &component.component_claim_commitment,
        &component.component_name,
        "claimed_sum",
        0,
    )?;
    let mut current_sum = claimed_sum;
    let mut round_polynomials = Vec::with_capacity(component.round_count);
    let mut derived_challenges = Vec::with_capacity(component.round_count);
    for round_index in 0..component.round_count {
        let round = phase56_prepare_round_polynomial(
            &component.component_claim_commitment,
            &component.component_name,
            round_index,
            component.round_polynomial_degree,
            current_sum,
        )?;
        let challenge = phase56_derive_round_challenge(
            &component.component_claim_commitment,
            &component.component_name,
            round_index,
            &round.polynomial_commitment,
        )?;
        current_sum = phase56_eval_round_polynomial(&round.coefficients, challenge)?;
        round_polynomials.push(round);
        derived_challenges.push(challenge);
    }
    let final_evaluations = vec![current_sum, 1];
    let mut proof = Phase56ExecutableSumcheckComponentProof {
        proof_backend: StarkProofBackend::Stwo,
        source_phase54_component_claim_commitment: component.component_claim_commitment.clone(),
        component_name: component.component_name.clone(),
        component_kind: component.component_kind.clone(),
        relation_field: component.relation_field.clone(),
        round_count: component.round_count,
        round_polynomial_degree: component.round_polynomial_degree,
        claimed_sum,
        round_polynomials,
        derived_challenges,
        final_evaluations,
        terminal_sum: current_sum,
        terminal_check_rule: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_TERMINAL_RULE_PHASE56.to_string(),
        transcript_protocol: STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_TRANSCRIPT_PROTOCOL_PHASE56
            .to_string(),
        executable_round_check_available: true,
        mle_opening_verifier_available: false,
        relation_witness_binding_available: false,
        cryptographic_soundness_claimed: false,
        component_proof_commitment: String::new(),
    };
    proof.component_proof_commitment = commit_phase56_executable_sumcheck_component_proof(&proof)?;
    verify_phase56_executable_sumcheck_component_proof(&proof)?;
    Ok(proof)
}

#[cfg(feature = "stwo-backend")]
fn phase56_prepare_round_polynomial(
    source_commitment: &str,
    component_name: &str,
    round_index: usize,
    degree: usize,
    current_sum: u32,
) -> Result<Phase56RoundPolynomial> {
    if degree == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 56 round polynomial degree must be non-zero".to_string(),
        ));
    }
    let mut coefficients = vec![0u32; degree + 1];
    coefficients[0] = phase56_derive_m31(source_commitment, component_name, "c0", round_index)?;
    let mut tail_sum = 0u32;
    for (degree_index, coefficient) in coefficients.iter_mut().enumerate().skip(2) {
        *coefficient = phase56_derive_m31(
            source_commitment,
            component_name,
            &format!("c{degree_index}"),
            round_index,
        )?;
        tail_sum = phase52_m31_add(tail_sum, *coefficient);
    }
    let two_c0 = phase52_m31_add(coefficients[0], coefficients[0]);
    coefficients[1] = phase52_m31_sub(phase52_m31_sub(current_sum, two_c0), tail_sum);
    let mut round = Phase56RoundPolynomial {
        round_index,
        degree,
        coefficients,
        polynomial_commitment: String::new(),
    };
    round.polynomial_commitment = commit_phase56_round_polynomial(&round)?;
    Ok(round)
}

#[cfg(feature = "stwo-backend")]
fn phase56_derive_round_challenge(
    source_commitment: &str,
    component_name: &str,
    round_index: usize,
    polynomial_commitment: &str,
) -> Result<u32> {
    phase43_require_hash32("phase56_round_source_commitment", source_commitment)?;
    phase43_require_hash32("phase56_round_polynomial_commitment", polynomial_commitment)?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 56 round challenge hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase56-round-challenge");
    phase29_update_len_prefixed(&mut hasher, source_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, component_name.as_bytes());
    phase29_update_usize(&mut hasher, round_index);
    phase29_update_len_prefixed(&mut hasher, polynomial_commitment.as_bytes());
    phase56_finalize_m31_hash(hasher, "Phase 56 round challenge")
}

#[cfg(feature = "stwo-backend")]
fn phase56_derive_m31(
    source_commitment: &str,
    component_name: &str,
    label: &str,
    round_index: usize,
) -> Result<u32> {
    phase43_require_hash32("phase56_m31_source_commitment", source_commitment)?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!("failed to initialize Phase 56 M31 hash: {err}"))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase56-derived-m31");
    phase29_update_len_prefixed(&mut hasher, source_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, component_name.as_bytes());
    phase29_update_len_prefixed(&mut hasher, label.as_bytes());
    phase29_update_usize(&mut hasher, round_index);
    phase56_finalize_m31_hash(hasher, "Phase 56 derived M31")
}

#[cfg(feature = "stwo-backend")]
fn phase56_finalize_m31_hash(hasher: Blake2bVar, label: &str) -> Result<u32> {
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .map_err(|err| VmError::InvalidConfig(format!("failed to finalize {label} hash: {err}")))?;
    let mut limb_bytes = [0u8; 8];
    limb_bytes.copy_from_slice(&out[..8]);
    Ok((u64::from_le_bytes(limb_bytes) % u64::from(PHASE44D_M31_MODULUS)) as u32)
}

#[cfg(feature = "stwo-backend")]
fn phase56_eval_round_polynomial(coefficients: &[u32], point: u32) -> Result<u32> {
    phase52_validate_m31_values("phase56_eval_coefficients", coefficients)?;
    if point >= PHASE44D_M31_MODULUS {
        return Err(VmError::InvalidConfig(
            "Phase 56 polynomial evaluation point exceeds M31 capacity".to_string(),
        ));
    }
    let mut acc = 0u32;
    for coefficient in coefficients.iter().rev() {
        acc = phase52_m31_add(phase52_m31_mul(acc, point), *coefficient);
    }
    Ok(acc)
}

#[cfg(feature = "stwo-backend")]
fn phase50_tensor_element_count(shape: &[usize]) -> Result<usize> {
    if shape.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim requires a non-empty shape".to_string(),
        ));
    }
    shape.iter().try_fold(1usize, |acc, dimension| {
        if *dimension == 0 {
            return Err(VmError::InvalidConfig(
                "Phase 50 tensor commitment claim shape dimensions must be non-zero".to_string(),
            ));
        }
        acc.checked_mul(*dimension).ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 50 tensor commitment claim shape element count overflow".to_string(),
            )
        })
    })
}

#[cfg(feature = "stwo-backend")]
fn phase50_next_power_of_two(value: usize) -> Result<usize> {
    if value == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 50 tensor commitment claim cannot pad an empty tensor".to_string(),
        ));
    }
    value.checked_next_power_of_two().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 50 tensor commitment claim padded element count overflow".to_string(),
        )
    })
}

#[cfg(feature = "stwo-backend")]
fn phase53_padded_log2(value: usize) -> Result<usize> {
    let padded = phase50_next_power_of_two(value)?;
    Ok(padded.trailing_zeros() as usize)
}

#[cfg(feature = "stwo-backend")]
fn phase53_derive_parameter_binding_commitment(
    relation_claim: &Phase51FirstLayerRelationClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 53 parameter binding commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase53-parameter-binding-placeholder");
    phase29_update_len_prefixed(
        &mut hasher,
        relation_claim.relation_claim_commitment.as_bytes(),
    );
    phase29_update_len_prefixed(
        &mut hasher,
        relation_claim.parameter_commitment_scheme.as_bytes(),
    );
    phase44d_update_usize_vec(&mut hasher, &relation_claim.gate_projection_shape);
    phase44d_update_usize_vec(&mut hasher, &relation_claim.value_projection_shape);
    phase44d_update_usize_vec(&mut hasher, &relation_claim.output_projection_shape);
    phase29_update_usize(&mut hasher, relation_claim.gate_bias_len);
    phase29_update_usize(&mut hasher, relation_claim.value_bias_len);
    phase29_update_usize(&mut hasher, relation_claim.output_bias_len);
    phase29_update_usize(&mut hasher, relation_claim.parameter_surface_unit_count);
    phase44d_finalize_hash(hasher, "Phase 53 parameter binding commitment")
}

#[cfg(feature = "stwo-backend")]
fn phase50_derive_tensor_root(
    contract: &Phase49LayerwiseTensorClaimPropagationContract,
    tensor_role: &str,
    tensor_shape: &[usize],
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 50 tensor-root derivation hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase50-derived-tensor-root");
    phase29_update_len_prefixed(&mut hasher, contract.contract_commitment.as_bytes());
    phase29_update_len_prefixed(&mut hasher, tensor_role.as_bytes());
    phase44d_update_usize_vec(&mut hasher, tensor_shape);
    phase44d_finalize_hash(hasher, "Phase 50 derived tensor root")
}

#[cfg(feature = "stwo-backend")]
fn phase52_validate_m31_values(label: &str, values: &[u32]) -> Result<()> {
    for value in values {
        if *value >= PHASE44D_M31_MODULUS {
            return Err(VmError::InvalidConfig(format!(
                "Phase 52 `{label}` value {value} exceeds M31 capacity"
            )));
        }
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase52_commit_raw_tensor_values(values: &[u32]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 52 raw tensor commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase52-raw-tensor-values");
    phase44d_update_u32_vec(&mut hasher, values);
    phase44d_finalize_hash(hasher, "Phase 52 raw tensor values")
}

#[cfg(feature = "stwo-backend")]
fn phase52_derive_mle_point(
    relation_claim_commitment: &str,
    endpoint_role: &str,
    padded_element_count: usize,
) -> Result<Vec<u32>> {
    phase43_require_hash32(
        "phase52_relation_claim_commitment",
        relation_claim_commitment,
    )?;
    if padded_element_count == 0 || !padded_element_count.is_power_of_two() {
        return Err(VmError::InvalidConfig(
            "Phase 52 MLE point derivation requires a non-zero power-of-two padded size"
                .to_string(),
        ));
    }
    let dimension = padded_element_count.trailing_zeros() as usize;
    let mut point = Vec::with_capacity(dimension);
    for index in 0..dimension {
        let mut hasher = Blake2bVar::new(32).map_err(|err| {
            VmError::InvalidConfig(format!(
                "failed to initialize Phase 52 MLE point challenge hash: {err}"
            ))
        })?;
        phase29_update_len_prefixed(&mut hasher, b"phase52-mle-point-coordinate");
        phase29_update_len_prefixed(&mut hasher, relation_claim_commitment.as_bytes());
        phase29_update_len_prefixed(&mut hasher, endpoint_role.as_bytes());
        phase29_update_usize(&mut hasher, index);
        let mut out = [0u8; 32];
        hasher.finalize_variable(&mut out).map_err(|err| {
            VmError::InvalidConfig(format!(
                "failed to finalize Phase 52 MLE point challenge hash: {err}"
            ))
        })?;
        let mut limb_bytes = [0u8; 8];
        limb_bytes.copy_from_slice(&out[..8]);
        point.push((u64::from_le_bytes(limb_bytes) % u64::from(PHASE44D_M31_MODULUS)) as u32);
    }
    Ok(point)
}

#[cfg(feature = "stwo-backend")]
fn phase52_evaluate_padded_mle(raw_values: &[u32], point: &[u32]) -> Result<u32> {
    phase52_validate_m31_values("raw_values", raw_values)?;
    phase52_validate_m31_values("mle_point", point)?;
    let padded_len = phase50_next_power_of_two(raw_values.len())?;
    if point.len() != padded_len.trailing_zeros() as usize {
        return Err(VmError::InvalidConfig(
            "Phase 52 MLE evaluation point dimension does not match padded tensor size".to_string(),
        ));
    }
    let mut layer = vec![0u32; padded_len];
    layer[..raw_values.len()].copy_from_slice(raw_values);
    for challenge in point {
        let one_minus_challenge = phase52_m31_sub(1, *challenge);
        let mut next = Vec::with_capacity(layer.len() / 2);
        for pair in layer.chunks_exact(2) {
            let left = phase52_m31_mul(pair[0], one_minus_challenge);
            let right = phase52_m31_mul(pair[1], *challenge);
            next.push(phase52_m31_add(left, right));
        }
        layer = next;
    }
    layer.first().copied().ok_or_else(|| {
        VmError::InvalidConfig("Phase 52 MLE evaluation produced an empty layer".to_string())
    })
}

#[cfg(feature = "stwo-backend")]
fn phase52_m31_add(left: u32, right: u32) -> u32 {
    ((u64::from(left) + u64::from(right)) % u64::from(PHASE44D_M31_MODULUS)) as u32
}

#[cfg(feature = "stwo-backend")]
fn phase52_m31_sub(left: u32, right: u32) -> u32 {
    ((u64::from(left) + u64::from(PHASE44D_M31_MODULUS) - u64::from(right))
        % u64::from(PHASE44D_M31_MODULUS)) as u32
}

#[cfg(feature = "stwo-backend")]
fn phase52_m31_mul(left: u32, right: u32) -> u32 {
    ((u128::from(left) * u128::from(right)) % u128::from(PHASE44D_M31_MODULUS)) as u32
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase42_boundary_preimage_evidence_json(
    json: &str,
) -> Result<Phase42BoundaryPreimageEvidence> {
    if json.len() > MAX_PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_JSON_BYTES
        )));
    }
    let evidence: Phase42BoundaryPreimageEvidence =
        serde_json::from_str(json).map_err(phase42_json_error)?;
    verify_phase42_boundary_preimage_evidence(&evidence)?;
    Ok(evidence)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase42_boundary_history_equivalence_witness_json(
    json: &str,
) -> Result<Phase42BoundaryHistoryEquivalenceWitness> {
    if json.len() > MAX_PHASE42_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 history-equivalence witness JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE42_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_JSON_BYTES
        )));
    }
    let witness: Phase42BoundaryHistoryEquivalenceWitness =
        serde_json::from_str(json).map_err(phase42_json_error)?;
    verify_phase42_boundary_history_equivalence_witness(&witness)?;
    Ok(witness)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase43_history_replay_trace_json(json: &str) -> Result<Phase43HistoryReplayTrace> {
    if json.len() > MAX_PHASE43_HISTORY_REPLAY_TRACE_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 history replay trace JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE43_HISTORY_REPLAY_TRACE_JSON_BYTES
        )));
    }
    let trace: Phase43HistoryReplayTrace =
        serde_json::from_str(json).map_err(phase43_json_error)?;
    verify_phase43_history_replay_trace(&trace)?;
    Ok(trace)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase42_boundary_preimage_evidence_json_against_sources(
    json: &str,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase42BoundaryPreimageEvidence> {
    let evidence = parse_phase42_boundary_preimage_evidence_json(json)?;
    verify_phase42_boundary_preimage_evidence_against_sources(
        &evidence, chain, phase28, contract, phase30,
    )?;
    Ok(evidence)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase42_boundary_history_equivalence_witness_json_against_sources(
    json: &str,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase42BoundaryHistoryEquivalenceWitness> {
    let witness = parse_phase42_boundary_history_equivalence_witness_json(json)?;
    verify_phase42_boundary_history_equivalence_witness_against_sources(
        &witness, chain, phase28, contract, phase30,
    )?;
    Ok(witness)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase43_history_replay_trace_json_against_sources(
    json: &str,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase43HistoryReplayTrace> {
    let trace = parse_phase43_history_replay_trace_json(json)?;
    verify_phase43_history_replay_trace_against_sources(&trace, chain, phase28, contract, phase30)?;
    Ok(trace)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase42_boundary_preimage_evidence(
    path: &Path,
) -> Result<Phase42BoundaryPreimageEvidence> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_JSON_BYTES,
        "Phase 42 boundary preimage evidence",
    )?;
    let evidence: Phase42BoundaryPreimageEvidence =
        serde_json::from_slice(&bytes).map_err(phase42_json_error)?;
    verify_phase42_boundary_preimage_evidence(&evidence)?;
    Ok(evidence)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase42_boundary_history_equivalence_witness(
    path: &Path,
) -> Result<Phase42BoundaryHistoryEquivalenceWitness> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE42_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_JSON_BYTES,
        "Phase 42 history-equivalence witness",
    )?;
    let witness: Phase42BoundaryHistoryEquivalenceWitness =
        serde_json::from_slice(&bytes).map_err(phase42_json_error)?;
    verify_phase42_boundary_history_equivalence_witness(&witness)?;
    Ok(witness)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase43_history_replay_trace(path: &Path) -> Result<Phase43HistoryReplayTrace> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE43_HISTORY_REPLAY_TRACE_JSON_BYTES,
        "Phase 43 history replay trace",
    )?;
    let trace: Phase43HistoryReplayTrace =
        serde_json::from_slice(&bytes).map_err(phase43_json_error)?;
    verify_phase43_history_replay_trace(&trace)?;
    Ok(trace)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase42_boundary_preimage_evidence_against_sources(
    path: &Path,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase42BoundaryPreimageEvidence> {
    let evidence = load_phase42_boundary_preimage_evidence(path)?;
    verify_phase42_boundary_preimage_evidence_against_sources(
        &evidence, chain, phase28, contract, phase30,
    )?;
    Ok(evidence)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase42_boundary_history_equivalence_witness_against_sources(
    path: &Path,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase42BoundaryHistoryEquivalenceWitness> {
    let witness = load_phase42_boundary_history_equivalence_witness(path)?;
    verify_phase42_boundary_history_equivalence_witness_against_sources(
        &witness, chain, phase28, contract, phase30,
    )?;
    Ok(witness)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase43_history_replay_trace_against_sources(
    path: &Path,
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase43HistoryReplayTrace> {
    let trace = load_phase43_history_replay_trace(path)?;
    verify_phase43_history_replay_trace_against_sources(&trace, chain, phase28, contract, phase30)?;
    Ok(trace)
}

#[cfg(feature = "stwo-backend")]
fn phase42_json_error(error: serde_json::Error) -> VmError {
    if error.is_data() || error.is_syntax() {
        VmError::InvalidConfig(format!(
            "invalid Phase 42 boundary preimage evidence JSON: {error}"
        ))
    } else {
        VmError::Serialization(error.to_string())
    }
}

#[cfg(feature = "stwo-backend")]
fn phase43_json_error(error: serde_json::Error) -> VmError {
    if error.is_data() || error.is_syntax() {
        VmError::InvalidConfig(format!(
            "invalid Phase 43 history replay trace JSON: {error}"
        ))
    } else {
        VmError::Serialization(error.to_string())
    }
}

#[cfg(feature = "stwo-backend")]
fn phase42_verify_source_stack(
    chain: &Phase12DecodingChainManifest,
    phase28: &Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    verify_phase12_decoding_chain(chain)?;
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation(phase28)?;
    verify_phase29_recursive_compression_input_contract(contract)?;
    verify_phase30_decoding_step_proof_envelope_manifest_against_chain(phase30, chain)?;
    let expected_contract =
        phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28(phase28)?;
    if contract != &expected_contract {
        return Err(VmError::InvalidConfig(
            "Phase 42 boundary preimage evidence requires the Phase 29 contract to be derived from the supplied Phase 28 aggregate"
                .to_string(),
        ));
    }
    if phase28.proof_backend_version != phase30.proof_backend_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence requires matching Phase28/Phase30 proof backend versions (`{}` != `{}`)",
            phase28.proof_backend_version, phase30.proof_backend_version
        )));
    }
    if phase28.statement_version != phase30.statement_version {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence requires matching Phase28/Phase30 statement versions (`{}` != `{}`)",
            phase28.statement_version, phase30.statement_version
        )));
    }
    if phase28.total_steps != phase30.total_steps || chain.total_steps != phase30.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence requires matching total_steps across Phase12 ({}) Phase28 ({}) and Phase30 ({})",
            chain.total_steps, phase28.total_steps, phase30.total_steps
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_commit_source_appended_pairs(
    chain: &Phase12DecodingChainManifest,
) -> Result<(String, usize)> {
    let latest_cached_pair_range = chain.layout.latest_cached_pair_range()?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 42 appended-pairs commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase42-source-appended-pairs");
    phase29_update_len_prefixed(
        &mut hasher,
        chain
            .steps
            .first()
            .map(|step| step.from_state.layout_commitment.as_bytes())
            .unwrap_or_default(),
    );
    phase29_update_usize(&mut hasher, chain.layout.pair_width);
    phase29_update_usize(&mut hasher, chain.steps.len());
    for (step_index, step) in chain.steps.iter().enumerate() {
        let pair = &step.proof.claim.final_state.memory[latest_cached_pair_range.clone()];
        if pair.len() != chain.layout.pair_width {
            return Err(VmError::InvalidConfig(format!(
                "Phase 42 source appended pair {step_index} has {} values, expected pair_width={}",
                pair.len(),
                chain.layout.pair_width
            )));
        }
        phase29_update_usize(&mut hasher, step_index);
        for value in pair {
            hasher.update(&value.to_le_bytes());
        }
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 42 appended-pairs commitment hash: {err}"
        ))
    })?;
    Ok((phase29_lower_hex(&out), chain.steps.len()))
}

#[cfg(feature = "stwo-backend")]
fn phase42_commit_source_lookup_rows_commitments(
    chain: &Phase12DecodingChainManifest,
) -> Result<(String, usize)> {
    let first_step = chain.steps.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 42 source lookup-row commitment requires a non-empty chain".to_string(),
        )
    })?;
    let mut commitments = Vec::with_capacity(chain.steps.len() + 1);
    commitments.push(first_step.from_state.lookup_rows_commitment.as_str());
    for step in &chain.steps {
        commitments.push(step.to_state.lookup_rows_commitment.as_str());
    }

    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 42 lookup-row replay commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase42-source-lookup-rows");
    phase29_update_len_prefixed(
        &mut hasher,
        first_step.from_state.layout_commitment.as_bytes(),
    );
    phase29_update_usize(&mut hasher, commitments.len());
    for (index, commitment) in commitments.iter().enumerate() {
        phase42_require_hash32(
            &format!("history_equivalence.lookup_rows[{index}]"),
            commitment,
        )?;
        phase29_update_usize(&mut hasher, index);
        phase29_update_len_prefixed(&mut hasher, commitment.as_bytes());
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 42 lookup-row replay commitment hash: {err}"
        ))
    })?;
    Ok((phase29_lower_hex(&out), commitments.len()))
}

#[cfg(feature = "stwo-backend")]
fn phase42_verify_phase12_state(label: &str, state: &Phase12DecodingState) -> Result<()> {
    if state.state_version != STWO_DECODING_STATE_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 `{label}` state version `{}` does not match expected `{}`",
            state.state_version, STWO_DECODING_STATE_VERSION_PHASE12
        )));
    }
    phase42_require_phase12_state_hashes(label, state)?;
    let expected = commit_phase12_public_state(state);
    if state.public_state_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 `{label}` public_state_commitment does not match recomputed `{expected}`"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_verify_phase14_state(label: &str, state: &Phase14DecodingState) -> Result<()> {
    if state.state_version != STWO_DECODING_STATE_VERSION_PHASE14 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 `{label}` state version `{}` does not match expected `{}`",
            state.state_version, STWO_DECODING_STATE_VERSION_PHASE14
        )));
    }
    phase42_require_phase14_state_hashes(label, state)?;
    let expected = commit_phase14_public_state(state);
    if state.public_state_commitment != expected {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 `{label}` public_state_commitment does not match recomputed `{expected}`"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_require_hash32(label: &str, value: &str) -> Result<()> {
    if !phase37_is_hash32_lower_hex(value) {
        return Err(VmError::InvalidConfig(format!(
            "Phase 42 boundary preimage evidence `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_require_phase12_state_hashes(label: &str, state: &Phase12DecodingState) -> Result<()> {
    for (field, value) in [
        ("layout_commitment", state.layout_commitment.as_str()),
        (
            "persistent_state_commitment",
            state.persistent_state_commitment.as_str(),
        ),
        (
            "kv_history_commitment",
            state.kv_history_commitment.as_str(),
        ),
        ("kv_cache_commitment", state.kv_cache_commitment.as_str()),
        (
            "incoming_token_commitment",
            state.incoming_token_commitment.as_str(),
        ),
        ("query_commitment", state.query_commitment.as_str()),
        ("output_commitment", state.output_commitment.as_str()),
        (
            "lookup_rows_commitment",
            state.lookup_rows_commitment.as_str(),
        ),
        (
            "public_state_commitment",
            state.public_state_commitment.as_str(),
        ),
    ] {
        phase42_require_hash32(&format!("{label}.{field}"), value)?;
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_require_phase14_state_hashes(label: &str, state: &Phase14DecodingState) -> Result<()> {
    for (field, value) in [
        ("layout_commitment", state.layout_commitment.as_str()),
        (
            "persistent_state_commitment",
            state.persistent_state_commitment.as_str(),
        ),
        (
            "kv_history_commitment",
            state.kv_history_commitment.as_str(),
        ),
        (
            "kv_history_sealed_commitment",
            state.kv_history_sealed_commitment.as_str(),
        ),
        (
            "kv_history_open_chunk_commitment",
            state.kv_history_open_chunk_commitment.as_str(),
        ),
        (
            "kv_history_frontier_commitment",
            state.kv_history_frontier_commitment.as_str(),
        ),
        (
            "lookup_transcript_commitment",
            state.lookup_transcript_commitment.as_str(),
        ),
        (
            "lookup_frontier_commitment",
            state.lookup_frontier_commitment.as_str(),
        ),
        ("kv_cache_commitment", state.kv_cache_commitment.as_str()),
        (
            "incoming_token_commitment",
            state.incoming_token_commitment.as_str(),
        ),
        ("query_commitment", state.query_commitment.as_str()),
        ("output_commitment", state.output_commitment.as_str()),
        (
            "lookup_rows_commitment",
            state.lookup_rows_commitment.as_str(),
        ),
        (
            "public_state_commitment",
            state.public_state_commitment.as_str(),
        ),
    ] {
        phase42_require_hash32(&format!("{label}.{field}"), value)?;
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_shared_core_matches_with_history_bridge(
    label: &str,
    phase12: &Phase12DecodingState,
    phase14: &Phase14DecodingState,
) -> Result<()> {
    if phase12.step_index != phase14.step_index {
        return phase42_shared_core_mismatch(label, "step_index");
    }
    if phase12.position != phase14.position {
        return phase42_shared_core_mismatch(label, "position");
    }
    if phase12.layout_commitment != phase14.layout_commitment {
        return phase42_shared_core_mismatch(label, "layout_commitment");
    }
    if phase12.persistent_state_commitment != phase14.persistent_state_commitment {
        return phase42_shared_core_mismatch(label, "persistent_state_commitment");
    }
    if phase12.kv_history_length != phase14.kv_history_length {
        return phase42_shared_core_mismatch(label, "kv_history_length");
    }
    if phase12.kv_cache_commitment != phase14.kv_cache_commitment {
        return phase42_shared_core_mismatch(label, "kv_cache_commitment");
    }
    if phase12.incoming_token_commitment != phase14.incoming_token_commitment {
        return phase42_shared_core_mismatch(label, "incoming_token_commitment");
    }
    if phase12.query_commitment != phase14.query_commitment {
        return phase42_shared_core_mismatch(label, "query_commitment");
    }
    if phase12.output_commitment != phase14.output_commitment {
        return phase42_shared_core_mismatch(label, "output_commitment");
    }
    if phase12.lookup_rows_commitment != phase14.lookup_rows_commitment {
        return phase42_shared_core_mismatch(label, "lookup_rows_commitment");
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_shared_core_matches(
    label: &str,
    phase12: &Phase12DecodingState,
    phase14: &Phase14DecodingState,
) -> Result<()> {
    if phase12.step_index != phase14.step_index {
        return phase42_shared_core_mismatch(label, "step_index");
    }
    if phase12.position != phase14.position {
        return phase42_shared_core_mismatch(label, "position");
    }
    if phase12.layout_commitment != phase14.layout_commitment {
        return phase42_shared_core_mismatch(label, "layout_commitment");
    }
    if phase12.persistent_state_commitment != phase14.persistent_state_commitment {
        return phase42_shared_core_mismatch(label, "persistent_state_commitment");
    }
    if phase12.kv_history_commitment != phase14.kv_history_commitment {
        return phase42_shared_core_mismatch(label, "kv_history_commitment");
    }
    if phase12.kv_history_length != phase14.kv_history_length {
        return phase42_shared_core_mismatch(label, "kv_history_length");
    }
    if phase12.kv_cache_commitment != phase14.kv_cache_commitment {
        return phase42_shared_core_mismatch(label, "kv_cache_commitment");
    }
    if phase12.incoming_token_commitment != phase14.incoming_token_commitment {
        return phase42_shared_core_mismatch(label, "incoming_token_commitment");
    }
    if phase12.query_commitment != phase14.query_commitment {
        return phase42_shared_core_mismatch(label, "query_commitment");
    }
    if phase12.output_commitment != phase14.output_commitment {
        return phase42_shared_core_mismatch(label, "output_commitment");
    }
    if phase12.lookup_rows_commitment != phase14.lookup_rows_commitment {
        return phase42_shared_core_mismatch(label, "lookup_rows_commitment");
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase42_shared_core_mismatch(label: &str, field: &str) -> Result<()> {
    Err(VmError::InvalidConfig(format!(
        "Phase 42 boundary preimage evidence {label} states differ in shared carried-state field `{field}`"
    )))
}

#[cfg(feature = "stwo-backend")]
fn commit_phase38_lookup_identity(
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<String> {
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;
    let mut static_registries = phase30
        .envelopes
        .iter()
        .map(|envelope| envelope.static_lookup_registry_commitment.as_str())
        .collect::<Vec<_>>();
    static_registries.sort_unstable();
    static_registries.dedup();

    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 38 lookup identity commitment hash: {err}"
        ))
    })?;
    phase29_update_len_prefixed(&mut hasher, b"phase38-paper3-lookup-identity");
    phase29_update_len_prefixed(&mut hasher, phase30.proof_backend_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, phase30.statement_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, phase30.source_chain_version.as_bytes());
    phase29_update_len_prefixed(&mut hasher, phase30.source_chain_semantic_scope.as_bytes());
    let layout_json = serde_json::to_vec(&phase30.layout)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    phase29_update_len_prefixed(&mut hasher, &layout_json);
    phase29_update_usize(&mut hasher, static_registries.len());
    for registry in static_registries {
        phase29_update_len_prefixed(&mut hasher, registry.as_bytes());
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize Phase 38 lookup identity commitment hash: {err}"
        ))
    })?;
    Ok(phase29_lower_hex(&out))
}

#[cfg(feature = "stwo-backend")]
fn phase38_segment_from_phase37_source(
    segment_index: usize,
    step_start: usize,
    source: &Phase38Paper3CompositionSource,
) -> Result<Phase38Paper3CompositionSegment> {
    verify_phase37_recursive_artifact_chain_harness_receipt_against_sources(
        &source.phase37_receipt,
        &source.phase29_contract,
        &source.phase30_manifest,
    )?;
    let receipt = &source.phase37_receipt;
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
        phase29_contract: source.phase29_contract.clone(),
        phase30_manifest: source.phase30_manifest.clone(),
        phase37_receipt: receipt.clone(),
        phase37_receipt_commitment: receipt
            .recursive_artifact_chain_harness_receipt_commitment
            .clone(),
        lookup_identity_commitment: commit_phase38_lookup_identity(&source.phase30_manifest)?,
        phase30_source_chain_commitment: receipt.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: receipt.phase30_step_envelopes_commitment.clone(),
        chain_start_boundary_commitment: receipt.chain_start_boundary_commitment.clone(),
        chain_end_boundary_commitment: receipt.chain_end_boundary_commitment.clone(),
        source_template_commitment: receipt.source_template_commitment.clone(),
        aggregation_template_commitment: receipt.aggregation_template_commitment.clone(),
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
    left.lookup_identity_commitment == right.lookup_identity_commitment
}

#[cfg(feature = "stwo-backend")]
fn phase38_execution_template_matches(
    left: &Phase38Paper3CompositionSegment,
    right: &Phase38Paper3CompositionSegment,
) -> bool {
    left.source_template_commitment == right.source_template_commitment
        && left.aggregation_template_commitment == right.aggregation_template_commitment
}

#[cfg(feature = "stwo-backend")]
fn phase38_source_chain_matches(
    left: &Phase38Paper3CompositionSegment,
    right: &Phase38Paper3CompositionSegment,
) -> bool {
    left.phase30_source_chain_commitment == right.phase30_source_chain_commitment
}

#[cfg(feature = "stwo-backend")]
fn phase38_require_segment_receipt_field(
    segment: &Phase38Paper3CompositionSegment,
    label: &str,
    segment_value: &str,
    receipt_value: &str,
) -> Result<()> {
    if segment_value != receipt_value {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype segment {} `{label}` `{segment_value}` does not match embedded Phase 37 receipt `{receipt_value}`",
            segment.segment_index
        )));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn phase38_verify_segment_receipt_binding(segment: &Phase38Paper3CompositionSegment) -> Result<()> {
    verify_phase37_recursive_artifact_chain_harness_receipt_against_sources(
        &segment.phase37_receipt,
        &segment.phase29_contract,
        &segment.phase30_manifest,
    )?;
    let expected_receipt_commitment =
        commit_phase37_recursive_artifact_chain_harness_receipt(&segment.phase37_receipt)?;
    if segment.phase37_receipt_commitment != expected_receipt_commitment {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype segment {} Phase 37 receipt commitment `{}` does not match recomputed `{}`",
            segment.segment_index,
            segment.phase37_receipt_commitment,
            expected_receipt_commitment
        )));
    }
    let expected_lookup_identity = commit_phase38_lookup_identity(&segment.phase30_manifest)?;
    if segment.lookup_identity_commitment != expected_lookup_identity {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype segment {} lookup identity commitment `{}` does not match recomputed `{}`",
            segment.segment_index,
            segment.lookup_identity_commitment,
            expected_lookup_identity
        )));
    }
    if segment.total_steps != segment.phase37_receipt.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype segment {} total steps `{}` do not match embedded Phase 37 receipt `{}`",
            segment.segment_index, segment.total_steps, segment.phase37_receipt.total_steps
        )));
    }
    phase38_require_segment_receipt_field(
        segment,
        "phase30_source_chain_commitment",
        &segment.phase30_source_chain_commitment,
        &segment.phase37_receipt.phase30_source_chain_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "phase30_step_envelopes_commitment",
        &segment.phase30_step_envelopes_commitment,
        &segment.phase37_receipt.phase30_step_envelopes_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "chain_start_boundary_commitment",
        &segment.chain_start_boundary_commitment,
        &segment.phase37_receipt.chain_start_boundary_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "chain_end_boundary_commitment",
        &segment.chain_end_boundary_commitment,
        &segment.phase37_receipt.chain_end_boundary_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "source_template_commitment",
        &segment.source_template_commitment,
        &segment.phase37_receipt.source_template_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "aggregation_template_commitment",
        &segment.aggregation_template_commitment,
        &segment.phase37_receipt.aggregation_template_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "phase34_shared_lookup_public_inputs_commitment",
        &segment.phase34_shared_lookup_public_inputs_commitment,
        &segment
            .phase37_receipt
            .phase34_shared_lookup_public_inputs_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "input_lookup_rows_commitments_commitment",
        &segment.input_lookup_rows_commitments_commitment,
        &segment
            .phase37_receipt
            .input_lookup_rows_commitments_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "output_lookup_rows_commitments_commitment",
        &segment.output_lookup_rows_commitments_commitment,
        &segment
            .phase37_receipt
            .output_lookup_rows_commitments_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "shared_lookup_artifact_commitments_commitment",
        &segment.shared_lookup_artifact_commitments_commitment,
        &segment
            .phase37_receipt
            .shared_lookup_artifact_commitments_commitment,
    )?;
    phase38_require_segment_receipt_field(
        segment,
        "static_lookup_registry_commitments_commitment",
        &segment.static_lookup_registry_commitments_commitment,
        &segment
            .phase37_receipt
            .static_lookup_registry_commitments_commitment,
    )?;
    Ok(())
}

#[cfg(feature = "stwo-backend")]
pub fn phase38_prepare_paper3_composition_prototype(
    sources: &[Phase38Paper3CompositionSource],
) -> Result<Phase38Paper3CompositionPrototype> {
    let first_source = sources.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype requires at least two Phase 37 source records"
                .to_string(),
        )
    })?;
    if sources.len() < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 38 Paper 3 composition prototype requires at least two Phase 37 source records"
                .to_string(),
        ));
    }

    let first = &first_source.phase37_receipt;
    let mut segments: Vec<Phase38Paper3CompositionSegment> = Vec::with_capacity(sources.len());
    let mut cursor = 0usize;
    for (index, source) in sources.iter().enumerate() {
        let segment = phase38_segment_from_phase37_source(index, cursor, source)?;
        let receipt = &segment.phase37_receipt;
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
            if !phase38_source_chain_matches(previous, &segment) {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype source-chain identity drift at segment {}",
                    segment.segment_index
                )));
            }
            if !phase38_execution_template_matches(previous, &segment) {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 38 Paper 3 composition prototype execution template drift at segment {}",
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
        phase38_verify_segment_receipt_binding(segment)?;
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
        if index > 0 && !phase38_source_chain_matches(&prototype.segments[0], segment) {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype source-chain identity drift at segment {index}"
            )));
        }
        if index > 0 && !phase38_execution_template_matches(&prototype.segments[0], segment) {
            return Err(VmError::InvalidConfig(format!(
                "Phase 38 Paper 3 composition prototype execution template drift at segment {index}"
            )));
        }
        for (label, value) in [
            (
                "phase37_receipt_commitment",
                segment.phase37_receipt_commitment.as_str(),
            ),
            (
                "lookup_identity_commitment",
                segment.lookup_identity_commitment.as_str(),
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
                "source_template_commitment",
                segment.source_template_commitment.as_str(),
            ),
            (
                "aggregation_template_commitment",
                segment.aggregation_template_commitment.as_str(),
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
pub fn parse_phase38_paper3_composition_prototype_json(
    json: &str,
) -> Result<Phase38Paper3CompositionPrototype> {
    if json.len() > MAX_PHASE38_PAPER3_COMPOSITION_PROTOTYPE_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 38 Paper 3 composition prototype JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE38_PAPER3_COMPOSITION_PROTOTYPE_JSON_BYTES
        )));
    }
    serde_json::from_str(json).map_err(phase38_json_error)
}

#[cfg(feature = "stwo-backend")]
/// Parses an untrusted Phase 41 witness artifact and verifies its internal
/// commitments only.
///
/// Source provenance is intentionally checked by
/// [`verify_phase41_boundary_translation_witness_against_sources`], because a
/// standalone JSON witness does not carry the full Phase 29 and Phase 30 source
/// artifacts needed to reject stale or swapped source bindings.
pub fn parse_phase41_boundary_translation_witness_json(
    json: &str,
) -> Result<Phase41BoundaryTranslationWitnessArtifact> {
    if json.len() > MAX_PHASE41_BOUNDARY_TRANSLATION_WITNESS_JSON_BYTES {
        return Err(VmError::InvalidConfig(format!(
            "Phase 41 boundary-translation witness JSON is {} bytes, exceeding the limit of {} bytes",
            json.len(),
            MAX_PHASE41_BOUNDARY_TRANSLATION_WITNESS_JSON_BYTES
        )));
    }
    let artifact: Phase41BoundaryTranslationWitnessArtifact =
        serde_json::from_str(json).map_err(phase41_json_error)?;
    phase41_witness_from_artifact(artifact.clone())?;
    Ok(artifact)
}

#[cfg(feature = "stwo-backend")]
pub fn parse_phase41_boundary_translation_witness_json_against_sources(
    json: &str,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase41BoundaryTranslationWitness> {
    let artifact = parse_phase41_boundary_translation_witness_json(json)?;
    let witness = phase41_witness_from_artifact(artifact)?;
    verify_phase41_boundary_translation_witness_against_sources(&witness, contract, phase30)?;
    Ok(witness)
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
pub fn load_phase38_paper3_composition_prototype(
    path: &Path,
) -> Result<Phase38Paper3CompositionPrototype> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE38_PAPER3_COMPOSITION_PROTOTYPE_JSON_BYTES,
        "Phase 38 Paper 3 composition prototype",
    )?;
    serde_json::from_slice(&bytes).map_err(phase38_json_error)
}

#[cfg(feature = "stwo-backend")]
/// Loads an untrusted Phase 41 witness artifact and verifies its internal
/// commitments only.
///
/// Call [`verify_phase41_boundary_translation_witness_against_sources`] before
/// trusting the witness as bound to specific Phase 29 and Phase 30 source
/// artifacts.
pub fn load_phase41_boundary_translation_witness(
    path: &Path,
) -> Result<Phase41BoundaryTranslationWitnessArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE41_BOUNDARY_TRANSLATION_WITNESS_JSON_BYTES,
        "Phase 41 boundary-translation witness",
    )?;
    let artifact: Phase41BoundaryTranslationWitnessArtifact =
        serde_json::from_slice(&bytes).map_err(phase41_json_error)?;
    phase41_witness_from_artifact(artifact.clone())?;
    Ok(artifact)
}

#[cfg(feature = "stwo-backend")]
pub fn load_phase41_boundary_translation_witness_against_sources(
    path: &Path,
    contract: &Phase29RecursiveCompressionInputContract,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase41BoundaryTranslationWitness> {
    let artifact = load_phase41_boundary_translation_witness(path)?;
    let witness = phase41_witness_from_artifact(artifact)?;
    verify_phase41_boundary_translation_witness_against_sources(&witness, contract, phase30)?;
    Ok(witness)
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
fn phase38_json_error(error: serde_json::Error) -> VmError {
    match error.classify() {
        serde_json::error::Category::Data
        | serde_json::error::Category::Syntax
        | serde_json::error::Category::Eof => VmError::InvalidConfig(error.to_string()),
        serde_json::error::Category::Io => VmError::Serialization(error.to_string()),
    }
}

#[cfg(feature = "stwo-backend")]
fn phase41_json_error(error: serde_json::Error) -> VmError {
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
    phase29_update_len_prefixed(&mut hasher, segment.lookup_identity_commitment.as_bytes());
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
        phase29_update_len_prefixed(&mut hasher, segment.lookup_identity_commitment.as_bytes());
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
        phase29_update_len_prefixed(&mut hasher, segment.source_template_commitment.as_bytes());
        phase29_update_len_prefixed(
            &mut hasher,
            segment.aggregation_template_commitment.as_bytes(),
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
    use crate::stwo_backend::decoding::{
        commit_phase30_step_envelope, commit_phase30_step_envelope_list,
    };
    #[cfg(feature = "stwo-backend")]
    use crate::stwo_backend::{
        phase12_default_decoding_layout, phase30_prepare_decoding_step_proof_envelope_manifest,
        phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range,
        prove_phase12_decoding_demo_for_layout, prove_phase12_decoding_demo_for_layout_steps,
        prove_phase28_phase30_shared_proof_boundary_demo,
        prove_phase42_boundary_preimage_shared_proof_demo,
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain_range,
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
            global_start_state_commitment: "d".repeat(64),
            global_end_state_commitment: "e".repeat(64),
            aggregation_template_commitment: "b".repeat(64),
            aggregated_chained_folded_interval_accumulator_commitment: "f".repeat(64),
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
    fn sample_phase38_segment_source(
        start: &str,
        end: &str,
        total_steps: usize,
        source_chain: &str,
    ) -> Phase38Paper3CompositionSource {
        let mut phase30 = sample_phase30_manifest();
        let template = phase30.envelopes[0].clone();
        phase30.source_chain_commitment = source_chain.to_string();
        phase30.total_steps = total_steps;
        phase30.envelopes = (0..total_steps)
            .map(|step_index| {
                let mut envelope = template.clone();
                envelope.source_chain_commitment = source_chain.to_string();
                envelope.step_index = step_index;
                envelope.input_boundary_commitment = if step_index == 0 {
                    start.to_string()
                } else {
                    format!("{}{:063x}", &phase38_test_hash32('9')[..1], step_index)
                };
                envelope.output_boundary_commitment = if step_index + 1 == total_steps {
                    end.to_string()
                } else {
                    format!("{}{:063x}", &phase38_test_hash32('9')[..1], step_index + 1)
                };
                envelope.envelope_commitment = commit_phase30_step_envelope(&envelope);
                envelope
            })
            .collect();
        phase30.chain_start_boundary_commitment = start.to_string();
        phase30.chain_end_boundary_commitment = end.to_string();
        phase30.step_envelopes_commitment = commit_phase30_step_envelope_list(&phase30.envelopes);
        verify_phase30_decoding_step_proof_envelope_manifest(&phase30)
            .expect("verify source-backed Phase 30 segment manifest");
        let phase29_contract = sample_phase29_contract_for_phase30(&phase30);
        let phase37_receipt =
            phase37_prepare_recursive_artifact_chain_harness_receipt(&phase29_contract, &phase30)
                .expect("prepare source-backed Phase 37 segment receipt");
        Phase38Paper3CompositionSource {
            phase29_contract,
            phase30_manifest: phase30,
            phase37_receipt,
        }
    }

    #[cfg(feature = "stwo-backend")]
    fn sample_phase38_segment_sources() -> Vec<Phase38Paper3CompositionSource> {
        let start = phase38_test_hash32('a');
        let mid = phase38_test_hash32('b');
        let end = phase38_test_hash32('c');
        let source_chain = phase38_test_hash32('1');
        vec![
            sample_phase38_segment_source(&start, &mid, 2, &source_chain),
            sample_phase38_segment_source(&mid, &end, 3, &source_chain),
        ]
    }

    #[cfg(feature = "stwo-backend")]
    fn phase38_source_from_generated_phase30_segment_harness(
        phase30: Phase30DecodingStepProofEnvelopeManifest,
    ) -> Phase38Paper3CompositionSource {
        // Phase 39 makes the Phase 12/30 decode surface generated. The Phase 29
        // contract remains the existing pre-recursive harness boundary.
        let phase29_contract = sample_phase29_contract_for_phase30(&phase30);
        let phase37_receipt =
            phase37_prepare_recursive_artifact_chain_harness_receipt(&phase29_contract, &phase30)
                .expect("prepare Phase 37 receipt for generated Phase 30 segment");
        Phase38Paper3CompositionSource {
            phase29_contract,
            phase30_manifest: phase30,
            phase37_receipt,
        }
    }

    #[cfg(feature = "stwo-backend")]
    fn write_phase39_composition_artifact_if_requested(
        prototype: &Phase38Paper3CompositionPrototype,
    ) {
        let Ok(path) = std::env::var("PHASE39_COMPOSITION_ARTIFACT_OUT") else {
            return;
        };
        let path = std::path::PathBuf::from(path);
        if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
            std::fs::create_dir_all(parent).expect("create Phase 39 artifact directory");
        }
        let json =
            serde_json::to_vec_pretty(prototype).expect("serialize Phase 39 prototype artifact");
        std::fs::write(&path, json).expect("write Phase 39 prototype artifact");
    }

    #[cfg(feature = "stwo-backend")]
    fn write_phase40_boundary_probe_if_requested(
        phase29: &Phase29RecursiveCompressionInputContract,
        phase30: &Phase30DecodingStepProofEnvelopeManifest,
        phase31_error: &str,
        phase37_error: &str,
        source_kind: &str,
    ) -> Result<()> {
        let path = match std::env::var("PHASE40_BOUNDARY_PROBE_OUT") {
            Ok(path) => path,
            Err(std::env::VarError::NotPresent) => return Ok(()),
            Err(std::env::VarError::NotUnicode(_)) => {
                return Err(VmError::InvalidConfig(
                    "PHASE40_BOUNDARY_PROBE_OUT must be valid UTF-8".to_string(),
                ));
            }
        };
        if path.is_empty() {
            return Err(VmError::InvalidConfig(
                "PHASE40_BOUNDARY_PROBE_OUT must not be empty".to_string(),
            ));
        }
        let path = std::path::PathBuf::from(path);
        if path.is_absolute()
            || path.components().any(|component| {
                matches!(
                    component,
                    std::path::Component::ParentDir
                        | std::path::Component::RootDir
                        | std::path::Component::Prefix(_)
                )
            })
        {
            return Err(VmError::InvalidConfig(
                "PHASE40_BOUNDARY_PROBE_OUT must be a repo-relative path without traversal"
                    .to_string(),
            ));
        }
        if path.file_name().and_then(|name| name.to_str()) != Some("evidence.json") {
            return Err(VmError::InvalidConfig(
                "PHASE40_BOUNDARY_PROBE_OUT must target an evidence.json file".to_string(),
            ));
        }
        if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
            std::fs::create_dir_all(parent)?;
        }
        let evidence = serde_json::json!({
            "issue": 176,
            "probe": "phase40-phase28-domain-phase30-boundary",
            "total_steps": phase30.total_steps,
            "source_kind": source_kind,
            "full_shared_proof_probe": "available via prove_phase28_phase30_shared_proof_boundary_demo; not run by the default local gate because 16-proof generation is expensive",
            "phase29_contract_commitment": phase29.input_contract_commitment.as_str(),
            "phase30_source_chain_commitment": phase30.source_chain_commitment.as_str(),
            "phase30_step_envelopes_commitment": phase30.step_envelopes_commitment.as_str(),
            "phase29_boundary_domain": "Phase28-derived Phase14/Phase23 boundary-state commitment",
            "phase30_boundary_domain": "Phase30 Phase12 public-state commitment",
            "direct_phase31_boundary_equality": {
                "start": phase29.global_start_state_commitment == phase30.chain_start_boundary_commitment,
                "end": phase29.global_end_state_commitment == phase30.chain_end_boundary_commitment,
            },
            "phase29_global_start_state_commitment": phase29.global_start_state_commitment.as_str(),
            "phase30_chain_start_boundary_commitment": phase30.chain_start_boundary_commitment.as_str(),
            "phase29_global_end_state_commitment": phase29.global_end_state_commitment.as_str(),
            "phase30_chain_end_boundary_commitment": phase30.chain_end_boundary_commitment.as_str(),
            "phase31_error_kind": "InvalidConfig",
            "phase31_boundary_blocker": "global_start_state_commitment",
            "phase31_error": phase31_error,
            "phase37_error_kind": "InvalidConfig",
            "phase37_boundary_blocker": "global_start_state_commitment",
            "phase37_error": phase37_error,
        });
        let json = serde_json::to_vec_pretty(&evidence).expect("serialize Phase 40 evidence");
        std::fs::write(&path, json)?;
        Ok(())
    }

    #[cfg(feature = "stwo-backend")]
    fn assert_phase40_start_boundary_mismatch(error: &VmError) {
        match error {
            VmError::InvalidConfig(message) => {
                assert_eq!(message, PHASE31_START_BOUNDARY_MISMATCH_ERROR);
            }
            other => panic!("unexpected Phase40 boundary mismatch error: {other}"),
        }
    }

    #[cfg(feature = "stwo-backend")]
    fn phase40_start_boundary_mismatch_display() -> String {
        VmError::InvalidConfig(PHASE31_START_BOUNDARY_MISMATCH_ERROR.to_string()).to_string()
    }

    #[cfg(feature = "stwo-backend")]
    fn refresh_phase38_source_receipt(source: &mut Phase38Paper3CompositionSource) {
        source.phase37_receipt = phase37_prepare_recursive_artifact_chain_harness_receipt(
            &source.phase29_contract,
            &source.phase30_manifest,
        )
        .expect("refresh source-backed Phase 37 receipt");
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
    fn sample_phase41_boundary_gap_sources() -> (
        Phase29RecursiveCompressionInputContract,
        Phase30DecodingStepProofEnvelopeManifest,
    ) {
        let phase30 = sample_phase30_manifest();
        let mut phase29 = sample_phase29_contract();
        phase29.phase28_proof_backend_version = phase30.proof_backend_version.clone();
        phase29.statement_version = phase30.statement_version.clone();
        phase29.total_steps = phase30.total_steps;
        phase29.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&phase29)
                .expect("recommit Phase41 boundary-gap Phase29 contract");
        assert_ne!(
            phase29.global_start_state_commitment,
            phase30.chain_start_boundary_commitment
        );
        assert_ne!(
            phase29.global_end_state_commitment,
            phase30.chain_end_boundary_commitment
        );
        (phase29, phase30)
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
        let sources = sample_phase38_segment_sources();
        let prototype = phase38_prepare_paper3_composition_prototype(&sources)
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
    fn phase39_real_decode_composition_artifact_accepts_generated_five_step_chain() {
        let layout =
            crate::stwo_backend::Phase12DecodingLayout::new(2, 2).expect("valid Phase 12 layout");
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 5)
            .expect("generate five-step Phase 12 decoding chain");
        assert_eq!(chain.total_steps, 5);
        assert_eq!(chain.steps.len(), 5);

        let first_segment =
            phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range(&chain, 0, 2)
                .expect("prepare first real Phase 30 segment");
        let second_segment =
            phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range(&chain, 2, 5)
                .expect("prepare second real Phase 30 segment");
        assert_eq!(first_segment.total_steps, 2);
        assert_eq!(second_segment.total_steps, 3);
        assert_eq!(
            first_segment.source_chain_commitment,
            second_segment.source_chain_commitment
        );
        assert_eq!(
            first_segment.chain_end_boundary_commitment,
            second_segment.chain_start_boundary_commitment
        );
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain_range(
            &first_segment,
            &chain,
            0,
            2,
        )
        .expect("first segment matches the generated source-chain range");
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain_range(
            &second_segment,
            &chain,
            2,
            5,
        )
        .expect("second segment matches the generated source-chain range");

        let full_manifest =
            phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range(&chain, 0, 5)
                .expect("prepare full real Phase 30 manifest");
        assert_eq!(
            first_segment.source_chain_commitment,
            full_manifest.source_chain_commitment
        );
        assert_eq!(
            first_segment.chain_start_boundary_commitment,
            full_manifest.chain_start_boundary_commitment
        );
        assert_eq!(
            second_segment.chain_end_boundary_commitment,
            full_manifest.chain_end_boundary_commitment
        );

        let sources = vec![
            phase38_source_from_generated_phase30_segment_harness(first_segment),
            phase38_source_from_generated_phase30_segment_harness(second_segment),
        ];
        let prototype = phase38_prepare_paper3_composition_prototype(&sources)
            .expect("compose real generated decode segments");

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
            prototype.chain_start_boundary_commitment,
            full_manifest.chain_start_boundary_commitment
        );
        assert_eq!(
            prototype.chain_end_boundary_commitment,
            full_manifest.chain_end_boundary_commitment
        );
        assert!(!prototype.recursive_verification_claimed);
        assert!(!prototype.cryptographic_compression_claimed);

        verify_phase38_paper3_composition_prototype(&prototype)
            .expect("verify real Phase 38 composition prototype");
        let json = serde_json::to_string_pretty(&prototype).expect("serialize prototype");
        let parsed = parse_phase38_paper3_composition_prototype_json(&json)
            .expect("parse serialized prototype");
        assert_eq!(parsed, prototype);
        write_phase39_composition_artifact_if_requested(&prototype);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase40_phase28_domain_phase29_phase30_boundary_probe_exposes_domain_gap() {
        let phase30 = sample_phase30_manifest();
        let mut phase29 = sample_phase29_contract();
        phase29.phase28_proof_backend_version = phase30.proof_backend_version.clone();
        phase29.statement_version = phase30.statement_version.clone();
        phase29.total_steps = phase30.total_steps;
        phase29.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&phase29)
                .expect("recommit Phase40 boundary-domain probe contract");

        assert_eq!(phase29.total_steps, phase30.total_steps);
        assert_eq!(
            phase29.phase28_proof_backend_version,
            phase30.proof_backend_version
        );
        assert_eq!(phase29.statement_version, phase30.statement_version);
        assert_ne!(
            phase29.global_start_state_commitment,
            phase30.chain_start_boundary_commitment
        );
        assert_ne!(
            phase29.global_end_state_commitment,
            phase30.chain_end_boundary_commitment
        );

        let phase31_error =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&phase29, &phase30)
                .expect_err(
                    "Phase28-domain Phase29 should not directly match Phase30 boundary domain",
                );
        assert_phase40_start_boundary_mismatch(&phase31_error);
        let phase31_message = phase31_error.to_string();
        assert_eq!(phase31_message, phase40_start_boundary_mismatch_display());

        let phase37_error =
            phase37_prepare_recursive_artifact_chain_harness_receipt(&phase29, &phase30)
                .expect_err("Phase37 should inherit the Phase29/Phase30 boundary-domain gap");
        assert_phase40_start_boundary_mismatch(&phase37_error);
        let phase37_message = phase37_error.to_string();
        assert_eq!(phase37_message, phase40_start_boundary_mismatch_display());

        write_phase40_boundary_probe_if_requested(
            &phase29,
            &phase30,
            &phase31_message,
            &phase37_message,
            "structural Phase29/Phase30 boundary-domain smoke",
        )
        .expect("write structural Phase40 boundary probe evidence if requested");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    #[ignore = "generates and checks a 16-step Stwo shared-proof source; too expensive for the default local merge gate"]
    fn phase40_full_shared_proof_phase28_phase30_boundary_probe_exposes_domain_gap() {
        let (phase28, phase30) = prove_phase28_phase30_shared_proof_boundary_demo()
            .expect("derive Phase 28 and Phase 30 from one proof list");
        let phase29 =
            phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28(
                &phase28,
            )
            .expect("derive Phase 29 from the shared-proof Phase 28 artifact");

        assert_eq!(phase28.total_steps, phase30.total_steps);
        assert_eq!(phase29.total_steps, phase30.total_steps);
        assert_eq!(
            phase29.phase28_proof_backend_version,
            phase30.proof_backend_version
        );
        assert_eq!(phase29.statement_version, phase30.statement_version);
        assert_ne!(
            phase29.global_start_state_commitment,
            phase30.chain_start_boundary_commitment
        );
        assert_ne!(
            phase29.global_end_state_commitment,
            phase30.chain_end_boundary_commitment
        );

        let phase31_error =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&phase29, &phase30)
                .expect_err(
                "real Phase28-derived Phase29 should not directly match Phase30 boundary domain",
            );
        assert_phase40_start_boundary_mismatch(&phase31_error);
        let phase31_message = phase31_error.to_string();
        assert_eq!(phase31_message, phase40_start_boundary_mismatch_display());

        let phase37_error =
            phase37_prepare_recursive_artifact_chain_harness_receipt(&phase29, &phase30)
                .expect_err(
                    "Phase37 harness receipt should inherit the real Phase29/Phase30 boundary gap",
                );
        assert_phase40_start_boundary_mismatch(&phase37_error);
        let phase37_message = phase37_error.to_string();
        assert_eq!(phase37_message, phase40_start_boundary_mismatch_display());

        write_phase40_boundary_probe_if_requested(
            &phase29,
            &phase30,
            &phase31_message,
            &phase37_message,
            "full shared-proof Phase29/Phase30 boundary-domain probe",
        )
        .expect("write full shared-proof Phase40 boundary probe evidence if requested");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_binds_phase40_gap_without_closing_phase31() {
        let (phase29, phase30) = sample_phase41_boundary_gap_sources();

        let witness = phase41_prepare_boundary_translation_witness(&phase29, &phase30)
            .expect("prepare Phase41 boundary-translation witness");
        assert_eq!(witness.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            witness.witness_version,
            STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41
        );
        assert_eq!(
            witness.semantic_scope,
            STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41
        );
        assert_eq!(
            witness.translation_rule,
            STWO_BOUNDARY_TRANSLATION_RULE_PHASE41
        );
        assert!(witness.boundary_domains_differ);
        assert!(!witness.recursive_verification_claimed);
        assert!(!witness.cryptographic_compression_claimed);
        assert!(!witness.derivation_proof_claimed);
        assert_eq!(
            witness.phase29_global_start_state_commitment,
            phase29.global_start_state_commitment
        );
        assert_eq!(
            witness.phase30_chain_start_boundary_commitment,
            phase30.chain_start_boundary_commitment
        );

        verify_phase41_boundary_translation_witness(&witness).expect("verify Phase41 witness");
        verify_phase41_boundary_translation_witness_against_sources(&witness, &phase29, &phase30)
            .expect("verify Phase41 witness against sources");

        let phase31_error =
            phase31_prepare_recursive_compression_decode_boundary_manifest(&phase29, &phase30)
                .expect_err("Phase41 witness must not silently satisfy Phase31 direct equality");
        assert_phase40_start_boundary_mismatch(&phase31_error);
        let phase37_error =
            phase37_prepare_recursive_artifact_chain_harness_receipt(&phase29, &phase30)
                .expect_err("Phase41 witness must not silently satisfy Phase37 direct equality");
        assert_phase40_start_boundary_mismatch(&phase37_error);

        let json = serde_json::to_string_pretty(&witness).expect("serialize Phase41 witness");
        let parsed_artifact = parse_phase41_boundary_translation_witness_json(&json)
            .expect("parse untrusted Phase41 witness artifact");
        assert_eq!(
            parsed_artifact.boundary_translation_witness_commitment,
            witness.boundary_translation_witness_commitment
        );
        let parsed = parse_phase41_boundary_translation_witness_json_against_sources(
            &json, &phase29, &phase30,
        )
        .expect("parse source-bound Phase41 witness");
        assert_eq!(parsed, witness);

        let path = std::env::temp_dir().join(format!(
            "phase41-boundary-translation-witness-{}.json",
            std::process::id()
        ));
        std::fs::write(&path, json).expect("write Phase41 witness temp file");
        let loaded_artifact =
            load_phase41_boundary_translation_witness(&path).expect("load Phase41 artifact file");
        assert_eq!(
            loaded_artifact.boundary_translation_witness_commitment,
            witness.boundary_translation_witness_commitment
        );
        let loaded =
            load_phase41_boundary_translation_witness_against_sources(&path, &phase29, &phase30)
                .expect("load source-bound Phase41 witness temp file");
        std::fs::remove_file(&path).expect("remove Phase41 witness temp file");
        assert_eq!(loaded, witness);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_rejects_direct_equality_false_positive() {
        let phase30 = sample_phase30_manifest();
        let phase29 = sample_phase29_contract_for_phase30(&phase30);

        let err = phase41_prepare_boundary_translation_witness(&phase29, &phase30)
            .expect_err("direct Phase29/Phase30 boundary equality is not a translation witness");
        assert!(err.to_string().contains("both boundaries already match"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_accepts_single_sided_boundary_equality() {
        let (mut phase29, phase30) = sample_phase41_boundary_gap_sources();
        phase29.global_start_state_commitment = phase30.chain_start_boundary_commitment.clone();
        phase29.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&phase29)
                .expect("recommit one-sided Phase41 Phase29 contract");

        let witness = phase41_prepare_boundary_translation_witness(&phase29, &phase30)
            .expect("one-sided boundary equality still needs a translation witness");
        assert_eq!(
            witness.phase29_global_start_state_commitment,
            witness.phase30_chain_start_boundary_commitment
        );
        assert_ne!(
            witness.phase29_global_end_state_commitment,
            witness.phase30_chain_end_boundary_commitment
        );
        verify_phase41_boundary_translation_witness_against_sources(&witness, &phase29, &phase30)
            .expect("verify one-sided Phase41 witness against sources");

        phase31_prepare_recursive_compression_decode_boundary_manifest(&phase29, &phase30)
            .expect_err("one-sided equality must not silently satisfy Phase31");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_rejects_swapped_source_boundary() {
        let (phase29, phase30) = sample_phase41_boundary_gap_sources();
        let mut witness = phase41_prepare_boundary_translation_witness(&phase29, &phase30)
            .expect("prepare Phase41 boundary-translation witness");

        witness.phase30_chain_start_boundary_commitment =
            phase30.chain_end_boundary_commitment.clone();
        let phase29_start = witness.phase29_global_start_state_commitment.clone();
        let phase30_start = witness.phase30_chain_start_boundary_commitment.clone();
        witness.start_boundary_translation_commitment = commit_phase41_boundary_translation_pair(
            "start",
            &phase29_start,
            &phase30_start,
            &witness,
        )
        .expect("recommit swapped start boundary translation");
        witness.boundary_translation_witness_commitment =
            commit_phase41_boundary_translation_witness(&witness)
                .expect("recommit swapped Phase41 witness");

        verify_phase41_boundary_translation_witness(&witness)
            .expect("internally consistent swapped witness verifies without sources");
        let err = verify_phase41_boundary_translation_witness_against_sources(
            &witness, &phase29, &phase30,
        )
        .expect_err("source-swapped Phase41 witness must fail source recomputation");
        assert!(err.to_string().contains("does not match the recomputed"));

        let json = serde_json::to_string(&witness).expect("serialize swapped Phase41 witness");
        parse_phase41_boundary_translation_witness_json(&json)
            .expect("standalone parse only checks internal consistency");
        let err = parse_phase41_boundary_translation_witness_json_against_sources(
            &json, &phase29, &phase30,
        )
        .expect_err("source-bound parse must reject swapped Phase41 witness");
        assert!(err.to_string().contains("does not match the recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_rejects_proof_derivation_claim_even_recommitted() {
        let (phase29, phase30) = sample_phase41_boundary_gap_sources();
        let mut witness = phase41_prepare_boundary_translation_witness(&phase29, &phase30)
            .expect("prepare Phase41 boundary-translation witness");
        witness.derivation_proof_claimed = true;
        witness.boundary_translation_witness_commitment =
            commit_phase41_boundary_translation_witness(&witness)
                .expect("recommit Phase41 witness with false proof-derivation claim");

        let err = verify_phase41_boundary_translation_witness(&witness)
            .expect_err("Phase41 must reject proof-level derivation claims");
        assert!(err.to_string().contains("proof-level derivation"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_deserialization_rejects_unknown_fields() {
        let (phase29, phase30) = sample_phase41_boundary_gap_sources();
        let witness = phase41_prepare_boundary_translation_witness(&phase29, &phase30)
            .expect("prepare Phase41 boundary-translation witness");
        let mut value = serde_json::to_value(&witness).expect("serialize Phase41 witness value");
        value["unexpected_phase41_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("serialize unknown-field Phase41 JSON");

        let err = parse_phase41_boundary_translation_witness_json(&json)
            .expect_err("unknown Phase41 fields must be rejected");
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase41_boundary_translation_witness_rejects_malformed_and_oversized_json() {
        let err = parse_phase41_boundary_translation_witness_json("{")
            .expect_err("malformed Phase41 witness JSON must fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig for malformed JSON, got {err:?}"
        );

        let json = " ".repeat(MAX_PHASE41_BOUNDARY_TRANSLATION_WITNESS_JSON_BYTES + 1);
        let err = parse_phase41_boundary_translation_witness_json(&json)
            .expect_err("oversized Phase41 witness JSON must fail before serde parsing");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig for oversized JSON, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    fn phase42_hash(hex: char) -> String {
        hex.to_string().repeat(64)
    }

    #[cfg(feature = "stwo-backend")]
    fn phase42_phase14_state_from_phase12(
        state: &Phase12DecodingState,
        salt: char,
    ) -> Phase14DecodingState {
        let mut phase14 = Phase14DecodingState {
            state_version: STWO_DECODING_STATE_VERSION_PHASE14.to_string(),
            step_index: state.step_index,
            position: state.position,
            layout_commitment: state.layout_commitment.clone(),
            persistent_state_commitment: state.persistent_state_commitment.clone(),
            kv_history_commitment: state.kv_history_commitment.clone(),
            kv_history_length: state.kv_history_length,
            kv_history_chunk_size: 2,
            kv_history_sealed_commitment: phase42_hash(salt),
            kv_history_sealed_chunks: state.step_index / 2,
            kv_history_open_chunk_commitment: phase42_hash('b'),
            kv_history_open_chunk_pairs: state.step_index % 2,
            kv_history_frontier_commitment: phase42_hash('c'),
            kv_history_frontier_pairs: state.kv_history_length,
            lookup_transcript_commitment: phase42_hash('d'),
            lookup_transcript_entries: state.step_index,
            lookup_frontier_commitment: phase42_hash('e'),
            lookup_frontier_entries: state.step_index,
            kv_cache_commitment: state.kv_cache_commitment.clone(),
            incoming_token_commitment: state.incoming_token_commitment.clone(),
            query_commitment: state.query_commitment.clone(),
            output_commitment: state.output_commitment.clone(),
            lookup_rows_commitment: state.lookup_rows_commitment.clone(),
            public_state_commitment: String::new(),
        };
        phase14.public_state_commitment = commit_phase14_public_state(&phase14);
        phase14
    }

    #[cfg(feature = "stwo-backend")]
    fn phase42_sample_evidence() -> Phase42BoundaryPreimageEvidence {
        let layout =
            crate::stwo_backend::Phase12DecodingLayout::new(2, 2).expect("valid Phase 12 layout");
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("generate two-step Phase 12 decoding chain");
        let phase12_start = chain
            .steps
            .first()
            .expect("Phase 12 sample chain has a first step")
            .from_state
            .clone();
        let phase12_end = chain
            .steps
            .last()
            .expect("Phase 12 sample chain has a last step")
            .to_state
            .clone();
        Phase42BoundaryPreimageEvidence {
            issue: STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
            evidence_version: STWO_BOUNDARY_PREIMAGE_EVIDENCE_VERSION_PHASE42.to_string(),
            relation_outcome: STWO_BOUNDARY_PREIMAGE_RELATION_PHASE42.to_string(),
            phase14_start_state: phase42_phase14_state_from_phase12(&phase12_start, 'a'),
            phase14_end_state: phase42_phase14_state_from_phase12(&phase12_end, 'f'),
            phase12_start_state: phase12_start,
            phase12_end_state: phase12_end,
        }
    }

    #[cfg(feature = "stwo-backend")]
    fn phase42_sample_history_equivalence_witness() -> Phase42BoundaryHistoryEquivalenceWitness {
        let mut witness = Phase42BoundaryHistoryEquivalenceWitness {
            issue: STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
            witness_version: STWO_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_VERSION_PHASE42.to_string(),
            relation_outcome: STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42.to_string(),
            transform_rule: STWO_BOUNDARY_HISTORY_EQUIVALENCE_RULE_PHASE42.to_string(),
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
            phase29_contract_commitment: phase42_hash('1'),
            phase28_aggregate_commitment: phase42_hash('2'),
            phase30_source_chain_commitment: phase42_hash('3'),
            phase30_step_envelopes_commitment: phase42_hash('4'),
            total_steps: 2,
            layout_commitment: phase42_hash('5'),
            rolling_kv_pairs: 2,
            pair_width: 2,
            phase12_start_public_state_commitment: phase42_hash('6'),
            phase12_end_public_state_commitment: phase42_hash('7'),
            phase14_start_boundary_commitment: phase42_hash('8'),
            phase14_end_boundary_commitment: phase42_hash('9'),
            phase12_start_history_commitment: phase42_hash('a'),
            phase12_end_history_commitment: phase42_hash('b'),
            phase14_start_history_commitment: phase42_hash('c'),
            phase14_end_history_commitment: phase42_hash('d'),
            initial_kv_cache_commitment: phase42_hash('e'),
            appended_pairs_commitment: phase42_hash('f'),
            appended_pair_count: 2,
            lookup_rows_commitments_commitment: phase42_hash('0'),
            lookup_rows_commitment_count: 3,
            full_history_replay_required: true,
            cryptographic_compression_claimed: false,
            witness_commitment: String::new(),
        };
        witness.witness_commitment = commit_phase42_boundary_history_equivalence_witness(&witness)
            .expect("commit sample Phase42 history witness");
        witness
    }

    #[cfg(feature = "stwo-backend")]
    fn phase43_sample_history_replay_trace() -> Phase43HistoryReplayTrace {
        let layout =
            crate::stwo_backend::Phase12DecodingLayout::new(2, 2).expect("valid Phase 12 layout");
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("generate two-step Phase 12 decoding chain");
        let phase30 = phase30_prepare_decoding_step_proof_envelope_manifest(&chain)
            .expect("derive Phase30 from Phase12 chain");
        let replayed_phase14 =
            phase14_prepare_decoding_chain(&chain).expect("derive replayed Phase14 chain");
        let latest_cached_pair_range = chain
            .layout
            .latest_cached_pair_range()
            .expect("latest cached pair range");
        let rows = chain
            .steps
            .iter()
            .zip(replayed_phase14.steps.iter())
            .zip(phase30.envelopes.iter())
            .enumerate()
            .map(
                |(step_index, ((phase12_step, phase14_step), phase30_envelope))| {
                    Phase43HistoryReplayTraceRow {
                        step_index,
                        appended_pair: phase12_step.proof.claim.final_state.memory
                            [latest_cached_pair_range.clone()]
                        .to_vec(),
                        input_lookup_rows_commitment: phase12_step
                            .from_state
                            .lookup_rows_commitment
                            .clone(),
                        output_lookup_rows_commitment: phase12_step
                            .to_state
                            .lookup_rows_commitment
                            .clone(),
                        phase30_step_envelope_commitment: phase30_envelope
                            .envelope_commitment
                            .clone(),
                        phase12_from_state: phase12_step.from_state.clone(),
                        phase12_to_state: phase12_step.to_state.clone(),
                        phase14_from_state: phase14_step.from_state.clone(),
                        phase14_to_state: phase14_step.to_state.clone(),
                    }
                },
            )
            .collect::<Vec<_>>();
        let (appended_pairs_commitment, appended_pair_count) =
            phase42_commit_source_appended_pairs(&chain).expect("commit Phase43 sample pairs");
        assert_eq!(appended_pair_count, rows.len());
        let (lookup_rows_commitments_commitment, lookup_row_count) =
            phase42_commit_source_lookup_rows_commitments(&chain)
                .expect("commit Phase43 sample lookup rows");
        assert_eq!(lookup_row_count, rows.len() + 1);
        let first = rows.first().expect("sample trace has first row");
        let last = rows.last().expect("sample trace has last row");
        let mut trace = Phase43HistoryReplayTrace {
            issue: STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
            trace_version: STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43.to_string(),
            relation_outcome: STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43.to_string(),
            transform_rule: STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43.to_string(),
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
            phase42_witness_commitment: phase42_hash('1'),
            phase29_contract_commitment: phase42_hash('2'),
            phase28_aggregate_commitment: phase42_hash('3'),
            phase30_source_chain_commitment: phase30.source_chain_commitment,
            phase30_step_envelopes_commitment: phase30.step_envelopes_commitment,
            total_steps: rows.len(),
            layout_commitment: first.phase12_from_state.layout_commitment.clone(),
            rolling_kv_pairs: chain.layout.rolling_kv_pairs,
            pair_width: chain.layout.pair_width,
            phase12_start_public_state_commitment: first
                .phase12_from_state
                .public_state_commitment
                .clone(),
            phase12_end_public_state_commitment: last
                .phase12_to_state
                .public_state_commitment
                .clone(),
            phase14_start_boundary_commitment: commit_phase23_boundary_state(
                &first.phase14_from_state,
            ),
            phase14_end_boundary_commitment: commit_phase23_boundary_state(&last.phase14_to_state),
            phase12_start_history_commitment: first
                .phase12_from_state
                .kv_history_commitment
                .clone(),
            phase12_end_history_commitment: last.phase12_to_state.kv_history_commitment.clone(),
            phase14_start_history_commitment: first
                .phase14_from_state
                .kv_history_commitment
                .clone(),
            phase14_end_history_commitment: last.phase14_to_state.kv_history_commitment.clone(),
            initial_kv_cache_commitment: first.phase12_from_state.kv_cache_commitment.clone(),
            appended_pairs_commitment,
            lookup_rows_commitments_commitment,
            rows,
            full_history_replay_required: true,
            cryptographic_compression_claimed: false,
            stwo_air_proof_claimed: false,
            trace_commitment: String::new(),
        };
        trace.trace_commitment =
            commit_phase43_history_replay_trace(&trace).expect("commit Phase43 sample trace");
        trace
    }

    #[cfg(feature = "stwo-backend")]
    fn phase43_recommit_trace(trace: &mut Phase43HistoryReplayTrace) {
        trace.trace_commitment =
            commit_phase43_history_replay_trace(trace).expect("recommit Phase43 trace");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_boundary_preimage_evidence_accepts_hash_preimage_relation_shape() {
        let evidence = phase42_sample_evidence();
        verify_phase42_boundary_preimage_evidence(&evidence)
            .expect("verify standalone Phase42 preimage evidence");

        let json = serde_json::to_string_pretty(&evidence).expect("serialize Phase42 evidence");
        let parsed = parse_phase42_boundary_preimage_evidence_json(&json)
            .expect("parse standalone Phase42 preimage evidence");
        assert_eq!(parsed, evidence);

        let path = std::env::temp_dir().join(format!(
            "phase42-boundary-preimage-evidence-{}.json",
            std::process::id()
        ));
        std::fs::write(&path, json).expect("write Phase42 evidence temp file");
        let loaded =
            load_phase42_boundary_preimage_evidence(&path).expect("load Phase42 evidence file");
        std::fs::remove_file(&path).expect("remove Phase42 evidence temp file");
        assert_eq!(loaded, evidence);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_boundary_preimage_evidence_rejects_shared_core_mismatch() {
        let mut evidence = phase42_sample_evidence();
        evidence.phase14_end_state.output_commitment = phase42_hash('9');
        evidence.phase14_end_state.public_state_commitment =
            commit_phase14_public_state(&evidence.phase14_end_state);

        let err = verify_phase42_boundary_preimage_evidence(&evidence)
            .expect_err("Phase42 must reject mismatched Phase12/Phase14 shared core");
        assert!(err.to_string().contains("shared carried-state field"));
        assert!(err.to_string().contains("output_commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_boundary_preimage_evidence_rejects_unknown_and_oversized_json() {
        let evidence = phase42_sample_evidence();
        let mut value = serde_json::to_value(&evidence).expect("serialize Phase42 evidence value");
        value["unexpected_phase42_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("serialize unknown-field Phase42 JSON");
        let err = parse_phase42_boundary_preimage_evidence_json(&json)
            .expect_err("unknown Phase42 fields must be rejected");
        assert!(err.to_string().contains("unknown field"));

        let json = " ".repeat(MAX_PHASE42_BOUNDARY_PREIMAGE_EVIDENCE_JSON_BYTES + 1);
        let err = parse_phase42_boundary_preimage_evidence_json(&json)
            .expect_err("oversized Phase42 evidence JSON must fail before serde parsing");
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_history_equivalence_witness_accepts_replay_transform_shape() {
        let witness = phase42_sample_history_equivalence_witness();
        verify_phase42_boundary_history_equivalence_witness(&witness)
            .expect("verify standalone Phase42 history-equivalence witness");

        assert_eq!(
            witness.relation_outcome,
            STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42
        );
        assert!(witness.full_history_replay_required);
        assert!(!witness.cryptographic_compression_claimed);

        let json = serde_json::to_string_pretty(&witness)
            .expect("serialize Phase42 history-equivalence witness");
        let parsed = parse_phase42_boundary_history_equivalence_witness_json(&json)
            .expect("parse standalone Phase42 history-equivalence witness");
        assert_eq!(parsed, witness);

        let path = std::env::temp_dir().join(format!(
            "phase42-history-equivalence-witness-{}.json",
            std::process::id()
        ));
        std::fs::write(&path, json).expect("write Phase42 history-equivalence witness temp file");
        let loaded = load_phase42_boundary_history_equivalence_witness(&path)
            .expect("load Phase42 history-equivalence witness file");
        std::fs::remove_file(&path).expect("remove Phase42 history-equivalence witness temp file");
        assert_eq!(loaded, witness);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_history_equivalence_witness_rejects_compression_claim_and_tamper() {
        let mut witness = phase42_sample_history_equivalence_witness();
        witness.cryptographic_compression_claimed = true;
        witness.witness_commitment = commit_phase42_boundary_history_equivalence_witness(&witness)
            .expect("recommit tampered compression claim");
        let err = verify_phase42_boundary_history_equivalence_witness(&witness)
            .expect_err("Phase42 replay witness must not claim compression");
        assert!(err.to_string().contains("cryptographic compression"));

        let mut witness = phase42_sample_history_equivalence_witness();
        witness.appended_pair_count += 1;
        witness.witness_commitment = commit_phase42_boundary_history_equivalence_witness(&witness)
            .expect("recommit tampered pair count");
        let err = verify_phase42_boundary_history_equivalence_witness(&witness)
            .expect_err("Phase42 replay witness must reject pair-count drift");
        assert!(err.to_string().contains("appended_pair_count"));

        let mut witness = phase42_sample_history_equivalence_witness();
        witness.phase14_end_history_commitment = phase42_hash('a');
        let err = verify_phase42_boundary_history_equivalence_witness(&witness)
            .expect_err("Phase42 replay witness must reject stale witness commitment");
        assert!(err.to_string().contains("witness commitment"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_history_equivalence_witness_rejects_unknown_and_oversized_json() {
        let witness = phase42_sample_history_equivalence_witness();
        let mut value =
            serde_json::to_value(&witness).expect("serialize Phase42 history witness value");
        value["unexpected_phase42_history_field"] = serde_json::json!(true);
        let json =
            serde_json::to_string(&value).expect("serialize unknown-field Phase42 history JSON");
        let err = parse_phase42_boundary_history_equivalence_witness_json(&json)
            .expect_err("unknown Phase42 history fields must be rejected");
        assert!(err.to_string().contains("unknown field"));

        let json = " ".repeat(MAX_PHASE42_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_JSON_BYTES + 1);
        let err = parse_phase42_boundary_history_equivalence_witness_json(&json)
            .expect_err("oversized Phase42 history witness JSON must fail before serde parsing");
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase43_history_replay_trace_accepts_normalized_replay_shape() {
        let trace = phase43_sample_history_replay_trace();
        verify_phase43_history_replay_trace(&trace).expect("verify standalone Phase43 trace");

        assert_eq!(
            trace.relation_outcome,
            STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43
        );
        assert!(trace.full_history_replay_required);
        assert!(!trace.cryptographic_compression_claimed);
        assert!(!trace.stwo_air_proof_claimed);
        assert_eq!(trace.rows.len(), trace.total_steps);
        assert_ne!(
            trace.phase12_end_history_commitment, trace.phase14_end_history_commitment,
            "Phase43 trace must preserve the Phase12/Phase14 history-domain gap"
        );

        let json = serde_json::to_string_pretty(&trace).expect("serialize Phase43 trace");
        let parsed =
            parse_phase43_history_replay_trace_json(&json).expect("parse standalone Phase43 trace");
        assert_eq!(parsed, trace);

        let path = std::env::temp_dir().join(format!(
            "phase43-history-replay-trace-{}.json",
            std::process::id()
        ));
        std::fs::write(&path, json).expect("write Phase43 trace temp file");
        let loaded = load_phase43_history_replay_trace(&path).expect("load Phase43 trace file");
        std::fs::remove_file(&path).expect("remove Phase43 trace temp file");
        assert_eq!(loaded, trace);
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase43_history_replay_trace_rejects_reordered_row_even_when_recommitted() {
        let mut trace = phase43_sample_history_replay_trace();
        trace.rows.swap(0, 1);
        trace.appended_pairs_commitment =
            phase43_commit_trace_appended_pairs(&trace).expect("recommit swapped pairs");
        trace.lookup_rows_commitments_commitment =
            phase43_commit_trace_lookup_rows_commitments(&trace)
                .expect("recommit swapped lookup rows");
        trace.phase30_step_envelopes_commitment =
            phase43_commit_trace_phase30_step_envelopes(&trace)
                .expect("recommit swapped Phase30 envelope rows");
        phase43_recommit_trace(&mut trace);

        let err = verify_phase43_history_replay_trace(&trace)
            .expect_err("Phase43 must reject reordered replay rows");
        assert!(err.to_string().contains("step_index"), "{err}");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase43_history_replay_trace_rejects_stale_lookup_handle_even_when_recommitted() {
        let mut trace = phase43_sample_history_replay_trace();
        trace.rows[0].output_lookup_rows_commitment = phase42_hash('a');
        trace.lookup_rows_commitments_commitment =
            phase43_commit_trace_lookup_rows_commitments(&trace)
                .expect("recommit stale lookup rows");
        phase43_recommit_trace(&mut trace);

        let err = verify_phase43_history_replay_trace(&trace)
            .expect_err("Phase43 must reject stale row-level lookup handle");
        assert!(
            err.to_string().contains("output_lookup_rows_commitment"),
            "{err}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase43_history_replay_trace_rejects_boundary_count_claim_and_commitment_tamper() {
        let mut boundary_swap = phase43_sample_history_replay_trace();
        boundary_swap.phase14_start_boundary_commitment =
            boundary_swap.phase14_end_boundary_commitment.clone();
        phase43_recommit_trace(&mut boundary_swap);
        let err = verify_phase43_history_replay_trace(&boundary_swap)
            .expect_err("Phase43 must reject swapped Phase28/Phase14 boundary");
        assert!(err.to_string().contains("start boundary"), "{err}");

        let mut count_mismatch = phase43_sample_history_replay_trace();
        count_mismatch.total_steps += 1;
        phase43_recommit_trace(&mut count_mismatch);
        let err = verify_phase43_history_replay_trace(&count_mismatch)
            .expect_err("Phase43 must reject count mismatch");
        assert!(err.to_string().contains("total_steps"), "{err}");

        let mut air_claim = phase43_sample_history_replay_trace();
        air_claim.stwo_air_proof_claimed = true;
        phase43_recommit_trace(&mut air_claim);
        let err = verify_phase43_history_replay_trace(&air_claim)
            .expect_err("Phase43 must reject premature AIR proof claims");
        assert!(err.to_string().contains("Stwo AIR proof"), "{err}");

        let mut envelope_drift = phase43_sample_history_replay_trace();
        envelope_drift.rows[0].phase30_step_envelope_commitment = phase42_hash('e');
        phase43_recommit_trace(&mut envelope_drift);
        let err = verify_phase43_history_replay_trace(&envelope_drift)
            .expect_err("Phase43 must reject stale Phase30 envelope handle");
        assert!(err.to_string().contains("step_envelopes"), "{err}");

        let mut compression_claim = phase43_sample_history_replay_trace();
        compression_claim.cryptographic_compression_claimed = true;
        phase43_recommit_trace(&mut compression_claim);
        let err = verify_phase43_history_replay_trace(&compression_claim)
            .expect_err("Phase43 must reject premature compression claims");
        assert!(
            err.to_string().contains("cryptographic compression"),
            "{err}"
        );

        let mut stale_commitment = phase43_sample_history_replay_trace();
        stale_commitment.phase30_source_chain_commitment = phase42_hash('f');
        let err = verify_phase43_history_replay_trace(&stale_commitment)
            .expect_err("Phase43 must reject stale trace commitment");
        assert!(err.to_string().contains("trace commitment"), "{err}");
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase43_history_replay_trace_rejects_unknown_and_oversized_json() {
        let trace = phase43_sample_history_replay_trace();
        let mut value = serde_json::to_value(&trace).expect("serialize Phase43 trace value");
        value["unexpected_phase43_trace_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("serialize unknown-field Phase43 JSON");
        let err = parse_phase43_history_replay_trace_json(&json)
            .expect_err("unknown Phase43 fields must be rejected");
        assert!(err.to_string().contains("unknown field"));

        let json = " ".repeat(MAX_PHASE43_HISTORY_REPLAY_TRACE_JSON_BYTES + 1);
        let err = parse_phase43_history_replay_trace_json(&json)
            .expect_err("oversized Phase43 trace JSON must fail before serde parsing");
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase42_boundary_preimage_evidence_rejects_synthetic_phase28_shell_sources() {
        let layout =
            crate::stwo_backend::Phase12DecodingLayout::new(2, 2).expect("valid Phase 12 layout");
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("generate two-step Phase 12 decoding chain");
        let phase30 = phase30_prepare_decoding_step_proof_envelope_manifest(&chain)
            .expect("derive Phase30 from Phase12 chain");
        let mut phase28 = empty_phase28_shell();
        phase28.proof_backend_version = phase30.proof_backend_version.clone();
        phase28.statement_version = phase30.statement_version.clone();
        phase28.total_steps = phase30.total_steps;
        let mut phase29 = sample_phase29_contract();
        phase29.phase28_proof_backend_version = phase30.proof_backend_version.clone();
        phase29.statement_version = phase30.statement_version.clone();
        phase29.total_steps = phase30.total_steps;
        phase29.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&phase29)
                .expect("recommit Phase29 source");

        let err = phase42_prepare_boundary_preimage_evidence(&chain, &phase28, &phase29, &phase30)
            .expect_err("Phase42 must reject Phase28 shells without nested boundary preimages");
        let message = err.to_string();
        assert!(
            message.contains("at least two members") || message.contains("Phase 28"),
            "{message}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    #[ignore = "generates and checks a 16-step shared-proof Phase12/28/29/30 source; run explicitly for the expensive Phase42 kill decision"]
    fn phase42_live_shared_phase28_phase30_sources_expose_history_gap_and_accept_replay_witness() {
        let (chain, phase28, phase30) = prove_phase42_boundary_preimage_shared_proof_demo()
            .expect("derive shared Phase12/28/30 boundary-preimage sources");
        let phase29 =
            phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28(
                &phase28,
            )
            .expect("derive Phase29 from Phase28 source");
        assert_ne!(
            phase29.global_start_state_commitment,
            phase30.chain_start_boundary_commitment
        );
        let err = phase42_prepare_boundary_preimage_evidence(&chain, &phase28, &phase29, &phase30)
            .expect_err("live Phase42 source stack must expose the Phase12/Phase14 history gap");
        let message = err.to_string();
        assert!(message.contains("kv_history_commitment"), "{message}");

        let witness = phase42_prepare_boundary_history_equivalence_witness(
            &chain, &phase28, &phase29, &phase30,
        )
        .expect("live Phase42 source stack must accept full-replay history equivalence");
        assert_eq!(
            witness.relation_outcome,
            STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42
        );
        assert!(witness.full_history_replay_required);
        assert!(!witness.cryptographic_compression_claimed);
        assert_ne!(
            witness.phase12_end_history_commitment,
            witness.phase14_end_history_commitment
        );
        verify_phase42_boundary_history_equivalence_witness_against_sources(
            &witness, &chain, &phase28, &phase29, &phase30,
        )
        .expect("source-bound Phase42 history-equivalence witness must verify");

        let mut tampered = witness.clone();
        tampered.appended_pairs_commitment = phase42_hash('e');
        tampered.witness_commitment =
            commit_phase42_boundary_history_equivalence_witness(&tampered)
                .expect("recommit tampered Phase42 history-equivalence witness");
        let err = verify_phase42_boundary_history_equivalence_witness_against_sources(
            &tampered, &chain, &phase28, &phase29, &phase30,
        )
        .expect_err("source-bound Phase42 history witness must reject appended-pair drift");
        assert!(err.to_string().contains("does not match the recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    #[ignore = "generates and checks a 16-step shared-proof Phase12/28/29/30 source; run explicitly for the expensive Phase43 kill decision"]
    fn phase43_live_shared_sources_accept_trace_and_reject_source_chain_swap() {
        let (chain, phase28, phase30) = prove_phase42_boundary_preimage_shared_proof_demo()
            .expect("derive shared Phase12/28/30 Phase43 replay-trace sources");
        let phase29 =
            phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28(
                &phase28,
            )
            .expect("derive Phase29 from Phase28 source");
        let trace = phase43_prepare_history_replay_trace(&chain, &phase28, &phase29, &phase30)
            .expect("live Phase43 source stack must produce a replay trace");
        assert_eq!(
            trace.relation_outcome,
            STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43
        );
        assert!(trace.full_history_replay_required);
        assert!(!trace.cryptographic_compression_claimed);
        assert!(!trace.stwo_air_proof_claimed);
        verify_phase43_history_replay_trace_against_sources(
            &trace, &chain, &phase28, &phase29, &phase30,
        )
        .expect("source-bound Phase43 replay trace must verify");

        let mut source_chain_swap = trace.clone();
        source_chain_swap.phase30_source_chain_commitment = phase42_hash('f');
        phase43_recommit_trace(&mut source_chain_swap);
        verify_phase43_history_replay_trace(&source_chain_swap)
            .expect("standalone Phase43 trace only checks internal replay shape");
        let err = verify_phase43_history_replay_trace_against_sources(
            &source_chain_swap,
            &chain,
            &phase28,
            &phase29,
            &phase30,
        )
        .expect_err("source-bound Phase43 trace must reject Phase30 source-chain swap");
        assert!(err.to_string().contains("does not match the recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_boundary_gap() {
        let mut sources = sample_phase38_segment_sources();
        let source_chain = sources[0].phase30_manifest.source_chain_commitment.clone();
        let end = sources[1]
            .phase37_receipt
            .chain_end_boundary_commitment
            .clone();
        sources[1] =
            sample_phase38_segment_source(&phase38_test_hash32('d'), &end, 3, &source_chain);

        let err = phase38_prepare_paper3_composition_prototype(&sources)
            .expect_err("boundary gap must fail");
        assert!(err.to_string().contains("boundary gap"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_shared_lookup_identity_drift() {
        let mut sources = sample_phase38_segment_sources();
        sources[1].phase30_manifest.envelopes[0].static_lookup_registry_commitment =
            phase38_test_hash32('e');
        sources[1].phase30_manifest.envelopes[0].envelope_commitment =
            commit_phase30_step_envelope(&sources[1].phase30_manifest.envelopes[0]);
        sources[1].phase30_manifest.step_envelopes_commitment =
            commit_phase30_step_envelope_list(&sources[1].phase30_manifest.envelopes);
        refresh_phase38_source_receipt(&mut sources[1]);

        let err = phase38_prepare_paper3_composition_prototype(&sources)
            .expect_err("shared lookup drift must fail");
        assert!(err.to_string().contains("shared lookup identity drift"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_source_chain_drift() {
        let mut sources = sample_phase38_segment_sources();
        let start = sources[0]
            .phase37_receipt
            .chain_end_boundary_commitment
            .clone();
        let end = sources[1]
            .phase37_receipt
            .chain_end_boundary_commitment
            .clone();
        sources[1] = sample_phase38_segment_source(&start, &end, 3, &phase38_test_hash32('8'));

        let err = phase38_prepare_paper3_composition_prototype(&sources)
            .expect_err("source-chain drift must fail");
        assert!(err.to_string().contains("source-chain identity drift"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_execution_template_drift() {
        let mut sources = sample_phase38_segment_sources();
        sources[1].phase29_contract.source_template_commitment = phase38_test_hash32('5');
        sources[1].phase29_contract.input_contract_commitment =
            commit_phase29_recursive_compression_input_contract(&sources[1].phase29_contract)
                .expect("recommit template-drift Phase 29 contract");
        refresh_phase38_source_receipt(&mut sources[1]);

        let err = phase38_prepare_paper3_composition_prototype(&sources)
            .expect_err("execution template drift must fail");
        assert!(err.to_string().contains("execution template drift"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_unbound_phase37_commitment_swap() {
        let sources = sample_phase38_segment_sources();
        let mut prototype = phase38_prepare_paper3_composition_prototype(&sources)
            .expect("prepare Phase 38 composition prototype");
        prototype.segments[0].phase37_receipt_commitment = phase38_test_hash32('f');
        prototype.segment_list_commitment = commit_phase38_segment_list(&prototype.segments)
            .expect("recommit tampered segment list");
        prototype.composition_commitment = commit_phase38_paper3_composition_prototype(&prototype)
            .expect("recommit tampered prototype");

        let err = verify_phase38_paper3_composition_prototype(&prototype)
            .expect_err("unbound Phase 37 commitment swap must fail");
        assert!(err.to_string().contains("Phase 37 receipt commitment"));
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_tampered_baseline() {
        let sources = sample_phase38_segment_sources();
        let mut prototype = phase38_prepare_paper3_composition_prototype(&sources)
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
        let sources = sample_phase38_segment_sources();
        let prototype = phase38_prepare_paper3_composition_prototype(&sources)
            .expect("prepare Phase 38 composition prototype");
        let json = serde_json::to_string(&prototype).expect("serialize phase38 prototype");
        let parsed = parse_phase38_paper3_composition_prototype_json(&json)
            .expect("parse phase38 prototype");
        assert_eq!(parsed, prototype);

        let mut tampered = serde_json::to_value(&prototype).expect("serialize phase38 value");
        tampered["composition_commitment"] = serde_json::json!("0".repeat(64));
        let err = serde_json::from_value::<Phase38Paper3CompositionPrototype>(tampered)
            .expect_err("tampered Phase 38 commitment must be rejected");
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_rejects_forged_lookup_identity() {
        let sources = sample_phase38_segment_sources();
        let mut prototype = phase38_prepare_paper3_composition_prototype(&sources)
            .expect("prepare Phase 38 composition prototype");
        let forged_lookup_identity = phase38_test_hash32('7');
        for segment in &mut prototype.segments {
            segment.lookup_identity_commitment = forged_lookup_identity.clone();
        }
        prototype.shared_lookup_identity_commitment =
            commit_phase38_shared_lookup_identity(&prototype.segments[0])
                .expect("recommit forged shared lookup identity");
        prototype.segment_list_commitment =
            commit_phase38_segment_list(&prototype.segments).expect("recommit forged segment list");
        prototype.composition_commitment = commit_phase38_paper3_composition_prototype(&prototype)
            .expect("recommit forged prototype");

        let json = serde_json::to_string(&prototype).expect("serialize forged phase38 prototype");
        let err = parse_phase38_paper3_composition_prototype_json(&json)
            .expect_err("forged lookup identity must fail against embedded manifest");
        assert!(err.to_string().contains("lookup identity commitment"));
        assert!(err.to_string().contains("does not match recomputed"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_source_deserialization_rejects_unbound_bundle() {
        let source = sample_phase38_segment_sources()
            .pop()
            .expect("sample source");
        let mut value = serde_json::to_value(&source).expect("serialize phase38 source");
        value["phase37_receipt"]["total_steps"] = serde_json::json!(99);

        let err = serde_json::from_value::<Phase38Paper3CompositionSource>(value)
            .expect_err("source deserialization must verify cross-artifact binding");
        assert!(err.to_string().contains("Phase 37"));

        let mut with_unknown = serde_json::to_value(&source).expect("serialize phase38 source");
        with_unknown["unexpected_source_field"] = serde_json::json!(true);
        let err = serde_json::from_value::<Phase38Paper3CompositionSource>(with_unknown)
            .expect_err("source deserialization must reject unknown fields");
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_segment_deserialization_rejects_bad_interval() {
        let sources = sample_phase38_segment_sources();
        let prototype = phase38_prepare_paper3_composition_prototype(&sources)
            .expect("prepare Phase 38 composition prototype");
        let mut segment_value =
            serde_json::to_value(&prototype.segments[0]).expect("serialize phase38 segment");
        segment_value["step_end"] = serde_json::json!(
            prototype.segments[0].step_start + prototype.segments[0].total_steps + 1
        );

        let err = serde_json::from_value::<Phase38Paper3CompositionSegment>(segment_value)
            .expect_err("segment deserialization must reject inconsistent interval");
        assert!(err.to_string().contains("spans"));
        assert!(err.to_string().contains("declares"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_paper3_composition_prototype_deserialization_rejects_unknown_fields() {
        let sources = sample_phase38_segment_sources();
        let prototype = phase38_prepare_paper3_composition_prototype(&sources)
            .expect("prepare Phase 38 composition prototype");
        let mut value = serde_json::to_value(&prototype).expect("serialize phase38 value");
        value["unexpected_phase38_field"] = serde_json::json!(true);
        let json = serde_json::to_string(&value).expect("json with unknown field");

        let err = parse_phase38_paper3_composition_prototype_json(&json)
            .expect_err("unknown Phase 38 fields must be rejected");
        assert!(err.to_string().contains("unknown field"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_parse_paper3_composition_prototype_reports_malformed_json_as_invalid_config() {
        let err = parse_phase38_paper3_composition_prototype_json("{")
            .expect_err("malformed Phase 38 prototype JSON must fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_parse_paper3_composition_prototype_rejects_oversized_json() {
        let json = " ".repeat(MAX_PHASE38_PAPER3_COMPOSITION_PROTOTYPE_JSON_BYTES + 1);
        let err = parse_phase38_paper3_composition_prototype_json(&json)
            .expect_err("oversized Phase 38 prototype JSON must fail before serde parsing");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase38_load_paper3_composition_prototype_rejects_oversized_file() {
        let path = std::env::temp_dir().join(format!(
            "phase38-paper3-composition-prototype-oversized-{}.json",
            std::process::id()
        ));
        std::fs::write(
            &path,
            vec![b'x'; MAX_PHASE38_PAPER3_COMPOSITION_PROTOTYPE_JSON_BYTES + 1],
        )
        .expect("write oversized Phase 38 prototype");

        let err = load_phase38_paper3_composition_prototype(&path)
            .expect_err("oversized Phase 38 prototype should fail");
        assert!(
            matches!(err, VmError::InvalidConfig(_)),
            "expected InvalidConfig, got {err:?}"
        );
        assert!(err.to_string().contains("exceeding the limit"));
        let _ = std::fs::remove_file(path);
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
