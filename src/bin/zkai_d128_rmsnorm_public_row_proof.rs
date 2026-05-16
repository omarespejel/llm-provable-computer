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
    prove_zkai_d128_rmsnorm_public_row_envelope, verify_zkai_d128_rmsnorm_public_row_envelope,
    zkai_d128_rmsnorm_public_row_input_from_json_str, ZkAiD128RmsnormPublicRowProofEnvelope,
    ZkAiD128RmsnormPublicRowProofInput, ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
};

#[cfg(feature = "stwo-backend")]
const MAX_ENVELOPE_JSON_BYTES: usize = 4_194_304;
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
    eprintln!("zkai_d128_rmsnorm_public_row_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err(
            "usage: zkai_d128_rmsnorm_public_row_proof prove <input.json> <envelope.json> | verify <envelope.json>"
                .to_string(),
        );
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
                ZKAI_D128_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES,
                "d128 RMSNorm public-row input JSON",
            )?;
            let input =
                rmsnorm_public_row_input_from_json_str(&raw).map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_rmsnorm_public_row_envelope(&input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_rmsnorm_public_row_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            let envelope_bytes = serde_json::to_vec_pretty(&envelope)
                .map_err(|error| format!("failed to serialize envelope: {error}"))?;
            if envelope_bytes.len() > MAX_ENVELOPE_JSON_BYTES {
                return Err(format!(
                    "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    MAX_ENVELOPE_JSON_BYTES
                ));
            }
            atomic_write_file(
                &envelope_path,
                &envelope_bytes,
                "RMSNorm public-row envelope",
            )?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-public-row-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "row_count": envelope.input.row_count,
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "claim_boundary": "d128_rmsnorm_public_row_native_proof_not_full_block_not_nanozk_win",
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
                MAX_ENVELOPE_JSON_BYTES,
                "d128 RMSNorm public-row envelope JSON",
            )?;
            let envelope: ZkAiD128RmsnormPublicRowProofEnvelope = serde_json::from_slice(&raw)
                .map_err(|error| format!("failed to parse envelope: {error}"))?;
            verify_zkai_d128_rmsnorm_public_row_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-public-row-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "row_count": envelope.input.row_count,
                "verified": true,
                "claim_boundary": "d128_rmsnorm_public_row_native_proof_not_full_block_not_nanozk_win",
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
fn rmsnorm_public_row_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128RmsnormPublicRowProofInput, String> {
    match zkai_d128_rmsnorm_public_row_input_from_json_str(raw_json) {
        Ok(input) => Ok(input),
        Err(direct_error) => {
            let wrapper: serde_json::Value =
                serde_json::from_str(raw_json).map_err(|_| direct_error.to_string())?;
            if wrapper.get("schema").and_then(serde_json::Value::as_str)
                != Some(ATTENTION_DERIVED_RMSNORM_WRAPPER_SCHEMA)
            {
                return Err(
                    "RMSNorm wrapper schema is not approved for public-row proof".to_string(),
                );
            }
            if wrapper.get("decision").and_then(serde_json::Value::as_str)
                != Some(ATTENTION_DERIVED_RMSNORM_WRAPPER_DECISION)
            {
                return Err(
                    "RMSNorm wrapper decision is not approved for public-row proof".to_string(),
                );
            }
            let nested = wrapper.get("rmsnorm_public_row_payload").ok_or_else(|| {
                "RMSNorm wrapper is missing rmsnorm_public_row_payload".to_string()
            })?;
            let nested_raw = serde_json::to_string(nested)
                .map_err(|error| format!("failed to serialize nested RMSNorm input: {error}"))?;
            zkai_d128_rmsnorm_public_row_input_from_json_str(&nested_raw)
                .map_err(|error| error.to_string())
        }
    }
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
        return Err(format!(
            "{label} requires Unix O_NOFOLLOW file opening for path safety: {}",
            path.display()
        ));
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

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;
    #[cfg(unix)]
    use std::os::unix::fs::symlink;

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

    #[cfg(unix)]
    #[test]
    fn read_bounded_file_rejects_symlink_input() {
        let dir = tempfile::tempdir().expect("temp dir");
        let target = dir.path().join("target.json");
        let link = dir.path().join("input.json");
        fs::write(&target, b"{}").expect("write target");
        symlink(&target, &link).expect("create symlink");

        let error = read_bounded_file(&link, 1024, "test input").expect_err("symlink must reject");
        assert!(
            error.contains("without following symlinks") || error.contains("symlink"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn read_bounded_file_enforces_post_read_limit() {
        let dir = tempfile::tempdir().expect("temp dir");
        let target = dir.path().join("input.json");
        fs::write(&target, b"0123456789").expect("write target");

        let error =
            read_bounded_file(&target, 4, "test input").expect_err("oversized input must reject");
        assert!(
            error.contains("exceeds max size"),
            "unexpected error: {error}"
        );
    }

    #[cfg(unix)]
    #[test]
    fn atomic_write_file_rejects_symlink_target() {
        let dir = tempfile::tempdir().expect("temp dir");
        let target = dir.path().join("target.json");
        let link = dir.path().join("output.json");
        fs::write(&target, b"{}").expect("write target");
        symlink(&target, &link).expect("create symlink");

        let error =
            atomic_write_file(&link, b"{}", "test output").expect_err("symlink must reject");
        assert!(
            error.contains("refusing to overwrite symlink"),
            "unexpected error: {error}"
        );
    }
}
