use std::process::ExitCode;

#[cfg(feature = "stwo-backend")]
use std::fs;
#[cfg(feature = "stwo-backend")]
use std::io::Read;
#[cfg(feature = "stwo-backend")]
use std::path::{Path, PathBuf};

#[cfg(feature = "stwo-backend")]
use serde::{Deserialize, Serialize};

#[cfg(feature = "stwo-backend")]
use sha2::{Digest, Sha256};

#[cfg(feature = "stwo-backend")]
use stwo::core::fields::m31::BaseField;
#[cfg(feature = "stwo-backend")]
use stwo::core::fields::qm31::SecureField;
#[cfg(feature = "stwo-backend")]
use stwo::core::pcs::PcsConfig;
#[cfg(feature = "stwo-backend")]
use stwo::core::proof::StarkProof;
#[cfg(feature = "stwo-backend")]
use stwo::core::vcs::blake2_hash::Blake2sHash;
#[cfg(feature = "stwo-backend")]
use stwo::core::vcs_lifted::blake2_merkle::Blake2sM31MerkleHasher;

#[cfg(feature = "stwo-backend")]
const MAX_ENVELOPE_JSON_BYTES: usize = 16 * 1024 * 1024;
#[cfg(feature = "stwo-backend")]
const MAX_PROOF_JSON_BYTES: usize = 2 * 1024 * 1024;
#[cfg(feature = "stwo-backend")]
const SCHEMA: &str = "zkai-stwo-local-binary-proof-accounting-cli-v1";
#[cfg(feature = "stwo-backend")]
const ACCOUNTING_DOMAIN: &str = "zkai:stwo:local-binary-proof-accounting";
#[cfg(feature = "stwo-backend")]
const ACCOUNTING_FORMAT_VERSION: &str = "v1";
#[cfg(feature = "stwo-backend")]
const ACCOUNTING_SOURCE: &str =
    "repo_owned_canonical_local_accounting_from_stwo_2_2_0_typed_StarkProof_fields";
#[cfg(feature = "stwo-backend")]
const UPSTREAM_SERIALIZATION_STATUS: &str =
    "NOT_UPSTREAM_STWO_SERIALIZATION_LOCAL_ACCOUNTING_RECORD_STREAM_ONLY";
#[cfg(feature = "stwo-backend")]
const PROOF_PAYLOAD_KIND: &str = "utf8_json_object_with_single_stark_proof_field";

#[cfg(feature = "stwo-backend")]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StwoProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[cfg(feature = "stwo-backend")]
#[derive(Serialize)]
struct AccountingRecord {
    path: &'static str,
    scalar_kind: &'static str,
    item_count: usize,
    item_size_bytes: usize,
    total_bytes: usize,
}

#[cfg(feature = "stwo-backend")]
#[derive(Default)]
struct ComponentBytes {
    trace_commitment_bytes: usize,
    trace_decommitment_merkle_path_bytes: usize,
    sampled_opened_value_bytes: usize,
    queried_value_bytes: usize,
    fri_layer_witness_bytes: usize,
    fri_last_layer_poly_bytes: usize,
    fri_commitment_bytes: usize,
    fri_decommitment_merkle_path_bytes: usize,
    proof_of_work_bytes: usize,
    config_bytes: usize,
}

#[cfg(feature = "stwo-backend")]
impl ComponentBytes {
    fn sum(&self) -> usize {
        self.trace_commitment_bytes
            + self.trace_decommitment_merkle_path_bytes
            + self.sampled_opened_value_bytes
            + self.queried_value_bytes
            + self.fri_layer_witness_bytes
            + self.fri_last_layer_poly_bytes
            + self.fri_commitment_bytes
            + self.fri_decommitment_merkle_path_bytes
            + self.proof_of_work_bytes
            + self.config_bytes
    }

