use ark_ff::Zero;
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use sha2::{Digest as ShaDigest, Sha256};
use stwo::core::air::Component;
use stwo::core::channel::Blake2sM31Channel;
use stwo::core::fields::m31::BaseField;
use stwo::core::fields::qm31::SecureField;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::core::ColumnVec;
use stwo::prover::backend::simd::column::BaseColumn;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::{BitReversedOrder, NaturalOrder};
use stwo::prover::{prove, CommitmentSchemeProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    EvalAtRow, FrameworkComponent, FrameworkEval, TraceLocationAllocator,
};

use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const ZKAI_VECTOR_BLOCK_INPUT_SCHEMA: &str =
    "zkai-vector-block-residual-add-air-proof-input-v1";
pub const ZKAI_VECTOR_BLOCK_INPUT_DECISION: &str =
    "GO_INPUT_FOR_VECTOR_BLOCK_RESIDUAL_ADD_AIR_PROOF";
pub const ZKAI_VECTOR_BLOCK_PROOF_VERSION: &str = "stwo-vector-block-residual-add-air-proof-v1";
pub const ZKAI_VECTOR_BLOCK_STATEMENT_VERSION: &str = "zkai-vector-block-residual-add-statement-v1";
pub const ZKAI_VECTOR_BLOCK_SEMANTIC_SCOPE: &str =
    "parameterized_vector_residual_add_rows_bound_to_statement_receipt";
pub const ZKAI_VECTOR_BLOCK_DECISION: &str = "GO_VECTOR_BLOCK_RESIDUAL_ADD_AIR_PROOF";
pub const ZKAI_VECTOR_BLOCK_OPERATION: &str = "residual_add";
pub const ZKAI_VECTOR_BLOCK_TARGET_ID: &str = "rmsnorm-swiglu-residual-d128-v1";
pub const ZKAI_VECTOR_BLOCK_REQUIRED_BACKEND_VERSION: &str = "stwo-rmsnorm-swiglu-residual-d128-v1";
pub const ZKAI_VECTOR_BLOCK_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1";
pub const ZKAI_VECTOR_BLOCK_SOURCE_PROOF_BACKEND_VERSION: &str =
    "synthetic-d128-residual-delta-source-v1";
pub const ZKAI_VECTOR_BLOCK_STATEMENT_COMMITMENT: &str =
    "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18";
pub const ZKAI_VECTOR_BLOCK_INPUT_ACTIVATION_DOMAIN: &str = "ptvm:zkai:d128-input-activation:v1";
pub const ZKAI_VECTOR_BLOCK_RESIDUAL_DELTA_DOMAIN: &str = "ptvm:zkai:d128-residual-delta:v1";
pub const ZKAI_VECTOR_BLOCK_OUTPUT_ACTIVATION_DOMAIN: &str = "ptvm:zkai:d128-output-activation:v1";
pub const ZKAI_VECTOR_BLOCK_RESIDUAL_ADD_ROW_DOMAIN: &str = "ptvm:zkai:d128-residual-add-rows:v1";
pub const ZKAI_VECTOR_BLOCK_NEXT_BACKEND_STEP: &str =
    "parameterize RMSNorm, projection, activation, and down-projection slices before claiming a full d128 transformer-block proof";
pub const ZKAI_VECTOR_BLOCK_MAX_JSON_BYTES: usize = 4 * 1024 * 1024;
pub const ZKAI_VECTOR_BLOCK_MAX_PROOF_BYTES: usize = 2 * 1024 * 1024;
pub const ZKAI_VECTOR_BLOCK_MIN_WIDTH: usize = 2;
pub const ZKAI_VECTOR_BLOCK_MAX_WIDTH: usize = 4096;
pub const ZKAI_VECTOR_BLOCK_TARGET_WIDTH: usize = 128;

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const Q8_SEMANTIC_ABS_BOUND: i64 = 1024;
const EXPECTED_TRACE_COMMITMENTS: usize = 2;
const EXPECTED_PROOF_COMMITMENTS: usize = 3;
const ZKAI_VECTOR_BLOCK_PARAMETER_KIND: &str = "d128-residual-add-synthetic-parameters-v1";
const ZKAI_VECTOR_BLOCK_PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:d128-public-instance:v1";
const ZKAI_VECTOR_BLOCK_PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:d128-proof-native-parameter-commitment:v1";

