mod adapter;
#[cfg(feature = "stwo-backend")]
mod arithmetic_component;
#[cfg(feature = "stwo-backend")]
mod arithmetic_subset_prover;
#[cfg(feature = "stwo-backend")]
mod decoding;
#[cfg(feature = "stwo-backend")]
mod history_replay_projection_prover;
mod layout;
#[cfg(feature = "stwo-backend")]
mod lookup_component;
#[cfg(feature = "stwo-backend")]
mod lookup_prover;
#[cfg(feature = "stwo-backend")]
mod normalization_component;
#[cfg(feature = "stwo-backend")]
mod normalization_prover;
mod recursion;
#[cfg(feature = "stwo-backend")]
mod shared_lookup_artifact;

use crate::config::Attention2DMode;
use crate::error::{Result, VmError};
use crate::instruction::Program;

pub use adapter::{
    phase2_dependency_seam, StwoDependencySeam, STWO_CONSTRAINT_FRAMEWORK_VERSION_PHASE2,
    STWO_CRATE_VERSION_PHASE2,
};
#[cfg(feature = "stwo-backend")]
pub use arithmetic_component::{
    phase3_arithmetic_component_metadata, phase3_arithmetic_preprocessed_columns,
    Phase3ArithmeticComponentMetadata, Phase3TreeSubspan,
};
#[cfg(feature = "stwo-backend")]
pub(crate) use arithmetic_subset_prover::{
    prove_phase5_arithmetic_subset, verify_phase5_arithmetic_subset,
};
#[cfg(feature = "stwo-backend")]
pub use decoding::{
    decoding_step_v1_program_with_initial_memory, decoding_step_v1_template_program,
    decoding_step_v2_program_with_initial_memory, decoding_step_v2_template_program,
    derive_phase11_from_final_memory, derive_phase11_from_program_initial_state,
    derive_phase12_from_final_memory, derive_phase12_from_program_initial_state,
    infer_phase12_decoding_layout, load_phase11_decoding_chain, load_phase12_decoding_chain,
    load_phase13_decoding_layout_matrix, load_phase14_decoding_chain,
    load_phase15_decoding_segment_bundle, load_phase16_decoding_segment_rollup,
    load_phase17_decoding_rollup_matrix, load_phase21_decoding_matrix_accumulator,
    load_phase22_decoding_lookup_accumulator, load_phase23_decoding_cross_step_lookup_accumulator,
    load_phase24_decoding_state_relation_accumulator,
    load_phase25_intervalized_decoding_state_relation,
    load_phase26_folded_intervalized_decoding_state_relation,
    load_phase27_chained_folded_intervalized_decoding_state_relation,
    load_phase27_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    load_phase28_aggregated_chained_folded_intervalized_decoding_state_relation,
    load_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    load_phase30_decoding_step_proof_envelope_manifest, matches_decoding_step_v1_family,
    matches_decoding_step_v2_family, parse_phase30_decoding_step_proof_envelope_manifest_json,
    phase11_prepare_decoding_chain, phase12_default_decoding_layout,
    phase12_prepare_decoding_chain, phase13_default_decoding_layout_matrix,
    phase14_prepare_decoding_chain, phase15_default_segment_step_limit,
    phase15_prepare_segment_bundle, phase16_default_rollup_segment_limit,
    phase16_prepare_segment_rollup, phase21_prepare_decoding_matrix_accumulator,
    phase22_prepare_decoding_lookup_accumulator,
    phase23_prepare_decoding_cross_step_lookup_accumulator,
    phase24_prepare_decoding_state_relation_accumulator,
    phase25_prepare_intervalized_decoding_state_relation,
    phase26_prepare_folded_intervalized_decoding_state_relation,
    phase27_prepare_chained_folded_intervalized_decoding_state_relation,
    phase28_prepare_aggregated_chained_folded_intervalized_decoding_state_relation,
    phase30_prepare_decoding_step_proof_envelope_manifest,
    phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range,
    prove_phase11_decoding_demo, prove_phase12_decoding_demo,
    prove_phase12_decoding_demo_for_layout, prove_phase12_decoding_demo_for_layout_steps,
    prove_phase12_decoding_demo_steps, prove_phase13_decoding_layout_matrix_demo,
    prove_phase14_decoding_demo, prove_phase14_decoding_demo_for_layout,
    prove_phase15_decoding_demo, prove_phase15_decoding_demo_for_layout,
    prove_phase16_decoding_demo, prove_phase16_decoding_demo_for_layout,
    prove_phase17_decoding_rollup_matrix_demo, prove_phase21_decoding_matrix_accumulator_demo,
    prove_phase22_decoding_lookup_accumulator_demo,
    prove_phase23_decoding_cross_step_lookup_accumulator_demo,
    prove_phase24_decoding_state_relation_accumulator_demo,
    prove_phase25_intervalized_decoding_state_relation_demo,
    prove_phase26_folded_intervalized_decoding_state_relation_demo,
    prove_phase27_chained_folded_intervalized_decoding_state_relation_demo,
    prove_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_demo,
    prove_phase28_phase30_shared_proof_boundary_demo,
    prove_phase42_boundary_preimage_shared_proof_demo, save_phase11_decoding_chain,
    save_phase12_decoding_chain, save_phase13_decoding_layout_matrix, save_phase14_decoding_chain,
    save_phase15_decoding_segment_bundle, save_phase16_decoding_segment_rollup,
    save_phase17_decoding_rollup_matrix, save_phase21_decoding_matrix_accumulator,
    save_phase22_decoding_lookup_accumulator, save_phase23_decoding_cross_step_lookup_accumulator,
    save_phase24_decoding_state_relation_accumulator,
    save_phase25_intervalized_decoding_state_relation,
    save_phase26_folded_intervalized_decoding_state_relation,
    save_phase27_chained_folded_intervalized_decoding_state_relation,
    save_phase28_aggregated_chained_folded_intervalized_decoding_state_relation,
    save_phase30_decoding_step_proof_envelope_manifest, verify_phase11_decoding_chain,
    verify_phase11_decoding_chain_with_proof_checks, verify_phase12_decoding_chain,
    verify_phase12_decoding_chain_with_proof_checks, verify_phase13_decoding_layout_matrix,
    verify_phase13_decoding_layout_matrix_with_proof_checks, verify_phase14_decoding_chain,
    verify_phase14_decoding_chain_with_proof_checks, verify_phase15_decoding_segment_bundle,
    verify_phase15_decoding_segment_bundle_with_proof_checks,
    verify_phase16_decoding_segment_rollup,
    verify_phase16_decoding_segment_rollup_with_proof_checks,
    verify_phase17_decoding_rollup_matrix, verify_phase17_decoding_rollup_matrix_with_proof_checks,
    verify_phase21_decoding_matrix_accumulator,
    verify_phase21_decoding_matrix_accumulator_with_proof_checks,
    verify_phase22_decoding_lookup_accumulator,
    verify_phase22_decoding_lookup_accumulator_with_proof_checks,
    verify_phase23_decoding_cross_step_lookup_accumulator,
    verify_phase23_decoding_cross_step_lookup_accumulator_with_proof_checks,
    verify_phase24_decoding_state_relation_accumulator,
    verify_phase24_decoding_state_relation_accumulator_with_proof_checks,
    verify_phase25_intervalized_decoding_state_relation,
    verify_phase25_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase26_folded_intervalized_decoding_state_relation,
    verify_phase26_folded_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase27_chained_folded_intervalized_decoding_state_relation,
    verify_phase27_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation,
    verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks,
    verify_phase30_decoding_step_proof_envelope_manifest,
    verify_phase30_decoding_step_proof_envelope_manifest_against_chain,
    verify_phase30_decoding_step_proof_envelope_manifest_against_chain_range,
    Phase11DecodingChainManifest, Phase11DecodingState, Phase11DecodingStep,
    Phase12DecodingChainManifest, Phase12DecodingLayout, Phase12DecodingState, Phase12DecodingStep,
    Phase13DecodingLayoutMatrixManifest, Phase14DecodingChainManifest, Phase14DecodingState,
    Phase14DecodingStep, Phase15DecodingHistorySegment,
    Phase15DecodingHistorySegmentBundleManifest, Phase16DecodingHistoryRollup,
    Phase16DecodingHistoryRollupManifest, Phase17DecodingHistoryRollupMatrixManifest,
    Phase21DecodingMatrixAccumulatorManifest, Phase22DecodingLookupAccumulatorManifest,
    Phase23DecodingCrossStepLookupAccumulatorManifest,
    Phase24DecodingStateRelationAccumulatorManifest, Phase24DecodingStateRelationMemberSummary,
    Phase25IntervalizedDecodingStateRelationManifest,
    Phase25IntervalizedDecodingStateRelationMemberSummary,
    Phase26FoldedIntervalizedDecodingStateRelationManifest,
    Phase26FoldedIntervalizedDecodingStateRelationMemberSummary,
    Phase27ChainedFoldedIntervalizedDecodingStateRelationManifest,
    Phase27ChainedFoldedIntervalizedDecodingStateRelationMemberSummary,
    Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest,
    Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationMemberSummary,
    Phase30DecodingStepProofEnvelope, Phase30DecodingStepProofEnvelopeManifest,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
    STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE27,
    STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27,
    STWO_DECODING_CHAIN_SCOPE_PHASE11, STWO_DECODING_CHAIN_SCOPE_PHASE12,
    STWO_DECODING_CHAIN_SCOPE_PHASE14, STWO_DECODING_CHAIN_VERSION_PHASE11,
    STWO_DECODING_CHAIN_VERSION_PHASE12, STWO_DECODING_CHAIN_VERSION_PHASE14,
    STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_SCOPE_PHASE23,
    STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23,
    STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13, STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13,
    STWO_DECODING_LAYOUT_VERSION_PHASE12, STWO_DECODING_LOOKUP_ACCUMULATOR_SCOPE_PHASE22,
    STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22,
    STWO_DECODING_MATRIX_ACCUMULATOR_SCOPE_PHASE21,
    STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21, STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17,
    STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17, STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15,
    STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15, STWO_DECODING_SEGMENT_ROLLUP_SCOPE_PHASE16,
    STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16,
    STWO_DECODING_STATE_RELATION_ACCUMULATOR_SCOPE_PHASE24,
    STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24, STWO_DECODING_STATE_VERSION_PHASE11,
    STWO_DECODING_STATE_VERSION_PHASE12, STWO_DECODING_STATE_VERSION_PHASE14,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_RELATION_PHASE30, STWO_DECODING_STEP_ENVELOPE_SCOPE_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_VERSION_PHASE30,
    STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE26,
    STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26,
    STWO_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE25,
    STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25,
    STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
};
#[cfg(feature = "stwo-backend")]
pub use history_replay_projection_prover::{
    assess_phase43_history_replay_projection_boundary, assess_phase43_proof_native_source_exposure,
    commit_phase43_history_replay_projection_compact_verifier_inputs,
    commit_phase44d_history_replay_projection_terminal_boundary_interaction_claim,
    commit_phase44d_history_replay_projection_terminal_boundary_logup_closure,
    derive_phase43_history_replay_projection_compact_verifier_inputs,
    derive_phase43_history_replay_projection_source_root_claim,
    derive_phase44d_history_replay_projection_terminal_boundary_logup_closure,
    emit_phase44d_history_replay_projection_source_chain_public_output_boundary,
    emit_phase44d_history_replay_projection_source_emission,
    emit_phase44d_history_replay_projection_source_emission_public_output,
    prepare_phase44d_history_replay_projection_source_emitted_root_artifact,
    project_phase44d_history_replay_projection_source_emission_public_output,
    prove_phase43_history_replay_projection_compact_claim_envelope,
    prove_phase43_history_replay_projection_envelope,
    verify_phase43_history_replay_projection_compact_claim_envelope,
    verify_phase43_history_replay_projection_envelope,
    verify_phase43_history_replay_projection_source_root_binding,
    verify_phase43_history_replay_projection_source_root_compact_envelope,
    verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance,
    verify_phase44d_history_replay_projection_external_source_root_acceptance,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance,
    verify_phase44d_history_replay_projection_source_emission_acceptance,
    verify_phase44d_history_replay_projection_source_emission_public_output_acceptance,
    verify_phase44d_history_replay_projection_terminal_boundary_logup_closure,
    Phase43HistoryReplayProjectionBoundaryAssessment, Phase43HistoryReplayProjectionCompactClaim,
    Phase43HistoryReplayProjectionCompactProofEnvelope,
    Phase43HistoryReplayProjectionCompactVerifierInputs,
    Phase43HistoryReplayProjectionProofEnvelope, Phase43HistoryReplayProjectionSourceRootClaim,
    Phase43HistoryReplayProjectionTerminalBoundaryClaim,
    Phase43HistoryReplayProofNativeSourceExposureAssessment,
    Phase44DHistoryReplayProjectionExternalSourceRootAcceptance,
    Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    Phase44DHistoryReplayProjectionSourceEmission,
    Phase44DHistoryReplayProjectionSourceEmissionPublicOutput,
    Phase44DHistoryReplayProjectionSourceEmittedRootArtifact,
    Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim,
    Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure,
    STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_ASSESSMENT_VERSION_PHASE43,
    STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_DECISION_PHASE43,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_COMPACT_VERIFIER_INPUTS_VERSION_PHASE46,
    STWO_HISTORY_REPLAY_PROJECTION_EXTERNAL_SOURCE_ROOT_ACCEPTANCE_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43,
    STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_BUNDLE_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_ISSUE_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_PUBLIC_OUTPUT_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMITTED_ROOT_ARTIFACT_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_BINDING_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_CLAIM_VERSION_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_SEMANTIC_SCOPE_PHASE44,
    STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43,
    STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_INTERACTION_CLAIM_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_LOGUP_CLOSURE_VERSION_PHASE44D,
    STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_VERSION_PHASE44,
    STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_DECISION_PHASE43,
    STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_VERSION_PHASE43,
};
pub use layout::{
    phase2_fixture_matrix, phase2_module_layout, phase2_supported_mnemonics,
    StwoBackendModuleLayout,
};
#[cfg(feature = "stwo-backend")]
pub use lookup_component::{
    phase3_binary_step_lookup_component_metadata, phase3_lookup_preprocessed_columns,
    phase3_lookup_table_rows, Phase3LookupComponentMetadata, Phase3LookupTableRow,
};
#[cfg(feature = "stwo-backend")]
pub use lookup_prover::{
    load_phase10_shared_binary_step_lookup_proof, load_phase3_binary_step_lookup_proof,
    prove_phase10_shared_binary_step_lookup_envelope, prove_phase3_binary_step_lookup_demo,
    prove_phase3_binary_step_lookup_demo_envelope, save_phase10_shared_binary_step_lookup_proof,
    save_phase3_binary_step_lookup_proof, verify_phase10_shared_binary_step_lookup_envelope,
    verify_phase3_binary_step_lookup_demo, verify_phase3_binary_step_lookup_demo_envelope,
    Phase10SharedLookupProofEnvelope, Phase3LookupProofEnvelope, STWO_LOOKUP_PROOF_VERSION_PHASE3,
    STWO_LOOKUP_SEMANTIC_SCOPE_PHASE3, STWO_LOOKUP_STATEMENT_VERSION_PHASE3,
    STWO_SHARED_LOOKUP_PROOF_VERSION_PHASE10, STWO_SHARED_LOOKUP_SEMANTIC_SCOPE_PHASE10,
    STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
};
#[cfg(feature = "stwo-backend")]
pub use normalization_component::{
    phase5_normalization_lookup_component_metadata, phase5_normalization_preprocessed_columns,
    phase5_normalization_table_rows, Phase5NormalizationComponentMetadata,
    Phase5NormalizationTableRow,
};
#[cfg(feature = "stwo-backend")]
pub use normalization_prover::{
    load_phase10_shared_normalization_lookup_proof, load_phase5_normalization_lookup_proof,
    prove_phase10_shared_normalization_lookup_envelope, prove_phase5_normalization_lookup_demo,
    prove_phase5_normalization_lookup_demo_envelope,
    save_phase10_shared_normalization_lookup_proof, save_phase5_normalization_lookup_proof,
    verify_phase10_shared_normalization_lookup_envelope, verify_phase5_normalization_lookup_demo,
    verify_phase5_normalization_lookup_demo_envelope,
    Phase10SharedNormalizationLookupProofEnvelope, Phase5NormalizationLookupProofEnvelope,
    STWO_NORMALIZATION_PROOF_VERSION_PHASE5, STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5,
    STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5, STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10,
    STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10,
    STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
};
#[cfg(feature = "stwo-backend")]
pub use recursion::{
    commit_phase29_recursive_compression_input_contract,
    commit_phase31_recursive_compression_decode_boundary_manifest,
    commit_phase32_recursive_compression_statement_contract,
    commit_phase33_recursive_compression_public_input_manifest,
    commit_phase34_recursive_compression_shared_lookup_manifest,
    commit_phase35_recursive_compression_target_manifest,
    commit_phase36_recursive_verifier_harness_receipt,
    commit_phase37_recursive_artifact_chain_harness_receipt,
    commit_phase38_paper3_composition_prototype, commit_phase41_boundary_translation_witness,
    commit_phase42_boundary_history_equivalence_witness, commit_phase43_history_replay_trace,
    commit_phase44d_recursive_verifier_public_output_aggregation,
    commit_phase44d_recursive_verifier_public_output_handoff,
    commit_phase45_recursive_verifier_public_input_bridge,
    commit_phase45_recursive_verifier_public_inputs, commit_phase46_stwo_proof_adapter_receipt,
    commit_phase47_proof_commitment_roots, commit_phase47_recursive_verifier_wrapper_candidate,
    commit_phase48_recursive_proof_wrapper_attempt,
    commit_phase49_layerwise_tensor_claim_propagation_contract, commit_phase50_layer_io_claim,
    commit_phase50_tensor_commitment_claim, commit_phase51_first_layer_relation_claim,
    commit_phase52_layer_endpoint_anchoring_claim, commit_phase52_tensor_endpoint_evaluation_claim,
    commit_phase53_first_layer_relation_benchmark_claim,
    commit_phase54_first_layer_sumcheck_skeleton_claim, commit_phase54_parameter_opening_skeleton,
    commit_phase54_sumcheck_component_skeleton,
    commit_phase55_first_layer_compression_effectiveness_claim,
    commit_phase56_executable_sumcheck_component_proof,
    commit_phase56_first_layer_executable_sumcheck_claim, commit_phase56_round_polynomial,
    commit_phase57_first_layer_mle_opening_verifier_claim,
    commit_phase57_mle_opening_verification_receipt,
    commit_phase58_first_layer_witness_pcs_opening_claim, commit_phase58_witness_bound_pcs_opening,
    commit_phase59_first_layer_relation_witness_binding_claim,
    commit_phase59_relation_witness_component_binding,
    commit_phase59_relation_witness_opening_binding,
    commit_phase60_first_layer_runtime_relation_witness_claim,
    commit_phase60_runtime_tensor_witness,
    commit_phase61_first_layer_runtime_witness_pcs_replacement_claim,
    commit_phase61_runtime_witness_pcs_replacement_opening,
    commit_phase62_proof_carrying_state_continuity_claim,
    commit_phase62_proof_carrying_state_step_envelope,
    load_phase29_recursive_compression_input_contract,
    load_phase31_recursive_compression_decode_boundary_manifest,
    load_phase32_recursive_compression_statement_contract,
    load_phase33_recursive_compression_public_input_manifest,
    load_phase34_recursive_compression_shared_lookup_manifest,
    load_phase35_recursive_compression_target_manifest,
    load_phase36_recursive_verifier_harness_receipt,
    load_phase37_recursive_artifact_chain_harness_receipt,
    load_phase38_paper3_composition_prototype, load_phase41_boundary_translation_witness,
    load_phase41_boundary_translation_witness_against_sources,
    load_phase42_boundary_history_equivalence_witness,
    load_phase42_boundary_history_equivalence_witness_against_sources,
    load_phase42_boundary_preimage_evidence,
    load_phase42_boundary_preimage_evidence_against_sources, load_phase43_history_replay_trace,
    load_phase43_history_replay_trace_against_sources,
    parse_phase29_recursive_compression_input_contract_json,
    parse_phase31_recursive_compression_decode_boundary_manifest_json,
    parse_phase32_recursive_compression_statement_contract_json,
    parse_phase33_recursive_compression_public_input_manifest_json,
    parse_phase34_recursive_compression_shared_lookup_manifest_json,
    parse_phase35_recursive_compression_target_manifest_json,
    parse_phase36_recursive_verifier_harness_receipt_json,
    parse_phase37_recursive_artifact_chain_harness_receipt_json,
    parse_phase38_paper3_composition_prototype_json,
    parse_phase41_boundary_translation_witness_json,
    parse_phase41_boundary_translation_witness_json_against_sources,
    parse_phase42_boundary_history_equivalence_witness_json,
    parse_phase42_boundary_history_equivalence_witness_json_against_sources,
    parse_phase42_boundary_preimage_evidence_json,
    parse_phase42_boundary_preimage_evidence_json_against_sources,
    parse_phase43_history_replay_trace_json,
    parse_phase43_history_replay_trace_json_against_sources,
    phase29_prepare_recursive_compression_input_contract,
    phase29_prepare_recursive_compression_input_contract_from_proof_checked_phase28,
    phase31_prepare_recursive_compression_decode_boundary_manifest,
    phase32_prepare_recursive_compression_statement_contract,
    phase33_prepare_recursive_compression_public_input_manifest,
    phase34_prepare_recursive_compression_shared_lookup_manifest,
    phase35_prepare_recursive_compression_target_manifest,
    phase36_prepare_recursive_verifier_harness_receipt,
    phase37_prepare_recursive_artifact_chain_harness_receipt,
    phase38_prepare_paper3_composition_prototype, phase41_prepare_boundary_translation_witness,
    phase42_prepare_boundary_history_equivalence_witness,
    phase42_prepare_boundary_preimage_evidence, phase43_prepare_history_replay_trace,
    phase44d_prepare_recursive_verifier_public_output_aggregation,
    phase44d_prepare_recursive_verifier_public_output_handoff,
    phase45_prepare_recursive_verifier_public_input_bridge,
    phase46_prepare_stwo_proof_adapter_receipt,
    phase47_prepare_recursive_verifier_wrapper_candidate,
    phase48_prepare_recursive_proof_wrapper_attempt,
    phase49_prepare_layerwise_tensor_claim_propagation_contract, phase50_prepare_layer_io_claim,
    phase50_prepare_tensor_commitment_claim, phase51_prepare_first_layer_relation_claim,
    phase52_prepare_layer_endpoint_anchoring_claim,
    phase52_prepare_tensor_endpoint_evaluation_claim,
    phase53_prepare_first_layer_relation_benchmark_claim,
    phase54_prepare_first_layer_sumcheck_skeleton_claim,
    phase55_prepare_first_layer_compression_effectiveness_claim,
    phase56_prepare_first_layer_executable_sumcheck_claim,
    phase57_prepare_first_layer_mle_opening_verifier_claim,
    phase58_prepare_first_layer_witness_pcs_opening_claim,
    phase59_prepare_first_layer_relation_witness_binding_claim,
    phase60_prepare_first_layer_runtime_relation_witness_claim,
    phase61_prepare_first_layer_runtime_witness_pcs_replacement_claim,
    phase62_prepare_proof_carrying_state_continuity_claim,
    verify_phase29_recursive_compression_input_contract,
    verify_phase31_recursive_compression_decode_boundary_manifest,
    verify_phase31_recursive_compression_decode_boundary_manifest_against_sources,
    verify_phase32_recursive_compression_statement_contract,
    verify_phase32_recursive_compression_statement_contract_against_phase31,
    verify_phase33_recursive_compression_public_input_manifest,
    verify_phase33_recursive_compression_public_input_manifest_against_phase32,
    verify_phase34_recursive_compression_shared_lookup_manifest,
    verify_phase34_recursive_compression_shared_lookup_manifest_against_sources,
    verify_phase35_recursive_compression_target_manifest,
    verify_phase35_recursive_compression_target_manifest_against_sources,
    verify_phase36_recursive_verifier_harness_receipt,
    verify_phase36_recursive_verifier_harness_receipt_against_sources,
    verify_phase37_recursive_artifact_chain_harness_receipt,
    verify_phase37_recursive_artifact_chain_harness_receipt_against_sources,
    verify_phase38_paper3_composition_prototype, verify_phase41_boundary_translation_witness,
    verify_phase41_boundary_translation_witness_against_sources,
    verify_phase42_boundary_history_equivalence_witness,
    verify_phase42_boundary_history_equivalence_witness_against_sources,
    verify_phase42_boundary_preimage_evidence,
    verify_phase42_boundary_preimage_evidence_against_sources, verify_phase43_history_replay_trace,
    verify_phase43_history_replay_trace_against_sources,
    verify_phase44d_recursive_verifier_public_output_aggregation,
    verify_phase44d_recursive_verifier_public_output_handoff,
    verify_phase44d_recursive_verifier_public_output_handoff_against_boundary,
    verify_phase45_recursive_verifier_public_input_bridge,
    verify_phase45_recursive_verifier_public_input_bridge_against_sources,
    verify_phase46_stwo_proof_adapter_receipt,
    verify_phase46_stwo_proof_adapter_receipt_against_sources,
    verify_phase47_recursive_verifier_wrapper_candidate,
    verify_phase47_recursive_verifier_wrapper_candidate_against_phase46,
    verify_phase48_recursive_proof_wrapper_attempt,
    verify_phase48_recursive_proof_wrapper_attempt_against_phase47,
    verify_phase49_layerwise_tensor_claim_propagation_contract,
    verify_phase49_layerwise_tensor_claim_propagation_contract_against_phase48,
    verify_phase50_layer_io_claim, verify_phase50_layer_io_claim_against_phase49,
    verify_phase50_tensor_commitment_claim, verify_phase51_first_layer_relation_claim,
    verify_phase51_first_layer_relation_claim_against_phase50,
    verify_phase52_layer_endpoint_anchoring_claim,
    verify_phase52_layer_endpoint_anchoring_claim_against_phase51,
    verify_phase52_tensor_endpoint_evaluation_claim,
    verify_phase53_first_layer_relation_benchmark_claim,
    verify_phase53_first_layer_relation_benchmark_claim_against_phase52,
    verify_phase54_first_layer_sumcheck_skeleton_claim,
    verify_phase54_first_layer_sumcheck_skeleton_claim_against_phase53,
    verify_phase54_parameter_opening_skeleton, verify_phase54_sumcheck_component_skeleton,
    verify_phase55_first_layer_compression_effectiveness_claim,
    verify_phase55_first_layer_compression_effectiveness_claim_against_phase54,
    verify_phase56_executable_sumcheck_component_proof,
    verify_phase56_first_layer_executable_sumcheck_claim,
    verify_phase56_first_layer_executable_sumcheck_claim_against_phase54,
    verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56,
    verify_phase57_mle_opening_verification_receipt,
    verify_phase58_first_layer_witness_pcs_opening_claim,
    verify_phase58_first_layer_witness_pcs_opening_claim_against_phase57,
    verify_phase58_witness_bound_pcs_opening,
    verify_phase59_first_layer_relation_witness_binding_claim,
    verify_phase59_first_layer_relation_witness_binding_claim_against_phase58,
    verify_phase59_relation_witness_component_binding,
    verify_phase59_relation_witness_opening_binding,
    verify_phase60_first_layer_runtime_relation_witness_claim,
    verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59,
    verify_phase60_runtime_tensor_witness,
    verify_phase61_first_layer_runtime_witness_pcs_replacement_claim,
    verify_phase61_first_layer_runtime_witness_pcs_replacement_claim_against_phase60,
    verify_phase61_runtime_witness_pcs_replacement_opening,
    verify_phase62_proof_carrying_state_continuity_claim,
    verify_phase62_proof_carrying_state_continuity_claim_against_phase61,
    verify_phase62_proof_carrying_state_step_envelope, Phase29RecursiveCompressionInputContract,
    Phase31RecursiveCompressionDecodeBoundaryManifest,
    Phase32RecursiveCompressionStatementContract, Phase33RecursiveCompressionPublicInputManifest,
    Phase34RecursiveCompressionSharedLookupManifest, Phase35RecursiveCompressionTargetManifest,
    Phase36RecursiveVerifierHarnessReceipt, Phase37RecursiveArtifactChainHarnessReceipt,
    Phase38Paper3CompositionPrototype, Phase38Paper3CompositionSegment,
    Phase38Paper3CompositionSource, Phase41BoundaryTranslationWitness,
    Phase41BoundaryTranslationWitnessArtifact, Phase42BoundaryHistoryEquivalenceWitness,
    Phase42BoundaryPreimageEvidence, Phase43HistoryReplayTrace, Phase43HistoryReplayTraceRow,
    Phase44DRecursiveVerifierPublicOutputAggregation, Phase44DRecursiveVerifierPublicOutputHandoff,
    Phase45RecursiveVerifierPublicInputBridge, Phase45RecursiveVerifierPublicInputLane,
    Phase46StwoProofAdapterReceipt, Phase47RecursiveVerifierWrapperCandidate,
    Phase48RecursiveProofWrapperAttempt, Phase49LayerwiseTensorClaimPropagationContract,
    Phase50LayerIoClaim, Phase50TensorCommitmentClaim, Phase51FirstLayerRelationClaim,
    Phase52LayerEndpointAnchoringClaim, Phase52TensorEndpointEvaluationClaim,
    Phase53FirstLayerRelationBenchmarkClaim, Phase54FirstLayerSumcheckSkeletonClaim,
    Phase54ParameterOpeningSkeleton, Phase54SumcheckComponentSkeleton,
    Phase55FirstLayerCompressionEffectivenessClaim, Phase56ExecutableSumcheckComponentProof,
    Phase56FirstLayerExecutableSumcheckClaim, Phase56RoundPolynomial,
    Phase57FirstLayerMleOpeningVerifierClaim, Phase57MleOpeningVerificationReceipt,
    Phase58FirstLayerWitnessPcsOpeningClaim, Phase58WitnessBoundPcsOpening,
    Phase59FirstLayerRelationWitnessBindingClaim, Phase59RelationWitnessComponentBinding,
    Phase59RelationWitnessOpeningBinding, Phase60FirstLayerRuntimeRelationWitnessClaim,
    Phase60RuntimeTensorWitness, Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
    Phase62ProofCarryingStateContinuityClaim, Phase62ProofCarryingStateStepEnvelope,
    STWO_BOUNDARY_HISTORY_EQUIVALENCE_RELATION_PHASE42,
    STWO_BOUNDARY_HISTORY_EQUIVALENCE_RULE_PHASE42,
    STWO_BOUNDARY_HISTORY_EQUIVALENCE_WITNESS_VERSION_PHASE42,
    STWO_BOUNDARY_PREIMAGE_EVIDENCE_VERSION_PHASE42, STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
    STWO_BOUNDARY_PREIMAGE_RELATION_PHASE42, STWO_BOUNDARY_TRANSLATION_RULE_PHASE41,
    STWO_BOUNDARY_TRANSLATION_WITNESS_SCOPE_PHASE41,
    STWO_BOUNDARY_TRANSLATION_WITNESS_VERSION_PHASE41,
    STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_SCOPE_PHASE55,
    STWO_FIRST_LAYER_COMPRESSION_EFFECTIVENESS_CLAIM_VERSION_PHASE55,
    STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_SCOPE_PHASE56,
    STWO_FIRST_LAYER_EXECUTABLE_SUMCHECK_CLAIM_VERSION_PHASE56,
    STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_SCOPE_PHASE57,
    STWO_FIRST_LAYER_MLE_OPENING_VERIFIER_CLAIM_VERSION_PHASE57,
    STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_SCOPE_PHASE53,
    STWO_FIRST_LAYER_RELATION_BENCHMARK_CLAIM_VERSION_PHASE53,
    STWO_FIRST_LAYER_RELATION_CLAIM_SCOPE_PHASE51, STWO_FIRST_LAYER_RELATION_CLAIM_VERSION_PHASE51,
    STWO_FIRST_LAYER_RELATION_WITNESS_BINDING_CLAIM_SCOPE_PHASE59,
    STWO_FIRST_LAYER_RELATION_WITNESS_BINDING_CLAIM_VERSION_PHASE59,
    STWO_FIRST_LAYER_RUNTIME_RELATION_WITNESS_CLAIM_SCOPE_PHASE60,
    STWO_FIRST_LAYER_RUNTIME_RELATION_WITNESS_CLAIM_VERSION_PHASE60,
    STWO_FIRST_LAYER_RUNTIME_WITNESS_PCS_REPLACEMENT_CLAIM_SCOPE_PHASE61,
    STWO_FIRST_LAYER_RUNTIME_WITNESS_PCS_REPLACEMENT_CLAIM_VERSION_PHASE61,
    STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_SCOPE_PHASE54,
    STWO_FIRST_LAYER_SUMCHECK_SKELETON_CLAIM_VERSION_PHASE54,
    STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_SCOPE_PHASE58,
    STWO_FIRST_LAYER_WITNESS_PCS_OPENING_CLAIM_VERSION_PHASE58,
    STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43, STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43,
    STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43, STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_SCOPE_PHASE49,
    STWO_LAYERWISE_TENSOR_CLAIM_CONTRACT_VERSION_PHASE49,
    STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_SCOPE_PHASE52,
    STWO_LAYER_ENDPOINT_ANCHORING_CLAIM_VERSION_PHASE52, STWO_LAYER_IO_CLAIM_SCOPE_PHASE50,
    STWO_LAYER_IO_CLAIM_VERSION_PHASE50, STWO_PAPER3_COMPOSITION_PROTOTYPE_SCOPE_PHASE38,
    STWO_PAPER3_COMPOSITION_PROTOTYPE_VERSION_PHASE38,
    STWO_PROOF_CARRYING_STATE_CONTINUITY_CLAIM_SCOPE_PHASE62,
    STWO_PROOF_CARRYING_STATE_CONTINUITY_CLAIM_VERSION_PHASE62,
    STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37,
    STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37,
    STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31,
    STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
    STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33,
    STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33,
    STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34,
    STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34,
    STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32,
    STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32,
    STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35,
    STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35,
    STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_SCOPE_PHASE48,
    STWO_RECURSIVE_PROOF_WRAPPER_ATTEMPT_VERSION_PHASE48,
    STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_SCOPE_PHASE46,
    STWO_RECURSIVE_STWO_PROOF_ADAPTER_RECEIPT_VERSION_PHASE46,
    STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36,
    STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36,
    STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_SCOPE_PHASE45,
    STWO_RECURSIVE_VERIFIER_PUBLIC_INPUT_BRIDGE_VERSION_PHASE45,
    STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_SCOPE_PHASE44D,
    STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_AGGREGATION_VERSION_PHASE44D,
    STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_SCOPE_PHASE44D,
    STWO_RECURSIVE_VERIFIER_PUBLIC_OUTPUT_HANDOFF_VERSION_PHASE44D,
    STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_SCOPE_PHASE47,
    STWO_RECURSIVE_VERIFIER_WRAPPER_CANDIDATE_VERSION_PHASE47,
    STWO_TENSOR_COMMITMENT_CLAIM_SCOPE_PHASE50, STWO_TENSOR_COMMITMENT_CLAIM_VERSION_PHASE50,
    STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_SCOPE_PHASE52,
    STWO_TENSOR_ENDPOINT_EVALUATION_CLAIM_VERSION_PHASE52,
};
pub use recursion::{
    phase6_prepare_recursion_batch, Phase6RecursionBatchEntry, Phase6RecursionBatchManifest,
    STWO_RECURSION_BATCH_SCOPE_PHASE6, STWO_RECURSION_BATCH_VERSION_PHASE6,
};
#[cfg(feature = "stwo-backend")]
pub use shared_lookup_artifact::{
    commit_phase12_shared_lookup_rows, load_phase12_shared_lookup_artifact,
    save_phase12_shared_lookup_artifact, verify_phase12_shared_lookup_artifact,
    Phase12SharedLookupArtifact, Phase12StaticLookupTableCommitment,
    STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12, STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12,
    STWO_SHARED_STATIC_ACTIVATION_TABLE_ID_PHASE12,
    STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12,
    STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12,
    STWO_SHARED_STATIC_NORMALIZATION_TABLE_ID_PHASE12,
};

