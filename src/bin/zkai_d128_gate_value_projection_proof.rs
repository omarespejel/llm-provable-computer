use std::process::{self, ExitCode};

#[cfg(feature = "stwo-backend")]
use std::fs;
#[cfg(feature = "stwo-backend")]
use std::io::{Read, Write};
#[cfg(feature = "stwo-backend")]
use std::path::{Path, PathBuf};
#[cfg(feature = "stwo-backend")]
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    prove_zkai_d128_gate_value_projection_compact_preprocessed_envelope,
    prove_zkai_d128_gate_value_projection_envelope,
    verify_zkai_d128_gate_value_projection_compact_preprocessed_envelope,
    verify_zkai_d128_gate_value_projection_envelope,
    zkai_d128_gate_value_projection_compact_preprocessed_envelope_from_json_slice,
    zkai_d128_gate_value_projection_envelope_from_json_slice,
    zkai_d128_gate_value_projection_input_from_json_str,
    ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES,
    ZKAI_D128_GATE_VALUE_PROJECTION_MAX_JSON_BYTES,
};

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
    eprintln!("zkai_d128_gate_value_projection_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_d128_gate_value_projection_proof prove <input.json> <envelope.json> | verify <envelope.json> | prove-compact <input.json> <envelope.json> | verify-compact <envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "prove" => {
            if args.len() != 2 {
                return Err("usage: prove <input.json> <envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_utf8(
                &input_path,
                ZKAI_D128_GATE_VALUE_PROJECTION_MAX_JSON_BYTES,
                "d128 gate/value projection input JSON",
            )?;
            let input = zkai_d128_gate_value_projection_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_gate_value_projection_envelope(&input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_gate_value_projection_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let envelope_bytes = serde_json::to_vec_pretty(&envelope)
                .map_err(|error| format!("failed to serialize envelope: {error}"))?;
            if envelope_bytes.len() > ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES {
                return Err(format!(
                    "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            atomic_write_file(&envelope_path, &envelope_bytes, "gate/value envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-projection-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "row_count": envelope.input.row_count,
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "claim_boundary": "d128_gate_value_projection_native_proof_not_full_block_not_nanozk_win",
            })
            .to_string())
        }
        "prove-compact" => {
            if args.len() != 2 {
                return Err("usage: prove-compact <input.json> <envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_utf8(
                &input_path,
                ZKAI_D128_GATE_VALUE_PROJECTION_MAX_JSON_BYTES,
                "d128 compact gate/value projection input JSON",
            )?;
            let input = zkai_d128_gate_value_projection_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope =
                prove_zkai_d128_gate_value_projection_compact_preprocessed_envelope(&input)
                    .map_err(|error| error.to_string())?;
            verify_zkai_d128_gate_value_projection_compact_preprocessed_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let envelope_bytes = serde_json::to_vec_pretty(&envelope)
                .map_err(|error| format!("failed to serialize compact envelope: {error}"))?;
            if envelope_bytes.len() > ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES {
                return Err(format!(
                    "compact envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            atomic_write_file(
                &envelope_path,
                &envelope_bytes,
                "compact gate/value envelope",
            )?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-projection-proof-cli-summary-v1",
                "mode": "prove-compact",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "row_count": envelope.input.row_count,
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "claim_boundary": "compact_preprocessed_gate_value_projection_not_full_block_not_matched_nanozk_benchmark",
            })
            .to_string())
        }
        "verify" => {
            if args.len() != 1 {
                return Err("usage: verify <envelope.json>".to_string());
            }
            let envelope_path = PathBuf::from(&args[0]);
            let raw = read_bounded_file(
                &envelope_path,
                ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES,
                "d128 gate/value projection envelope JSON",
            )?;
            let envelope = zkai_d128_gate_value_projection_envelope_from_json_slice(&raw)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_gate_value_projection_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-projection-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "row_count": envelope.input.row_count,
                "verified": true,
                "claim_boundary": "d128_gate_value_projection_native_proof_not_full_block_not_nanozk_win",
            })
            .to_string())
        }
        "verify-compact" => {
            if args.len() != 1 {
                return Err("usage: verify-compact <envelope.json>".to_string());
            }
            let envelope_path = PathBuf::from(&args[0]);
            let raw = read_bounded_file(
                &envelope_path,
                ZKAI_D128_GATE_VALUE_PROJECTION_MAX_ENVELOPE_JSON_BYTES,
                "d128 compact gate/value projection envelope JSON",
            )?;
            let envelope =
                zkai_d128_gate_value_projection_compact_preprocessed_envelope_from_json_slice(&raw)
                    .map_err(|error| error.to_string())?;
            verify_zkai_d128_gate_value_projection_compact_preprocessed_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-projection-proof-cli-summary-v1",
                "mode": "verify-compact",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "row_count": envelope.input.row_count,
                "verified": true,
                "claim_boundary": "compact_preprocessed_gate_value_projection_not_full_block_not_matched_nanozk_benchmark",
            })
            .to_string())
        }
        other => Err(format!("unknown mode: {other}")),
    }
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_utf8(path: &Path, max_bytes: usize, label: &str) -> Result<String, String> {
    String::from_utf8(read_bounded_file(path, max_bytes, label)?)
        .map_err(|error| format!("{label} is not UTF-8: {error}"))
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_file(path: &Path, max_bytes: usize, label: &str) -> Result<Vec<u8>, String> {
    #[cfg(unix)]
    let file = {
        use std::os::unix::fs::OpenOptionsExt;

        fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(path)
            .map_err(|error| {
                format!(
                    "failed to open {label} {} without following symlinks: io_kind={:?}: {error}",
                    path.display(),
                    error.kind()
                )
            })?
    };
    #[cfg(not(unix))]
    let file = {
        let metadata = fs::symlink_metadata(path)
            .map_err(|error| format!("failed to stat {label} {}: {error}", path.display()))?;
        if metadata.file_type().is_symlink() {
            return Err(format!("refusing symlink for {label}: {}", path.display()));
        }
        if !metadata.is_file() {
            return Err(format!(
                "expected regular file for {label}: {}",
                path.display()
            ));
        }
        fs::OpenOptions::new()
            .read(true)
            .open(path)
            .map_err(|error| format!("failed to open {label} {}: {error}", path.display()))?
    };
    let metadata = file
        .metadata()
        .map_err(|error| format!("failed to stat opened {label} {}: {error}", path.display()))?;
    if !metadata.is_file() {
        return Err(format!(
            "expected regular file for {label}: {}",
            path.display()
        ));
    }
    let size = usize::try_from(metadata.len())
        .map_err(|_| format!("{label} size does not fit usize: {}", path.display()))?;
    if size > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got {size} bytes, limit {max_bytes} bytes"
        ));
    }
    let mut bytes = Vec::with_capacity(max_bytes.min(size));
    file.take(max_bytes.saturating_add(1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("failed to read {}: {error}", path.display()))?;
    if bytes.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got more than {max_bytes} bytes, limit {max_bytes} bytes"
        ));
    }
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn atomic_write_file(path: &Path, bytes: &[u8], label: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("failed to create {}: {error}", parent.display()))?;
    }
    let metadata = fs::symlink_metadata(path).ok();
    if metadata
        .as_ref()
        .is_some_and(|meta| meta.file_type().is_symlink())
    {
        return Err(format!(
            "refusing to overwrite symlink for {label}: {}",
            path.display()
        ));
    }
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| format!("invalid output path: {}", path.display()))?;
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("system clock before epoch: {error}"))?
        .as_nanos();
    let tmp_path = parent.join(format!(".{file_name}.tmp.{}.{}", process::id(), nonce));
    {
        let mut file = fs::File::create_new(&tmp_path)
            .map_err(|error| format!("failed to create {}: {error}", tmp_path.display()))?;
        file.write_all(bytes)
            .map_err(|error| format!("failed to write {}: {error}", tmp_path.display()))?;
        file.sync_all()
            .map_err(|error| format!("failed to sync {}: {error}", tmp_path.display()))?;
    }
    publish_temp_file(&tmp_path, path, label)
}

#[cfg(feature = "stwo-backend")]
fn publish_temp_file(tmp_path: &Path, path: &Path, label: &str) -> Result<(), String> {
    match fs::rename(tmp_path, path) {
        Ok(()) => Ok(()),
        Err(first_error) if path.exists() => {
            if let Err(remove_error) = fs::remove_file(path) {
                let _ = fs::remove_file(tmp_path);
                return Err(format!(
                    "failed to replace existing {label} {} after publish error {first_error}: {remove_error}",
                    path.display()
                ));
            }
            if let Err(second_error) = fs::rename(tmp_path, path) {
                let _ = fs::remove_file(tmp_path);
                return Err(format!(
                    "failed to publish replacement {label} {} after removing existing destination: {second_error}",
                    path.display()
                ));
            }
            Ok(())
        }
        Err(error) => {
            let _ = fs::remove_file(tmp_path);
            Err(format!(
                "failed to move {} to {}: {error}",
                tmp_path.display(),
                path.display()
            ))
        }
    }
}
