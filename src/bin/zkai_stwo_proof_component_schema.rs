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
const STABLE_BINARY_SERIALIZER_STATUS: &str =
    "NO_GO_STABLE_BINARY_STWO_PROOF_SERIALIZER_NOT_EXPOSED";
#[cfg(feature = "stwo-backend")]
const COMPONENT_SCHEMA_STATUS: &str =
    "GO_FINE_GRAINED_TYPED_COMPONENT_SCHEMA_WITH_STABLE_BINARY_SERIALIZER_NO_GO";

#[cfg(feature = "stwo-backend")]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StwoProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[cfg(feature = "stwo-backend")]
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

    fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "trace_commitment_bytes": self.trace_commitment_bytes,
            "trace_decommitment_merkle_path_bytes": self.trace_decommitment_merkle_path_bytes,
            "sampled_opened_value_bytes": self.sampled_opened_value_bytes,
            "queried_value_bytes": self.queried_value_bytes,
            "fri_layer_witness_bytes": self.fri_layer_witness_bytes,
            "fri_last_layer_poly_bytes": self.fri_last_layer_poly_bytes,
            "fri_commitment_bytes": self.fri_commitment_bytes,
            "fri_decommitment_merkle_path_bytes": self.fri_decommitment_merkle_path_bytes,
            "proof_of_work_bytes": self.proof_of_work_bytes,
            "config_bytes": self.config_bytes,
        })
    }
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
    eprintln!("zkai_stwo_proof_component_schema requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let paths = std::env::args_os()
        .skip(1)
        .map(PathBuf::from)
        .collect::<Vec<_>>();
    if paths.is_empty() {
        return Err("usage: zkai_stwo_proof_component_schema <envelope.json>...".to_string());
    }
    let rows = paths
        .iter()
        .map(|path| component_schema_row(path))
        .collect::<Result<Vec<_>, _>>()?;
    serde_json::to_string_pretty(&serde_json::json!({
        "schema": "zkai-stwo-proof-component-schema-cli-v1",
        "accounting_source": "public_stwo_2_2_0_stark_proof_field_traversal_and_mem_size_estimates",
        "proof_payload_kind": "utf8_json_object_with_single_stark_proof_field",
        "stable_binary_serializer_status": STABLE_BINARY_SERIALIZER_STATUS,
        "component_schema_status": COMPONENT_SCHEMA_STATUS,
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
fn component_schema_row(path: &Path) -> Result<serde_json::Value, String> {
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
    let stwo_grouped = proof.size_breakdown_estimate();
    let typed_size_estimate = proof.size_estimate();
    let components = component_bytes(&proof);
    let component_sum_bytes = components.sum();
    if component_sum_bytes != typed_size_estimate {
        return Err(format!(
            "component sum does not match typed estimate for {}: components {}, estimate {}",
            path.display(),
            component_sum_bytes,
            typed_size_estimate
        ));
    }

    Ok(serde_json::json!({
        "path": path.to_string_lossy(),
        "proof_sha256": sha256_hex(&proof_bytes),
        "json_proof_size_bytes": proof_bytes.len(),
        "typed_size_estimate_bytes": typed_size_estimate,
        "component_bytes": components.to_json(),
        "component_sum_bytes": component_sum_bytes,
        "grouped_reconstruction": {
            "oods_samples": components.sampled_opened_value_bytes,
            "queries_values": components.queried_value_bytes,
            "fri_samples": components.fri_layer_witness_bytes + components.fri_last_layer_poly_bytes,
            "fri_decommitments": components.fri_commitment_bytes + components.fri_decommitment_merkle_path_bytes,
            "trace_decommitments": components.trace_commitment_bytes + components.trace_decommitment_merkle_path_bytes,
            "fixed_overhead": components.proof_of_work_bytes + components.config_bytes,
        },
        "stwo_grouped_breakdown": {
            "oods_samples": stwo_grouped.oods_samples,
            "queries_values": stwo_grouped.queries_values,
            "fri_samples": stwo_grouped.fri_samples,
            "fri_decommitments": stwo_grouped.fri_decommitments,
            "trace_decommitments": stwo_grouped.trace_decommitments,
            "fixed_overhead": typed_size_estimate
                - stwo_grouped.oods_samples
                - stwo_grouped.queries_values
                - stwo_grouped.fri_samples
                - stwo_grouped.fri_decommitments
                - stwo_grouped.trace_decommitments,
        },
        "json_over_typed_size_ratio": ratio(proof_bytes.len(), typed_size_estimate)?,
        "json_minus_typed_size_bytes": proof_bytes.len() as i64 - typed_size_estimate as i64,
    }))
}

#[cfg(feature = "stwo-backend")]
fn component_bytes(proof: &StarkProof<Blake2sM31MerkleHasher>) -> ComponentBytes {
    let pcs = &proof.0;
    let hash_bytes = std::mem::size_of::<Blake2sHash>();
    let base_field_bytes = std::mem::size_of::<BaseField>();
    let secure_field_bytes = std::mem::size_of::<SecureField>();
    let fri = &pcs.fri_proof;

    ComponentBytes {
        trace_commitment_bytes: pcs.commitments.len() * hash_bytes,
        trace_decommitment_merkle_path_bytes: pcs
            .decommitments
            .iter()
            .map(|decommitment| decommitment.hash_witness.len() * hash_bytes)
            .sum(),
        sampled_opened_value_bytes: pcs
            .sampled_values
            .iter()
            .flat_map(|tree| tree.iter())
            .map(|values| values.len() * secure_field_bytes)
            .sum(),
        queried_value_bytes: pcs
            .queried_values
            .iter()
            .flat_map(|tree| tree.iter())
            .map(|values| values.len() * base_field_bytes)
            .sum(),
        fri_layer_witness_bytes: fri.first_layer.fri_witness.len() * secure_field_bytes
            + fri
                .inner_layers
                .iter()
                .map(|layer| layer.fri_witness.len() * secure_field_bytes)
                .sum::<usize>(),
        fri_last_layer_poly_bytes: fri.last_layer_poly.len() * secure_field_bytes,
        fri_commitment_bytes: hash_bytes + fri.inner_layers.len() * hash_bytes,
        fri_decommitment_merkle_path_bytes: fri.first_layer.decommitment.hash_witness.len()
            * hash_bytes
            + fri
                .inner_layers
                .iter()
                .map(|layer| layer.decommitment.hash_witness.len() * hash_bytes)
                .sum::<usize>(),
        proof_of_work_bytes: std::mem::size_of::<u64>(),
        config_bytes: std::mem::size_of::<PcsConfig>(),
    }
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
