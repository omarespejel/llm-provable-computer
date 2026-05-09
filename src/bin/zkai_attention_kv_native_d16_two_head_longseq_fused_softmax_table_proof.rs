use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    prove_zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope,
    verify_zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope,
    zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope_from_json_slice,
    zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_source_input_from_json_str,
    ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
    ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES,
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
        "zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_proof requires --features stwo-backend"
    );
    ExitCode::from(2)
}

#[cfg(feature = "stwo-backend")]
fn run() -> Result<String, String> {
    run_with_args(std::env::args_os().skip(1).collect())
}

#[cfg(feature = "stwo-backend")]
fn run_with_args(mut args: Vec<std::ffi::OsString>) -> Result<String, String> {
    if args.is_empty() {
        return Err("usage: zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_proof prove <source-input.json> <fused-envelope.json> | verify <fused-envelope.json>".to_string());
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
                ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
                "source input JSON",
            )?;
            let raw = std::str::from_utf8(&raw).map_err(|error| {
                format!(
                    "failed to decode source input JSON {}: {error}",
                    input_path.display()
                )
            })?;
            let source_input =
                zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_source_input_from_json_str(
                    raw,
                )
                .map_err(|error| error.to_string())?;
            let envelope =
                prove_zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope(
                    &source_input,
                )
                .map_err(|error| error.to_string())?;
            verify_zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope(
                &envelope,
            )
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
                > ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
            {
                return Err(format!(
                    "fused envelope JSON exceeds max size: got {} bytes, limit {} bytes",
                    envelope_bytes.len(),
                    ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
                ));
            }
            fs::write(&envelope_path, &envelope_bytes).map_err(|error| {
                format!(
                    "failed to write fused envelope {}: {error}",
                    envelope_path.display()
                )
            })?;
            let input_path_json = input_path.to_string_lossy().into_owned();
            let envelope_path_json = envelope_path.to_string_lossy().into_owned();
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-cli-summary-v1",
                "mode": "prove",
                "source_input_path": input_path_json,
                "fused_envelope_path": envelope_path_json,
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
                ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES,
                "fused envelope JSON",
            )?;
            let envelope =
                zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope_from_json_slice(
                    &raw,
                )
                .map_err(|error| error.to_string())?;
            verify_zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_envelope(
                &envelope,
            )
            .map_err(|error| error.to_string())?;
            let envelope_path_json = envelope_path.to_string_lossy().into_owned();
            Ok(serde_json::json!({
                "schema": "zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-cli-summary-v1",
                "mode": "verify",
                "fused_envelope_path": envelope_path_json,
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
    let preflight_metadata = fs::metadata(path)
        .map_err(|error| format!("failed to stat {} {}: {error}", label, path.display()))?;
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

#[cfg(all(test, feature = "stwo-backend"))]
mod tests {
    use super::{
        read_bounded_file, run_with_args,
        ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES,
    };
    use std::{
        fs,
        path::PathBuf,
        process,
        time::{SystemTime, UNIX_EPOCH},
    };

    fn temp_dir(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time before epoch")
            .as_nanos();
        std::env::temp_dir().join(format!(
            "zkai-longseq-fused-cli-{label}-{}-{nonce}",
            process::id()
        ))
    }

    #[test]
    fn read_bounded_file_rejects_non_file_and_oversized_input() {
        let dir = temp_dir("reader");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("create temp dir");
        let oversized = dir.join("oversized.json");
        let valid = dir.join("valid.json");
        fs::write(&oversized, b"abcd").expect("write oversized fixture");
        fs::write(&valid, b"abc").expect("write valid fixture");

        let non_file_error = read_bounded_file(&dir, 8, "fixture").expect_err("directory rejected");
        assert!(non_file_error.contains("not a regular file"));
        let oversized_error =
            read_bounded_file(&oversized, 3, "fixture").expect_err("oversized file rejected");
        assert!(oversized_error.contains("exceeds max size"));
        assert_eq!(
            read_bounded_file(&valid, 3, "fixture").expect("valid file accepted"),
            b"abc"
        );

        fs::remove_dir_all(&dir).expect("remove temp dir");
    }

    #[test]
    fn verify_mode_rejects_non_file_malformed_and_oversized_inputs() {
        let dir = temp_dir("verify");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("create temp dir");
        let malformed = dir.join("malformed.json");
        let oversized = dir.join("oversized.json");
        fs::write(&malformed, b"{}").expect("write malformed fixture");
        fs::write(
            &oversized,
            vec![
                b'x';
                ZKAI_ATTENTION_KV_NATIVE_D16_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
                    + 1
            ],
        )
        .expect("write oversized fixture");

        let non_file_error = run_with_args(vec!["verify".into(), dir.as_os_str().to_os_string()])
            .expect_err("directory rejected");
        assert!(non_file_error.contains("not a regular file"));
        let malformed_error =
            run_with_args(vec!["verify".into(), malformed.as_os_str().to_os_string()])
                .expect_err("malformed envelope rejected");
        assert!(
            malformed_error.contains("missing field")
                || malformed_error.contains("unknown variant")
                || malformed_error.contains("expected")
        );
        let oversized_error =
            run_with_args(vec!["verify".into(), oversized.as_os_str().to_os_string()])
                .expect_err("oversized envelope rejected");
        assert!(oversized_error.contains("exceeds max size"));

        fs::remove_dir_all(&dir).expect("remove temp dir");
    }
}
