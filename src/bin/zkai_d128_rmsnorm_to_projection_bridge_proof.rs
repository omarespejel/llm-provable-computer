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
    prove_zkai_d128_rmsnorm_to_projection_bridge_envelope,
    verify_zkai_d128_rmsnorm_to_projection_bridge_envelope,
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str,
    ZkAiD128RmsnormToProjectionBridgeEnvelope,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
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
    eprintln!("zkai_d128_rmsnorm_to_projection_bridge_proof requires --features stwo-backend");
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    let mut args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        return Err(
            "usage: zkai_d128_rmsnorm_to_projection_bridge_proof prove <input.json> <envelope.json> | verify <envelope.json>"
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
                ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES,
                "d128 RMSNorm-to-projection bridge input JSON",
            )?;
            let input = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(&raw)
                .map_err(|error| error.to_string())?;
            let envelope = prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input)
                .map_err(|error| error.to_string())?;
            verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope)
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
            atomic_write_file(&envelope_path, &envelope_bytes, "RMSNorm bridge envelope")?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-to-projection-bridge-proof-cli-summary-v1",
                "mode": "prove",
                "input_path": input_path.display().to_string(),
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": envelope_bytes.len(),
                "row_count": envelope.input.row_count,
                "statement_commitment": envelope.input.statement_commitment,
                "public_instance_commitment": envelope.input.public_instance_commitment,
                "claim_boundary": "d128_rmsnorm_to_projection_bridge_native_proof_not_full_block_not_nanozk_win",
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
                "d128 RMSNorm-to-projection bridge envelope JSON",
            )?;
            let envelope: ZkAiD128RmsnormToProjectionBridgeEnvelope = serde_json::from_slice(&raw)
                .map_err(|error| format!("failed to parse envelope: {error}"))?;
            verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope)
                .map_err(|error| error.to_string())?;
            Ok(serde_json::json!({
                "schema": "zkai-d128-rmsnorm-to-projection-bridge-proof-cli-summary-v1",
                "mode": "verify",
                "envelope_path": envelope_path.display().to_string(),
                "proof_size_bytes": envelope.proof.len(),
                "envelope_size_bytes": raw.len(),
                "row_count": envelope.input.row_count,
                "verified": true,
                "claim_boundary": "d128_rmsnorm_to_projection_bridge_native_proof_not_full_block_not_nanozk_win",
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
    reject_symlinked_ancestors(path, label)?;
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
    reject_symlinked_ancestors(path, label)?;
    if let Some(parent) = path.parent() {
        ensure_directory_without_symlinks(parent, label)?;
        reject_symlinked_ancestors(path, label)?;
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
    reject_symlinked_ancestors(&tmp_path, label)?;
    write_temp_file(&tmp_path, bytes)?;
    publish_temp_file(&tmp_path, path, label)
}

#[cfg(feature = "stwo-backend")]
fn write_temp_file(tmp_path: &Path, bytes: &[u8]) -> Result<(), String> {
    let mut file = fs::File::create_new(tmp_path)
        .map_err(|error| format!("failed to create {}: {error}", tmp_path.display()))?;
    let write_result = file
        .write_all(bytes)
        .map_err(|error| format!("failed to write {}: {error}", tmp_path.display()))
        .and_then(|()| {
            file.sync_all()
                .map_err(|error| format!("failed to sync {}: {error}", tmp_path.display()))
        });
    if let Err(error) = write_result {
        drop(file);
        let _ = fs::remove_file(tmp_path);
        return Err(error);
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn reject_symlinked_ancestors(path: &Path, label: &str) -> Result<(), String> {
    #[cfg(not(unix))]
    {
        let _ = path;
        let _ = label;
        Ok(())
    }
    #[cfg(unix)]
    {
        for ancestor in path.ancestors().skip(1) {
            if ancestor.as_os_str().is_empty() {
                continue;
            }
            match fs::symlink_metadata(ancestor) {
                Ok(metadata) if metadata.file_type().is_symlink() => {
                    return Err(format!(
                        "refusing symlinked parent for {label}: {}",
                        ancestor.display()
                    ));
                }
                Ok(_) => {}
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
                Err(error) => {
                    return Err(format!(
                        "failed to inspect parent {} for {label}: {error}",
                        ancestor.display()
                    ));
                }
            }
        }
        Ok(())
    }
}

#[cfg(feature = "stwo-backend")]
fn ensure_directory_without_symlinks(path: &Path, label: &str) -> Result<(), String> {
    if path.as_os_str().is_empty() {
        return Ok(());
    }
    let mut current = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::RootDir => {
                current.push(component.as_os_str());
            }
            std::path::Component::CurDir => {
                if current.as_os_str().is_empty() {
                    current.push(".");
                }
            }
            std::path::Component::Normal(part) => {
                current.push(part);
                ensure_existing_or_created_dir(&current, label)?;
            }
            std::path::Component::ParentDir => {
                return Err(format!(
                    "refusing parent-directory component in {label} path: {}",
                    path.display()
                ));
            }
            std::path::Component::Prefix(_) => {
                return Err(format!(
                    "unsupported path prefix for {label}: {}",
                    path.display()
                ));
            }
        }
    }
    Ok(())
}

#[cfg(feature = "stwo-backend")]
fn ensure_existing_or_created_dir(path: &Path, label: &str) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(format!(
                "refusing symlinked directory for {label}: {}",
                path.display()
            ));
        }
        Ok(metadata) if metadata.is_dir() => Ok(()),
        Ok(_) => Err(format!(
            "refusing non-directory parent for {label}: {}",
            path.display()
        )),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            match fs::create_dir(path) {
                Ok(()) => {}
                Err(create_error) if create_error.kind() == std::io::ErrorKind::AlreadyExists => {}
                Err(create_error) => {
                    return Err(format!(
                        "failed to create directory {} for {label}: {create_error}",
                        path.display()
                    ));
                }
            }
            match fs::symlink_metadata(path) {
                Ok(metadata) if metadata.file_type().is_symlink() => Err(format!(
                    "refusing symlinked directory for {label}: {}",
                    path.display()
                )),
                Ok(metadata) if metadata.is_dir() => Ok(()),
                Ok(_) => Err(format!(
                    "refusing non-directory parent for {label}: {}",
                    path.display()
                )),
                Err(stat_error) => Err(format!(
                    "failed to inspect created directory {} for {label}: {stat_error}",
                    path.display()
                )),
            }
        }
        Err(error) => Err(format!(
            "failed to inspect parent directory {} for {label}: {error}",
            path.display()
        )),
    }
}

