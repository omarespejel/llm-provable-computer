use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use assert_cmd::Command;
#[cfg(any(feature = "onnx-export", feature = "stwo-backend"))]
use blake2::digest::{Update, VariableOutput};
#[cfg(any(feature = "onnx-export", feature = "stwo-backend"))]
use blake2::Blake2bVar;
#[cfg(feature = "stwo-backend")]
use flate2::GzBuilder;
#[cfg(feature = "onnx-export")]
use jsonschema::{Draft, JSONSchema};
use predicates::prelude::*;
#[cfg(feature = "stwo-backend")]
use std::io::Write;
#[cfg(feature = "stwo-backend")]
use std::sync::{Mutex, OnceLock};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    commit_phase12_shared_lookup_rows, prove_phase10_shared_binary_step_lookup_envelope,
    prove_phase10_shared_normalization_lookup_envelope, Phase10SharedLookupProofEnvelope,
    Phase10SharedNormalizationLookupProofEnvelope, Phase3LookupTableRow,
    STWO_BACKEND_VERSION_PHASE12,
    STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27,
    STWO_DECODING_CHAIN_VERSION_PHASE12, STWO_DECODING_CHAIN_VERSION_PHASE14,
    STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23,
    STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13, STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22,
    STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21, STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17,
    STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15, STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16,
    STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24,
    STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26,
    STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25,
    STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12,
};

fn unique_temp_dir(name: &str) -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    std::env::temp_dir().join(format!("llm-provable-computer-{name}-{suffix}"))
}

#[cfg(feature = "stwo-backend")]
fn write_test_gzip_copy(source: &std::path::Path, target: &std::path::Path) {
    let bytes = std::fs::read(source).expect("read source json");
    let file = std::fs::File::create(target).expect("create gzip target");
    let mut encoder = GzBuilder::new()
        .mtime(0)
        .write(file, flate2::Compression::best());
    encoder.write_all(&bytes).expect("write gzip bytes");
    encoder.finish().expect("finish gzip copy");
}

#[cfg(feature = "stwo-backend")]
fn phase27_cli_test_guard() -> std::sync::MutexGuard<'static, ()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

fn tvm_command() -> Command {
    let binary = std::env::var_os("CARGO_BIN_EXE_tvm")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let target_dir = std::env::var_os("CARGO_TARGET_DIR")
                .map(PathBuf::from)
                .map(|path| {
                    if path.is_absolute() {
                        path
                    } else {
                        manifest_dir.join(path)
                    }
                })
                .unwrap_or_else(|| manifest_dir.join("target"));
            let profile = std::env::var("PROFILE").unwrap_or_else(|_| "debug".to_string());
            let binary_name = format!("tvm{}", std::env::consts::EXE_SUFFIX);
            let mut candidates = Vec::new();
            if let Some(target_triple) = std::env::var_os("CARGO_BUILD_TARGET")
                .or_else(|| std::env::var_os("TARGET"))
            {
                candidates.push(target_dir.join(target_triple).join(&profile).join(&binary_name));
            }
            candidates.push(target_dir.join(&profile).join(&binary_name));
            candidates.push(manifest_dir.join("target").join(&profile).join(&binary_name));
            candidates
                .into_iter()
                .find(|candidate| candidate.exists())
                .unwrap_or_else(|| {
                    panic!(
                        "could not resolve `tvm` binary; checked CARGO_BIN_EXE_tvm and fallback candidates under `{}`",
                        target_dir.display()
                    )
                })
        });
    Command::from_std(std::process::Command::new(binary))
}

#[cfg(feature = "stwo-backend")]
fn phase27_cli_demo_fixture_path() -> PathBuf {
    static FIXTURE: OnceLock<PathBuf> = OnceLock::new();
    FIXTURE
        .get_or_init(|| {
            let path = unique_temp_dir(
                "cli-stwo-chained-folded-intervalized-decoding-state-relation-fixture",
            )
            .with_extension("json");
            let mut prove = tvm_command();
            prove
                .arg("prove-stwo-chained-folded-intervalized-decoding-state-relation-demo")
                .arg("-o")
                .arg(&path)
                .assert()
                .success();
            path
        })
        .clone()
}

#[cfg(feature = "onnx-export")]
fn validate_json_against_schema(artifact: &serde_json::Value, schema_relative_path: &str) {
    let schema_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(schema_relative_path);
    let schema_bytes = std::fs::read(&schema_path).expect("schema bytes");
    let schema_json: serde_json::Value =
        serde_json::from_slice(&schema_bytes).expect("schema json");

    let compiled = JSONSchema::options()
        .with_draft(Draft::Draft202012)
        .compile(&schema_json)
        .expect("compile schema");

    let validation_summary = match compiled.validate(artifact) {
        Ok(()) => None,
        Err(errors) => Some(
            errors
                .map(|error| error.to_string())
                .collect::<Vec<_>>()
                .join("; "),
        ),
    };
    if let Some(summary) = validation_summary {
        panic!(
            "artifact failed schema validation `{}`: {}",
            schema_relative_path, summary
        );
    }
}

#[cfg(feature = "onnx-export")]
fn read_repo_file(relative_path: &str) -> Vec<u8> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(relative_path);
    std::fs::read(path).expect("repo file")
}

#[cfg(any(feature = "onnx-export", feature = "stwo-backend"))]
#[cfg_attr(
    all(feature = "stwo-backend", not(feature = "onnx-export")),
    allow(dead_code)
)]
fn blake2b_256_hex(bytes: &[u8]) -> String {
    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).expect("blake2b-256 hasher");
    hasher.update(bytes);
    hasher
        .finalize_variable(&mut output)
        .expect("blake2b-256 finalization");
    output.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(feature = "stwo-backend")]
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
struct TestEmbeddedSharedNormalizationClaimRow {
    norm_sq_memory_index: u8,
    inv_sqrt_q8_memory_index: u8,
    expected_norm_sq: i16,
    expected_inv_sqrt_q8: i16,
}

#[cfg(feature = "stwo-backend")]
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
struct TestEmbeddedSharedNormalizationProof {
    statement_version: String,
    semantic_scope: String,
    claimed_rows: Vec<TestEmbeddedSharedNormalizationClaimRow>,
    proof_envelope: Phase10SharedNormalizationLookupProofEnvelope,
}

#[cfg(feature = "stwo-backend")]
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
struct TestEmbeddedSharedActivationClaimRow {
    input_memory_index: u8,
    output_memory_index: u8,
    expected_input: i16,
    expected_output: i16,
}

#[cfg(feature = "stwo-backend")]
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
struct TestEmbeddedSharedActivationLookupProof {
    statement_version: String,
    semantic_scope: String,
    claimed_rows: Vec<TestEmbeddedSharedActivationClaimRow>,
    proof_envelope: Phase10SharedLookupProofEnvelope,
}

#[cfg(feature = "stwo-backend")]
fn phase12_artifact_commitment_from_json(artifact: &serde_json::Value) -> String {
    let layout_commitment = artifact["layout_commitment"]
        .as_str()
        .expect("layout commitment");
    let flattened_lookup_rows: Vec<i16> =
        serde_json::from_value(artifact["flattened_lookup_rows"].clone())
            .expect("flattened lookup rows");
    let normalization: TestEmbeddedSharedNormalizationProof =
        serde_json::from_value(artifact["normalization_proof_envelope"].clone())
            .expect("normalization proof envelope");
    let activation: TestEmbeddedSharedActivationLookupProof =
        serde_json::from_value(artifact["activation_proof_envelope"].clone())
            .expect("activation proof envelope");

    let flattened_json = serde_json::to_vec(&flattened_lookup_rows).expect("flattened rows json");
    let normalization_json = serde_json::to_vec(&normalization).expect("normalization json");
    let activation_json = serde_json::to_vec(&activation).expect("activation json");

    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).expect("blake2b-256 hasher");
    hasher.update(STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(&(flattened_json.len() as u64).to_le_bytes());
    hasher.update(&flattened_json);
    hasher.update(&(normalization_json.len() as u64).to_le_bytes());
    hasher.update(&normalization_json);
    hasher.update(&(activation_json.len() as u64).to_le_bytes());
    hasher.update(&activation_json);
    hasher
        .finalize_variable(&mut output)
        .expect("blake2b-256 finalization");
    output.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(feature = "stwo-backend")]
