use methods::{D128_STATEMENT_RECEIPT_ELF, D128_STATEMENT_RECEIPT_ID};
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
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

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn image_id_hex() -> String {
    D128_STATEMENT_RECEIPT_ID
        .iter()
        .map(|word| format!("{word:08x}"))
        .collect()
}

fn read_expected_journal(path: &PathBuf) -> Vec<u8> {
    fs::read(path).expect("read expected journal bytes")
}

fn write_summary(
    out_path: &PathBuf,
    mode: &str,
    journal_bytes: &[u8],
    receipt_bytes: &[u8],
    prove_time_ms: Option<f64>,
    verify_time_ms: f64,
) {
    let summary = json!({
        "schema": "zkai-d128-risc0-host-summary-v1",
        "mode": mode,
        "risc0_zkvm_version": risc0_zkvm::VERSION,
        "image_id_hex": image_id_hex(),
        "journal_sha256": sha256_hex(journal_bytes),
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

fn verify_receipt(receipt: &Receipt, journal_bytes: &[u8]) -> f64 {
    let verify_started = Instant::now();
    receipt
        .verify(D128_STATEMENT_RECEIPT_ID)
        .expect("receipt verifies against image id");
    let decoded: Vec<u8> = receipt
        .journal
        .decode()
        .expect("decode receipt journal as bytes");
    assert_eq!(
        decoded, journal_bytes,
        "receipt journal does not match expected contract bytes"
    );
    verify_started.elapsed().as_secs_f64() * 1000.0
}

fn prove(journal_path: PathBuf, receipt_path: PathBuf, summary_path: PathBuf) {
    let journal_bytes = read_expected_journal(&journal_path);
    let env = ExecutorEnv::builder()
        .write(&journal_bytes)
        .expect("write journal input")
        .build()
        .expect("build executor env");
    let prover = default_prover();
    let prove_started = Instant::now();
    let prove_info = prover
        .prove(env, D128_STATEMENT_RECEIPT_ELF)
        .expect("prove RISC Zero receipt");
    let prove_time_ms = prove_started.elapsed().as_secs_f64() * 1000.0;
    let receipt = prove_info.receipt;
    let verify_time_ms = verify_receipt(&receipt, &journal_bytes);
    let receipt_bytes = bincode::serialize(&receipt).expect("serialize receipt");
    fs::write(&receipt_path, &receipt_bytes).expect("write receipt artifact");
    write_summary(
        &summary_path,
        "prove",
        &journal_bytes,
        &receipt_bytes,
        Some(prove_time_ms),
        verify_time_ms,
    );
}

fn verify(journal_path: PathBuf, receipt_path: PathBuf, summary_path: PathBuf) {
    let journal_bytes = read_expected_journal(&journal_path);
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
    let verify_time_ms = verify_receipt(&receipt, &journal_bytes);
    write_summary(
        &summary_path,
        "verify",
        &journal_bytes,
        &receipt_bytes,
        None,
        verify_time_ms,
    );
}

fn usage() -> ! {
    eprintln!("usage: host prove <journal-json> <receipt-out> <summary-out>");
    eprintln!("   or: host verify <journal-json> <receipt-in> <summary-out>");
    std::process::exit(2);
}

fn main() {
    let mut args = env::args().skip(1);
    let Some(command) = args.next() else { usage() };
    let Some(journal_path) = args.next().map(PathBuf::from) else {
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
        "prove" => prove(journal_path, receipt_path, summary_path),
        "verify" => verify(journal_path, receipt_path, summary_path),
        _ => usage(),
    }
}
