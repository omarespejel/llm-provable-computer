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

use super::d128_native_activation_swiglu_proof::{
    ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
    ZKAI_D128_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT, ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT,
};

pub const ZKAI_D128_DOWN_PROJECTION_INPUT_SCHEMA: &str =
    "zkai-d128-down-projection-air-proof-input-v1";
pub const ZKAI_D128_DOWN_PROJECTION_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF";
pub const ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION: &str = "stwo-d128-down-projection-air-proof-v1";
pub const ZKAI_D128_DOWN_PROJECTION_STATEMENT_VERSION: &str =
    "zkai-d128-down-projection-statement-v1";
pub const ZKAI_D128_DOWN_PROJECTION_SEMANTIC_SCOPE: &str =
    "d128_down_projection_rows_bound_to_hidden_activation_receipt";
pub const ZKAI_D128_DOWN_PROJECTION_DECISION: &str = "GO_D128_DOWN_PROJECTION_AIR_PROOF";
pub const ZKAI_D128_DOWN_PROJECTION_NEXT_BACKEND_STEP: &str =
    "bind d128 residual-add rows to residual_delta_commitment and output_activation_commitment";
pub const ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D128_DOWN_PROJECTION_MAX_PROOF_BYTES: usize = 67_108_864;
pub const ZKAI_D128_DOWN_MATRIX_ROOT: &str =
    "blake2b-256:0d6cd2bee99c821788d1faf5dd24e5e3e8ff4d4d4acd4d99c46a10ecc166c7ab";
pub const ZKAI_D128_RESIDUAL_DELTA_COMMITMENT: &str =
    "blake2b-256:537e11aeea97aa83cb510806cec96cd97ccd5673b8cc0dfdc3399fd90fc13ffe";
pub const ZKAI_D128_DOWN_PROJECTION_MUL_ROW_COMMITMENT: &str =
    "blake2b-256:76c1e5a35ffbc0c9b390f73d3491d973e85180421ac6168c0cb0e18a91a2ca68";

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const ZKAI_D128_TARGET_ID: &str = "rmsnorm-swiglu-residual-d128-v1";
const ZKAI_D128_REQUIRED_BACKEND_VERSION: &str = "stwo-rmsnorm-swiglu-residual-d128-v1";
const ZKAI_D128_VERIFIER_DOMAIN: &str = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1";
const ZKAI_D128_WIDTH: usize = 128;
const ZKAI_D128_FF_DIM: usize = 512;
const ZKAI_D128_DOWN_PROJECTION_MUL_ROWS: usize = ZKAI_D128_WIDTH * ZKAI_D128_FF_DIM;
const ZKAI_D128_RESIDUAL_ROWS: usize = ZKAI_D128_WIDTH;
const ZKAI_D128_TARGET_COMMITMENT: &str =
    "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18";
const ZKAI_D128_OUTPUT_ACTIVATION_COMMITMENT: &str =
    "blake2b-256:7e6ae6d301fc60ac2232d807d155785eabe653cf4e91971adda470a04246a572";
const PROOF_NATIVE_PARAMETER_KIND: &str = "d128-down-projection-synthetic-parameters-v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str = "ptvm:zkai:d128-proof-native-parameter-commitment:v1";
const PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:d128-public-instance:v1";
pub const ZKAI_D128_DOWN_PROJECTION_PROOF_NATIVE_PARAMETER_COMMITMENT: &str =
    "blake2b-256:ee69217168238b20e0b46a722554b42abe4fd5c599231f130d25ca7e4b432aef";
pub const ZKAI_D128_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT: &str =
    "blake2b-256:26b01b31147ec5cf0b45d9736f56cf77309f98a6bba5f6d440ae1be0f03de63e";
pub const ZKAI_D128_DOWN_PROJECTION_STATEMENT_COMMITMENT: &str =
    "blake2b-256:bf283328fcef05dfcae9fb0c3e90cbe53ebe1705ef78a73d63acd6b1b2891564";
