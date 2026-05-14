use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{self, ExitCode};
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    prove_zkai_d128_rmsnorm_public_row_envelope,
    prove_zkai_d128_rmsnorm_to_projection_bridge_envelope,
    verify_zkai_d128_rmsnorm_public_row_envelope,
    verify_zkai_d128_rmsnorm_to_projection_bridge_envelope,
    zkai_d128_rmsnorm_public_row_input_from_json_str,
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str,
    ZkAiD128RmsnormPublicRowProofEnvelope, ZkAiD128RmsnormToProjectionBridgeEnvelope,
    ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
};

#[cfg(feature = "stwo-backend")]
const MAX_ENVELOPE_JSON_BYTES: usize = 4 * 1024 * 1024;

#[cfg(feature = "stwo-backend")]
fn main() -> ExitCode {
    match run() {
        Ok(summary) => {
            println!("{summary}");
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
    eprintln!("zkai_d128_selected_two_slice_proof_envelopes requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_d128_selected_two_slice_proof_envelopes prove <rmsnorm_input.json> <rmsnorm_envelope.json> <bridge_input.json> <bridge_envelope.json> | verify <rmsnorm_envelope.json> <bridge_envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "prove" => {
            if args.len() != 4 {
                return Err("usage: prove <rmsnorm_input.json> <rmsnorm_envelope.json> <bridge_input.json> <bridge_envelope.json>".to_string());
            }
            let rmsnorm_input_path = PathBuf::from(&args[0]);
            let rmsnorm_envelope_path = PathBuf::from(&args[1]);
            let bridge_input_path = PathBuf::from(&args[2]);
            let bridge_envelope_path = PathBuf::from(&args[3]);

            let rmsnorm_input = read_input_text(
                &rmsnorm_input_path,
                ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
                "rmsnorm input JSON",
            )?;
            let rmsnorm_input = zkai_d128_rmsnorm_public_row_input_from_json_str(&rmsnorm_input)
                .map_err(|error| error.to_string())?;
            let rmsnorm_envelope = prove_zkai_d128_rmsnorm_public_row_envelope(&rmsnorm_input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_rmsnorm_public_row_envelope(&rmsnorm_envelope)
                .map_err(|error| error.to_string())?;

            let bridge_input = read_input_text(
                &bridge_input_path,
                ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
                "bridge input JSON",
            )?;
            let bridge_input =
                zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(&bridge_input)
                    .map_err(|error| error.to_string())?;
            let bridge_envelope =
                prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&bridge_input)
                    .map_err(|error| error.to_string())?;
            verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&bridge_envelope)
                .map_err(|error| error.to_string())?;

            let rmsnorm_bytes = envelope_json_bytes(&rmsnorm_envelope, "rmsnorm envelope")?;
            let bridge_bytes = envelope_json_bytes(&bridge_envelope, "bridge envelope")?;
            atomic_write_file(&rmsnorm_envelope_path, &rmsnorm_bytes, "rmsnorm envelope")?;
            atomic_write_file(&bridge_envelope_path, &bridge_bytes, "bridge envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-selected-two-slice-proof-envelopes-cli-summary-v1",
                "mode": "prove",
                "rmsnorm_input_path": rmsnorm_input_path.display().to_string(),
                "rmsnorm_envelope_path": rmsnorm_envelope_path.display().to_string(),
                "rmsnorm_proof_size_bytes": rmsnorm_envelope.proof.len(),
                "rmsnorm_envelope_size_bytes": rmsnorm_bytes.len(),
                "rmsnorm_statement_commitment": rmsnorm_envelope.input.statement_commitment,
                "bridge_input_path": bridge_input_path.display().to_string(),
                "bridge_envelope_path": bridge_envelope_path.display().to_string(),
                "bridge_proof_size_bytes": bridge_envelope.proof.len(),
                "bridge_envelope_size_bytes": bridge_bytes.len(),
                "bridge_statement_commitment": bridge_envelope.input.statement_commitment,
                "selected_slice_count": 2,
                "claim_boundary": "selected_inner_stwo_proof_envelopes_not_native_outer_verifier_execution",
            })
            .to_string())
        }
        "verify" => {
            if args.len() != 2 {
                return Err(
                    "usage: verify <rmsnorm_envelope.json> <bridge_envelope.json>".to_string(),
                );
            }
            let rmsnorm_envelope_path = PathBuf::from(&args[0]);
            let bridge_envelope_path = PathBuf::from(&args[1]);
            let rmsnorm_raw = read_bounded_file(
                &rmsnorm_envelope_path,
                MAX_ENVELOPE_JSON_BYTES,
                "rmsnorm envelope JSON",
            )?;
            let rmsnorm_envelope: ZkAiD128RmsnormPublicRowProofEnvelope =
                serde_json::from_slice(&rmsnorm_raw)
                    .map_err(|error| format!("failed to parse rmsnorm envelope: {error}"))?;
            verify_zkai_d128_rmsnorm_public_row_envelope(&rmsnorm_envelope)
                .map_err(|error| error.to_string())?;

            let bridge_raw = read_bounded_file(
                &bridge_envelope_path,
                MAX_ENVELOPE_JSON_BYTES,
                "bridge envelope JSON",
            )?;
            let bridge_envelope: ZkAiD128RmsnormToProjectionBridgeEnvelope =
                serde_json::from_slice(&bridge_raw)
                    .map_err(|error| format!("failed to parse bridge envelope: {error}"))?;
            verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&bridge_envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-selected-two-slice-proof-envelopes-cli-summary-v1",
                "mode": "verify",
                "rmsnorm_envelope_path": rmsnorm_envelope_path.display().to_string(),
                "rmsnorm_proof_size_bytes": rmsnorm_envelope.proof.len(),
                "rmsnorm_envelope_size_bytes": rmsnorm_raw.len(),
                "rmsnorm_statement_commitment": rmsnorm_envelope.input.statement_commitment,
                "bridge_envelope_path": bridge_envelope_path.display().to_string(),
                "bridge_proof_size_bytes": bridge_envelope.proof.len(),
                "bridge_envelope_size_bytes": bridge_raw.len(),
                "bridge_statement_commitment": bridge_envelope.input.statement_commitment,
                "selected_slice_count": 2,
                "verified": true,
                "claim_boundary": "selected_inner_stwo_proof_envelopes_not_native_outer_verifier_execution",
            })
            .to_string())
        }
        _ => Err(format!("unknown mode: {mode}")),
    }
}

