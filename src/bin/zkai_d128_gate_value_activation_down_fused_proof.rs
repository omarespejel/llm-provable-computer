use std::process::ExitCode;

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
    build_zkai_d128_gate_value_activation_down_fused_input,
    prove_zkai_d128_gate_value_activation_down_fused_envelope,
    verify_zkai_d128_gate_value_activation_down_fused_envelope,
    zkai_d128_activation_swiglu_input_from_json_str, zkai_d128_down_projection_input_from_json_str,
    zkai_d128_gate_value_activation_down_fused_envelope_from_json_slice,
    zkai_d128_gate_value_activation_down_fused_input_from_json_str,
    zkai_d128_gate_value_projection_input_from_json_str,
    ZKAI_D128_ACTIVATION_SWIGLU_MAX_JSON_BYTES, ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES,
    ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES,
    ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES,
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
    eprintln!("zkai_d128_gate_value_activation_down_fused_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_d128_gate_value_activation_down_fused_proof build-input <gate-value.json> <activation.json> <down.json> <input.json> | prove <input.json> <envelope.json> | verify <envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "build-input" => {
            if args.len() != 4 {
                return Err(
                    "usage: build-input <gate-value.json> <activation.json> <down.json> <input.json>"
                        .to_string(),
                );
            }
            let gate_path = PathBuf::from(&args[0]);
            let activation_path = PathBuf::from(&args[1]);
            let down_path = PathBuf::from(&args[2]);
            let input_path = PathBuf::from(&args[3]);
            let gate_raw = read_bounded_utf8(
                &gate_path,
                ZKAI_D128_GATE_VALUE_PROJECTION_MAX_JSON_BYTES,
                "gate/value input JSON",
            )?;
            let activation_raw = read_bounded_utf8(
                &activation_path,
                ZKAI_D128_ACTIVATION_SWIGLU_MAX_JSON_BYTES,
                "activation/SwiGLU input JSON",
            )?;
            let down_raw = read_bounded_utf8(
                &down_path,
                ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES,
                "down-projection input JSON",
            )?;
            let gate = zkai_d128_gate_value_projection_input_from_json_str(&gate_raw)
                .map_err(|error| error.to_string())?;
            let activation = zkai_d128_activation_swiglu_input_from_json_str(&activation_raw)
                .map_err(|error| error.to_string())?;
            let down = zkai_d128_down_projection_input_from_json_str(&down_raw)
                .map_err(|error| error.to_string())?;
            let input =
                build_zkai_d128_gate_value_activation_down_fused_input(gate, activation, down)
                    .map_err(|error| error.to_string())?;
            let input_bytes = serde_json::to_vec_pretty(&input)
                .map_err(|error| format!("failed to serialize input: {error}"))?;
            if input_bytes.len() > ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES {
                return Err(format!(
                    "input JSON exceeds max size: got {} bytes, limit {} bytes",
                    input_bytes.len(),
                    ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES
                ));
            }
            atomic_write_file(&input_path, &input_bytes, "down-fused input")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-activation-down-fused-proof-cli-summary-v1",
                "mode": "build-input",
                "gate_value_input_path": gate_path.display().to_string(),
                "activation_input_path": activation_path.display().to_string(),
                "down_projection_input_path": down_path.display().to_string(),
                "input_path": input_path.display().to_string(),
                "input_size_bytes": input_bytes.len(),
                "statement_commitment": input.statement_commitment,
                "public_instance_commitment": input.public_instance_commitment,
                "gate_value_row_count": input.gate_value_row_count,
                "activation_row_count": input.activation_row_count,
                "down_projection_row_count": input.down_projection_row_count,
                "claim_boundary": "down_fused_input_not_full_block_not_nanozk_win",
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
                ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES,
                "down-fused input JSON",
            )?;
            let input = zkai_d128_gate_value_activation_down_fused_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_gate_value_activation_down_fused_envelope(&input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_gate_value_activation_down_fused_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let envelope_bytes = serde_json::to_vec_pretty(&envelope)
                .map_err(|error| format!("failed to serialize envelope: {error}"))?;
            if envelope_bytes.len() > ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES
            {
                return Err(format!(
                    "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            atomic_write_file(&envelope_path, &envelope_bytes, "down-fused envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-activation-down-fused-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "gate_value_row_count": envelope.input.gate_value_row_count,
                "activation_row_count": envelope.input.activation_row_count,
                "down_projection_row_count": envelope.input.down_projection_row_count,
                "claim_boundary": "d128_gate_value_activation_down_fused_native_proof_not_full_block_not_nanozk_win",
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
                ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES,
                "down-fused envelope JSON",
            )?;
            let envelope =
                zkai_d128_gate_value_activation_down_fused_envelope_from_json_slice(&raw)
                    .map_err(|error| error.to_string())?;
            verify_zkai_d128_gate_value_activation_down_fused_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-gate-value-activation-down-fused-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "gate_value_row_count": envelope.input.gate_value_row_count,
                "activation_row_count": envelope.input.activation_row_count,
                "down_projection_row_count": envelope.input.down_projection_row_count,
                "verified": true,
                "claim_boundary": "d128_gate_value_activation_down_fused_native_proof_not_full_block_not_nanozk_win",
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
    let file = fs::OpenOptions::new()
        .read(true)
        .open(path)
        .map_err(|error| format!("failed to open {label} {}: {error}", path.display()))?;

    let metadata = file
        .metadata()
        .map_err(|error| format!("failed to stat {label} {}: {error}", path.display()))?;
    if !metadata.is_file() {
        return Err(format!("{label} is not a regular file: {}", path.display()));
    }
    if metadata.len() as usize > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got {} bytes, limit {} bytes",
            metadata.len(),
            max_bytes
        ));
    }
    let mut reader = std::io::BufReader::new(file);
    let mut buf = Vec::new();
    reader
        .by_ref()
        .take(max_bytes as u64 + 1)
        .read_to_end(&mut buf)
        .map_err(|error| format!("failed to read {label} {}: {error}", path.display()))?;
    if buf.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got at least {} bytes, limit {} bytes",
            buf.len(),
            max_bytes
        ));
    }
    Ok(buf)
}

#[cfg(feature = "stwo-backend")]
fn atomic_write_file(path: &Path, bytes: &[u8], label: &str) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent)
        .map_err(|error| format!("failed to create {}: {error}", parent.display()))?;
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("system clock before UNIX_EPOCH: {error}"))?
        .as_nanos();
    let tmp = parent.join(format!(
        ".{}.{}.tmp",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("gate-value-activation-down-fused"),
        unique
    ));
    {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp)
            .map_err(|error| format!("failed to create temp {}: {error}", tmp.display()))?;
        file.write_all(bytes)
            .map_err(|error| format!("failed to write temp {}: {error}", tmp.display()))?;
        file.sync_all()
            .map_err(|error| format!("failed to sync temp {}: {error}", tmp.display()))?;
    }
    fs::rename(&tmp, path).map_err(|error| {
        let _ = fs::remove_file(&tmp);
        format!(
            "failed to atomically replace {label} {}: {error}",
            path.display()
        )
    })
}
