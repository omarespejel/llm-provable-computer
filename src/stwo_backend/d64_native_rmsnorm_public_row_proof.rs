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

use super::d64_native_export_contract::{
    ZKAI_D64_INPUT_ACTIVATION_COMMITMENT, ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION,
    ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION, ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT,
    ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT, ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D64_REQUIRED_BACKEND_VERSION, ZKAI_D64_STATEMENT_COMMITMENT, ZKAI_D64_TARGET_ID,
    ZKAI_D64_VERIFIER_DOMAIN, ZKAI_D64_WIDTH,
};
use super::d64_native_rmsnorm_slice_contract::{
    ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION, ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION,
    ZKAI_D64_RMS_SCALE_TREE_ROOT,
};

pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_INPUT_SCHEMA: &str =
    "zkai-d64-native-rmsnorm-public-row-air-proof-input-v2";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_INPUT_DECISION: &str =
    "GO_PUBLIC_ROW_INPUT_FOR_D64_RMSNORM_AIR_PROOF";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_PROOF_VERSION: &str =
    "stwo-d64-rmsnorm-public-row-air-proof-v2";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_STATEMENT_VERSION: &str =
    "zkai-d64-rmsnorm-public-row-statement-v1";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_SEMANTIC_SCOPE: &str =
    "d64_rmsnorm_public_rows_bound_to_statement_receipt";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_DECISION: &str = "GO_PUBLIC_ROW_D64_RMSNORM_AIR_PROOF";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_NEXT_BACKEND_STEP: &str =
    "bridge RMSNorm-local normed rows into the next d64 transformer-block relation surface without relabeling them as the full output commitment";
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_PROOF_BYTES: usize = 1_048_576;

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const D64_RMSNORM_LOG_SIZE: u32 = 6;
const D64_Q8_SCALE: i64 = 256;
const D64_RMSNORM_SCALAR_RANGE_BITS: usize = 17;
const ZKAI_D64_RMSNORM_PUBLIC_ROW_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D64_RMSNORM_PUBLIC_ROW_EXPECTED_PROOF_COMMITMENTS: usize = 3;

const COLUMN_IDS: [&str; 9] = [
    "zkai/d64/rmsnorm/index",
    "zkai/d64/rmsnorm/input_q8",
    "zkai/d64/rmsnorm/rms_scale_q8",
    "zkai/d64/rmsnorm/input_square",
    "zkai/d64/rmsnorm/scaled_floor",
    "zkai/d64/rmsnorm/scale_remainder",
    "zkai/d64/rmsnorm/normed_q8",
    "zkai/d64/rmsnorm/norm_remainder",
    "zkai/d64/rmsnorm/rms_q8",
];
const AVERAGE_SQUARE_FLOOR_COLUMN_ID: &str = "zkai/d64/rmsnorm/scalar/average_square_floor";
const SQRT_LOW_DELTA_COLUMN_ID: &str = "zkai/d64/rmsnorm/scalar/sqrt_low_delta";
const SQRT_HIGH_GAP_COLUMN_ID: &str = "zkai/d64/rmsnorm/scalar/sqrt_high_gap";
const RMSNORM_OUTPUT_ROW_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d64-rmsnorm-output-row:v1";

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not private witness privacy",
    "not full d64 block proof",
    "not projection, activation, SwiGLU, down-projection, or residual proof",
    "rms_q8 scalar sqrt inequality is AIR-native only for this public scalar row surface",
    "not proof that private witness rows open to proof_native_parameter_commitment beyond public rms_scale_tree_root recomputation",
    "not binding the full d64 output_activation_commitment from only RMSNorm local rows",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "signed M31 bounds and checked i64 arithmetic for public-row relations",
    "exact integer isqrt recomputation without floating-point sqrt",
    "AIR-native bounded sqrt inequality via 17-bit nonnegative gap decompositions",
    "local RMSNorm output row commitment recomputation before proof verification",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

