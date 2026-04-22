use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use assert_cmd::Command;
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
#[cfg(feature = "stwo-backend")]
use flate2::GzBuilder;
#[cfg(any(feature = "onnx-export", feature = "stwo-backend"))]
use jsonschema::{Draft, JSONSchema};
use predicates::prelude::*;
use sha2::{Digest, Sha256};
#[cfg(feature = "stwo-backend")]
use std::io::Write;
#[cfg(feature = "stwo-backend")]
use std::sync::{Mutex, OnceLock};

#[cfg(feature = "stwo-backend")]
use llm_provable_computer::stwo_backend::{
    commit_phase12_shared_lookup_rows, commit_phase29_recursive_compression_input_contract,
    commit_phase31_recursive_compression_decode_boundary_manifest,
    commit_phase32_recursive_compression_statement_contract,
    commit_phase33_recursive_compression_public_input_manifest, phase12_default_decoding_layout,
    prove_phase10_shared_binary_step_lookup_envelope,
    prove_phase10_shared_normalization_lookup_envelope, prove_phase12_decoding_demo_for_layout,
    save_phase12_decoding_chain, Phase10SharedLookupProofEnvelope,
    Phase10SharedNormalizationLookupProofEnvelope, Phase12DecodingLayout,
    Phase29RecursiveCompressionInputContract, Phase3LookupTableRow,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
    STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
    STWO_BACKEND_VERSION_PHASE12,
    STWO_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE27,
    STWO_DECODING_CHAIN_VERSION_PHASE12, STWO_DECODING_CHAIN_VERSION_PHASE14,
    STWO_DECODING_CROSS_STEP_LOOKUP_ACCUMULATOR_VERSION_PHASE23,
    STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13, STWO_DECODING_LOOKUP_ACCUMULATOR_VERSION_PHASE22,
    STWO_DECODING_MATRIX_ACCUMULATOR_VERSION_PHASE21, STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17,
    STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15, STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16,
    STWO_DECODING_STATE_RELATION_ACCUMULATOR_VERSION_PHASE24,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30,
    STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
    STWO_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE26,
    STWO_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE25,
    STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
    STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37,
    STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37,
    STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31,
    STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29,
    STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29,
    STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33,
    STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33,
    STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34,
    STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34,
    STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32,
    STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32,
    STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35,
    STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35,
    STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36,
    STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36,
    STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12, STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12,
    STWO_SHARED_STATIC_ACTIVATION_TABLE_ID_PHASE12,
    STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12,
    STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12,
    STWO_SHARED_STATIC_NORMALIZATION_TABLE_ID_PHASE12,
};
#[cfg(feature = "stwo-backend")]
use llm_provable_computer::{StarkProofBackend, CLAIM_STATEMENT_VERSION_V1};

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
fn write_alternate_phase12_chain(path: &std::path::Path) {
    let default_layout = phase12_default_decoding_layout();
    let alternate_layout = Phase12DecodingLayout::new(2, 2).expect("alternate layout");
    assert_ne!(alternate_layout, default_layout);
    let manifest = prove_phase12_decoding_demo_for_layout(&alternate_layout)
        .expect("alternate phase12 decoding demo");
    save_phase12_decoding_chain(&manifest, path).expect("save alternate phase12 chain");
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
        .or_else(|| std::env::var_os("TVM_TEST_BINARY"))
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            panic!(
                "could not resolve current-feature `tvm` binary; set `TVM_TEST_BINARY` when `CARGO_BIN_EXE_tvm` is unavailable"
            )
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

#[cfg(feature = "stwo-backend")]
fn phase28_cli_demo_fixture_path() -> PathBuf {
    static FIXTURE: OnceLock<PathBuf> = OnceLock::new();
    FIXTURE
        .get_or_init(|| {
            let path = unique_temp_dir(
                "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-fixture",
            )
            .with_extension("json");
            let mut prove = tvm_command();
            prove
                .arg("prove-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
                .arg("-o")
                .arg(&path)
                .assert()
                .success();
            path
        })
        .clone()
}

#[cfg(feature = "stwo-backend")]
fn phase28_publication_artifact_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(
        "docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/decoding-phase28.aggregated-chained-folded-intervalized-state-relation.json.gz",
    )
}

#[cfg(feature = "stwo-backend")]
fn sample_phase29_recursive_compression_input_contract() -> Phase29RecursiveCompressionInputContract
{
    let mut contract = Phase29RecursiveCompressionInputContract {
        proof_backend: StarkProofBackend::Stwo,
        contract_version: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29.to_string(),
        semantic_scope: STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29.to_string(),
        phase28_artifact_version:
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28
                .to_string(),
        phase28_semantic_scope:
            STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28
                .to_string(),
        phase28_proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
        required_recursion_posture: STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE.to_string(),
        recursive_verification_claimed: false,
        cryptographic_compression_claimed: false,
        phase28_bounded_aggregation_arity: 2,
        phase28_member_count: 2,
        phase28_member_summaries: 2,
        phase28_nested_members: 2,
        total_phase26_members: 4,
        total_phase25_members: 8,
        max_nested_chain_arity: 2,
        max_nested_fold_arity: 2,
        total_matrices: 2,
        total_layouts: 4,
        total_rollups: 4,
        total_segments: 8,
        total_steps: 16,
        lookup_delta_entries: 8,
        max_lookup_frontier_entries: 2,
        source_template_commitment: "source-template".to_string(),
        global_start_state_commitment: "start-state".to_string(),
        global_end_state_commitment: "end-state".to_string(),
        aggregation_template_commitment: "aggregation-template".to_string(),
        aggregated_chained_folded_interval_accumulator_commitment: "accumulator".to_string(),
        input_contract_commitment: String::new(),
    };
    contract.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&contract).expect("commit contract");
    contract
}

#[cfg(feature = "stwo-backend")]
fn sample_phase29_contract_matched_to_phase30_manifest(
    manifest_json: &serde_json::Value,
) -> Phase29RecursiveCompressionInputContract {
    let mut contract = sample_phase29_recursive_compression_input_contract();
    contract.phase28_proof_backend_version = manifest_json["proof_backend_version"]
        .as_str()
        .expect("phase30 proof_backend_version")
        .to_string();
    contract.statement_version = manifest_json["statement_version"]
        .as_str()
        .expect("phase30 statement_version")
        .to_string();
    contract.total_steps = manifest_json["total_steps"]
        .as_u64()
        .expect("phase30 total_steps") as usize;
    contract.source_template_commitment = "a".repeat(64);
    contract.aggregation_template_commitment = "b".repeat(64);
    contract.global_start_state_commitment = manifest_json["chain_start_boundary_commitment"]
        .as_str()
        .expect("phase30 chain_start_boundary_commitment")
        .to_string();
    contract.global_end_state_commitment = manifest_json["chain_end_boundary_commitment"]
        .as_str()
        .expect("phase30 chain_end_boundary_commitment")
        .to_string();
    contract.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&contract).expect("commit contract");
    contract
}

#[cfg(feature = "stwo-backend")]
struct RecursiveCompressionCliFixture {
    proof_path: PathBuf,
    phase30_path: PathBuf,
    phase29_path: PathBuf,
    phase31_path: PathBuf,
    phase32_path: PathBuf,
    phase33_path: PathBuf,
    phase34_path: PathBuf,
    phase35_path: PathBuf,
}

#[cfg(feature = "stwo-backend")]
impl RecursiveCompressionCliFixture {
    fn cleanup(&self) {
        for path in [
            &self.proof_path,
            &self.phase30_path,
            &self.phase29_path,
            &self.phase31_path,
            &self.phase32_path,
            &self.phase33_path,
            &self.phase34_path,
            &self.phase35_path,
        ] {
            let _ = std::fs::remove_file(path);
        }
    }
}

#[cfg(feature = "stwo-backend")]
fn prepare_phase35_recursive_compression_cli_fixture(
    prefix: &str,
) -> RecursiveCompressionCliFixture {
    let proof_path = unique_temp_dir(&format!("{prefix}-proof")).with_extension("json");
    let phase30_path = unique_temp_dir(&format!("{prefix}-phase30")).with_extension("json");
    let phase29_path = unique_temp_dir(&format!("{prefix}-phase29")).with_extension("json");
    let phase31_path = unique_temp_dir(&format!("{prefix}-phase31")).with_extension("json");
    let phase32_path = unique_temp_dir(&format!("{prefix}-phase32")).with_extension("json");
    let phase33_path = unique_temp_dir(&format!("{prefix}-phase33")).with_extension("json");
    let phase34_path = unique_temp_dir(&format!("{prefix}-phase34")).with_extension("json");
    let phase35_path = unique_temp_dir(&format!("{prefix}-phase35")).with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success();

    let mut prepare_phase35 = tvm_command();
    prepare_phase35
        .arg("prepare-stwo-recursive-compression-target-manifest")
        .arg("--statement-contract")
        .arg(&phase32_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--shared-lookup")
        .arg(&phase34_path)
        .arg("-o")
        .arg(&phase35_path)
        .assert()
        .success();

    RecursiveCompressionCliFixture {
        proof_path,
        phase30_path,
        phase29_path,
        phase31_path,
        phase32_path,
        phase33_path,
        phase34_path,
        phase35_path,
    }
}

#[cfg(any(feature = "onnx-export", feature = "stwo-backend"))]
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
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
struct TestPhase12StaticLookupTableCommitment {
    table_id: String,
    statement_version: String,
    semantic_scope: String,
    table_commitment: String,
    row_count: u64,
    row_width: u64,
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
    let (static_table_commitments, static_table_registry_commitment) =
        phase12_static_lookup_table_registry_from_envelopes(
            &normalization.proof_envelope,
            &activation.proof_envelope,
        );

    let flattened_json = serde_json::to_vec(&flattened_lookup_rows).expect("flattened rows json");
    let static_table_commitments_json =
        serde_json::to_vec(&static_table_commitments).expect("static table commitments json");
    let normalization_json = serde_json::to_vec(&normalization).expect("normalization json");
    let activation_json = serde_json::to_vec(&activation).expect("activation json");

    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).expect("blake2b-256 hasher");
    hasher.update(STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(&(flattened_json.len() as u64).to_le_bytes());
    hasher.update(&flattened_json);
    hasher.update(STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12.as_bytes());
    hasher.update(STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12.as_bytes());
    hasher.update(static_table_registry_commitment.as_bytes());
    hasher.update(&(static_table_commitments_json.len() as u64).to_le_bytes());
    hasher.update(&static_table_commitments_json);
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
fn phase12_static_lookup_table_registry_from_envelopes(
    normalization_envelope: &Phase10SharedNormalizationLookupProofEnvelope,
    activation_envelope: &Phase10SharedLookupProofEnvelope,
) -> (Vec<TestPhase12StaticLookupTableCommitment>, String) {
    let normalization_rows: Vec<[i64; 2]> = normalization_envelope
        .canonical_table_rows
        .iter()
        .map(|(norm_sq, inv_sqrt_q8)| [i64::from(*norm_sq), i64::from(*inv_sqrt_q8)])
        .collect();
    let activation_rows: Vec<[i64; 2]> = activation_envelope
        .canonical_table_rows
        .iter()
        .map(|row| [i64::from(row.input), i64::from(row.output)])
        .collect();
    let table_commitments = vec![
        TestPhase12StaticLookupTableCommitment {
            table_id: STWO_SHARED_STATIC_NORMALIZATION_TABLE_ID_PHASE12.to_string(),
            statement_version: normalization_envelope.statement_version.clone(),
            semantic_scope: normalization_envelope.semantic_scope.clone(),
            table_commitment: phase12_static_lookup_table_commitment(
                STWO_SHARED_STATIC_NORMALIZATION_TABLE_ID_PHASE12,
                &normalization_envelope.statement_version,
                &normalization_envelope.semantic_scope,
                &normalization_rows,
            ),
            row_count: u64::try_from(normalization_rows.len()).expect("row count fits in u64"),
            row_width: 2,
        },
        TestPhase12StaticLookupTableCommitment {
            table_id: STWO_SHARED_STATIC_ACTIVATION_TABLE_ID_PHASE12.to_string(),
            statement_version: activation_envelope.statement_version.clone(),
            semantic_scope: activation_envelope.semantic_scope.clone(),
            table_commitment: phase12_static_lookup_table_commitment(
                STWO_SHARED_STATIC_ACTIVATION_TABLE_ID_PHASE12,
                &activation_envelope.statement_version,
                &activation_envelope.semantic_scope,
                &activation_rows,
            ),
            row_count: u64::try_from(activation_rows.len()).expect("row count fits in u64"),
            row_width: 2,
        },
    ];
    let table_commitments =
        canonical_test_phase12_static_lookup_table_commitments(table_commitments);
    let registry_commitment = phase12_static_lookup_table_registry_commitment(&table_commitments);
    (table_commitments, registry_commitment)
}

#[cfg(feature = "stwo-backend")]
fn phase12_static_lookup_table_commitment(
    table_id: &str,
    statement_version: &str,
    semantic_scope: &str,
    rows: &[[i64; 2]],
) -> String {
    let rows_json = serde_json::to_vec(rows).expect("static lookup table rows json");
    let row_count = u64::try_from(rows.len()).expect("row count fits in u64");
    let row_count_bytes = row_count.to_le_bytes();
    let row_width_bytes = 2u64.to_le_bytes();
    let rows_json_len_bytes = u64::try_from(rows_json.len())
        .expect("rows json length fits in u64")
        .to_le_bytes();
    phase12_blake2b_256_hex(&[
        STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12.as_bytes(),
        table_id.as_bytes(),
        statement_version.as_bytes(),
        semantic_scope.as_bytes(),
        &row_count_bytes,
        &row_width_bytes,
        &rows_json_len_bytes,
        &rows_json,
    ])
}

#[cfg(feature = "stwo-backend")]
fn phase12_static_lookup_table_registry_commitment(
    table_commitments: &[TestPhase12StaticLookupTableCommitment],
) -> String {
    let table_commitments =
        canonical_test_phase12_static_lookup_table_commitments(table_commitments.to_vec());
    let descriptors_json =
        serde_json::to_vec(&table_commitments).expect("static table commitments json");
    let descriptors_json_len_bytes = u64::try_from(descriptors_json.len())
        .expect("static table commitments json length fits in u64")
        .to_le_bytes();
    phase12_blake2b_256_hex(&[
        STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12.as_bytes(),
        STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12.as_bytes(),
        &descriptors_json_len_bytes,
        &descriptors_json,
    ])
}

#[cfg(feature = "stwo-backend")]
fn canonical_test_phase12_static_lookup_table_commitments(
    mut table_commitments: Vec<TestPhase12StaticLookupTableCommitment>,
) -> Vec<TestPhase12StaticLookupTableCommitment> {
    table_commitments.sort_by(|left, right| {
        (
            &left.table_id,
            &left.statement_version,
            &left.semantic_scope,
            &left.table_commitment,
            left.row_count,
            left.row_width,
        )
            .cmp(&(
                &right.table_id,
                &right.statement_version,
                &right.semantic_scope,
                &right.table_commitment,
                right.row_count,
                right.row_width,
            ))
    });
    table_commitments
}

#[cfg(feature = "stwo-backend")]
fn phase12_blake2b_256_hex(parts: &[&[u8]]) -> String {
    let mut output = [0u8; 32];
    let mut hasher = Blake2bVar::new(output.len()).expect("blake2b-256 hasher");
    for part in parts {
        hasher.update(part);
    }
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

fn hash_json_value(value: &serde_json::Value) -> String {
    blake2b_256_hex(&serde_json::to_vec(value).expect("json hash payload"))
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    Digest::update(&mut hasher, bytes);
    format!("{:x}", hasher.finalize())
}

fn write_hf_external_attestation_statement(
    path: &std::path::Path,
    subject_paths: &[&std::path::Path],
    builder_id: Option<&str>,
    build_invocation_id: Option<&str>,
) {
    let subjects = subject_paths
        .iter()
        .map(|subject_path| {
            let bytes = std::fs::read(subject_path).expect("read attestation subject");
            serde_json::json!({
                "name": subject_path.display().to_string(),
                "digest": {
                    "sha256": sha256_hex(&bytes),
                }
            })
        })
        .collect::<Vec<_>>();

    let mut predicate = serde_json::Map::new();
    let mut run_details = serde_json::Map::new();
    if let Some(builder_id) = builder_id {
        run_details.insert(
            "builder".to_string(),
            serde_json::json!({ "id": builder_id }),
        );
    }
    if let Some(build_invocation_id) = build_invocation_id {
        run_details.insert(
            "metadata".to_string(),
            serde_json::json!({ "invocationId": build_invocation_id }),
        );
    }
    if !run_details.is_empty() {
        predicate.insert(
            "runDetails".to_string(),
            serde_json::Value::Object(run_details),
        );
    }

    let statement = serde_json::json!({
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": serde_json::Value::Object(predicate),
    });
    std::fs::write(
        path,
        serde_json::to_vec_pretty(&statement).expect("serialize attestation statement"),
    )
    .expect("write attestation statement");
}

#[cfg(all(feature = "burn-model", feature = "onnx-export"))]
fn assert_research_v3_runtime_commitments(artifact: &serde_json::Value) {
    let expected_relation_format_hash =
        hash_json_value(artifact.get("relation_format").expect("relation_format"));
    let expected_limitations_hash =
        hash_json_value(artifact.get("limitations").expect("limitations"));
    let expected_frontend_runtime_semantics_registry_hash = hash_json_value(
        artifact
            .get("frontend_runtime_semantics_registry")
            .expect("frontend runtime semantics registry"),
    );
    let expected_engine_summaries_hash = hash_json_value(artifact.get("engines").expect("engines"));
    let expected_rule_witnesses_hash =
        hash_json_value(artifact.get("rule_witnesses").expect("rule_witnesses"));

    assert_eq!(
        json_string_at(artifact, &["commitments", "relation_format_hash"]),
        Some(expected_relation_format_hash.as_str())
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "limitations_hash"]),
        Some(expected_limitations_hash.as_str())
    );
    assert_eq!(
        json_string_at(
            artifact,
            &["commitments", "frontend_runtime_semantics_registry_hash"]
        ),
        Some(expected_frontend_runtime_semantics_registry_hash.as_str())
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "engine_summaries_hash"]),
        Some(expected_engine_summaries_hash.as_str())
    );
    assert_eq!(
        json_string_at(artifact, &["commitments", "rule_witnesses_hash"]),
        Some(expected_rule_witnesses_hash.as_str())
    );
}

#[cfg(all(feature = "burn-model", feature = "onnx-export"))]
fn research_v3_registry_lane_statuses(
    registry: &serde_json::Value,
) -> std::collections::BTreeMap<&str, &str> {
    let lanes = registry
        .get("lanes")
        .and_then(serde_json::Value::as_array)
        .expect("registry lanes");
    let mut lane_statuses = std::collections::BTreeMap::new();
    for lane in lanes {
        let lane_id = lane
            .get("lane_id")
            .and_then(serde_json::Value::as_str)
            .expect("registry lane_id");
        let status = lane
            .get("status")
            .and_then(serde_json::Value::as_str)
            .expect("registry lane status");
        assert!(
            lane_statuses.insert(lane_id, status).is_none(),
            "registry contains duplicate lane_id {lane_id}"
        );
    }
    assert_eq!(
        lane_statuses.len(),
        lanes.len(),
        "registry contains duplicate lane_id entries"
    );
    lane_statuses
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
        .stdout(predicate::str::contains("production-v1"))
        .stdout(predicate::str::contains("publication-v1"));

    let mut verify_help = tvm_command();
    verify_help
        .arg("verify-stark")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("--verification-profile"))
        .stdout(predicate::str::contains("--backend"))
        .stdout(predicate::str::contains("production-v1"))
        .stdout(predicate::str::contains("publication-v1"));
}

