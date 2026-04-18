#![no_main]

use libfuzzer_sys::fuzz_target;
use llm_provable_computer::{
    parse_phase35_recursive_compression_target_manifest_json,
    verify_phase35_recursive_compression_target_manifest,
};

fuzz_target!(|data: &[u8]| {
    if data.len() > 1024 * 1024 {
        return;
    }
    let Ok(json) = std::str::from_utf8(data) else {
        return;
    };
    let Ok(manifest) = parse_phase35_recursive_compression_target_manifest_json(json) else {
        return;
    };
    let _ = verify_phase35_recursive_compression_target_manifest(&manifest);
});