#[derive(Debug, Clone)]
struct D64RmsnormPublicRowEval {
    log_size: u32,
}

impl FrameworkEval for D64RmsnormPublicRowEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let index = eval.next_trace_mask();
        let input_q8 = eval.next_trace_mask();
        let rms_scale_q8 = eval.next_trace_mask();
        let input_square = eval.next_trace_mask();
        let scaled_floor = eval.next_trace_mask();
        let scale_remainder = eval.next_trace_mask();
        let normed_q8 = eval.next_trace_mask();
        let norm_remainder = eval.next_trace_mask();
        let rms_q8 = eval.next_trace_mask();
        let average_square_floor = eval.next_trace_mask();
        let sqrt_low_delta = eval.next_trace_mask();
        let sqrt_high_gap = eval.next_trace_mask();

        let trace_values = [
            index.clone(),
            input_q8.clone(),
            rms_scale_q8.clone(),
            input_square.clone(),
            scaled_floor.clone(),
            scale_remainder.clone(),
            normed_q8.clone(),
            norm_remainder.clone(),
            rms_q8.clone(),
        ];
        for (column_id, trace_value) in COLUMN_IDS.iter().zip(trace_values) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        for (column_id, trace_value) in [
            (AVERAGE_SQUARE_FLOOR_COLUMN_ID, average_square_floor.clone()),
            (SQRT_LOW_DELTA_COLUMN_ID, sqrt_low_delta.clone()),
            (SQRT_HIGH_GAP_COLUMN_ID, sqrt_high_gap.clone()),
        ] {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }

        let one = E::F::from(BaseField::from(1u32));
        let mut low_delta_bits = E::F::from(BaseField::from(0u32));
        for bit_index in 0..D64_RMSNORM_SCALAR_RANGE_BITS {
            let bit = eval.next_trace_mask();
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(
                &scalar_bit_column_id("low", bit_index),
            ));
            eval.add_constraint(bit.clone() - public_value);
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            low_delta_bits = low_delta_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut high_gap_bits = E::F::from(BaseField::from(0u32));
        for bit_index in 0..D64_RMSNORM_SCALAR_RANGE_BITS {
            let bit = eval.next_trace_mask();
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(
                &scalar_bit_column_id("high", bit_index),
            ));
            eval.add_constraint(bit.clone() - public_value);
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            high_gap_bits = high_gap_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }

        let q8_scale = E::F::from(BaseField::from(D64_Q8_SCALE as u32));
        eval.add_constraint(input_q8.clone() * input_q8.clone() - input_square);
        eval.add_constraint(
            input_q8 * rms_scale_q8 - scaled_floor.clone() * q8_scale.clone() - scale_remainder,
        );
        eval.add_constraint(scaled_floor * q8_scale - normed_q8 * rms_q8.clone() - norm_remainder);
        eval.add_constraint(sqrt_low_delta.clone() - low_delta_bits);
        eval.add_constraint(sqrt_high_gap.clone() - high_gap_bits);
        eval.add_constraint(
            rms_q8.clone() * rms_q8.clone() + sqrt_low_delta - average_square_floor.clone(),
        );
        let next_rms_q8 = rms_q8 + one.clone();
        eval.add_constraint(
            next_rms_q8.clone() * next_rms_q8 - average_square_floor - sqrt_high_gap - one,
        );
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D64RmsnormPublicRow {
    pub index: usize,
    pub input_q8: i64,
    pub rms_scale_q8: i64,
    pub input_square: i64,
    pub scaled_floor: i64,
    pub scale_remainder: i64,
    pub normed_q8: i64,
    pub norm_remainder: i64,
    pub rms_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD64RmsnormPublicRowProofInput {
    pub schema: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub row_count: usize,
    pub scale_q8: i64,
    pub rms_q8: i64,
    pub sum_squares: i64,
    pub average_square_floor: i64,
    pub proof_native_parameter_commitment: String,
    pub normalization_config_commitment: String,
    pub input_activation_commitment: String,
    pub rmsnorm_output_row_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub rms_scale_tree_root: String,
    pub rows: Vec<D64RmsnormPublicRow>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64RmsnormPublicRowProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub source_export_contract_version: String,
    pub source_export_decision: String,
    pub source_rmsnorm_slice_contract_version: String,
    pub source_rmsnorm_slice_decision: String,
    pub input: ZkAiD64RmsnormPublicRowProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct D64RmsnormPublicRowProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d64_rmsnorm_public_row_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD64RmsnormPublicRowProofInput> {
    if raw_json.len() > ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES {
        return Err(public_row_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD64RmsnormPublicRowProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_public_row_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d64_rmsnorm_public_row_envelope(
    input: &ZkAiD64RmsnormPublicRowProofInput,
) -> Result<ZkAiD64RmsnormPublicRowProofEnvelope> {
    validate_public_row_input(input)?;
    Ok(ZkAiD64RmsnormPublicRowProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D64_RMSNORM_PUBLIC_ROW_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D64_RMSNORM_PUBLIC_ROW_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D64_RMSNORM_PUBLIC_ROW_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D64_RMSNORM_PUBLIC_ROW_DECISION.to_string(),
        source_export_contract_version: ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION.to_string(),
        source_export_decision: ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION.to_string(),
        source_rmsnorm_slice_contract_version: ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION
            .to_string(),
        source_rmsnorm_slice_decision: ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION.to_string(),
        input: input.clone(),
        proof: prove_public_rows(input)?,
    })
}

pub fn verify_zkai_d64_rmsnorm_public_row_envelope(
    envelope: &ZkAiD64RmsnormPublicRowProofEnvelope,
) -> Result<bool> {
    validate_public_row_envelope(envelope)?;
    verify_public_rows(&envelope.input, &envelope.proof)
}

fn validate_public_row_envelope(envelope: &ZkAiD64RmsnormPublicRowProofEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(public_row_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_DECISION,
        "decision",
    )?;
    expect_eq(
        &envelope.source_export_contract_version,
        ZKAI_D64_NATIVE_EXPORT_CONTRACT_VERSION,
        "source export contract version",
    )?;
    expect_eq(
        &envelope.source_export_decision,
        ZKAI_D64_NATIVE_EXPORT_CONTRACT_DECISION,
        "source export decision",
    )?;
    expect_eq(
        &envelope.source_rmsnorm_slice_contract_version,
        ZKAI_D64_NATIVE_RMSNORM_SLICE_CONTRACT_VERSION,
        "source rmsnorm slice contract version",
    )?;
    expect_eq(
        &envelope.source_rmsnorm_slice_decision,
        ZKAI_D64_NATIVE_RMSNORM_SLICE_DECISION,
        "source rmsnorm slice decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(public_row_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_PROOF_BYTES {
        return Err(public_row_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_PROOF_BYTES
        )));
    }
    validate_public_row_input(&envelope.input)
}

fn validate_public_row_input(input: &ZkAiD64RmsnormPublicRowProofInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_INPUT_DECISION,
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
    expect_usize(input.row_count, ZKAI_D64_WIDTH, "row count")?;
    expect_i64(input.scale_q8, D64_Q8_SCALE, "scale q8")?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "proof-native parameter commitment",
    )?;
    expect_eq(
        &input.normalization_config_commitment,
        ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT,
        "normalization config commitment",
    )?;
    expect_eq(
        &input.input_activation_commitment,
        ZKAI_D64_INPUT_ACTIVATION_COMMITMENT,
        "input activation commitment",
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
    expect_eq(
        &input.rms_scale_tree_root,
        ZKAI_D64_RMS_SCALE_TREE_ROOT,
        "rms scale tree root",
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
        ZKAI_D64_RMSNORM_PUBLIC_ROW_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    if input.rows.len() != ZKAI_D64_WIDTH {
        return Err(public_row_error(format!(
            "row vector length mismatch: got {}, expected {}",
            input.rows.len(),
            ZKAI_D64_WIDTH
        )));
    }

    let mut sum_squares = 0i64;
    let mut input_values = Vec::with_capacity(input.rows.len());
    let mut normed_values = Vec::with_capacity(input.rows.len());
    let mut scale_values = Vec::with_capacity(input.rows.len());
    for (expected_index, row) in input.rows.iter().enumerate() {
        validate_row(row, expected_index, input.rms_q8)?;
        sum_squares = checked_add_i64(sum_squares, row.input_square, "sum square accumulation")?;
        input_values.push(row.input_q8);
        normed_values.push(row.normed_q8);
        scale_values.push(row.rms_scale_q8);
    }
    expect_i64(input.sum_squares, sum_squares, "sum squares")?;
    let average_square_floor = sum_squares / ZKAI_D64_WIDTH as i64;
    expect_i64(
        input.average_square_floor,
        average_square_floor,
        "average square floor",
    )?;
    if average_square_floor == 0 {
        return Err(public_row_error(
            "average square floor must be positive for public-row rms_q8",
        ));
    }
    expect_i64(input.rms_q8, integer_sqrt(average_square_floor), "rms q8")?;
    scalar_sqrt_witness(input)?;
    expect_eq(
        &sequence_commitment(
            &input_values,
            "ptvm:zkai:d64-input-activation:v1",
            ZKAI_D64_WIDTH,
        ),
        ZKAI_D64_INPUT_ACTIVATION_COMMITMENT,
        "input activation recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &normed_values,
            RMSNORM_OUTPUT_ROW_COMMITMENT_DOMAIN,
            ZKAI_D64_WIDTH,
        ),
        &input.rmsnorm_output_row_commitment,
        "RMSNorm output row recomputed commitment",
    )?;
    let scale_commitment =
        sequence_commitment(&scale_values, "ptvm:zkai:d64-rms-scale:v1", ZKAI_D64_WIDTH);
    expect_eq(
        &normalization_config_commitment(input.rms_q8, &scale_commitment),
        ZKAI_D64_NORMALIZATION_CONFIG_COMMITMENT,
        "normalization config recomputed commitment",
    )?;
    expect_eq(
        &rms_scale_tree_root(&scale_values)?,
        ZKAI_D64_RMS_SCALE_TREE_ROOT,
        "rms scale tree recomputed root",
    )?;
    Ok(())
}

fn validate_row(row: &D64RmsnormPublicRow, expected_index: usize, rms_q8: i64) -> Result<()> {
    expect_usize(row.index, expected_index, "row index")?;
    if rms_q8 <= 0 {
        return Err(public_row_error("rms_q8 must be positive"));
    }
    expect_signed_m31(row.input_q8, "input q8")?;
    expect_signed_m31(row.rms_scale_q8, "rms scale q8")?;
    expect_signed_m31(row.input_square, "input square")?;
    expect_signed_m31(row.scaled_floor, "scaled floor")?;
    expect_signed_m31(row.scale_remainder, "scale remainder")?;
    expect_signed_m31(row.normed_q8, "normed q8")?;
    expect_signed_m31(row.norm_remainder, "norm remainder")?;
    expect_signed_m31(row.rms_q8, "row rms q8")?;
    if row.input_square < 0 {
        return Err(public_row_error("input square must be non-negative"));
    }
    expect_i64(row.rms_q8, rms_q8, "row rms q8")?;
    expect_i64(
        row.input_square,
        checked_mul_i64(row.input_q8, row.input_q8, "input square")?,
        "input square",
    )?;
    let scaled_product = checked_mul_i64(row.input_q8, row.rms_scale_q8, "scaled product")?;
    let scaled_floor_product =
        checked_mul_i64(row.scaled_floor, D64_Q8_SCALE, "scaled floor q8 product")?;
    let scaled_relation_rhs = checked_add_i64(
        scaled_floor_product,
        row.scale_remainder,
        "scaled floor relation",
    )?;
    expect_i64(scaled_product, scaled_relation_rhs, "scaled floor relation")?;
    if !(0..D64_Q8_SCALE).contains(&row.scale_remainder) {
        return Err(public_row_error("scale remainder is out of q8 range"));
    }
    let normed_product = checked_mul_i64(row.normed_q8, row.rms_q8, "normed rms product")?;
    let normed_relation_rhs =
        checked_add_i64(normed_product, row.norm_remainder, "normed relation")?;
    expect_i64(scaled_floor_product, normed_relation_rhs, "normed relation")?;
    if !(0..row.rms_q8).contains(&row.norm_remainder) {
        return Err(public_row_error("norm remainder is out of rms range"));
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct ScalarSqrtWitness {
    sqrt_low_delta: i64,
    sqrt_high_gap: i64,
    sqrt_low_delta_bits: [u8; D64_RMSNORM_SCALAR_RANGE_BITS],
    sqrt_high_gap_bits: [u8; D64_RMSNORM_SCALAR_RANGE_BITS],
}

fn scalar_sqrt_witness(input: &ZkAiD64RmsnormPublicRowProofInput) -> Result<ScalarSqrtWitness> {
    if input.rms_q8 <= 0 {
        return Err(public_row_error(
            "rms_q8 must be positive for scalar sqrt witness",
        ));
    }
    let rms_square = checked_mul_i64(input.rms_q8, input.rms_q8, "rms_q8 square")?;
    let next_rms = checked_add_i64(input.rms_q8, 1, "next rms_q8")?;
    let next_square = checked_mul_i64(next_rms, next_rms, "next rms_q8 square")?;
    let sqrt_low_delta = input
        .average_square_floor
        .checked_sub(rms_square)
        .ok_or_else(|| public_row_error("sqrt low delta underflow"))?;
    let sqrt_high_gap = next_square
        .checked_sub(input.average_square_floor)
        .and_then(|value| value.checked_sub(1))
        .ok_or_else(|| public_row_error("sqrt high gap underflow"))?;
    Ok(ScalarSqrtWitness {
        sqrt_low_delta,
        sqrt_high_gap,
        sqrt_low_delta_bits: decompose_scalar_gap(sqrt_low_delta, "sqrt low delta")?,
        sqrt_high_gap_bits: decompose_scalar_gap(sqrt_high_gap, "sqrt high gap")?,
    })
}

fn decompose_scalar_gap(value: i64, label: &str) -> Result<[u8; D64_RMSNORM_SCALAR_RANGE_BITS]> {
    if value < 0 {
        return Err(public_row_error(format!("{label} must be non-negative")));
    }
    if value >= (1i64 << D64_RMSNORM_SCALAR_RANGE_BITS) {
        return Err(public_row_error(format!(
            "{label} exceeds {}-bit scalar range",
            D64_RMSNORM_SCALAR_RANGE_BITS
        )));
    }
    let mut bits = [0u8; D64_RMSNORM_SCALAR_RANGE_BITS];
    for (index, bit) in bits.iter_mut().enumerate() {
        *bit = ((value >> index) & 1) as u8;
    }
    Ok(bits)
}

fn prove_public_rows(input: &ZkAiD64RmsnormPublicRowProofInput) -> Result<Vec<u8>> {
    let component = public_row_component();
    let config = public_row_pcs_config();
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
    tree_builder.extend_evals(public_row_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(public_row_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "d64 RMSNorm public-row AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D64RmsnormPublicRowProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_public_rows(input: &ZkAiD64RmsnormPublicRowProofInput, proof: &[u8]) -> Result<bool> {
    let payload: D64RmsnormPublicRowProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_public_row_pcs_config(stark_proof.config)?;
    let component = public_row_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D64_RMSNORM_PUBLIC_ROW_EXPECTED_TRACE_COMMITMENTS {
        return Err(public_row_error(format!(
            "internal public-row component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D64_RMSNORM_PUBLIC_ROW_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    // The v1 proof format is intentionally fail-closed: any extra commitment
    // roots are a shape change that should bump the proof version.
    if stark_proof.commitments.len() != ZKAI_D64_RMSNORM_PUBLIC_ROW_EXPECTED_PROOF_COMMITMENTS {
        return Err(public_row_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D64_RMSNORM_PUBLIC_ROW_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = public_row_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(public_row_error(
            "preprocessed row commitment does not match checked public rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(public_row_error(
            "base row commitment does not match checked public rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    Ok(verify(&[&component], channel, commitment_scheme, stark_proof).is_ok())
}

fn validate_public_row_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    super::validate_publication_v1_pcs_config(actual, "d64 RMSNorm public-row proof")
        .map_err(|error| public_row_error(error.to_string()))
}

fn public_row_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn public_row_commitment_roots(
    input: &ZkAiD64RmsnormPublicRowProofInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = public_row_component();
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
    tree_builder.extend_evals(public_row_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(public_row_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn public_row_component() -> FrameworkComponent<D64RmsnormPublicRowEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D64RmsnormPublicRowEval {
            log_size: D64_RMSNORM_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn public_row_trace(
    input: &ZkAiD64RmsnormPublicRowProofInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D64_RMSNORM_LOG_SIZE).circle_domain();
    let rows = &input.rows;
    let scalar_witness =
        scalar_sqrt_witness(input).expect("validated d64 RMSNorm scalar sqrt witness");
    let mut columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.index)).collect(),
        rows.iter().map(|row| field_i64(row.input_q8)).collect(),
        rows.iter().map(|row| field_i64(row.rms_scale_q8)).collect(),
        rows.iter().map(|row| field_i64(row.input_square)).collect(),
        rows.iter().map(|row| field_i64(row.scaled_floor)).collect(),
        rows.iter()
            .map(|row| field_i64(row.scale_remainder))
            .collect(),
        rows.iter().map(|row| field_i64(row.normed_q8)).collect(),
        rows.iter()
            .map(|row| field_i64(row.norm_remainder))
            .collect(),
        rows.iter().map(|row| field_i64(row.rms_q8)).collect(),
    ];
    columns.push(vec![field_i64(input.average_square_floor); ZKAI_D64_WIDTH]);
    columns.push(vec![
        field_i64(scalar_witness.sqrt_low_delta);
        ZKAI_D64_WIDTH
    ]);
    columns.push(vec![
        field_i64(scalar_witness.sqrt_high_gap);
        ZKAI_D64_WIDTH
    ]);
    for bit in scalar_witness.sqrt_low_delta_bits {
        columns.push(vec![field_i64(i64::from(bit)); ZKAI_D64_WIDTH]);
    }
    for bit in scalar_witness.sqrt_high_gap_bits {
        columns.push(vec![field_i64(i64::from(bit)); ZKAI_D64_WIDTH]);
    }
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
    let mut ids: Vec<PreProcessedColumnId> =
        COLUMN_IDS.into_iter().map(preprocessed_column_id).collect();
    ids.push(preprocessed_column_id(AVERAGE_SQUARE_FLOOR_COLUMN_ID));
    ids.push(preprocessed_column_id(SQRT_LOW_DELTA_COLUMN_ID));
    ids.push(preprocessed_column_id(SQRT_HIGH_GAP_COLUMN_ID));
    for bit_index in 0..D64_RMSNORM_SCALAR_RANGE_BITS {
        ids.push(preprocessed_column_id(&scalar_bit_column_id(
            "low", bit_index,
        )));
    }
    for bit_index in 0..D64_RMSNORM_SCALAR_RANGE_BITS {
        ids.push(preprocessed_column_id(&scalar_bit_column_id(
            "high", bit_index,
        )));
    }
    ids
}

fn preprocessed_column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

fn scalar_bit_column_id(kind: &str, bit_index: usize) -> String {
    format!("zkai/d64/rmsnorm/scalar/sqrt_{kind}_bit_{bit_index:02}")
}

fn field_usize(value: usize) -> BaseField {
    BaseField::from(value as u32)
}

fn field_i64(value: i64) -> BaseField {
    BaseField::from(value.rem_euclid(M31_MODULUS) as u32)
}

fn integer_sqrt(value: i64) -> i64 {
    if value <= 0 {
        return 0;
    }
    let n = value as u128;
    let mut x = n;
    let mut y = (x + 1) / 2;
    while y < x {
        x = y;
        y = (x + n / x) / 2;
    }
    x as i64
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

fn normalization_config_commitment(rms_q8: i64, scale_commitment: &str) -> String {
    let payload = format!(
        "{{\"rms_q8\":{},\"rms_square_rows\":{},\"scale_commitment\":\"{}\"}}",
        rms_q8, ZKAI_D64_WIDTH, scale_commitment
    );
    blake2b_commitment_bytes(payload.as_bytes(), "ptvm:zkai:d64-rmsnorm-config:v1")
}

fn rms_scale_tree_root(scale_values: &[i64]) -> Result<String> {
    if scale_values.is_empty() {
        return Err(public_row_error("cannot commit empty RMS scale tree"));
    }
    let mut level: Vec<String> = scale_values
        .iter()
        .enumerate()
        .map(|(index, value)| {
            let leaf_json = format!(
                "{{\"index\":{},\"kind\":\"rms_scale\",\"value_q8\":{}}}",
                index, value
            );
            blake2b_hex(leaf_json.as_bytes(), "ptvm:zkai:d64:rms-scale-leaf:v1")
        })
        .collect();
    while level.len() > 1 {
        if level.len() % 2 == 1 {
            let last = level.last().expect("non-empty merkle level").to_string();
            level.push(last);
        }
        let mut next = Vec::with_capacity(level.len() / 2);
        for pair in level.chunks_exact(2) {
            let mut bytes = parse_blake2b_hex(&pair[0])?;
            bytes.extend(parse_blake2b_hex(&pair[1])?);
            next.push(blake2b_hex(&bytes, "ptvm:zkai:d64:rms-scale-tree:v1"));
        }
        level = next;
    }
    Ok(format!("blake2b-256:{}", level[0]))
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

fn parse_blake2b_hex(value: &str) -> Result<Vec<u8>> {
    let raw = value.strip_prefix("blake2b-256:").unwrap_or(value);
    if raw.len() != 64 {
        return Err(public_row_error("invalid blake2b hex length"));
    }
    let mut out = Vec::with_capacity(32);
    for index in (0..raw.len()).step_by(2) {
        let byte = u8::from_str_radix(&raw[index..index + 2], 16)
            .map_err(|_| public_row_error("invalid blake2b hex"))?;
        out.push(byte);
    }
    Ok(out)
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
        return Err(public_row_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(public_row_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(public_row_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(public_row_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
}

fn checked_mul_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_mul(rhs)
        .ok_or_else(|| public_row_error(format!("{label} overflow")))
}

fn checked_add_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_add(rhs)
        .ok_or_else(|| public_row_error(format!("{label} overflow")))
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
        return Err(public_row_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn public_row_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 RMSNorm public-row proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.json"
    );

    fn input() -> ZkAiD64RmsnormPublicRowProofInput {
        zkai_d64_rmsnorm_public_row_input_from_json_str(INPUT_JSON).expect("public row input")
    }

    #[test]
    fn public_row_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(input.rows.len(), ZKAI_D64_WIDTH);
        assert_eq!(input.rms_q8, 115);
        assert_eq!(input.sum_squares, 849_454);
        assert_eq!(input.average_square_floor, 13_272);
        assert_eq!(input.rows[0].input_q8, 24);
        assert_eq!(input.rows[0].normed_q8, 46);
    }

    #[test]
    fn public_row_air_proof_round_trips() {
        let input = input();
        let envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn public_row_pcs_config_uses_shared_publication_v1_profile() {
        let actual = public_row_pcs_config();
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
    fn public_row_air_proof_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        envelope.input.rows[0].input_q8 += 1;
        let error = verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("d64 RMSNorm public-row proof rejected"));
    }

    #[test]
    fn public_row_input_rejects_rms_scalar_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rms_q8"] = Value::from(116);
        value["rows"][0]["rms_q8"] = Value::from(116);
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("d64 RMSNorm public-row proof rejected"));
    }

    #[test]
    fn scalar_sqrt_witness_decomposes_checked_inequality_gaps() {
        let input = input();
        let witness = scalar_sqrt_witness(&input).expect("scalar sqrt witness");

        assert_eq!(witness.sqrt_low_delta, 47);
        assert_eq!(witness.sqrt_high_gap, 183);
        assert_eq!(witness.sqrt_low_delta_bits[0], 1);
        assert_eq!(witness.sqrt_low_delta_bits[4], 0);
        assert_eq!(witness.sqrt_low_delta_bits[5], 1);
        assert_eq!(witness.sqrt_high_gap_bits[0], 1);
        assert_eq!(witness.sqrt_high_gap_bits[2], 1);
        assert_eq!(witness.sqrt_high_gap_bits[7], 1);
    }

    #[test]
    fn public_row_input_rejects_average_square_floor_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["average_square_floor"] = Value::from(13_273);
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("average square floor"));
    }

    #[test]
    fn public_row_input_rejects_rmsnorm_output_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rmsnorm_output_row_commitment"] =
            Value::from(format!("blake2b-256:{}", "77".repeat(32)));
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("RMSNorm output row recomputed commitment"));
    }

    #[test]
    fn scalar_sqrt_witness_rejects_out_of_bound_gap_surface() {
        let error =
            decompose_scalar_gap(1 << D64_RMSNORM_SCALAR_RANGE_BITS, "sqrt low delta").unwrap_err();
        assert!(error.to_string().contains("sqrt low delta exceeds"));
    }

    #[test]
    fn public_row_input_rejects_remainder_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][1]["scale_remainder"] = Value::from(0);
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("scaled floor relation"));
    }

    #[test]
    fn public_row_input_rejects_input_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][0]["input_q8"] = Value::from(25);
        value["rows"][0]["input_square"] = Value::from(625);
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("d64 RMSNorm public-row proof rejected"));
    }

    #[test]
    fn public_row_input_rejects_checked_integer_overflow_surface() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][0]["input_q8"] = Value::from(i64::MAX);
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("signed M31 verifier bound"));
    }

    #[test]
    fn public_row_input_rejects_non_claim_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["non_claims"]
            .as_array_mut()
            .expect("non claims")
            .pop();
        let error = zkai_d64_rmsnorm_public_row_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("non claims"));
    }

    #[test]
    fn public_row_air_proof_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).is_err());
    }

    #[test]
    fn public_row_air_proof_rejects_short_commitment_vector() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments")
            .pop();
        payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments")
            .pop();
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("proof commitment count"));
    }

    #[test]
    fn public_row_air_proof_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("proof commitment count"));
    }

    #[test]
    fn public_row_air_proof_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }

    #[test]
    fn public_row_air_proof_rejects_oversized_proof_before_deserialization() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_public_row_envelope(&input).expect("public-row proof");
        envelope.proof = vec![b'0'; ZKAI_D64_RMSNORM_PUBLIC_ROW_MAX_PROOF_BYTES + 1];
        let error = verify_zkai_d64_rmsnorm_public_row_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("proof bytes exceed"));
    }

    #[test]
    fn exact_integer_sqrt_stays_bounded_without_floating_point() {
        for value in [0, 1, 2, 3, 4, 13_272, i64::MAX] {
            let root = integer_sqrt(value);
            assert!((root as i128) * (root as i128) <= value as i128);
            assert!(((root + 1) as i128) * ((root + 1) as i128) > value as i128);
        }
    }
}