fn phase12_lookup_rows_commitment_from_json(artifact: &serde_json::Value) -> String {
    let layout_commitment = artifact["layout_commitment"]
        .as_str()
        .expect("layout commitment");
    let flattened_lookup_rows: Vec<i16> =
        serde_json::from_value(artifact["flattened_lookup_rows"].clone())
            .expect("flattened lookup rows");
    commit_phase12_shared_lookup_rows(layout_commitment, &flattened_lookup_rows)
}

#[cfg(feature = "onnx-export")]
fn json_string_at<'a>(value: &'a serde_json::Value, path: &[&str]) -> Option<&'a str> {
    let mut cursor = value;
    for key in path {
        cursor = cursor.get(*key)?;
    }
    cursor.as_str()
}

#[cfg(feature = "onnx-export")]
fn assert_research_v2_spec_commitments(
    artifact: &serde_json::Value,
    statement_spec_path: &str,
    artifact_schema_path: &str,
) {
    let expected_statement_spec_hash = blake2b_256_hex(&read_repo_file(statement_spec_path));
    let expected_fixed_point_spec_hash =
        blake2b_256_hex(&read_repo_file("spec/fixed-point-semantics-v2.json"));
    let expected_onnx_op_subset_hash =
        blake2b_256_hex(&read_repo_file("spec/onnx-op-subset-v2.json"));
    let expected_artifact_schema_hash = blake2b_256_hex(&read_repo_file(artifact_schema_path));

    assert_eq!(
        json_string_at(artifact, &["commitments", "hash_function"]),
        Some("blake2b-256")
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "statement_spec_hash"]),
        Some(expected_statement_spec_hash.as_str())
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "fixed_point_spec_hash"]),
        Some(expected_fixed_point_spec_hash.as_str())
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "onnx_op_subset_hash"]),
        Some(expected_onnx_op_subset_hash.as_str())
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "artifact_schema_hash"]),
        Some(expected_artifact_schema_hash.as_str())
    );
}

#[test]
fn cli_runs_addition_program() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .assert()
        .success()
        .stdout(predicate::str::contains("halted: true"))
        .stdout(predicate::str::contains("sp: 4"))
        .stdout(predicate::str::contains("acc: 8"));
}

#[test]
fn cli_supports_program_path_shortcut() {
    let mut command = tvm_command();
    command
        .arg("programs/addition.tvm")
        .assert()
        .success()
        .stdout(predicate::str::contains("engine: transformer"))
        .stdout(predicate::str::contains("acc: 8"));
}

#[test]
fn cli_help_describes_subcommands() {
    let mut command = tvm_command();
    command
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Run a program and print the final machine state",
        ))
        .stdout(predicate::str::contains(
            "Produce a STARK proof for a supported execution",
        ));
}

#[test]
fn cli_run_help_describes_core_flags() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Maximum number of execution steps before stopping",
        ))
        .stdout(predicate::str::contains(
            "Execution backend to use for the run",
        ))
        .stdout(predicate::str::contains(
            "Attention mode to use for memory reads",
        ));
}

#[test]
fn cli_stark_help_describes_profile_flags() {
    let mut prove_help = tvm_command();
    prove_help
        .arg("prove-stark")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("--stark-profile"))
        .stdout(predicate::str::contains("--backend"))
        .stdout(predicate::str::contains("production-v1"));

    let mut verify_help = tvm_command();
    verify_help
        .arg("verify-stark")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("--verification-profile"))
        .stdout(predicate::str::contains("--backend"))
        .stdout(predicate::str::contains("production-v1"));
}

#[test]
fn cli_supports_multi_layer_trace_output() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--layers")
        .arg("2")
        .arg("--trace")
        .assert()
        .success()
        .stdout(predicate::str::contains("layers: 2"))
        .stdout(predicate::str::contains("trace[001]"))
        .stdout(predicate::str::contains("sp=4"))
        .stdout(predicate::str::contains("instr=\"LOADI 5\""));
}

#[test]
fn cli_runs_subroutine_program() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/subroutine_addition.tvm")
        .assert()
        .success()
        .stdout(predicate::str::contains("halted: true"))
        .stdout(predicate::str::contains("sp: 8"))
        .stdout(predicate::str::contains("acc: 42"))
        .stdout(predicate::str::contains("memory: [0, 0, 0, 0, 0, 0, 0, 2]"));
}

#[test]
fn cli_supports_native_engine_selection() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--engine")
        .arg("native")
        .assert()
        .success()
        .stdout(predicate::str::contains("engine: native"))
        .stdout(predicate::str::contains("acc: 8"));
}

#[test]
fn cli_accepts_attention_mode_flag() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/soft_attention_memory.tvm")
        .arg("--attention-mode")
        .arg("hard-softmax:10")
        .assert()
        .success()
        .stdout(predicate::str::contains("attention_mode: hard-softmax:10"))
        .stdout(predicate::str::contains("acc: 4"));
}

#[test]
fn cli_can_verify_against_native_interpreter() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/fibonacci.tvm")
        .arg("--layers")
        .arg("3")
        .arg("--verify-native")
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_native: true"))
        .stdout(predicate::str::contains("verified_steps:"))
        .stdout(predicate::str::contains("acc: 21"));
}

#[test]
fn cli_can_prove_and_verify_stark_execution() {
    let proof_path = unique_temp_dir("cli-stark-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: vanilla"))
        .stdout(predicate::str::contains(
            "proof_backend_version: vanilla-v1",
        ))
        .stdout(predicate::str::contains("statement_version: statement-v1"))
        .stdout(predicate::str::contains(
            "semantic_scope: native_isa_execution_with_transformer_native_equivalence_check",
        ))
        .stdout(predicate::str::contains("commitment_program_hash:"))
        .stdout(predicate::str::contains("commitment_stark_options_hash:"))
        .stdout(predicate::str::contains("equivalence_checked_steps:"))
        .stdout(predicate::str::contains("proof_bytes:"))
        .stdout(predicate::str::contains("acc: 8"));

    assert!(proof_path.exists());

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&proof_path)
        .arg("--reexecute")
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: vanilla"))
        .stdout(predicate::str::contains(
            "proof_backend_version: vanilla-v1",
        ))
        .stdout(predicate::str::contains("statement_version: statement-v1"))
        .stdout(predicate::str::contains("commitment_program_hash:"))
        .stdout(predicate::str::contains("reexecuted_equivalence: true"))
        .stdout(predicate::str::contains("equivalence_checked_steps:"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains("acc: 8"))
        .stdout(predicate::str::contains("instructions: 3"));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(not(feature = "stwo-backend"))]
