#[cfg(feature = "stwo-backend")]
use std::ffi::OsString;
#[cfg(feature = "stwo-backend")]
use std::fs;
#[cfg(feature = "stwo-backend")]
use std::io::Read;
#[cfg(feature = "stwo-backend")]
use std::path::{Path, PathBuf};
use std::process::ExitCode;
#[cfg(feature = "stwo-backend")]
use std::time::Instant;

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend as backend;
#[cfg(feature = "stwo-backend")]
use serde_json::Value;
#[cfg(feature = "stwo-backend")]
use sha2::{Digest, Sha256};

#[cfg(feature = "stwo-backend")]
const SCHEMA: &str = "zkai-attention-kv-stwo-softmax-table-median-timing-cli-v1";
#[cfg(feature = "stwo-backend")]
const ROUTE_FAMILY: &str = "stwo_softmax_table_source_sidecar_fused_route_family";
#[cfg(feature = "stwo-backend")]
const TIMING_POLICY: &str =
    "median_of_5_existing_typed_envelope_verifier_runs_microsecond_capture_engineering_only";
#[cfg(feature = "stwo-backend")]
const TIMING_SCOPE: &str =
    "existing_envelope_loaded_once_then_typed_stwo_verify_function_timed_in_process";
#[cfg(feature = "stwo-backend")]
const CLAIM_BOUNDARY: &str =
    "ENGINEERING_LOCAL_VERIFY_EXISTING_ENVELOPE_TIMING_FOR_STWO_SOFTMAX_TABLE_ROUTE_FAMILY_NOT_PUBLIC_BENCHMARK_NOT_PROVER_TIMING_NOT_CARGO_OR_BUILD_TIMING_NOT_REAL_SOFTMAX_NOT_FULL_INFERENCE_NOT_RECURSION_OR_PCD";
#[cfg(feature = "stwo-backend")]
const DECISION: &str = "GO_ENGINEERING_LOCAL_MEDIAN_OF_5_VERIFY_TIMING_HARNESS";
#[cfg(feature = "stwo-backend")]
const MAX_ENVELOPE_JSON_BYTES: usize = 16 * 1024 * 1024;
#[cfg(feature = "stwo-backend")]
const DEFAULT_RUNS: usize = 5;
#[cfg(feature = "stwo-backend")]
const VALIDATION_COMMANDS: [&str; 4] = [
    "cargo +nightly-2025-07-14 run --locked --release --features stwo-backend --bin zkai_attention_kv_stwo_softmax_table_timing -- --evidence-dir docs/engineering/evidence --runs 5",
    "python3 scripts/zkai_attention_kv_stwo_median_timing_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-softmax-table-median-timing-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_median_timing_gate",
    "cargo +nightly-2025-07-14 test --locked --release --features stwo-backend --bin zkai_attention_kv_stwo_softmax_table_timing",
];
#[cfg(feature = "stwo-backend")]
const NON_CLAIMS: [&str; 7] = [
    "not prover timing",
    "not cargo or build timing",
    "not subprocess timing",
    "not a public benchmark",
    "not exact real-valued Softmax",
    "not full inference",
    "not recursion or PCD",
];

#[cfg(feature = "stwo-backend")]
type TimedVerifier = fn(&[u8], usize) -> Result<Vec<u64>, String>;

#[cfg(feature = "stwo-backend")]
#[derive(Clone, Copy)]
struct Route {
    profile_id: &'static str,
    axis_role: &'static str,
    key_width: usize,
    value_width: usize,
    head_count: usize,
    steps_per_head: usize,
    role: &'static str,
    evidence_relative_path: &'static str,
    timed_verifier: TimedVerifier,
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug)]
struct Config {
    evidence_dir: PathBuf,
    runs: usize,
}

#[cfg(feature = "stwo-backend")]
macro_rules! timed_verifier {
    ($fn_name:ident, $parser:path, $verifier:path) => {
        fn $fn_name(raw: &[u8], runs: usize) -> Result<Vec<u64>, String> {
            let envelope = $parser(raw).map_err(|error| {
                format!("failed to parse {} envelope: {error}", stringify!($fn_name))
            })?;
            let mut timings = Vec::with_capacity(runs);
            for _ in 0..runs {
                let started = Instant::now();
                let verified = $verifier(&envelope).map_err(|error| {
                    format!("{} verifier failed: {error}", stringify!($fn_name))
                })?;
                let elapsed = u64::try_from(started.elapsed().as_micros())
                    .map_err(|_| format!("{} verifier timing overflow", stringify!($fn_name)))?;
                if !verified {
                    return Err(format!("{} verifier returned false", stringify!($fn_name)));
                }
                timings.push(elapsed);
            }
            Ok(timings)
        }
    };
}