const COLUMN_IDS: [&str; 4] = [
    "zkai/vector-block/residual-add/row-index",
    "zkai/vector-block/residual-add/input-q8",
    "zkai/vector-block/residual-add/residual-delta-q8",
    "zkai/vector-block/residual-add/output-q8",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not a full transformer-block proof",
    "not RMSNorm, projection, activation, or down-projection proof",
    "not recursive composition",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not onchain deployment evidence",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "pinned d128 target width checked before proof verification",
    "canonical d128 vector and row commitment domains checked before proof verification",
    "explicit power-of-two trace domain check before proving",
    "input activation commitment recomputation before proof verification",
    "residual-delta commitment recomputation before proof verification",
    "output activation commitment recomputation before proof verification",
    "residual-add row commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR residual-add relation for every checked output coordinate",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "python3 scripts/zkai_d128_vector_residual_add_proof_input.py --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv",
    "just gate-fast",
    "python3 -m unittest scripts.tests.test_zkai_d128_vector_residual_add_proof_input",
    "cargo +nightly-2025-07-14 test zkai_vector_block_residual_add_proof --lib --features stwo-backend",
    "just gate",
];

#[derive(Debug, Clone)]
struct ZkAiVectorBlockResidualAddEval {
    log_size: u32,
}

impl FrameworkEval for ZkAiVectorBlockResidualAddEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let row_index = eval.next_trace_mask();
        let input_q8 = eval.next_trace_mask();
        let residual_delta_q8 = eval.next_trace_mask();
        let output_q8 = eval.next_trace_mask();

        for (column_id, trace_value) in COLUMN_IDS.iter().zip([
            row_index,
            input_q8.clone(),
            residual_delta_q8.clone(),
            output_q8.clone(),
        ]) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        eval.add_constraint(input_q8 + residual_delta_q8 - output_q8);
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiVectorBlockResidualAddRow {
    pub row_index: usize,
    pub input_q8: i64,
    pub residual_delta_q8: i64,
    pub output_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiVectorBlockProofInput {
    pub schema: String,
    pub decision: String,
    pub operation: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub row_count: usize,
    pub source_proof_backend_version: String,
    pub input_activation_domain: String,
    pub residual_delta_domain: String,
    pub output_activation_domain: String,
    pub residual_add_row_domain: String,
    pub input_activation_commitment: String,
    pub residual_delta_commitment: String,
    pub output_activation_commitment: String,
    pub residual_add_row_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub input_q8: Vec<i64>,
    pub residual_delta_q8: Vec<i64>,
    pub output_q8: Vec<i64>,
    pub rows: Vec<ZkAiVectorBlockResidualAddRow>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiVectorBlockProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub operation: String,
    pub source_proof_backend_version: String,
    pub input: ZkAiVectorBlockProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ZkAiVectorBlockProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_vector_block_input_from_json_str(raw_json: &str) -> Result<ZkAiVectorBlockProofInput> {
    if raw_json.len() > ZKAI_VECTOR_BLOCK_MAX_JSON_BYTES {
        return Err(vector_block_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_VECTOR_BLOCK_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiVectorBlockProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_vector_block_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_vector_block_envelope(
    input: &ZkAiVectorBlockProofInput,
) -> Result<ZkAiVectorBlockProofEnvelope> {
    validate_vector_block_input(input)?;
    Ok(ZkAiVectorBlockProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_VECTOR_BLOCK_PROOF_VERSION.to_string(),
        statement_version: ZKAI_VECTOR_BLOCK_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_VECTOR_BLOCK_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_VECTOR_BLOCK_DECISION.to_string(),
        operation: ZKAI_VECTOR_BLOCK_OPERATION.to_string(),
        source_proof_backend_version: input.source_proof_backend_version.clone(),
        input: input.clone(),
        proof: prove_vector_block_rows(input)?,
    })
}

pub fn verify_zkai_vector_block_envelope(envelope: &ZkAiVectorBlockProofEnvelope) -> Result<bool> {
    validate_vector_block_envelope(envelope)?;
    verify_vector_block_rows(&envelope.input, &envelope.proof)
}

fn validate_vector_block_envelope(envelope: &ZkAiVectorBlockProofEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(vector_block_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_VECTOR_BLOCK_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_VECTOR_BLOCK_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_VECTOR_BLOCK_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(&envelope.decision, ZKAI_VECTOR_BLOCK_DECISION, "decision")?;
    expect_eq(
        &envelope.operation,
        ZKAI_VECTOR_BLOCK_OPERATION,
        "operation",
    )?;
    expect_eq(
        &envelope.source_proof_backend_version,
        &envelope.input.source_proof_backend_version,
        "source proof backend version",
    )?;
    if envelope.proof.is_empty() {
        return Err(vector_block_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_VECTOR_BLOCK_MAX_PROOF_BYTES {
        return Err(vector_block_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_VECTOR_BLOCK_MAX_PROOF_BYTES
        )));
    }
    validate_vector_block_input(&envelope.input)
}

fn validate_vector_block_input(input: &ZkAiVectorBlockProofInput) -> Result<()> {
    expect_eq(&input.schema, ZKAI_VECTOR_BLOCK_INPUT_SCHEMA, "schema")?;
    expect_eq(
        &input.decision,
        ZKAI_VECTOR_BLOCK_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(&input.operation, ZKAI_VECTOR_BLOCK_OPERATION, "operation")?;
    expect_eq(&input.target_id, ZKAI_VECTOR_BLOCK_TARGET_ID, "target id")?;
    expect_eq(
        &input.required_backend_version,
        ZKAI_VECTOR_BLOCK_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    validate_domain(&input.verifier_domain, "verifier domain")?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_VECTOR_BLOCK_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_eq(
        &input.source_proof_backend_version,
        ZKAI_VECTOR_BLOCK_SOURCE_PROOF_BACKEND_VERSION,
        "source proof backend version",
    )?;
    validate_commitment(
        &input.input_activation_commitment,
        "input activation commitment",
    )?;
    validate_commitment(
        &input.residual_delta_commitment,
        "residual delta commitment",
    )?;
    validate_commitment(
        &input.output_activation_commitment,
        "output activation commitment",
    )?;
    validate_commitment(
        &input.residual_add_row_commitment,
        "residual-add row commitment",
    )?;
    validate_commitment(
        &input.proof_native_parameter_commitment,
        "proof-native parameter commitment",
    )?;
    validate_commitment(
        &input.public_instance_commitment,
        "public instance commitment",
    )?;
    validate_commitment(&input.statement_commitment, "statement commitment")?;
    expect_eq(
        &input.statement_commitment,
        ZKAI_VECTOR_BLOCK_STATEMENT_COMMITMENT,
        "statement commitment",
    )?;
    validate_domain(&input.input_activation_domain, "input activation domain")?;
    expect_eq(
        &input.input_activation_domain,
        ZKAI_VECTOR_BLOCK_INPUT_ACTIVATION_DOMAIN,
        "input activation domain",
    )?;
    validate_domain(&input.residual_delta_domain, "residual delta domain")?;
    expect_eq(
        &input.residual_delta_domain,
        ZKAI_VECTOR_BLOCK_RESIDUAL_DELTA_DOMAIN,
        "residual delta domain",
    )?;
    validate_domain(&input.output_activation_domain, "output activation domain")?;
    expect_eq(
        &input.output_activation_domain,
        ZKAI_VECTOR_BLOCK_OUTPUT_ACTIVATION_DOMAIN,
        "output activation domain",
    )?;
    validate_domain(&input.residual_add_row_domain, "residual-add row domain")?;
    expect_eq(
        &input.residual_add_row_domain,
        ZKAI_VECTOR_BLOCK_RESIDUAL_ADD_ROW_DOMAIN,
        "residual-add row domain",
    )?;
    validate_width(input.width)?;
    expect_usize(input.width, ZKAI_VECTOR_BLOCK_TARGET_WIDTH, "target width")?;
    expect_usize(input.row_count, input.width, "row count")?;
    let log_size = log2_exact(input.width)?;
    if usize::try_from(1u128 << log_size).unwrap_or(usize::MAX) != input.width {
        return Err(vector_block_error("width does not match trace domain"));
    }
    expect_eq(
        &input.public_instance_commitment,
        &public_instance_commitment(&input.statement_commitment, input.width),
        "public instance recomputed commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        &proof_native_parameter_commitment(&input.statement_commitment),
        "proof-native parameter recomputed commitment",
    )?;
    if input.residual_delta_commitment == input.output_activation_commitment {
        return Err(vector_block_error(
            "residual delta commitment must not relabel as full output activation commitment",
        ));
    }
    if input.input_activation_commitment == input.output_activation_commitment {
        return Err(vector_block_error(
            "input activation commitment must not relabel as output activation commitment",
        ));
    }
    expect_str_set_eq(
        input.non_claims.iter().map(String::as_str),
        EXPECTED_NON_CLAIMS,
        "non claims",
    )?;
    expect_str_set_eq(
        input.proof_verifier_hardening.iter().map(String::as_str),
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_str_list_eq(
        input.validation_commands.iter().map(String::as_str),
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
    )?;
    expect_eq(
        &input.next_backend_step,
        ZKAI_VECTOR_BLOCK_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    for (label, values) in [
        ("input activation q8", &input.input_q8),
        ("residual delta q8", &input.residual_delta_q8),
        ("output activation q8", &input.output_q8),
    ] {
        if values.len() != input.width {
            return Err(vector_block_error(format!(
                "{label} vector length mismatch: got {}, expected {}",
                values.len(),
                input.width
            )));
        }
        for (index, value) in values.iter().enumerate() {
            expect_signed_q8(*value, &format!("{label} {index}"))?;
            expect_signed_m31(*value, &format!("{label} {index}"))?;
        }
    }
    if input.rows.len() != input.width {
        return Err(vector_block_error(format!(
            "row vector length mismatch: got {}, expected {}",
            input.rows.len(),
            input.width
        )));
    }
    expect_eq(
        &sequence_commitment(&input.input_q8, &input.input_activation_domain, input.width),
        &input.input_activation_commitment,
        "input activation recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &input.residual_delta_q8,
            &input.residual_delta_domain,
            input.width,
        ),
        &input.residual_delta_commitment,
        "residual delta recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &input.output_q8,
            &input.output_activation_domain,
            input.width,
        ),
        &input.output_activation_commitment,
        "output activation recomputed commitment",
    )?;
    let recomputed_rows = build_rows(&input.input_q8, &input.residual_delta_q8)?;
    if recomputed_rows != input.rows {
        return Err(vector_block_error("residual-add row relation drift"));
    }
    for (expected_index, row) in input.rows.iter().enumerate() {
        validate_vector_block_row(row, expected_index)?;
        expect_i64(
            row.output_q8,
            input.output_q8[expected_index],
            "output activation row value",
        )?;
    }
    expect_eq(
        &rows_commitment(&input.rows, &input.residual_add_row_domain),
        &input.residual_add_row_commitment,
        "residual-add row recomputed commitment",
    )?;
    Ok(())
}

fn validate_vector_block_row(
    row: &ZkAiVectorBlockResidualAddRow,
    expected_index: usize,
) -> Result<()> {
    expect_usize(row.row_index, expected_index, "row index")?;
    expect_signed_q8(row.input_q8, "input activation q8")?;
    expect_signed_m31(row.input_q8, "input activation q8")?;
    expect_signed_q8(row.residual_delta_q8, "residual delta q8")?;
    expect_signed_m31(row.residual_delta_q8, "residual delta q8")?;
    expect_signed_q8(row.output_q8, "output activation q8")?;
    expect_signed_m31(row.output_q8, "output activation q8")?;
    let expected_output =
        checked_add_i64(row.input_q8, row.residual_delta_q8, "residual-add output")?;
    expect_i64(row.output_q8, expected_output, "residual-add relation")
}

fn build_rows(
    input_q8: &[i64],
    residual_delta_q8: &[i64],
) -> Result<Vec<ZkAiVectorBlockResidualAddRow>> {
    if input_q8.len() != residual_delta_q8.len() {
        return Err(vector_block_error(
            "input and residual delta lengths differ",
        ));
    }
    validate_width(input_q8.len())?;
    let mut rows = Vec::with_capacity(input_q8.len());
    for (row_index, (input_q8, residual_delta_q8)) in
        input_q8.iter().zip(residual_delta_q8.iter()).enumerate()
    {
        let output_q8 = checked_add_i64(*input_q8, *residual_delta_q8, "residual-add output")?;
        rows.push(ZkAiVectorBlockResidualAddRow {
            row_index,
            input_q8: *input_q8,
            residual_delta_q8: *residual_delta_q8,
            output_q8,
        });
    }
    Ok(rows)
}

fn prove_vector_block_rows(input: &ZkAiVectorBlockProofInput) -> Result<Vec<u8>> {
    let component = vector_block_component(input.width)?;
    let config = vector_block_pcs_config();
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(vector_block_trace(input)?);
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(vector_block_trace(input)?);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "vector-block residual-add AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&ZkAiVectorBlockProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_vector_block_rows(input: &ZkAiVectorBlockProofInput, proof: &[u8]) -> Result<bool> {
    let payload: ZkAiVectorBlockProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_vector_block_pcs_config(stark_proof.config)?;
    let component = vector_block_component(input.width)?;
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != EXPECTED_TRACE_COMMITMENTS {
        return Err(vector_block_error(format!(
            "internal component commitment count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(vector_block_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = vector_block_commitment_roots(input, config)?;
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(vector_block_error(
            "preprocessed row commitment does not match checked vector-block rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(vector_block_error(
            "base row commitment does not match checked vector-block rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| vector_block_error(format!("STARK verification failed: {error}")))
}

fn validate_vector_block_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(vector_block_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(vector_block_pcs_config())
}

fn vector_block_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn vector_block_commitment_roots(
    input: &ZkAiVectorBlockProofInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    // This recomputes the expected commitment roots from the already-validated
    // public rows so a proof cannot relabel one row set as another. It is a
    // binding check, not a claimed verifier-time-optimized path.
    let component = vector_block_component(input.width)?;
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(vector_block_trace(input)?);
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(vector_block_trace(input)?);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn vector_block_component(
    width: usize,
) -> Result<FrameworkComponent<ZkAiVectorBlockResidualAddEval>> {
    Ok(FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        ZkAiVectorBlockResidualAddEval {
            log_size: log2_exact(width)?,
        },
        SecureField::zero(),
    ))
}

fn vector_block_trace(
    input: &ZkAiVectorBlockProofInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let log_size = log2_exact(input.width)?;
    let domain = CanonicCoset::new(log_size).circle_domain();
    let rows = &input.rows;
    let columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.row_index)).collect(),
        rows.iter().map(|row| field_i64(row.input_q8)).collect(),
        rows.iter()
            .map(|row| field_i64(row.residual_delta_q8))
            .collect(),
        rows.iter().map(|row| field_i64(row.output_q8)).collect(),
    ];
    Ok(columns
        .into_iter()
        .map(|column| {
            CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
                domain,
                BaseColumn::from_iter(column),
            )
            .bit_reverse()
        })
        .collect())
}

fn preprocessed_column_ids() -> Vec<PreProcessedColumnId> {
    COLUMN_IDS.into_iter().map(preprocessed_column_id).collect()
}

fn preprocessed_column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

fn field_usize(value: usize) -> BaseField {
    BaseField::from(u32::try_from(value).expect("field_usize: value out of u32 range"))
}

fn field_i64(value: i64) -> BaseField {
    BaseField::from(value.rem_euclid(M31_MODULUS) as u32)
}

fn sequence_commitment(values: &[i64], domain: &str, width: usize) -> String {
    let values_json = canonical_i64_array(values);
    let values_sha256 = sha256_hex(values_json.as_bytes());
    let payload = format!(
        "{{\"encoding\":\"signed_integer_sequence_v1\",\"shape\":[{}],\"values_sha256\":\"{}\"}}",
        width, values_sha256
    );
    blake2b_commitment_bytes(payload.as_bytes(), domain)
}

fn rows_commitment(rows: &[ZkAiVectorBlockResidualAddRow], domain: &str) -> String {
    let rows_json = canonical_row_material(rows);
    let rows_sha256 = sha256_hex(rows_json.as_bytes());
    let payload = format!(
        "{{\"encoding\":\"vector_block_residual_add_rows_v1\",\"rows_sha256\":\"{}\",\"shape\":[{},4]}}",
        rows_sha256,
        rows.len()
    );
    blake2b_commitment_bytes(payload.as_bytes(), domain)
}

fn public_instance_commitment(statement_commitment: &str, width: usize) -> String {
    let payload = format!(
        "{{\"operation\":\"{}\",\"target_commitment\":\"{}\",\"width\":{}}}",
        ZKAI_VECTOR_BLOCK_OPERATION, statement_commitment, width
    );
    blake2b_commitment_bytes(payload.as_bytes(), ZKAI_VECTOR_BLOCK_PUBLIC_INSTANCE_DOMAIN)
}

fn proof_native_parameter_commitment(statement_commitment: &str) -> String {
    let payload = format!(
        "{{\"kind\":\"{}\",\"target_commitment\":\"{}\"}}",
        ZKAI_VECTOR_BLOCK_PARAMETER_KIND, statement_commitment
    );
    blake2b_commitment_bytes(
        payload.as_bytes(),
        ZKAI_VECTOR_BLOCK_PROOF_NATIVE_PARAMETER_DOMAIN,
    )
}

fn canonical_i64_array(values: &[i64]) -> String {
    let mut out = String::from("[");
    for (index, value) in values.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        out.push_str(&value.to_string());
    }
    out.push(']');
    out
}

fn canonical_row_material(rows: &[ZkAiVectorBlockResidualAddRow]) -> String {
    let mut out = String::from("[");
    for (index, row) in rows.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        out.push('[');
        for (field_index, value) in [
            row.row_index as i64,
            row.input_q8,
            row.residual_delta_q8,
            row.output_q8,
        ]
        .iter()
        .enumerate()
        {
            if field_index > 0 {
                out.push(',');
            }
            out.push_str(&value.to_string());
        }
        out.push(']');
    }
    out.push(']');
    out
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    ShaDigest::update(&mut hasher, bytes);
    lower_hex(&hasher.finalize())
}

fn blake2b_commitment_bytes(bytes: &[u8], domain: &str) -> String {
    format!("blake2b-256:{}", blake2b_hex(bytes, domain))
}

fn blake2b_hex(bytes: &[u8], domain: &str) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(domain.as_bytes());
    hasher.update(b"\0");
    hasher.update(bytes);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn lower_hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        write!(&mut out, "{byte:02x}").expect("hex write");
    }
    out
}

fn validate_width(width: usize) -> Result<()> {
    if !(ZKAI_VECTOR_BLOCK_MIN_WIDTH..=ZKAI_VECTOR_BLOCK_MAX_WIDTH).contains(&width) {
        return Err(vector_block_error(format!(
            "width outside supported range: got {width}, expected {ZKAI_VECTOR_BLOCK_MIN_WIDTH}..={ZKAI_VECTOR_BLOCK_MAX_WIDTH}"
        )));
    }
    log2_exact(width).map(|_| ())
}

fn log2_exact(width: usize) -> Result<u32> {
    if !width.is_power_of_two() {
        return Err(vector_block_error(format!(
            "width must be a power of two trace domain: got {width}"
        )));
    }
    Ok(width.trailing_zeros())
}

fn validate_label(value: &str, label: &str) -> Result<()> {
    if value.trim().is_empty() || value.len() > 256 {
        return Err(vector_block_error(format!(
            "{label} must be a bounded non-empty string"
        )));
    }
    Ok(())
}

fn validate_domain(value: &str, label: &str) -> Result<()> {
    validate_label(value, label)?;
    if !value.starts_with("ptvm:zkai:") {
        return Err(vector_block_error(format!(
            "{label} must be a ptvm:zkai domain-separated label"
        )));
    }
    Ok(())
}

fn validate_commitment(value: &str, label: &str) -> Result<()> {
    let Some(digest) = value.strip_prefix("blake2b-256:") else {
        return Err(vector_block_error(format!(
            "{label} must be a blake2b-256 commitment"
        )));
    };
    if digest.len() != 64
        || !digest
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(vector_block_error(format!(
            "{label} must contain a lowercase 32-byte hex digest"
        )));
    }
    Ok(())
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(vector_block_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(vector_block_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(vector_block_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(vector_block_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
}

fn expect_signed_q8(value: i64, label: &str) -> Result<()> {
    if !(-Q8_SEMANTIC_ABS_BOUND..=Q8_SEMANTIC_ABS_BOUND).contains(&value) {
        return Err(vector_block_error(format!(
            "{label} is outside fixed-point q8 semantic bound: {value}"
        )));
    }
    Ok(())
}

fn checked_add_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_add(rhs)
        .ok_or_else(|| vector_block_error(format!("{label} overflow")))
}

fn expect_str_set_eq<'a>(
    actual: impl IntoIterator<Item = &'a str>,
    expected: &[&str],
    label: &str,
) -> Result<()> {
    let mut actual_vec: Vec<&str> = actual.into_iter().collect();
    let mut expected_vec = expected.to_vec();
    actual_vec.sort_unstable();
    expected_vec.sort_unstable();
    if actual_vec != expected_vec {
        return Err(vector_block_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn expect_str_list_eq<'a>(
    actual: impl IntoIterator<Item = &'a str>,
    expected: &[&str],
    label: &str,
) -> Result<()> {
    let actual_vec: Vec<&str> = actual.into_iter().collect();
    if actual_vec.as_slice() != expected {
        return Err(vector_block_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected:?}"
        )));
    }
    Ok(())
}

fn vector_block_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "vector-block residual-add proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json"
    );

    fn input() -> ZkAiVectorBlockProofInput {
        zkai_vector_block_input_from_json_str(INPUT_JSON).expect("vector block input")
    }

    fn json_i64_vec(value: &Value, key: &str) -> Vec<i64> {
        value[key]
            .as_array()
            .expect("array")
            .iter()
            .map(|item| item.as_i64().expect("i64"))
            .collect()
    }

    #[test]
    fn vector_block_input_validates_d128_rows() {
        let input = input();
        assert_eq!(input.width, 128);
        assert_eq!(input.rows.len(), 128);
        assert_eq!(
            input.rows[0].input_q8 + input.rows[0].residual_delta_q8,
            input.rows[0].output_q8
        );
        assert_ne!(
            input.residual_delta_commitment,
            input.output_activation_commitment
        );
    }

    #[test]
    fn vector_block_air_proof_round_trips_d128() {
        let input = input();
        let envelope = prove_zkai_vector_block_envelope(&input).expect("vector proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_vector_block_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn vector_block_rejects_width_relabeling() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["width"] = Value::from(64);
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("target width"));
    }

    #[test]
    fn vector_block_rejects_consistent_non_d128_width() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["width"] = Value::from(64);
        value["row_count"] = Value::from(64);
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("target width"));
    }

    #[test]
    fn vector_block_rejects_non_power_of_two_width() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["width"] = Value::from(127);
        value["row_count"] = Value::from(127);
        value["rows"].as_array_mut().expect("rows").pop();
        value["input_q8"].as_array_mut().expect("input").pop();
        value["residual_delta_q8"]
            .as_array_mut()
            .expect("delta")
            .pop();
        value["output_q8"].as_array_mut().expect("output").pop();
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("power of two"));
    }

    #[test]
    fn vector_block_rejects_input_vector_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["input_q8"][0] = Value::from(value["input_q8"][0].as_i64().unwrap() + 1);
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error
            .to_string()
            .contains("input activation recomputed commitment"));
    }

    #[test]
    fn vector_block_rejects_row_relation_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][0]["output_q8"] =
            Value::from(value["rows"][0]["output_q8"].as_i64().unwrap() + 1);
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error
            .to_string()
            .contains("residual-add row relation drift"));
    }

    #[test]
    fn vector_block_rejects_commitment_relabeling() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_commitment"] = value["output_activation_commitment"].clone();
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("must not relabel"));
    }

    #[test]
    fn vector_block_rejects_statement_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["statement_commitment"] = Value::from(format!("blake2b-256:{}", "11".repeat(32)));
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("statement commitment"));
    }

    #[test]
    fn vector_block_rejects_public_instance_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["public_instance_commitment"] =
            Value::from(format!("blake2b-256:{}", "22".repeat(32)));
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("public instance"));
    }

    #[test]
    fn vector_block_rejects_proof_native_parameter_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["proof_native_parameter_commitment"] =
            Value::from(format!("blake2b-256:{}", "33".repeat(32)));
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("proof-native parameter"));
    }

    #[test]
    fn vector_block_rejects_verifier_domain_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["verifier_domain"] = Value::from("ptvm:zkai:other-domain:v1");
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("verifier domain"));
    }

    #[test]
    fn vector_block_rejects_validation_command_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["validation_commands"][0] = Value::from("echo skipped");
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("validation commands"));
    }

    #[test]
    fn vector_block_rejects_recomputed_noncanonical_input_domain() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        let domain = "ptvm:zkai:noncanonical-input-activation:v1";
        value["input_activation_domain"] = Value::from(domain);
        value["input_activation_commitment"] = Value::from(sequence_commitment(
            &json_i64_vec(&value, "input_q8"),
            domain,
            128,
        ));
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("input activation domain"));
    }

    #[test]
    fn vector_block_rejects_uppercase_commitment_hex() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["input_activation_commitment"] = Value::from(
            value["input_activation_commitment"]
                .as_str()
                .expect("commitment")
                .to_ascii_uppercase()
                .replace("BLAKE2B-256:", "blake2b-256:"),
        );
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("lowercase"));
    }

    #[test]
    fn vector_block_rejects_repeated_commitment_prefix() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["proof_native_parameter_commitment"] =
            Value::from(format!("blake2b-256:blake2b-256:{}", "44".repeat(32)));
        let error =
            zkai_vector_block_input_from_json_str(&serde_json::to_string(&value).expect("json"))
                .unwrap_err();
        assert!(error.to_string().contains("lowercase"));
    }

    #[test]
    fn vector_block_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope = prove_zkai_vector_block_envelope(&input).expect("vector proof");
        envelope.input.rows[0].output_q8 += 1;
        let error = verify_zkai_vector_block_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("vector-block residual-add proof rejected"));
    }

    #[test]
    fn vector_block_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope = prove_zkai_vector_block_envelope(&input).expect("vector proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_vector_block_envelope(&envelope).is_err());
    }

    #[test]
    fn vector_block_rejects_unknown_proof_payload_fields() {
        let input = input();
        let mut envelope = prove_zkai_vector_block_envelope(&input).expect("vector proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        payload["unexpected"] = Value::from(true);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        assert!(verify_zkai_vector_block_envelope(&envelope).is_err());
    }

    #[test]
    fn vector_block_rejects_unknown_envelope_fields() {
        let input = input();
        let envelope = prove_zkai_vector_block_envelope(&input).expect("vector proof");
        let mut value = serde_json::to_value(&envelope).expect("envelope json");
        value["unexpected"] = Value::from(true);
        assert!(serde_json::from_value::<ZkAiVectorBlockProofEnvelope>(value).is_err());
    }

    #[test]
    fn vector_block_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope = prove_zkai_vector_block_envelope(&input).expect("vector proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_vector_block_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }
}
