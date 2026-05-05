use methods::{ATTENTION_KV_TRANSITION_RECEIPT_ELF, ATTENTION_KV_TRANSITION_RECEIPT_ID};
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    env,
    fs::{self, File},
    io::Read,
    path::PathBuf,
    time::Instant,
};

const MAX_RECEIPT_BYTES: usize = 2_000_000;
const JOURNAL_SCHEMA: &str = "zkai-attention-kv-risc0-semantics-journal-v1";
const SEMANTICS: &str = "tiny-single-head-integer-argmax-attention-v1";

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
struct AttentionInput {
    prior_kv_cache: Vec<KvEntry>,
    input_step: InputStep,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct ScoreRow {
    position: i32,
    score: i32,
    value: [i32; 2],
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct AttentionJournal {
    schema: String,
    semantics: String,
    prior_kv_cache: Vec<KvEntry>,
    input_step: InputStep,
    scores: Vec<ScoreRow>,
    selected_position: i32,
    attention_output: [i32; 2],
    next_kv_cache: Vec<KvEntry>,
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn image_id_hex() -> String {
    ATTENTION_KV_TRANSITION_RECEIPT_ID
        .iter()
        .map(|word| format!("{word:08x}"))
        .collect()
}

fn dot(lhs: [i32; 2], rhs: [i32; 2]) -> i32 {
    lhs[0] * rhs[0] + lhs[1] * rhs[1]
}

fn expected_journal(input: &AttentionInput) -> AttentionJournal {
    assert!(
        !input.prior_kv_cache.is_empty(),
        "attention fixture needs at least one prior KV row"
    );
    let next_item = KvEntry {
        position: input.input_step.token_position,
        key: input.input_step.new_key,
        value: input.input_step.new_value,
    };
    let mut next_kv_cache = input.prior_kv_cache.clone();
    next_kv_cache.push(next_item);
    let scores: Vec<ScoreRow> = next_kv_cache
        .iter()
        .map(|item| ScoreRow {
            position: item.position,
            score: dot(input.input_step.query, item.key),
            value: item.value,
        })
        .collect();
    let selected = scores
        .iter()
        .max_by_key(|row| (row.score, -row.position))
        .expect("non-empty score trace");
    let selected_position = selected.position;
    let attention_output = selected.value;
    AttentionJournal {
        schema: JOURNAL_SCHEMA.to_string(),
        semantics: SEMANTICS.to_string(),
        prior_kv_cache: input.prior_kv_cache.clone(),
        input_step: input.input_step.clone(),
        scores,
        selected_position,
        attention_output,
        next_kv_cache,
    }
}

fn read_input(path: &PathBuf) -> AttentionInput {
    let bytes = fs::read(path).expect("read attention input JSON");
    serde_json::from_slice(&bytes).expect("decode attention input JSON")
}

fn write_summary(
    out_path: &PathBuf,
    mode: &str,
    journal: &AttentionJournal,
    receipt_bytes: &[u8],
    prove_time_ms: Option<f64>,
    verify_time_ms: f64,
) {
    let journal_json = serde_json::to_value(journal).expect("journal to JSON value");
    let journal_bytes = serde_json::to_vec(journal).expect("serialize journal for hash");
    let summary = json!({
        "schema": "zkai-attention-kv-risc0-host-summary-v1",
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

fn verify_receipt(receipt: &Receipt, expected: &AttentionJournal) -> (AttentionJournal, f64) {
    let verify_started = Instant::now();
    receipt
        .verify(ATTENTION_KV_TRANSITION_RECEIPT_ID)
        .expect("receipt verifies against image id");
    let decoded: AttentionJournal = receipt
        .journal
        .decode()
        .expect("decode receipt journal as attention journal");
    assert_eq!(
        &decoded, expected,
        "receipt journal does not match expected attention/KV transition"
    );
    (decoded, verify_started.elapsed().as_secs_f64() * 1000.0)
}

fn prove(input_path: PathBuf, receipt_path: PathBuf, summary_path: PathBuf) {
    let input = read_input(&input_path);
    let expected = expected_journal(&input);
    let env = ExecutorEnv::builder()
        .write(&input)
        .expect("write attention input")
        .build()
        .expect("build executor env");
    let prover = default_prover();
    let prove_started = Instant::now();
    let prove_info = prover
        .prove(env, ATTENTION_KV_TRANSITION_RECEIPT_ELF)
        .expect("prove RISC Zero attention/KV receipt");
    let prove_time_ms = prove_started.elapsed().as_secs_f64() * 1000.0;
    let receipt = prove_info.receipt;
    let (decoded, verify_time_ms) = verify_receipt(&receipt, &expected);
    let receipt_bytes = bincode::serialize(&receipt).expect("serialize receipt");
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
    let receipt: Receipt =
        bincode::deserialize(&receipt_bytes).expect("deserialize RISC Zero receipt");
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
    eprintln!("usage: host prove <attention-input-json> <receipt-out> <summary-out>");
    eprintln!("   or: host verify <attention-input-json> <receipt-in> <summary-out>");
    std::process::exit(2);
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
        usage();
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

    fn test_dir(name: &str) -> PathBuf {
        let dir = env::temp_dir().join(format!("risc0-attention-kv-host-{name}"));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("create test directory");
        dir
    }

    #[test]
    fn expected_journal_uses_lowest_position_tie_break() {
        let input = AttentionInput {
            prior_kv_cache: vec![
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
            input_step: InputStep {
                token_position: 2,
                query: [1, 1],
                new_key: [1, -1],
                new_value: [4, 2],
            },
        };
        let journal = expected_journal(&input);
        assert_eq!(journal.selected_position, 0);
        assert_eq!(journal.attention_output, [2, 1]);
        assert_eq!(journal.next_kv_cache.len(), 3);
    }

    #[test]
    fn verify_rejects_oversized_receipt_before_deserialize() {
        let dir = test_dir("oversized-receipt");
        let input_path = dir.join("input.json");
        let receipt_path = dir.join("receipt.bincode");
        let summary_path = dir.join("summary.json");
        fs::write(
            &input_path,
            br#"{"prior_kv_cache":[{"position":0,"key":[1,0],"value":[2,1]}],"input_step":{"token_position":1,"query":[1,0],"new_key":[0,1],"new_value":[3,4]}}"#,
        )
        .expect("write input fixture");
        fs::write(&receipt_path, vec![0u8; MAX_RECEIPT_BYTES + 1])
            .expect("write oversized receipt fixture");

        let summary_for_check = summary_path.clone();
        let result = std::panic::catch_unwind(|| verify(input_path, receipt_path, summary_path));

        assert!(result.is_err(), "oversized receipt must be rejected");
        assert!(
            !summary_for_check.exists(),
            "rejected receipt must not write a verification summary"
        );
        fs::remove_dir_all(&dir).expect("remove test directory");
    }
}
