#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    verify_phase45_recursive_verifier_public_input_bridge, Phase45RecursiveVerifierPublicInputBridge,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(bridge) = serde_json::from_str::<Phase45RecursiveVerifierPublicInputBridge>(json) else {
        return;
    };
    let _ = verify_phase45_recursive_verifier_public_input_bridge(&bridge);
});
