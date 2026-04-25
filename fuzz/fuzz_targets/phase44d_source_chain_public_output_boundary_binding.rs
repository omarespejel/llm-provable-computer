#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    Phase43HistoryReplayProjectionCompactClaim,
    Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
};
use llm_provable_computer::stwo_backend::
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Phase44DBoundaryBindingInput {
    boundary: Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_claim: Phase43HistoryReplayProjectionCompactClaim,
}

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(input) = serde_json::from_str::<Phase44DBoundaryBindingInput>(json) else {
        return;
    };
    let _ = verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding(
        &input.boundary,
        &input.compact_claim,
    );
});
