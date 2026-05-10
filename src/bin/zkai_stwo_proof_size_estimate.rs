use std::process::ExitCode;

#[cfg(feature = "stwo-backend")]
use std::fs;
#[cfg(feature = "stwo-backend")]
use std::io::Read;
#[cfg(feature = "stwo-backend")]
use std::path::{Path, PathBuf};

#[cfg(feature = "stwo-backend")]
use serde::Deserialize;

#[cfg(feature = "stwo-backend")]
use sha2::{Digest, Sha256};

#[cfg(feature = "stwo-backend")]
use stwo::core::proof::StarkProof;
#[cfg(feature = "stwo-backend")]
use stwo::core::vcs_lifted::blake2_merkle::Blake2sM31MerkleHasher;

#[cfg(feature = "stwo-backend")]
const MAX_ENVELOPE_JSON_BYTES: usize = 16 * 1024 * 1024;
#[cfg(feature = "stwo-backend")]
const MAX_PROOF_JSON_BYTES: usize = 2 * 1024 * 1024;
#[cfg(feature = "stwo-backend")]
const BREAKDOWN_STATUS: &str = "GO_GROUPED_STWO_TYPED_BREAKDOWN_FINE_GRAINED_BINARY_SPLITS_NO_GO";
#[cfg(feature = "stwo-backend")]
const UNEXPOSED_FINE_GRAINED_CATEGORIES: &[&str] = &[
    "binary_commitment_bytes",
    "binary_sampled_opened_value_bytes",
    "binary_decommitment_merkle_path_bytes",
    "binary_fri_witness_bytes",
    "binary_fri_commitment_bytes",
    "proof_of_work_bytes",
    "config_bytes",
];