const WEIGHT_GENERATOR_SEED: &str = "zkai-d128-down-projection-synthetic-parameters-2026-05-v1";
const D128_DOWN_PROJECTION_LOG_SIZE: u32 = 16;
const ZKAI_D128_DOWN_PROJECTION_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D128_DOWN_PROJECTION_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const HIDDEN_ACTIVATION_DOMAIN: &str = "ptvm:zkai:d128-hidden-activation:v1";
const RESIDUAL_DELTA_DOMAIN: &str = "ptvm:zkai:d128-residual-delta:v1";
const DOWN_PROJECTION_MUL_ROW_DOMAIN: &str = "ptvm:zkai:d128-down-projection-mul-rows:v1";
const MATRIX_ROW_LEAF_DOMAIN: &str = "ptvm:zkai:d128:param-matrix-row-leaf:v1";
const MATRIX_ROW_TREE_DOMAIN: &str = "ptvm:zkai:d128:param-matrix-row-tree:v1";
static EXPECTED_DOWN_MATRIX_ROOT: OnceLock<String> = OnceLock::new();

const COLUMN_IDS: [&str; 6] = [
    "zkai/d128/down-projection/row-index",
    "zkai/d128/down-projection/output-index",
    "zkai/d128/down-projection/hidden-index",
    "zkai/d128/down-projection/hidden-q8",
    "zkai/d128/down-projection/weight-q8",
    "zkai/d128/down-projection/product-q8",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not full d128 block proof",
    "not residual proof",
    "not recursive composition",
    "not binding the full d128 output_activation_commitment",
    "not a private down-weight opening proof",
    "down projection aggregation is verifier-recomputed from checked public multiplication rows, not a private AIR aggregation claim",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "source d128 activation/SwiGLU evidence validation before down-projection construction",
    "source activation statement and public-instance commitments checked before proof verification",
    "hidden activation commitment recomputation before proof verification",
    "down-projection multiplication row commitment recomputation before proof verification",
    "residual-delta commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR multiplication relation for every checked down-projection row",
    "down matrix root recomputed from checked row weights",
    "signed-M31 bounds for hidden activations and residual deltas; fixed-point q8 semantic bounds for down weights",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "python3 scripts/zkai_d128_down_projection_proof_input.py --write-json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input",
    "cargo +nightly-2025-07-14 test d128_native_down_projection_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone)]
struct D128DownProjectionEval {
    log_size: u32,
}

impl FrameworkEval for D128DownProjectionEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let row_index = eval.next_trace_mask();
        let output_index = eval.next_trace_mask();
        let hidden_index = eval.next_trace_mask();
        let hidden_q8 = eval.next_trace_mask();
        let weight_q8 = eval.next_trace_mask();
        let product_q8 = eval.next_trace_mask();

        for (column_id, trace_value) in COLUMN_IDS.iter().zip([
            row_index,
            output_index,
            hidden_index,
            hidden_q8.clone(),
            weight_q8.clone(),
            product_q8.clone(),
        ]) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        eval.add_constraint(hidden_q8 * weight_q8 - product_q8);
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D128DownProjectionMulRow {
    pub row_index: usize,
    pub output_index: usize,
    pub hidden_index: usize,
    pub hidden_q8: i64,
    pub weight_q8: i64,
    pub product_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128DownProjectionProofInput {
    pub schema: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub ff_dim: usize,
    pub row_count: usize,
    pub down_projection_mul_rows: usize,
    pub residual_delta_rows: usize,
    pub source_activation_swiglu_proof_version: String,
    pub source_activation_swiglu_statement_commitment: String,
    pub source_activation_swiglu_public_instance_commitment: String,
    pub source_hidden_activation_commitment: String,
    pub down_matrix_root: String,
    pub proof_native_parameter_commitment: String,
    pub residual_delta_commitment: String,
    pub down_projection_mul_row_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub hidden_q8: Vec<i64>,
    pub residual_delta_q8: Vec<i64>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD128DownProjectionEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub source_activation_swiglu_proof_version: String,
    pub input: ZkAiD128DownProjectionProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct D128DownProjectionProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d128_down_projection_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128DownProjectionProofInput> {
    if raw_json.len() > ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES {
        return Err(down_projection_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD128DownProjectionProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_down_projection_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d128_down_projection_envelope(
    input: &ZkAiD128DownProjectionProofInput,
) -> Result<ZkAiD128DownProjectionEnvelope> {
    validate_down_projection_input(input)?;
    Ok(ZkAiD128DownProjectionEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D128_DOWN_PROJECTION_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D128_DOWN_PROJECTION_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D128_DOWN_PROJECTION_DECISION.to_string(),
        source_activation_swiglu_proof_version: ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION
            .to_string(),
        input: input.clone(),
        proof: prove_down_projection_rows(input)?,
    })
}

pub fn verify_zkai_d128_down_projection_envelope(
    envelope: &ZkAiD128DownProjectionEnvelope,
) -> Result<bool> {
    validate_down_projection_envelope(envelope)?;
    verify_down_projection_rows(&envelope.input, &envelope.proof)
}

fn validate_down_projection_envelope(envelope: &ZkAiD128DownProjectionEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(down_projection_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_DOWN_PROJECTION_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_DOWN_PROJECTION_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_DOWN_PROJECTION_DECISION,
        "decision",
    )?;
    expect_eq(
        &envelope.source_activation_swiglu_proof_version,
        ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source activation/SwiGLU proof version",
    )?;
    if envelope.proof.is_empty() {
        return Err(down_projection_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D128_DOWN_PROJECTION_MAX_PROOF_BYTES {
        return Err(down_projection_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_DOWN_PROJECTION_MAX_PROOF_BYTES
        )));
    }
    validate_down_projection_input(&envelope.input)
}

fn validate_down_projection_input(input: &ZkAiD128DownProjectionProofInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D128_DOWN_PROJECTION_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D128_DOWN_PROJECTION_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(&input.target_id, ZKAI_D128_TARGET_ID, "target id")?;
    expect_eq(
        &input.required_backend_version,
        ZKAI_D128_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_D128_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_usize(input.width, ZKAI_D128_WIDTH, "width")?;
    expect_usize(input.ff_dim, ZKAI_D128_FF_DIM, "ff dim")?;
    expect_usize(
        input.row_count,
        ZKAI_D128_DOWN_PROJECTION_MUL_ROWS,
        "row count",
    )?;
    expect_usize(
        input.down_projection_mul_rows,
        ZKAI_D128_DOWN_PROJECTION_MUL_ROWS,
        "down projection mul rows",
    )?;
    expect_usize(
        input.residual_delta_rows,
        ZKAI_D128_RESIDUAL_ROWS,
        "residual delta rows",
    )?;
    expect_eq(
        &input.source_activation_swiglu_proof_version,
        ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
        "source activation/SwiGLU proof version",
    )?;
    expect_eq(
        &input.source_activation_swiglu_statement_commitment,
        ZKAI_D128_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
        "source activation/SwiGLU statement commitment",
    )?;
    expect_eq(
        &input.source_activation_swiglu_public_instance_commitment,
        ZKAI_D128_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
        "source activation/SwiGLU public instance commitment",
    )?;
    expect_eq(
        &input.source_hidden_activation_commitment,
        ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT,
        "source hidden activation commitment",
    )?;
    let expected_down_matrix_root = expected_down_matrix_root();
    expect_eq(
        expected_down_matrix_root,
        ZKAI_D128_DOWN_MATRIX_ROOT,
        "down matrix root generator constant",
    )?;
    expect_eq(
        &input.down_matrix_root,
        expected_down_matrix_root,
        "down matrix root",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        ZKAI_D128_DOWN_PROJECTION_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "proof-native parameter commitment",
    )?;
    if input.residual_delta_commitment == ZKAI_D128_OUTPUT_ACTIVATION_COMMITMENT {
        return Err(down_projection_error(
            "residual delta commitment must not relabel as full output activation commitment",
        ));
    }
    expect_eq(
        &input.residual_delta_commitment,
        ZKAI_D128_RESIDUAL_DELTA_COMMITMENT,
        "residual delta commitment",
    )?;
    expect_eq(
        &input.down_projection_mul_row_commitment,
        ZKAI_D128_DOWN_PROJECTION_MUL_ROW_COMMITMENT,
        "down projection row commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        ZKAI_D128_DOWN_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
        "public instance commitment",
    )?;
    expect_eq(
        &input.statement_commitment,
        ZKAI_D128_DOWN_PROJECTION_STATEMENT_COMMITMENT,
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
        ZKAI_D128_DOWN_PROJECTION_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    expect_str_set_eq(
        input.validation_commands.iter().map(String::as_str),
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
    )?;
    if input.hidden_q8.len() != ZKAI_D128_FF_DIM {
        return Err(down_projection_error(
            "hidden activation output vector length mismatch",
        ));
    }
    if input.residual_delta_q8.len() != ZKAI_D128_WIDTH {
        return Err(down_projection_error(
            "residual delta vector length mismatch",
        ));
    }
    for (label, values) in [
        ("hidden activation", &input.hidden_q8),
        ("residual delta", &input.residual_delta_q8),
    ] {
        for (index, value) in values.iter().enumerate() {
            expect_signed_m31(*value, &format!("{label} {index}"))?;
        }
    }
    expect_eq(
        &sequence_commitment(&input.hidden_q8, HIDDEN_ACTIVATION_DOMAIN, ZKAI_D128_FF_DIM),
        &input.source_hidden_activation_commitment,
        "source hidden activation recomputed commitment",
    )?;

    let rows = build_rows(&input.hidden_q8)?;
    let mut accumulators = vec![0i64; ZKAI_D128_WIDTH];
    for (expected_row_index, row) in rows.iter().enumerate() {
        validate_down_projection_row(row, expected_row_index)?;
        let product = checked_mul_i64(row.hidden_q8, row.weight_q8, "down projection product")?;
        expect_i64(row.product_q8, product, "down projection product relation")?;
        expect_i64(
            row.hidden_q8,
            input.hidden_q8[row.hidden_index],
            "hidden activation value",
        )?;
        accumulators[row.output_index] = checked_add_i64(
            accumulators[row.output_index],
            row.product_q8,
            "down projection accumulator",
        )?;
    }
    let recomputed_delta = divide_accumulators(&accumulators)?;
    if recomputed_delta != input.residual_delta_q8 {
        return Err(down_projection_error("residual delta output drift"));
    }
    expect_eq(
        &sequence_commitment(
            &input.residual_delta_q8,
            RESIDUAL_DELTA_DOMAIN,
            ZKAI_D128_WIDTH,
        ),
        &input.residual_delta_commitment,
        "residual delta recomputed commitment",
    )?;
    expect_eq(
        &rows_commitment(&rows),
        &input.down_projection_mul_row_commitment,
        "down projection row recomputed commitment",
    )?;
    expect_eq(
        &proof_native_parameter_commitment(&input.down_matrix_root),
        &input.proof_native_parameter_commitment,
        "proof-native parameter recomputed commitment",
    )?;
    expect_eq(
        &statement_commitment(input),
        &input.statement_commitment,
        "statement recomputed commitment",
    )?;
    expect_eq(
        &public_instance_commitment(&input.statement_commitment),
        &input.public_instance_commitment,
        "public instance recomputed commitment",
    )?;
    Ok(())
}

fn validate_down_projection_row(
    row: &D128DownProjectionMulRow,
    expected_index: usize,
) -> Result<()> {
    expect_usize(row.row_index, expected_index, "row index")?;
    if row.output_index >= ZKAI_D128_WIDTH {
        return Err(down_projection_error("output index drift"));
    }
    if row.hidden_index >= ZKAI_D128_FF_DIM {
        return Err(down_projection_error("hidden index drift"));
    }
    expect_signed_m31(row.hidden_q8, "hidden activation")?;
    expect_signed_q8(row.weight_q8, "down projection weight q8")?;
    expect_signed_m31(row.weight_q8, "down projection weight q8")?;
    expect_signed_m31(row.product_q8, "down projection product q8")?;
    expect_usize(
        row.output_index,
        row.row_index / ZKAI_D128_FF_DIM,
        "row-order output index",
    )?;
    expect_usize(
        row.hidden_index,
        row.row_index % ZKAI_D128_FF_DIM,
        "row-order hidden index",
    )?;
    expect_i64(
        row.weight_q8,
        weight_value("down", row.output_index, row.hidden_index)?,
        "down projection weight relation",
    )?;
    Ok(())
}

fn divide_accumulators(accumulators: &[i64]) -> Result<Vec<i64>> {
    let mut out = Vec::with_capacity(accumulators.len());
    for value in accumulators {
        out.push(value.div_euclid(ZKAI_D128_FF_DIM as i64));
    }
    Ok(out)
}

fn build_rows(hidden: &[i64]) -> Result<Vec<D128DownProjectionMulRow>> {
    if hidden.len() != ZKAI_D128_FF_DIM {
        return Err(down_projection_error(
            "hidden activation vector length mismatch",
        ));
    }
    let mut rows = Vec::with_capacity(ZKAI_D128_DOWN_PROJECTION_MUL_ROWS);
    let mut row_index = 0usize;
    for output_index in 0..ZKAI_D128_WIDTH {
        for (hidden_index, hidden_q8) in hidden.iter().enumerate() {
            let weight_q8 = weight_value("down", output_index, hidden_index)?;
            let product_q8 = checked_mul_i64(*hidden_q8, weight_q8, "down projection product")?;
            rows.push(D128DownProjectionMulRow {
                row_index,
                output_index,
                hidden_index,
                hidden_q8: *hidden_q8,
                weight_q8,
                product_q8,
            });
            row_index += 1;
        }
    }
    Ok(rows)
}

fn weight_value(matrix: &str, row: usize, col: usize) -> Result<i64> {
    if matrix != "down" {
        return Err(down_projection_error("unknown projection matrix"));
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
        return Err(down_projection_error("invalid deterministic integer range"));
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

fn prove_down_projection_rows(input: &ZkAiD128DownProjectionProofInput) -> Result<Vec<u8>> {
    let component = down_projection_component();
    let config = down_projection_pcs_config();
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
    tree_builder.extend_evals(down_projection_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(down_projection_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "d128 down projection AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128DownProjectionProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_down_projection_rows(
    input: &ZkAiD128DownProjectionProofInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D128DownProjectionProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_down_projection_pcs_config(stark_proof.config)?;
    let component = down_projection_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D128_DOWN_PROJECTION_EXPECTED_TRACE_COMMITMENTS {
        return Err(down_projection_error(format!(
            "internal down projection component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D128_DOWN_PROJECTION_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D128_DOWN_PROJECTION_EXPECTED_PROOF_COMMITMENTS {
        return Err(down_projection_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D128_DOWN_PROJECTION_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = down_projection_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(down_projection_error(
            "preprocessed row commitment does not match checked down projection rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(down_projection_error(
            "base row commitment does not match checked down projection rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| down_projection_error(format!("STARK verification failed: {error}")))
}

fn validate_down_projection_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(down_projection_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(down_projection_pcs_config())
}

fn down_projection_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn down_projection_commitment_roots(
    input: &ZkAiD128DownProjectionProofInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = down_projection_component();
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
    tree_builder.extend_evals(down_projection_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(down_projection_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn down_projection_component() -> FrameworkComponent<D128DownProjectionEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D128DownProjectionEval {
            log_size: D128_DOWN_PROJECTION_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn down_projection_trace(
    input: &ZkAiD128DownProjectionProofInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D128_DOWN_PROJECTION_LOG_SIZE).circle_domain();
    let rows = build_rows(&input.hidden_q8).expect("validated down projection rows");
    let columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.row_index)).collect(),
        rows.iter()
            .map(|row| field_usize(row.output_index))
            .collect(),
        rows.iter()
            .map(|row| field_usize(row.hidden_index))
            .collect(),
        rows.iter().map(|row| field_i64(row.hidden_q8)).collect(),
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

fn rows_commitment(rows: &[D128DownProjectionMulRow]) -> String {
    let rows_json = canonical_row_material(rows);
    let rows_sha256 = sha256_hex(rows_json.as_bytes());
    let payload = format!(
        "{{\"encoding\":\"d128_down_projection_mul_rows_v1\",\"rows_sha256\":\"{}\",\"shape\":[{},6]}}",
        rows_sha256,
        rows.len()
    );
    blake2b_commitment_bytes(payload.as_bytes(), DOWN_PROJECTION_MUL_ROW_DOMAIN)
}

fn proof_native_parameter_commitment(down_root: &str) -> String {
    let payload = format!(
        "{{\"down_matrix_root\":\"{}\",\"ff_dim\":{},\"kind\":\"{}\",\"target_commitment\":\"{}\",\"weight_generator_seed\":\"{}\",\"width\":{}}}",
        down_root,
        ZKAI_D128_FF_DIM,
        PROOF_NATIVE_PARAMETER_KIND,
        ZKAI_D128_TARGET_COMMITMENT,
        WEIGHT_GENERATOR_SEED,
        ZKAI_D128_WIDTH
    );
    blake2b_commitment_bytes(payload.as_bytes(), PROOF_NATIVE_PARAMETER_DOMAIN)
}

fn statement_commitment(input: &ZkAiD128DownProjectionProofInput) -> String {
    let payload = format!(
        "{{\"down_matrix_root\":\"{}\",\"down_projection_mul_row_commitment\":\"{}\",\"ff_dim\":{},\"operation\":\"down_projection\",\"proof_native_parameter_commitment\":\"{}\",\"required_backend_version\":\"{}\",\"residual_delta_commitment\":\"{}\",\"row_count\":{},\"source_activation_swiglu_proof_version\":\"{}\",\"source_activation_swiglu_statement_commitment\":\"{}\",\"source_hidden_activation_commitment\":\"{}\",\"target_commitment\":\"{}\",\"target_id\":\"{}\",\"verifier_domain\":\"{}\",\"width\":{}}}",
        input.down_matrix_root,
        input.down_projection_mul_row_commitment,
        input.ff_dim,
        input.proof_native_parameter_commitment,
        ZKAI_D128_REQUIRED_BACKEND_VERSION,
        input.residual_delta_commitment,
        input.row_count,
        ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
        input.source_activation_swiglu_statement_commitment,
        input.source_hidden_activation_commitment,
        ZKAI_D128_TARGET_COMMITMENT,
        ZKAI_D128_TARGET_ID,
        ZKAI_D128_VERIFIER_DOMAIN,
        input.width
    );
    blake2b_commitment_bytes(payload.as_bytes(), ZKAI_D128_VERIFIER_DOMAIN)
}

fn public_instance_commitment(statement: &str) -> String {
    let payload = format!(
        "{{\"ff_dim\":{},\"operation\":\"down_projection\",\"target_commitment\":\"{}\",\"width\":{}}}",
        ZKAI_D128_FF_DIM, statement, ZKAI_D128_WIDTH
    );
    blake2b_commitment_bytes(payload.as_bytes(), PUBLIC_INSTANCE_DOMAIN)
}

fn expected_down_matrix_root() -> &'static str {
    EXPECTED_DOWN_MATRIX_ROOT
        .get_or_init(|| matrix_root("down").expect("deterministic down matrix root"))
        .as_str()
}

fn matrix_root(matrix: &str) -> Result<String> {
    let mut leaf_hashes = Vec::with_capacity(ZKAI_D128_WIDTH);
    for output_index in 0..ZKAI_D128_WIDTH {
        let values = matrix_row_values(matrix, output_index)?;
        let values_sha256 = sha256_hex(canonical_i64_array(&values).as_bytes());
        let leaf_payload = format!(
            "{{\"kind\":\"matrix_row\",\"matrix\":\"{}\",\"row\":{},\"shape\":[{}],\"values_sha256\":\"{}\"}}",
            matrix, output_index, ZKAI_D128_FF_DIM, values_sha256
        );
        leaf_hashes.push(blake2b_hex(leaf_payload.as_bytes(), MATRIX_ROW_LEAF_DOMAIN));
    }
    merkle_root(&leaf_hashes, MATRIX_ROW_TREE_DOMAIN)
}

fn matrix_row_values(matrix: &str, output_index: usize) -> Result<Vec<i64>> {
    let mut values = Vec::with_capacity(ZKAI_D128_FF_DIM);
    for hidden_index in 0..ZKAI_D128_FF_DIM {
        values.push(weight_value(matrix, output_index, hidden_index)?);
    }
    Ok(values)
}

fn merkle_root(leaf_hashes: &[String], domain: &str) -> Result<String> {
    if leaf_hashes.is_empty() {
        return Err(down_projection_error("cannot commit empty matrix tree"));
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

fn canonical_row_material(rows: &[D128DownProjectionMulRow]) -> String {
    let mut out = String::from("[");
    for (index, row) in rows.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        out.push('[');
        for (field_index, value) in [
            row.row_index as i64,
            row.output_index as i64,
            row.hidden_index as i64,
            row.hidden_q8,
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
        return Err(down_projection_error("invalid blake2b hex length"));
    }
    let mut out = Vec::with_capacity(32);
    for index in (0..raw.len()).step_by(2) {
        let byte = u8::from_str_radix(&raw[index..index + 2], 16)
            .map_err(|_| down_projection_error("invalid blake2b hex"))?;
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
        return Err(down_projection_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(down_projection_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(down_projection_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(down_projection_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
}

fn expect_signed_q8(value: i64, label: &str) -> Result<()> {
    if !(-1024..=1024).contains(&value) {
        return Err(down_projection_error(format!(
            "{label} is outside fixed-point q8 semantic bound: {value}"
        )));
    }
    Ok(())
}

fn checked_mul_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_mul(rhs)
        .ok_or_else(|| down_projection_error(format!("{label} overflow")))
}

fn checked_add_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_add(rhs)
        .ok_or_else(|| down_projection_error(format!("{label} overflow")))
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
        return Err(down_projection_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn down_projection_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d128 down projection proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json"
    );

    fn input() -> ZkAiD128DownProjectionProofInput {
        zkai_d128_down_projection_input_from_json_str(INPUT_JSON).expect("down projection input")
    }

    #[test]
    fn down_projection_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(input.hidden_q8.len(), ZKAI_D128_FF_DIM);
        let rows = build_rows(&input.hidden_q8).expect("derived rows");
        assert_eq!(rows.len(), ZKAI_D128_DOWN_PROJECTION_MUL_ROWS);
        assert_eq!(rows[0].hidden_q8, 2658);
        assert_eq!(rows[0].weight_q8, 6);
        assert_eq!(rows[0].product_q8, 15948);
        assert_eq!(input.residual_delta_q8[0], -2594);
        assert_eq!(
            input.source_hidden_activation_commitment,
            ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT
        );
        assert_eq!(
            input.residual_delta_commitment,
            ZKAI_D128_RESIDUAL_DELTA_COMMITMENT
        );
        assert_ne!(
            input.residual_delta_commitment,
            ZKAI_D128_OUTPUT_ACTIVATION_COMMITMENT
        );
    }

    #[test]
    fn down_projection_matrix_root_matches_deterministic_generator() {
        assert_eq!(
            matrix_root("down").expect("down root"),
            ZKAI_D128_DOWN_MATRIX_ROOT
        );
    }

    #[test]
    fn down_projection_pcs_config_uses_shared_publication_v1_profile() {
        let actual = down_projection_pcs_config();
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
    fn down_projection_air_proof_round_trips() {
        let input = input();
        let envelope = prove_zkai_d128_down_projection_envelope(&input).expect("down proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d128_down_projection_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn down_projection_rejects_residual_delta_relabeling_as_full_output() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_commitment"] =
            Value::String(ZKAI_D128_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("must not relabel"));
    }

    #[test]
    fn down_projection_rejects_hidden_vector_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["hidden_q8"][0] = Value::from(-67);
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("source hidden activation recomputed commitment"));
    }

    #[test]
    fn down_projection_rejects_source_hidden_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["source_hidden_activation_commitment"] =
            Value::String(format!("blake2b-256:{}", "77".repeat(32)));
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("source hidden activation commitment"));
    }

    #[test]
    fn down_projection_rejects_residual_delta_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_q8"][0] = Value::from(17);
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("residual delta output drift"));
    }

    #[test]
    fn down_projection_rejects_hidden_m31_bounds_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["hidden_q8"][0] = Value::from(M31_MODULUS);
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("signed M31"));
    }

    #[test]
    fn down_projection_rejects_residual_delta_m31_bounds_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["residual_delta_q8"][0] = Value::from(M31_MODULUS);
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("signed M31"));
    }

    #[test]
    fn down_projection_rejects_down_matrix_root_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["down_matrix_root"] = Value::String(format!("blake2b-256:{}", "88".repeat(32)));
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("down matrix root"));
    }

    #[test]
    fn down_projection_rejects_row_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["down_projection_mul_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "55".repeat(32)));
        let error = zkai_d128_down_projection_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("down projection row commitment"));
    }

    #[test]
    fn down_projection_rejects_oversized_input_json() {
        let oversized = " ".repeat(ZKAI_D128_DOWN_PROJECTION_MAX_JSON_BYTES + 1);
        let error = zkai_d128_down_projection_input_from_json_str(&oversized).unwrap_err();
        assert!(error.to_string().contains("input JSON exceeds max size"));
    }

    #[test]
    fn down_projection_rejects_oversized_proof_bytes() {
        let input = input();
        let envelope = ZkAiD128DownProjectionEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D128_DOWN_PROJECTION_PROOF_VERSION.to_string(),
            statement_version: ZKAI_D128_DOWN_PROJECTION_STATEMENT_VERSION.to_string(),
            semantic_scope: ZKAI_D128_DOWN_PROJECTION_SEMANTIC_SCOPE.to_string(),
            decision: ZKAI_D128_DOWN_PROJECTION_DECISION.to_string(),
            source_activation_swiglu_proof_version: ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION
                .to_string(),
            input,
            proof: vec![0u8; ZKAI_D128_DOWN_PROJECTION_MAX_PROOF_BYTES + 1],
        };
        let error = verify_zkai_d128_down_projection_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof bytes exceed bounded verifier limit"));
    }

    #[test]
    fn down_projection_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope = prove_zkai_d128_down_projection_envelope(&input).expect("down proof");
        envelope.input.hidden_q8[0] += 1;
        let error = verify_zkai_d128_down_projection_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("d128 down projection proof rejected"));
    }

    #[test]
    fn down_projection_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope = prove_zkai_d128_down_projection_envelope(&input).expect("down proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d128_down_projection_envelope(&envelope).is_err());
    }

    #[test]
    fn down_projection_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope = prove_zkai_d128_down_projection_envelope(&input).expect("down proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d128_down_projection_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn down_projection_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope = prove_zkai_d128_down_projection_envelope(&input).expect("down proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d128_down_projection_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }
}