    fn grouped(&self) -> serde_json::Value {
        serde_json::json!({
            "oods_samples": self.sampled_opened_value_bytes,
            "queries_values": self.queried_value_bytes,
            "fri_samples": self.fri_layer_witness_bytes + self.fri_last_layer_poly_bytes,
            "fri_decommitments": self.fri_commitment_bytes + self.fri_decommitment_merkle_path_bytes,
            "trace_decommitments": self.trace_commitment_bytes + self.trace_decommitment_merkle_path_bytes,
            "fixed_overhead": self.proof_of_work_bytes + self.config_bytes,
        })
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
        eprintln!("zkai_stwo_proof_binary_accounting requires --features stwo-backend");
        ExitCode::from(2)
    }
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.len() < 3 || args.first().and_then(|arg| arg.to_str()) != Some("--evidence-dir") {
        return Err(
            "usage: zkai_stwo_proof_binary_accounting --evidence-dir <dir> <envelope.json>..."
                .to_string(),
        );
    }
    args.remove(0);
    let evidence_dir = PathBuf::from(args.remove(0));
    let canonical_root = fs::canonicalize(&evidence_dir).map_err(|error| {
        format!(
            "failed to canonicalize evidence dir {}: {error}",
            evidence_dir.display()
        )
    })?;
    let paths = args.into_iter().map(PathBuf::from).collect::<Vec<_>>();
    let rows = paths
        .iter()
        .map(|path| proof_accounting_row(&canonical_root, path))
        .collect::<Result<Vec<_>, _>>()?;
    serde_json::to_string_pretty(&serde_json::json!({
        "schema": SCHEMA,
        "accounting_domain": ACCOUNTING_DOMAIN,
        "accounting_format_version": ACCOUNTING_FORMAT_VERSION,
        "accounting_source": ACCOUNTING_SOURCE,
        "upstream_stwo_serialization_status": UPSTREAM_SERIALIZATION_STATUS,
        "proof_payload_kind": PROOF_PAYLOAD_KIND,
        "safety": {
            "max_envelope_json_bytes": MAX_ENVELOPE_JSON_BYTES,
            "max_proof_json_bytes": MAX_PROOF_JSON_BYTES,
            "path_policy": "inputs_must_be_regular_non_symlink_files_inside_canonical_evidence_dir",
            "commitment": "sha256_over_repo_owned_canonical_local_binary_accounting_record_stream",
        },
        "size_constants": {
            "base_field_bytes": std::mem::size_of::<BaseField>(),
            "secure_field_bytes": std::mem::size_of::<SecureField>(),
            "blake2s_hash_bytes": std::mem::size_of::<Blake2sHash>(),
            "proof_of_work_bytes": std::mem::size_of::<u64>(),
            "pcs_config_bytes": std::mem::size_of::<PcsConfig>(),
        },
        "rows": rows,
    }))
    .map_err(|error| format!("failed to serialize summary: {error}"))
}

