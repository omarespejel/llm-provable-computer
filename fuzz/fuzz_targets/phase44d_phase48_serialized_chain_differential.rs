#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    commit_phase44d_recursive_verifier_public_output_handoff,
    commit_phase45_recursive_verifier_public_input_bridge,
    commit_phase45_recursive_verifier_public_inputs, commit_phase46_stwo_proof_adapter_receipt,
    commit_phase47_recursive_verifier_wrapper_candidate,
    commit_phase48_recursive_proof_wrapper_attempt,
    emit_phase44d_history_replay_projection_source_chain_public_output_boundary,
    phase29_prepare_recursive_compression_input_contract, phase43_prepare_history_replay_trace,
    phase44d_prepare_recursive_verifier_public_output_handoff,
    phase45_prepare_recursive_verifier_public_input_bridge,
    phase46_prepare_stwo_proof_adapter_receipt,
    phase47_prepare_recursive_verifier_wrapper_candidate,
    phase48_prepare_recursive_proof_wrapper_attempt,
    prove_phase42_boundary_preimage_shared_proof_demo,
    prove_phase43_history_replay_projection_compact_claim_envelope,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding,
    verify_phase44d_recursive_verifier_public_output_handoff,
    verify_phase44d_recursive_verifier_public_output_handoff_against_boundary,
    verify_phase45_recursive_verifier_public_input_bridge,
    verify_phase45_recursive_verifier_public_input_bridge_against_sources,
    verify_phase46_stwo_proof_adapter_receipt, verify_phase46_stwo_proof_adapter_receipt_against_sources,
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
use std::sync::OnceLock;

#[derive(Clone)]
struct DifferentialFixture {
    compact_envelope: Phase43HistoryReplayProjectionCompactProofEnvelope,
    boundary: Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    handoff: Phase44DRecursiveVerifierPublicOutputHandoff,
    bridge: Phase45RecursiveVerifierPublicInputBridge,
    receipt: Phase46StwoProofAdapterReceipt,
    candidate: Phase47RecursiveVerifierWrapperCandidate,
    attempt: Phase48RecursiveProofWrapperAttempt,
}

fn hash32(hex: char) -> String {
    hex.to_string().repeat(64)
}

fn fixture() -> &'static DifferentialFixture {
    static FIXTURE: OnceLock<DifferentialFixture> = OnceLock::new();
    FIXTURE.get_or_init(|| {
        let (chain, phase28, phase30) =
            prove_phase42_boundary_preimage_shared_proof_demo().expect("build shared-proof demo");
        let contract = phase29_prepare_recursive_compression_input_contract(&phase28)
            .expect("prepare phase29 contract");
        let trace = phase43_prepare_history_replay_trace(&chain, &phase28, &contract, &phase30)
            .expect("prepare phase43 trace");
        let compact_envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove compact envelope");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit phase44d boundary");
        let handoff = phase44d_prepare_recursive_verifier_public_output_handoff(
            &boundary,
            &compact_envelope,
        )
        .expect("prepare phase44d handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare phase45 bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare phase46 receipt");
        let candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare phase47 candidate");
        let attempt = phase48_prepare_recursive_proof_wrapper_attempt(&candidate)
            .expect("prepare phase48 attempt");

        DifferentialFixture {
            compact_envelope,
            boundary,
            handoff,
            bridge,
            receipt,
            candidate,
            attempt,
        }
    })
}

fn deserialize_tampered<T: serde::Serialize + serde::de::DeserializeOwned>(artifact: &T) -> serde_json::Value {
    serde_json::to_value(artifact).expect("serialize accepted artifact")
}

fn boundary_case(variant: u8) {
    let fixture = fixture();
    let mut boundary_json = deserialize_tampered(&fixture.boundary);
    match variant % 2 {
        0 => {
            boundary_json["verifier_requires_phase43_trace"] = serde_json::json!(true);
            boundary_json["verifier_requires_phase30_manifest"] = serde_json::json!(true);
        }
        _ => {
            let total_steps = boundary_json["source_emission_public_output"]["source_emission"]
                ["source_claim"]["total_steps"]
                .as_u64()
                .expect("total_steps")
                + 1;
            boundary_json["source_emission_public_output"]["source_emission"]["source_claim"]
                ["total_steps"] = serde_json::json!(total_steps);
        }
    }
    let boundary: Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary =
        serde_json::from_value(boundary_json).expect("deserialize tampered boundary");

    assert!(verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
        &boundary,
        &fixture.compact_envelope,
    )
    .is_err());
    assert!(verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding(
        &boundary,
        &fixture.compact_envelope.claim,
    )
    .is_err());
}

