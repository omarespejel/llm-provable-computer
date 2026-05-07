use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope,
    verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope,
    zkai_attention_kv_native_four_head_fused_softmax_table_envelope_from_json_slice,
    zkai_attention_kv_native_four_head_fused_softmax_table_source_input_from_json_str,
    ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
    ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES,
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
        "zkai_attention_kv_native_four_head_fused_softmax_table_proof requires --features stwo-backend"
    );
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_attention_kv_native_four_head_fused_softmax_table_proof prove <source-input.json> <fused-envelope.json> | verify <fused-envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "prove" => {
            if args.len() != 2 {
                return Err("usage: prove <source-input.json> <fused-envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_file(
                &input_path,
                ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
                "source input JSON",
            )?;
            let raw = std::str::from_utf8(&raw).map_err(|error| {
                format!(
                    "failed to decode source input JSON {}: {error}",
                    input_path.display()
                )
            })?;
            let source_input =
                zkai_attention_kv_native_four_head_fused_softmax_table_source_input_from_json_str(
                    raw,
                )
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(
                &source_input,
            )
            .map_err(|error| error.to_string())?;
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .map_err(|error| error.to_string())?;
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
                .map_err(|error| format!("failed to serialize fused envelope: {error}"))?;
            if envelope_bytes.len()
                > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
            {
                return Err(format!(
                    "fused envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            fs::write(&envelope_path, &envelope_bytes).map_err(|error| {
                format!(
                    "failed to write fused envelope {}: {error}",
                    envelope_path.display()
                )
            })?;
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-cli-summary-v1",
                "mode": "prove",
                "source_input_path": input_path.display().to_string(),
                "fused_envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "source_plus_sidecar_raw_proof_bytes": envelope.fused_summary.source_plus_sidecar_raw_proof_bytes,
                "source_statement_commitment": envelope.fused_summary.source_statement_commitment,
                "lookup_claims": envelope.fused_summary.lookup_claims,
                "table_rows": envelope.fused_summary.table_rows,
                "fusion_status": envelope.fused_summary.fusion_status,
            })
            .to_string())
        }
        "verify" => {
            if args.len() != 1 {
                return Err("usage: verify <fused-envelope.json>".to_string());
            }
            let envelope_path = PathBuf::from(&args[0]);
            let raw = read_bounded_file(
                &envelope_path,
                ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES,
                "fused envelope JSON",
            )?;
            let envelope =
                zkai_attention_kv_native_four_head_fused_softmax_table_envelope_from_json_slice(
                    &raw,
                )
                .map_err(|error| error.to_string())?;
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-cli-summary-v1",
                "mode": "verify",
                "fused_envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "source_plus_sidecar_raw_proof_bytes": envelope.fused_summary.source_plus_sidecar_raw_proof_bytes,
                "source_statement_commitment": envelope.fused_summary.source_statement_commitment,
                "lookup_claims": envelope.fused_summary.lookup_claims,
                "table_rows": envelope.fused_summary.table_rows,
                "verified": true,
            })
            .to_string())
        }
        _ => Err(format!("unknown mode: {mode}")),
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
