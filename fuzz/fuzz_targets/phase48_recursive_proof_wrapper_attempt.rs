#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    verify_phase48_recursive_proof_wrapper_attempt, Phase48RecursiveProofWrapperAttempt,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(attempt) = serde_json::from_str::<Phase48RecursiveProofWrapperAttempt>(json) else {
        return;
    };
    let _ = verify_phase48_recursive_proof_wrapper_attempt(&attempt);
});
