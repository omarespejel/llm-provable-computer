#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    parse_phase36_recursive_verifier_harness_receipt_json,
    verify_phase36_recursive_verifier_harness_receipt,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(receipt) = parse_phase36_recursive_verifier_harness_receipt_json(json) else {
        return;
    };
    let _ = verify_phase36_recursive_verifier_harness_receipt(&receipt);
});
