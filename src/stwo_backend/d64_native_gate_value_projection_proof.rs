use std::sync::OnceLock;

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
    ZKAI_D64_FF_DIM, ZKAI_D64_GATE_PROJECTION_MUL_ROWS, ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT,
    ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT, ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D64_REQUIRED_BACKEND_VERSION, ZKAI_D64_STATEMENT_COMMITMENT, ZKAI_D64_TARGET_ID,
    ZKAI_D64_VALUE_PROJECTION_MUL_ROWS, ZKAI_D64_VERIFIER_DOMAIN, ZKAI_D64_WIDTH,
};
use super::d64_native_rmsnorm_to_projection_bridge_proof::{
    ZKAI_D64_PROJECTION_INPUT_ROW_COMMITMENT, ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
};

pub const ZKAI_D64_GATE_VALUE_PROJECTION_INPUT_SCHEMA: &str =
    "zkai-d64-gate-value-projection-air-proof-input-v1";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D64_GATE_VALUE_PROJECTION_AIR_PROOF";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION: &str =
    "stwo-d64-gate-value-projection-air-proof-v1";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_STATEMENT_VERSION: &str =
    "zkai-d64-gate-value-projection-statement-v1";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_SEMANTIC_SCOPE: &str =
    "d64_gate_value_projection_rows_bound_to_projection_input_receipt";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_DECISION: &str = "GO_D64_GATE_VALUE_PROJECTION_AIR_PROOF";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_NEXT_BACKEND_STEP: &str =
    "encode activation/SwiGLU rows that consume gate_value_projection_output_commitment and produce hidden_activation_commitment";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D64_GATE_VALUE_PROJECTION_MAX_PROOF_BYTES: usize = 16_777_216;
pub const ZKAI_D64_GATE_MATRIX_ROOT: &str =
    "blake2b-256:c7f5f490cc4140756951d0305a4786a1de9a282687c05a161ea04bd658657cfa";
pub const ZKAI_D64_VALUE_MATRIX_ROOT: &str =
    "blake2b-256:e63d0d6839c92386e50314370e8b13dee0aa68c624f8ce88c34f6a4c1a2c3174";
pub const ZKAI_D64_GATE_PROJECTION_OUTPUT_COMMITMENT: &str =
    "blake2b-256:11d4782e19becb15a541ff542971789049c802277255410db88b6423998b1ef8";
pub const ZKAI_D64_VALUE_PROJECTION_OUTPUT_COMMITMENT: &str =
    "blake2b-256:71599f8691b781d78edddac94f09c3b4c1d572e20013c6122faea8d83abf724d";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT: &str =
    "blake2b-256:d7127c1002acd821428da00b5ca1aabdb5a43809d6834b9b6b08d13d8e9f8e02";
pub const ZKAI_D64_GATE_VALUE_PROJECTION_MUL_ROW_COMMITMENT: &str =
    "blake2b-256:2ea591b42ef4a2bc6c5c88f8dc33003bb4a0cf357b57f01e1c5b7dce822035db";

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const WEIGHT_GENERATOR_SEED: &str = "zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05-v1";
const D64_GATE_VALUE_LOG_SIZE: u32 = 15;
const GATE_SELECTOR: usize = 0;
const VALUE_SELECTOR: usize = 1;
const ZKAI_D64_GATE_VALUE_ROW_COUNT: usize =
    ZKAI_D64_GATE_PROJECTION_MUL_ROWS + ZKAI_D64_VALUE_PROJECTION_MUL_ROWS;
const ZKAI_D64_GATE_VALUE_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D64_GATE_VALUE_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d64-projection-input-row:v1";
const GATE_PROJECTION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-gate-projection-output:v1";
const VALUE_PROJECTION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-value-projection-output:v1";
const GATE_VALUE_PROJECTION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-gate-value-projection-output:v1";
const GATE_VALUE_PROJECTION_MUL_ROW_DOMAIN: &str =
    "ptvm:zkai:d64-gate-value-projection-mul-rows:v1";