#[cfg(feature = "stwo-backend")]
fn publish_temp_file(tmp_path: &Path, path: &Path, label: &str) -> Result<(), String> {
    match fs::rename(tmp_path, path) {
        Ok(()) => Ok(()),
        Err(first_error)
            if matches!(
                first_error.kind(),
                std::io::ErrorKind::AlreadyExists | std::io::ErrorKind::PermissionDenied
            ) =>
        {
            match existing_non_symlink_destination(path, label) {
                Ok(true) => {
                    if let Err(remove_error) = fs::remove_file(path) {
                        let _ = fs::remove_file(tmp_path);
                        return Err(format!(
                            "failed to replace existing {label} {} after publish error {first_error}: {remove_error}",
                            path.display()
                        ));
                    }
                }
                Ok(false) => {}
                Err(error) => {
                    let _ = fs::remove_file(tmp_path);
                    return Err(error);
                }
            }
            if let Err(second_error) = fs::rename(tmp_path, path) {
                let _ = fs::remove_file(tmp_path);
                return Err(format!(
                    "failed to publish replacement {label} {} after handling existing destination: {second_error}",
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

#[cfg(feature = "stwo-backend")]
fn existing_non_symlink_destination(path: &Path, label: &str) -> Result<bool, String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => Err(format!(
            "refusing to overwrite symlink for {label}: {}",
            path.display()
        )),
        Ok(metadata) if metadata.is_file() => Ok(true),
        Ok(_) => Err(format!(
            "refusing to replace non-file destination for {label}: {}",
            path.display()
        )),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(format!(
            "failed to inspect destination {} for {label}: {error}",
            path.display()
        )),
    }
}

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;
    #[cfg(unix)]
    use std::os::unix::fs::symlink;

    fn local_tempdir() -> tempfile::TempDir {
        tempfile::Builder::new()
            .prefix("zkai-d128-rmsnorm-bridge-test-")
            .tempdir_in(std::env::current_dir().expect("current dir"))
            .expect("temp dir")
    }

    #[cfg(unix)]
    #[test]
    fn read_bounded_file_rejects_symlink_input() {
        let dir = local_tempdir();
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

    #[cfg(unix)]
    #[test]
    fn read_bounded_file_rejects_symlink_parent() {
        let dir = local_tempdir();
        let real = dir.path().join("real");
        let link = dir.path().join("link");
        fs::create_dir(&real).expect("create real dir");
        symlink(&real, &link).expect("create parent symlink");
        fs::write(real.join("input.json"), b"{}").expect("write target");

        let error = read_bounded_file(&link.join("input.json"), 1024, "test input")
            .expect_err("symlinked parent must reject");
        assert!(
            error.contains("symlinked parent"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn read_bounded_file_enforces_post_read_limit() {
        let dir = local_tempdir();
        let target = dir.path().join("input.json");
        fs::write(&target, b"0123456789").expect("write target");

        let error =
            read_bounded_file(&target, 4, "test input").expect_err("oversized input must reject");
        assert!(
            error.contains("exceeds max size"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn atomic_write_file_creates_nested_directory_without_symlink() {
        let dir = local_tempdir();
        let output = dir.path().join("nested").join("proof").join("output.json");

        atomic_write_file(&output, b"{\"ok\":true}\n", "test output").expect("atomic write");

        assert_eq!(fs::read(&output).expect("read output"), b"{\"ok\":true}\n");
    }

    #[cfg(unix)]
    #[test]
    fn atomic_write_file_rejects_symlink_target() {
        let dir = local_tempdir();
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

    #[cfg(unix)]
    #[test]
    fn atomic_write_file_rejects_symlink_parent() {
        let dir = local_tempdir();
        let real = dir.path().join("real");
        let link = dir.path().join("link");
        fs::create_dir(&real).expect("create real dir");
        symlink(&real, &link).expect("create parent symlink");

        let output = link.join("output.json");
        let error = atomic_write_file(&output, b"{}", "test output")
            .expect_err("symlinked parent must reject");
        assert!(
            error.contains("symlinked parent"),
            "unexpected error: {error}"
        );
        assert!(!real.join("output.json").exists());
    }
}