fn handoff_case(variant: u8) {
    let fixture = fixture();
    let mut handoff_json = deserialize_tampered(&fixture.handoff);
    let handoff: Phase44DRecursiveVerifierPublicOutputHandoff = match variant % 2 {
        0 => {
            handoff_json["verifier_requires_phase43_trace"] = serde_json::json!(true);
            handoff_json["verifier_requires_phase30_manifest"] = serde_json::json!(true);
            let mut handoff: Phase44DRecursiveVerifierPublicOutputHandoff =
                serde_json::from_value(handoff_json).expect("deserialize tampered handoff");
            handoff.handoff_commitment = commit_phase44d_recursive_verifier_public_output_handoff(&handoff)
                .expect("recommit tampered handoff");
            handoff
        }
        _ => {
            handoff_json["source_chain_public_output_boundary_commitment"] =
                serde_json::json!(hash32('b'));
            serde_json::from_value(handoff_json).expect("deserialize stale handoff")
        }
    };

    assert!(verify_phase44d_recursive_verifier_public_output_handoff(&handoff).is_err());
    assert!(verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
        &handoff,
        &fixture.boundary,
        &fixture.compact_envelope,
    )
    .is_err());
}

fn bridge_case(variant: u8) {
    let fixture = fixture();
    let mut bridge_json = deserialize_tampered(&fixture.bridge);
    let bridge: Phase45RecursiveVerifierPublicInputBridge = match variant % 2 {
        0 => {
            bridge_json["verifier_requires_phase43_trace"] = serde_json::json!(true);
            bridge_json["verifier_requires_phase30_manifest"] = serde_json::json!(true);
            let mut bridge: Phase45RecursiveVerifierPublicInputBridge =
                serde_json::from_value(bridge_json).expect("deserialize tampered bridge");
            bridge.bridge_commitment =
                commit_phase45_recursive_verifier_public_input_bridge(&bridge)
                    .expect("recommit tampered bridge");
            bridge
        }
        _ => {
            let lanes = bridge_json["ordered_public_input_lanes"]
                .as_array_mut()
                .expect("ordered lanes");
            if lanes.len() >= 2 {
                lanes.swap(0, 1);
            }
            let mut bridge: Phase45RecursiveVerifierPublicInputBridge =
                serde_json::from_value(bridge_json).expect("deserialize reordered bridge");
            bridge.ordered_public_inputs_commitment =
                commit_phase45_recursive_verifier_public_inputs(&bridge.ordered_public_input_lanes)
                    .expect("recommit reordered public inputs");
            bridge.bridge_commitment =
                commit_phase45_recursive_verifier_public_input_bridge(&bridge)
                    .expect("recommit reordered bridge");
            bridge
        }
    };

    assert!(verify_phase45_recursive_verifier_public_input_bridge(&bridge).is_err());
    assert!(verify_phase45_recursive_verifier_public_input_bridge_against_sources(
        &bridge,
        &fixture.boundary,
        &fixture.compact_envelope,
        &fixture.handoff,
    )
    .is_err());
}

fn receipt_case(variant: u8) {
    let fixture = fixture();
    let mut receipt_json = deserialize_tampered(&fixture.receipt);
    let receipt: Phase46StwoProofAdapterReceipt = match variant % 2 {
        0 => {
            receipt_json["recursive_verification_claimed"] = serde_json::json!(true);
            receipt_json["cryptographic_compression_claimed"] = serde_json::json!(true);
            let mut receipt: Phase46StwoProofAdapterReceipt =
                serde_json::from_value(receipt_json).expect("deserialize tampered receipt");
            receipt.adapter_receipt_commitment = commit_phase46_stwo_proof_adapter_receipt(&receipt)
                .expect("recommit tampered receipt");
            receipt
        }
        _ => {
            receipt_json["terminal_boundary_public_logup_sum_limbs"][0] = serde_json::json!(1);
            let mut receipt: Phase46StwoProofAdapterReceipt =
                serde_json::from_value(receipt_json).expect("deserialize tampered receipt sums");
            receipt.adapter_receipt_commitment = commit_phase46_stwo_proof_adapter_receipt(&receipt)
                .expect("recommit tampered receipt sums");
            receipt
        }
    };

    assert!(verify_phase46_stwo_proof_adapter_receipt(&receipt).is_err());
    assert!(verify_phase46_stwo_proof_adapter_receipt_against_sources(
        &receipt,
        &fixture.bridge,
        &fixture.boundary,
        &fixture.compact_envelope,
        &fixture.handoff,
    )
    .is_err());
}