#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d8_source,
    backend::zkai_attention_kv_native_d8_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d8_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d8_sidecar,
    backend::zkai_attention_kv_native_d8_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d8_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d8_fused,
    backend::zkai_attention_kv_native_d8_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d8_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_source,
    backend::zkai_attention_kv_native_d16_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_sidecar,
    backend::zkai_attention_kv_native_d16_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_fused,
    backend::zkai_attention_kv_native_d16_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d32_source,
    backend::zkai_attention_kv_native_d32_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d32_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d32_sidecar,
    backend::zkai_attention_kv_native_d32_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d32_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d32_fused,
    backend::zkai_attention_kv_native_d32_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d32_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_source,
    backend::zkai_attention_kv_native_two_head_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_sidecar,
    backend::zkai_attention_kv_native_two_head_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_fused,
    backend::zkai_attention_kv_native_two_head_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_four_head_source,
    backend::zkai_attention_kv_native_four_head_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_four_head_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_four_head_sidecar,
    backend::zkai_attention_kv_native_four_head_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_four_head_fused,
    backend::zkai_attention_kv_native_four_head_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_eight_head_source,
    backend::zkai_attention_kv_native_eight_head_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_eight_head_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_eight_head_sidecar,
    backend::zkai_attention_kv_native_eight_head_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_eight_head_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_eight_head_fused,
    backend::zkai_attention_kv_native_eight_head_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_eight_head_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_sixteen_head_source,
    backend::zkai_attention_kv_native_sixteen_head_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_sixteen_head_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_sixteen_head_sidecar,
    backend::zkai_attention_kv_native_sixteen_head_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_sixteen_head_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_sixteen_head_fused,
    backend::zkai_attention_kv_native_sixteen_head_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_sixteen_head_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_longseq_source,
    backend::zkai_attention_kv_native_two_head_longseq_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_longseq_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_longseq_sidecar,
    backend::zkai_attention_kv_native_two_head_longseq_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_longseq_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_longseq_fused,
    backend::zkai_attention_kv_native_two_head_longseq_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_longseq_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_seq32_source,
    backend::zkai_attention_kv_native_two_head_seq32_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_seq32_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_seq32_sidecar,
    backend::zkai_attention_kv_native_two_head_seq32_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_seq32_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_two_head_seq32_fused,
    backend::zkai_attention_kv_native_two_head_seq32_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_two_head_seq32_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_two_head_source,
    backend::zkai_attention_kv_native_d16_two_head_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_two_head_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_two_head_sidecar,
    backend::zkai_attention_kv_native_d16_two_head_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_two_head_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_two_head_fused,
    backend::zkai_attention_kv_native_d16_two_head_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_two_head_fused_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_two_head_longseq_source,
    backend::zkai_attention_kv_native_d16_two_head_longseq_bounded_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_two_head_longseq_bounded_softmax_table_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_two_head_longseq_sidecar,
    backend::zkai_attention_kv_native_d16_two_head_longseq_softmax_table_lookup_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_two_head_longseq_softmax_table_lookup_envelope
);
#[cfg(feature = "stwo-backend")]
timed_verifier!(
    time_d16_two_head_longseq_fused,
    backend::zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope_from_json_slice,
    backend::verify_zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope
);

