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
    build_zkai_d128_rmsnorm_mlp_fused_input, prove_zkai_d128_rmsnorm_mlp_fused_envelope,
    verify_zkai_d128_rmsnorm_mlp_fused_envelope, zkai_d128_activation_swiglu_input_from_json_str,
    zkai_d128_down_projection_input_from_json_str,
    zkai_d128_gate_value_projection_input_from_json_str,
    zkai_d128_residual_add_input_from_json_str,
    zkai_d128_rmsnorm_mlp_fused_envelope_from_json_slice,
    zkai_d128_rmsnorm_mlp_fused_input_from_json_str,
    zkai_d128_rmsnorm_public_row_input_from_json_str,
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str,
    ZKAI_D128_ACTIVATION_SWIGLU_MAX_JSON_BYTES, ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES,
    ZKAI_D128_GATE_VALUE_PROJECTION_MAX_JSON_BYTES, ZKAI_D128_RESIDUAL_ADD_MAX_JSON_BYTES,
    ZKAI_D128_RMSNORM_MLP_FUSED_MAX_ENVELOPE_JSON_BYTES,
    ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES, ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
};

#[cfg(feature = "stwo-backend")]
const ATTENTION_DERIVED_RMSNORM_WRAPPER_SCHEMA: &str =
    "zkai-attention-derived-d128-rmsnorm-public-row-gate-v1";
#[cfg(feature = "stwo-backend")]
const ATTENTION_DERIVED_RMSNORM_WRAPPER_DECISION: &str =
    "GO_ATTENTION_DERIVED_D128_RMSNORM_PUBLIC_ROW_INPUT";

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
    eprintln!("zkai_d128_rmsnorm_mlp_fused_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err("usage: zkai_d128_rmsnorm_mlp_fused_proof build-input <rmsnorm.json> <bridge.json> <gate-value.json> <activation.json> <down.json> <residual.json> <input.json> | prove <input.json> <envelope.json> | verify <envelope.json>".to_string());
    }
    let mode = args.remove(0).to_string_lossy().to_string();
    match mode.as_str() {
        "build-input" => {
            if args.len() != 7 {
                return Err("usage: build-input <rmsnorm.json> <bridge.json> <gate-value.json> <activation.json> <down.json> <residual.json> <input.json>".to_string());
            }
            let rmsnorm_path = PathBuf::from(&args[0]);
            let bridge_path = PathBuf::from(&args[1]);
            let gate_path = PathBuf::from(&args[2]);
            let activation_path = PathBuf::from(&args[3]);
            let down_path = PathBuf::from(&args[4]);
            let residual_path = PathBuf::from(&args[5]);
            let input_path = PathBuf::from(&args[6]);
            let rmsnorm = rmsnorm_public_row_input_from_json_str(&read_bounded_utf8(
                &rmsnorm_path,
                ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
                "RMSNorm input JSON",
            )?)
            .map_err(|error| error.to_string())?;
            let bridge =
                zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(&read_bounded_utf8(
                    &bridge_path,
                    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
                    "projection bridge input JSON",
                )?)
                .map_err(|error| error.to_string())?;
            let gate = zkai_d128_gate_value_projection_input_from_json_str(&read_bounded_utf8(
                &gate_path,
                ZKAI_D128_GATE_VALUE_PROJECTION_MAX_JSON_BYTES,
                "gate/value input JSON",
            )?)
            .map_err(|error| error.to_string())?;
            let activation = zkai_d128_activation_swiglu_input_from_json_str(&read_bounded_utf8(
                &activation_path,
                ZKAI_D128_ACTIVATION_SWIGLU_MAX_JSON_BYTES,
                "activation/SwiGLU input JSON",
            )?)
            .map_err(|error| error.to_string())?;
            let down = zkai_d128_down_projection_input_from_json_str(&read_bounded_utf8(
                &down_path,
                ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES,
                "down-projection input JSON",
            )?)
            .map_err(|error| error.to_string())?;
            let residual = zkai_d128_residual_add_input_from_json_str(&read_bounded_utf8(
                &residual_path,
                ZKAI_D128_RESIDUAL_ADD_MAX_JSON_BYTES,
                "residual-add input JSON",
            )?)
            .map_err(|error| error.to_string())?;
            let input = build_zkai_d128_rmsnorm_mlp_fused_input(
                rmsnorm, bridge, gate, activation, down, residual,
            )
            .map_err(|error| error.to_string())?;
            let input_bytes = pretty_json_bytes_with_trailing_newline(
                &input,
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES,
                "input JSON",
            )?;
            atomic_write_file(&input_path, &input_bytes, "RMSNorm-MLP fused input")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-mlp-fused-proof-cli-summary-v1",
                "mode": "build-input",
                "input_path": input_path.display().to_string(),
                "input_size_bytes": input_bytes.len(),
                "statement_commitment": input.statement_commitment,
                "public_instance_commitment": input.public_instance_commitment,
                "proof_native_parameter_commitment": input.proof_native_parameter_commitment,
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
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_JSON_BYTES,
                "RMSNorm-MLP fused input JSON",
            )?;
            let input = zkai_d128_rmsnorm_mlp_fused_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_rmsnorm_mlp_fused_envelope(&input)
                .map_err(|error| error.to_string())?;
            let bytes = pretty_json_bytes_with_trailing_newline(
                &envelope,
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_ENVELOPE_JSON_BYTES,
                "envelope JSON",
            )?;
            atomic_write_file(&envelope_path, &bytes, "RMSNorm-MLP fused envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-mlp-fused-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": bytes.len(),
                "proof_backend_version": envelope.proof_backend_version,
                "statement_version": envelope.statement_version,
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
                ZKAI_D128_RMSNORM_MLP_FUSED_MAX_ENVELOPE_JSON_BYTES,
                "RMSNorm-MLP fused envelope JSON",
            )?;
            let envelope = zkai_d128_rmsnorm_mlp_fused_envelope_from_json_slice(&raw)
                .map_err(|error| error.to_string())?;
            let verified = verify_zkai_d128_rmsnorm_mlp_fused_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-mlp-fused-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "verified": verified,
                "proof_size_bytes": envelope.proof.len(),
            })
            .to_string())
        }
        _ => Err(format!("unknown mode: {mode}")),
    }
}