#[test]
fn cli_verify_stark_publication_profile_reexecutes() {
    let proof_path = unique_temp_dir("cli-stark-proof-publication-profile").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/addition.tvm")
        .arg("--stark-profile")
        .arg("publication-v1")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut verify = tvm_command();
    verify
        .arg("verify-stark")
        .arg(&proof_path)
        .arg("--verification-profile")
        .arg("publication-v1")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "verification_profile: publication-v1",
        ))
        .stdout(predicate::str::contains(
            "required_conjectured_security_bits: 96",
        ))
        .stdout(predicate::str::contains("reexecuted_equivalence: true"));

    let _ = std::fs::remove_file(proof_path);
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
        ("programs/linear_block_v1.tvm", "linear-block-v1", "16"),
        ("programs/linear_block_v2.tvm", "linear-block-v2", "16"),
        ("programs/linear_block_v3.tvm", "linear-block-v3", "16"),
        (
            "programs/linear_block_v4_with_lookup.tvm",
            "linear-block-v4-with-lookup",
            "16",
        ),
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
        assert!(proof_json.contains("stwo-phase10-linear-block-v4-with-lookup"));
        if program == "programs/linear_block_v1.tvm" {
            assert!(proof_json.contains("\"normalization_companion\""));
            assert!(proof_json.contains("stwo-normalization-demo-v1"));
            assert!(
                proof_json.contains("stwo_linear_block_v1_execution_plus_normalization_companion")
            );
        }
        if program == "programs/linear_block_v2.tvm"
            || program == "programs/linear_block_v3.tvm"
            || program == "programs/linear_block_v4_with_lookup.tvm"
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
            if program == "programs/linear_block_v2.tvm"
                || program == "programs/linear_block_v3.tvm"
            {
                assert_eq!(
                    payload["embedded_normalization"]["statement_version"],
                    "stwo-normalization-demo-v1"
                );
                let expected_norm_scope = if program == "programs/linear_block_v3.tvm" {
                    "stwo_linear_block_v3_execution_with_embedded_normalization"
                } else {
                    "stwo_linear_block_v2_execution_with_embedded_normalization"
                };
                assert_eq!(
                    payload["embedded_normalization"]["semantic_scope"],
                    expected_norm_scope
                );
            }
            if program == "programs/linear_block_v3.tvm" {
                assert_eq!(
                    payload["embedded_activation_lookup"]["statement_version"],
                    "stwo-binary-step-lookup-demo-v1"
                );
                assert_eq!(
                    payload["embedded_activation_lookup"]["semantic_scope"],
                    "stwo_linear_block_v3_execution_with_embedded_binary_step_lookup"
                );
            } else if program == "programs/linear_block_v4_with_lookup.tvm" {
                assert_eq!(
                    payload["embedded_shared_normalization"]["statement_version"],
                    "stwo-shared-normalization-lookup-v1"
                );
                assert_eq!(
                    payload["embedded_shared_normalization"]["semantic_scope"],
                    "stwo_linear_block_v4_with_lookup_execution_with_shared_normalization_lookup"
                );
                assert_eq!(
                    payload["embedded_shared_activation_lookup"]["statement_version"],
                    "stwo-shared-binary-step-lookup-v1"
                );
                assert_eq!(
                    payload["embedded_shared_activation_lookup"]["semantic_scope"],
                    "stwo_linear_block_v4_with_lookup_execution_with_shared_binary_step_lookup"
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
                "proof_backend_version: stwo-phase10-linear-block-v4-with-lookup",
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
        .arg("programs/linear_block_v1.tvm")
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
            "linear_block_v1 normalization companion does not match claimed final state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_linear_block_v2_embedded_normalization() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v2-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-linear-block-v2-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/linear_block_v2.tvm")
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
            "linear_block_v2/v3 embedded normalization does not match claimed final state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_linear_block_v3_embedded_activation() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v3-proof").with_extension("json");
    let invalid_path =
        unique_temp_dir("cli-stwo-linear-block-v3-proof-tampered").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/linear_block_v3.tvm")
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
            "linear_block_v3 embedded activation does not match claimed final state",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_linear_block_v4_with_lookup_shared_normalization() {
    let proof_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-proof").with_extension("json");
    let invalid_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-proof-tampered-norm")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
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
            "linear_block_v4_with_lookup shared normalization embedded claimed rows do not match the canonical final-state rows",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_tampered_linear_block_v4_with_lookup_shared_activation() {
    let proof_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-proof").with_extension("json");
    let invalid_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-proof-tampered-act")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
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
                "linear_block_v4_with_lookup shared activation embedded claimed rows do not match the canonical final-state rows",
            )
            .or(predicate::str::contains(
                "linear_block_v4_with_lookup shared activation does not match claimed final state",
            )),
        );

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(invalid_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stark_rejects_mismatched_stwo_backend_version_for_program_family() {
    let proof_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-proof").with_extension("json");
    let invalid_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-proof-bad-version")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
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
            "does not match expected `stwo-phase10-linear-block-v4-with-lookup`",
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
fn cli_can_prepare_and_verify_stwo_shared_normalization_primitive_artifact() {
    let artifact_path =
        unique_temp_dir("cli-stwo-shared-normalization-primitive").with_extension("json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-shared-normalization-primitive-artifact")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase92-shared-normalization-primitive-artifact-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_tensor_native_shared_normalization_primitive_artifact",
        ))
        .stdout(predicate::str::contains("total_steps: 2"))
        .stdout(predicate::str::contains("total_claimed_rows: 2"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase92-shared-normalization-primitive-artifact-v1"));
    assert!(artifact_json.contains("\"step_label\": \"token-step-0.norm\""));

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-shared-normalization-primitive-artifact")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "proof_backend_version: stwo-phase10-shared-normalization-lookup-v1",
        ));

    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_shared_normalization_primitive_artifact_rejects_tampered_step_rows() {
    let artifact_path =
        unique_temp_dir("cli-stwo-shared-normalization-primitive-bad").with_extension("json");

    tvm_command()
        .arg("prepare-stwo-shared-normalization-primitive-artifact")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["steps"][1]["claimed_rows"][0][1] = serde_json::json!(65);
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-shared-normalization-primitive-artifact")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("step rows"));

    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_tensor_native_chain_artifact() {
    let artifact_path = unique_temp_dir("cli-stwo-tensor-native-chain").with_extension("json");

    tvm_command()
        .arg("prepare-stwo-tensor-native-chain-artifact")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase93-tensor-native-chain-artifact-v1",
        ))
        .stdout(predicate::str::contains(
            "semantic_scope: stwo_tensor_native_transformer_shaped_chain_artifact",
        ))
        .stdout(predicate::str::contains("total_steps: 4"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase93-tensor-native-chain-artifact-v1"));
    assert!(artifact_json.contains("\"step_label\": \"attention.pre_norm\""));

    tvm_command()
        .arg("verify-stwo-tensor-native-chain-artifact")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "shared_table_registry_commitment:",
        ));

    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_tensor_native_chain_artifact_rejects_tampered_boundary() {
    let artifact_path = unique_temp_dir("cli-stwo-tensor-native-chain-bad").with_extension("json");

    tvm_command()
        .arg("prepare-stwo-tensor-native-chain-artifact")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["steps"][1]["carried_state_in"]["hidden_state_commitment"] = serde_json::json!("bad");
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-tensor-native-chain-artifact")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(
            predicate::str::contains("continuity mismatch")
                .or(predicate::str::contains("carried_state_in commitment")),
        );

    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_gemma_block_core_slice_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase945-proof")
        .with_extension("json");
    let chain_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase945-chain")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase945-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-tensor-native-chain-artifact")
        .arg("-o")
        .arg(&chain_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-linear-block-core-slice-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--chain")
        .arg(&chain_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase94-5-gemma-block-core-slice-artifact-v1",
        ))
        .stdout(predicate::str::contains(
            "program_label: linear_block_v4_with_lookup",
        ))
        .stdout(predicate::str::contains(
            "total_shared_normalization_rows: 2",
        ))
        .stdout(predicate::str::contains("total_shared_activation_rows: 2"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase94-5-gemma-block-core-slice-artifact-v1"));
    assert!(artifact_json.contains("\"program_label\": \"linear_block_v4_with_lookup\""));

    tvm_command()
        .arg("verify-stwo-linear-block-core-slice-artifact")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "normalization_row_set_commitment:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(chain_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_gemma_block_core_slice_artifact_rejects_tampered_normalization_rows() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase945-proof")
        .with_extension("json");
    let chain_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase945-chain")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase945-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-tensor-native-chain-artifact")
        .arg("-o")
        .arg(&chain_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-linear-block-core-slice-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--chain")
        .arg(&chain_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["shared_normalization_rows"][1]["inv_sqrt_q8"] = serde_json::json!(65);
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-linear-block-core-slice-artifact")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(
            predicate::str::contains("shared_normalization_rows")
                .or(predicate::str::contains("normalization_row_set_commitment")),
        );

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(chain_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_gemma_block_richer_slice_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase9475-proof")
        .with_extension("json");
    let chain_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase9475-chain")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase9475-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-tensor-native-chain-artifact")
        .arg("-o")
        .arg(&chain_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-linear-block-richer-slice-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--chain")
        .arg(&chain_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase94-75-gemma-block-richer-slice-artifact-v1",
        ))
        .stdout(predicate::str::contains("local_score: 2"))
        .stdout(predicate::str::contains("grouped_value_mix: 8"))
        .stdout(predicate::str::contains("residual_output: 4"))
        .stdout(predicate::str::contains(
            "selected_memory_window_entries: 12",
        ));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase94-75-gemma-block-richer-slice-artifact-v1"));
    assert!(artifact_json.contains("\"local_score\": 2"));

    tvm_command()
        .arg("verify-stwo-linear-block-richer-slice-artifact")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "selected_memory_window_commitment:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(chain_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_gemma_block_richer_slice_artifact_rejects_tampered_residual() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase9475-proof")
        .with_extension("json");
    let chain_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase9475-chain")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase9475-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-tensor-native-chain-artifact")
        .arg("-o")
        .arg(&chain_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-linear-block-richer-slice-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--chain")
        .arg(&chain_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["residual_output"] = serde_json::json!(5);
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-linear-block-richer-slice-artifact")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(
            predicate::str::contains("summary fields")
                .or(predicate::str::contains("artifact commitment")),
        );

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(chain_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_repeated_gemma_slice_accumulation_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase95-proof")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase95-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("4")
        .arg("--token-position")
        .arg("0")
        .arg("--start-block-index")
        .arg("2")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase95-repeated-gemma-slice-accumulation-artifact-v1",
        ))
        .stdout(predicate::str::contains("total_slices: 4"))
        .stdout(predicate::str::contains("start_block_index: 2"))
        .stdout(predicate::str::contains("terminal_block_index: 5"))
        .stdout(predicate::str::contains(
            "naive_repeated_proof_bytes: 361728",
        ));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase95-repeated-gemma-slice-accumulation-artifact-v1"));
    assert!(artifact_json.contains("\"block_index\": 5"));

    tvm_command()
        .arg("verify-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains("members_commitment:"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_repeated_gemma_slice_accumulation_artifact_rejects_tampered_member() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase95-proof")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase95-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("3")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["members"][1]["block_index"] = serde_json::json!(9);
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("block_index").or(predicate::str::contains("member 1")));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prepare_stwo_repeated_gemma_slice_accumulation_artifact_rejects_oversized_total_slices() {
    let proof_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase95-proof-oversized")
            .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase95-artifact-oversized")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("17")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("at most 16 slices"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_folded_gemma_slice_accumulation_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase965-proof")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase965-source")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase965-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("4")
        .arg("--start-block-index")
        .arg("2")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-linear-block-slice-accumulation-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase96-5-folded-gemma-slice-accumulation-artifact-v1",
        ))
        .stdout(predicate::str::contains("bounded_fold_arity: 2"))
        .stdout(predicate::str::contains("total_folded_groups: 2"))
        .stdout(predicate::str::contains("local_score_sum: 8"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase96-5-folded-gemma-slice-accumulation-artifact-v1"));

    tvm_command()
        .arg("verify-stwo-folded-linear-block-slice-accumulation-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains(
            "folded_slice_accumulator_commitment:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_gemma_slice_accumulation_artifact_rejects_tampered_accumulator() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase965-proof-bad")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase965-source-bad")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase965-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-linear-block-slice-accumulation-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["folded_slice_accumulator_commitment"] = serde_json::json!("bad-accumulator");
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-folded-linear-block-slice-accumulation-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "folded_slice_accumulator_commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_folded_gemma_richer_slice_family_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-proof")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-source")
        .with_extension("json");
    let folded_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-folded")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-linear-block-slice-accumulation-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&folded_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-linear-block-richer-slice-family-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase98-folded-gemma-richer-slice-family-artifact-v1",
        ))
        .stdout(predicate::str::contains(
            "selected_memory_window_family_commitment:",
        ))
        .stdout(predicate::str::contains("primary_norm_sq_min: 16"))
        .stdout(predicate::str::contains("primary_activation_output_sum: 4"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains("stwo-phase98-folded-gemma-richer-slice-family-artifact-v1"));

    tvm_command()
        .arg("verify-stwo-folded-linear-block-richer-slice-family-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains(
            "folded_richer_family_accumulator_commitment:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(folded_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_gemma_richer_slice_family_artifact_rejects_tampered_family_commitment() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-proof-bad")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-source-bad")
        .with_extension("json");
    let folded_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-folded-bad")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase98-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-repeated-linear-block-slice-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-linear-block-slice-accumulation-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&folded_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-linear-block-richer-slice-family-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["selected_memory_window_family_commitment"] = serde_json::json!("bad-family");
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-folded-linear-block-richer-slice-family-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "selected_memory_window_family_commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(folded_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_multi_interval_gemma_richer_family_accumulation_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase99-proof")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase99-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-intervals")
        .arg("4")
        .arg("--interval-total-slices")
        .arg("4")
        .arg("--token-position-start")
        .arg("1")
        .arg("--token-position-stride")
        .arg("2")
        .arg("--start-block-index")
        .arg("2")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase99-multi-interval-gemma-richer-family-accumulation-artifact-v1",
        ))
        .stdout(predicate::str::contains("total_intervals: 4"))
        .stdout(predicate::str::contains("terminal_token_position: 7"))
        .stdout(predicate::str::contains("interval_members_commitment:"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json
        .contains("stwo-phase99-multi-interval-gemma-richer-family-accumulation-artifact-v1",));
    assert!(artifact_json.contains("\"repeated_token_position\": 7"));

    tvm_command()
        .arg("verify-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(
            "naive_interval_repeated_proof_bytes:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_multi_interval_gemma_richer_family_accumulation_artifact_rejects_member_drift() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase99-proof-bad")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase99-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-intervals")
        .arg("3")
        .arg("--interval-total-slices")
        .arg("4")
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["members"][1]["repeated_token_position"] = serde_json::json!(99);
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg(&artifact_path)
        .assert()
        .failure()
        .stderr(
            predicate::str::contains("interval member 1").or(predicate::str::contains(
                "canonical reconstructed richer-family interval",
            )),
        );

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_folded_multi_interval_gemma_accumulation_prototype_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase1015-proof")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase1015-source")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase1015-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-intervals")
        .arg("4")
        .arg("--interval-total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase101-5-folded-multi-interval-gemma-accumulation-prototype-artifact-v1",
        ))
        .stdout(predicate::str::contains("bounded_fold_arity: 2"))
        .stdout(predicate::str::contains("total_folded_interval_groups: 2"))
        .stdout(predicate::str::contains("accumulation_handoff_commitment:"));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json.contains(
        "stwo-phase101-5-folded-multi-interval-gemma-accumulation-prototype-artifact-v1",
    ));

    tvm_command()
        .arg("verify-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains(
            "folded_interval_prototype_accumulator_commitment:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_multi_interval_gemma_accumulation_prototype_artifact_rejects_handoff_drift(
) {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase1015-proof-bad")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase1015-source-bad")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase1015-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-intervals")
        .arg("4")
        .arg("--interval-total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["accumulation_handoff_commitment"] = serde_json::json!("bad-handoff");
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("accumulation_handoff_commitment"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_folded_multi_interval_gemma_richer_family_artifact() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-proof")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-source")
        .with_extension("json");
    let folded_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-folded")
        .with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-artifact")
        .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-intervals")
        .arg("4")
        .arg("--interval-total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&folded_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-multi-interval-linear-block-richer-family-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "artifact_version: stwo-phase102-folded-multi-interval-gemma-richer-family-artifact-v1",
        ))
        .stdout(predicate::str::contains("total_folded_richer_groups: 2"))
        .stdout(predicate::str::contains(
            "folded_richer_multi_interval_family_accumulator_commitment:",
        ));

    let artifact_json = std::fs::read_to_string(&artifact_path).expect("artifact json");
    assert!(artifact_json
        .contains("stwo-phase102-folded-multi-interval-gemma-richer-family-artifact-v1"));

    tvm_command()
        .arg("verify-stwo-folded-multi-interval-linear-block-richer-family-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains(
            "selected_memory_window_family_commitment_sequence_commitment:",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(folded_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_folded_multi_interval_gemma_richer_family_artifact_rejects_sequence_drift() {
    let proof_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-proof-bad")
        .with_extension("json");
    let source_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-source-bad")
        .with_extension("json");
    let folded_path = unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-folded-bad")
        .with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-linear-block-v4-with-lookup-phase102-artifact-bad")
            .with_extension("json");

    tvm_command()
        .arg("prove-stark")
        .arg("programs/linear_block_v4_with_lookup.tvm")
        .arg("-o")
        .arg(&proof_path)
        .arg("--backend")
        .arg("stwo")
        .arg("--max-steps")
        .arg("256")
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--total-intervals")
        .arg("4")
        .arg("--interval-total-slices")
        .arg("4")
        .arg("-o")
        .arg(&source_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("-o")
        .arg(&folded_path)
        .assert()
        .success();

    tvm_command()
        .arg("prepare-stwo-folded-multi-interval-linear-block-richer-family-artifact")
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("parse artifact json");
    artifact["selected_memory_window_family_commitment_sequence_commitment"] =
        serde_json::json!("bad-sequence");
    std::fs::write(
        &artifact_path,
        serde_json::to_string_pretty(&artifact).expect("serialize tampered artifact"),
    )
    .expect("write tampered artifact");

    tvm_command()
        .arg("verify-stwo-folded-multi-interval-linear-block-richer-family-artifact")
        .arg(&artifact_path)
        .arg("--source")
        .arg(&source_path)
        .arg("--folded")
        .arg(&folded_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "selected_memory_window_family_commitment_sequence_commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(source_path);
    let _ = std::fs::remove_file(folded_path);
    let _ = std::fs::remove_file(artifact_path);
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
    let shared_lookup_artifacts = proof_json["shared_lookup_artifacts"]
        .as_array()
        .expect("shared lookup artifacts array");
    assert!(!shared_lookup_artifacts.is_empty());
    for artifact in shared_lookup_artifacts {
        validate_json_against_schema(
            artifact,
            "spec/stwo-phase12-shared-lookup-artifact.schema.json",
        );
    }

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
fn cli_can_prepare_and_verify_stwo_shared_lookup_artifact() {
    let proof_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-proof").with_extension("json");
    let artifact_path = unique_temp_dir("cli-stwo-shared-lookup-artifact").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("proof json value");
    let artifact_commitment = proof_json["shared_lookup_artifacts"][0]["artifact_commitment"]
        .as_str()
        .expect("shared lookup artifact commitment")
        .to_string();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-shared-lookup-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--artifact-commitment")
        .arg(&artifact_commitment)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "artifact_version: {STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12}",
        )))
        .stdout(predicate::str::contains(format!(
            "artifact_commitment: {artifact_commitment}",
        )));

    let artifact_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("artifact json value");
    validate_json_against_schema(
        &artifact_json,
        "spec/stwo-phase12-shared-lookup-artifact.schema.json",
    );
    assert_eq!(
        artifact_json
            .get("artifact_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_SHARED_LOOKUP_ARTIFACT_VERSION_PHASE12)
    );
    assert_eq!(
        artifact_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_SHARED_LOOKUP_ARTIFACT_SCOPE_PHASE12)
    );
    assert_eq!(
        artifact_json
            .get("artifact_commitment")
            .and_then(serde_json::Value::as_str),
        Some(artifact_commitment.as_str())
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-shared-lookup-artifact")
        .arg("--artifact")
        .arg(&artifact_path)
        .arg("--proof")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_artifact: true"))
        .stdout(predicate::str::contains("verified_against_chain: true"))
        .stdout(predicate::str::contains(format!(
            "static_table_registry_scope: {STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12}",
        )));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_shared_lookup_artifact_rejects_tampered_registry_commitment() {
    let proof_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-proof-tamper").with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-tamper").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-registry-drift").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("proof json value");
    let artifact_commitment = proof_json["shared_lookup_artifacts"][0]["artifact_commitment"]
        .as_str()
        .expect("shared lookup artifact commitment")
        .to_string();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-shared-lookup-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--artifact-commitment")
        .arg(&artifact_commitment)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    let mut artifact_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&artifact_path).expect("artifact json"))
            .expect("artifact json value");
    artifact_json["static_table_registry_commitment"] = serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec_pretty(&artifact_json).expect("tampered artifact json"),
    )
    .expect("write tampered artifact");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-shared-lookup-artifact")
        .arg("--artifact")
        .arg(&tampered_path)
        .arg("--proof")
        .arg(&proof_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "static table registry commitment does not match its table descriptors",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(artifact_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_shared_lookup_artifact_rejects_wrong_proof_chain() {
    let proof_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-proof-valid").with_extension("json");
    let wrong_proof_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-proof-wrong").with_extension("json");
    let artifact_path =
        unique_temp_dir("cli-stwo-shared-lookup-artifact-valid").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("proof json value");
    let artifact_commitment = proof_json["shared_lookup_artifacts"][0]["artifact_commitment"]
        .as_str()
        .expect("shared lookup artifact commitment")
        .to_string();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-shared-lookup-artifact")
        .arg("--proof")
        .arg(&proof_path)
        .arg("--artifact-commitment")
        .arg(&artifact_commitment)
        .arg("-o")
        .arg(&artifact_path)
        .assert()
        .success();

    write_alternate_phase12_chain(&wrong_proof_path);

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-shared-lookup-artifact")
        .arg("--artifact")
        .arg(&artifact_path)
        .arg("--proof")
        .arg(&wrong_proof_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "Phase 12 shared lookup artifact layout commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(wrong_proof_path);
    let _ = std::fs::remove_file(artifact_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_decoding_step_envelope_manifest() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-proof").with_extension("json");
    let manifest_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-manifest").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&manifest_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "manifest_version: {STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30}",
        )))
        .stdout(predicate::str::contains("total_steps: 3"));

    let manifest_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&manifest_path).expect("manifest json"))
            .expect("json");
    validate_json_against_schema(
        &manifest_json,
        "spec/stwo-phase30-decoding-step-envelope-manifest.schema.json",
    );
    assert_eq!(
        manifest_json
            .get("manifest_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30)
    );
    assert_eq!(
        manifest_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_DECODING_STEP_ENVELOPE_MANIFEST_SCOPE_PHASE30)
    );
    assert_eq!(
        manifest_json
            .get("total_steps")
            .and_then(serde_json::Value::as_u64),
        Some(3)
    );
    assert_eq!(
        manifest_json["envelopes"][0]["step_index"]
            .as_u64()
            .expect("step index"),
        0
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-step-envelope-manifest")
        .arg("--manifest")
        .arg(&manifest_path)
        .arg("--proof")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_manifest: true"))
        .stdout(predicate::str::contains("verified_against_chain: true"))
        .stdout(predicate::str::contains(format!(
            "manifest_version: {STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30}",
        )));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(manifest_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_step_envelope_manifest_rejects_tampered_end_boundary() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-proof-tamper").with_extension("json");
    let manifest_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-manifest-tamper").with_extension("json");
    let tampered_path = unique_temp_dir("cli-stwo-decoding-step-envelope-manifest-end-drift")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&manifest_path)
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&manifest_path).expect("manifest json"))
            .expect("json");
    manifest_json["chain_end_boundary_commitment"] = serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&manifest_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-step-envelope-manifest")
        .arg("--manifest")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "end boundary does not match the final envelope",
        ))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(manifest_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_decoding_step_envelope_manifest_rejects_wrong_proof_chain() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-proof-valid").with_extension("json");
    let wrong_proof_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-proof-wrong").with_extension("json");
    let manifest_path =
        unique_temp_dir("cli-stwo-decoding-step-envelope-manifest-valid").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&manifest_path)
        .assert()
        .success();

    write_alternate_phase12_chain(&wrong_proof_path);

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-decoding-step-envelope-manifest")
        .arg("--manifest")
        .arg(&manifest_path)
        .arg("--proof")
        .arg(&wrong_proof_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "decoding step envelope manifest does not match the derived Phase 12 chain",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(wrong_proof_path);
    let _ = std::fs::remove_file(manifest_path);
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
fn cli_verify_stwo_decoding_family_demo_rejects_tampered_static_table_descriptor() {
    let proof_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-static-table-proof").with_extension("json");
    let scope_tampered_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-static-table-scope-tampered")
            .with_extension("json");
    let shape_tampered_path =
        unique_temp_dir("cli-stwo-decoding-family-demo-static-table-shape-tampered")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let mut scope_tampered_json = proof_json.clone();
    let artifact = &proof_json["shared_lookup_artifacts"]
        .as_array()
        .expect("artifact array")[0];
    let original_commitment = artifact["artifact_commitment"]
        .as_str()
        .expect("artifact commitment")
        .to_string();

    let artifact = &mut scope_tampered_json["shared_lookup_artifacts"]
        .as_array_mut()
        .expect("artifact array")[0];
    artifact["static_table_commitments"][0]["semantic_scope"] =
        serde_json::Value::String("tampered-static-table-scope".to_string());
    let tampered_commitment = phase12_artifact_commitment_from_json(artifact);
    artifact["artifact_commitment"] = serde_json::Value::String(tampered_commitment.clone());

    for step in scope_tampered_json["steps"]
        .as_array_mut()
        .expect("steps array")
    {
        if step["shared_lookup_artifact_commitment"] == original_commitment {
            step["shared_lookup_artifact_commitment"] =
                serde_json::Value::String(tampered_commitment.clone());
        }
    }

    std::fs::write(
        &scope_tampered_path,
        serde_json::to_vec(&scope_tampered_json).expect("serialize"),
    )
    .expect("write");

    let mut verify_scope = tvm_command();
    verify_scope
        .arg("verify-stwo-decoding-family-demo")
        .arg(&scope_tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("static table commitments"));

    let mut shape_tampered_json = proof_json;
    let artifact = &mut shape_tampered_json["shared_lookup_artifacts"]
        .as_array_mut()
        .expect("artifact array")[0];
    artifact["static_table_commitments"][0]["row_count"] = serde_json::Value::from(123_456u64);
    artifact["static_table_commitments"][0]["row_width"] = serde_json::Value::from(3u64);
    let tampered_commitment = phase12_artifact_commitment_from_json(artifact);
    artifact["artifact_commitment"] = serde_json::Value::String(tampered_commitment.clone());

    for step in shape_tampered_json["steps"]
        .as_array_mut()
        .expect("steps array")
    {
        if step["shared_lookup_artifact_commitment"] == original_commitment {
            step["shared_lookup_artifact_commitment"] =
                serde_json::Value::String(tampered_commitment.clone());
        }
    }

    std::fs::write(
        &shape_tampered_path,
        serde_json::to_vec(&shape_tampered_json).expect("serialize"),
    )
    .expect("write");

    let mut verify_shape = tvm_command();
    verify_shape
        .arg("verify-stwo-decoding-family-demo")
        .arg(&shape_tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("static table commitments"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(scope_tampered_path);
    let _ = std::fs::remove_file(shape_tampered_path);
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
            "exceed the final nested cumulative total",
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
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_accumulator_commitment(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path =
        unique_temp_dir("cli-stwo-chained-folded-intervalized-decoding-state-relation-accumulator")
            .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-accumulator-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["chained_folded_interval_accumulator_commitment"] =
        serde_json::Value::String("tampered".to_string());
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
            "chained_folded_interval_accumulator_commitment does not match the computed chained fold accumulator commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
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
fn cli_verify_stwo_chained_folded_intervalized_decoding_state_relation_demo_rejects_underreported_total_phase25_members(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-total-phase25-underflow",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-chained-folded-intervalized-decoding-state-relation-total-phase25-underflow-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase27_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["total_phase25_members"] = serde_json::Value::from(1_u64);
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
        .stderr(predicate::str::contains("total_phase25_members=1"))
        .stderr(predicate::str::contains(
            "must be between 4 and supported maximum",
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
fn cli_can_verify_stwo_recursive_compression_input_contract() {
    let contract_path = unique_temp_dir("cli-stwo-recursive-compression-input-contract-fast")
        .with_extension("json");
    let contract = sample_phase29_recursive_compression_input_contract();
    std::fs::write(
        &contract_path,
        serde_json::to_vec_pretty(&contract).expect("serialize contract"),
    )
    .expect("write contract");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-input-contract")
        .arg("--input")
        .arg(&contract_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_contract: true"))
        .stdout(predicate::str::contains(format!(
            "expected_contract_version: {STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29}",
        )))
        .stdout(predicate::str::contains(
            "recursive_verification_claimed: false",
        ))
        .stdout(predicate::str::contains(
            "cryptographic_compression_claimed: false",
        ));

    let _ = std::fs::remove_file(contract_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
#[ignore = "expensive Phase 28 proof-checking CLI gate"]
fn cli_can_prepare_and_verify_stwo_recursive_compression_input_contract() {
    let _guard = phase27_cli_test_guard();
    let phase28_path = phase28_publication_artifact_path();
    let contract_path =
        unique_temp_dir("cli-stwo-recursive-compression-input-contract").with_extension("json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-recursive-compression-input-contract")
        .arg("--phase28")
        .arg(&phase28_path)
        .arg("-o")
        .arg(&contract_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_phase28: true"))
        .stdout(predicate::str::contains(format!(
            "contract_version: {STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29}",
        )))
        .stdout(predicate::str::contains(
            "recursive_verification_claimed: false",
        ))
        .stdout(predicate::str::contains(
            "cryptographic_compression_claimed: false",
        ));

    let contract_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&contract_path).expect("contract json"))
            .expect("json");
    assert_eq!(
        contract_json
            .get("contract_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29)
    );
    assert_eq!(
        contract_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_SCOPE_PHASE29)
    );
    assert_eq!(
        contract_json
            .get("recursive_verification_claimed")
            .and_then(serde_json::Value::as_bool),
        Some(false)
    );
    assert_eq!(
        contract_json
            .get("cryptographic_compression_claimed")
            .and_then(serde_json::Value::as_bool),
        Some(false)
    );
    assert_eq!(
        contract_json
            .get("input_contract_commitment")
            .and_then(serde_json::Value::as_str)
            .map(str::len),
        Some(64)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-input-contract")
        .arg("--input")
        .arg(&contract_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_contract: true"))
        .stdout(predicate::str::contains(format!(
            "expected_contract_version: {STWO_RECURSIVE_COMPRESSION_INPUT_CONTRACT_VERSION_PHASE29}",
        )));

    let _ = std::fs::remove_file(contract_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_input_contract_rejects_tampered_commitment() {
    let contract_path = unique_temp_dir("cli-stwo-recursive-compression-input-contract-tamper")
        .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-recursive-compression-input-contract-commitment-tampered")
            .with_extension("json");
    let contract = sample_phase29_recursive_compression_input_contract();
    std::fs::write(
        &contract_path,
        serde_json::to_vec_pretty(&contract).expect("serialize contract"),
    )
    .expect("write contract");

    let mut contract_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&contract_path).expect("contract json"))
            .expect("json");
    contract_json["input_contract_commitment"] = serde_json::Value::String("tampered".to_string());
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&contract_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-input-contract")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(contract_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_input_contract_rejects_recomputed_header_drift() {
    let contract_path =
        unique_temp_dir("cli-stwo-recursive-compression-input-contract-header-drift")
            .with_extension("json");
    let mut contract = sample_phase29_recursive_compression_input_contract();
    contract.semantic_scope = "forged-phase29-semantic-scope".to_string();
    contract.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&contract).expect("recommit contract");
    std::fs::write(
        &contract_path,
        serde_json::to_vec_pretty(&contract).expect("serialize contract"),
    )
    .expect("write contract");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-input-contract")
        .arg("--input")
        .arg(&contract_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("scope"))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(contract_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prepare_stwo_recursive_compression_input_contract_rejects_synthetic_phase28_shell() {
    let phase28_path = unique_temp_dir("cli-stwo-recursive-compression-input-phase28-shell")
        .with_extension("json");
    let contract_path = unique_temp_dir("cli-stwo-recursive-compression-input-contract-shell")
        .with_extension("json");

    let phase28_json = serde_json::json!({
        "proof_backend": "stwo",
        "artifact_version": STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28,
        "semantic_scope": STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_SCOPE_PHASE28,
        "proof_backend_version": STWO_BACKEND_VERSION_PHASE12,
        "statement_version": CLAIM_STATEMENT_VERSION_V1,
        "recursion_posture": STWO_PHASE28_RECURSION_POSTURE_PRE_RECURSIVE,
        "recursive_verification_claimed": false,
        "cryptographic_compression_claimed": false,
        "bounded_aggregation_arity": 2,
        "member_count": 0,
        "total_phase26_members": 0,
        "total_phase25_members": 0,
        "max_nested_chain_arity": 0,
        "max_nested_fold_arity": 0,
        "total_matrices": 0,
        "total_layouts": 0,
        "total_rollups": 0,
        "total_segments": 0,
        "total_steps": 0,
        "lookup_delta_entries": 0,
        "max_lookup_frontier_entries": 0,
        "source_template_commitment": "source-template",
        "global_start_state_commitment": "start-state",
        "global_end_state_commitment": "end-state",
        "aggregation_template_commitment": "aggregation-template",
        "aggregated_chained_folded_interval_accumulator_commitment": "accumulator",
        "member_summaries": [],
        "members": []
    });
    std::fs::write(
        &phase28_path,
        serde_json::to_vec(&phase28_json).expect("serialize"),
    )
    .expect("write");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-recursive-compression-input-contract")
        .arg("--phase28")
        .arg(&phase28_path)
        .arg("-o")
        .arg(&contract_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "must contain at least two members",
        ))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(phase28_path);
    let _ = std::fs::remove_file(contract_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_compression_decode_boundary_manifest() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-proof")
        .with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase30")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase29")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase31")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    validate_json_against_schema(
        &phase30_json,
        "spec/stwo-phase30-decoding-step-envelope-manifest.schema.json",
    );

    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "manifest_version: {STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31}",
        )))
        .stdout(predicate::str::contains("verified_phase29_contract: true"))
        .stdout(predicate::str::contains("verified_phase30_manifest: true"));

    let phase31_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase31_path).expect("phase31 json"))
            .expect("phase31 value");
    validate_json_against_schema(
        &phase31_json,
        "spec/stwo-phase31-recursive-compression-decode-boundary-manifest.schema.json",
    );
    assert_eq!(
        phase31_json
            .get("manifest_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_VERSION_PHASE31)
    );
    assert_eq!(
        phase31_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_DECODE_BOUNDARY_MANIFEST_SCOPE_PHASE31)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--input")
        .arg(&phase31_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_manifest: true"));

    let mut verify_sources = tvm_command();
    verify_sources
        .arg("verify-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--input")
        .arg(&phase31_path)
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_sources: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_decode_boundary_manifest_rejects_tampered_commitment() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-proof-tamper")
        .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase30-tamper")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase29-tamper")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase31-tamper")
            .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase31-commitment-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut phase31_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase31_path).expect("phase31 json"))
            .expect("phase31 value");
    phase31_json["decode_boundary_bridge_commitment"] = serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&phase31_json).expect("serialize tampered phase31"),
    )
    .expect("write tampered phase31");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_decode_boundary_manifest_rejects_source_drift() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-proof-drift")
        .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase30-drift")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase29-drift")
            .with_extension("json");
    let tampered_phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase29-start-drift")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase31-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut tampered_phase29 = phase29.clone();
    tampered_phase29.global_start_state_commitment = "tampered-start-boundary".to_string();
    tampered_phase29.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&tampered_phase29)
            .expect("commit tampered phase29");
    std::fs::write(
        &tampered_phase29_path,
        serde_json::to_vec_pretty(&tampered_phase29).expect("serialize tampered phase29"),
    )
    .expect("write tampered phase29");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--input")
        .arg(&phase31_path)
        .arg("--contract")
        .arg(&tampered_phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires Phase 29 global_start_state_commitment to match the Phase 30 chain_start_boundary_commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(tampered_phase29_path);
    let _ = std::fs::remove_file(phase31_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_decode_boundary_manifest_rejects_partial_source_pair() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-proof-pair")
        .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase30-pair")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase29-pair")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-decode-boundary-phase31-pair")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut verify_contract_only = tvm_command();
    verify_contract_only
        .arg("verify-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--input")
        .arg(&phase31_path)
        .arg("--contract")
        .arg(&phase29_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires both `--contract` and `--manifest`",
        ));

    let mut verify_manifest_only = tvm_command();
    verify_manifest_only
        .arg("verify-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--input")
        .arg(&phase31_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires both `--contract` and `--manifest`",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_compression_statement_contract() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-statement-contract-proof")
        .with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase30")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase29")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase31")
        .with_extension("json");
    let phase32_path = unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase32")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "contract_version: {STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32}",
        )))
        .stdout(predicate::str::contains("verified_phase31_manifest: true"));

    let phase32_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase32_path).expect("phase32 json"))
            .expect("phase32 value");
    validate_json_against_schema(
        &phase32_json,
        "spec/stwo-phase32-recursive-compression-statement-contract.schema.json",
    );
    assert_eq!(
        phase32_json
            .get("contract_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_VERSION_PHASE32)
    );
    assert_eq!(
        phase32_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_STATEMENT_CONTRACT_SCOPE_PHASE32)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-compression-statement-contract")
        .arg("--input")
        .arg(&phase32_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_contract: true"));

    let mut verify_source = tvm_command();
    verify_source
        .arg("verify-stwo-recursive-compression-statement-contract")
        .arg("--input")
        .arg(&phase32_path)
        .arg("--manifest")
        .arg(&phase31_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_source: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_statement_contract_rejects_tampered_commitment() {
    let proof_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-proof-tamper")
            .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase30-tamper")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase29-tamper")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase31-tamper")
            .with_extension("json");
    let phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase32-tamper")
            .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-commitment-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut phase32_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase32_path).expect("phase32 json"))
            .expect("phase32 value");
    phase32_json["recursive_statement_contract_commitment"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&phase32_json).expect("serialize tampered phase32"),
    )
    .expect("write tampered phase32");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-statement-contract")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_statement_contract_rejects_source_drift() {
    let proof_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-proof-drift")
            .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase30-drift")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase29-drift")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase31-drift")
            .with_extension("json");
    let tampered_phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase31-source-drift")
            .with_extension("json");
    let phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-statement-contract-phase32-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut manifest: llm_provable_computer::Phase31RecursiveCompressionDecodeBoundaryManifest =
        serde_json::from_str(&std::fs::read_to_string(&phase31_path).expect("phase31 json"))
            .expect("parse phase31 manifest");
    manifest.chain_start_boundary_commitment = "1".repeat(64);
    manifest.decode_boundary_bridge_commitment = String::new();
    manifest.decode_boundary_bridge_commitment =
        commit_phase31_recursive_compression_decode_boundary_manifest(&manifest)
            .expect("recommit tampered phase31");
    std::fs::write(
        &tampered_phase31_path,
        serde_json::to_vec_pretty(&manifest).expect("serialize tampered phase31"),
    )
    .expect("write tampered phase31");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-statement-contract")
        .arg("--input")
        .arg(&phase32_path)
        .arg("--manifest")
        .arg(&tampered_phase31_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "does not match the recomputed Phase 31 source manifest",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(tampered_phase31_path);
    let _ = std::fs::remove_file(phase32_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_compression_public_input_manifest() {
    let proof_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-proof").with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase30")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase29")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase31")
        .with_extension("json");
    let phase32_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase32")
        .with_extension("json");
    let phase33_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase33")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "manifest_version: {STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33}",
        )))
        .stdout(predicate::str::contains("verified_phase32_contract: true"));

    let phase33_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase33_path).expect("phase33 json"))
            .expect("phase33 value");
    validate_json_against_schema(
        &phase33_json,
        "spec/stwo-phase33-recursive-compression-public-input-manifest.schema.json",
    );
    assert_eq!(
        phase33_json
            .get("manifest_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_VERSION_PHASE33)
    );
    assert_eq!(
        phase33_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_PUBLIC_INPUT_MANIFEST_SCOPE_PHASE33)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-compression-public-input-manifest")
        .arg("--input")
        .arg(&phase33_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_manifest: true"));

    let mut verify_source = tvm_command();
    verify_source
        .arg("verify-stwo-recursive-compression-public-input-manifest")
        .arg("--input")
        .arg(&phase33_path)
        .arg("--contract")
        .arg(&phase32_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_source: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_public_input_manifest_rejects_tampered_commitment() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-proof-tamper")
        .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-phase30-tamper")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-phase29-tamper")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-phase31-tamper")
            .with_extension("json");
    let phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-phase32-tamper")
            .with_extension("json");
    let phase33_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-phase33-tamper")
            .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-commitment-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut phase33_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase33_path).expect("phase33 json"))
            .expect("phase33 value");
    phase33_json["recursive_public_inputs_commitment"] = serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&phase33_json).expect("serialize tampered phase33"),
    )
    .expect("write tampered phase33");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-public-input-manifest")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_public_input_manifest_rejects_source_drift() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-proof-drift")
        .with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase30-drift")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase29-drift")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase31-drift")
        .with_extension("json");
    let phase32_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase32-drift")
        .with_extension("json");
    let tampered_phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-public-input-phase32-source-drift")
            .with_extension("json");
    let phase33_path = unique_temp_dir("cli-stwo-recursive-compression-public-input-phase33-drift")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut contract: llm_provable_computer::Phase32RecursiveCompressionStatementContract =
        serde_json::from_str(&std::fs::read_to_string(&phase32_path).expect("phase32 json"))
            .expect("parse phase32 contract");
    contract.chain_start_boundary_commitment = "2".repeat(64);
    contract.recursive_statement_contract_commitment = String::new();
    contract.recursive_statement_contract_commitment =
        commit_phase32_recursive_compression_statement_contract(&contract)
            .expect("recommit tampered phase32");
    std::fs::write(
        &tampered_phase32_path,
        serde_json::to_vec_pretty(&contract).expect("serialize tampered phase32"),
    )
    .expect("write tampered phase32");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-public-input-manifest")
        .arg("--input")
        .arg(&phase33_path)
        .arg("--contract")
        .arg(&tampered_phase32_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "does not match the recomputed Phase 32 source contract",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(tampered_phase32_path);
    let _ = std::fs::remove_file(phase33_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_compression_shared_lookup_manifest() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-proof")
        .with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase30")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase29")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase31")
        .with_extension("json");
    let phase32_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase32")
        .with_extension("json");
    let phase33_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase33")
        .with_extension("json");
    let phase34_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase34")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "manifest_version: {STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34}",
        )))
        .stdout(predicate::str::contains(
            "verified_phase33_public_inputs: true",
        ))
        .stdout(predicate::str::contains("verified_phase30_envelopes: true"));

    let phase34_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase34_path).expect("phase34 json"))
            .expect("phase34 value");
    validate_json_against_schema(
        &phase34_json,
        "spec/stwo-phase34-recursive-compression-shared-lookup-manifest.schema.json",
    );
    assert_eq!(
        phase34_json
            .get("manifest_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_VERSION_PHASE34)
    );
    assert_eq!(
        phase34_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_SHARED_LOOKUP_MANIFEST_SCOPE_PHASE34)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--input")
        .arg(&phase34_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_manifest: true"));

    let mut verify_source = tvm_command();
    verify_source
        .arg("verify-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--input")
        .arg(&phase34_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_sources: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(phase34_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_shared_lookup_manifest_rejects_tampered_commitment() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-proof-tamper")
        .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase30-tamper")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase29-tamper")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase31-tamper")
            .with_extension("json");
    let phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase32-tamper")
            .with_extension("json");
    let phase33_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase33-tamper")
            .with_extension("json");
    let phase34_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase34-tamper")
            .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-commitment-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success();

    let mut phase34_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase34_path).expect("phase34 json"))
            .expect("phase34 value");
    phase34_json["shared_lookup_public_inputs_commitment"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&phase34_json).expect("serialize tampered phase34"),
    )
    .expect("write tampered phase34");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(phase34_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_shared_lookup_manifest_rejects_source_drift() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-proof-drift")
        .with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase30-drift")
            .with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase29-drift")
            .with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase31-drift")
            .with_extension("json");
    let phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase32-drift")
            .with_extension("json");
    let phase33_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase33-drift")
            .with_extension("json");
    let tampered_phase33_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase33-source-drift")
            .with_extension("json");
    let phase34_path =
        unique_temp_dir("cli-stwo-recursive-compression-shared-lookup-phase34-drift")
            .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success();

    let mut manifest: llm_provable_computer::Phase33RecursiveCompressionPublicInputManifest =
        serde_json::from_str(&std::fs::read_to_string(&phase33_path).expect("phase33 json"))
            .expect("parse phase33 manifest");
    manifest.phase30_step_envelopes_commitment = "2".repeat(64);
    manifest.recursive_public_inputs_commitment = String::new();
    manifest.recursive_public_inputs_commitment =
        commit_phase33_recursive_compression_public_input_manifest(&manifest)
            .expect("recommit tampered phase33");
    std::fs::write(
        &tampered_phase33_path,
        serde_json::to_vec_pretty(&manifest).expect("serialize tampered phase33"),
    )
    .expect("write tampered phase33");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--input")
        .arg(&phase34_path)
        .arg("--public-inputs")
        .arg(&tampered_phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires the Phase 33 step-envelope commitment to match the Phase 30 step-envelope commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(tampered_phase33_path);
    let _ = std::fs::remove_file(phase34_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_compression_target_manifest() {
    let proof_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-proof").with_extension("json");
    let phase30_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase30").with_extension("json");
    let phase29_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase29").with_extension("json");
    let phase31_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase31").with_extension("json");
    let phase32_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase32").with_extension("json");
    let phase33_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase33").with_extension("json");
    let phase34_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase34").with_extension("json");
    let phase35_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase35").with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success();

    let mut prepare_phase35 = tvm_command();
    prepare_phase35
        .arg("prepare-stwo-recursive-compression-target-manifest")
        .arg("--statement-contract")
        .arg(&phase32_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--shared-lookup")
        .arg(&phase34_path)
        .arg("-o")
        .arg(&phase35_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "manifest_version: {STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35}",
        )))
        .stdout(predicate::str::contains(
            "verified_phase32_statement_contract: true",
        ))
        .stdout(predicate::str::contains(
            "verified_phase33_public_inputs: true",
        ))
        .stdout(predicate::str::contains(
            "verified_phase34_shared_lookup: true",
        ));

    let phase35_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase35_path).expect("phase35 json"))
            .expect("phase35 value");
    validate_json_against_schema(
        &phase35_json,
        "spec/stwo-phase35-recursive-compression-target-manifest.schema.json",
    );
    assert_eq!(
        phase35_json
            .get("manifest_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_VERSION_PHASE35)
    );
    assert_eq!(
        phase35_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_COMPRESSION_TARGET_MANIFEST_SCOPE_PHASE35)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-compression-target-manifest")
        .arg("--input")
        .arg(&phase35_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_manifest: true"));

    let mut verify_source = tvm_command();
    verify_source
        .arg("verify-stwo-recursive-compression-target-manifest")
        .arg("--input")
        .arg(&phase35_path)
        .arg("--statement-contract")
        .arg(&phase32_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--shared-lookup")
        .arg(&phase34_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_sources: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(phase34_path);
    let _ = std::fs::remove_file(phase35_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_target_manifest_rejects_tampered_commitment() {
    let proof_path = unique_temp_dir("cli-stwo-recursive-compression-target-proof-tamper")
        .with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase30-tamper")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase29-tamper")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase31-tamper")
        .with_extension("json");
    let phase32_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase32-tamper")
        .with_extension("json");
    let phase33_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase33-tamper")
        .with_extension("json");
    let phase34_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase34-tamper")
        .with_extension("json");
    let phase35_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase35-tamper")
        .with_extension("json");
    let tampered_path = unique_temp_dir("cli-stwo-recursive-compression-target-commitment-drift")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success();

    let mut prepare_phase35 = tvm_command();
    prepare_phase35
        .arg("prepare-stwo-recursive-compression-target-manifest")
        .arg("--statement-contract")
        .arg(&phase32_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--shared-lookup")
        .arg(&phase34_path)
        .arg("-o")
        .arg(&phase35_path)
        .assert()
        .success();

    let mut phase35_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase35_path).expect("phase35 json"))
            .expect("phase35 value");
    phase35_json["recursive_target_manifest_commitment"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&phase35_json).expect("serialize tampered phase35"),
    )
    .expect("write tampered phase35");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-target-manifest")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(phase34_path);
    let _ = std::fs::remove_file(phase35_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_compression_target_manifest_rejects_source_drift() {
    let proof_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-proof-drift").with_extension("json");
    let phase30_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase30-drift")
        .with_extension("json");
    let phase29_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase29-drift")
        .with_extension("json");
    let phase31_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase31-drift")
        .with_extension("json");
    let phase32_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase32-drift")
        .with_extension("json");
    let phase33_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase33-drift")
        .with_extension("json");
    let phase34_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase34-drift")
        .with_extension("json");
    let tampered_phase34_path =
        unique_temp_dir("cli-stwo-recursive-compression-target-phase34-source-drift")
            .with_extension("json");
    let phase35_path = unique_temp_dir("cli-stwo-recursive-compression-target-phase35-drift")
        .with_extension("json");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-decoding-family-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success();

    let mut prepare_phase30 = tvm_command();
    prepare_phase30
        .arg("prepare-stwo-decoding-step-envelope-manifest")
        .arg("--proof")
        .arg(&proof_path)
        .arg("-o")
        .arg(&phase30_path)
        .assert()
        .success();

    let phase30_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase30_path).expect("phase30 json"))
            .expect("phase30 value");
    let phase29 = sample_phase29_contract_matched_to_phase30_manifest(&phase30_json);
    std::fs::write(
        &phase29_path,
        serde_json::to_vec_pretty(&phase29).expect("serialize phase29"),
    )
    .expect("write phase29");

    let mut prepare_phase31 = tvm_command();
    prepare_phase31
        .arg("prepare-stwo-recursive-compression-decode-boundary-manifest")
        .arg("--contract")
        .arg(&phase29_path)
        .arg("--manifest")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase31_path)
        .assert()
        .success();

    let mut prepare_phase32 = tvm_command();
    prepare_phase32
        .arg("prepare-stwo-recursive-compression-statement-contract")
        .arg("--manifest")
        .arg(&phase31_path)
        .arg("-o")
        .arg(&phase32_path)
        .assert()
        .success();

    let mut prepare_phase33 = tvm_command();
    prepare_phase33
        .arg("prepare-stwo-recursive-compression-public-input-manifest")
        .arg("--contract")
        .arg(&phase32_path)
        .arg("-o")
        .arg(&phase33_path)
        .assert()
        .success();

    let mut prepare_phase34 = tvm_command();
    prepare_phase34
        .arg("prepare-stwo-recursive-compression-shared-lookup-manifest")
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--envelopes")
        .arg(&phase30_path)
        .arg("-o")
        .arg(&phase34_path)
        .assert()
        .success();

    let mut prepare_phase35 = tvm_command();
    prepare_phase35
        .arg("prepare-stwo-recursive-compression-target-manifest")
        .arg("--statement-contract")
        .arg(&phase32_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--shared-lookup")
        .arg(&phase34_path)
        .arg("-o")
        .arg(&phase35_path)
        .assert()
        .success();

    let mut manifest: llm_provable_computer::Phase34RecursiveCompressionSharedLookupManifest =
        serde_json::from_str(&std::fs::read_to_string(&phase34_path).expect("phase34 json"))
            .expect("parse phase34 manifest");
    manifest.phase33_recursive_public_inputs_commitment = "3".repeat(64);
    manifest.shared_lookup_public_inputs_commitment = String::new();
    manifest.shared_lookup_public_inputs_commitment =
        llm_provable_computer::commit_phase34_recursive_compression_shared_lookup_manifest(
            &manifest,
        )
        .expect("recommit tampered phase34");
    std::fs::write(
        &tampered_phase34_path,
        serde_json::to_vec_pretty(&manifest).expect("serialize tampered phase34"),
    )
    .expect("write tampered phase34");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-compression-target-manifest")
        .arg("--input")
        .arg(&phase35_path)
        .arg("--statement-contract")
        .arg(&phase32_path)
        .arg("--public-inputs")
        .arg(&phase33_path)
        .arg("--shared-lookup")
        .arg(&tampered_phase34_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires the Phase 34 public-input commitment to match the Phase 33 public-input commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(phase30_path);
    let _ = std::fs::remove_file(phase29_path);
    let _ = std::fs::remove_file(phase31_path);
    let _ = std::fs::remove_file(phase32_path);
    let _ = std::fs::remove_file(phase33_path);
    let _ = std::fs::remove_file(phase34_path);
    let _ = std::fs::remove_file(tampered_phase34_path);
    let _ = std::fs::remove_file(phase35_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_verifier_harness_receipt() {
    let fixture = prepare_phase35_recursive_compression_cli_fixture(
        "cli-stwo-recursive-verifier-harness-receipt",
    );
    let phase36_path = unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-phase36")
        .with_extension("json");

    let mut prepare_phase36 = tvm_command();
    prepare_phase36
        .arg("prepare-stwo-recursive-verifier-harness-receipt")
        .arg("--target")
        .arg(&fixture.phase35_path)
        .arg("--statement-contract")
        .arg(&fixture.phase32_path)
        .arg("--public-inputs")
        .arg(&fixture.phase33_path)
        .arg("--shared-lookup")
        .arg(&fixture.phase34_path)
        .arg("-o")
        .arg(&phase36_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "receipt_version: {STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36}",
        )))
        .stdout(predicate::str::contains("verified_phase35_target: true"))
        .stdout(predicate::str::contains("verified_source_binding: true"));

    let phase36_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase36_path).expect("phase36 json"))
            .expect("phase36 value");
    validate_json_against_schema(
        &phase36_json,
        "spec/stwo-phase36-recursive-verifier-harness-receipt.schema.json",
    );
    assert_eq!(
        phase36_json
            .get("receipt_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_VERSION_PHASE36)
    );
    assert_eq!(
        phase36_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_VERIFIER_HARNESS_RECEIPT_SCOPE_PHASE36)
    );
    assert_eq!(
        phase36_json
            .get("recursive_verification_claimed")
            .and_then(serde_json::Value::as_bool),
        Some(false)
    );
    assert_eq!(
        phase36_json
            .get("cryptographic_compression_claimed")
            .and_then(serde_json::Value::as_bool),
        Some(false)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-verifier-harness-receipt")
        .arg("--input")
        .arg(&phase36_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_receipt: true"));

    let mut verify_source = tvm_command();
    verify_source
        .arg("verify-stwo-recursive-verifier-harness-receipt")
        .arg("--input")
        .arg(&phase36_path)
        .arg("--target")
        .arg(&fixture.phase35_path)
        .arg("--statement-contract")
        .arg(&fixture.phase32_path)
        .arg("--public-inputs")
        .arg(&fixture.phase33_path)
        .arg("--shared-lookup")
        .arg(&fixture.phase34_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_sources: true"));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase36_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_verifier_harness_receipt_rejects_tampered_commitment() {
    let fixture = prepare_phase35_recursive_compression_cli_fixture(
        "cli-stwo-recursive-verifier-harness-receipt-tamper",
    );
    let phase36_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-phase36-tamper")
            .with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-commitment-drift")
            .with_extension("json");

    let mut prepare_phase36 = tvm_command();
    prepare_phase36
        .arg("prepare-stwo-recursive-verifier-harness-receipt")
        .arg("--target")
        .arg(&fixture.phase35_path)
        .arg("--statement-contract")
        .arg(&fixture.phase32_path)
        .arg("--public-inputs")
        .arg(&fixture.phase33_path)
        .arg("--shared-lookup")
        .arg(&fixture.phase34_path)
        .arg("-o")
        .arg(&phase36_path)
        .assert()
        .success();

    let mut phase36_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase36_path).expect("phase36 json"))
            .expect("phase36 value");
    phase36_json["recursive_verifier_harness_receipt_commitment"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&phase36_json).expect("serialize tampered phase36"),
    )
    .expect("write tampered phase36");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-verifier-harness-receipt")
        .arg("--input")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("does not match recomputed"));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase36_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_verifier_harness_receipt_rejects_source_drift() {
    let fixture = prepare_phase35_recursive_compression_cli_fixture(
        "cli-stwo-recursive-verifier-harness-receipt-drift",
    );
    let phase36_path = unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-phase36-drift")
        .with_extension("json");
    let tampered_phase35_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-target-source-drift")
            .with_extension("json");

    let mut prepare_phase36 = tvm_command();
    prepare_phase36
        .arg("prepare-stwo-recursive-verifier-harness-receipt")
        .arg("--target")
        .arg(&fixture.phase35_path)
        .arg("--statement-contract")
        .arg(&fixture.phase32_path)
        .arg("--public-inputs")
        .arg(&fixture.phase33_path)
        .arg("--shared-lookup")
        .arg(&fixture.phase34_path)
        .arg("-o")
        .arg(&phase36_path)
        .assert()
        .success();

    let mut manifest: llm_provable_computer::Phase35RecursiveCompressionTargetManifest =
        serde_json::from_str(
            &std::fs::read_to_string(&fixture.phase35_path).expect("phase35 json"),
        )
        .expect("parse phase35 manifest");
    manifest.phase30_source_chain_commitment = "5".repeat(64);
    manifest.recursive_target_manifest_commitment = String::new();
    manifest.recursive_target_manifest_commitment =
        llm_provable_computer::commit_phase35_recursive_compression_target_manifest(&manifest)
            .expect("recommit tampered phase35");
    std::fs::write(
        &tampered_phase35_path,
        serde_json::to_vec_pretty(&manifest).expect("serialize tampered phase35"),
    )
    .expect("write tampered phase35");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-verifier-harness-receipt")
        .arg("--input")
        .arg(&phase36_path)
        .arg("--target")
        .arg(&tampered_phase35_path)
        .arg("--statement-contract")
        .arg(&fixture.phase32_path)
        .arg("--public-inputs")
        .arg(&fixture.phase33_path)
        .arg("--shared-lookup")
        .arg(&fixture.phase34_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "Phase 35 recursive-compression target manifest does not match the recomputed Phase 32 + Phase 33 + Phase 34 source artifacts",
        ));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase36_path);
    let _ = std::fs::remove_file(tampered_phase35_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prepare_stwo_recursive_verifier_harness_receipt_rejects_gzip_output_path() {
    let target_path = unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-gzip-target")
        .with_extension("json");
    let statement_contract_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-gzip-statement")
            .with_extension("json");
    let public_inputs_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-gzip-public")
            .with_extension("json");
    let shared_lookup_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-gzip-shared")
            .with_extension("json");
    let output_path = unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-gzip-output")
        .with_extension("json.gz");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-recursive-verifier-harness-receipt")
        .arg("--target")
        .arg(&target_path)
        .arg("--statement-contract")
        .arg(&statement_contract_path)
        .arg("--public-inputs")
        .arg(&public_inputs_path)
        .arg("--shared-lookup")
        .arg(&shared_lookup_path)
        .arg("-o")
        .arg(&output_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "writes plain JSON; use a `.json` output path",
        ));
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_verifier_harness_receipt_requires_all_source_args() {
    let fixture = prepare_phase35_recursive_compression_cli_fixture(
        "cli-stwo-recursive-verifier-harness-receipt-partial-source",
    );
    let phase36_path =
        unique_temp_dir("cli-stwo-recursive-verifier-harness-receipt-partial-phase36")
            .with_extension("json");

    let mut prepare_phase36 = tvm_command();
    prepare_phase36
        .arg("prepare-stwo-recursive-verifier-harness-receipt")
        .arg("--target")
        .arg(&fixture.phase35_path)
        .arg("--statement-contract")
        .arg(&fixture.phase32_path)
        .arg("--public-inputs")
        .arg(&fixture.phase33_path)
        .arg("--shared-lookup")
        .arg(&fixture.phase34_path)
        .arg("-o")
        .arg(&phase36_path)
        .assert()
        .success();

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-verifier-harness-receipt")
        .arg("--input")
        .arg(&phase36_path)
        .arg("--target")
        .arg(&fixture.phase35_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires either all of --target, --statement-contract, --public-inputs, and --shared-lookup or none",
        ));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase36_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_can_prepare_and_verify_stwo_recursive_artifact_chain_harness_receipt() {
    let fixture =
        prepare_phase35_recursive_compression_cli_fixture("cli-stwo-recursive-artifact-chain");
    let phase37_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-phase37").with_extension("json");

    let mut prepare_phase37 = tvm_command();
    prepare_phase37
        .arg("prepare-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--contract")
        .arg(&fixture.phase29_path)
        .arg("--manifest")
        .arg(&fixture.phase30_path)
        .arg("-o")
        .arg(&phase37_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!(
            "receipt_version: {STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37}",
        )))
        .stdout(predicate::str::contains(format!(
            "semantic_scope: {STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37}",
        )))
        .stdout(predicate::str::contains(
            "verified_recursive_artifact_chain: true",
        ))
        .stdout(predicate::str::contains("source_binding_verified: true"));

    let phase37_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&phase37_path).expect("phase37 json"))
            .expect("phase37 value");
    validate_json_against_schema(
        &phase37_json,
        "spec/stwo-phase37-recursive-artifact-chain-harness-receipt.schema.json",
    );
    assert_eq!(
        phase37_json
            .get("receipt_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_VERSION_PHASE37)
    );
    assert_eq!(
        phase37_json
            .get("semantic_scope")
            .and_then(serde_json::Value::as_str),
        Some(STWO_RECURSIVE_ARTIFACT_CHAIN_HARNESS_RECEIPT_SCOPE_PHASE37)
    );
    assert_eq!(
        phase37_json
            .get("recursive_verification_claimed")
            .and_then(serde_json::Value::as_bool),
        Some(false)
    );
    assert_eq!(
        phase37_json
            .get("cryptographic_compression_claimed")
            .and_then(serde_json::Value::as_bool),
        Some(false)
    );
    assert_eq!(
        phase37_json
            .get("phase36_verifier_harness_receipt_verified")
            .and_then(serde_json::Value::as_bool),
        Some(true)
    );

    let mut verify_standalone = tvm_command();
    verify_standalone
        .arg("verify-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--input")
        .arg(&phase37_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_receipt: true"));

    let mut verify_source = tvm_command();
    verify_source
        .arg("verify-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--input")
        .arg(&phase37_path)
        .arg("--contract")
        .arg(&fixture.phase29_path)
        .arg("--manifest")
        .arg(&fixture.phase30_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_against_sources: true"));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase37_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_artifact_chain_harness_receipt_rejects_source_drift() {
    let fixture = prepare_phase35_recursive_compression_cli_fixture(
        "cli-stwo-recursive-artifact-chain-drift",
    );
    let phase37_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-phase37-drift").with_extension("json");
    let tampered_phase29_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-contract-drift").with_extension("json");

    let mut prepare_phase37 = tvm_command();
    prepare_phase37
        .arg("prepare-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--contract")
        .arg(&fixture.phase29_path)
        .arg("--manifest")
        .arg(&fixture.phase30_path)
        .arg("-o")
        .arg(&phase37_path)
        .assert()
        .success();

    let mut contract: Phase29RecursiveCompressionInputContract = serde_json::from_str(
        &std::fs::read_to_string(&fixture.phase29_path).expect("phase29 json"),
    )
    .expect("parse phase29 contract");
    contract.source_template_commitment = "9".repeat(64);
    contract.input_contract_commitment =
        commit_phase29_recursive_compression_input_contract(&contract)
            .expect("recommit tampered phase29 contract");
    std::fs::write(
        &tampered_phase29_path,
        serde_json::to_vec_pretty(&contract).expect("serialize tampered phase29"),
    )
    .expect("write tampered phase29");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--input")
        .arg(&phase37_path)
        .arg("--contract")
        .arg(&tampered_phase29_path)
        .arg("--manifest")
        .arg(&fixture.phase30_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "Phase 31 decode-boundary manifest requires Phase 29 global_start_state_commitment to match the Phase 30 chain_start_boundary_commitment",
        ).or(predicate::str::contains(
            "Phase 37 recursive artifact-chain harness receipt does not match the recomputed Phase 29 + Phase 30 source artifacts",
        )));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase37_path);
    let _ = std::fs::remove_file(tampered_phase29_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prepare_stwo_recursive_artifact_chain_harness_receipt_rejects_gzip_output_path() {
    let contract_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-gzip-contract").with_extension("json");
    let manifest_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-gzip-manifest").with_extension("json");
    let output_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-gzip-output").with_extension("json.gz");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--contract")
        .arg(&contract_path)
        .arg("--manifest")
        .arg(&manifest_path)
        .arg("-o")
        .arg(&output_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "writes plain JSON; use a `.json` output path",
        ));
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_recursive_artifact_chain_harness_receipt_requires_all_source_args() {
    let fixture = prepare_phase35_recursive_compression_cli_fixture(
        "cli-stwo-recursive-artifact-chain-partial-source",
    );
    let phase37_path =
        unique_temp_dir("cli-stwo-recursive-artifact-chain-partial-phase37").with_extension("json");

    let mut prepare_phase37 = tvm_command();
    prepare_phase37
        .arg("prepare-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--contract")
        .arg(&fixture.phase29_path)
        .arg("--manifest")
        .arg(&fixture.phase30_path)
        .arg("-o")
        .arg(&phase37_path)
        .assert()
        .success();

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-recursive-artifact-chain-harness-receipt")
        .arg("--input")
        .arg(&phase37_path)
        .arg("--contract")
        .arg(&fixture.phase29_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requires either both --contract and --manifest or neither",
        ));

    fixture.cleanup();
    let _ = std::fs::remove_file(phase37_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_prepare_stwo_recursive_compression_input_contract_rejects_gzip_output_path() {
    let phase28_path = unique_temp_dir("cli-stwo-recursive-compression-input-missing-phase28")
        .with_extension("json");
    std::fs::write(&phase28_path, b"{}").expect("write placeholder phase28");
    let contract_path =
        unique_temp_dir("cli-stwo-recursive-compression-input-contract").with_extension("json.gz");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-stwo-recursive-compression-input-contract")
        .arg("--phase28")
        .arg(&phase28_path)
        .arg("-o")
        .arg(&contract_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("writes plain JSON"))
        .stderr(predicate::str::contains("panicked at").not());

    let _ = std::fs::remove_file(phase28_path);
    let _ = std::fs::remove_file(contract_path);
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

#[cfg(not(all(feature = "burn-model", feature = "onnx-export")))]
#[test]
fn cli_reports_missing_features_for_research_v3_equivalence() {
    let output_path = unique_temp_dir("cli-research-v3-equivalence-missing").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v3-equivalence")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "`research-v3-equivalence` requires the `burn-model` and `onnx-export` features",
        ));

    assert!(!output_path.exists());

    let mut verify = tvm_command();
    verify
        .arg("verify-research-v3-equivalence")
        .arg(&output_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "`verify-research-v3-equivalence` requires the `burn-model` and `onnx-export` features",
        ));
}

