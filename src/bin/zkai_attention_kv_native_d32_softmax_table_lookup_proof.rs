#[cfg(feature = "stwo-backend")]
use std::ffi::OsString;
#[cfg(feature = "stwo-backend")]
use std::fs;
#[cfg(feature = "stwo-backend")]
use std::io::{Read, Write};
#[cfg(feature = "stwo-backend")]
use std::path::{Path, PathBuf};
#[cfg(feature = "stwo-backend")]
use std::process;
use std::process::ExitCode;
#[cfg(feature = "stwo-backend")]
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
    run_with_args(std::env::args_os().skip(1))
}

#[cfg(feature = "stwo-backend")]
fn run_with_args<I>(args: I) -> Result<String, String>
where
    I: IntoIterator<Item = OsString>,
{
    let mut args = args.into_iter().collect::<Vec<_>>();
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
    sync_parent_directory(parent, label, path)?;
    Ok(())
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

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn arg(value: &str) -> OsString {
        OsString::from(value)
    }

    fn temp_path(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("time")
            .as_nanos();
        std::env::temp_dir().join(format!(
            "ptvm-d32-softmax-table-lookup-cli-{label}-{}-{nonce}.json",
            std::process::id()
        ))
    }

    fn write_temp(label: &str, bytes: &[u8]) -> PathBuf {
        let path = temp_path(label);
        fs::write(&path, bytes).expect("write temp file");
        path
    }

    #[test]
    fn rejects_missing_or_unknown_cli_args() {
        assert!(run_with_args(Vec::<OsString>::new())
            .expect_err("missing args must reject")
            .contains("usage:"));
        assert_eq!(
            run_with_args(vec![arg("wat")]).expect_err("unknown mode must reject"),
            "unknown mode: wat"
        );
        assert_eq!(
            run_with_args(vec![arg("prove")]).expect_err("bad prove args must reject"),
            "usage: prove <source-input.json> <lookup-envelope.json>"
        );
        assert_eq!(
            run_with_args(vec![arg("verify")]).expect_err("bad verify args must reject"),
            "usage: verify <lookup-envelope.json>"
        );
    }

    #[test]
    fn rejects_malformed_source_input_json() {
        let input = write_temp("bad-input", b"{not-json");
        let output = temp_path("unused-output");
        let error = run_with_args(vec![
            arg("prove"),
            input.as_os_str().to_os_string(),
            output.as_os_str().to_os_string(),
        ])
        .expect_err("malformed input must reject");
        assert!(error.contains("key must be a string") || error.contains("expected ident"));
        let _ = fs::remove_file(input);
        let _ = fs::remove_file(output);
    }

    #[test]
    fn rejects_malformed_envelope_json() {
        let envelope = write_temp("bad-envelope", b"{not-json");
        let error = run_with_args(vec![arg("verify"), envelope.as_os_str().to_os_string()])
            .expect_err("malformed envelope must reject");
        assert!(error.contains("key must be a string") || error.contains("expected ident"));
        let _ = fs::remove_file(envelope);
    }

    #[test]
    fn proves_verifies_and_rejects_tampered_envelope_proof_bytes() {
        let input = write_temp(
            "source-input",
            include_bytes!(
                "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-d32-bounded-softmax-table-proof-2026-05.json"
            ),
        );
        let envelope = temp_path("lookup-envelope");
        let prove_summary = run_with_args(vec![
            arg("prove"),
            input.as_os_str().to_os_string(),
            envelope.as_os_str().to_os_string(),
        ])
        .expect("prove lookup envelope");
        assert!(prove_summary.contains("\"mode\":\"prove\""));
        let verify_summary =
            run_with_args(vec![arg("verify"), envelope.as_os_str().to_os_string()])
                .expect("verify lookup envelope");
        assert!(verify_summary.contains("\"verified\":true"));

        let mut tampered: serde_json::Value =
            serde_json::from_slice(&fs::read(&envelope).expect("read lookup envelope"))
                .expect("lookup envelope JSON");
        let proof = tampered
            .get_mut("proof")
            .and_then(serde_json::Value::as_array_mut)
            .expect("proof bytes");
        let first = proof
            .first()
            .and_then(serde_json::Value::as_u64)
            .expect("first proof byte");
        proof[0] = serde_json::Value::from((first ^ 1) as u8);
        fs::write(
            &envelope,
            serde_json::to_vec(&tampered).expect("serialize tampered lookup envelope"),
        )
        .expect("write tampered lookup envelope");
        let error = run_with_args(vec![arg("verify"), envelope.as_os_str().to_os_string()])
            .expect_err("tampered lookup envelope must reject");
        assert!(!error.is_empty());
        let _ = fs::remove_file(input);
        let _ = fs::remove_file(envelope);
    }
}