#[cfg(feature = "stwo-backend")]
fn proof_accounting_row(canonical_root: &Path, path: &Path) -> Result<serde_json::Value, String> {
    let envelope = read_contained_bounded_file(
        canonical_root,
        path,
        MAX_ENVELOPE_JSON_BYTES,
        "envelope JSON",
    )?;
    let envelope_value: serde_json::Value = serde_json::from_slice(&envelope)
        .map_err(|error| format!("failed to parse envelope JSON {}: {error}", path.display()))?;
    let proof_backend = required_string(&envelope_value, "proof_backend", path)?;
    if proof_backend != "stwo" {
        return Err(format!(
            "envelope {} proof_backend must be stwo",
            path.display()
        ));
    }
    let proof_backend_version = required_string(&envelope_value, "proof_backend_version", path)?;
    let statement_version = required_string(&envelope_value, "statement_version", path)?;
    let verifier_domain = optional_string(&envelope_value, "verifier_domain", path)?;
    let proof_schema_version = optional_string(&envelope_value, "proof_schema_version", path)?;
    let target_id = optional_string(&envelope_value, "target_id", path)?;
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
    let records = accounting_records(&proof);
    let component_bytes = component_bytes_from_records(&records);
    let component_sum_bytes = component_bytes.sum();
    let typed_size_estimate = proof.size_estimate();
    ensure_component_sum_matches_typed_estimate(component_sum_bytes, typed_size_estimate, path)?;
    let grouped_reconstruction = component_bytes.grouped();
    let stwo_grouped = proof.size_breakdown_estimate();
    let fixed_overhead = checked_fixed_overhead(
        typed_size_estimate,
        &[
            ("oods_samples", stwo_grouped.oods_samples),
            ("queries_values", stwo_grouped.queries_values),
            ("fri_samples", stwo_grouped.fri_samples),
            ("fri_decommitments", stwo_grouped.fri_decommitments),
            ("trace_decommitments", stwo_grouped.trace_decommitments),
        ],
        path,
    )?;
    let stwo_grouped_breakdown = serde_json::json!({
        "oods_samples": stwo_grouped.oods_samples,
        "queries_values": stwo_grouped.queries_values,
        "fri_samples": stwo_grouped.fri_samples,
        "fri_decommitments": stwo_grouped.fri_decommitments,
        "trace_decommitments": stwo_grouped.trace_decommitments,
        "fixed_overhead": fixed_overhead,
    });
    ensure_grouped_reconstruction_matches_stwo(
        &grouped_reconstruction,
        &stwo_grouped_breakdown,
        path,
    )?;
    let local_binary_stream = canonical_local_binary_accounting_stream(&records)?;
    let canonical_path = fs::canonicalize(path)
        .map_err(|error| format!("failed to canonicalize {}: {error}", path.display()))?;
    let relative_path = canonical_path
        .strip_prefix(canonical_root)
        .map_err(|_| format!("{} escaped evidence dir", path.display()))?;
    Ok(serde_json::json!({
        "path": path.to_string_lossy(),
        "evidence_relative_path": relative_path.to_string_lossy(),
        "envelope_sha256": sha256_hex(&envelope),
        "proof_sha256": sha256_hex(&proof_bytes),
        "proof_json_size_bytes": proof_bytes.len(),
        "envelope_metadata": {
            "proof_backend": proof_backend,
            "proof_backend_version": proof_backend_version,
            "statement_version": statement_version,
            "verifier_domain": verifier_domain,
            "proof_schema_version": proof_schema_version,
            "target_id": target_id,
        },
        "local_binary_accounting": {
            "format_domain": ACCOUNTING_DOMAIN,
            "format_version": ACCOUNTING_FORMAT_VERSION,
            "upstream_stwo_serialization_status": UPSTREAM_SERIALIZATION_STATUS,
            "records": records,
            "record_count": records.len(),
            "component_sum_bytes": component_sum_bytes,
            "typed_size_estimate_bytes": typed_size_estimate,
            "grouped_reconstruction": grouped_reconstruction,
            "stwo_grouped_breakdown": stwo_grouped_breakdown,
            "record_stream_bytes": local_binary_stream.len(),
            "record_stream_sha256": sha256_hex(&local_binary_stream),
            "json_over_local_typed_ratio": ratio(proof_bytes.len(), typed_size_estimate)?,
            "json_minus_local_typed_bytes": proof_bytes.len() as i64 - typed_size_estimate as i64,
        },
    }))
}

#[cfg(feature = "stwo-backend")]
fn required_string<'a>(
    envelope: &'a serde_json::Value,
    key: &str,
    path: &Path,
) -> Result<&'a str, String> {
    envelope
        .get(key)
        .and_then(|value| value.as_str())
        .ok_or_else(|| {
            format!(
                "envelope {} missing required string field {key}",
                path.display()
            )
        })
}

#[cfg(feature = "stwo-backend")]
fn optional_string(
    envelope: &serde_json::Value,
    key: &str,
    path: &Path,
) -> Result<Option<String>, String> {
    match envelope.get(key) {
        None | Some(serde_json::Value::Null) => Ok(None),
        Some(value) => value
            .as_str()
            .map(|text| Some(text.to_string()))
            .ok_or_else(|| format!("envelope {} field {key} must be a string", path.display())),
    }
}

