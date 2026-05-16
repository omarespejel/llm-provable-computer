use std::process::ExitCode;

#[cfg(feature = "stwo-backend")]
use std::fs;
#[cfg(feature = "stwo-backend")]
use std::io::ErrorKind;
#[cfg(feature = "stwo-backend")]
use std::io::{Read, Write};
#[cfg(all(feature = "stwo-backend", unix))]
use std::os::unix::fs::OpenOptionsExt;
#[cfg(feature = "stwo-backend")]
use std::path::{Path, PathBuf};
#[cfg(feature = "stwo-backend")]
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    build_zkai_native_attention_mlp_single_proof_input_with_adapter_mode,
    prove_zkai_native_attention_mlp_single_proof_envelope,
    verify_zkai_native_attention_mlp_single_proof_envelope,
    zkai_attention_kv_native_d8_fused_softmax_table_source_input_from_json_str,
    zkai_d128_rmsnorm_mlp_fused_input_from_json_str,
    zkai_native_attention_mlp_single_proof_envelope_from_json_slice,
    zkai_native_attention_mlp_single_proof_input_from_json_str, ZkAiNativeAttentionMlpAdapterMode,
    ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
    ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES,
    ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_ENVELOPE_JSON_BYTES,
    ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES,
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
    eprintln!("zkai_native_attention_mlp_single_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_native_attention_mlp_single_proof build-input <attention-source.json> <mlp-input.json> <single-input.json> | build-input-duplicate-selector <attention-source.json> <mlp-input.json> <single-input.json> | build-input-compact <attention-source.json> <mlp-input.json> <single-input.json> | prove <single-input.json> <envelope.json> | verify <envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "build-input" => {
            if args.len() != 3 {
                return Err("usage: build-input <attention-source.json> <mlp-input.json> <single-input.json>".to_string());
            }
            let attention_path = PathBuf::from(&args[0]);
            let mlp_path = PathBuf::from(&args[1]);
            let output_path = PathBuf::from(&args[2]);
            let attention_raw = read_bounded_utf8(
                &attention_path,
                ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
                "attention source input JSON",
            )?;
            let attention =
                zkai_attention_kv_native_d8_fused_softmax_table_source_input_from_json_str(
                    &attention_raw,
                )
                .map_err(|error| error.to_string())?;
            let mlp_raw = read_bounded_utf8(
                &mlp_path,
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES,
                "d128 RMSNorm-MLP fused input JSON",
            )?;
            let mlp = zkai_d128_rmsnorm_mlp_fused_input_from_json_str(&mlp_raw)
                .map_err(|error| error.to_string())?;
            let input = build_zkai_native_attention_mlp_single_proof_input_with_adapter_mode(
                attention,
                mlp,
                ZkAiNativeAttentionMlpAdapterMode::DuplicateBasePreprocessed,
            )
            .map_err(|error| error.to_string())?;
            let bytes = pretty_json_bytes_with_trailing_newline(
                &input,
                ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES,
                "single proof input JSON",
            )?;
            atomic_write_file(&output_path, &bytes, "single proof input")?;
            Ok(serde_json::json!({
                "schema": "zkai-native-attention-mlp-single-proof-cli-summary-v1",
                "mode": "build-input",
                "input_path": output_path.display().to_string(),
                "input_size_bytes": bytes.len(),
                "statement_commitment": input.statement_commitment,
                "public_instance_commitment": input.public_instance_commitment,
                "adapter_mode": input.adapter_mode,
                "adapter_status": input.adapter_status,
                "adapter_trace_cells": input.adapter_trace_cells,
                "pcs_lifting_log_size": input.pcs_lifting_log_size,
                "current_two_proof_frontier_typed_bytes": input.current_two_proof_frontier_typed_bytes,
            })
            .to_string())
        }
        "build-input-compact" => {
            if args.len() != 3 {
                return Err("usage: build-input-compact <attention-source.json> <mlp-input.json> <single-input.json>".to_string());
            }
            let attention_path = PathBuf::from(&args[0]);
            let mlp_path = PathBuf::from(&args[1]);
            let output_path = PathBuf::from(&args[2]);
            let attention_raw = read_bounded_utf8(
                &attention_path,
                ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
                "attention source input JSON",
            )?;
            let attention =
                zkai_attention_kv_native_d8_fused_softmax_table_source_input_from_json_str(
                    &attention_raw,
                )
                .map_err(|error| error.to_string())?;
            let mlp_raw = read_bounded_utf8(
                &mlp_path,
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES,
                "d128 RMSNorm-MLP fused input JSON",
            )?;
            let mlp = zkai_d128_rmsnorm_mlp_fused_input_from_json_str(&mlp_raw)
                .map_err(|error| error.to_string())?;
            let input = build_zkai_native_attention_mlp_single_proof_input_with_adapter_mode(
                attention,
                mlp,
                ZkAiNativeAttentionMlpAdapterMode::CompactBaseReferencedFixed,
            )
            .map_err(|error| error.to_string())?;
            let bytes = pretty_json_bytes_with_trailing_newline(
                &input,
                ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES,
                "single proof compact input JSON",
            )?;
            atomic_write_file(&output_path, &bytes, "single proof compact input")?;
            Ok(serde_json::json!({
                "schema": "zkai-native-attention-mlp-single-proof-cli-summary-v1",
                "mode": "build-input-compact",
                "input_path": output_path.display().to_string(),
                "input_size_bytes": bytes.len(),
                "statement_commitment": input.statement_commitment,
                "public_instance_commitment": input.public_instance_commitment,
                "adapter_mode": input.adapter_mode,
                "adapter_status": input.adapter_status,
                "adapter_trace_cells": input.adapter_trace_cells,
                "pcs_lifting_log_size": input.pcs_lifting_log_size,
                "current_two_proof_frontier_typed_bytes": input.current_two_proof_frontier_typed_bytes,
            })
            .to_string())
        }
        "build-input-duplicate-selector" => {
            if args.len() != 3 {
                return Err("usage: build-input-duplicate-selector <attention-source.json> <mlp-input.json> <single-input.json>".to_string());
            }
            let attention_path = PathBuf::from(&args[0]);
            let mlp_path = PathBuf::from(&args[1]);
            let output_path = PathBuf::from(&args[2]);
            let attention_raw = read_bounded_utf8(
                &attention_path,
                ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
                "attention source input JSON",
            )?;
            let attention =
                zkai_attention_kv_native_d8_fused_softmax_table_source_input_from_json_str(
                    &attention_raw,
                )
                .map_err(|error| error.to_string())?;
            let mlp_raw = read_bounded_utf8(
                &mlp_path,
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES,
                "d128 RMSNorm-MLP fused input JSON",
            )?;
            let mlp = zkai_d128_rmsnorm_mlp_fused_input_from_json_str(&mlp_raw)
                .map_err(|error| error.to_string())?;
            let input = build_zkai_native_attention_mlp_single_proof_input_with_adapter_mode(
                attention,
                mlp,
                ZkAiNativeAttentionMlpAdapterMode::DuplicateBasePreprocessedSelector,
            )
            .map_err(|error| error.to_string())?;
            let bytes = pretty_json_bytes_with_trailing_newline(
                &input,
                ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES,
                "single proof duplicate selector input JSON",
            )?;
            atomic_write_file(
                &output_path,
                &bytes,
                "single proof duplicate selector input",
            )?;
            Ok(serde_json::json!({
                "schema": "zkai-native-attention-mlp-single-proof-cli-summary-v1",
                "mode": "build-input-duplicate-selector",
                "input_path": output_path.display().to_string(),
                "input_size_bytes": bytes.len(),
                "statement_commitment": input.statement_commitment,
                "public_instance_commitment": input.public_instance_commitment,
                "adapter_mode": input.adapter_mode,
                "adapter_status": input.adapter_status,
                "adapter_trace_cells": input.adapter_trace_cells,
                "pcs_lifting_log_size": input.pcs_lifting_log_size,
                "current_two_proof_frontier_typed_bytes": input.current_two_proof_frontier_typed_bytes,
            })
            .to_string())
        }
        "prove" => {
            if args.len() != 2 {
                return Err("usage: prove <single-input.json> <envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_utf8(
                &input_path,
                ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_INPUT_JSON_BYTES,
                "single proof input JSON",
            )?;
            let input = zkai_native_attention_mlp_single_proof_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_native_attention_mlp_single_proof_envelope(&input)
                .map_err(|error| error.to_string())?;
            let verified = verify_zkai_native_attention_mlp_single_proof_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let bytes = pretty_json_bytes_with_trailing_newline(
                &envelope,
                ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_ENVELOPE_JSON_BYTES,
                "single proof envelope JSON",
            )?;
            atomic_write_file(&envelope_path, &bytes, "single proof envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-native-attention-mlp-single-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "verified": verified,
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": bytes.len(),
                "proof_backend_version": envelope.proof_backend_version,
                "statement_version": envelope.statement_version,
                "adapter_mode": envelope.input.adapter_mode,
                "adapter_status": envelope.input.adapter_status,
                "adapter_trace_cells": envelope.input.adapter_trace_cells,
                "pcs_lifting_log_size": envelope.input.pcs_lifting_log_size,
                "current_two_proof_frontier_typed_bytes": envelope.input.current_two_proof_frontier_typed_bytes,
            })
            .to_string())
        }
        "verify" => {
            if args.len() != 1 {
                return Err("usage: verify <envelope.json>".to_string());
            }
            let envelope_path = PathBuf::from(&args[0]);
            let raw = read_bounded_bytes(
                &envelope_path,
                ZKAI_NATIVE_ATTENTION_MLP_SINGLE_PROOF_MAX_ENVELOPE_JSON_BYTES,
                "single proof envelope JSON",
            )?;
            let envelope = zkai_native_attention_mlp_single_proof_envelope_from_json_slice(&raw)
                .map_err(|error| error.to_string())?;
            let verified = verify_zkai_native_attention_mlp_single_proof_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-native-attention-mlp-single-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "verified": verified,
                "proof_size_bytes": envelope.proof.len(),
                "adapter_mode": envelope.input.adapter_mode,
                "adapter_status": envelope.input.adapter_status,
                "adapter_trace_cells": envelope.input.adapter_trace_cells,
                "pcs_lifting_log_size": envelope.input.pcs_lifting_log_size,
            })
            .to_string())
        }
        _ => Err(format!("unknown mode: {mode}")),
    }
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_utf8(path: &Path, max_bytes: usize, label: &str) -> Result<String, String> {
    let bytes = read_bounded_bytes(path, max_bytes, label)?;
    String::from_utf8(bytes).map_err(|error| {
        format!(
            "failed to decode {label} {} as UTF-8: {error}",
            path.display()
        )
    })
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_bytes(path: &Path, max_bytes: usize, label: &str) -> Result<Vec<u8>, String> {
    let mut open_options = fs::OpenOptions::new();
    open_options.read(true);
    #[cfg(unix)]
    {
        open_options.custom_flags(libc::O_NOFOLLOW);
    }
    let mut file = open_options
        .open(path)
        .map_err(|error| format!("failed to open {label} {}: {error}", path.display()))?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("failed to stat opened {label} {}: {error}", path.display()))?;
    if !metadata.is_file() {
        return Err(format!("{label} {} is not a regular file", path.display()));
    }
    if metadata.len() > max_bytes as u64 {
        return Err(format!(
            "{label} exceeds max size: got {} bytes, limit {max_bytes} bytes",
            metadata.len()
        ));
    }
    let mut raw = Vec::new();
    std::io::Read::by_ref(&mut file)
        .take(max_bytes.saturating_add(1) as u64)
        .read_to_end(&mut raw)
        .map_err(|error| format!("failed to read {label} {}: {error}", path.display()))?;
    if raw.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got more than {max_bytes} bytes, limit {max_bytes} bytes"
        ));
    }
    Ok(raw)
}

