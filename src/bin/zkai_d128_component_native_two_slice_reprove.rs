use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{self, ExitCode};
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    build_zkai_d128_component_two_slice_reprove_input,
    prove_zkai_d128_component_two_slice_reprove_envelope,
    verify_zkai_d128_component_two_slice_reprove_envelope,
    zkai_d128_component_two_slice_reprove_envelope_from_json_slice,
    zkai_d128_component_two_slice_reprove_input_from_json_str,
    zkai_d128_rmsnorm_public_row_input_from_json_str,
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str,
    ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES,
    ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES,
    ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
};

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
    eprintln!("zkai_d128_component_native_two_slice_reprove requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_d128_component_native_two_slice_reprove build-input <rmsnorm.json> <bridge.json> <input.json> | prove <input.json> <envelope.json> | verify <envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "build-input" => {
            if args.len() != 3 {
                return Err(
                    "usage: build-input <rmsnorm.json> <bridge.json> <input.json>".to_string(),
                );
            }
            let rmsnorm_path = PathBuf::from(&args[0]);
            let bridge_path = PathBuf::from(&args[1]);
            let input_path = PathBuf::from(&args[2]);
            let rmsnorm_raw = read_bounded_utf8(
                &rmsnorm_path,
                ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
                "RMSNorm input JSON",
            )?;
            let bridge_raw = read_bounded_utf8(
                &bridge_path,
                ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
                "bridge input JSON",
            )?;
            let rmsnorm_input = zkai_d128_rmsnorm_public_row_input_from_json_str(&rmsnorm_raw)
                .map_err(|error| error.to_string())?;
            let bridge_input =
                zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(&bridge_raw)
                    .map_err(|error| error.to_string())?;
            let input =
                build_zkai_d128_component_two_slice_reprove_input(rmsnorm_input, bridge_input)
                    .map_err(|error| error.to_string())?;
            let input_bytes = serde_json::to_vec_pretty(&input)
                .map_err(|error| format!("failed to serialize input: {error}"))?;
            if input_bytes.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES {
                return Err(format!(
                    "input JSON exceeds max size: got {} bytes, limit {} bytes",
                    input_bytes.len(),
                    ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES
                ));
            }
            atomic_write_file(&input_path, &input_bytes, "component-native input")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-component-native-two-slice-reprove-cli-summary-v1",
                "mode": "build-input",
                "rmsnorm_input_path": rmsnorm_path.display().to_string(),
                "bridge_input_path": bridge_path.display().to_string(),
                "input_path": input_path.display().to_string(),
                "input_size_bytes": input_bytes.len(),
                "statement_commitment": input.statement_commitment,
                "public_instance_commitment": input.public_instance_commitment,
                "selected_checked_rows": input.selected_checked_rows,
                "selected_slice_ids": input.selected_slice_ids,
                "claim_boundary": "component_native_reprove_input_not_verifier_execution",
            })
            .to_string())
        }
        "prove" => {
            if args.len() != 2 {
                return Err("usage: prove <input.json> <envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_utf8(
                &input_path,
                ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES,
                "component-native input JSON",
            )?;
            let input = zkai_d128_component_two_slice_reprove_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_component_two_slice_reprove_envelope(&input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_component_two_slice_reprove_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let envelope_bytes = serde_json::to_vec_pretty(&envelope)
                .map_err(|error| format!("failed to serialize envelope: {error}"))?;
            if envelope_bytes.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES
            {
                return Err(format!(
                    "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            atomic_write_file(&envelope_path, &envelope_bytes, "component-native envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-component-native-two-slice-reprove-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "selected_checked_rows": envelope.input.selected_checked_rows,
                "selected_slice_ids": envelope.input.selected_slice_ids,
                "claim_boundary": "component_native_reprove_not_verifier_execution_not_nanozk_win",
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
                ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES,
                "component-native envelope JSON",
            )?;
            let envelope = zkai_d128_component_two_slice_reprove_envelope_from_json_slice(&raw)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_component_two_slice_reprove_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-component-native-two-slice-reprove-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "selected_checked_rows": envelope.input.selected_checked_rows,
                "selected_slice_ids": envelope.input.selected_slice_ids,
                "verified": true,
                "claim_boundary": "component_native_reprove_not_verifier_execution_not_nanozk_win",
            })
            .to_string())
        }
        _ => Err(format!("unknown mode: {mode}")),
    }
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_utf8(path: &Path, max_bytes: usize, label: &str) -> Result<String, String> {
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