#[cfg(feature = "stwo-backend")]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StwoProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[cfg(feature = "stwo-backend")]
fn main() -> ExitCode {
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
fn main() -> ExitCode {
    eprintln!("zkai_stwo_proof_size_estimate requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let paths = std::env::args_os()
        .skip(1)
        .map(PathBuf::from)
        .collect::<Vec<_>>();
    if paths.is_empty() {
        return Err("usage: zkai_stwo_proof_size_estimate <envelope.json>...".to_string());
    }
    let rows = paths
        .iter()
        .map(|path| proof_size_row(path))
        .collect::<Result<Vec<_>, _>>()?;
    serde_json::to_string_pretty(&serde_json::json!({
        "schema": "zkai-stwo-proof-size-estimate-cli-v1",
        "accounting_source": "stwo::core::proof::StarkProof::size_estimate_and_size_breakdown_estimate",
        "proof_payload_kind": "utf8_json_object_with_single_stark_proof_field",
        "stable_binary_serializer_status": "NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED",
        "breakdown_status": BREAKDOWN_STATUS,
        "unexposed_fine_grained_categories": UNEXPOSED_FINE_GRAINED_CATEGORIES,
        "rows": rows,
    }))
    .map_err(|error| format!("failed to serialize summary: {error}"))
}

#[cfg(feature = "stwo-backend")]
fn proof_size_row(path: &Path) -> Result<serde_json::Value, String> {
    let envelope = read_bounded_file(path, MAX_ENVELOPE_JSON_BYTES, "envelope JSON")?;
    let envelope_value: serde_json::Value = serde_json::from_slice(&envelope)
        .map_err(|error| format!("failed to parse envelope JSON {}: {error}", path.display()))?;
    let proof_values = envelope_value
        .get("proof")
        .and_then(|value| value.as_array())
        .ok_or_else(|| format!("envelope {} missing proof byte array", path.display()))?;
    if proof_values.is_empty() || proof_values.len() > MAX_PROOF_JSON_BYTES {
        return Err(format!(
            "proof byte array length outside cap for {}: {}",
            path.display(),
            proof_values.len()
        ));
    }
    let mut proof_bytes = Vec::with_capacity(proof_values.len());
    for (index, value) in proof_values.iter().enumerate() {
        let byte = value.as_u64().ok_or_else(|| {
            format!(
                "proof byte {index} in envelope {} is not an unsigned integer",
                path.display()
            )
        })?;
        if byte > 255 {
            return Err(format!(
                "proof byte {index} in envelope {} exceeds u8",
                path.display()
            ));
        }
        proof_bytes.push(byte as u8);
    }
    let payload: StwoProofPayload = serde_json::from_slice(&proof_bytes).map_err(|error| {
        format!(
            "failed to parse Stwo proof payload {}: {error}",
            path.display()
        )
    })?;
    let proof = payload.stark_proof;
    let breakdown = proof.size_breakdown_estimate();
    let typed_size_estimate = proof.size_estimate();
    let typed_breakdown_sum = breakdown.oods_samples
        + breakdown.queries_values
        + breakdown.fri_samples
        + breakdown.fri_decommitments
        + breakdown.trace_decommitments;
    if typed_size_estimate < typed_breakdown_sum {
        return Err(format!(
            "Stwo typed size estimate underflows breakdown for {}: estimate {}, breakdown sum {}",
            path.display(),
            typed_size_estimate,
            typed_breakdown_sum
        ));
    }
    if typed_size_estimate == 0 {
        return Err(format!(
            "Stwo typed size estimate is zero for {}",
            path.display()
        ));
    }
    let fixed_unclassified_overhead = typed_size_estimate - typed_breakdown_sum;
    let json_over_typed_size_ratio = ratio(proof_bytes.len(), typed_size_estimate)?;
    Ok(serde_json::json!({
        "path": path.to_string_lossy(),
        "proof_sha256": sha256_hex(&proof_bytes),
        "json_proof_size_bytes": proof_bytes.len(),
        "typed_size_estimate_bytes": typed_size_estimate,
        "typed_breakdown": {
            "oods_samples": breakdown.oods_samples,
            "queries_values": breakdown.queries_values,
            "fri_samples": breakdown.fri_samples,
            "fri_decommitments": breakdown.fri_decommitments,
            "trace_decommitments": breakdown.trace_decommitments,
            "fixed_unclassified_overhead": fixed_unclassified_overhead,
        },
        "typed_breakdown_sum_bytes": typed_breakdown_sum,
        "json_over_typed_size_ratio": json_over_typed_size_ratio,
        "json_minus_typed_size_bytes": proof_bytes.len() as i64 - typed_size_estimate as i64,
    }))
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_file(path: &Path, max_bytes: usize, label: &str) -> Result<Vec<u8>, String> {
    let metadata = fs::metadata(path)
        .map_err(|error| format!("failed to stat {} {}: {error}", label, path.display()))?;
    if !metadata.is_file() {
        return Err(format!(
            "{} {} is not a regular file",
            label,
            path.display()
        ));
    }
    if metadata.len() > max_bytes as u64 {
        return Err(format!(
            "{label} exceeds max size: got {} bytes, limit {} bytes",
            metadata.len(),
            max_bytes
        ));
    }
    let file = fs::File::open(path)
        .map_err(|error| format!("failed to open {} {}: {error}", label, path.display()))?;
    let mut raw = Vec::new();
    file.take(max_bytes.saturating_add(1) as u64)
        .read_to_end(&mut raw)
        .map_err(|error| format!("failed to read {} {}: {error}", label, path.display()))?;
    if raw.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got more than {max_bytes} bytes, limit {max_bytes} bytes"
        ));
    }
    Ok(raw)
}

#[cfg(feature = "stwo-backend")]
fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(feature = "stwo-backend")]
fn ratio(numerator: usize, denominator: usize) -> Result<f64, String> {
    if denominator == 0 {
        return Err("ratio denominator must be positive".to_string());
    }
    let scaled = (numerator as f64 / denominator as f64) * 1_000_000.0;
    Ok(scaled.round() / 1_000_000.0)
}