#[cfg(feature = "stwo-backend")]
fn pretty_json_bytes_with_trailing_newline<T: serde::Serialize>(
    value: &T,
    max_bytes: usize,
    label: &str,
) -> Result<Vec<u8>, String> {
    let mut bytes = serde_json::to_vec_pretty(value)
        .map_err(|error| format!("failed to encode {label}: {error}"))?;
    bytes.push(b'\n');
    if bytes.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size after serialization: got {}, limit {}",
            bytes.len(),
            max_bytes
        ));
    }
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn atomic_write_file(path: &Path, bytes: &[u8], label: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent).map_err(|error| {
                format!(
                    "failed to create parent for {label} {}: {error}",
                    path.display()
                )
            })?;
        }
    }
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| {
            format!(
                "{label} output path has no UTF-8 file name: {}",
                path.display()
            )
        })?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("system clock before UNIX_EPOCH: {error}"))?
        .as_nanos();
    let tmp_path = parent.join(format!(".{file_name}.{stamp}.tmp"));
    let write_result = write_new_file(&tmp_path, bytes).and_then(|()| {
        fs::rename(&tmp_path, path)
            .map_err(|error| format!("failed to rename temp {label} {}: {error}", path.display()))
    });
    if write_result.is_err() {
        let _ = fs::remove_file(&tmp_path);
    }
    write_result
}

#[cfg(feature = "stwo-backend")]
fn write_new_file(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let mut options = fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        options.mode(0o600);
    }
    let mut file = match options.open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == ErrorKind::AlreadyExists => {
            return Err(format!("temp file collision at {}", path.display()));
        }
        Err(error) => {
            return Err(format!(
                "failed to create temp file {}: {error}",
                path.display()
            ));
        }
    };
    file.write_all(bytes)
        .map_err(|error| format!("failed to write temp file {}: {error}", path.display()))?;
    file.sync_all()
        .map_err(|error| format!("failed to sync temp file {}: {error}", path.display()))
}
