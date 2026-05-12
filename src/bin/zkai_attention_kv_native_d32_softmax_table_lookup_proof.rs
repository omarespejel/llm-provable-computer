use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{self, ExitCode};
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    prove_zkai_attention_kv_native_d32_softmax_table_lookup_envelope,
    verify_zkai_attention_kv_native_d32_softmax_table_lookup_envelope,
    zkai_attention_kv_native_d32_softmax_table_lookup_envelope_from_json_slice,
    zkai_attention_kv_native_d32_softmax_table_lookup_source_input_from_json_str,
    ZKAI_ATTENTION_KV_NATIVE_D32_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
    ZKAI_ATTENTION_KV_NATIVE_D32_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES,
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
    eprintln!(
        "zkai_attention_kv_native_d32_softmax_table_lookup_proof requires --features stwo-backend"
    );
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_attention_kv_native_d32_softmax_table_lookup_proof prove <source-input.json> <lookup-envelope.json> | verify <lookup-envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "prove" => {
            if args.len() != 2 {
                return Err("usage: prove <source-input.json> <lookup-envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_file(
                &input_path,
                ZKAI_ATTENTION_KV_NATIVE_D32_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
                "source input JSON",
            )?;
            let raw = std::str::from_utf8(&raw).map_err(|error| {
                format!(
                    "failed to decode source input JSON {}: {error}",
                    input_path.display()
                )
            })?;
            let source_input =
                zkai_attention_kv_native_d32_softmax_table_lookup_source_input_from_json_str(raw)
                    .map_err(|error| error.to_string())?;
            let envelope =
                prove_zkai_attention_kv_native_d32_softmax_table_lookup_envelope(&source_input)
                    .map_err(|error| error.to_string())?;
            let verified =
                verify_zkai_attention_kv_native_d32_softmax_table_lookup_envelope(&envelope)
                    .map_err(|error| error.to_string())?;
            if !verified {
                return Err("lookup sidecar envelope verification returned false".to_string());
            }
            if let Some(parent) = envelope_path.parent() {
                if !parent.as_os_str().is_empty() {
                    fs::create_dir_all(parent).map_err(|error| {
                        format!(
                            "failed to create output parent {}: {error}",
                            parent.display()
                        )
                    })?;
                }
            }
            let envelope_bytes = serde_json::to_vec_pretty(&envelope)
                .map_err(|error| format!("failed to serialize lookup envelope: {error}"))?;
            if envelope_bytes.len()
                > ZKAI_ATTENTION_KV_NATIVE_D32_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES
            {
                return Err(format!(
                    "lookup envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_ATTENTION_KV_NATIVE_D32_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            atomic_write_file(&envelope_path, &envelope_bytes, "lookup envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-cli-summary-v1",
                "mode": "prove",
                "source_input_path": input_path,
                "lookup_envelope_path": envelope_path,
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "source_statement_commitment": envelope.lookup_summary.source_statement_commitment,
                "source_weight_table_commitment": envelope.lookup_summary.source_weight_table_commitment,
                "lookup_claims": envelope.lookup_summary.lookup_claims,
                "table_rows": envelope.lookup_summary.table_rows,
            })
            .to_string())
        }
        "verify" => {
            if args.len() != 1 {
                return Err("usage: verify <lookup-envelope.json>".to_string());
            }
            let envelope_path = PathBuf::from(&args[0]);
            let raw = read_bounded_file(
                &envelope_path,
                ZKAI_ATTENTION_KV_NATIVE_D32_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES,
                "lookup envelope JSON",
            )?;
            let envelope =
                zkai_attention_kv_native_d32_softmax_table_lookup_envelope_from_json_slice(&raw)
                    .map_err(|error| error.to_string())?;
            let verified =
                verify_zkai_attention_kv_native_d32_softmax_table_lookup_envelope(&envelope)
                    .map_err(|error| error.to_string())?;
            if !verified {
                return Err("lookup sidecar envelope verification returned false".to_string());
            }
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-d32-softmax-table-logup-sidecar-cli-summary-v1",
                "mode": "verify",
                "lookup_envelope_path": envelope_path,
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "source_statement_commitment": envelope.lookup_summary.source_statement_commitment,
                "lookup_claims": envelope.lookup_summary.lookup_claims,
                "table_rows": envelope.lookup_summary.table_rows,
                "verified": true,
            })
            .to_string())
        }
        _ => Err(format!("unknown mode: {mode}")),
    }
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_file(path: &Path, max_bytes: usize, label: &str) -> Result<Vec<u8>, String> {
    let preflight_metadata = fs::symlink_metadata(path)
        .map_err(|error| format!("failed to stat {} {}: {error}", label, path.display()))?;
    if preflight_metadata.file_type().is_symlink() {
        return Err(format!(
            "{} {} is a symlink, expected a regular file",
            label,
            path.display()
        ));
    }
    if !preflight_metadata.is_file() {
        return Err(format!(
            "{} {} is not a regular file",
            label,
            path.display()
        ));
    }
    if preflight_metadata.len() > max_bytes as u64 {
        return Err(format!(
            "{label} exceeds max size: got {} bytes, limit {} bytes",
            preflight_metadata.len(),
            max_bytes
        ));
    }
    #[cfg(unix)]
    let file = {
        use std::os::unix::fs::OpenOptionsExt;

        fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(path)
            .map_err(|error| {
                format!(
                    "failed to open {} {} without following symlinks: io_kind={:?}: {error}",
                    label,
                    path.display(),
                    error.kind()
                )
            })?
    };
    #[cfg(not(unix))]
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
            "{} {} is not a regular file after open",
            label,
            path.display()
        ));
    }
    if metadata.len() > max_bytes as u64 {
        return Err(format!(
            "{label} exceeds max size after open: got {} bytes, limit {} bytes",
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
    if let Err(error) = fs::rename(&tmp_path, path) {
        let _ = fs::remove_file(&tmp_path);
        return Err(format!(
            "failed to publish {} {}: {error}",
            label,
            path.display()
        ));
    }
    Ok(())
}