#[cfg(all(feature = "burn-model", feature = "onnx-export"))]
#[test]
fn cli_research_v3_equivalence_rejects_max_steps_above_artifact_cap() {
    let output_path =
        unique_temp_dir("cli-research-v3-equivalence-over-cap").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v3-equivalence")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .arg("--max-steps")
        .arg("4097")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "--max-steps must be in 1..=4096 for research-v3-equivalence",
        ));

    assert!(!output_path.exists());
}

#[test]
fn cli_can_prepare_and_verify_hf_provenance_manifest() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-manifest");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let tokenizer_config = fixture_dir.join("tokenizer_config.json");
    let transcript = fixture_dir.join("tokenization-transcript.json");
    let safetensors = fixture_dir.join("model.safetensors");
    let onnx_model = fixture_dir.join("model.onnx");
    let model_card = fixture_dir.join("README.md");
    let attestation_statement = fixture_dir.join("release.attestation.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");
    std::fs::write(&tokenizer_config, br#"{"model_max_length":16}"#)
        .expect("write tokenizer config");
    std::fs::write(
        &transcript,
        br#"{"prompt":"hello","token_ids":[1,2],"tokens":["hello","world"]}"#,
    )
    .expect("write tokenization transcript");
    let safetensors_header = br#"{"weight":{"dtype":"F32","shape":[1],"data_offsets":[0,4]},"__metadata__":{"format":"pt"}}"#;
    let mut safetensors_bytes = Vec::new();
    safetensors_bytes.extend_from_slice(&(safetensors_header.len() as u64).to_le_bytes());
    safetensors_bytes.extend_from_slice(safetensors_header);
    safetensors_bytes.extend_from_slice(&[0, 0, 0, 0]);
    std::fs::write(&safetensors, safetensors_bytes).expect("write safetensors fixture");
    std::fs::write(&onnx_model, b"fake-onnx-graph").expect("write ONNX fixture");
    std::fs::write(
        &model_card,
        "# HF provenance fixture\n\nPinned for CLI manifest tests.\n",
    )
    .expect("write model card");
    write_hf_external_attestation_statement(
        &attestation_statement,
        &[
            tokenizer_json.as_path(),
            tokenizer_config.as_path(),
            transcript.as_path(),
            safetensors.as_path(),
            onnx_model.as_path(),
            model_card.as_path(),
        ],
        Some("https://github.com/example/workflows/release.yml@refs/tags/v1"),
        Some("build-123"),
    );

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .arg("--tokenizer-config")
        .arg(&tokenizer_config)
        .arg("--tokenization-transcript")
        .arg(&transcript)
        .arg("--safetensors")
        .arg(&safetensors)
        .arg("--onnx-model")
        .arg(&onnx_model)
        .arg("--onnx-exporter-version")
        .arg("optimum-test")
        .arg("--model-card")
        .arg(&model_card)
        .arg("--doi")
        .arg("10.57967/hf/example")
        .arg("--dataset")
        .arg("example/prompts")
        .arg("--note")
        .arg("fixture only")
        .arg("--attestation-builder-id")
        .arg("https://github.com/example/workflows/release.yml@refs/tags/v1")
        .arg("--attestation-build-invocation-id")
        .arg("build-123")
        .arg("--attestation-source-repository")
        .arg("omarespejel/provable-transformer-vm")
        .arg("--attestation-source-revision")
        .arg("45706ff0776fd2e5a36b22b4c3cb85533d0676c6")
        .arg("--external-attestation-statement")
        .arg(&attestation_statement)
        .assert()
        .success()
        .stdout(predicate::str::contains("hf_provenance_manifest:"))
        .stdout(predicate::str::contains("safetensors_files: 1"))
        .stdout(predicate::str::contains("attestation_subjects: 6"));

    let manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    #[cfg(feature = "onnx-export")]
    validate_json_against_schema(&manifest_json, "spec/hf-provenance-manifest.schema.json");
    assert_eq!(
        manifest_json
            .get("manifest_version")
            .and_then(serde_json::Value::as_str),
        Some("hf-provenance-manifest-v7")
    );
    assert_eq!(
        manifest_json["attestation"]["attestation_version"].as_str(),
        Some("hf-attestation-metadata-v1")
    );
    assert_eq!(
        manifest_json["attestation"]["builder_id"].as_str(),
        Some("https://github.com/example/workflows/release.yml@refs/tags/v1")
    );
    assert_eq!(
        manifest_json["attestation"]["build_invocation_id"].as_str(),
        Some("build-123")
    );
    assert_eq!(
        manifest_json["attestation"]["source_repository"].as_str(),
        Some("omarespejel/provable-transformer-vm")
    );
    assert_eq!(
        manifest_json["attestation"]["source_revision"].as_str(),
        Some("45706ff0776fd2e5a36b22b4c3cb85533d0676c6")
    );
    assert_eq!(
        manifest_json["attestation"]["subjects"]
            .as_array()
            .map(|subjects| subjects.len()),
        Some(6)
    );
    assert_eq!(
        manifest_json
            .get("commitment_hash_function")
            .and_then(serde_json::Value::as_str),
        Some("blake2b-256")
    );
    assert!(
        manifest_json["commitments"]["hub_binding_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.hub_binding_hash must be hex",
    );
    assert!(
        manifest_json["commitments"]["onnx_metadata_identity_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.onnx_metadata_identity_hash must be hex",
    );
    assert!(
        manifest_json["commitments"]["attestation_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.attestation_hash must be hex",
    );
    assert!(
        manifest_json["commitments"]["external_attestation_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.external_attestation_hash must be hex",
    );
    assert_eq!(
        manifest_json["external_attestation"]["identity"]["identity_version"].as_str(),
        Some("hf-external-attestation-identity-v1")
    );
    assert_eq!(
        manifest_json["external_attestation"]["identity"]["builder_id"].as_str(),
        Some("https://github.com/example/workflows/release.yml@refs/tags/v1")
    );
    assert_eq!(
        manifest_json["external_attestation"]["identity"]["build_invocation_id"].as_str(),
        Some("build-123")
    );
    assert!(manifest_json["onnx_export"]["metadata_identity"].is_null());
    assert_eq!(
        manifest_json
            .get("tokenizer")
            .and_then(|tokenizer| tokenizer.get("tokenizer_json"))
            .and_then(|value| value.get("sha256"))
            .and_then(serde_json::Value::as_str)
            .map(str::len),
        Some(64)
    );
    assert!(
        manifest_json["tokenizer"]["tokenizer_json"]["sha256"]
            .as_str()
            .is_some_and(|digest| digest.chars().all(|c| c.is_ascii_hexdigit())),
        "tokenizer.tokenizer_json.sha256 must be hex",
    );
    assert_eq!(
        manifest_json
            .get("safetensors")
            .and_then(serde_json::Value::as_array)
            .and_then(|files| files.first())
            .and_then(|file| file.get("tensor_count"))
            .and_then(serde_json::Value::as_u64),
        Some(1)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "verified_hf_provenance_manifest: true",
        ));

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[BAD]"}}"#,
    )
    .expect("tamper tokenizer json");
    let mut verify_tampered = tvm_command();
    verify_tampered
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "tokenizer_json blake2b_256 commitment mismatch",
        ));

    let floating_manifest = fixture_dir.join("floating.json");
    let mut floating = tvm_command();
    floating
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&floating_manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("main")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hub_revision must be pinned to an immutable commit or release tag",
        ));

    let branch_manifest = fixture_dir.join("branch-ref.json");
    let mut branch_ref = tvm_command();
    branch_ref
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&branch_manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("refs/heads/main")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hub_revision must be pinned to an immutable commit or release tag",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_hf_manifest_hub_binding_tamper() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-hub-binding-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .assert()
        .success();

    let base_manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    for (field, replacement) in [
        ("hub_revision", serde_json::json!("fedcba9876543210")),
        ("hub_repo", serde_json::json!("example/other-model")),
    ] {
        let mut manifest_json = base_manifest_json.clone();
        manifest_json[field] = replacement;
        std::fs::write(
            &manifest,
            serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
        )
        .expect("write tampered manifest");

        let mut verify = tvm_command();
        verify
            .arg("verify-hf-provenance-manifest")
            .arg(&manifest)
            .assert()
            .failure()
            .stderr(predicate::str::contains(
                "hf hub_binding_hash commitment mismatch",
            ));
    }

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_hf_manifest_sha256_tamper() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-sha256-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["tokenizer"]["tokenizer_json"]["sha256"] = serde_json::json!("0".repeat(64));
    manifest_json["commitments"]["tokenizer_hash"] = serde_json::Value::String(hash_json_value(
        manifest_json
            .get("tokenizer")
            .expect("tokenizer section after sha256 tamper"),
    ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "tokenizer_json sha256 commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_hf_manifest_model_card_sha256_tamper() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-model-card-sha256-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let model_card = fixture_dir.join("README.md");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");
    std::fs::write(&model_card, b"# Card\n").expect("write model card");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .arg("--model-card")
        .arg(&model_card)
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["release"]["model_card"]["sha256"] = serde_json::json!("0".repeat(64));
    manifest_json["commitments"]["release_metadata_hash"] =
        serde_json::Value::String(hash_json_value(
            manifest_json
                .get("release")
                .expect("release section after sha256 tamper"),
        ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "model_card sha256 commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_hf_manifest_safetensors_sha256_tamper() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-safetensors-sha256-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let safetensors = fixture_dir.join("model.safetensors");
    let manifest = fixture_dir.join("hf-provenance.json");

    let safetensors_header = br#"{"weight":{"dtype":"F32","shape":[1],"data_offsets":[0,4]},"__metadata__":{"format":"pt"}}"#;
    let mut safetensors_bytes = Vec::new();
    safetensors_bytes.extend_from_slice(&(safetensors_header.len() as u64).to_le_bytes());
    safetensors_bytes.extend_from_slice(safetensors_header);
    safetensors_bytes.extend_from_slice(&[0, 0, 0, 0]);
    std::fs::write(&safetensors, safetensors_bytes).expect("write safetensors fixture");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--safetensors")
        .arg(&safetensors)
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["safetensors"][0]["sha256"] = serde_json::json!("0".repeat(64));
    manifest_json["commitments"]["safetensors_manifest_hash"] =
        serde_json::Value::String(hash_json_value(
            manifest_json
                .get("safetensors")
                .expect("safetensors section after sha256 tamper"),
        ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains("HF provenance safetensors"))
        .stderr(predicate::str::contains("sha256 commitment mismatch"));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_legacy_hf_manifest_versions() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-legacy-v2");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .assert()
        .success();

    let base_manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    for (legacy_version, reason) in [
        (
            "hf-provenance-manifest-v1",
            "after the ONNX sidecar format bump",
        ),
        (
            "hf-provenance-manifest-v2",
            "after the attestation-digest format bump",
        ),
        (
            "hf-provenance-manifest-v3",
            "after the hub-binding hardening update",
        ),
        (
            "hf-provenance-manifest-v4",
            "after the ONNX metadata-identity hardening update",
        ),
    ] {
        let mut manifest_json = base_manifest_json.clone();
        manifest_json["manifest_version"] = serde_json::json!(legacy_version);
        if legacy_version == "hf-provenance-manifest-v3" {
            manifest_json["commitments"]
                .as_object_mut()
                .expect("commitments object")
                .remove("hub_binding_hash");
        }
        std::fs::write(
            &manifest,
            serde_json::to_vec_pretty(&manifest_json).expect("serialize legacy manifest"),
        )
        .expect("write legacy manifest");

        let mut verify = tvm_command();
        verify
            .arg("verify-hf-provenance-manifest")
            .arg(&manifest)
            .assert()
            .failure()
            .stderr(predicate::str::contains(format!(
                "legacy manifest_version `{legacy_version}` is no longer accepted",
            )))
            .stderr(predicate::str::contains(reason));
    }

    let _ = std::fs::remove_dir_all(fixture_dir);
}

fn hf_provenance_prepare_command(
    manifest: &std::path::Path,
    onnx_model: &std::path::Path,
    onnx_metadata: Option<&std::path::Path>,
    onnx_external_data: &[&std::path::Path],
) -> Command {
    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--onnx-model")
        .arg(onnx_model);
    if let Some(onnx_metadata) = onnx_metadata {
        prepare.arg("--onnx-metadata").arg(onnx_metadata);
    }
    for path in onnx_external_data {
        prepare.arg("--onnx-external-data").arg(path);
    }
    prepare
}

fn hf_provenance_export_valid_onnx_fixture(
    fixture_dir: &std::path::Path,
) -> (std::path::PathBuf, std::path::PathBuf) {
    let export_dir = fixture_dir.join("onnx-export");
    std::fs::create_dir_all(&export_dir).expect("create ONNX export fixture dir");
    let graph = export_dir.join("instr_0.onnx");
    let metadata = export_dir.join("metadata.json");
    std::fs::write(&graph, b"fake-onnx-graph").expect("write ONNX graph fixture");
    std::fs::write(
        &metadata,
        serde_json::to_vec_pretty(&serde_json::json!({
            "format_version": 1,
            "ir_version": 9,
            "opset_version": 19,
            "input_dim": 9,
            "output_dim": 7,
            "input_encoding": "operand-stack-v1",
            "output_encoding": "transition-v1",
            "input_layout": [
                {"index": 0, "name": "pc"},
                {"index": 1, "name": "sp"},
                {"index": 2, "name": "halted"}
            ],
            "output_layout": [
                "next_pc",
                "next_acc",
                "next_sp"
            ],
            "instructions": [
                {"opcode": "push", "value": 1},
                {"opcode": "push", "value": 2},
                {"opcode": "add"}
            ]
        }))
        .expect("serialize ONNX metadata fixture"),
    )
    .expect("write ONNX metadata fixture");
    (graph, metadata)
}

#[test]
fn cli_rejects_hf_provenance_manifest_when_onnx_metadata_reuses_graph_path() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-duplicate-metadata");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, _) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare = hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_model), &[]);
    prepare.assert().failure().stderr(predicate::str::contains(
        "onnx_export.metadata reuses the same underlying HF artifact",
    ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_rejects_hf_provenance_manifest_when_onnx_external_data_reuses_graph_path() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-duplicate-external-data");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, _) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare = hf_provenance_prepare_command(&manifest, &onnx_model, None, &[&onnx_model]);
    prepare.assert().failure().stderr(predicate::str::contains(
        "onnx_export.external_data_files[] reuses the same underlying HF artifact",
    ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_rejects_hf_provenance_manifest_when_onnx_exporter_version_has_no_graph() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-exporter-version-without-graph");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--onnx-exporter-version")
        .arg("1.17.0")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "ONNX metadata, exporter version, or external-data files require --onnx-model",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_rejects_hf_provenance_manifest_when_onnx_metadata_aliases_graph_path() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-alias-metadata");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, _) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let aliased_onnx_model = onnx_model
        .parent()
        .expect("onnx model parent")
        .join("./instr_0.onnx");
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&aliased_onnx_model), &[]);
    prepare.assert().failure().stderr(predicate::str::contains(
        "onnx_export.metadata reuses the same underlying HF artifact",
    ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_rejects_hf_provenance_manifest_when_model_card_reuses_tokenizer_json_path() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-duplicate-model-card");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let shared = fixture_dir.join("shared.json");
    let aliased_shared = fixture_dir.join("./shared.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &shared,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write shared fixture");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&shared)
        .arg("--model-card")
        .arg(&shared)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "model_card reuses the same underlying HF artifact",
        ));

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&shared)
        .arg("--model-card")
        .arg(&aliased_shared)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "model_card reuses the same underlying HF artifact",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_hf_manifest_emits_onnx_metadata_identity() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-metadata-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["identity_version"].as_str(),
        Some("onnx-program-metadata-identity-v1")
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["format_version"].as_u64(),
        Some(1)
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["ir_version"].as_u64(),
        Some(9)
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["opset_version"].as_u64(),
        Some(19)
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["input_dim"].as_u64(),
        Some(9)
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["output_dim"].as_u64(),
        Some(7)
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["input_encoding"].as_str(),
        Some("operand-stack-v1")
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["output_encoding"].as_str(),
        Some("transition-v1")
    );
    assert_eq!(
        manifest_json["onnx_export"]["metadata_identity"]["instruction_count"].as_u64(),
        Some(3),
        "instruction_count must match the deterministic ONNX metadata fixture",
    );
    assert_eq!(
        manifest_json["onnx_export"]["exporter_identity"]["identity_version"].as_str(),
        Some("onnx-exporter-identity-v1")
    );
    assert_eq!(
        manifest_json["onnx_export"]["exporter_identity"]["exporter"].as_str(),
        Some("optimum-onnx")
    );
    assert_eq!(
        manifest_json["onnx_export"]["graph_constraint_identity"]["identity_version"].as_str(),
        Some("onnx-graph-constraint-identity-v1")
    );
    assert_eq!(
        manifest_json["onnx_export"]["graph_constraint_identity"]["instruction_count"].as_u64(),
        Some(3)
    );
    assert!(
        manifest_json["onnx_export"]["graph_constraint_identity"]["input_layout_hash"]
            .as_str()
            .is_some_and(
                |digest| digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            )
    );
    assert!(
        manifest_json["onnx_export"]["graph_constraint_identity"]["output_layout_hash"]
            .as_str()
            .is_some_and(
                |digest| digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            )
    );
    assert!(
        manifest_json["onnx_export"]["graph_constraint_identity"]["instruction_table_hash"]
            .as_str()
            .is_some_and(
                |digest| digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            )
    );
    assert!(
        manifest_json["commitments"]["onnx_exporter_identity_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.onnx_exporter_identity_hash must be hex",
    );
    assert!(
        manifest_json["commitments"]["onnx_metadata_identity_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.onnx_metadata_identity_hash must be hex",
    );
    assert!(
        manifest_json["commitments"]["onnx_graph_constraint_identity_hash"]
            .as_str()
            .is_some_and(|digest| {
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit())
            }),
        "commitments.onnx_graph_constraint_identity_hash must be hex",
    );

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_hf_attestation_hash() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-attestation-hash-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .arg("--attestation-builder-id")
        .arg("https://github.com/example/workflows/release.yml@refs/tags/v1")
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]["attestation_hash"] = serde_json::json!("0".repeat(64));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf attestation_hash commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_hf_attestation_subjects() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-attestation-subjects-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["attestation"]["subjects"][0]["sha256"] = serde_json::json!("0".repeat(64));
    manifest_json["commitments"]["attestation_hash"] = serde_json::Value::String(hash_json_value(
        manifest_json
            .get("attestation")
            .expect("attestation section after tamper"),
    ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "HF provenance attestation.subjects do not match the bound local-file surface",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_hf_external_attestation_hash() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-external-attestation-hash-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let statement = fixture_dir.join("release.attestation.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");
    write_hf_external_attestation_statement(
        &statement,
        &[tokenizer_json.as_path()],
        Some("https://github.com/example/workflows/release.yml@refs/tags/v1"),
        Some("build-123"),
    );

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .arg("--external-attestation-statement")
        .arg(&statement)
        .assert()
        .success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]["external_attestation_hash"] = serde_json::json!("0".repeat(64));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf external_attestation_hash commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_hf_external_attestation_statement() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-external-attestation-statement-tamper");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let statement = fixture_dir.join("release.attestation.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");
    write_hf_external_attestation_statement(
        &statement,
        &[tokenizer_json.as_path()],
        Some("https://github.com/example/workflows/release.yml@refs/tags/v1"),
        Some("build-123"),
    );

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .arg("--external-attestation-statement")
        .arg(&statement)
        .assert()
        .success();

    write_hf_external_attestation_statement(
        &statement,
        &[tokenizer_json.as_path()],
        Some("https://github.com/example/workflows/release.yml@refs/tags/v2"),
        Some("build-123"),
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "HF provenance external_attestation.statement blake2b_256 commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_rejects_hf_external_attestation_builder_mismatch() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-external-attestation-builder-mismatch");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let tokenizer_json = fixture_dir.join("tokenizer.json");
    let statement = fixture_dir.join("release.attestation.json");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(
        &tokenizer_json,
        br#"{"version":"1.0","model":{"type":"WordPiece","unk_token":"[UNK]"}}"#,
    )
    .expect("write tokenizer json");
    write_hf_external_attestation_statement(
        &statement,
        &[tokenizer_json.as_path()],
        Some("https://github.com/example/workflows/release.yml@refs/tags/v1"),
        Some("build-123"),
    );

    let mut prepare = tvm_command();
    prepare
        .arg("prepare-hf-provenance-manifest")
        .arg("-o")
        .arg(&manifest)
        .arg("--hub-repo")
        .arg("example/test-model")
        .arg("--hub-revision")
        .arg("0123456789abcdef")
        .arg("--tokenizer-id")
        .arg("example/test-model")
        .arg("--tokenizer-json")
        .arg(&tokenizer_json)
        .arg("--attestation-builder-id")
        .arg("https://github.com/example/workflows/release.yml@refs/tags/v9")
        .arg("--external-attestation-statement")
        .arg(&statement)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf external_attestation.identity.builder_id mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_missing_onnx_exporter_identity_fields() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-missing-exporter-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["onnx_export"]
        .as_object_mut()
        .expect("onnx_export object")
        .remove("exporter_identity");
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "missing field `exporter_identity` in `onnx_export`",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_missing_onnx_metadata_identity_fields() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-missing-metadata-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["onnx_export"]
        .as_object_mut()
        .expect("onnx_export object")
        .remove("metadata_identity");
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "missing field `metadata_identity` in `onnx_export`",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_missing_onnx_graph_constraint_identity_fields() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-missing-graph-constraint-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["onnx_export"]
        .as_object_mut()
        .expect("onnx_export object")
        .remove("graph_constraint_identity");
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "missing field `graph_constraint_identity` in `onnx_export`",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_missing_onnx_exporter_identity_hash_field() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-missing-exporter-identity-hash");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]
        .as_object_mut()
        .expect("commitments object")
        .remove("onnx_exporter_identity_hash");
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "missing field `onnx_exporter_identity_hash` in `commitments`",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_missing_onnx_metadata_identity_hash_field() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-missing-metadata-identity-hash");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]
        .as_object_mut()
        .expect("commitments object")
        .remove("onnx_metadata_identity_hash");
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "missing field `onnx_metadata_identity_hash` in `commitments`",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_missing_onnx_graph_constraint_identity_hash_field() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-missing-graph-constraint-identity-hash");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]
        .as_object_mut()
        .expect("commitments object")
        .remove("onnx_graph_constraint_identity_hash");
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "missing field `onnx_graph_constraint_identity_hash` in `commitments`",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_stale_onnx_exporter_identity_hash() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-stale-exporter-identity-hash");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]["onnx_exporter_identity_hash"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf onnx_exporter_identity_hash commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_stale_onnx_metadata_identity_hash() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-stale-metadata-identity-hash");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]["onnx_metadata_identity_hash"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf onnx_metadata_identity_hash commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_stale_onnx_graph_constraint_identity_hash() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-stale-graph-constraint-identity-hash");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["commitments"]["onnx_graph_constraint_identity_hash"] =
        serde_json::Value::String("0".repeat(64));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf onnx_graph_constraint_identity_hash commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_hf_manifest_rejects_negative_onnx_versions() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-negative-onnx-version");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut metadata_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&onnx_metadata).expect("metadata bytes"))
            .expect("metadata json");
    metadata_json["ir_version"] = serde_json::json!(-1);
    std::fs::write(
        &onnx_metadata,
        serde_json::to_vec_pretty(&metadata_json).expect("serialize tampered ONNX metadata"),
    )
    .expect("write tampered ONNX metadata");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().failure().stderr(predicate::str::contains(
        "field `ir_version` must be non-negative",
    ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_hf_manifest_rejects_negative_onnx_format_version() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-negative-onnx-format-version");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut metadata_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&onnx_metadata).expect("metadata bytes"))
            .expect("metadata json");
    metadata_json["format_version"] = serde_json::json!(-1);
    std::fs::write(
        &onnx_metadata,
        serde_json::to_vec_pretty(&metadata_json).expect("serialize tampered ONNX metadata"),
    )
    .expect("write tampered ONNX metadata");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().failure().stderr(predicate::str::contains(
        "field `format_version` must be non-negative",
    ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_hf_manifest_rejects_malformed_onnx_integer_metadata_fields() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-malformed-onnx-integer-fields");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let manifest = fixture_dir.join("hf-provenance.json");

    for field in ["format_version", "ir_version", "input_dim"] {
        let case_dir = fixture_dir.join(field);
        std::fs::create_dir_all(&case_dir).expect("create malformed integer case dir");
        let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&case_dir);

        let mut metadata_json: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&onnx_metadata).expect("metadata bytes"))
                .expect("metadata json");
        metadata_json[field] = serde_json::json!("not-an-integer");
        std::fs::write(
            &onnx_metadata,
            serde_json::to_vec_pretty(&metadata_json).expect("serialize tampered ONNX metadata"),
        )
        .expect("write tampered ONNX metadata");

        let mut prepare =
            hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
        prepare
            .assert()
            .failure()
            .stderr(predicate::str::contains(format!(
                "field `{field}` malformed: expected integer"
            )));
    }

    for field in ["format_version", "ir_version", "input_dim"] {
        let case_dir = fixture_dir.join(format!("{field}-fractional"));
        std::fs::create_dir_all(&case_dir).expect("create fractional integer case dir");
        let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&case_dir);

        let mut metadata_json: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&onnx_metadata).expect("metadata bytes"))
                .expect("metadata json");
        metadata_json[field] = serde_json::json!(1.5);
        std::fs::write(
            &onnx_metadata,
            serde_json::to_vec_pretty(&metadata_json).expect("serialize tampered ONNX metadata"),
        )
        .expect("write tampered ONNX metadata");

        let mut prepare =
            hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
        prepare
            .assert()
            .failure()
            .stderr(predicate::str::contains(format!(
                "field `{field}` malformed: expected non-negative integer"
            )));
    }

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_hf_manifest_rejects_empty_onnx_string_metadata_fields() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-empty-onnx-string-fields");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let manifest = fixture_dir.join("hf-provenance.json");

    for field in ["input_encoding", "output_encoding"] {
        let case_dir = fixture_dir.join(field);
        std::fs::create_dir_all(&case_dir).expect("create empty string case dir");
        let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&case_dir);

        let mut metadata_json: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&onnx_metadata).expect("metadata bytes"))
                .expect("metadata json");
        metadata_json[field] = serde_json::json!("");
        std::fs::write(
            &onnx_metadata,
            serde_json::to_vec_pretty(&metadata_json).expect("serialize tampered ONNX metadata"),
        )
        .expect("write tampered ONNX metadata");

        let mut prepare =
            hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
        prepare
            .assert()
            .failure()
            .stderr(predicate::str::contains(format!(
                "missing string field `{field}`"
            )));
    }

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_prepare_hf_manifest_rejects_oversized_onnx_metadata_json() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-oversized-onnx-metadata");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(&onnx_metadata, vec![b'0'; 8 * 1024 * 1024 + 1])
        .expect("write oversized ONNX metadata");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare
        .assert()
        .failure()
        .stderr(predicate::str::contains("HF provenance ONNX metadata"))
        .stderr(predicate::str::contains(
            "exceeding the limit of 8388608 bytes",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_onnx_metadata() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-tampered-metadata");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let onnx_external = fixture_dir.join("model.onnx_data");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(&onnx_external, b"onnx-external-data").expect("write ONNX external data");

    let mut prepare = hf_provenance_prepare_command(
        &manifest,
        &onnx_model,
        Some(&onnx_metadata),
        &[&onnx_external],
    );
    prepare.assert().success();

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .success();

    let mut metadata_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&onnx_metadata).expect("metadata bytes"))
            .expect("metadata json");
    metadata_json["output_encoding"] = serde_json::json!("transition-v2");
    std::fs::write(
        &onnx_metadata,
        serde_json::to_vec_pretty(&metadata_json).expect("serialize tampered ONNX metadata"),
    )
    .expect("tamper ONNX metadata");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "onnx_export.metadata blake2b_256 commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_onnx_exporter_identity() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-tampered-exporter-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["onnx_export"]["exporter_identity"]["exporter"] =
        serde_json::json!("different-exporter");
    manifest_json["commitments"]["onnx_exporter_identity_hash"] =
        serde_json::Value::String(hash_json_value(
            manifest_json
                .get("onnx_export")
                .and_then(|value| value.get("exporter_identity"))
                .expect("exporter identity value"),
        ));
    manifest_json["commitments"]["onnx_export_hash"] = serde_json::Value::String(hash_json_value(
        manifest_json
            .get("onnx_export")
            .expect("onnx export section after exporter identity tamper"),
    ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf onnx_export.exporter_identity mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_onnx_metadata_identity() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-tampered-metadata-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["onnx_export"]["metadata_identity"]["instruction_count"] = serde_json::json!(999);
    manifest_json["commitments"]["onnx_metadata_identity_hash"] =
        serde_json::Value::String(hash_json_value(
            manifest_json
                .get("onnx_export")
                .and_then(|value| value.get("metadata_identity"))
                .expect("metadata identity value"),
        ));
    manifest_json["commitments"]["onnx_export_hash"] = serde_json::Value::String(hash_json_value(
        manifest_json
            .get("onnx_export")
            .expect("onnx export section after metadata identity tamper"),
    ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf onnx_export.metadata_identity mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_onnx_graph_constraint_identity() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-tampered-graph-constraint-identity");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let manifest = fixture_dir.join("hf-provenance.json");

    let mut prepare =
        hf_provenance_prepare_command(&manifest, &onnx_model, Some(&onnx_metadata), &[]);
    prepare.assert().success();

    let mut manifest_json: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&manifest).expect("manifest bytes"))
            .expect("manifest json");
    manifest_json["onnx_export"]["graph_constraint_identity"]["instruction_count"] =
        serde_json::json!(999);
    manifest_json["commitments"]["onnx_graph_constraint_identity_hash"] =
        serde_json::Value::String(hash_json_value(
            manifest_json
                .get("onnx_export")
                .and_then(|value| value.get("graph_constraint_identity"))
                .expect("graph constraint identity value"),
        ));
    manifest_json["commitments"]["onnx_export_hash"] = serde_json::Value::String(hash_json_value(
        manifest_json
            .get("onnx_export")
            .expect("onnx export section after graph constraint tamper"),
    ));
    std::fs::write(
        &manifest,
        serde_json::to_vec_pretty(&manifest_json).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "hf onnx_export.graph_constraint_identity mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
}

#[test]
fn cli_verifier_rejects_tampered_onnx_external_data() {
    let fixture_dir = unique_temp_dir("cli-hf-provenance-tampered-external");
    std::fs::create_dir_all(&fixture_dir).expect("create HF provenance fixture dir");
    let (onnx_model, onnx_metadata) = hf_provenance_export_valid_onnx_fixture(&fixture_dir);
    let onnx_external = fixture_dir.join("model.onnx_data");
    let manifest = fixture_dir.join("hf-provenance.json");

    std::fs::write(&onnx_external, b"onnx-external-data").expect("write ONNX external data");

    let mut prepare = hf_provenance_prepare_command(
        &manifest,
        &onnx_model,
        Some(&onnx_metadata),
        &[&onnx_external],
    );
    prepare.assert().success();

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .success();

    std::fs::write(&onnx_external, b"tampered-external!").expect("tamper ONNX external data");

    let mut verify = tvm_command();
    verify
        .arg("verify-hf-provenance-manifest")
        .arg(&manifest)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "onnx_export.external_data_files[] blake2b_256 commitment mismatch",
        ));

    let _ = std::fs::remove_dir_all(fixture_dir);
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
fn cli_supports_research_v3_equivalence_command() {
    let output_path = unique_temp_dir("cli-research-v3-equivalence").with_extension("json");
    let tampered_path =
        unique_temp_dir("cli-research-v3-equivalence-tampered").with_extension("json");
    let state_mismatch_path =
        unique_temp_dir("cli-research-v3-equivalence-state-mismatch").with_extension("json");
    let trace_hash_path =
        unique_temp_dir("cli-research-v3-equivalence-trace-hash").with_extension("json");
    let canonical_event_path =
        unique_temp_dir("cli-research-v3-equivalence-canonical-event").with_extension("json");
    let unexpected_engine_path =
        unique_temp_dir("cli-research-v3-equivalence-unexpected-engine").with_extension("json");
    let missing_engine_path =
        unique_temp_dir("cli-research-v3-equivalence-missing-engine").with_extension("json");
    let extra_event_path =
        unique_temp_dir("cli-research-v3-equivalence-extra-event").with_extension("json");
    let extra_trace_path =
        unique_temp_dir("cli-research-v3-equivalence-extra-trace").with_extension("json");
    let extra_lane_path =
        unique_temp_dir("cli-research-v3-equivalence-extra-lane").with_extension("json");
    let swapped_lane_path =
        unique_temp_dir("cli-research-v3-equivalence-swapped-lane").with_extension("json");
    let participating_engines_budget_path =
        unique_temp_dir("cli-research-v3-equivalence-participating-engines-budget")
            .with_extension("json");
    let witness_hash_budget_path =
        unique_temp_dir("cli-research-v3-equivalence-witness-hash-budget").with_extension("json");
    let step_budget_path =
        unique_temp_dir("cli-research-v3-equivalence-step-budget").with_extension("json");
    let requested_budget_path =
        unique_temp_dir("cli-research-v3-equivalence-requested-budget").with_extension("json");
    let trace_len_budget_path =
        unique_temp_dir("cli-research-v3-equivalence-trace-len-budget").with_extension("json");
    let events_len_budget_path =
        unique_temp_dir("cli-research-v3-equivalence-events-len-budget").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v3-equivalence")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .arg("--max-steps")
        .arg("8")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "semantic_scope: multi_engine_trace_equivalence_kernel_with_rule_witnesses",
        ))
        .stdout(predicate::str::contains(
            "relation_format: multi-engine-trace-relation-v1-no-egraph-no-smt",
        ))
        .stdout(predicate::str::contains(
            "engines: transformer,native,burn,onnx/tract",
        ));

    assert!(output_path.exists());
    let artifact_bytes = std::fs::read(&output_path).expect("artifact");
    let artifact_json: serde_json::Value =
        serde_json::from_slice(&artifact_bytes).expect("artifact json");
    validate_json_against_schema(
        &artifact_json,
        "spec/statement-v3-equivalence-kernel.schema.json",
    );
    assert_research_v2_spec_commitments(
        &artifact_json,
        "spec/statement-v3-equivalence-kernel-research.json",
        "spec/statement-v3-equivalence-kernel.schema.json",
    );
    assert_research_v3_runtime_commitments(&artifact_json);
    assert!(artifact_json.get("matched").is_none());
    let frontend_runtime_registry = artifact_json
        .get("frontend_runtime_semantics_registry")
        .expect("frontend runtime semantics registry");
    assert_eq!(
        frontend_runtime_registry
            .get("registry_version")
            .and_then(serde_json::Value::as_str),
        Some("frontend-runtime-semantics-registry-v1")
    );
    let expected_registry_lanes = std::collections::BTreeMap::from([
        ("transformer-vm", "implemented"),
        ("native-isa", "implemented"),
        ("burn", "implemented"),
        ("onnx-tract", "implemented"),
        ("torch-export", "research_watch"),
        ("executorch", "research_watch"),
        ("stablehlo", "research_watch"),
        ("iree", "research_watch"),
        ("onnx-mlir", "research_watch"),
        ("tvm-unity", "research_watch"),
        ("vllm", "research_watch"),
        ("sglang", "research_watch"),
        ("egg-emerge", "research_watch"),
    ]);
    assert_eq!(
        research_v3_registry_lane_statuses(frontend_runtime_registry),
        expected_registry_lanes,
        "frontend/runtime semantics registry lane boundary drifted"
    );
    assert_eq!(
        artifact_json
            .get("statement_version")
            .and_then(serde_json::Value::as_str),
        Some("statement-v3-research-draft")
    );
    assert_eq!(
        artifact_json
            .get("engines")
            .and_then(serde_json::Value::as_array)
            .map(Vec::len),
        Some(4)
    );
    let engine_names = artifact_json
        .get("engines")
        .and_then(serde_json::Value::as_array)
        .expect("engines")
        .iter()
        .map(|entry| {
            entry
                .get("name")
                .and_then(serde_json::Value::as_str)
                .expect("engine name")
        })
        .collect::<Vec<_>>();
    assert_eq!(
        engine_names,
        ["transformer", "native", "burn", "onnx/tract"]
    );
    for engine in artifact_json
        .get("engines")
        .and_then(serde_json::Value::as_array)
        .expect("engines")
    {
        let trace_len = engine
            .get("trace_len")
            .and_then(serde_json::Value::as_u64)
            .expect("trace_len") as usize;
        let events_len = engine
            .get("events_len")
            .and_then(serde_json::Value::as_u64)
            .expect("events_len") as usize;
        assert_eq!(
            engine
                .get("trace")
                .and_then(serde_json::Value::as_array)
                .map(Vec::len),
            Some(trace_len)
        );
        assert_eq!(
            engine
                .get("canonical_events")
                .and_then(serde_json::Value::as_array)
                .map(Vec::len),
            Some(events_len)
        );
        assert_eq!(trace_len, events_len + 1);
    }
    let mut verify = tvm_command();
    verify
        .arg("verify-research-v3-equivalence")
        .arg(&output_path)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "verified_research_v3_equivalence: true",
        ))
        .stdout(predicate::str::contains("rule_witnesses: 3"));

    let checked_steps = artifact_json
        .get("checked_steps")
        .and_then(serde_json::Value::as_u64)
        .expect("checked_steps") as usize;
    assert_eq!(
        artifact_json
            .get("rule_witnesses")
            .and_then(serde_json::Value::as_array)
            .map(Vec::len),
        Some(checked_steps)
    );
    let rule_witnesses = artifact_json
        .get("rule_witnesses")
        .and_then(serde_json::Value::as_array)
        .expect("rule_witnesses");
    let first_witness = rule_witnesses.first().expect("first rule witness");
    assert_eq!(
        first_witness
            .get("participating_engines")
            .and_then(serde_json::Value::as_array)
            .expect("participating engines")
            .iter()
            .map(|entry| entry.as_str().expect("engine name"))
            .collect::<Vec<_>>(),
        ["transformer", "native", "burn", "onnx/tract"]
    );
    for hashes_key in ["state_before_hashes", "state_after_hashes"] {
        let hashes = first_witness
            .get(hashes_key)
            .and_then(serde_json::Value::as_object)
            .expect("per-engine witness hashes");
        for engine_name in ["transformer", "native", "burn", "onnx/tract"] {
            let hash = hashes
                .get(engine_name)
                .and_then(serde_json::Value::as_str)
                .expect("per-engine state hash");
            assert_eq!(hash.len(), 64);
        }
    }
    let canonical_transition_hash = first_witness
        .get("canonical_transition_hash")
        .and_then(serde_json::Value::as_str)
        .expect("canonical transition hash");
    assert_eq!(canonical_transition_hash.len(), 64);
    let engine_transition_hashes = first_witness
        .get("engine_transition_hashes")
        .and_then(serde_json::Value::as_object)
        .expect("engine transition hashes");
    for engine_name in ["transformer", "native", "burn", "onnx/tract"] {
        let transition_hash = engine_transition_hashes
            .get(engine_name)
            .and_then(serde_json::Value::as_str)
            .expect("per-engine transition hash");
        assert_eq!(
            transition_hash, canonical_transition_hash,
            "transition relation hash drift for {engine_name}"
        );
    }
    let limitations = artifact_json
        .get("limitations")
        .and_then(serde_json::Value::as_array)
        .expect("limitations");
    for expected in [
        "Emerge reproduction",
        "e-graph saturation",
        "SMT-backed rewrite synthesis",
        "randomized opaque-kernel testing",
        "recursive accumulation",
        "cryptographic implementation-equivalence proof",
    ] {
        assert!(
            limitations
                .iter()
                .any(|entry| entry.as_str().is_some_and(|text| text.contains(expected))),
            "missing limitation covering {expected}",
        );
    }
    let mut tampered = artifact_json.clone();
    tampered["commitments"]["engine_summaries_hash"] = serde_json::Value::String("0".repeat(64));
    assert!(
        std::panic::catch_unwind(|| assert_research_v3_runtime_commitments(&tampered)).is_err()
    );
    let mut tampered_registry_hash = artifact_json.clone();
    tampered_registry_hash["commitments"]["frontend_runtime_semantics_registry_hash"] =
        serde_json::Value::String("0".repeat(64));
    assert!(std::panic::catch_unwind(|| {
        assert_research_v3_runtime_commitments(&tampered_registry_hash)
    })
    .is_err());
    let mut tampered_transition_hash = artifact_json.clone();
    tampered_transition_hash["rule_witnesses"][0]["engine_transition_hashes"]["native"] =
        serde_json::Value::String("0".repeat(64));
    assert!(std::panic::catch_unwind(|| {
        assert_research_v3_runtime_commitments(&tampered_transition_hash)
    })
    .is_err());
    tampered_transition_hash["commitments"]["rule_witnesses_hash"] =
        serde_json::Value::String(hash_json_value(
            tampered_transition_hash
                .get("rule_witnesses")
                .expect("tampered rule witnesses"),
        ));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&tampered_transition_hash).expect("tampered artifact json"),
    )
    .expect("write tampered artifact");
    let mut verify_tampered = tvm_command();
    verify_tampered
        .arg("verify-research-v3-equivalence")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "transition_hash commitment mismatch",
        ));

    let mut tampered_state_mismatch = artifact_json.clone();
    tampered_state_mismatch["rule_witnesses"][0]["state_after_hashes"]["native"] =
        serde_json::Value::String("1".repeat(64));
    tampered_state_mismatch["commitments"]["rule_witnesses_hash"] =
        serde_json::Value::String(hash_json_value(
            tampered_state_mismatch
                .get("rule_witnesses")
                .expect("tampered state mismatch rule witnesses"),
        ));
    std::fs::write(
        &state_mismatch_path,
        serde_json::to_vec(&tampered_state_mismatch)
            .expect("tampered state mismatch artifact json"),
    )
    .expect("write state mismatch artifact");
    let mut verify_state_mismatch = tvm_command();
    verify_state_mismatch
        .arg("verify-research-v3-equivalence")
        .arg(&state_mismatch_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "state_after_hash commitment mismatch",
        ));

    let mut tampered_trace_hash = artifact_json.clone();
    tampered_trace_hash["engines"][0]["trace_hash"] = serde_json::Value::String("2".repeat(64));
    tampered_trace_hash["commitments"]["engine_summaries_hash"] =
        serde_json::Value::String(hash_json_value(
            tampered_trace_hash
                .get("engines")
                .expect("tampered engines"),
        ));
    std::fs::write(
        &trace_hash_path,
        serde_json::to_vec(&tampered_trace_hash).expect("tampered trace hash artifact json"),
    )
    .expect("write trace hash artifact");
    let mut verify_trace_hash = tvm_command();
    verify_trace_hash
        .arg("verify-research-v3-equivalence")
        .arg(&trace_hash_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("trace_hash commitment mismatch"));

    let mut tampered_canonical_event = artifact_json.clone();
    tampered_canonical_event["engines"][0]["canonical_events"][0]["state_after_hash"] =
        serde_json::Value::String("3".repeat(64));
    tampered_canonical_event["engines"][0]["event_relation_hash"] =
        serde_json::Value::String(hash_json_value(
            tampered_canonical_event["engines"][0]
                .get("canonical_events")
                .expect("tampered canonical events"),
        ));
    tampered_canonical_event["commitments"]["engine_summaries_hash"] =
        serde_json::Value::String(hash_json_value(
            tampered_canonical_event
                .get("engines")
                .expect("tampered canonical event engines"),
        ));
    std::fs::write(
        &canonical_event_path,
        serde_json::to_vec(&tampered_canonical_event)
            .expect("tampered canonical event artifact json"),
    )
    .expect("write canonical event artifact");
    let mut verify_canonical_event = tvm_command();
    verify_canonical_event
        .arg("verify-research-v3-equivalence")
        .arg(&canonical_event_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "canonical event 1 state_after_hash commitment mismatch",
        ));

    let mut unexpected_engine = artifact_json.clone();
    unexpected_engine["engines"][3]["name"] =
        serde_json::Value::String("experimental-onnx".to_string());
    for witness in unexpected_engine["rule_witnesses"]
        .as_array_mut()
        .expect("rule_witnesses")
    {
        let participating_engines = witness["participating_engines"]
            .as_array_mut()
            .expect("participating engines");
        for engine_name in participating_engines {
            if engine_name.as_str() == Some("onnx/tract") {
                *engine_name = serde_json::Value::String("experimental-onnx".to_string());
            }
        }
        for object_key in [
            "state_before_hashes",
            "state_after_hashes",
            "engine_transition_hashes",
        ] {
            let hashes = witness[object_key]
                .as_object_mut()
                .expect("witness hash object");
            let value = hashes
                .remove("onnx/tract")
                .expect("onnx/tract witness hash entry");
            hashes.insert("experimental-onnx".to_string(), value);
        }
    }
    unexpected_engine["commitments"]["engine_summaries_hash"] =
        serde_json::Value::String(hash_json_value(
            unexpected_engine
                .get("engines")
                .expect("unexpected engines"),
        ));
    unexpected_engine["commitments"]["rule_witnesses_hash"] =
        serde_json::Value::String(hash_json_value(
            unexpected_engine
                .get("rule_witnesses")
                .expect("unexpected rule witnesses"),
        ));
    std::fs::write(
        &unexpected_engine_path,
        serde_json::to_vec(&unexpected_engine).expect("unexpected engine artifact json"),
    )
    .expect("write unexpected engine artifact");
    let mut verify_unexpected_engine = tvm_command();
    verify_unexpected_engine
        .arg("verify-research-v3-equivalence")
        .arg(&unexpected_engine_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "is not bound to a pinned implemented lane",
        ));

    let mut missing_engine = artifact_json.clone();
    missing_engine
        .get_mut("engines")
        .and_then(serde_json::Value::as_array_mut)
        .expect("engines")
        .retain(|engine| {
            engine.get("name").and_then(serde_json::Value::as_str) != Some("onnx/tract")
        });
    for witness in missing_engine["rule_witnesses"]
        .as_array_mut()
        .expect("rule_witnesses")
    {
        witness["participating_engines"]
            .as_array_mut()
            .expect("participating engines")
            .retain(|engine_name| engine_name.as_str() != Some("onnx/tract"));
        for object_key in [
            "state_before_hashes",
            "state_after_hashes",
            "engine_transition_hashes",
        ] {
            witness[object_key]
                .as_object_mut()
                .expect("witness hash object")
                .remove("onnx/tract");
        }
    }
    missing_engine["commitments"]["engine_summaries_hash"] = serde_json::Value::String(
        hash_json_value(missing_engine.get("engines").expect("missing engines")),
    );
    missing_engine["commitments"]["rule_witnesses_hash"] =
        serde_json::Value::String(hash_json_value(
            missing_engine
                .get("rule_witnesses")
                .expect("missing rule witnesses"),
        ));
    std::fs::write(
        &missing_engine_path,
        serde_json::to_vec(&missing_engine).expect("missing engine artifact json"),
    )
    .expect("write missing engine artifact");
    let mut verify_missing_engine = tvm_command();
    verify_missing_engine
        .arg("verify-research-v3-equivalence")
        .arg(&missing_engine_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "engine set does not match the pinned artifact boundary",
        ));

    let mut extra_event = artifact_json.clone();
    let extra_event_expected_steps = extra_event
        .get("checked_steps")
        .and_then(serde_json::Value::as_u64)
        .expect("checked_steps");
    for engine in extra_event["engines"].as_array_mut().expect("engines") {
        let final_state = engine
            .get("final_state")
            .cloned()
            .expect("engine final state");
        let final_state_hash = hash_json_value(&final_state);
        let next_step = engine["canonical_events"]
            .as_array()
            .map(|events| events.len() as u64 + 1)
            .expect("canonical events");
        engine["trace"]
            .as_array_mut()
            .expect("engine trace")
            .push(final_state);
        engine["canonical_events"]
            .as_array_mut()
            .expect("canonical events")
            .push(serde_json::json!({
                "step": next_step,
                "instruction": "NOP",
                "state_before_hash": final_state_hash.clone(),
                "state_after_hash": final_state_hash,
            }));
        let trace_len = engine["trace"]
            .as_array()
            .map(|trace| trace.len() as u64)
            .expect("trace");
        let events_len = engine["canonical_events"]
            .as_array()
            .map(|events| events.len() as u64)
            .expect("canonical events");
        engine["trace_len"] = serde_json::Value::from(trace_len);
        engine["events_len"] = serde_json::Value::from(events_len);
        engine["trace_hash"] =
            serde_json::Value::String(hash_json_value(engine.get("trace").expect("engine trace")));
        engine["event_relation_hash"] = serde_json::Value::String(hash_json_value(
            engine.get("canonical_events").expect("canonical events"),
        ));
        engine["final_state_hash"] = serde_json::Value::String(hash_json_value(
            engine.get("final_state").expect("final state"),
        ));
    }
    extra_event["commitments"]["engine_summaries_hash"] = serde_json::Value::String(
        hash_json_value(extra_event.get("engines").expect("extra-event engines")),
    );
    std::fs::write(
        &extra_event_path,
        serde_json::to_vec(&extra_event).expect("extra event artifact json"),
    )
    .expect("write extra event artifact");
    let mut verify_extra_event = tvm_command();
    verify_extra_event
        .arg("verify-research-v3-equivalence")
        .arg(&extra_event_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(format!(
            "events_len {} does not match checked_steps {}",
            extra_event_expected_steps + 1,
            extra_event_expected_steps
        )));

    let mut extra_trace = artifact_json.clone();
    let extra_trace_expected_steps = extra_trace
        .get("checked_steps")
        .and_then(serde_json::Value::as_u64)
        .expect("checked_steps");
    for engine in extra_trace["engines"].as_array_mut().expect("engines") {
        let final_state = engine
            .get("final_state")
            .cloned()
            .expect("engine final state");
        engine["trace"]
            .as_array_mut()
            .expect("engine trace")
            .push(final_state);
        let trace_len = engine["trace"]
            .as_array()
            .map(|trace| trace.len() as u64)
            .expect("trace");
        engine["trace_len"] = serde_json::Value::from(trace_len);
        engine["trace_hash"] =
            serde_json::Value::String(hash_json_value(engine.get("trace").expect("engine trace")));
    }
    extra_trace["commitments"]["engine_summaries_hash"] = serde_json::Value::String(
        hash_json_value(extra_trace.get("engines").expect("extra-trace engines")),
    );
    std::fs::write(
        &extra_trace_path,
        serde_json::to_vec(&extra_trace).expect("extra trace artifact json"),
    )
    .expect("write extra trace artifact");
    let mut verify_extra_trace = tvm_command();
    verify_extra_trace
        .arg("verify-research-v3-equivalence")
        .arg(&extra_trace_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(format!(
            "trace_len {} does not match checked_steps+1 {}",
            extra_trace_expected_steps + 2,
            extra_trace_expected_steps + 1
        )));

    let mut extra_lane = artifact_json.clone();
    let lanes = extra_lane["frontend_runtime_semantics_registry"]["lanes"]
        .as_array_mut()
        .expect("registry lanes");
    lanes.push(serde_json::json!({
        "lane_id": "surprise-watch",
        "ecosystem": "surprise",
        "role": "unexpected watch lane",
        "status": "research_watch",
        "artifact_binding": "No artifact binding in research-v3-equivalence.",
        "claim_boundary": "This lane must not drift into the pinned registry without an explicit update."
    }));
    extra_lane["commitments"]["frontend_runtime_semantics_registry_hash"] =
        serde_json::Value::String(hash_json_value(
            extra_lane
                .get("frontend_runtime_semantics_registry")
                .expect("extra lane registry"),
        ));
    std::fs::write(
        &extra_lane_path,
        serde_json::to_vec(&extra_lane).expect("extra lane artifact json"),
    )
    .expect("write extra lane artifact");
    let mut verify_extra_lane = tvm_command();
    verify_extra_lane
        .arg("verify-research-v3-equivalence")
        .arg(&extra_lane_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "frontend runtime semantics registry lane count 14 exceeds ingest cap 13",
        ));

    let mut swapped_lane = artifact_json.clone();
    let lanes = swapped_lane["frontend_runtime_semantics_registry"]["lanes"]
        .as_array_mut()
        .expect("registry lanes");
    let replaced_lane = lanes
        .iter_mut()
        .find(|lane| lane.get("lane_id").and_then(serde_json::Value::as_str) == Some("egg-emerge"))
        .expect("egg-emerge lane");
    *replaced_lane = serde_json::json!({
        "lane_id": "surprise-watch",
        "ecosystem": "surprise",
        "role": "unexpected watch lane",
        "status": "research_watch",
        "artifact_binding": "No artifact binding in research-v3-equivalence.",
        "claim_boundary": "This lane must not drift into the pinned registry without an explicit update."
    });
    swapped_lane["commitments"]["frontend_runtime_semantics_registry_hash"] =
        serde_json::Value::String(hash_json_value(
            swapped_lane
                .get("frontend_runtime_semantics_registry")
                .expect("swapped lane registry"),
        ));
    std::fs::write(
        &swapped_lane_path,
        serde_json::to_vec(&swapped_lane).expect("swapped lane artifact json"),
    )
    .expect("write swapped lane artifact");
    let mut verify_swapped_lane = tvm_command();
    verify_swapped_lane
        .arg("verify-research-v3-equivalence")
        .arg(&swapped_lane_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "frontend runtime semantics registry missing lane egg-emerge",
        ));

    let mut participating_engines_budget = artifact_json.clone();
    participating_engines_budget["rule_witnesses"][0]["participating_engines"]
        .as_array_mut()
        .expect("participating engines")
        .push(serde_json::Value::String("surprise-engine".to_string()));
    participating_engines_budget["commitments"]["rule_witnesses_hash"] =
        serde_json::Value::String(hash_json_value(
            participating_engines_budget
                .get("rule_witnesses")
                .expect("participating engines budget witnesses"),
        ));
    std::fs::write(
        &participating_engines_budget_path,
        serde_json::to_vec(&participating_engines_budget)
            .expect("participating engines budget artifact json"),
    )
    .expect("write participating engines budget artifact");
    let mut verify_participating_engines_budget = tvm_command();
    verify_participating_engines_budget
        .arg("verify-research-v3-equivalence")
        .arg(&participating_engines_budget_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "research-v3 witness 1 participating_engines length 5 exceeds ingest cap 4",
        ));

    for object_key in [
        "state_before_hashes",
        "state_after_hashes",
        "engine_transition_hashes",
    ] {
        let mut witness_hash_budget = artifact_json.clone();
        witness_hash_budget["rule_witnesses"][0][object_key]
            .as_object_mut()
            .expect("witness hash object")
            .insert(
                "surprise-engine".to_string(),
                serde_json::Value::String("0".repeat(64)),
            );
        witness_hash_budget["commitments"]["rule_witnesses_hash"] =
            serde_json::Value::String(hash_json_value(
                witness_hash_budget
                    .get("rule_witnesses")
                    .expect("witness hash budget witnesses"),
            ));
        std::fs::write(
            &witness_hash_budget_path,
            serde_json::to_vec(&witness_hash_budget).expect("witness hash budget artifact json"),
        )
        .expect("write witness hash budget artifact");
        let mut verify_witness_hash_budget = tvm_command();
        verify_witness_hash_budget
            .arg("verify-research-v3-equivalence")
            .arg(&witness_hash_budget_path)
            .assert()
            .failure()
            .stderr(predicate::str::contains(format!(
                "research-v3 witness 1 {object_key} length 5 exceeds ingest cap 4",
            )));
    }

    let mut step_budget = artifact_json.clone();
    step_budget["checked_steps"] = serde_json::Value::from(4097_u64);
    std::fs::write(
        &step_budget_path,
        serde_json::to_vec(&step_budget).expect("step budget artifact json"),
    )
    .expect("write step budget artifact");
    let mut verify_step_budget = tvm_command();
    verify_step_budget
        .arg("verify-research-v3-equivalence")
        .arg(&step_budget_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "checked_steps 4097 exceeds ingest cap 4096",
        ));

    let mut requested_budget = artifact_json.clone();
    requested_budget["requested_max_steps"] = serde_json::Value::from(4097_u64);
    std::fs::write(
        &requested_budget_path,
        serde_json::to_vec(&requested_budget).expect("requested budget artifact json"),
    )
    .expect("write requested budget artifact");
    let mut verify_requested_budget = tvm_command();
    verify_requested_budget
        .arg("verify-research-v3-equivalence")
        .arg(&requested_budget_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "requested_max_steps 4097 exceeds ingest cap 4096",
        ));

    let mut trace_len_budget = artifact_json.clone();
    trace_len_budget["engines"][0]["trace_len"] = serde_json::Value::from(4098_u64);
    trace_len_budget["commitments"]["engine_summaries_hash"] =
        serde_json::Value::String(hash_json_value(
            trace_len_budget
                .get("engines")
                .expect("trace len budget engines"),
        ));
    std::fs::write(
        &trace_len_budget_path,
        serde_json::to_vec(&trace_len_budget).expect("trace len budget artifact json"),
    )
    .expect("write trace len budget artifact");
    let mut verify_trace_len_budget = tvm_command();
    verify_trace_len_budget
        .arg("verify-research-v3-equivalence")
        .arg(&trace_len_budget_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "research-v3 engine transformer trace_len 4098 exceeds ingest cap 4097",
        ));

    let mut events_len_budget = artifact_json.clone();
    events_len_budget["engines"][0]["events_len"] = serde_json::Value::from(4097_u64);
    events_len_budget["commitments"]["engine_summaries_hash"] =
        serde_json::Value::String(hash_json_value(
            events_len_budget
                .get("engines")
                .expect("events len budget engines"),
        ));
    std::fs::write(
        &events_len_budget_path,
        serde_json::to_vec(&events_len_budget).expect("events len budget artifact json"),
    )
    .expect("write events len budget artifact");
    let mut verify_events_len_budget = tvm_command();
    verify_events_len_budget
        .arg("verify-research-v3-equivalence")
        .arg(&events_len_budget_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "research-v3 engine transformer events_len 4097 exceeds ingest cap 4096",
        ));

    let mut malformed_hash = artifact_json.clone();
    malformed_hash["commitments"]["relation_format_hash"] =
        serde_json::Value::String("not-a-blake2b-hash".to_string());
    malformed_hash["rule_witnesses"][0]["state_before_hashes"]["transformer"] =
        serde_json::Value::String("also-not-a-blake2b-hash".to_string());
    malformed_hash["rule_witnesses"][0]["engine_transition_hashes"]["native"] =
        serde_json::Value::String("not-a-transition-hash".to_string());
    assert!(std::panic::catch_unwind(|| {
        validate_json_against_schema(
            &malformed_hash,
            "spec/statement-v3-equivalence-kernel.schema.json",
        );
    })
    .is_err());

    let mut missing_relation = artifact_json.clone();
    missing_relation
        .as_object_mut()
        .expect("artifact object")
        .remove("relation_format");
    assert!(std::panic::catch_unwind(|| {
        validate_json_against_schema(
            &missing_relation,
            "spec/statement-v3-equivalence-kernel.schema.json",
        );
    })
    .is_err());

    let _ = std::fs::remove_file(output_path);
    let _ = std::fs::remove_file(tampered_path);
    let _ = std::fs::remove_file(state_mismatch_path);
    let _ = std::fs::remove_file(trace_hash_path);
    let _ = std::fs::remove_file(canonical_event_path);
    let _ = std::fs::remove_file(unexpected_engine_path);
    let _ = std::fs::remove_file(missing_engine_path);
    let _ = std::fs::remove_file(extra_event_path);
    let _ = std::fs::remove_file(extra_trace_path);
    let _ = std::fs::remove_file(extra_lane_path);
    let _ = std::fs::remove_file(swapped_lane_path);
    let _ = std::fs::remove_file(participating_engines_budget_path);
    let _ = std::fs::remove_file(witness_hash_budget_path);
    let _ = std::fs::remove_file(step_budget_path);
    let _ = std::fs::remove_file(requested_budget_path);
    let _ = std::fs::remove_file(trace_len_budget_path);
    let _ = std::fs::remove_file(events_len_budget_path);
}

