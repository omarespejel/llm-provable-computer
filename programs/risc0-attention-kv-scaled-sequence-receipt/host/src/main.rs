use bincode::Options;
use methods::{ATTENTION_KV_SCALED_SEQUENCE_RECEIPT_ELF, ATTENTION_KV_SCALED_SEQUENCE_RECEIPT_ID};
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    cmp::Ordering,
    env,
    fs::{self, File},
    io::Read,
    path::{Component, PathBuf},
    time::Instant,
};

const MAX_RECEIPT_BYTES: usize = 2_500_000;
const JOURNAL_SCHEMA: &str = "zkai-attention-kv-risc0-scaled-sequence-journal-v1";
const SEMANTICS: &str = "tiny-single-head-integer-argmax-attention-scaled-sequence-v1";
const EXACT_SEQUENCE_LENGTH: usize = 8;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct KvEntry {
    position: i32,
    key: [i32; 2],
    value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct InputStep {
    token_position: i32,
    query: [i32; 2],
    new_key: [i32; 2],
    new_value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct AttentionSequenceInput {
    initial_kv_cache: Vec<KvEntry>,
    input_steps: Vec<InputStep>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct ScoreRow {
    position: i32,
    score: i64,
    value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct TransitionRow {
    step_index: usize,
    prior_kv_cache: Vec<KvEntry>,
    input_step: InputStep,
    scores: Vec<ScoreRow>,
    selected_position: i32,
    attention_output: [i32; 2],
    next_kv_cache: Vec<KvEntry>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct AttentionSequenceJournal {
    schema: String,
    semantics: String,
    masking_policy: String,
    tie_break: String,
    key_width: usize,
    value_width: usize,
    sequence_length: usize,
    initial_kv_cache: Vec<KvEntry>,
    input_steps: Vec<InputStep>,
    transitions: Vec<TransitionRow>,
    final_kv_cache: Vec<KvEntry>,
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn image_id_hex() -> String {
    ATTENTION_KV_SCALED_SEQUENCE_RECEIPT_ID
        .iter()
        .map(|word| format!("{word:08x}"))
        .collect()
}

fn dot(lhs: [i32; 2], rhs: [i32; 2]) -> i64 {
    let score = i128::from(lhs[0]) * i128::from(rhs[0]) + i128::from(lhs[1]) * i128::from(rhs[1]);
    i64::try_from(score).expect("attention score outside i64 semantics bound")
}

fn attention_order(lhs: &ScoreRow, rhs: &ScoreRow) -> Ordering {
    match lhs.score.cmp(&rhs.score) {
        Ordering::Equal => rhs.position.cmp(&lhs.position),
        order => order,
    }
}

fn apply_step(
    step_index: usize,
    prior_kv_cache: &[KvEntry],
    input_step: &InputStep,
) -> TransitionRow {
    let next_item = KvEntry {
        position: input_step.token_position,
        key: input_step.new_key,
        value: input_step.new_value,
    };
    let mut next_kv_cache = prior_kv_cache.to_vec();
    next_kv_cache.push(next_item);
    let scores: Vec<ScoreRow> = next_kv_cache
        .iter()
        .map(|item| ScoreRow {
            position: item.position,
            score: dot(input_step.query, item.key),
            value: item.value,
        })
        .collect();
    let selected = scores
        .iter()
        .max_by(|left, right| attention_order(left, right))
        .expect("non-empty score trace");
    let selected_position = selected.position;
    let attention_output = selected.value;
    TransitionRow {
        step_index,
        prior_kv_cache: prior_kv_cache.to_vec(),
        input_step: input_step.clone(),
        scores,
        selected_position,
        attention_output,
        next_kv_cache,
    }
}

fn assert_append_only_positions(input: &AttentionSequenceInput) {
    let mut previous_position: Option<i32> = None;
    for position in input
        .initial_kv_cache
        .iter()
        .map(|entry| entry.position)
        .chain(input.input_steps.iter().map(|step| step.token_position))
    {
        if let Some(previous) = previous_position {
            assert!(
                position > previous,
                "attention KV positions must be strictly increasing for append-only tamper rules"
            );
        }
        previous_position = Some(position);
    }
}

fn expected_journal(input: &AttentionSequenceInput) -> AttentionSequenceJournal {
    assert!(
        !input.initial_kv_cache.is_empty(),
        "attention fixture needs at least one initial KV row"
    );
    assert!(
        input.input_steps.len() == EXACT_SEQUENCE_LENGTH,
        "scaled sequence fixture requires exactly eight carried KV transitions"
    );
    assert_append_only_positions(input);
    let mut current_kv_cache = input.initial_kv_cache.clone();
    let mut transitions = Vec::with_capacity(input.input_steps.len());
    for (step_index, input_step) in input.input_steps.iter().enumerate() {
        let row = apply_step(step_index, &current_kv_cache, input_step);
        current_kv_cache = row.next_kv_cache.clone();
        transitions.push(row);
    }
    AttentionSequenceJournal {
        schema: JOURNAL_SCHEMA.to_string(),
        semantics: SEMANTICS.to_string(),
        masking_policy: "none".to_string(),
        tie_break: "lowest_position".to_string(),
        key_width: 2,
        value_width: 2,
        sequence_length: input.input_steps.len(),
        initial_kv_cache: input.initial_kv_cache.clone(),
        input_steps: input.input_steps.clone(),
        transitions,
        final_kv_cache: current_kv_cache,
    }
}

fn read_input(path: &PathBuf) -> AttentionSequenceInput {
    let bytes = fs::read(path).expect("read attention sequence input JSON");
    serde_json::from_slice(&bytes).expect("decode attention sequence input JSON")
}

fn create_parent_dir(path: &PathBuf) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("create output parent directory");
    }
}

fn write_summary(
    out_path: &PathBuf,
    mode: &str,
    journal: &AttentionSequenceJournal,
    receipt_bytes: &[u8],
    prove_time_ms: Option<f64>,
    verify_time_ms: f64,
) {
    create_parent_dir(out_path);
    let journal_json = serde_json::to_value(journal).expect("journal to JSON value");
    let journal_bytes = serde_json::to_vec(journal).expect("serialize journal for hash");
    let summary = json!({
        "schema": "zkai-attention-kv-risc0-scaled-sequence-host-summary-v1",
        "mode": mode,
        "risc0_zkvm_version": risc0_zkvm::VERSION,
        "image_id_hex": image_id_hex(),
        "journal": journal_json,
        "journal_sha256": sha256_hex(&journal_bytes),
        "receipt_sha256": sha256_hex(receipt_bytes),
        "receipt_size_bytes": receipt_bytes.len(),
        "prove_time_ms": prove_time_ms,
        "verify_time_ms": verify_time_ms,
    });
    fs::write(
        out_path,
        serde_json::to_vec_pretty(&summary).expect("serialize summary"),
    )
    .expect("write summary");
    println!(
        "{}",
        serde_json::to_string_pretty(&summary).expect("print summary")
    );
}

fn verify_receipt(
    receipt: &Receipt,
    expected: &AttentionSequenceJournal,
) -> (AttentionSequenceJournal, f64) {
    let verify_started = Instant::now();
    receipt
        .verify(ATTENTION_KV_SCALED_SEQUENCE_RECEIPT_ID)
        .expect("receipt verifies against image id");
    let decoded: AttentionSequenceJournal = receipt
        .journal
        .decode()
        .expect("decode receipt journal as attention sequence journal");
    assert_eq!(
        &decoded, expected,
        "receipt journal does not match expected attention/KV sequence"
    );
    (decoded, verify_started.elapsed().as_secs_f64() * 1000.0)
}

fn prove(input_path: PathBuf, receipt_path: PathBuf, summary_path: PathBuf) {
    let input = read_input(&input_path);
    let expected = expected_journal(&input);
    let env = ExecutorEnv::builder()
        .write(&input)
        .expect("write attention sequence input")
        .build()
        .expect("build executor env");
    let prover = default_prover();
    let prove_started = Instant::now();
    let prove_info = prover
        .prove(env, ATTENTION_KV_SCALED_SEQUENCE_RECEIPT_ELF)
        .expect("prove RISC Zero attention/KV sequence receipt");
    let prove_time_ms = prove_started.elapsed().as_secs_f64() * 1000.0;
    let receipt = prove_info.receipt;
    let (decoded, verify_time_ms) = verify_receipt(&receipt, &expected);
    let receipt_bytes = bincode::serialize(&receipt).expect("serialize receipt");
    create_parent_dir(&receipt_path);
    fs::write(&receipt_path, &receipt_bytes).expect("write receipt artifact");
    write_summary(
        &summary_path,
        "prove",
        &decoded,
        &receipt_bytes,
        Some(prove_time_ms),
        verify_time_ms,
    );
}

fn verify(input_path: PathBuf, receipt_path: PathBuf, summary_path: PathBuf) {
    let input = read_input(&input_path);
    let expected = expected_journal(&input);
    let receipt_file = File::open(&receipt_path).expect("open receipt artifact");
    let receipt_len = receipt_file
        .metadata()
        .expect("stat opened receipt artifact")
        .len();
    if receipt_len == 0 || receipt_len > MAX_RECEIPT_BYTES as u64 {
        panic!(
            "receipt artifact size outside allowed bound: {} bytes",
            receipt_len
        );
    }
    let mut receipt_bytes = Vec::with_capacity(receipt_len as usize);
    let mut limited_reader = receipt_file.take(MAX_RECEIPT_BYTES as u64 + 1);
    limited_reader
        .read_to_end(&mut receipt_bytes)
        .expect("read receipt artifact");
    if receipt_bytes.is_empty() || receipt_bytes.len() > MAX_RECEIPT_BYTES {
        panic!(
            "receipt artifact size outside allowed bound after read: {} bytes",
            receipt_bytes.len()
        );
    }
    let receipt: Receipt = bincode::DefaultOptions::new()
        .with_fixint_encoding()
        .with_limit(MAX_RECEIPT_BYTES as u64)
        .deserialize(&receipt_bytes)
        .expect("deserialize size-limited RISC Zero receipt");
    let (decoded, verify_time_ms) = verify_receipt(&receipt, &expected);
    write_summary(
        &summary_path,
        "verify",
        &decoded,
        &receipt_bytes,
        None,
        verify_time_ms,
    );
}

fn usage() -> ! {
    eprintln!("usage: host prove <attention-scaled-sequence-input-json> <receipt-out> <summary-out>");
    eprintln!("   or: host verify <attention-scaled-sequence-input-json> <receipt-in> <summary-out>");
    std::process::exit(2);
}

fn normalize_output_path(path: &PathBuf) -> PathBuf {
    let joined = if path.is_absolute() {
        path.clone()
    } else {
        env::current_dir()
            .expect("resolve current directory")
            .join(path)
    };
    let mut normalized = PathBuf::new();
    for component in joined.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            other => normalized.push(other.as_os_str()),
        }
    }
    normalized
}

fn output_paths_overlap(receipt_path: &PathBuf, summary_path: &PathBuf) -> bool {
    normalize_output_path(receipt_path) == normalize_output_path(summary_path)
}

fn main() {
    let mut args = env::args().skip(1);
    let Some(command) = args.next() else { usage() };
    let Some(input_path) = args.next().map(PathBuf::from) else {
        usage()
    };
    let Some(receipt_path) = args.next().map(PathBuf::from) else {
        usage()
    };
    let Some(summary_path) = args.next().map(PathBuf::from) else {
        usage()
    };
    if args.next().is_some() {
        usage()
    }
    if output_paths_overlap(&receipt_path, &summary_path) {
        eprintln!("receipt path and summary path must be different");
        std::process::exit(2);
    }
    match command.as_str() {
        "prove" => prove(input_path, receipt_path, summary_path),
        "verify" => verify(input_path, receipt_path, summary_path),
        _ => usage(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_input() -> AttentionSequenceInput {
        AttentionSequenceInput {
            initial_kv_cache: vec![
                KvEntry {
                    position: 0,
                    key: [1, 0],
                    value: [2, 1],
                },
                KvEntry {
                    position: 1,
                    key: [0, 1],
                    value: [-1, 3],
                },
            ],
            input_steps: vec![
                InputStep {
                    token_position: 2,
                    query: [1, 1],
                    new_key: [1, -1],
                    new_value: [4, 2],
                },
                InputStep {
                    token_position: 3,
                    query: [2, -1],
                    new_key: [0, 2],
                    new_value: [5, -2],
                },
                InputStep {
                    token_position: 4,
                    query: [-1, 2],
                    new_key: [2, 1],
                    new_value: [0, 6],
                },
                InputStep {
                    token_position: 5,
                    query: [3, 0],
                    new_key: [-1, 3],
                    new_value: [7, 1],
                },
                InputStep {
                    token_position: 6,
                    query: [0, 3],
                    new_key: [3, -2],
                    new_value: [-3, 4],
                },
                InputStep {
                    token_position: 7,
                    query: [2, 2],
                    new_key: [-2, -1],
                    new_value: [6, 6],
                },
                InputStep {
                    token_position: 8,
                    query: [-2, 1],
                    new_key: [1, 3],
                    new_value: [8, -1],
                },
                InputStep {
                    token_position: 9,
                    query: [1, -3],
                    new_key: [2, -2],
                    new_value: [-5, 5],
                },
            ],
        }
    }

    #[test]
    fn create_parent_dir_creates_nested_output_parent() {
        let root =
            std::env::temp_dir().join(format!("ptvm-risc0-scaled-sequence-test-{}", std::process::id()));
        let out = root.join("nested").join("summary.json");
        if root.exists() {
            fs::remove_dir_all(&root).expect("remove stale test directory");
        }

        create_parent_dir(&out);

        assert!(out.parent().expect("parent").is_dir());
        fs::remove_dir_all(root).expect("cleanup test directory");
    }

    #[test]
    fn output_paths_overlap_rejects_same_relative_path() {
        let receipt = PathBuf::from("target/shared-output");
        let summary = PathBuf::from(".")
            .join("target")
            .join("nested")
            .join("..")
            .join("shared-output");

        assert!(output_paths_overlap(&receipt, &summary));
    }

    #[test]
    fn expected_journal_carries_kv_state_across_eight_steps() {
        let journal = expected_journal(&sample_input());

        assert_eq!(journal.sequence_length, 8);
        assert_eq!(journal.transitions.len(), 8);
        assert_eq!(
            journal
                .transitions
                .iter()
                .map(|row| row.selected_position)
                .collect::<Vec<_>>(),
            vec![0, 2, 3, 4, 5, 4, 5, 6]
        );
        assert_eq!(
            journal
                .transitions
                .iter()
                .map(|row| row.attention_output)
                .collect::<Vec<_>>(),
            vec![[2, 1], [4, 2], [5, -2], [0, 6], [7, 1], [0, 6], [7, 1], [-3, 4]]
        );
        for idx in 1..journal.transitions.len() {
            assert_eq!(
                journal.transitions[idx].prior_kv_cache,
                journal.transitions[idx - 1].next_kv_cache
            );
        }
        assert_eq!(journal.final_kv_cache, journal.transitions[7].next_kv_cache);
        assert_eq!(journal.final_kv_cache.len(), 10);
    }

    #[test]
    #[should_panic(expected = "scaled sequence fixture requires exactly eight carried KV transitions")]
    fn expected_journal_requires_a_real_sequence() {
        let mut input = sample_input();
        input.input_steps.truncate(1);
        expected_journal(&input);
    }

    #[test]
    #[should_panic(expected = "attention KV positions must be strictly increasing for append-only tamper rules")]
    fn expected_journal_rejects_non_append_only_positions() {
        let mut input = sample_input();
        input.input_steps[1].token_position = input.input_steps[0].token_position;
        expected_journal(&input);
    }

    #[test]
    fn dot_bound_is_inside_i64_for_two_wide_i32_fixture() {
        let score = dot([i32::MAX, i32::MAX], [i32::MAX, i32::MAX]);
        assert_eq!(score, 9_223_372_028_264_841_218);
        assert!(score < i64::MAX);
    }
}
