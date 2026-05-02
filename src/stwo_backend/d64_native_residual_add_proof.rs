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

use super::d64_native_down_projection_proof::{
    ZKAI_D64_DOWN_PROJECTION_PROOF_VERSION, ZKAI_D64_RESIDUAL_DELTA_COMMITMENT,
};
use super::d64_native_export_contract::{
    ZKAI_D64_INPUT_ACTIVATION_COMMITMENT, ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT,
    ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT, ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D64_REQUIRED_BACKEND_VERSION, ZKAI_D64_RESIDUAL_ROWS, ZKAI_D64_STATEMENT_COMMITMENT,
    ZKAI_D64_TARGET_ID, ZKAI_D64_VERIFIER_DOMAIN, ZKAI_D64_WIDTH,
};

pub const ZKAI_D64_RESIDUAL_ADD_INPUT_SCHEMA: &str = "zkai-d64-residual-add-air-proof-input-v1";
pub const ZKAI_D64_RESIDUAL_ADD_INPUT_DECISION: &str = "GO_INPUT_FOR_D64_RESIDUAL_ADD_AIR_PROOF";
pub const ZKAI_D64_RESIDUAL_ADD_PROOF_VERSION: &str = "stwo-d64-residual-add-air-proof-v1";
pub const ZKAI_D64_RESIDUAL_ADD_STATEMENT_VERSION: &str = "zkai-d64-residual-add-statement-v1";
pub const ZKAI_D64_RESIDUAL_ADD_SEMANTIC_SCOPE: &str =
    "d64_residual_add_rows_bound_to_down_projection_receipt_and_public_instance";
pub const ZKAI_D64_RESIDUAL_ADD_DECISION: &str = "GO_D64_RESIDUAL_ADD_AIR_PROOF";
pub const ZKAI_D64_RESIDUAL_ADD_NEXT_BACKEND_STEP: &str =
    "compose the d64 proof slices into a single statement-bound block receipt";
pub const ZKAI_D64_RESIDUAL_ADD_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D64_RESIDUAL_ADD_MAX_PROOF_BYTES: usize = 1_048_576;
pub const ZKAI_D64_RESIDUAL_ADD_ROW_COMMITMENT: &str =
    "blake2b-256:6baf5415fa20ad7fce80b14c361815ea55553fe7609b17bff383c16771651592";

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const D64_RESIDUAL_ADD_LOG_SIZE: u32 = 6;
const Q8_SEMANTIC_ABS_BOUND: i64 = 1024;
const ZKAI_D64_RESIDUAL_ADD_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D64_RESIDUAL_ADD_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const INPUT_ACTIVATION_DOMAIN: &str = "ptvm:zkai:d64-input-activation:v1";
const RESIDUAL_DELTA_DOMAIN: &str = "ptvm:zkai:d64-residual-delta:v1";
const OUTPUT_ACTIVATION_DOMAIN: &str = "ptvm:zkai:d64-output-activation:v1";
const RESIDUAL_ADD_ROW_DOMAIN: &str = "ptvm:zkai:d64-residual-add-rows:v1";

