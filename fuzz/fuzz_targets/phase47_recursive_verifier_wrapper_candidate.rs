#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    verify_phase47_recursive_verifier_wrapper_candidate, Phase47RecursiveVerifierWrapperCandidate,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(candidate) = serde_json::from_str::<Phase47RecursiveVerifierWrapperCandidate>(json) else {
        return;
    };
    let _ = verify_phase47_recursive_verifier_wrapper_candidate(&candidate);
});