#[cfg(feature = "stwo-backend")]
fn accounting_records(proof: &StarkProof<Blake2sM31MerkleHasher>) -> Vec<AccountingRecord> {
    let pcs = &proof.0;
    let fri = &pcs.fri_proof;
    let hash_bytes = std::mem::size_of::<Blake2sHash>();
    let base_field_bytes = std::mem::size_of::<BaseField>();
    let secure_field_bytes = std::mem::size_of::<SecureField>();
    let proof_of_work_bytes = std::mem::size_of::<u64>();
    let pcs_config_bytes = std::mem::size_of::<PcsConfig>();
    let trace_hash_witness_count = pcs
        .decommitments
        .iter()
        .map(|decommitment| decommitment.hash_witness.len())
        .sum::<usize>();
    let sampled_opened_value_count = pcs
        .sampled_values
        .iter()
        .flat_map(|tree| tree.iter())
        .map(Vec::len)
        .sum::<usize>();
    let queried_value_count = pcs
        .queried_values
        .iter()
        .flat_map(|tree| tree.iter())
        .map(Vec::len)
        .sum::<usize>();
    let first_layer_fri_witness_count = fri.first_layer.fri_witness.len();
    let inner_layer_fri_witness_count = fri
        .inner_layers
        .iter()
        .map(|layer| layer.fri_witness.len())
        .sum::<usize>();
    let first_layer_fri_decommitment_count = fri.first_layer.decommitment.hash_witness.len();
    let inner_layer_fri_decommitment_count = fri
        .inner_layers
        .iter()
        .map(|layer| layer.decommitment.hash_witness.len())
        .sum::<usize>();
    vec![
        record(
            "pcs.commitments",
            "blake2s_hash",
            pcs.commitments.len(),
            hash_bytes,
        ),
        record(
            "pcs.trace_decommitments.hash_witness",
            "blake2s_hash",
            trace_hash_witness_count,
            hash_bytes,
        ),
        record(
            "pcs.sampled_values",
            "secure_field",
            sampled_opened_value_count,
            secure_field_bytes,
        ),
        record(
            "pcs.queried_values",
            "base_field",
            queried_value_count,
            base_field_bytes,
        ),
        record(
            "pcs.fri.first_layer.fri_witness",
            "secure_field",
            first_layer_fri_witness_count,
            secure_field_bytes,
        ),
        record(
            "pcs.fri.inner_layers.fri_witness",
            "secure_field",
            inner_layer_fri_witness_count,
            secure_field_bytes,
        ),
        record(
            "pcs.fri.last_layer_poly",
            "secure_field",
            fri.last_layer_poly.len(),
            secure_field_bytes,
        ),
        record(
            "pcs.fri.first_layer.commitment",
            "blake2s_hash",
            1,
            hash_bytes,
        ),
        record(
            "pcs.fri.inner_layers.commitments",
            "blake2s_hash",
            fri.inner_layers.len(),
            hash_bytes,
        ),
        record(
            "pcs.fri.first_layer.decommitment.hash_witness",
            "blake2s_hash",
            first_layer_fri_decommitment_count,
            hash_bytes,
        ),
        record(
            "pcs.fri.inner_layers.decommitment.hash_witness",
            "blake2s_hash",
            inner_layer_fri_decommitment_count,
            hash_bytes,
        ),
        record("pcs.proof_of_work", "u64_le", 1, proof_of_work_bytes),
        record("pcs.config", "pcs_config", 1, pcs_config_bytes),
    ]
}

#[cfg(feature = "stwo-backend")]
fn record(
    path: &'static str,
    scalar_kind: &'static str,
    item_count: usize,
    item_size_bytes: usize,
) -> AccountingRecord {
    AccountingRecord {
        path,
        scalar_kind,
        item_count,
        item_size_bytes,
        total_bytes: item_count * item_size_bytes,
    }
}

#[cfg(feature = "stwo-backend")]
fn component_bytes_from_records(records: &[AccountingRecord]) -> ComponentBytes {
    let mut bytes = ComponentBytes::default();
    for record in records {
        match record.path {
            "pcs.commitments" => bytes.trace_commitment_bytes = record.total_bytes,
            "pcs.trace_decommitments.hash_witness" => {
                bytes.trace_decommitment_merkle_path_bytes = record.total_bytes;
            }
            "pcs.sampled_values" => bytes.sampled_opened_value_bytes = record.total_bytes,
            "pcs.queried_values" => bytes.queried_value_bytes = record.total_bytes,
            "pcs.fri.first_layer.fri_witness" | "pcs.fri.inner_layers.fri_witness" => {
                bytes.fri_layer_witness_bytes += record.total_bytes;
            }
            "pcs.fri.last_layer_poly" => bytes.fri_last_layer_poly_bytes = record.total_bytes,
            "pcs.fri.first_layer.commitment" | "pcs.fri.inner_layers.commitments" => {
                bytes.fri_commitment_bytes += record.total_bytes;
            }
            "pcs.fri.first_layer.decommitment.hash_witness"
            | "pcs.fri.inner_layers.decommitment.hash_witness" => {
                bytes.fri_decommitment_merkle_path_bytes += record.total_bytes;
            }
            "pcs.proof_of_work" => bytes.proof_of_work_bytes = record.total_bytes,
            "pcs.config" => bytes.config_bytes = record.total_bytes,
            _ => {}
        }
    }
    bytes
}