#[cfg(feature = "stwo-backend")]
fn rmsnorm_public_row_input_from_json_str(
    raw_json: &str,
) -> Result<llm_provable_computer::stwo_backend::ZkAiD128RmsnormPublicRowProofInput, String> {
    match zkai_d128_rmsnorm_public_row_input_from_json_str(raw_json) {
        Ok(input) => return Ok(input),
        Err(direct_error) => {
            let wrapper: serde_json::Value =
                serde_json::from_str(raw_json).map_err(|_| direct_error.to_string())?;
            let Some(nested) = wrapper.get("rmsnorm_public_row_payload") else {
                return Err(direct_error.to_string());
            };
            if wrapper.get("schema").and_then(serde_json::Value::as_str)
                != Some(ATTENTION_DERIVED_RMSNORM_WRAPPER_SCHEMA)
            {
                return Err("RMSNorm wrapper schema is not approved for fused input".to_string());
            }
            if wrapper.get("decision").and_then(serde_json::Value::as_str)
                != Some(ATTENTION_DERIVED_RMSNORM_WRAPPER_DECISION)
            {
                return Err("RMSNorm wrapper decision is not approved for fused input".to_string());
            }
            let nested_raw = serde_json::to_string(nested)
                .map_err(|error| format!("failed to serialize nested RMSNorm payload: {error}"))?;
            zkai_d128_rmsnorm_public_row_input_from_json_str(&nested_raw)
                .map_err(|error| error.to_string())
        }
    }
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_utf8(path: &Path, max_bytes: usize, label: &str) -> Result<String, String> {
    let bytes = read_bounded_bytes(path, max_bytes, label)?;
    String::from_utf8(bytes).map_err(|error| format!("{label} is not UTF-8: {error}"))
}

#[cfg(feature = "stwo-backend")]
fn pretty_json_bytes_with_trailing_newline<T: serde::Serialize>(
    value: &T,
    max_bytes: usize,
    label: &str,
) -> Result<Vec<u8>, String> {
    let mut bytes = serde_json::to_vec_pretty(value)
        .map_err(|error| format!("failed to serialize {label}: {error}"))?;
    bytes.push(b'\n');
    if bytes.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got {} bytes, limit {} bytes",
            bytes.len(),
            max_bytes
        ));
    }
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn read_bounded_bytes(path: &Path, max_bytes: usize, label: &str) -> Result<Vec<u8>, String> {
    reject_symlink(path, label)?;
    let metadata =
        fs::metadata(path).map_err(|error| format!("failed to stat {label}: {error}"))?;
    let len = usize::try_from(metadata.len())
        .map_err(|_| format!("{label} length does not fit usize"))?;
    if len > max_bytes {
        return Err(format!(
            "{label} exceeds max size: got {len} bytes, limit {max_bytes} bytes"
        ));
    }
    let mut options = fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    options.custom_flags(libc::O_NOFOLLOW);
    let file = options
        .open(path)
        .map_err(|error| format!("failed to open {label}: {error}"))?;
    let mut bytes = Vec::with_capacity(max_bytes.min(len));
    file.take(max_bytes.saturating_add(1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("failed to read {label}: {error}"))?;
    if bytes.len() > max_bytes {
        return Err(format!(
            "{label} exceeds max size after read: got {} bytes, limit {} bytes",
            bytes.len(),
            max_bytes
        ));
    }
    Ok(bytes)
}

#[cfg(feature = "stwo-backend")]
fn atomic_write_file(path: &Path, bytes: &[u8], label: &str) -> Result<(), String> {
    reject_symlink(path, label)?;
    let parent = path
        .parent()
        .ok_or_else(|| format!("{label} path has no parent: {}", path.display()))?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("failed to create {label} parent directory: {error}"))?;
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("system clock before UNIX_EPOCH: {error}"))?
        .as_nanos();
    let tmp = parent.join(format!(
        ".{}.{}.{}.tmp",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("zkai-rmsnorm-mlp-fused"),
        std::process::id(),
        nanos
    ));
    {
        let mut options = fs::OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        options.custom_flags(libc::O_NOFOLLOW);
        let mut file = options
            .open(&tmp)
            .map_err(|error| format!("failed to create temp {label}: {error}"))?;
        file.write_all(bytes)
            .map_err(|error| format!("failed to write temp {label}: {error}"))?;
        file.sync_all()
            .map_err(|error| format!("failed to sync temp {label}: {error}"))?;
    }
    publish_temp_file(&tmp, path, label)
}