/// Backend version label used by the experimental Phase 2 S-two seam.
pub const STWO_BACKEND_VERSION_PHASE2: &str = "stwo-phase2";
/// Backend version label used by the current shipped-fixture `stwo` execution-proof path.
pub const STWO_BACKEND_VERSION_PHASE5: &str = "stwo-phase10-gemma-block-v4";
/// Backend version label used by the fixed-shape proof-carrying decoding demo family.
pub const STWO_BACKEND_VERSION_PHASE11: &str = "stwo-phase11-decoding-step-v1";
/// Backend version label used by the parameterized proof-carrying decoding family.
pub const STWO_BACKEND_VERSION_PHASE12: &str = "stwo-phase12-decoding-family-v9";
/// Cargo feature that enables the experimental S-two backend seam.
pub const STWO_BACKEND_FEATURE_NAME: &str = "stwo-backend";

/// Returns whether the binary was built with the experimental S-two backend feature.
pub fn is_enabled() -> bool {
    cfg!(feature = "stwo-backend")
}

/// Validates that a program fits the current Phase 2 S-two proof shape.
pub fn validate_phase2_proof_shape(
    program: &Program,
    attention_mode: &Attention2DMode,
) -> Result<()> {
    ensure_feature_enabled()?;

    if program.instructions().is_empty() {
        return Err(VmError::UnsupportedProof(
            "S-two backend Phase 2 does not accept empty programs".to_string(),
        ));
    }

    if !matches!(attention_mode, Attention2DMode::AverageHard) {
        return Err(VmError::UnsupportedProof(format!(
            "S-two backend Phase 2 supports only `average-hard` attention, got `{attention_mode}`"
        )));
    }

    layout::validate_phase2_instruction_subset(program)
}