const COLUMN_IDS: [&str; 4] = [
    "zkai/d64/residual-add/row-index",
    "zkai/d64/residual-add/input-q8",
    "zkai/d64/residual-add/residual-delta-q8",
    "zkai/d64/residual-add/output-q8",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not recursive composition of all d64 proof slices",
    "not private parameter-opening proof",
    "not model-scale transformer inference",
    "not verifier-time benchmark evidence",
    "not onchain deployment evidence",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "source down-projection residual-delta commitment recomputation before proof verification",
    "canonical input activation commitment recomputation before proof verification",
    "residual-add row commitment recomputation before proof verification",
    "final output activation commitment recomputation before proof verification",
    "AIR residual-add relation for every checked d64 output coordinate",
    "explicit fixed-point q8 semantic bounds for input, residual delta, and output activations",
    "intermediate commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

#[derive(Debug, Clone)]
struct D64ResidualAddEval {
    log_size: u32,
}

impl FrameworkEval for D64ResidualAddEval {
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
pub struct D64ResidualAddRow {
    pub row_index: usize,
    pub input_q8: i64,
    pub residual_delta_q8: i64,
    pub output_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD64ResidualAddProofInput {
    pub schema: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub row_count: usize,
    pub source_down_projection_proof_version: String,
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
    pub rows: Vec<D64ResidualAddRow>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64ResidualAddEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub source_down_projection_proof_version: String,
    pub input: ZkAiD64ResidualAddProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct D64ResidualAddProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d64_residual_add_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD64ResidualAddProofInput> {
    if raw_json.len() > ZKAI_D64_RESIDUAL_ADD_MAX_JSON_BYTES {
        return Err(residual_add_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D64_RESIDUAL_ADD_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD64ResidualAddProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_residual_add_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d64_residual_add_envelope(
    input: &ZkAiD64ResidualAddProofInput,
) -> Result<ZkAiD64ResidualAddEnvelope> {
    validate_residual_add_input(input)?;
    Ok(ZkAiD64ResidualAddEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D64_RESIDUAL_ADD_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D64_RESIDUAL_ADD_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D64_RESIDUAL_ADD_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D64_RESIDUAL_ADD_DECISION.to_string(),
        source_down_projection_proof_version: ZKAI_D64_DOWN_PROJECTION_PROOF_VERSION.to_string(),
        input: input.clone(),
        proof: prove_residual_add_rows(input)?,
    })
}

pub fn verify_zkai_d64_residual_add_envelope(
    envelope: &ZkAiD64ResidualAddEnvelope,
) -> Result<bool> {
    validate_residual_add_envelope(envelope)?;
    verify_residual_add_rows(&envelope.input, &envelope.proof)
}

fn validate_residual_add_envelope(envelope: &ZkAiD64ResidualAddEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(residual_add_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D64_RESIDUAL_ADD_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D64_RESIDUAL_ADD_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D64_RESIDUAL_ADD_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D64_RESIDUAL_ADD_DECISION,
        "decision",
    )?;
    expect_eq(
        &envelope.source_down_projection_proof_version,
        ZKAI_D64_DOWN_PROJECTION_PROOF_VERSION,
        "source down-projection proof version",
    )?;
    if envelope.proof.is_empty() {
        return Err(residual_add_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D64_RESIDUAL_ADD_MAX_PROOF_BYTES {
        return Err(residual_add_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D64_RESIDUAL_ADD_MAX_PROOF_BYTES
        )));
    }
    validate_residual_add_input(&envelope.input)
}

fn validate_residual_add_input(input: &ZkAiD64ResidualAddProofInput) -> Result<()> {
    expect_eq(&input.schema, ZKAI_D64_RESIDUAL_ADD_INPUT_SCHEMA, "schema")?;
    expect_eq(
        &input.decision,
        ZKAI_D64_RESIDUAL_ADD_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(&input.target_id, ZKAI_D64_TARGET_ID, "target id")?;
    expect_eq(
        &input.required_backend_version,
        ZKAI_D64_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_D64_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_usize(input.width, ZKAI_D64_WIDTH, "width")?;
    expect_usize(input.row_count, ZKAI_D64_RESIDUAL_ROWS, "row count")?;
    expect_eq(
        &input.source_down_projection_proof_version,
        ZKAI_D64_DOWN_PROJECTION_PROOF_VERSION,
        "source down-projection proof version",
    )?;
    if input.residual_delta_commitment == input.output_activation_commitment {
        return Err(residual_add_error(
            "residual delta commitment must not relabel as full output activation commitment",
        ));
    }
    if input.input_activation_commitment == input.output_activation_commitment {
        return Err(residual_add_error(
            "input activation commitment must not relabel as output activation commitment",
        ));
    }
    expect_eq(
        &input.input_activation_commitment,
        ZKAI_D64_INPUT_ACTIVATION_COMMITMENT,
        "input activation commitment",
    )?;
    expect_eq(
        &input.residual_delta_commitment,
        ZKAI_D64_RESIDUAL_DELTA_COMMITMENT,
        "residual delta commitment",
    )?;
    expect_eq(
        &input.output_activation_commitment,
        ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT,
        "output activation commitment",
    )?;
    expect_eq(
        &input.residual_add_row_commitment,
        ZKAI_D64_RESIDUAL_ADD_ROW_COMMITMENT,
        "residual-add row commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "proof-native parameter commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
        "public instance commitment",
    )?;
    expect_eq(
        &input.statement_commitment,
        ZKAI_D64_STATEMENT_COMMITMENT,
        "statement commitment",
    )?;
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
    expect_eq(
        &input.next_backend_step,
        ZKAI_D64_RESIDUAL_ADD_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    if input.input_q8.len() != ZKAI_D64_WIDTH {
        return Err(residual_add_error(
            "input activation vector length mismatch",
        ));
    }
    if input.residual_delta_q8.len() != ZKAI_D64_WIDTH {
        return Err(residual_add_error("residual delta vector length mismatch"));
    }
    if input.output_q8.len() != ZKAI_D64_WIDTH {
        return Err(residual_add_error(
            "output activation vector length mismatch",
        ));
    }
    if input.rows.len() != ZKAI_D64_WIDTH {
        return Err(residual_add_error(format!(
            "row vector length mismatch: got {}, expected {}",
            input.rows.len(),
            ZKAI_D64_WIDTH
        )));
    }
    for (label, values) in [
        ("input activation q8", &input.input_q8),
        ("residual delta q8", &input.residual_delta_q8),
        ("output activation q8", &input.output_q8),
    ] {
        for (index, value) in values.iter().enumerate() {
            expect_signed_q8(*value, &format!("{label} {index}"))?;
            expect_signed_m31(*value, &format!("{label} {index}"))?;
        }
    }
    expect_eq(
        &sequence_commitment(&input.input_q8, INPUT_ACTIVATION_DOMAIN, ZKAI_D64_WIDTH),
        &input.input_activation_commitment,
        "input activation recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &input.residual_delta_q8,
            RESIDUAL_DELTA_DOMAIN,
            ZKAI_D64_WIDTH,
        ),
        &input.residual_delta_commitment,
        "residual delta recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(&input.output_q8, OUTPUT_ACTIVATION_DOMAIN, ZKAI_D64_WIDTH),
        &input.output_activation_commitment,
        "output activation recomputed commitment",
    )?;
    let recomputed_rows = build_rows(&input.input_q8, &input.residual_delta_q8)?;
    if recomputed_rows != input.rows {
        return Err(residual_add_error("residual-add row relation drift"));
    }
    for (expected_index, row) in input.rows.iter().enumerate() {
        validate_residual_add_row(row, expected_index)?;
        expect_i64(
            row.output_q8,
            input.output_q8[expected_index],
            "output activation row value",
        )?;
    }
    expect_eq(
        &rows_commitment(&input.rows),
        &input.residual_add_row_commitment,
        "residual-add row recomputed commitment",
    )?;
    Ok(())
}

fn validate_residual_add_row(row: &D64ResidualAddRow, expected_index: usize) -> Result<()> {
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

fn build_rows(input_q8: &[i64], residual_delta_q8: &[i64]) -> Result<Vec<D64ResidualAddRow>> {
    if input_q8.len() != ZKAI_D64_WIDTH {
        return Err(residual_add_error(
            "input activation vector length mismatch",
        ));
    }
    if residual_delta_q8.len() != ZKAI_D64_WIDTH {
        return Err(residual_add_error("residual delta vector length mismatch"));
    }
    let mut rows = Vec::with_capacity(ZKAI_D64_WIDTH);
    for (row_index, (input_q8, residual_delta_q8)) in
        input_q8.iter().zip(residual_delta_q8.iter()).enumerate()
    {
        let output_q8 = checked_add_i64(*input_q8, *residual_delta_q8, "residual-add output")?;
        rows.push(D64ResidualAddRow {
            row_index,
            input_q8: *input_q8,
            residual_delta_q8: *residual_delta_q8,
            output_q8,
        });
    }
    Ok(rows)
}

fn prove_residual_add_rows(input: &ZkAiD64ResidualAddProofInput) -> Result<Vec<u8>> {
    let component = residual_add_component();
    let config = residual_add_pcs_config();
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
    tree_builder.extend_evals(residual_add_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(residual_add_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!("d64 residual-add AIR proving failed: {error}"))
            })?;
    serde_json::to_vec(&D64ResidualAddProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_residual_add_rows(input: &ZkAiD64ResidualAddProofInput, proof: &[u8]) -> Result<bool> {
    let payload: D64ResidualAddProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_residual_add_pcs_config(stark_proof.config)?;
    let component = residual_add_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D64_RESIDUAL_ADD_EXPECTED_TRACE_COMMITMENTS {
        return Err(residual_add_error(format!(
            "internal residual-add component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D64_RESIDUAL_ADD_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D64_RESIDUAL_ADD_EXPECTED_PROOF_COMMITMENTS {
        return Err(residual_add_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D64_RESIDUAL_ADD_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = residual_add_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(residual_add_error(
            "preprocessed row commitment does not match checked residual-add rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(residual_add_error(
            "base row commitment does not match checked residual-add rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| residual_add_error(format!("STARK verification failed: {error}")))
}

fn validate_residual_add_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(residual_add_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(residual_add_pcs_config())
}

fn residual_add_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn residual_add_commitment_roots(
    input: &ZkAiD64ResidualAddProofInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = residual_add_component();
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
    tree_builder.extend_evals(residual_add_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(residual_add_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn residual_add_component() -> FrameworkComponent<D64ResidualAddEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D64ResidualAddEval {
            log_size: D64_RESIDUAL_ADD_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn residual_add_trace(
    input: &ZkAiD64ResidualAddProofInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D64_RESIDUAL_ADD_LOG_SIZE).circle_domain();
    let rows = &input.rows;
    let columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.row_index)).collect(),
        rows.iter().map(|row| field_i64(row.input_q8)).collect(),
        rows.iter()
            .map(|row| field_i64(row.residual_delta_q8))
            .collect(),
        rows.iter().map(|row| field_i64(row.output_q8)).collect(),
    ];
    columns
        .into_iter()
        .map(|column| {
            CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
                domain,
                BaseColumn::from_iter(column),
            )
            .bit_reverse()
        })
        .collect()
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

fn rows_commitment(rows: &[D64ResidualAddRow]) -> String {
    let rows_json = canonical_row_material(rows);
    let rows_sha256 = sha256_hex(rows_json.as_bytes());
    let payload = format!(
        "{{\"encoding\":\"d64_residual_add_rows_v1\",\"rows_sha256\":\"{}\",\"shape\":[{},4]}}",
        rows_sha256,
        rows.len()
    );
    blake2b_commitment_bytes(payload.as_bytes(), RESIDUAL_ADD_ROW_DOMAIN)
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

fn canonical_row_material(rows: &[D64ResidualAddRow]) -> String {
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

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(residual_add_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(residual_add_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(residual_add_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(residual_add_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
}

fn expect_signed_q8(value: i64, label: &str) -> Result<()> {
    if !(-Q8_SEMANTIC_ABS_BOUND..=Q8_SEMANTIC_ABS_BOUND).contains(&value) {
        return Err(residual_add_error(format!(
            "{label} is outside fixed-point q8 semantic bound: {value}"
        )));
    }
    Ok(())
}

fn checked_add_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_add(rhs)
        .ok_or_else(|| residual_add_error(format!("{label} overflow")))
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
        return Err(residual_add_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn residual_add_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 residual-add proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str =
        include_str!("../../docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json");

    fn input() -> ZkAiD64ResidualAddProofInput {
        zkai_d64_residual_add_input_from_json_str(INPUT_JSON).expect("residual-add input")
    }

    #[test]
    fn residual_add_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(input.rows.len(), ZKAI_D64_WIDTH);
        assert_eq!(input.input_q8.len(), ZKAI_D64_WIDTH);
        assert_eq!(input.residual_delta_q8.len(), ZKAI_D64_WIDTH);
        assert_eq!(input.output_q8.len(), ZKAI_D64_WIDTH);
        assert_eq!(input.rows[0].input_q8, 24);
        assert_eq!(input.rows[0].residual_delta_q8, 16);
        assert_eq!(input.rows[0].output_q8, 40);
        assert_eq!(
            input.input_activation_commitment,
            ZKAI_D64_INPUT_ACTIVATION_COMMITMENT
        );
        assert_eq!(
            input.residual_delta_commitment,
            ZKAI_D64_RESIDUAL_DELTA_COMMITMENT
        );
        assert_eq!(
            input.output_activation_commitment,
            ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT
        );
        assert_eq!(
            input.residual_add_row_commitment,
            ZKAI_D64_RESIDUAL_ADD_ROW_COMMITMENT
        );
        assert_ne!(
            input.residual_delta_commitment,
            ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT
        );
    }

    #[test]
    fn residual_add_pcs_config_uses_shared_publication_v1_profile() {
        let actual = residual_add_pcs_config();
        let expected = crate::stwo_backend::publication_v1_pcs_config();
        assert_eq!(actual.pow_bits, expected.pow_bits);
        assert_eq!(
            actual.fri_config.log_blowup_factor,
            expected.fri_config.log_blowup_factor
        );
        assert_eq!(actual.fri_config.n_queries, expected.fri_config.n_queries);
        assert_eq!(
            actual.fri_config.log_last_layer_degree_bound,
            expected.fri_config.log_last_layer_degree_bound
        );
        assert_eq!(actual.fri_config.fold_step, expected.fri_config.fold_step);
        assert_eq!(actual.lifting_log_size, expected.lifting_log_size);
    }

    #[test]
    fn residual_add_air_proof_round_trips() {
        let input = input();
        let envelope = prove_zkai_d64_residual_add_envelope(&input).expect("residual-add proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d64_residual_add_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn residual_add_rejects_residual_delta_relabeling_as_full_output() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_commitment"] =
            Value::String(ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("must not relabel"));
    }

    #[test]
    fn residual_add_rejects_input_relabeling_as_output() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["input_activation_commitment"] =
            Value::String(ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("input activation commitment"));
    }

    #[test]
    fn residual_add_rejects_input_vector_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["input_q8"][0] = Value::from(25);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("input activation recomputed commitment"));
    }

    #[test]
    fn residual_add_rejects_residual_delta_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_q8"][0] = Value::from(17);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("residual delta recomputed commitment"));
    }

    #[test]
    fn residual_add_rejects_output_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["output_q8"][0] = Value::from(41);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("output activation recomputed commitment"));
    }

    #[test]
    fn residual_add_rejects_row_relation_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][0]["output_q8"] = Value::from(41);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("residual-add row relation drift"));
    }

    #[test]
    fn residual_add_rejects_input_q8_bounds_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["input_q8"][0] = Value::from(Q8_SEMANTIC_ABS_BOUND + 1);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("q8 semantic bound"));
    }

    #[test]
    fn residual_add_rejects_residual_delta_q8_bounds_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_q8"][0] = Value::from(Q8_SEMANTIC_ABS_BOUND + 1);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("q8 semantic bound"));
    }

    #[test]
    fn residual_add_rejects_output_q8_bounds_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["output_q8"][0] = Value::from(Q8_SEMANTIC_ABS_BOUND + 1);
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("q8 semantic bound"));
    }

    #[test]
    fn residual_add_rejects_row_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_add_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "55".repeat(32)));
        let error = zkai_d64_residual_add_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("residual-add row commitment"));
    }

    #[test]
    fn residual_add_rejects_oversized_input_json() {
        let oversized = " ".repeat(ZKAI_D64_RESIDUAL_ADD_MAX_JSON_BYTES + 1);
        let error = zkai_d64_residual_add_input_from_json_str(&oversized).unwrap_err();
        assert!(error.to_string().contains("input JSON exceeds max size"));
    }

    #[test]
    fn residual_add_rejects_oversized_proof_bytes() {
        let input = input();
        let envelope = ZkAiD64ResidualAddEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D64_RESIDUAL_ADD_PROOF_VERSION.to_string(),
            statement_version: ZKAI_D64_RESIDUAL_ADD_STATEMENT_VERSION.to_string(),
            semantic_scope: ZKAI_D64_RESIDUAL_ADD_SEMANTIC_SCOPE.to_string(),
            decision: ZKAI_D64_RESIDUAL_ADD_DECISION.to_string(),
            source_down_projection_proof_version: ZKAI_D64_DOWN_PROJECTION_PROOF_VERSION
                .to_string(),
            input,
            proof: vec![0u8; ZKAI_D64_RESIDUAL_ADD_MAX_PROOF_BYTES + 1],
        };
        let error = verify_zkai_d64_residual_add_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof bytes exceed bounded verifier limit"));
    }

    #[test]
    fn residual_add_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope = prove_zkai_d64_residual_add_envelope(&input).expect("residual proof");
        envelope.input.rows[0].output_q8 += 1;
        let error = verify_zkai_d64_residual_add_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("d64 residual-add proof rejected"));
    }

    #[test]
    fn residual_add_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope = prove_zkai_d64_residual_add_envelope(&input).expect("residual proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d64_residual_add_envelope(&envelope).is_err());
    }

    #[test]
    fn residual_add_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope = prove_zkai_d64_residual_add_envelope(&input).expect("residual proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_residual_add_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn residual_add_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope = prove_zkai_d64_residual_add_envelope(&input).expect("residual proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_residual_add_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }
}