#[cfg(feature = "stwo-backend")]
fn checked_fixed_overhead(
    typed_size_estimate: usize,
    grouped_components: &[(&str, usize)],
    path: &Path,
) -> Result<usize, String> {
    let mut remaining = typed_size_estimate;
    for (name, value) in grouped_components {
        remaining = remaining.checked_sub(*value).ok_or_else(|| {
            format!(
                "Stwo grouped breakdown exceeds typed size estimate for {} while subtracting {name}: estimate {}, remaining {}, component {}",
                path.display(),
                typed_size_estimate,
                remaining,
                value
            )
        })?;
    }
    Ok(remaining)
}

#[cfg(feature = "stwo-backend")]
fn ensure_component_sum_matches_typed_estimate(
    component_sum_bytes: usize,
    typed_size_estimate: usize,
    path: &Path,
) -> Result<(), String> {
    if component_sum_bytes != typed_size_estimate {
        return Err(format!(
            "local component sum does not match Stwo typed estimate for {}: components {}, estimate {}",
            path.display(),
            component_sum_bytes,
            typed_size_estimate
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn ensure_grouped_reconstruction_matches_stwo(
    grouped_reconstruction: &serde_json::Value,
    stwo_grouped_breakdown: &serde_json::Value,
    path: &Path,
) -> Result<(), String> {
    if grouped_reconstruction != stwo_grouped_breakdown {
        return Err(format!(
            "local grouped reconstruction drift for {}",
            path.display()
        ));
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn canonical_local_binary_accounting_stream(
    records: &[AccountingRecord],
) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    push_string(&mut bytes, ACCOUNTING_DOMAIN)?;
    push_string(&mut bytes, ACCOUNTING_FORMAT_VERSION)?;
    push_u64(&mut bytes, records.len())?;
    for record in records {
        push_string(&mut bytes, record.path)?;
        push_string(&mut bytes, record.scalar_kind)?;
        push_u64(&mut bytes, record.item_count)?;
        push_u64(&mut bytes, record.item_size_bytes)?;
        push_u64(&mut bytes, record.total_bytes)?;
    }
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn push_string(bytes: &mut Vec<u8>, value: &str) -> Result<(), String> {
    push_u64(bytes, value.len())?;
    bytes.extend_from_slice(value.as_bytes());
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn push_u64(bytes: &mut Vec<u8>, value: usize) -> Result<(), String> {
    let value = u64::try_from(value).map_err(|_| "usize does not fit u64".to_string())?;
    bytes.extend_from_slice(&value.to_le_bytes());
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn read_contained_bounded_file(
    canonical_root: &Path,
    path: &Path,
    max_bytes: usize,
    label: &str,
) -> Result<Vec<u8>, String> {
    let symlink_metadata = fs::symlink_metadata(path)
        .map_err(|error| format!("failed to lstat {} {}: {error}", label, path.display()))?;
    if symlink_metadata.file_type().is_symlink() {
        return Err(format!(
            "{} {} must not be a symlink",
            label,
            path.display()
        ));
    }
    let canonical_path = fs::canonicalize(path).map_err(|error| {
        format!(
            "failed to canonicalize {} {}: {error}",
            label,
            path.display()
        )
    })?;
    if !canonical_path.starts_with(canonical_root) {
        return Err(format!(
            "{} {} escapes evidence dir {}",
            label,
            path.display(),
            canonical_root.display()
        ));
    }
    let metadata = fs::metadata(&canonical_path)
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
    let file = fs::File::open(&canonical_path)
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

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn canonical_stream_is_deterministic_and_domain_separated() {
        let records = vec![
            record("pcs.commitments", "blake2s_hash", 3, 32),
            record("pcs.config", "pcs_config", 1, 4),
        ];
        let first = canonical_local_binary_accounting_stream(&records).unwrap();
        let second = canonical_local_binary_accounting_stream(&records).unwrap();
        assert_eq!(first, second);
        assert_ne!(sha256_hex(&first), sha256_hex(b""));
        assert!(first
            .windows(ACCOUNTING_DOMAIN.len())
            .any(|window| { window == ACCOUNTING_DOMAIN.as_bytes() }));
    }

    #[test]
    fn contained_reader_rejects_paths_outside_root() {
        let root = tempfile::tempdir().unwrap();
        let outside = tempfile::NamedTempFile::new().unwrap();
        let canonical_root = fs::canonicalize(root.path()).unwrap();
        let error = read_contained_bounded_file(&canonical_root, outside.path(), 1024, "test file")
            .unwrap_err();
        assert!(error.contains("escapes evidence dir"));
    }

    #[cfg(unix)]
    #[test]
    fn contained_reader_rejects_symlink_input() {
        let root = tempfile::tempdir().unwrap();
        let target_path = root.path().join("target.json");
        fs::write(&target_path, b"{}").unwrap();
        let link_path = root.path().join("link.json");
        std::os::unix::fs::symlink(&target_path, &link_path).unwrap();
        let canonical_root = fs::canonicalize(root.path()).unwrap();
        let error = read_contained_bounded_file(&canonical_root, &link_path, 1024, "test file")
            .unwrap_err();
        assert!(error.contains("must not be a symlink"));
    }

    #[test]
    fn contained_reader_enforces_byte_cap() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("large.json");
        let mut file = fs::File::create(&path).unwrap();
        file.write_all(b"abcdef").unwrap();
        let canonical_root = fs::canonicalize(root.path()).unwrap();
        let error =
            read_contained_bounded_file(&canonical_root, &path, 5, "test file").unwrap_err();
        assert!(error.contains("exceeds max size"));
    }

    #[test]
    fn fixed_overhead_rejects_underflow() {
        let error = checked_fixed_overhead(
            7,
            &[("oods_samples", 3), ("queries_values", 5)],
            Path::new("fixture.envelope.json"),
        )
        .unwrap_err();
        assert!(error.contains("exceeds typed size estimate"));
    }

    #[test]
    fn fixed_overhead_returns_remaining_bytes() {
        let fixed_overhead = checked_fixed_overhead(
            16,
            &[
                ("oods_samples", 3),
                ("queries_values", 4),
                ("fri_samples", 5),
            ],
            Path::new("fixture.envelope.json"),
        )
        .unwrap();
        assert_eq!(fixed_overhead, 4);
    }

    #[test]
    fn component_sum_check_rejects_typed_estimate_mismatch() {
        let error =
            ensure_component_sum_matches_typed_estimate(16, 15, Path::new("fixture.envelope.json"))
                .unwrap_err();
        assert!(error.contains("component sum does not match"));
        ensure_component_sum_matches_typed_estimate(16, 16, Path::new("fixture.envelope.json"))
            .unwrap();
    }

    #[test]
    fn grouped_reconstruction_check_rejects_stwo_breakdown_mismatch() {
        let grouped_reconstruction = serde_json::json!({
            "oods_samples": 3,
            "queries_values": 5,
            "fri_samples": 7,
            "fri_decommitments": 11,
            "trace_decommitments": 13,
            "fixed_overhead": 17,
        });
        let mut stwo_grouped_breakdown = grouped_reconstruction.clone();
        stwo_grouped_breakdown["fri_samples"] = serde_json::json!(8);

        let error = ensure_grouped_reconstruction_matches_stwo(
            &grouped_reconstruction,
            &stwo_grouped_breakdown,
            Path::new("fixture.envelope.json"),
        )
        .unwrap_err();
        assert!(error.contains("grouped reconstruction drift"));
        ensure_grouped_reconstruction_matches_stwo(
            &grouped_reconstruction,
            &grouped_reconstruction,
            Path::new("fixture.envelope.json"),
        )
        .unwrap();
    }

    #[test]
    fn ratio_is_rounded_and_rejects_zero_denominator() {
        assert_eq!(ratio(1, 3).unwrap(), 0.333333);
        assert!(ratio(1, 0).is_err());
    }
}