fn cli_prove_stark_requires_stwo_feature_flag() {
    let proof_path = unique_temp_dir("cli-stark-proof-stwo").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "S-two backend requires building with `--features stwo-backend`",
        ));
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_phase5_shipped_arithmetic_fixtures() {
    for (program, stem, expected_acc) in [
        ("programs/addition.tvm", "addition", "8"),
        ("programs/counter.tvm", "counter", "5"),
        ("programs/memory_roundtrip.tvm", "memory-roundtrip", "42"),
        ("programs/multiply.tvm", "multiply", "42"),
        ("programs/dot_product.tvm", "dot", "70"),
        ("programs/fibonacci.tvm", "fibonacci", "21"),
        ("programs/gemma_block_v1.tvm", "gemma-block-v1", "16"),
        ("programs/gemma_block_v2.tvm", "gemma-block-v2", "16"),
        ("programs/gemma_block_v3.tvm", "gemma-block-v3", "16"),
        ("programs/gemma_block_v4.tvm", "gemma-block-v4", "16"),
        ("programs/matmul_2x2.tvm", "matmul-2x2", "134"),
        ("programs/single_neuron.tvm", "single-neuron", "1"),
    ] {
        let proof_path =
            unique_temp_dir(&format!("cli-stark-proof-stwo-phase5-{stem}")).with_extension("json");

        let mut prove = tvm_command();
        prove
            .arg("prove-stark")
            .arg(program)
            .arg("-o")
            .arg(&proof_path)
            .arg("--backend")
            .arg("stwo")
            .arg("--max-steps")
            .arg("256")
            .assert()
            .success()
            .stdout(predicate::str::contains("proof_backend: stwo"))
            .stdout(predicate::str::contains(format!("acc: {expected_acc}")));

        let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
        assert!(proof_json.contains("\"proof_backend\": \"stwo\""));
        assert!(proof_json.contains("stwo-phase10-gemma-block-v4"));
        if program == "programs/gemma_block_v1.tvm" {
            assert!(proof_json.contains("\"normalization_companion\""));
            assert!(proof_json.contains("stwo-normalization-demo-v1"));
            assert!(
                proof_json.contains("stwo_gemma_block_v1_execution_plus_normalization_companion")
            );
        }
        if program == "programs/gemma_block_v2.tvm"
            || program == "programs/gemma_block_v3.tvm"
            || program == "programs/gemma_block_v4.tvm"
        {
            let proof_value: serde_json::Value =
                serde_json::from_str(&proof_json).expect("proof value");
            let proof_bytes = proof_value["proof"]
                .as_array()
                .expect("proof bytes")
                .iter()
                .map(|v| v.as_u64().expect("byte") as u8)
                .collect::<Vec<_>>();
            let payload: serde_json::Value =
                serde_json::from_slice(&proof_bytes).expect("payload json");
            assert!(!proof_json.contains("\"stwo_auxiliary\""));
            if program == "programs/gemma_block_v2.tvm" || program == "programs/gemma_block_v3.tvm"
            {
                assert_eq!(
                    payload["embedded_normalization"]["statement_version"],
                    "stwo-normalization-demo-v1"
                );
                let expected_norm_scope = if program == "programs/gemma_block_v3.tvm" {
                    "stwo_gemma_block_v3_execution_with_embedded_normalization"
                } else {
                    "stwo_gemma_block_v2_execution_with_embedded_normalization"
                };
                assert_eq!(
                    payload["embedded_normalization"]["semantic_scope"],
                    expected_norm_scope
                );
            }
            if program == "programs/gemma_block_v3.tvm" {
                assert_eq!(
                    payload["embedded_activation_lookup"]["statement_version"],
                    "stwo-binary-step-lookup-demo-v1"
                );
                assert_eq!(
                    payload["embedded_activation_lookup"]["semantic_scope"],
                    "stwo_gemma_block_v3_execution_with_embedded_binary_step_lookup"
                );
            } else if program == "programs/gemma_block_v4.tvm" {
                assert_eq!(
                    payload["embedded_shared_normalization"]["statement_version"],
                    "stwo-shared-normalization-lookup-v1"
                );
                assert_eq!(
                    payload["embedded_shared_normalization"]["semantic_scope"],
                    "stwo_gemma_block_v4_execution_with_shared_normalization_lookup"
                );
                assert_eq!(
                    payload["embedded_shared_activation_lookup"]["statement_version"],
                    "stwo-shared-binary-step-lookup-v1"
                );
                assert_eq!(
                    payload["embedded_shared_activation_lookup"]["semantic_scope"],
                    "stwo_gemma_block_v4_execution_with_shared_binary_step_lookup"
                );
                assert_eq!(
                    payload["embedded_shared_normalization"]["claimed_rows"]
                        .as_array()
                        .expect("shared normalization rows")
                        .len(),
                    2
                );
                assert_eq!(
                    payload["embedded_shared_activation_lookup"]["claimed_rows"]
                        .as_array()
                        .expect("shared activation rows")
                        .len(),
                    2
                );
            }
        }

        let mut verify = tvm_command();
        verify
            .arg("verify-stark")
            .arg(&proof_path)
            .arg("--reexecute")
            .assert()
            .success()
            .stdout(predicate::str::contains("proof_backend: stwo"))
            .stdout(predicate::str::contains(
                "proof_backend_version: stwo-phase10-gemma-block-v4",
            ))
            .stdout(predicate::str::contains("verified_stark: true"))
            .stdout(predicate::str::contains("reexecuted_equivalence: true"))
            .stdout(predicate::str::contains(format!("acc: {expected_acc}")));

        let _ = std::fs::remove_file(proof_path);
    }
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_gemma_block_normalization_companion() {
    let proof_path = unique_temp_dir("cli-stwo-gemma-block-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-gemma-block-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/gemma_block_v1.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&proof_path).expect("read proof")).expect("json");
    proof_json["stwo_auxiliary"]["normalization_companion"]["expected_inv_sqrt_q8"] =
        serde_json::json!(65);
    std::fs::write(
        &invalid_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&invalid_path)
        .arg("--reexecute")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "gemma_block_v1 normalization companion does not match claimed final state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_gemma_block_v2_embedded_normalization() {
    let proof_path = unique_temp_dir("cli-stwo-gemma-block-v2-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-gemma-block-v2-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/gemma_block_v2.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&proof_path).expect("read proof")).expect("json");
    let proof_bytes = proof_json["proof"]
        .as_array()
        .expect("proof bytes")
        .iter()
        .map(|v| v.as_u64().expect("byte") as u8)
        .collect::<Vec<_>>();
    let mut payload: serde_json::Value = serde_json::from_slice(&proof_bytes).expect("payload");
    payload["embedded_normalization"]["expected_inv_sqrt_q8"] = serde_json::json!(65);
    proof_json["proof"] = serde_json::Value::Array(
        serde_json::to_vec(&payload)
            .expect("encode payload")
            .into_iter()
            .map(serde_json::Value::from)
            .collect(),
    );
    std::fs::write(
        &invalid_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&invalid_path)
        .arg("--reexecute")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "gemma_block_v2/v3 embedded normalization does not match claimed final state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_gemma_block_v3_embedded_activation() {
    let proof_path = unique_temp_dir("cli-stwo-gemma-block-v3-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-gemma-block-v3-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/gemma_block_v3.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&proof_path).expect("read proof")).expect("json");
    let proof_bytes = proof_json["proof"]
        .as_array()
        .expect("proof bytes")
        .iter()
        .map(|v| v.as_u64().expect("byte") as u8)
        .collect::<Vec<_>>();
    let mut payload: serde_json::Value = serde_json::from_slice(&proof_bytes).expect("payload");
    payload["embedded_activation_lookup"]["expected_output"] = serde_json::json!(0);
    proof_json["proof"] = serde_json::Value::Array(
        serde_json::to_vec(&payload)
            .expect("encode payload")
            .into_iter()
            .map(serde_json::Value::from)
            .collect(),
    );
    std::fs::write(
        &invalid_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&invalid_path)
        .arg("--reexecute")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "gemma_block_v3 embedded activation does not match claimed final state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_gemma_block_v4_shared_normalization() {
    let proof_path = unique_temp_dir("cli-stwo-gemma-block-v4-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-gemma-block-v4-proof-tampered-norm").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/gemma_block_v4.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&proof_path).expect("read proof")).expect("json");
    let proof_bytes = proof_json["proof"]
        .as_array()
        .expect("proof bytes")
        .iter()
        .map(|v| v.as_u64().expect("byte") as u8)
        .collect::<Vec<_>>();
    let mut payload: serde_json::Value = serde_json::from_slice(&proof_bytes).expect("payload");
    payload["embedded_shared_normalization"]["claimed_rows"][1]["expected_inv_sqrt_q8"] =
        serde_json::json!(65);
    proof_json["proof"] = serde_json::Value::Array(
        serde_json::to_vec(&payload)
            .expect("encode payload")
            .into_iter()
            .map(serde_json::Value::from)
            .collect(),
    );
    std::fs::write(
        &invalid_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&invalid_path)
        .arg("--reexecute")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "gemma_block_v4 shared normalization embedded claimed rows do not match the canonical final-state rows",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_gemma_block_v4_shared_activation() {
    let proof_path = unique_temp_dir("cli-stwo-gemma-block-v4-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-gemma-block-v4-proof-tampered-act").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/gemma_block_v4.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&proof_path).expect("read proof")).expect("json");
    let proof_bytes = proof_json["proof"]
        .as_array()
        .expect("proof bytes")
        .iter()
        .map(|v| v.as_u64().expect("byte") as u8)
        .collect::<Vec<_>>();
    let mut payload: serde_json::Value = serde_json::from_slice(&proof_bytes).expect("payload");
    payload["embedded_shared_activation_lookup"]["claimed_rows"][1]["expected_output"] =
        serde_json::json!(0);
    proof_json["proof"] = serde_json::Value::Array(
        serde_json::to_vec(&payload)
            .expect("encode payload")
            .into_iter()
            .map(serde_json::Value::from)
            .collect(),
    );
    std::fs::write(
        &invalid_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&invalid_path)
        .arg("--reexecute")
        .assert()
        .failure()
        .stderr(
            predicate::str::contains(
                "gemma_block_v4 shared activation embedded claimed rows do not match the canonical final-state rows",
            )
            .or(predicate::str::contains(
                "gemma_block_v4 shared activation does not match claimed final state",
            )),
        );

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_mismatched_stwo_backend_version_for_program_family() {
    let proof_path = unique_temp_dir("cli-stwo-gemma-block-v4-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-gemma-block-v4-proof-bad-version").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/gemma_block_v4.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&proof_path).expect("read proof")).expect("json");
    proof_json["proof_backend_version"] =
        serde_json::Value::String("stwo-phase11-decoding-step-v1".to_string());
    std::fs::write(
        &invalid_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&invalid_path)
        .arg("--reexecute")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "does not match expected `stwo-phase10-gemma-block-v4`",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prove_stark_rejects_program_outside_stwo_phase2_subset() {
    let proof_path = unique_temp_dir("cli-stark-proof-stwo-subset").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/subroutine_addition.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "outside the current S-two Phase 2 arithmetic subset",
        ));
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prove_stark_rejects_phase5_programs_outside_shipped_fixtures() {
    let temp_dir = unique_temp_dir("cli-stark-proof-stwo-phase5-custom-subset");
    let program_path = temp_dir.with_extension("tvm");
    let proof_path = temp_dir.with_extension("json");
    std::fs::write(&program_path, ".memory 4\n\nLOADI 9\nHALT\n").expect("write program");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg(&program_path)
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "currently proves only the shipped arithmetic fixtures",
        ));

    let _ = std::fs::remove_file(program_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_lookup_demo() {
    let proof_path = unique_temp_dir("cli-stwo-lookup-demo-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-lookup-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(
            "proof_backend_version: stwo-phase3-binary-step-lookup-demo-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_binary_step_activation_lookup_demo_with_canonical_table",
        ));

    let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
    assert!(proof_json.contains("\"proof_backend\": \"stwo\""));
    assert!(proof_json.contains("stwo-phase3-binary-step-lookup-demo-v1"));

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-lookup-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "statement_version: stwo-binary-step-lookup-demo-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_binary_step_activation_lookup_demo_with_canonical_table",
        ));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_normalization_demo() {
    let proof_path = unique_temp_dir("cli-stwo-normalization-demo-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-normalization-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(
            "proof_backend_version: stwo-phase5-normalization-demo-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_normalization_lookup_demo_with_canonical_table",
        ));

    let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
    assert!(proof_json.contains("\"proof_backend\": \"stwo\""));
    assert!(proof_json.contains("stwo-phase5-normalization-demo-v1"));

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-normalization-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "statement_version: stwo-normalization-demo-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_normalization_lookup_demo_with_canonical_table",
        ));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_shared_lookup_demo() {
    let proof_path = unique_temp_dir("cli-stwo-shared-lookup-demo-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-shared-lookup-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(
            "proof_backend_version: stwo-phase10-shared-binary-step-lookup-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_shared_binary_step_activation_lookup_with_canonical_table",
        ))
        .stdout(predicate::str::contains("claimed_rows: 2"));

    let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
    assert!(proof_json.contains("\"proof_backend\": \"stwo\""));
    assert!(proof_json.contains("stwo-phase10-shared-binary-step-lookup-v1"));

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-shared-lookup-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "statement_version: stwo-shared-binary-step-lookup-v1",
        ));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_shared_normalization_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-shared-normalization-demo-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-shared-normalization-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(
            "proof_backend_version: stwo-phase10-shared-normalization-lookup-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_shared_normalization_lookup_with_canonical_table",
        ))
        .stdout(predicate::str::contains("claimed_rows: 2"));

    let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
    assert!(proof_json.contains("\"proof_backend\": \"stwo\""));
    assert!(proof_json.contains("stwo-phase10-shared-normalization-lookup-v1"));

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-shared-normalization-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "statement_version: stwo-shared-normalization-lookup-v1",
        ));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_demo() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-demo-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(
            "chain_version: stwo-phase11-decoding-chain-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_execution_proof_carrying_decoding_chain",
        ))
        .stdout(predicate::str::contains("total_steps: 3"));

    let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
    assert!(proof_json.contains("\"proof_backend\": \"stwo\""));
    assert!(proof_json.contains("stwo-phase11-decoding-chain-v1"));
    assert!(proof_json.contains("stwo-phase11-decoding-step-v1"));

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "expected_chain_version: stwo-phase11-decoding-chain-v1",
        ));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_demo_rejects_tampered_kv_link() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-demo-proof-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-demo-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["steps"][1]["from_state"]["kv_cache_commitment"] =
        serde_json::Value::String("deadbeef".repeat(8));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "recorded from_state does not match the proof's initial state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_family_demo() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-family-demo-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_execution_parameterized_proof_carrying_decoding_chain",
        ))
        .stdout(predicate::str::contains("rolling_kv_pairs: 4"))
        .stdout(predicate::str::contains("pair_width: 4"))
        .stdout(predicate::str::contains("start_history_length: 4"))
        .stdout(predicate::str::contains("final_history_length: 7"))
        .stdout(predicate::str::contains("total_steps: 3"));

    let proof_json = std::fs::read_to_string(&proof_path).expect("proof json");
    let proof_json: serde_json::Value = serde_json::from_str(&proof_json).expect("proof json");
    assert_eq!(
        proof_json
            .get("proof_backend")
            .and_then(serde_json::Value::as_str),
        Some("stwo")
    );
    assert_eq!(
        proof_json
            .get("chain_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_CHAIN_VERSION_PHASE12)
    );
    assert_eq!(
        proof_json
            .get("proof_backend_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_BACKEND_VERSION_PHASE12)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-family-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains("rolling_kv_pairs: 4"))
        .stdout(predicate::str::contains("pair_width: 4"))
        .stdout(predicate::str::contains("start_history_length: 4"))
        .stdout(predicate::str::contains("final_history_length: 7"));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_family_demo_rejects_tampered_persistent_link() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-proof-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["steps"][1]["from_state"]["persistent_state_commitment"] =
        serde_json::Value::String("deadbeef".repeat(8));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-family-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "recorded from_state does not match the proof's initial state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_family_demo_rejects_tampered_history_link() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-history-proof").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-history-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["steps"][1]["from_state"]["kv_history_commitment"] =
        serde_json::Value::String("beadfeed".repeat(8));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-family-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "recorded from_state does not match the proof's initial state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_family_demo_rejects_missing_shared_lookup_artifact() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-artifact-proof").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-artifact-tampered").with_extension("json");
    let wrong_ref_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-artifact-wrong-ref").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["shared_lookup_artifacts"] = serde_json::Value::Array(Vec::new());
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-family-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "must contain at least one shared lookup artifact",
        ));

    let mut wrong_ref_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let artifact_commitments: Vec<String> = wrong_ref_json["shared_lookup_artifacts"]
        .as_array()
        .expect("artifact array")
        .iter()
        .filter_map(|artifact| artifact["artifact_commitment"].as_str().map(str::to_string))
        .collect();
    let original_commitment = wrong_ref_json["steps"][0]["shared_lookup_artifact_commitment"]
        .as_str()
        .expect("original shared lookup artifact commitment")
        .to_string();
    let wrong_commitment =
        if artifact_commitments.len() > 1 && artifact_commitments[1] != original_commitment {
            artifact_commitments[1].clone()
        } else {
            let artifact_array = wrong_ref_json["shared_lookup_artifacts"]
                .as_array_mut()
                .expect("artifact array");
            let mut synthetic = artifact_array[0].clone();
            let normalization_rows = vec![(4u16, 128u16), (16u16, 64u16)];
            let activation_rows = vec![
                Phase3LookupTableRow {
                    input: 0,
                    output: 1,
                },
                Phase3LookupTableRow {
                    input: 1,
                    output: 1,
                },
            ];
            let normalization_envelope =
                prove_phase10_shared_normalization_lookup_envelope(&normalization_rows)
                    .expect("synthetic normalization envelope");
            let activation_envelope =
                prove_phase10_shared_binary_step_lookup_envelope(&activation_rows)
                    .expect("synthetic activation envelope");
            synthetic["flattened_lookup_rows"] = serde_json::json!([4, 128, 0, 1, 16, 64, 1, 1]);
            synthetic["normalization_proof_envelope"]["claimed_rows"][0]["expected_norm_sq"] =
                serde_json::Value::from(4);
            synthetic["normalization_proof_envelope"]["claimed_rows"][0]["expected_inv_sqrt_q8"] =
                serde_json::Value::from(128);
            synthetic["normalization_proof_envelope"]["claimed_rows"][1]["expected_norm_sq"] =
                serde_json::Value::from(16);
            synthetic["normalization_proof_envelope"]["claimed_rows"][1]["expected_inv_sqrt_q8"] =
                serde_json::Value::from(64);
            synthetic["normalization_proof_envelope"]["proof_envelope"] =
                serde_json::to_value(normalization_envelope).expect("serialize normalization");
            synthetic["activation_proof_envelope"]["claimed_rows"][0]["expected_input"] =
                serde_json::Value::from(0);
            synthetic["activation_proof_envelope"]["claimed_rows"][0]["expected_output"] =
                serde_json::Value::from(1);
            synthetic["activation_proof_envelope"]["claimed_rows"][1]["expected_input"] =
                serde_json::Value::from(1);
            synthetic["activation_proof_envelope"]["claimed_rows"][1]["expected_output"] =
                serde_json::Value::from(1);
            synthetic["activation_proof_envelope"]["proof_envelope"] =
                serde_json::to_value(activation_envelope).expect("serialize activation");
            let lookup_rows_commitment = phase12_lookup_rows_commitment_from_json(&synthetic);
            synthetic["lookup_rows_commitment"] = serde_json::Value::String(lookup_rows_commitment);
            let commitment = phase12_artifact_commitment_from_json(&synthetic);
            synthetic["artifact_commitment"] = serde_json::Value::String(commitment.clone());
            artifact_array.push(synthetic);
            commitment
        };
    wrong_ref_json["steps"][0]["shared_lookup_artifact_commitment"] =
        serde_json::Value::String(wrong_commitment);
    std::fs::write(
        &wrong_ref_path,
        serde_json::to_vec(&wrong_ref_json).expect("serialize"),
    )
    .expect("write");

    let mut verify_wrong_ref = tvm_command();
    verify_wrong_ref
        .arg("verify-stwo-decoding-family-demo")
        .arg(&wrong_ref_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match the proof payload"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
    let _ = std::fs::remove_file(wrong_ref_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_family_demo_rejects_tampered_layout() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-layout-proof").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-layout-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["layout"]["rolling_kv_pairs"] = serde_json::Value::from(3u64);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-family-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(
            predicate::str::contains(
                "is not a decoding_step_v2-family proof for the manifest layout",
            )
            .or(predicate::str::contains(
                "shared lookup artifact layout commitment",
            )),
        );

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_layout_matrix_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-layout-matrix-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-layout-matrix-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "matrix_version: {STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13}",
        )))
        .stdout(predicate::str::contains("total_layouts: 3"))
        .stdout(predicate::str::contains("total_steps: 9"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("matrix_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13)
    );
    assert_eq!(
        proof_json
            .get("total_layouts")
            .and_then(serde_json::Value::as_u64),
        Some(3)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-layout-matrix-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_matrix_version: {STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_layout_matrix_demo_rejects_tampered_totals() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-layout-matrix-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-layout-matrix-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-layout-matrix-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["total_layouts"] = serde_json::Value::from(99u64);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-layout-matrix-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "total_layouts=99 does not match chains.len()=3",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_chunked_history_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-chunked-history-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-chunked-history-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE14}",
        )))
        .stdout(predicate::str::contains("history_chunk_pairs: 2"))
        .stdout(predicate::str::contains("start_sealed_chunks: 2"))
        .stdout(predicate::str::contains("final_history_length: 7"))
        .stdout(predicate::str::contains("final_open_chunk_pairs: 1"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("chain_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_CHAIN_VERSION_PHASE14)
    );
    assert_eq!(
        proof_json
            .get("history_chunk_pairs")
            .and_then(serde_json::Value::as_u64),
        Some(2)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-chunked-history-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_chain_version: {STWO_DECODING_CHAIN_VERSION_PHASE14}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains("history_chunk_pairs: 2"))
        .stdout(predicate::str::contains("final_sealed_chunks: 3"));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_chunked_history_demo_rejects_tampered_chunk_state() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-chunked-history-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-chunked-history-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-chunked-history-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["steps"][1]["from_state"]["kv_history_open_chunk_pairs"] =
        serde_json::Value::from(0u64);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-chunked-history-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "recorded from_state does not match the proof's initial state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_history_segments_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-history-segments-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-history-segments-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "bundle_version: {STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15}",
        )))
        .stdout(predicate::str::contains("total_segments: 2"))
        .stdout(predicate::str::contains("max_segment_steps: 2"))
        .stdout(predicate::str::contains("final_history_length: 7"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("bundle_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15)
    );
    assert_eq!(
        proof_json
            .get("total_segments")
            .and_then(serde_json::Value::as_u64),
        Some(2)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-history-segments-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_bundle_version: {STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains("last_segment_start_step: 2"));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_history_segments_demo_rejects_tampered_segment_start() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-history-segments-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-history-segments-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-history-segments-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["segments"][1]["global_start_step_index"] = serde_json::Value::from(99u64);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-history-segments-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "starts at global step 99 instead of 2",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_history_rollup_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-history-rollup-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-history-rollup-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "rollup_version: {STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16}",
        )))
        .stdout(predicate::str::contains("total_rollups: 2"))
        .stdout(predicate::str::contains("total_segments: 3"))
        .stdout(predicate::str::contains("final_history_length: 7"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("rollup_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16)
    );
    assert_eq!(
        proof_json
            .get("total_rollups")
            .and_then(serde_json::Value::as_u64),
        Some(2)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-history-rollup-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_rollup_version: {STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains("last_rollup_start_step: 2"));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_history_rollup_demo_rejects_tampered_rollup_start() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-history-rollup-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-history-rollup-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-history-rollup-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let rollup = proof_json
        .get_mut("rollups")
        .and_then(serde_json::Value::as_array_mut)
        .and_then(|rollups| rollups.get_mut(1))
        .unwrap_or_else(|| {
            panic!(
                "phase16 demo should produce at least two rollups in {}",
                proof_path.display()
            )
        });
    rollup["global_start_step_index"] = serde_json::Value::from(99u64);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-history-rollup-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "starts at global step 99 instead of 2",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_history_rollup_matrix_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-history-rollup-matrix-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-history-rollup-matrix-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "matrix_version: {STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17}",
        )))
        .stdout(predicate::str::contains("total_layouts: 3"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("matrix_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-history-rollup-matrix-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_matrix_version: {STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_history_rollup_matrix_demo_rejects_tampered_total_rollups() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-history-rollup-matrix-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-history-rollup-matrix-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-history-rollup-matrix-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["total_rollups"] = serde_json::Value::from(99u64);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-history-rollup-matrix-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "total_rollups=99 does not match derived total_rollups",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_matrix_accumulator_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-matrix-accumulator-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-matrix-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "accumulator_version: {STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21}",
        )))
        .stdout(predicate::str::contains("total_matrices:"))
        .stdout(predicate::str::contains("total_steps:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("accumulator_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-matrix-accumulator-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_accumulator_version: {STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_matrix_accumulator_demo_rejects_tampered_accumulator_commitment() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-matrix-accumulator-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-matrix-accumulator-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-matrix-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["accumulator_commitment"] = serde_json::Value::from("tampered");
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-matrix-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "accumulator_commitment does not match the computed accumulator commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_lookup_accumulator_demo() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-lookup-accumulator-proof").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-lookup-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "accumulator_version: {STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22}",
        )))
        .stdout(predicate::str::contains("lookup_delta_entries:"))
        .stdout(predicate::str::contains("max_lookup_frontier_entries:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("accumulator_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-lookup-accumulator-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_accumulator_version: {STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_lookup_accumulator_demo_rejects_tampered_lookup_delta_entries() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-lookup-accumulator-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-lookup-accumulator-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-lookup-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original_lookup_delta_entries = proof_json["lookup_delta_entries"]
        .as_u64()
        .expect("lookup_delta_entries");
    proof_json["lookup_delta_entries"] =
        serde_json::Value::from(original_lookup_delta_entries.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-lookup-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("lookup_delta_entries="))
        .stderr(predicate::str::contains(
            "does not match derived lookup_delta_entries",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_lookup_accumulator_demo_rejects_tampered_max_lookup_frontier_entries() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-lookup-accumulator-frontier").with_extension("json");
    let tampered_path = unique_temp_dir("cli-stwo-decoding-lookup-accumulator-frontier-tampered")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-lookup-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original_max_lookup_frontier_entries = proof_json["max_lookup_frontier_entries"]
        .as_u64()
        .expect("max_lookup_frontier_entries");
    proof_json["max_lookup_frontier_entries"] =
        serde_json::Value::from(original_max_lookup_frontier_entries.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-lookup-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("max_lookup_frontier_entries="))
        .stderr(predicate::str::contains(
            "does not match derived max_lookup_frontier_entries",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_cross_step_lookup_accumulator_demo() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-cross-step-lookup-accumulator-proof")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-cross-step-lookup-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "accumulator_version: {STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23}",
        )))
        .stdout(predicate::str::contains("member_count:"))
        .stdout(predicate::str::contains("lookup_delta_entries:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("accumulator_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-cross-step-lookup-accumulator-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_accumulator_version: {STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_cross_step_lookup_accumulator_demo_rejects_tampered_lookup_template() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-cross-step-lookup-accumulator-tamper")
        .with_extension("json");
    let tampered_path = unique_temp_dir("cli-stwo-decoding-cross-step-lookup-accumulator-tampered")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-cross-step-lookup-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original = proof_json["lookup_template_commitment"]
        .as_str()
        .expect("lookup_template_commitment")
        .to_string();
    let mut tampered = original.clone();
    let replacement = if &original[..2] == "00" { "ff" } else { "00" };
    tampered.replace_range(0..2, replacement);
    proof_json["lookup_template_commitment"] = serde_json::Value::String(tampered);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-cross-step-lookup-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "lookup_template_commitment does not match the computed member lookup template commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_cross_step_lookup_accumulator_demo_rejects_tampered_lookup_delta_entries(
) {
    let proof_path = unique_temp_dir("cli-stwo-decoding-cross-step-lookup-accumulator-delta")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-cross-step-lookup-accumulator-delta-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-cross-step-lookup-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let value = proof_json["lookup_delta_entries"]
        .as_u64()
        .expect("lookup_delta_entries");
    proof_json["lookup_delta_entries"] = serde_json::Value::from(value.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-cross-step-lookup-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("lookup_delta_entries="))
        .stderr(predicate::str::contains(
            "does not match derived lookup_delta_entries",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_decoding_state_relation_accumulator_demo() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-state-relation-accumulator-proof")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-state-relation-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "accumulator_version: {STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24}",
        )))
        .stdout(predicate::str::contains("member_count:"))
        .stdout(predicate::str::contains("lookup_delta_entries:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("accumulator_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-state-relation-accumulator-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_accumulator_version: {STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_state_relation_accumulator_demo_rejects_tampered_relation_template() {
    let proof_path = unique_temp_dir("cli-stwo-decoding-state-relation-accumulator-template")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-state-relation-accumulator-template-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-state-relation-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original = proof_json["relation_template_commitment"]
        .as_str()
        .expect("relation_template_commitment")
        .to_string();
    assert!(
        original.len() >= 2,
        "relation_template_commitment must be at least one byte of hex"
    );
    let mut tampered = original.clone();
    let replacement = if original.starts_with("00") {
        "ff"
    } else {
        "00"
    };
    tampered.replace_range(0..2, replacement);
    proof_json["relation_template_commitment"] = serde_json::Value::String(tampered);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-state-relation-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "relation_template_commitment does not match the computed member relation template commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_state_relation_accumulator_demo_rejects_tampered_lookup_delta_entries()
{
    let proof_path = unique_temp_dir("cli-stwo-decoding-state-relation-accumulator-delta")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-decoding-state-relation-accumulator-delta-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-state-relation-accumulator-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let value = proof_json["lookup_delta_entries"]
        .as_u64()
        .expect("lookup_delta_entries");
    proof_json["lookup_delta_entries"] = serde_json::Value::from(value.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-state-relation-accumulator-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("lookup_delta_entries="))
        .stderr(predicate::str::contains(
            "does not match derived lookup_delta_entries",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_intervalized_decoding_state_relation_demo() {
    let proof_path = unique_temp_dir("cli-stwo-intervalized-decoding-state-relation-proof")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "artifact_version: {STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25}",
        )))
        .stdout(predicate::str::contains("member_count:"))
        .stdout(predicate::str::contains("lookup_delta_entries:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("artifact_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-intervalized-decoding-state-relation-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_artifact_version: {STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_intervalized_decoding_state_relation_demo_rejects_tampered_interval_template() {
    let proof_path = unique_temp_dir("cli-stwo-intervalized-decoding-state-relation-template")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-intervalized-decoding-state-relation-template-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original = proof_json["interval_template_commitment"]
        .as_str()
        .expect("interval_template_commitment")
        .to_string();
    let mut tampered = original.clone();
    let replacement = if original.starts_with("00") {
        "ff"
    } else {
        "00"
    };
    tampered.replace_range(0..2, replacement);
    proof_json["interval_template_commitment"] = serde_json::Value::String(tampered);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "interval_template_commitment does not match the computed interval template commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_intervalized_decoding_state_relation_demo_rejects_tampered_lookup_delta_entries()
{
    let proof_path = unique_temp_dir("cli-stwo-intervalized-decoding-state-relation-delta")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-intervalized-decoding-state-relation-delta-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let value = proof_json["lookup_delta_entries"]
        .as_u64()
        .expect("lookup_delta_entries");
    proof_json["lookup_delta_entries"] = serde_json::Value::from(value.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("lookup_delta_entries="))
        .stderr(predicate::str::contains(
            "does not match derived lookup_delta_entries",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_folded_intervalized_decoding_state_relation_demo() {
    let proof_path = unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-proof")
        .with_extension("json");
    let gzip_path = proof_path.with_extension("json.gz");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "artifact_version: {STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26}",
        )))
        .stdout(predicate::str::contains("bounded_fold_arity:"))
        .stdout(predicate::str::contains("lookup_delta_entries:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("artifact_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_artifact_version: {STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    write_test_gzip_copy(&proof_path, &gzip_path);

    let mut verify_gzip = tvm_command();
    verify_gzip
        .arg("verify-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg(&gzip_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_artifact_version: {STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26}",
        )));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(gzip_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_intervalized_decoding_state_relation_demo_rejects_corrupt_gzip() {
    let proof_path = unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-gzip")
        .with_extension("json");
    let gzip_path = proof_path.with_extension("json.gz");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    write_test_gzip_copy(&proof_path, &gzip_path);
    let mut bytes = std::fs::read(&gzip_path).expect("read gzip");
    bytes.truncate(bytes.len().saturating_sub(8));
    std::fs::write(&gzip_path, bytes).expect("write corrupt gzip");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg(&gzip_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "could not be decompressed as gzip",
        ))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(gzip_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_intervalized_decoding_state_relation_demo_rejects_tampered_fold_template()
{
    let proof_path =
        unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-template")
            .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-template-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original = proof_json["fold_template_commitment"]
        .as_str()
        .expect("fold_template_commitment")
        .to_string();
    let mut tampered = original.clone();
    let replacement = if original.starts_with("00") {
        "ff"
    } else {
        "00"
    };
    tampered.replace_range(0..2, replacement);
    proof_json["fold_template_commitment"] = serde_json::Value::String(tampered);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "fold_template_commitment does not match the computed fold template commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_intervalized_decoding_state_relation_demo_rejects_tampered_lookup_delta_entries(
) {
    let proof_path = unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-delta")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-delta-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let value = proof_json["lookup_delta_entries"]
        .as_u64()
        .expect("lookup_delta_entries");
    proof_json["lookup_delta_entries"] = serde_json::Value::from(value.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("lookup_delta_entries="))
        .stderr(predicate::str::contains(
            "does not match derived lookup_delta_entries",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_intervalized_decoding_state_relation_demo_rejects_tampered_member_continuity(
) {
    let proof_path = unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-order")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-folded-intervalized-decoding-state-relation-order-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let members = proof_json["members"].as_array_mut().expect("members array");
    assert!(
        members.len() >= 2,
        "phase26 demo must emit at least two members"
    );
    members.swap(0, 1);
    let summaries = proof_json["member_summaries"]
        .as_array_mut()
        .expect("member_summaries array");
    summaries.swap(0, 1);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "does not preserve the carried-state commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prove_and_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo() {
    let _guard = phase27_cli_test_guard();
    let proof_path =
        unique_temp_dir("cli-stwo-chained-folded-intervalized-decoding-state-relation-proof")
            .with_extension("json");
    let gzip_path = proof_path.with_extension("json.gz");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "artifact_version: {STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27}",
        )))
        .stdout(predicate::str::contains("bounded_chain_arity:"))
        .stdout(predicate::str::contains("total_phase25_members:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("artifact_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_artifact_version: {STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    write_test_gzip_copy(&proof_path, &gzip_path);

    let mut verify_gzip = tvm_command();
    verify_gzip
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&gzip_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(gzip_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_corrupt_gzip() {
    let _guard = phase27_cli_test_guard();
    let proof_path =
        unique_temp_dir("cli-stwo-chained-folded-intervalized-decoding-state-relation-gzip")
            .with_extension("json");
    let gzip_path = proof_path.with_extension("json.gz");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    write_test_gzip_copy(&proof_path, &gzip_path);
    let mut bytes = std::fs::read(&gzip_path).expect("read gzip");
    bytes.truncate(bytes.len().saturating_sub(8));
    std::fs::write(&gzip_path, bytes).expect("write corrupt gzip");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&gzip_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "could not be decompressed as gzip",
        ))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(gzip_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_chain_template(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path =
        unique_temp_dir("cli-stwo-chained-folded-intervalized-decoding-state-relation-template")
            .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-template-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let original = proof_json["chain_template_commitment"]
        .as_str()
        .expect("chain_template_commitment")
        .to_string();
    let mut tampered = original.clone();
    let replacement = if original.starts_with("00") {
        "ff"
    } else {
        "00"
    };
    tampered.replace_range(0..2, replacement);
    proof_json["chain_template_commitment"] = serde_json::Value::String(tampered);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "chain_template_commitment does not match the computed chain template commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_total_phase25_members(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-total-phase25",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-total-phase25-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let value = proof_json["total_phase25_members"]
        .as_u64()
        .expect("total_phase25_members");
    proof_json["total_phase25_members"] = serde_json::Value::from(value.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("total_phase25_members="))
        .stderr(predicate::str::contains(
            "does not match derived total_phase25_members",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_semantic_scope_drift(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path =
        unique_temp_dir("cli-stwo-chained-folded-intervalized-decoding-state-relation-scope")
            .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-scope-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["semantic_scope"] =
        serde_json::Value::String("forged-phase27-semantic-scope".to_string());
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "unsupported chained folded intervalized decoding state relation semantic scope",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_member_continuity(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path =
        unique_temp_dir("cli-stwo-chained-folded-intervalized-decoding-state-relation-order")
            .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-order-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let members = proof_json["members"].as_array_mut().expect("members array");
    assert!(
        members.len() >= 2,
        "phase27 demo must emit at least two members"
    );
    members.swap(0, 1);
    let summaries = proof_json["member_summaries"]
        .as_array_mut()
        .expect("member_summaries array");
    summaries.swap(0, 1);
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "does not preserve the carried-state commitment from the previous folded interval member",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_stwo_recursion_batch_manifest() {
    let proof_a = unique_temp_dir("cli-stwo-recursion-proof-a").with_extension("json");
    let proof_b = unique_temp_dir("cli-stwo-recursion-proof-b").with_extension("json");
    let manifest_path = unique_temp_dir("cli-stwo-recursion-manifest").with_extension("json");

    let mut prove_a = tvm_command();
    prove_a
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&proof_a)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut prove_b = tvm_command();
    prove_b
        .arg("prove-stark")
        .arg("programs/counter.tvm")
        .arg("-o")
        .arg(&proof_b)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-recursion-batch")
        .arg("--proof")
        .arg(&proof_a)
        .arg("--proof")
        .arg(&proof_b)
        .arg("-o")
        .arg(&manifest_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(
            "batch_version: stwo-phase6-recursion-batch-v1",
        ))
        .stdout(predicate::str::contains("total_proofs: 2"));

    let manifest_json = std::fs::read_to_string(&manifest_path).expect("manifest json");
    assert!(manifest_json.contains("\"proof_backend\": \"stwo\""));
    assert!(manifest_json.contains("stwo_execution_proof_batch_preaggregation_manifest"));

    let _ = std::fs::remove_file(proof_a);
    let _ = std::fs::remove_file(proof_b);
    let _ = std::fs::remove_file(manifest_path);
}

#[test]
fn cli_verify_stark_rejects_backend_override_mismatch() {
    let proof_path = unique_temp_dir("cli-stark-proof-backend-mismatch").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "proof backend override `stwo` does not match encoded proof backend `vanilla`",
        ));

    let _ = std::fs::remove_file(proof_path);
}

#[test]
fn cli_runs_neural_style_programs_with_verify_native() {
    let cases = [
        ("programs/dot_product.tvm", "70"),
        ("programs/matmul_2x2.tvm", "134"),
        ("programs/single_neuron.tvm", "1"),
    ];

    for (program, expected_acc) in cases {
        let mut run = tvm_command();
        run.arg("run")
            .arg(program)
            .arg("--verify-native")
            .arg("--max-steps")
            .arg("128")
            .assert()
            .success()
            .stdout(predicate::str::contains(format!("acc: {expected_acc}")))
            .stdout(predicate::str::contains("verified_against_native: true"));
    }
}

#[test]
fn cli_verify_stark_rejects_malformed_proof_without_panic() {
    let valid_path = unique_temp_dir("cli-stark-proof-valid").with_extension("json");
    let bad_path = unique_temp_dir("cli-stark-proof-bad").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&valid_path)
        .assert()
        .success();

    let mut proof_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&valid_path).expect("read proof")).expect("json");
    proof_json["proof"] = serde_json::json!([0]);
    std::fs::write(
        &bad_path,
        serde_json::to_vec(&proof_json).expect("encode bad proof"),
    )
    .expect("write bad proof");

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&bad_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("stark proof verification failed"))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(valid_path);
    let _ = std::fs::remove_file(bad_path);
}

#[test]
fn cli_verify_stark_strict_policy_rejects_low_security_proof() {
    let proof_path = unique_temp_dir("cli-stark-proof-low-security").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&proof_path)
        .arg("--strict")
        .assert()
        .failure()
        .stderr(predicate::str::contains("conjectured security"))
        .stderr(predicate::str::contains("below required"));

    let _ = std::fs::remove_file(proof_path);
}

#[cfg(not(feature = "burn-model"))]
#[test]
fn cli_reports_missing_burn_feature_for_burn_engine() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--engine")
        .arg("burn")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "engine `burn` requires the `burn-model` feature",
        ));
}

#[cfg(feature = "burn-model")]
#[test]
fn cli_supports_burn_engine_selection() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--engine")
        .arg("burn")
        .assert()
        .success()
        .stdout(predicate::str::contains("engine: burn"))
        .stdout(predicate::str::contains("acc: 8"));
}

#[cfg(feature = "burn-model")]
#[test]
fn cli_supports_verify_burn_flag() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/fibonacci.tvm")
        .arg("--verify-burn")
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_burn: true"))
        .stdout(predicate::str::contains(
            "verified_burn_engines: transformer,native,burn",
        ))
        .stdout(predicate::str::contains("acc: 21"));
}

#[cfg(not(feature = "onnx-export"))]
#[test]
fn cli_reports_missing_onnx_feature_for_export_command() {
    let export_dir = unique_temp_dir("cli-export-missing-feature");
    let mut command = tvm_command();
    command
        .arg("export-onnx")
        .arg("programs/fibonacci.tvm")
        .arg("-o")
        .arg(&export_dir)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "`export-onnx` requires the `onnx-export` feature",
        ));
}

#[cfg(not(feature = "onnx-export"))]
#[test]
fn cli_reports_missing_onnx_feature_for_onnx_engine() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--engine")
        .arg("onnx")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "engine `onnx` requires the `onnx-export` feature",
        ));
}

#[cfg(not(feature = "onnx-export"))]
#[test]
fn cli_reports_missing_onnx_feature_for_research_v2_step() {
    let output_path = unique_temp_dir("cli-research-v2-step-missing").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v2-step")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "`research-v2-step` requires the `onnx-export` feature",
        ));
}

#[cfg(not(feature = "onnx-export"))]
#[test]
fn cli_reports_missing_onnx_feature_for_research_v2_trace() {
    let output_path = unique_temp_dir("cli-research-v2-trace-missing").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v2-trace")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "`research-v2-trace` requires the `onnx-export` feature",
        ));
}

#[cfg(not(feature = "onnx-export"))]
#[test]
fn cli_reports_missing_onnx_feature_for_research_v2_matrix() {
    let output_path = unique_temp_dir("cli-research-v2-matrix-missing").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v2-matrix")
        .arg("-o")
        .arg(&output_path)
        .arg("--program")
        .arg("programs/addition.tvm")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "`research-v2-matrix` requires the `onnx-export` feature",
        ));
}

#[cfg(feature = "onnx-export")]
#[test]
fn cli_supports_export_onnx_command() {
    let export_dir = unique_temp_dir("cli-export-onnx");
    let mut command = tvm_command();
    command
        .arg("export-onnx")
        .arg("programs/fibonacci.tvm")
        .arg("-o")
        .arg(&export_dir)
        .assert()
        .success()
        .stdout(predicate::str::contains("instructions:"))
        .stdout(predicate::str::contains("metadata:"));

    assert!(export_dir.join("metadata.json").exists());
    assert!(export_dir.join("instr_0.onnx").exists());

    let _ = std::fs::remove_dir_all(export_dir);
}

#[cfg(feature = "onnx-export")]
#[test]
fn cli_supports_onnx_engine_selection() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/addition.tvm")
        .arg("--engine")
        .arg("onnx")
        .assert()
        .success()
        .stdout(predicate::str::contains("engine: onnx"))
        .stdout(predicate::str::contains("acc: 8"));
}

#[cfg(feature = "onnx-export")]
#[test]
fn cli_supports_verify_onnx_flag() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/fibonacci.tvm")
        .arg("--verify-onnx")
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_onnx: true"))
        .stdout(predicate::str::contains(
            "verified_onnx_engines: transformer,native,onnx",
        ))
        .stdout(predicate::str::contains("acc: 21"));
}

#[cfg(feature = "onnx-export")]
#[test]
fn cli_supports_research_v2_step_command() {
    let output_path = unique_temp_dir("cli-research-v2-step").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v2-step")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .arg("--max-steps")
        .arg("1")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "statement_version: statement-v2-research-draft",
        ))
        .stdout(predicate::str::contains("matched: true"))
        .stdout(predicate::str::contains("commitment_program_hash:"));

    assert!(output_path.exists());
    let artifact_bytes = std::fs::read(&output_path).expect("artifact");
    let artifact_json: serde_json::Value =
        serde_json::from_slice(&artifact_bytes).expect("artifact json");
    validate_json_against_schema(
        &artifact_json,
        "spec/statement-v2-one-step-certificate.schema.json",
    );
    assert_research_v2_spec_commitments(
        &artifact_json,
        "spec/statement-v2-research.json",
        "spec/statement-v2-one-step-certificate.schema.json",
    );
    assert_eq!(
        artifact_json
            .get("statement_version")
            .and_then(serde_json::Value::as_str),
        Some("statement-v2-research-draft")
    );
    assert_eq!(
        artifact_json
            .get("matched")
            .and_then(serde_json::Value::as_bool),
        Some(true)
    );
    let _ = std::fs::remove_file(output_path);
}

#[cfg(feature = "onnx-export")]
#[test]
fn cli_supports_research_v2_trace_command() {
    let output_path = unique_temp_dir("cli-research-v2-trace").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v2-trace")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .arg("--max-steps")
        .arg("8")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "semantic_scope: prefix_trace_transformer_onnx_equivalence_under_fixed_profile",
        ))
        .stdout(predicate::str::contains("matched: true"))
        .stdout(predicate::str::contains("checked_steps: 3"));

    assert!(output_path.exists());
    let artifact_bytes = std::fs::read(&output_path).expect("artifact");
    let artifact_json: serde_json::Value =
        serde_json::from_slice(&artifact_bytes).expect("artifact json");
    validate_json_against_schema(
        &artifact_json,
        "spec/statement-v2-trace-certificate.schema.json",
    );
    assert_research_v2_spec_commitments(
        &artifact_json,
        "spec/statement-v2-trace-research.json",
        "spec/statement-v2-trace-certificate.schema.json",
    );
    assert_eq!(
        artifact_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some("prefix_trace_transformer_onnx_equivalence_under_fixed_profile")
    );
    assert_eq!(
        artifact_json
            .get("matched")
            .and_then(serde_json::Value::as_bool),
        Some(true)
    );
    assert_eq!(
        artifact_json
            .get("checked_steps")
            .and_then(serde_json::Value::as_u64),
        Some(3)
    );
    let _ = std::fs::remove_file(output_path);
}