#[cfg(feature = "stwo-backend")]
const ROUTES: &[Route] = &[
    route("d8_single_head_seq8", "baseline", 8, 8, 1, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json", time_d8_source),
    route("d8_single_head_seq8", "baseline", 8, 8, 1, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_d8_sidecar),
    route("d8_single_head_seq8", "baseline", 8, 8, 1, 8, "fused", "zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json", time_d8_fused),
    route("d16_single_head_seq8", "width_axis", 16, 16, 1, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json", time_d16_source),
    route("d16_single_head_seq8", "width_axis", 16, 16, 1, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_d16_sidecar),
    route("d16_single_head_seq8", "width_axis", 16, 16, 1, 8, "fused", "zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json", time_d16_fused),
    route("d32_single_head_seq8", "width_axis_extension", 32, 32, 1, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-d32-bounded-softmax-table-proof-2026-05.envelope.json", time_d32_source),
    route("d32_single_head_seq8", "width_axis_extension", 32, 32, 1, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_d32_sidecar),
    route("d32_single_head_seq8", "width_axis_extension", 32, 32, 1, 8, "fused", "zkai-attention-kv-stwo-native-d32-fused-softmax-table-proof-2026-05.envelope.json", time_d32_fused),
    route("d8_two_head_seq8", "head_axis", 8, 8, 2, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json", time_two_head_source),
    route("d8_two_head_seq8", "head_axis", 8, 8, 2, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_two_head_sidecar),
    route("d8_two_head_seq8", "head_axis", 8, 8, 2, 8, "fused", "zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json", time_two_head_fused),
    route("d8_four_head_seq8", "head_axis_extension", 8, 8, 4, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json", time_four_head_source),
    route("d8_four_head_seq8", "head_axis_extension", 8, 8, 4, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_four_head_sidecar),
    route("d8_four_head_seq8", "head_axis_extension", 8, 8, 4, 8, "fused", "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json", time_four_head_fused),
    route("d8_eight_head_seq8", "head_axis_extension", 8, 8, 8, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.envelope.json", time_eight_head_source),
    route("d8_eight_head_seq8", "head_axis_extension", 8, 8, 8, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_eight_head_sidecar),
    route("d8_eight_head_seq8", "head_axis_extension", 8, 8, 8, 8, "fused", "zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-proof-2026-05.envelope.json", time_eight_head_fused),
    route("d8_sixteen_head_seq8", "head_axis_extension", 8, 8, 16, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.envelope.json", time_sixteen_head_source),
    route("d8_sixteen_head_seq8", "head_axis_extension", 8, 8, 16, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_sixteen_head_sidecar),
    route("d8_sixteen_head_seq8", "head_axis_extension", 8, 8, 16, 8, "fused", "zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-proof-2026-05.envelope.json", time_sixteen_head_fused),
    route("d8_two_head_seq16", "sequence_axis", 8, 8, 2, 16, "source_arithmetic", "zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json", time_two_head_longseq_source),
    route("d8_two_head_seq16", "sequence_axis", 8, 8, 2, 16, "logup_sidecar", "zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_two_head_longseq_sidecar),
    route("d8_two_head_seq16", "sequence_axis", 8, 8, 2, 16, "fused", "zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json", time_two_head_longseq_fused),
    route("d8_two_head_seq32", "sequence_axis_extension", 8, 8, 2, 32, "source_arithmetic", "zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.envelope.json", time_two_head_seq32_source),
    route("d8_two_head_seq32", "sequence_axis_extension", 8, 8, 2, 32, "logup_sidecar", "zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_two_head_seq32_sidecar),
    route("d8_two_head_seq32", "sequence_axis_extension", 8, 8, 2, 32, "fused", "zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-proof-2026-05.envelope.json", time_two_head_seq32_fused),
    route("d16_two_head_seq8", "combined_width_head_axis", 16, 16, 2, 8, "source_arithmetic", "zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.envelope.json", time_d16_two_head_source),
    route("d16_two_head_seq8", "combined_width_head_axis", 16, 16, 2, 8, "logup_sidecar", "zkai-attention-kv-stwo-native-d16-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_d16_two_head_sidecar),
    route("d16_two_head_seq8", "combined_width_head_axis", 16, 16, 2, 8, "fused", "zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json", time_d16_two_head_fused),
    route("d16_two_head_seq16", "combined_width_head_sequence_axis", 16, 16, 2, 16, "source_arithmetic", "zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json", time_d16_two_head_longseq_source),
    route("d16_two_head_seq16", "combined_width_head_sequence_axis", 16, 16, 2, 16, "logup_sidecar", "zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json", time_d16_two_head_longseq_sidecar),
    route("d16_two_head_seq16", "combined_width_head_sequence_axis", 16, 16, 2, 16, "fused", "zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json", time_d16_two_head_longseq_fused),
];

#[cfg(feature = "stwo-backend")]
const fn route(
    profile_id: &'static str,
    axis_role: &'static str,
    key_width: usize,
    value_width: usize,
    head_count: usize,
    steps_per_head: usize,
    role: &'static str,
    evidence_relative_path: &'static str,
    timed_verifier: TimedVerifier,
) -> Route {
    Route {
        profile_id,
        axis_role,
        key_width,
        value_width,
        head_count,
        steps_per_head,
        role,
        evidence_relative_path,
        timed_verifier,
    }
}

fn main() -> ExitCode {
    #[cfg(feature = "stwo-backend")]
    {
        match run() {
            Ok(summary) => {
                println!("{}", summary);
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("{error}");
                ExitCode::from(2)
            }
        }
    }
    #[cfg(not(feature = "stwo-backend"))]
    {
        eprintln!("zkai_attention_kv_stwo_softmax_table_timing requires --features stwo-backend");
        ExitCode::from(2)
    }
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let config = parse_args(std::env::args_os().skip(1))?;
    let canonical_root = fs::canonicalize(&config.evidence_dir).map_err(|error| {
        format!(
            "failed to canonicalize evidence dir {}: {error}",
            config.evidence_dir.display()
        )
    })?;
    let rows = ROUTES
        .iter()
        .map(|route| timed_route_row(&canonical_root, route, config.runs))
        .collect::<Result<Vec<_>, _>>()?;
    let profile_summaries = profile_summaries(&rows)?;
    serde_json::to_string_pretty(&serde_json::json!({
        "schema": SCHEMA,
        "decision": DECISION,
        "route_family": ROUTE_FAMILY,
        "timing_policy": TIMING_POLICY,
        "timing_scope": TIMING_SCOPE,
        "claim_boundary": CLAIM_BOUNDARY,
        "runs_per_envelope": config.runs,
        "clock": "std_time_instant_elapsed_as_micros",
        "safety": {
            "max_envelope_json_bytes": MAX_ENVELOPE_JSON_BYTES,
            "path_policy": "relative_paths_must_be_regular_non_symlink_files_inside_canonical_evidence_dir",
            "timed_window_excludes_cargo_build_subprocess_startup_file_read_and_json_deserialize": true,
        },
        "non_claims": NON_CLAIMS,
        "validation_commands": VALIDATION_COMMANDS,
        "rows": rows,
        "profile_summaries": profile_summaries,
    }))
    .map_err(|error| format!("failed to serialize timing summary: {error}"))
}

#[cfg(feature = "stwo-backend")]
fn parse_args<I>(args: I) -> Result<Config, String>
where
    I: IntoIterator<Item = OsString>,
{
    let mut args = args.into_iter().collect::<Vec<_>>();
    let mut evidence_dir = None;
    let mut runs = DEFAULT_RUNS;
    while !args.is_empty() {
        let flag = args.remove(0);
        match flag.to_string_lossy().as_ref() {
            "--evidence-dir" => {
                if args.is_empty() {
                    return Err("--evidence-dir requires a value".to_string());
                }
                evidence_dir = Some(PathBuf::from(args.remove(0)));
            }
            "--runs" => {
                if args.is_empty() {
                    return Err("--runs requires a value".to_string());
                }
                let raw = args.remove(0);
                let parsed = raw
                    .to_string_lossy()
                    .parse::<usize>()
                    .map_err(|error| format!("failed to parse --runs: {error}"))?;
                if parsed != DEFAULT_RUNS {
                    return Err(format!(
                        "--runs must be {DEFAULT_RUNS} for the checked median-of-5 timing policy"
                    ));
                }
                runs = parsed;
            }
            "--help" | "-h" => return Err(usage()),
            other => return Err(format!("unknown argument: {other}\n{}", usage())),
        }
    }
    Ok(Config {
        evidence_dir: evidence_dir.ok_or_else(usage)?,
        runs,
    })
}

#[cfg(feature = "stwo-backend")]
fn usage() -> String {
    "usage: zkai_attention_kv_stwo_softmax_table_timing --evidence-dir <dir> [--runs 5]".to_string()
}

#[cfg(feature = "stwo-backend")]
fn timed_route_row(
    canonical_root: &Path,
    route: &Route,
    runs: usize,
) -> Result<serde_json::Value, String> {
    let raw = read_contained_bounded_file(
        canonical_root,
        route.evidence_relative_path,
        MAX_ENVELOPE_JSON_BYTES,
    )?;
    let metadata = envelope_metadata(&raw, route.evidence_relative_path)?;
    let timings = (route.timed_verifier)(&raw, runs)?;
    if timings.len() != runs {
        return Err(format!(
            "{} {} emitted {} timings, expected {}",
            route.profile_id,
            route.role,
            timings.len(),
            runs
        ));
    }
    let median = median_us(&timings)?;
    let min = *timings.iter().min().ok_or("missing min timing")?;
    let max = *timings.iter().max().ok_or("missing max timing")?;
    Ok(serde_json::json!({
        "profile_id": route.profile_id,
        "axis_role": route.axis_role,
        "key_width": route.key_width,
        "value_width": route.value_width,
        "head_count": route.head_count,
        "steps_per_head": route.steps_per_head,
        "role": route.role,
        "evidence_relative_path": route.evidence_relative_path,
        "envelope_sha256": sha256_hex(&raw),
        "proof_backend": metadata.proof_backend,
        "proof_backend_version": metadata.proof_backend_version,
        "statement_version": metadata.statement_version,
        "proof_schema_version": metadata.proof_schema_version,
        "target_id": metadata.target_id,
        "verifier_domain": metadata.verifier_domain,
        "proof_size_bytes": metadata.proof_size_bytes,
        "envelope_size_bytes": raw.len(),
        "verify_runs_us": timings,
        "verify_median_us": median,
        "verify_min_us": min,
        "verify_max_us": max,
        "verified": true,
    }))
}

#[cfg(feature = "stwo-backend")]
#[derive(Debug)]
struct EnvelopeMetadata {
    proof_backend: String,
    proof_backend_version: String,
    statement_version: String,
    proof_schema_version: Option<String>,
    target_id: Option<String>,
    verifier_domain: Option<String>,
    proof_size_bytes: usize,
}

#[cfg(feature = "stwo-backend")]
fn envelope_metadata(raw: &[u8], label: &str) -> Result<EnvelopeMetadata, String> {
    let value: Value = serde_json::from_slice(raw)
        .map_err(|error| format!("failed to parse generic envelope JSON {label}: {error}"))?;
    let proof_backend = required_string(&value, "proof_backend", label)?;
    if proof_backend != "stwo" {
        return Err(format!("{label} proof_backend must be stwo"));
    }
    let proof_backend_version = required_string(&value, "proof_backend_version", label)?;
    let statement_version = required_string(&value, "statement_version", label)?;
    let proof = value
        .get("proof")
        .and_then(Value::as_array)
        .ok_or_else(|| format!("{label} missing proof byte array"))?;
    if proof.is_empty() {
        return Err(format!("{label} proof byte array is empty"));
    }
    if proof
        .iter()
        .any(|byte| byte.as_u64().is_none_or(|value| value > 255))
    {
        return Err(format!(
            "{label} proof byte array must contain uint8 values"
        ));
    }
    Ok(EnvelopeMetadata {
        proof_backend: proof_backend.to_string(),
        proof_backend_version: proof_backend_version.to_string(),
        statement_version: statement_version.to_string(),
        proof_schema_version: optional_string(&value, "proof_schema_version", label)?,
        target_id: optional_string(&value, "target_id", label)?,
        verifier_domain: optional_string(&value, "verifier_domain", label)?,
        proof_size_bytes: proof.len(),
    })
}

#[cfg(feature = "stwo-backend")]
fn required_string<'a>(value: &'a Value, key: &str, label: &str) -> Result<&'a str, String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("{label} missing string field {key}"))
}

#[cfg(feature = "stwo-backend")]
fn optional_string(value: &Value, key: &str, label: &str) -> Result<Option<String>, String> {
    match value.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(text)) => Ok(Some(text.clone())),
        Some(_) => Err(format!("{label} field {key} must be string or null")),
    }
}

#[cfg(feature = "stwo-backend")]
fn profile_summaries(rows: &[serde_json::Value]) -> Result<Vec<serde_json::Value>, String> {
    let mut summaries = Vec::new();
    for chunk in rows.chunks_exact(3) {
        let source = &chunk[0];
        let sidecar = &chunk[1];
        let fused = &chunk[2];
        if source["role"] != "source_arithmetic"
            || sidecar["role"] != "logup_sidecar"
            || fused["role"] != "fused"
        {
            return Err("route rows are not grouped as source, sidecar, fused".to_string());
        }
        let profile_id = source["profile_id"]
            .as_str()
            .ok_or("profile_id must be a string")?;
        if sidecar["profile_id"] != profile_id || fused["profile_id"] != profile_id {
            return Err(format!("profile grouping drift for {profile_id}"));
        }
        let source_median = source["verify_median_us"]
            .as_u64()
            .ok_or("source median must be u64")?;
        let sidecar_median = sidecar["verify_median_us"]
            .as_u64()
            .ok_or("sidecar median must be u64")?;
        let fused_median = fused["verify_median_us"]
            .as_u64()
            .ok_or("fused median must be u64")?;
        let source_plus_sidecar = source_median
            .checked_add(sidecar_median)
            .ok_or_else(|| format!("source+sidecar median overflow for {profile_id}"))?;
        let ratio = if source_plus_sidecar == 0 {
            0.0
        } else {
            fused_median as f64 / source_plus_sidecar as f64
        };
        summaries.push(serde_json::json!({
            "profile_id": profile_id,
            "axis_role": source["axis_role"],
            "key_width": source["key_width"],
            "value_width": source["value_width"],
            "head_count": source["head_count"],
            "steps_per_head": source["steps_per_head"],
            "source_plus_sidecar_verify_median_us": source_plus_sidecar,
            "fused_verify_median_us": fused_median,
            "fused_minus_source_plus_sidecar_verify_median_us": fused_median as i128 - source_plus_sidecar as i128,
            "fused_to_source_plus_sidecar_verify_median_ratio": round6(ratio),
            "timing_status": "ENGINEERING_LOCAL_OBSERVATION_ONLY_NOT_PUBLIC_BENCHMARK",
        }));
    }
    if !rows.chunks_exact(3).remainder().is_empty() {
        return Err("route row count must be divisible by three".to_string());
    }
    Ok(summaries)
}

#[cfg(feature = "stwo-backend")]
fn median_us(values: &[u64]) -> Result<u64, String> {
    if values.len() != DEFAULT_RUNS {
        return Err(format!(
            "median timing requires exactly {DEFAULT_RUNS} runs, got {}",
            values.len()
        ));
    }
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    Ok(sorted[sorted.len() / 2])
}

#[cfg(feature = "stwo-backend")]
fn round6(value: f64) -> f64 {
    (value * 1_000_000.0).round() / 1_000_000.0
}

#[cfg(feature = "stwo-backend")]
fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

#[cfg(feature = "stwo-backend")]
fn read_contained_bounded_file(
    canonical_root: &Path,
    relative_path: &str,
    max_bytes: usize,
) -> Result<Vec<u8>, String> {
    if relative_path.starts_with('/') || relative_path.contains("..") {
        return Err(format!(
            "evidence path must be relative and contained: {relative_path}"
        ));
    }
    let path = canonical_root.join(relative_path);
    let preflight = fs::symlink_metadata(&path)
        .map_err(|error| format!("failed to stat evidence file {}: {error}", path.display()))?;
    if preflight.file_type().is_symlink() {
        return Err(format!(
            "evidence file {} is a symlink, expected a regular file",
            path.display()
        ));
    }
    if !preflight.is_file() {
        return Err(format!(
            "evidence file {} is not a regular file",
            path.display()
        ));
    }
    if preflight.len() > max_bytes as u64 {
        return Err(format!(
            "evidence file {} exceeds max size: got {} bytes, limit {} bytes",
            path.display(),
            preflight.len(),
            max_bytes
        ));
    }
    let canonical_path = fs::canonicalize(&path)
        .map_err(|error| format!("failed to canonicalize {}: {error}", path.display()))?;
    if !canonical_path.starts_with(canonical_root) {
        return Err(format!(
            "evidence file {} escapes evidence dir {}",
            canonical_path.display(),
            canonical_root.display()
        ));
    }
    #[cfg(unix)]
    let file = {
        use std::os::unix::fs::OpenOptionsExt;

        fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(&canonical_path)
            .map_err(|error| {
                format!(
                    "failed to open evidence file {} without following symlinks: io_kind={:?}: {error}",
                    canonical_path.display(),
                    error.kind()
                )
            })?
    };
    #[cfg(not(unix))]
    let mut file = fs::File::open(&canonical_path).map_err(|error| {
        format!(
            "failed to open evidence file {}: {error}",
            canonical_path.display()
        )
    })?;
    let opened_metadata = file.metadata().map_err(|error| {
        format!(
            "failed to stat opened evidence file {}: {error}",
            canonical_path.display()
        )
    })?;
    if !opened_metadata.is_file() {
        return Err(format!(
            "opened evidence file {} is not a regular file",
            canonical_path.display()
        ));
    }
    if opened_metadata.len() > max_bytes as u64 {
        return Err(format!(
            "opened evidence file {} exceeds max size: got {} bytes, limit {} bytes",
            canonical_path.display(),
            opened_metadata.len(),
            max_bytes
        ));
    }
    let mut buffer = Vec::new();
    file.take((max_bytes + 1) as u64)
        .read_to_end(&mut buffer)
        .map_err(|error| {
            format!(
                "failed to read evidence file {}: {error}",
                canonical_path.display()
            )
        })?;
    if buffer.len() > max_bytes {
        return Err(format!(
            "evidence file {} exceeds max size while reading: got more than {} bytes",
            canonical_path.display(),
            max_bytes
        ));
    }
    Ok(buffer)
}

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;

    #[test]
    fn median_requires_exactly_five_runs() {
        assert_eq!(median_us(&[9, 3, 5, 1, 7]).unwrap(), 5);
        let error = median_us(&[1, 2, 3]).unwrap_err();
        assert!(error.contains("exactly 5 runs"));
    }

    #[test]
    fn parse_args_requires_evidence_dir_and_exact_runs() {
        let config = parse_args([
            OsString::from("--evidence-dir"),
            OsString::from("docs/engineering/evidence"),
            OsString::from("--runs"),
            OsString::from("5"),
        ])
        .unwrap();
        assert_eq!(
            config.evidence_dir,
            PathBuf::from("docs/engineering/evidence")
        );
        assert_eq!(config.runs, 5);

        let missing = parse_args([OsString::from("--runs"), OsString::from("5")]).unwrap_err();
        assert!(missing.contains("usage:"));

        let wrong_runs = parse_args([
            OsString::from("--evidence-dir"),
            OsString::from("docs/engineering/evidence"),
            OsString::from("--runs"),
            OsString::from("3"),
        ])
        .unwrap_err();
        assert!(wrong_runs.contains("must be 5"));
    }

    #[test]
    fn envelope_metadata_rejects_missing_or_non_byte_proof() {
        let valid = br#"{
            "proof_backend": "stwo",
            "proof_backend_version": "v",
            "statement_version": "s",
            "proof": [0, 255]
        }"#;
        let metadata = envelope_metadata(valid, "fixture").unwrap();
        assert_eq!(metadata.proof_size_bytes, 2);
        assert_eq!(metadata.proof_backend, "stwo");

        let bad_backend = br#"{
            "proof_backend": "risc0",
            "proof_backend_version": "v",
            "statement_version": "s",
            "proof": [0]
        }"#;
        assert!(envelope_metadata(bad_backend, "fixture")
            .unwrap_err()
            .contains("proof_backend must be stwo"));

        let bad_byte = br#"{
            "proof_backend": "stwo",
            "proof_backend_version": "v",
            "statement_version": "s",
            "proof": [256]
        }"#;
        assert!(envelope_metadata(bad_byte, "fixture")
            .unwrap_err()
            .contains("uint8"));
    }

    #[test]
    fn route_catalog_is_grouped_and_complete() {
        assert_eq!(ROUTES.len(), 33);
        for chunk in ROUTES.chunks_exact(3) {
            assert_eq!(chunk[0].role, "source_arithmetic");
            assert_eq!(chunk[1].role, "logup_sidecar");
            assert_eq!(chunk[2].role, "fused");
            assert_eq!(chunk[0].profile_id, chunk[1].profile_id);
            assert_eq!(chunk[0].profile_id, chunk[2].profile_id);
        }
    }
}
