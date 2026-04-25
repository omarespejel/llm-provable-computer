#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    verify_phase46_stwo_proof_adapter_receipt, Phase46StwoProofAdapterReceipt,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(receipt) = serde_json::from_str::<Phase46StwoProofAdapterReceipt>(json) else {
        return;
    };
    let _ = verify_phase46_stwo_proof_adapter_receipt(&receipt);
});