#[cfg(feature = "stwo-backend")]
fn publish_temp_file(tmp: &Path, path: &Path, label: &str) -> Result<(), String> {
    match fs::rename(tmp, path) {
        Ok(()) => Ok(()),
        Err(first_error) if first_error.kind() == ErrorKind::AlreadyExists && path.exists() => {
            if let Err(remove_error) = fs::remove_file(path) {
                let _ = fs::remove_file(tmp);
                return Err(format!(
                    "failed to replace existing {label} {} after install error {first_error}: {remove_error}",
                    path.display()
                ));
            }
            if let Err(second_error) = fs::rename(tmp, path) {
                let _ = fs::remove_file(tmp);
                return Err(format!(
                    "failed to install replacement {label} {} after removing existing destination: {second_error}",
                    path.display()
                ));
            }
            Ok(())
        }
        Err(error) => {
            let _ = fs::remove_file(tmp);
            Err(format!("failed to atomically install {label}: {error}"))
        }
    }
}

#[cfg(feature = "stwo-backend")]
fn reject_symlink(path: &Path, label: &str) -> Result<(), String> {
    let mut current = PathBuf::new();
    for component in path.components() {
        current.push(component.as_os_str());
        match fs::symlink_metadata(&current) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err(format!(
                    "{label} path component must not be a symlink: {}",
                    current.display()
                ));
            }
            Ok(_) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => {
                return Err(format!(
                    "failed to inspect {label} path component {}: {error}",
                    current.display()
                ));
            }
        }
    }
    Ok(())
}

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;

    const DERIVED_INPUT_COMMITMENT: &str =
        "blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35";

    fn derived_wrapper() -> serde_json::Value {
        serde_json::from_str(include_str!(
            "../../docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json"
        ))
        .expect("derived RMSNorm wrapper")
    }

    #[test]
    fn rmsnorm_wrapper_happy_path() {
        let wrapper = derived_wrapper();
        assert_eq!(
            wrapper.get("schema").and_then(serde_json::Value::as_str),
            Some(ATTENTION_DERIVED_RMSNORM_WRAPPER_SCHEMA)
        );
        assert_eq!(
            wrapper.get("decision").and_then(serde_json::Value::as_str),
            Some(ATTENTION_DERIVED_RMSNORM_WRAPPER_DECISION)
        );
        let parsed = rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&wrapper).expect("wrapper JSON"),
        )
        .expect("wrapped RMSNorm input parses");
        assert_eq!(parsed.input_activation_commitment, DERIVED_INPUT_COMMITMENT);
    }

    #[test]
    fn rmsnorm_wrapper_rejects_invalid_wrapper() {
        let mut wrapper = derived_wrapper();
        wrapper["schema"] = serde_json::Value::String("wrong-schema".to_string());
        assert!(rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&wrapper).expect("wrapper JSON")
        )
        .is_err());

        let mut wrapper = derived_wrapper();
        wrapper
            .as_object_mut()
            .expect("wrapper object")
            .remove("rmsnorm_public_row_payload");
        assert!(rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&wrapper).expect("wrapper JSON")
        )
        .is_err());
    }
}