#[cfg(all(feature = "burn-model", feature = "onnx-export"))]
#[test]
fn cli_research_v3_equivalence_rejects_zero_max_steps() {
    let output_path =
        unique_temp_dir("cli-research-v3-equivalence-zero-steps").with_extension("json");
    let mut command = tvm_command();
    command
        .arg("research-v3-equivalence")
        .arg("programs/addition.tvm")
        .arg("-o")
        .arg(&output_path)
        .arg("--max-steps")
        .arg("0")
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "--max-steps must be in 1..=4096 for research-v3-equivalence",
        ));

    assert!(!output_path.exists());
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

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_missing_file(
) {
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-missing",
    )
    .with_extension("json.gz");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&proof_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "Phase 28 aggregated chained folded intervalized decoding state relation",
        ))
        .stderr(
            predicate::str::contains("could not be inspected before reading")
                .and(predicate::str::contains("io_kind=NotFound")),
        )
        .stderr(predicate::str::contains("panicked at").not());
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_smoke() {
    let _guard = phase27_cli_test_guard();
    let proof_path = phase28_cli_demo_fixture_path();

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_artifact_version: {STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_outer_template_commitment(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-template",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-template-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["aggregation_template_commitment"] =
        serde_json::Value::String("tampered".to_string());
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "aggregation_template_commitment does not match the computed aggregation template commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_total_phase25_members(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-total-phase25",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-total-phase25-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

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
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
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
#[ignore = "expensive Phase 28 16-proof end-to-end CLI gate"]
fn cli_can_prove_and_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-proof",
    )
    .with_extension("json");
    let gzip_path = proof_path.with_extension("json.gz");

    let mut prove = tvm_command();
    prove
        .arg("prove-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg("-o")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("proof_backend: stwo"))
        .stdout(predicate::str::contains(format!(
            "artifact_version: {STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28}",
        )))
        .stdout(predicate::str::contains("bounded_aggregation_arity:"))
        .stdout(predicate::str::contains("total_phase26_members:"))
        .stdout(predicate::str::contains("total_phase25_members:"));

    let proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    assert_eq!(
        proof_json
            .get("artifact_version")
            .and_then(serde_json::Value::as_str),
        Some(STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28)
    );

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&proof_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"))
        .stdout(predicate::str::contains(format!(
            "expected_artifact_version: {STWO_AGGREGATED_CHAINED_FOLDED_INTERVALIZED_DECODING_STATE_RELATION_VERSION_PHASE28}",
        )))
        .stdout(predicate::str::contains(format!(
            "expected_proof_backend_version: {STWO_BACKEND_VERSION_PHASE12}",
        )));

    write_test_gzip_copy(&proof_path, &gzip_path);

    let mut verify_gzip = tvm_command();
    verify_gzip
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&gzip_path)
        .assert()
        .success()
        .stdout(predicate::str::contains("verified_stark: true"));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(gzip_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
#[ignore = "expensive Phase 28 16-proof end-to-end CLI gate"]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_corrupt_gzip(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-gzip",
    )
    .with_extension("json");
    let gzip_path = proof_path.with_extension("json.gz");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    write_test_gzip_copy(&proof_path, &gzip_path);
    let mut bytes = std::fs::read(&gzip_path).expect("read gzip");
    bytes.truncate(bytes.len().saturating_sub(8));
    std::fs::write(&gzip_path, bytes).expect("write corrupt gzip");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
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
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_accumulator_commitment(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-accumulator",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-accumulator-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["aggregated_chained_folded_interval_accumulator_commitment"] =
        serde_json::Value::String("tampered".to_string());
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "aggregated_chained_folded_interval_accumulator_commitment does not match the computed aggregated accumulator commitment",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
#[ignore = "expensive Phase 28 16-proof end-to-end CLI gate"]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_total_phase26_members(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-total-phase26",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-total-phase26-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let value = proof_json["total_phase26_members"]
        .as_u64()
        .expect("total_phase26_members");
    proof_json["total_phase26_members"] = serde_json::Value::from(value.saturating_add(1));
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains("total_phase26_members="))
        .stderr(predicate::str::contains(
            "does not match derived total_phase26_members",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
#[ignore = "expensive Phase 28 16-proof end-to-end CLI gate"]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_semantic_scope_drift(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-scope",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-scope-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    proof_json["semantic_scope"] =
        serde_json::Value::String("forged-phase28-semantic-scope".to_string());
    std::fs::write(
        &tampered_path,
        serde_json::to_vec(&proof_json).expect("serialize"),
    )
    .expect("write");

    let mut verify = tvm_command();
    verify
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "unsupported aggregated chained folded intervalized decoding state relation semantic scope",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}

#[test]
#[cfg(feature = "stwo-backend")]
#[ignore = "expensive Phase 28 16-proof end-to-end CLI gate"]
fn cli_verify_stwo_aggregated_chained_folded_intervalized_decoding_state_relation_demo_rejects_tampered_member_continuity(
) {
    let _guard = phase27_cli_test_guard();
    let proof_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-order",
    )
    .with_extension("json");
    let tampered_path = unique_temp_dir(
        "cli-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-order-tampered",
    )
    .with_extension("json");

    std::fs::copy(phase28_cli_demo_fixture_path(), &proof_path).expect("copy proof");

    let mut proof_json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&proof_path).expect("proof json"))
            .expect("json");
    let members = proof_json["members"].as_array_mut().expect("members array");
    assert!(
        members.len() >= 2,
        "phase28 demo must emit at least two members"
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
        .arg("verify-stwo-aggregated-chained-folded-intervalized-decoding-state-relation-demo")
        .arg(&tampered_path)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "does not preserve the carried-state commitment from the previous chained folded interval member",
        ));

    let _ = std::fs::remove_file(proof_path);
    let _ = std::fs::remove_file(tampered_path);
}