#[cfg(feature = "stwo-backend")]
fn read_input_text(path: &Path, max_bytes: usize, label: &str) -> Result<String, String> {
    let raw = read_bounded_file(path, max_bytes, label)?;
    String::from_utf8(raw)
        .map_err(|error| format!("failed to decode {} {}: {error}", label, path.display()))
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_file(path: &Path, max_bytes: usize, label: &str) -> Result<Vec<u8>, String> {
    let file = fs::File::open(path)
        .map_err(|error| format!("failed to open {} {}: {error}", label, path.display()))?;
    let metadata = file.metadata().map_err(|error| {
        format!(
            "failed to stat opened {} {}: {error}",
            label,
            path.display()
        )
    })?;
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
fn envelope_json_bytes<T: serde::Serialize>(envelope: &T, label: &str) -> Result<Vec<u8>, String> {
    let bytes = serde_json::to_vec_pretty(envelope)
        .map_err(|error| format!("failed to serialize {label}: {error}"))?;
    if bytes.len() > MAX_ENVELOPE_JSON_BYTES {
        return Err(format!(
            "{label} JSON exceeds max size: got {} bytes, limit {} bytes",
            bytes.len(),
            MAX_ENVELOPE_JSON_BYTES
        ));
    }
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn atomic_write_file(path: &Path, bytes: &[u8], label: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent).map_err(|error| {
        format!(
            "failed to create output parent {} for {} {}: {error}",
            parent.display(),
            label,
            path.display()
        )
    })?;
    let file_name = path
        .file_name()
        .ok_or_else(|| format!("{} {} has no file name", label, path.display()))?;
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("system time before epoch while writing {}: {error}", label))?
        .as_nanos();
    let tmp_path = parent.join(format!(
        ".{}.{}.{}.tmp",
        file_name.to_string_lossy(),
        process::id(),
        nonce
    ));
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&tmp_path)
        .map_err(|error| {
            format!(
                "failed to create temp {} {}: {error}",
                label,
                tmp_path.display()
            )
        })?;
    if let Err(error) = file.write_all(bytes).and_then(|_| file.sync_all()) {
        let _ = fs::remove_file(&tmp_path);
        return Err(format!(
            "failed to write temp {} {}: {error}",
            label,
            tmp_path.display()
        ));
    }
    drop(file);
    publish_temp_file(&tmp_path, path, label)?;
    if let Err(error) = sync_parent_directory(parent, label, path) {
        eprintln!("warning: {error}");
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn publish_temp_file(tmp_path: &Path, path: &Path, label: &str) -> Result<(), String> {
    match fs::rename(tmp_path, path) {
        Ok(()) => Ok(()),
        Err(first_error) if path.exists() => {
            if let Err(remove_error) = fs::remove_file(path) {
                let _ = fs::remove_file(tmp_path);
                return Err(format!(
                    "failed to replace existing {} {} after publish error {first_error}: {remove_error}",
                    label,
                    path.display()
                ));
            }
            if let Err(second_error) = fs::rename(tmp_path, path) {
                let _ = fs::remove_file(tmp_path);
                return Err(format!(
                    "failed to publish replacement {} {} after removing existing destination: {second_error}",
                    label,
                    path.display()
                ));
            }
            Ok(())
        }
        Err(error) => {
            let _ = fs::remove_file(tmp_path);
            Err(format!(
                "failed to publish {} {}: {error}",
                label,
                path.display()
            ))
        }
    }
}

#[cfg(all(feature = "stwo-backend", unix))]
fn sync_parent_directory(parent: &Path, label: &str, path: &Path) -> Result<(), String> {
    fs::File::open(parent)
        .and_then(|directory| directory.sync_all())
        .map_err(|error| {
            format!(
                "failed to sync output parent {} for {} {}: {error}",
                parent.display(),
                label,
                path.display()
            )
        })
}

#[cfg(all(feature = "stwo-backend", not(unix)))]
fn sync_parent_directory(_parent: &Path, _label: &str, _path: &Path) -> Result<(), String> {
    Ok(())
}

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;

    #[test]
    fn atomic_write_file_replaces_existing_destination() {
        let dir = tempfile::tempdir().expect("temp dir");
        let path = dir.path().join("envelope.json");

        atomic_write_file(&path, b"first", "test envelope").expect("first write");
        atomic_write_file(&path, b"second", "test envelope").expect("replacement write");

        assert_eq!(fs::read(&path).expect("read replacement"), b"second");
    }
}
