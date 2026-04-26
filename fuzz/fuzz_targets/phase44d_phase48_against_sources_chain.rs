#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding,
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
    Phase43HistoryReplayProjectionCompactProofEnvelope,
    Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    Phase44DRecursiveVerifierPublicOutputHandoff, Phase45RecursiveVerifierPublicInputBridge,
    Phase46StwoProofAdapterReceipt, Phase47RecursiveVerifierWrapperCandidate,
    Phase48RecursiveProofWrapperAttempt,
};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Phase44DPhase48AgainstSourcesChainInput {
    compact_envelope: Phase43HistoryReplayProjectionCompactProofEnvelope,
    boundary: Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    handoff: Phase44DRecursiveVerifierPublicOutputHandoff,
    bridge: Phase45RecursiveVerifierPublicInputBridge,
    receipt: Phase46StwoProofAdapterReceipt,
    candidate: Phase47RecursiveVerifierWrapperCandidate,
    attempt: Phase48RecursiveProofWrapperAttempt,
}

fuzz_target!(|data: &[u8]| {
    if data.len() > 8 * 1024 * 1024 {
        return;
    }
    let Ok(input) = serde_json::from_slice::<Phase44DPhase48AgainstSourcesChainInput>(data) else {
        return;
    };

    let _ = verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
        &input.boundary,
        &input.compact_envelope,
    );
    let _ = verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding(
        &input.boundary,
        &input.compact_envelope.claim,
    );
    let _ = verify_phase44d_recursive_verifier_public_output_handoff(&input.handoff);
    let _ = verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
        &input.handoff,
        &input.boundary,
        &input.compact_envelope,
    );
    let _ = verify_phase45_recursive_verifier_public_input_bridge(&input.bridge);
    let _ = verify_phase45_recursive_verifier_public_input_bridge_against_sources(
        &input.bridge,
        &input.boundary,
        &input.compact_envelope,
        &input.handoff,
    );
    let _ = verify_phase46_stwo_proof_adapter_receipt(&input.receipt);
    let _ = verify_phase46_stwo_proof_adapter_receipt_against_sources(
        &input.receipt,
        &input.bridge,
        &input.boundary,
        &input.compact_envelope,
        &input.handoff,
    );
    let _ = verify_phase47_recursive_verifier_wrapper_candidate(&input.candidate);
    let _ = verify_phase47_recursive_verifier_wrapper_candidate_against_phase46(
        &input.candidate,
        &input.receipt,
    );
    let _ = verify_phase48_recursive_proof_wrapper_attempt(&input.attempt);
    let _ = verify_phase48_recursive_proof_wrapper_attempt_against_phase47(
        &input.attempt,
        &input.candidate,
    );
});
