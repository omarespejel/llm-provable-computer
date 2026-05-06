use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::Instant;

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    prove_zkai_attention_kv_native_d8_bounded_weighted_envelope,
    verify_zkai_attention_kv_native_d8_bounded_weighted_envelope,
    zkai_attention_kv_native_d8_bounded_weighted_envelope_from_json_slice,
    zkai_attention_kv_native_d8_bounded_weighted_input_from_json_str,
    ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES,
    ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_WEIGHTED_MAX_INPUT_JSON_BYTES,
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
        "zkai_attention_kv_native_d8_bounded_weighted_proof requires --features stwo-backend"
    );
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_attention_kv_native_d8_bounded_weighted_proof prove <input.json> <envelope.json> | verify <envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "prove" => {
            if args.len() != 2 {
                return Err("usage: prove <input.json> <envelope.json>".to_string());
            }
            let input_path = PathBuf::from(&args[0]);
            let envelope_path = PathBuf::from(&args[1]);
            let raw = read_bounded_file(
                &input_path,
                ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_WEIGHTED_MAX_INPUT_JSON_BYTES,
                "input JSON",
            )?;
            let raw = std::str::from_utf8(&raw).map_err(|error| {
                format!(
                    "failed to decode input JSON {}: {error}",
                    input_path.display()
                )
            })?;
            let input = zkai_attention_kv_native_d8_bounded_weighted_input_from_json_str(raw)
                .map_err(|error| error.to_string())?;
            let started = Instant::now();
            let envelope = prove_zkai_attention_kv_native_d8_bounded_weighted_envelope(&input)
                .map_err(|error| error.to_string())?;
            let prove_time_ms = started.elapsed().as_secs_f64() * 1000.0;
            let verify_started = Instant::now();
            verify_zkai_attention_kv_native_d8_bounded_weighted_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let verify_time_ms = verify_started.elapsed().as_secs_f64() * 1000.0;
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
                .map_err(|error| format!("failed to serialize envelope: {error}"))?;
            if envelope_bytes.len()
                > ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES
            {
                return Err(format!(
                    "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            fs::write(&envelope_path, &envelope_bytes).map_err(|error| {
                format!(
                    "failed to write envelope {}: {error}",
                    envelope_path.display()
                )
            })?;
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-d8-bounded-weighted-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path,
                "envelope_path": envelope_path,
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "prove_time_ms": prove_time_ms,
                "verify_time_ms": verify_time_ms,
                "statement_commitment": envelope.input.statement_commitment,
                "score_row_count": envelope.input.score_row_count,
                "trace_row_count": envelope.input.trace_row_count,
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
                ZKAI_ATTENTION_KV_NATIVE_D8_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES,
                "envelope JSON",
            )?;
            let envelope =
                zkai_attention_kv_native_d8_bounded_weighted_envelope_from_json_slice(&raw)
                    .map_err(|error| error.to_string())?;
            let verify_started = Instant::now();
            verify_zkai_attention_kv_native_d8_bounded_weighted_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let verify_time_ms = verify_started.elapsed().as_secs_f64() * 1000.0;
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-d8-bounded-weighted-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path,
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "verify_time_ms": verify_time_ms,
                "statement_commitment": envelope.input.statement_commitment,
                "score_row_count": envelope.input.score_row_count,
                "trace_row_count": envelope.input.trace_row_count,
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