#[cfg(feature = "onnx-export")]
#[test]
fn cli_supports_research_v2_matrix_command() {
    let output_path = unique_temp_dir("cli-research-v2-matrix").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v2-matrix")
        .arg("-o")
        .arg(&output_path)
        .arg("--program")
        .arg("programs/addition.tvm")
        .arg("--program")
        .arg("programs/counter.tvm")
        .arg("--max-steps")
        .arg("8")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "semantic_scope: matrix_prefix_trace_transformer_onnx_equivalence_under_fixed_profile",
        ))
        .stdout(predicate::str::contains("total_programs: 2"))
        .stdout(predicate::str::contains("mismatched_programs: 0"));

    assert!(output_path.exists());
    let artifact_bytes = std::fs::read(&output_path).expect("artifact");
    let artifact_json: serde_json::Value =
        serde_json::from_slice(&artifact_bytes).expect("artifact json");
    validate_json_against_schema(
        &artifact_json,
        "spec/statement-v2-matrix-certificate.schema.json",
    );
    assert_research_v2_spec_commitments(
        &artifact_json,
        "spec/statement-v2-matrix-research.json",
        "spec/statement-v2-matrix-certificate.schema.json",
    );
    assert_eq!(
        artifact_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some("matrix_prefix_trace_transformer_onnx_equivalence_under_fixed_profile")
    );
    assert_eq!(
        artifact_json
            .get("total_programs")
            .and_then(serde_json::Value::as_u64),
        Some(2)
    );
    assert_eq!(
        artifact_json
            .get("mismatched_programs")
            .and_then(serde_json::Value::as_u64),
        Some(0)
    );
    let _ = std::fs::remove_file(output_path);
}

#[cfg(all(feature = "burn-model", feature = "onnx-export"))]
#[test]
fn cli_supports_verify_all_flag() {
    let mut command = tvm_command();
    command
        .arg("run")
        .arg("programs/fibonacci.tvm")
        .arg("--verify-all")
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_all: true"))
        .stdout(predicate::str::contains(
            "verified_all_engines: transformer,native,burn,onnx",
        ))
        .stdout(predicate::str::contains("acc: 21"));
}