const MATRIX_ROW_LEAF_DOMAIN: &str = "ptvm:zkai:d64:param-matrix-row-leaf:v1";
const MATRIX_ROW_TREE_DOMAIN: &str = "ptvm:zkai:d64:param-matrix-row-tree:v1";
static EXPECTED_GATE_MATRIX_ROOT: OnceLock<String> = OnceLock::new();
static EXPECTED_VALUE_MATRIX_ROOT: OnceLock<String> = OnceLock::new();

const COLUMN_IDS: [&str; 7] = [
    "zkai/d64/gate-value-projection/row-index",
    "zkai/d64/gate-value-projection/matrix-selector",
    "zkai/d64/gate-value-projection/output-index",
    "zkai/d64/gate-value-projection/input-index",
    "zkai/d64/gate-value-projection/projection-input-q8",
    "zkai/d64/gate-value-projection/weight-q8",
    "zkai/d64/gate-value-projection/product-q8",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not full d64 block proof",
    "not activation or SwiGLU proof",
    "not down projection proof",
    "not residual proof",
    "not binding the full d64 output_activation_commitment",
    "output aggregation is verifier-recomputed from checked public multiplication rows, not a private AIR aggregation claim",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "projection input row commitment recomputation before proof verification",
    "gate/value projection multiplication row commitment recomputation before proof verification",
    "gate/value output commitment recomputation before proof verification",
    "AIR multiplication relation for every checked gate/value row",
    "gate and value matrix roots recomputed from checked row weights",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

#[derive(Debug, Clone)]
struct D64GateValueProjectionEval {
    log_size: u32,
}

impl FrameworkEval for D64GateValueProjectionEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let row_index = eval.next_trace_mask();
        let matrix_selector = eval.next_trace_mask();
        let output_index = eval.next_trace_mask();
        let input_index = eval.next_trace_mask();
        let projection_input_q8 = eval.next_trace_mask();
        let weight_q8 = eval.next_trace_mask();
        let product_q8 = eval.next_trace_mask();

        for (column_id, trace_value) in COLUMN_IDS.iter().zip([
            row_index,
            matrix_selector,
            output_index,
            input_index,
            projection_input_q8.clone(),
            weight_q8.clone(),
            product_q8.clone(),
        ]) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        eval.add_constraint(projection_input_q8 * weight_q8 - product_q8);
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D64GateValueProjectionMulRow {
    pub row_index: usize,
    pub matrix: String,
    pub matrix_selector: usize,
    pub output_index: usize,
    pub input_index: usize,
    pub projection_input_q8: i64,
    pub weight_q8: i64,
    pub product_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD64GateValueProjectionProofInput {
    pub schema: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub ff_dim: usize,
    pub row_count: usize,
    pub gate_projection_mul_rows: usize,
    pub value_projection_mul_rows: usize,
    pub source_bridge_proof_version: String,
    pub source_projection_input_row_commitment: String,
    pub gate_matrix_root: String,
    pub value_matrix_root: String,
    pub proof_native_parameter_commitment: String,
    pub gate_projection_output_commitment: String,
    pub value_projection_output_commitment: String,
    pub gate_value_projection_output_commitment: String,
    pub gate_value_projection_mul_row_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub projection_input_q8: Vec<i64>,
    pub gate_projection_q8: Vec<i64>,
    pub value_projection_q8: Vec<i64>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64GateValueProjectionEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub source_bridge_proof_version: String,
    pub input: ZkAiD64GateValueProjectionProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct D64GateValueProjectionProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d64_gate_value_projection_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD64GateValueProjectionProofInput> {
    if raw_json.len() > ZKAI_D64_GATE_VALUE_PROJECTION_MAX_JSON_BYTES {
        return Err(gate_value_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D64_GATE_VALUE_PROJECTION_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD64GateValueProjectionProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_gate_value_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d64_gate_value_projection_envelope(
    input: &ZkAiD64GateValueProjectionProofInput,
) -> Result<ZkAiD64GateValueProjectionEnvelope> {
    validate_gate_value_input(input)?;
    Ok(ZkAiD64GateValueProjectionEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D64_GATE_VALUE_PROJECTION_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D64_GATE_VALUE_PROJECTION_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D64_GATE_VALUE_PROJECTION_DECISION.to_string(),
        source_bridge_proof_version: ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION
            .to_string(),
        input: input.clone(),
        proof: prove_gate_value_rows(input)?,
    })
}

pub fn verify_zkai_d64_gate_value_projection_envelope(
    envelope: &ZkAiD64GateValueProjectionEnvelope,
) -> Result<bool> {
    validate_gate_value_envelope(envelope)?;
    verify_gate_value_rows(&envelope.input, &envelope.proof)
}

fn validate_gate_value_envelope(envelope: &ZkAiD64GateValueProjectionEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(gate_value_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D64_GATE_VALUE_PROJECTION_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D64_GATE_VALUE_PROJECTION_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D64_GATE_VALUE_PROJECTION_DECISION,
        "decision",
    )?;
    expect_eq(
        &envelope.source_bridge_proof_version,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
        "source bridge proof version",
    )?;
    if envelope.proof.is_empty() {
        return Err(gate_value_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D64_GATE_VALUE_PROJECTION_MAX_PROOF_BYTES {
        return Err(gate_value_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D64_GATE_VALUE_PROJECTION_MAX_PROOF_BYTES
        )));
    }
    validate_gate_value_input(&envelope.input)
}

fn validate_gate_value_input(input: &ZkAiD64GateValueProjectionProofInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D64_GATE_VALUE_PROJECTION_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D64_GATE_VALUE_PROJECTION_INPUT_DECISION,
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
    expect_usize(input.ff_dim, ZKAI_D64_FF_DIM, "ff dim")?;
    expect_usize(input.row_count, ZKAI_D64_GATE_VALUE_ROW_COUNT, "row count")?;
    expect_usize(
        input.gate_projection_mul_rows,
        ZKAI_D64_GATE_PROJECTION_MUL_ROWS,
        "gate projection mul rows",
    )?;
    expect_usize(
        input.value_projection_mul_rows,
        ZKAI_D64_VALUE_PROJECTION_MUL_ROWS,
        "value projection mul rows",
    )?;
    expect_eq(
        &input.source_bridge_proof_version,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
        "source bridge proof version",
    )?;
    expect_eq(
        &input.source_projection_input_row_commitment,
        ZKAI_D64_PROJECTION_INPUT_ROW_COMMITMENT,
        "source projection input row commitment",
    )?;
    let expected_gate_matrix_root = expected_gate_matrix_root();
    let expected_value_matrix_root = expected_value_matrix_root();
    expect_eq(
        expected_gate_matrix_root,
        ZKAI_D64_GATE_MATRIX_ROOT,
        "gate matrix root generator constant",
    )?;
    expect_eq(
        &input.gate_matrix_root,
        expected_gate_matrix_root,
        "gate matrix root",
    )?;
    expect_eq(
        expected_value_matrix_root,
        ZKAI_D64_VALUE_MATRIX_ROOT,
        "value matrix root generator constant",
    )?;
    expect_eq(
        &input.value_matrix_root,
        expected_value_matrix_root,
        "value matrix root",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "proof-native parameter commitment",
    )?;
    expect_eq(
        &input.gate_projection_output_commitment,
        ZKAI_D64_GATE_PROJECTION_OUTPUT_COMMITMENT,
        "gate projection output commitment",
    )?;
    expect_eq(
        &input.value_projection_output_commitment,
        ZKAI_D64_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "value projection output commitment",
    )?;
    if input.gate_value_projection_output_commitment == ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT {
        return Err(gate_value_error(
            "gate/value projection output commitment must not relabel as full output activation commitment",
        ));
    }
    expect_eq(
        &input.gate_value_projection_output_commitment,
        ZKAI_D64_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "gate/value projection output commitment",
    )?;
    expect_eq(
        &input.gate_value_projection_mul_row_commitment,
        ZKAI_D64_GATE_VALUE_PROJECTION_MUL_ROW_COMMITMENT,
        "gate/value projection row commitment",
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
        ZKAI_D64_GATE_VALUE_PROJECTION_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    if input.projection_input_q8.len() != ZKAI_D64_WIDTH {
        return Err(gate_value_error(format!(
            "projection input vector length mismatch: got {}, expected {}",
            input.projection_input_q8.len(),
            ZKAI_D64_WIDTH
        )));
    }
    if input.gate_projection_q8.len() != ZKAI_D64_FF_DIM {
        return Err(gate_value_error(
            "gate projection output vector length mismatch",
        ));
    }
    if input.value_projection_q8.len() != ZKAI_D64_FF_DIM {
        return Err(gate_value_error(
            "value projection output vector length mismatch",
        ));
    }

    for (index, value) in input.projection_input_q8.iter().enumerate() {
        expect_signed_m31(*value, &format!("projection input q8 {index}"))?;
    }
    let rows = build_rows(&input.projection_input_q8)?;
    let mut gate_accumulators = vec![0i64; ZKAI_D64_FF_DIM];
    let mut value_accumulators = vec![0i64; ZKAI_D64_FF_DIM];
    let mut gate_rows = 0usize;
    let mut value_rows = 0usize;
    for (expected_row_index, row) in rows.iter().enumerate() {
        validate_gate_value_row(row, expected_row_index)?;
        let product =
            checked_mul_i64(row.projection_input_q8, row.weight_q8, "projection product")?;
        expect_i64(row.product_q8, product, "projection product relation")?;
        expect_i64(
            row.projection_input_q8,
            input.projection_input_q8[row.input_index],
            "projection input value",
        )?;
        match row.matrix_selector {
            GATE_SELECTOR => {
                gate_rows += 1;
                gate_accumulators[row.output_index] = checked_add_i64(
                    gate_accumulators[row.output_index],
                    row.product_q8,
                    "gate projection accumulator",
                )?;
            }
            VALUE_SELECTOR => {
                value_rows += 1;
                value_accumulators[row.output_index] = checked_add_i64(
                    value_accumulators[row.output_index],
                    row.product_q8,
                    "value projection accumulator",
                )?;
            }
            _ => return Err(gate_value_error("matrix selector drift")),
        }
    }
    expect_usize(
        gate_rows,
        ZKAI_D64_GATE_PROJECTION_MUL_ROWS,
        "gate row count",
    )?;
    expect_usize(
        value_rows,
        ZKAI_D64_VALUE_PROJECTION_MUL_ROWS,
        "value row count",
    )?;
    expect_eq(
        &sequence_commitment(
            &input.projection_input_q8,
            PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN,
            ZKAI_D64_WIDTH,
        ),
        &input.source_projection_input_row_commitment,
        "projection input recomputed commitment",
    )?;
    let recomputed_gate = divide_accumulators(&gate_accumulators)?;
    let recomputed_value = divide_accumulators(&value_accumulators)?;
    if recomputed_gate != input.gate_projection_q8 {
        return Err(gate_value_error("gate projection output drift"));
    }
    if recomputed_value != input.value_projection_q8 {
        return Err(gate_value_error("value projection output drift"));
    }
    expect_eq(
        &sequence_commitment(
            &input.gate_projection_q8,
            GATE_PROJECTION_OUTPUT_DOMAIN,
            ZKAI_D64_FF_DIM,
        ),
        &input.gate_projection_output_commitment,
        "gate projection output recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &input.value_projection_q8,
            VALUE_PROJECTION_OUTPUT_DOMAIN,
            ZKAI_D64_FF_DIM,
        ),
        &input.value_projection_output_commitment,
        "value projection output recomputed commitment",
    )?;
    expect_eq(
        &gate_value_output_commitment(&input.gate_projection_q8, &input.value_projection_q8),
        &input.gate_value_projection_output_commitment,
        "gate/value projection output recomputed commitment",
    )?;
    expect_eq(
        &rows_commitment(&rows),
        &input.gate_value_projection_mul_row_commitment,
        "gate/value projection row recomputed commitment",
    )?;
    Ok(())
}

fn validate_gate_value_row(
    row: &D64GateValueProjectionMulRow,
    expected_index: usize,
) -> Result<()> {
    expect_usize(row.row_index, expected_index, "row index")?;
    match row.matrix.as_str() {
        "gate" => expect_usize(row.matrix_selector, GATE_SELECTOR, "gate matrix selector")?,
        "value" => expect_usize(row.matrix_selector, VALUE_SELECTOR, "value matrix selector")?,
        _ => return Err(gate_value_error("matrix label drift")),
    }
    if row.output_index >= ZKAI_D64_FF_DIM {
        return Err(gate_value_error("output index drift"));
    }
    if row.input_index >= ZKAI_D64_WIDTH {
        return Err(gate_value_error("input index drift"));
    }
    expect_signed_m31(row.projection_input_q8, "projection input q8")?;
    expect_signed_m31(row.weight_q8, "projection weight q8")?;
    expect_signed_m31(row.product_q8, "projection product q8")?;
    let expected_matrix_selector = if row.row_index < ZKAI_D64_GATE_PROJECTION_MUL_ROWS {
        GATE_SELECTOR
    } else {
        VALUE_SELECTOR
    };
    expect_usize(
        row.matrix_selector,
        expected_matrix_selector,
        "row-order matrix selector",
    )?;
    let expected_local = if row.matrix_selector == GATE_SELECTOR {
        row.row_index
    } else {
        row.row_index - ZKAI_D64_GATE_PROJECTION_MUL_ROWS
    };
    expect_usize(
        row.output_index,
        expected_local / ZKAI_D64_WIDTH,
        "row-order output index",
    )?;
    expect_usize(
        row.input_index,
        expected_local % ZKAI_D64_WIDTH,
        "row-order input index",
    )?;
    Ok(())
}

fn divide_accumulators(accumulators: &[i64]) -> Result<Vec<i64>> {
    let mut out = Vec::with_capacity(accumulators.len());
    for value in accumulators {
        out.push(value.div_euclid(ZKAI_D64_WIDTH as i64));
    }
    Ok(out)
}

fn build_rows(inputs: &[i64]) -> Result<Vec<D64GateValueProjectionMulRow>> {
    if inputs.len() != ZKAI_D64_WIDTH {
        return Err(gate_value_error("projection input vector length mismatch"));
    }
    let mut rows = Vec::with_capacity(ZKAI_D64_GATE_VALUE_ROW_COUNT);
    let mut row_index = 0usize;
    for (matrix, matrix_selector) in [("gate", GATE_SELECTOR), ("value", VALUE_SELECTOR)] {
        for output_index in 0..ZKAI_D64_FF_DIM {
            for (input_index, projection_input_q8) in inputs.iter().enumerate() {
                let weight_q8 = weight_value(matrix, output_index, input_index)?;
                let product_q8 =
                    checked_mul_i64(*projection_input_q8, weight_q8, "projection product")?;
                rows.push(D64GateValueProjectionMulRow {
                    row_index,
                    matrix: matrix.to_string(),
                    matrix_selector,
                    output_index,
                    input_index,
                    projection_input_q8: *projection_input_q8,
                    weight_q8,
                    product_q8,
                });
                row_index += 1;
            }
        }
    }
    Ok(rows)
}

fn weight_value(matrix: &str, row: usize, col: usize) -> Result<i64> {
    if !matches!(matrix, "gate" | "value") {
        return Err(gate_value_error("unknown projection matrix"));
    }
    deterministic_int(&format!("{matrix}_weight_q8"), &[row, col], -8, 8)
}

fn deterministic_int(
    label: &str,
    indices: &[usize],
    min_value: i64,
    max_value: i64,
) -> Result<i64> {
    if min_value > max_value {
        return Err(gate_value_error("invalid deterministic integer range"));
    }
    let mut parts = Vec::with_capacity(indices.len() + 2);
    parts.push(WEIGHT_GENERATOR_SEED.to_string());
    parts.push(label.to_string());
    parts.extend(indices.iter().map(|index| index.to_string()));
    let payload = parts.join(":");
    let mut hasher = Sha256::new();
    ShaDigest::update(&mut hasher, payload.as_bytes());
    let digest = hasher.finalize();
    let mut first_eight = [0u8; 8];
    first_eight.copy_from_slice(&digest[..8]);
    let raw = u64::from_be_bytes(first_eight);
    let width = (max_value - min_value + 1) as u64;
    Ok(min_value + (raw % width) as i64)
}

fn prove_gate_value_rows(input: &ZkAiD64GateValueProjectionProofInput) -> Result<Vec<u8>> {
    let component = gate_value_component();
    let config = gate_value_pcs_config();
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
    tree_builder.extend_evals(gate_value_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(gate_value_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "d64 gate/value projection AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D64GateValueProjectionProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_gate_value_rows(
    input: &ZkAiD64GateValueProjectionProofInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D64GateValueProjectionProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_gate_value_pcs_config(stark_proof.config)?;
    let component = gate_value_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D64_GATE_VALUE_EXPECTED_TRACE_COMMITMENTS {
        return Err(gate_value_error(format!(
            "internal gate/value component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D64_GATE_VALUE_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D64_GATE_VALUE_EXPECTED_PROOF_COMMITMENTS {
        return Err(gate_value_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D64_GATE_VALUE_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = gate_value_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(gate_value_error(
            "preprocessed row commitment does not match checked gate/value rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(gate_value_error(
            "base row commitment does not match checked gate/value rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| gate_value_error(format!("STARK verification failed: {error}")))
}

fn validate_gate_value_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    super::validate_publication_v1_pcs_config(actual, "d64 gate/value projection proof")
        .map_err(|error| gate_value_error(error.to_string()))
}

fn gate_value_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn gate_value_commitment_roots(
    input: &ZkAiD64GateValueProjectionProofInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = gate_value_component();
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
    tree_builder.extend_evals(gate_value_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(gate_value_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn gate_value_component() -> FrameworkComponent<D64GateValueProjectionEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D64GateValueProjectionEval {
            log_size: D64_GATE_VALUE_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn gate_value_trace(
    input: &ZkAiD64GateValueProjectionProofInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D64_GATE_VALUE_LOG_SIZE).circle_domain();
    let rows =
        build_rows(&input.projection_input_q8).expect("validated gate/value projection rows");
    let columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.row_index)).collect(),
        rows.iter()
            .map(|row| field_usize(row.matrix_selector))
            .collect(),
        rows.iter()
            .map(|row| field_usize(row.output_index))
            .collect(),
        rows.iter()
            .map(|row| field_usize(row.input_index))
            .collect(),
        rows.iter()
            .map(|row| field_i64(row.projection_input_q8))
            .collect(),
        rows.iter().map(|row| field_i64(row.weight_q8)).collect(),
        rows.iter().map(|row| field_i64(row.product_q8)).collect(),
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

fn gate_value_output_commitment(gate: &[i64], value: &[i64]) -> String {
    let gate_values_sha256 = sha256_hex(canonical_i64_array(gate).as_bytes());
    let value_values_sha256 = sha256_hex(canonical_i64_array(value).as_bytes());
    let payload = format!(
        "{{\"encoding\":\"d64_gate_value_projection_output_v1\",\"gate_values_sha256\":\"{}\",\"shape\":{{\"gate\":[{}],\"value\":[{}]}},\"value_values_sha256\":\"{}\"}}",
        gate_values_sha256, ZKAI_D64_FF_DIM, ZKAI_D64_FF_DIM, value_values_sha256
    );
    blake2b_commitment_bytes(payload.as_bytes(), GATE_VALUE_PROJECTION_OUTPUT_DOMAIN)
}

fn rows_commitment(rows: &[D64GateValueProjectionMulRow]) -> String {
    let rows_json = canonical_row_material(rows);
    let rows_sha256 = sha256_hex(rows_json.as_bytes());
    let payload = format!(
        "{{\"encoding\":\"d64_gate_value_projection_mul_rows_v1\",\"rows_sha256\":\"{}\",\"shape\":[{},7]}}",
        rows_sha256,
        rows.len()
    );
    blake2b_commitment_bytes(payload.as_bytes(), GATE_VALUE_PROJECTION_MUL_ROW_DOMAIN)
}

fn expected_gate_matrix_root() -> &'static str {
    EXPECTED_GATE_MATRIX_ROOT
        .get_or_init(|| matrix_root("gate").expect("deterministic gate matrix root"))
        .as_str()
}

fn expected_value_matrix_root() -> &'static str {
    EXPECTED_VALUE_MATRIX_ROOT
        .get_or_init(|| matrix_root("value").expect("deterministic value matrix root"))
        .as_str()
}

fn matrix_root(matrix: &str) -> Result<String> {
    let mut leaf_hashes = Vec::with_capacity(ZKAI_D64_FF_DIM);
    for output_index in 0..ZKAI_D64_FF_DIM {
        let values = matrix_row_values(matrix, output_index)?;
        let values_sha256 = sha256_hex(canonical_i64_array(&values).as_bytes());
        let leaf_payload = format!(
            "{{\"kind\":\"matrix_row\",\"matrix\":\"{}\",\"row\":{},\"shape\":[{}],\"values_sha256\":\"{}\"}}",
            matrix, output_index, ZKAI_D64_WIDTH, values_sha256
        );
        leaf_hashes.push(blake2b_hex(leaf_payload.as_bytes(), MATRIX_ROW_LEAF_DOMAIN));
    }
    merkle_root(&leaf_hashes, MATRIX_ROW_TREE_DOMAIN)
}

fn matrix_row_values(matrix: &str, output_index: usize) -> Result<Vec<i64>> {
    let mut values = Vec::with_capacity(ZKAI_D64_WIDTH);
    for input_index in 0..ZKAI_D64_WIDTH {
        values.push(weight_value(matrix, output_index, input_index)?);
    }
    Ok(values)
}

fn merkle_root(leaf_hashes: &[String], domain: &str) -> Result<String> {
    if leaf_hashes.is_empty() {
        return Err(gate_value_error("cannot commit empty matrix tree"));
    }
    let mut level = leaf_hashes.to_vec();
    while level.len() > 1 {
        if level.len() % 2 == 1 {
            let last = level.last().expect("non-empty merkle level").to_string();
            level.push(last);
        }
        let mut next = Vec::with_capacity(level.len() / 2);
        for pair in level.chunks_exact(2) {
            let mut bytes = parse_blake2b_hex(&pair[0])?;
            bytes.extend(parse_blake2b_hex(&pair[1])?);
            next.push(blake2b_hex(&bytes, domain));
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

fn canonical_row_material(rows: &[D64GateValueProjectionMulRow]) -> String {
    let mut out = String::from("[");
    for (index, row) in rows.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        out.push('[');
        for (field_index, value) in [
            row.row_index as i64,
            row.matrix_selector as i64,
            row.output_index as i64,
            row.input_index as i64,
            row.projection_input_q8,
            row.weight_q8,
            row.product_q8,
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

fn parse_blake2b_hex(value: &str) -> Result<Vec<u8>> {
    let raw = value.strip_prefix("blake2b-256:").unwrap_or(value);
    if raw.len() != 64 {
        return Err(gate_value_error("invalid blake2b hex length"));
    }
    let mut out = Vec::with_capacity(32);
    for index in (0..raw.len()).step_by(2) {
        let byte = u8::from_str_radix(&raw[index..index + 2], 16)
            .map_err(|_| gate_value_error("invalid blake2b hex"))?;
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
        return Err(gate_value_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(gate_value_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(gate_value_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(gate_value_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
}

fn checked_mul_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_mul(rhs)
        .ok_or_else(|| gate_value_error(format!("{label} overflow")))
}

fn checked_add_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_add(rhs)
        .ok_or_else(|| gate_value_error(format!("{label} overflow")))
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
        return Err(gate_value_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn gate_value_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 gate/value projection proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json"
    );

    fn input() -> ZkAiD64GateValueProjectionProofInput {
        zkai_d64_gate_value_projection_input_from_json_str(INPUT_JSON).expect("gate/value input")
    }

    #[test]
    fn gate_value_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(input.projection_input_q8.len(), ZKAI_D64_WIDTH);
        let rows = build_rows(&input.projection_input_q8).expect("derived rows");
        assert_eq!(rows.len(), ZKAI_D64_GATE_VALUE_ROW_COUNT);
        assert_eq!(rows[0].matrix, "gate");
        assert_eq!(rows[0].projection_input_q8, 46);
        assert_eq!(rows[0].weight_q8, -2);
        assert_eq!(rows[0].product_q8, -92);
        assert_eq!(
            input.source_projection_input_row_commitment,
            ZKAI_D64_PROJECTION_INPUT_ROW_COMMITMENT
        );
        assert_eq!(
            input.gate_value_projection_output_commitment,
            ZKAI_D64_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT
        );
        assert_ne!(
            input.gate_value_projection_output_commitment,
            ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT
        );
    }

    #[test]
    fn gate_value_matrix_roots_match_deterministic_generator() {
        assert_eq!(
            matrix_root("gate").expect("gate root"),
            ZKAI_D64_GATE_MATRIX_ROOT
        );
        assert_eq!(
            matrix_root("value").expect("value root"),
            ZKAI_D64_VALUE_MATRIX_ROOT
        );
    }

    #[test]
    fn gate_value_pcs_config_uses_shared_publication_v1_profile() {
        let actual = gate_value_pcs_config();
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
    fn gate_value_air_proof_round_trips() {
        let input = input();
        let envelope =
            prove_zkai_d64_gate_value_projection_envelope(&input).expect("gate/value proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d64_gate_value_projection_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn gate_value_rejects_output_relabeling_as_full_output() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["gate_value_projection_output_commitment"] =
            Value::String(ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d64_gate_value_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("must not relabel"));
    }

    #[test]
    fn gate_value_rejects_projection_input_vector_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["projection_input_q8"][0] = Value::from(47);
        let error = zkai_d64_gate_value_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("projection input recomputed commitment"));
    }

    #[test]
    fn gate_value_rejects_row_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["gate_value_projection_mul_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "55".repeat(32)));
        let error = zkai_d64_gate_value_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("gate/value projection row commitment"));
    }

    #[test]
    fn gate_value_rejects_source_projection_input_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["source_projection_input_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "77".repeat(32)));
        let error = zkai_d64_gate_value_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("source projection input row commitment"));
    }

    #[test]
    fn gate_value_rejects_gate_output_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["gate_projection_output_commitment"] =
            Value::String(format!("blake2b-256:{}", "88".repeat(32)));
        let error = zkai_d64_gate_value_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("gate projection output commitment"));
    }

    #[test]
    fn gate_value_rejects_oversized_input_json() {
        let oversized = " ".repeat(ZKAI_D64_GATE_VALUE_PROJECTION_MAX_JSON_BYTES + 1);
        let error = zkai_d64_gate_value_projection_input_from_json_str(&oversized).unwrap_err();
        assert!(error.to_string().contains("input JSON exceeds max size"));
    }

    #[test]
    fn gate_value_rejects_oversized_proof_bytes() {
        let input = input();
        let envelope = ZkAiD64GateValueProjectionEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION.to_string(),
            statement_version: ZKAI_D64_GATE_VALUE_PROJECTION_STATEMENT_VERSION.to_string(),
            semantic_scope: ZKAI_D64_GATE_VALUE_PROJECTION_SEMANTIC_SCOPE.to_string(),
            decision: ZKAI_D64_GATE_VALUE_PROJECTION_DECISION.to_string(),
            source_bridge_proof_version: ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION
                .to_string(),
            input,
            proof: vec![0u8; ZKAI_D64_GATE_VALUE_PROJECTION_MAX_PROOF_BYTES + 1],
        };
        let error = verify_zkai_d64_gate_value_projection_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof bytes exceed bounded verifier limit"));
    }

    #[test]
    fn gate_value_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_gate_value_projection_envelope(&input).expect("gate/value proof");
        envelope.input.projection_input_q8[0] += 1;
        let error = verify_zkai_d64_gate_value_projection_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("d64 gate/value projection proof rejected"));
    }

    #[test]
    fn gate_value_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_gate_value_projection_envelope(&input).expect("gate/value proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d64_gate_value_projection_envelope(&envelope).is_err());
    }

    #[test]
    fn gate_value_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_gate_value_projection_envelope(&input).expect("gate/value proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_gate_value_projection_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn gate_value_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_gate_value_projection_envelope(&input).expect("gate/value proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_gate_value_projection_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }
}
