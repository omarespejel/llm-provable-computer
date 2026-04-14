#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    parse_phase29_recursive_compression_input_contract_json,
    verify_phase29_recursive_compression_input_contract,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 2 * 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(contract) = parse_phase29_recursive_compression_input_contract_json(json) else {
        return;
    };
    let _ = verify_phase29_recursive_compression_input_contract(&contract);
});