/// Returns the placeholder error emitted by `prove-stark --backend stwo` in Phase 2.
pub fn phase2_placeholder_prove_error() -> VmError {
    if !is_enabled() {
        return feature_gate_error();
    }

    let seam = phase2_dependency_seam();
    VmError::UnsupportedProof(format!(
        "S-two backend Phase 2 adapter seam is present (official crates: {} {}, {} {}; modules: {}, {}), but proving is not implemented yet in binaries built without the `stwo-backend` feature; the feature-gated implementation now covers real proof paths for the shipped arithmetic fixtures plus a separate normalization lookup demo",
        seam.stwo_crate,
        seam.stwo_crate_version,
        seam.constraint_framework_crate,
        seam.constraint_framework_version,
        seam.adapter_module,
        seam.layout_module
    ))
}

/// Returns the placeholder error emitted by `verify-stark --backend stwo` in Phase 2.
pub fn phase2_placeholder_verify_error() -> VmError {
    if !is_enabled() {
        return feature_gate_error();
    }

    let seam = phase2_dependency_seam();
    VmError::UnsupportedProof(format!(
        "S-two backend Phase 2 adapter seam is present (official crates: {} {}, {} {}; modules: {}, {}), but verification is not implemented yet in binaries built without the `stwo-backend` feature; the feature-gated implementation now covers real proof paths for the shipped arithmetic fixtures plus a separate normalization lookup demo",
        seam.stwo_crate,
        seam.stwo_crate_version,
        seam.constraint_framework_crate,
        seam.constraint_framework_version,
        seam.adapter_module,
        seam.layout_module
    ))
}

fn ensure_feature_enabled() -> Result<()> {
    if is_enabled() {
        return Ok(());
    }

    Err(feature_gate_error())
}

fn feature_gate_error() -> VmError {
    VmError::UnsupportedProof(format!(
        "S-two backend requires building with `--features {STWO_BACKEND_FEATURE_NAME}`"
    ))
}