fn candidate_case(variant: u8) {
    let fixture = fixture();
    let mut candidate_json = deserialize_tampered(&fixture.candidate);
    let candidate: Phase47RecursiveVerifierWrapperCandidate = match variant % 2 {
        0 => {
            candidate_json["wrapper_requires_phase43_trace"] = serde_json::json!(true);
            candidate_json["wrapper_requires_phase30_manifest"] = serde_json::json!(true);
            let mut candidate: Phase47RecursiveVerifierWrapperCandidate = serde_json::from_value(candidate_json)
                .expect("deserialize tampered candidate");
            candidate.candidate_commitment =
                commit_phase47_recursive_verifier_wrapper_candidate(&candidate)
                    .expect("recommit tampered candidate");
            candidate
        }
        _ => {
            candidate_json["recursive_proof_available"] = serde_json::json!(true);
            candidate_json["recursive_verification_claimed"] = serde_json::json!(true);
            candidate_json["cryptographic_compression_claimed"] = serde_json::json!(true);
            let mut candidate: Phase47RecursiveVerifierWrapperCandidate = serde_json::from_value(candidate_json)
                .expect("deserialize false-claim candidate");
            candidate.candidate_commitment =
                commit_phase47_recursive_verifier_wrapper_candidate(&candidate)
                    .expect("recommit false-claim candidate");
            candidate
        }
    };

    assert!(verify_phase47_recursive_verifier_wrapper_candidate(&candidate).is_err());
    assert!(verify_phase47_recursive_verifier_wrapper_candidate_against_phase46(
        &candidate,
        &fixture.receipt,
    )
    .is_err());
}

fn attempt_case(variant: u8) {
    let fixture = fixture();
    let mut attempt_json = deserialize_tampered(&fixture.attempt);
    let attempt: Phase48RecursiveProofWrapperAttempt = match variant % 2 {
        0 => {
            attempt_json["actual_recursive_wrapper_available"] = serde_json::json!(true);
            attempt_json["recursive_proof_constructed"] = serde_json::json!(true);
            attempt_json["recursive_verification_claimed"] = serde_json::json!(true);
            attempt_json["cryptographic_compression_claimed"] = serde_json::json!(true);
            let mut attempt: Phase48RecursiveProofWrapperAttempt = serde_json::from_value(attempt_json)
                .expect("deserialize false-claim attempt");
            attempt.attempt_commitment = commit_phase48_recursive_proof_wrapper_attempt(&attempt)
                .expect("recommit false-claim attempt");
            attempt
        }
        _ => {
            attempt_json["blocking_reasons"] = serde_json::json!(["generic wrapper blocker"]);
            let mut attempt: Phase48RecursiveProofWrapperAttempt = serde_json::from_value(attempt_json)
                .expect("deserialize blocker-drift attempt");
            attempt.attempt_commitment = commit_phase48_recursive_proof_wrapper_attempt(&attempt)
                .expect("recommit blocker-drift attempt");
            attempt
        }
    };

    assert!(verify_phase48_recursive_proof_wrapper_attempt(&attempt).is_err());
    assert!(verify_phase48_recursive_proof_wrapper_attempt_against_phase47(
        &attempt,
        &fixture.candidate,
    )
    .is_err());
}

fuzz_target!(|data: &[u8]| {
    let selector = data.first().copied().unwrap_or(0);
    let variant = data.get(1).copied().unwrap_or(0);

    match selector % 6 {
        0 => boundary_case(variant),
        1 => handoff_case(variant),
        2 => bridge_case(variant),
        3 => receipt_case(variant),
        4 => candidate_case(variant),
        _ => attempt_case(variant),
    }
});
