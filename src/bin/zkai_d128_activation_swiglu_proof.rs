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
    prove_zkai_d128_activation_swiglu_envelope, verify_zkai_d128_activation_swiglu_envelope,
    zkai_d128_activation_swiglu_input_from_json_str, ZkAiD128ActivationSwiGluEnvelope,
    ZKAI_D128_ACTIVATION_SWIGLU_MAX_JSON_BYTES,
};

#[cfg(feature = "stwo-backend")]
const MAX_ENVELOPE_JSON_BYTES: usize = 4_194_304;

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
    eprintln!("zkai_d128_activation_swiglu_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err(
            "usage: zkai_d128_activation_swiglu_proof prove <input.json> <envelope.json> | verify <envelope.json>"
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
                ZKAI_D128_ACTIVATION_SWIGLU_MAX_JSON_BYTES,
                "d128 activation/SwiGLU input JSON",
            )?;
            let input = zkai_d128_activation_swiglu_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_activation_swiglu_envelope(&input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_activation_swiglu_envelope(&envelope)
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
                "activation/SwiGLU envelope",
            )?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-activation-swiglu-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "row_count": envelope.input.row_count,
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "claim_boundary": "d128_activation_swiglu_native_proof_not_full_block_not_nanozk_win",
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
                "d128 activation/SwiGLU envelope JSON",
            )?;
            let envelope: ZkAiD128ActivationSwiGluEnvelope = serde_json::from_slice(&raw)
                .map_err(|error| format!("failed to parse envelope: {error}"))?;
            verify_zkai_d128_activation_swiglu_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-activation-swiglu-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "row_count": envelope.input.row_count,
                "verified": true,
                "claim_boundary": "d128_activation_swiglu_native_proof_not_full_block_not_nanozk_win",
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
        .ok_or_else(|| format!("{label} output has no parent: {}", path.display()))?;
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
            .unwrap_or("activation-swiglu-envelope"),
        unique
    ));
    {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp)
            .map_err(|error| format!("failed to create temp {label} {}: {error}", tmp.display()))?;
        file.write_all(bytes)
            .map_err(|error| format!("failed to write temp {label} {}: {error}", tmp.display()))?;
        file.sync_all()
            .map_err(|error| format!("failed to sync temp {label} {}: {error}", tmp.display()))?;
    }
    fs::rename(&tmp, path).map_err(|error| {
        format!(
            "failed to rename temp {label} to {}: {error}",
            path.display()
        )
    })
}
