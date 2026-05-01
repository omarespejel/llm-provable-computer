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
    ZKAI_D64_ACTIVATION_LOOKUP_COMMITMENT, ZKAI_D64_ACTIVATION_LOOKUP_ROWS,
    ZKAI_D64_ACTIVATION_TABLE_ROWS, ZKAI_D64_FF_DIM, ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT,
    ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT, ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D64_REQUIRED_BACKEND_VERSION, ZKAI_D64_STATEMENT_COMMITMENT, ZKAI_D64_SWIGLU_MIX_ROWS,
    ZKAI_D64_TARGET_ID, ZKAI_D64_VERIFIER_DOMAIN, ZKAI_D64_WIDTH,
};
use super::d64_native_gate_value_projection_proof::{
    ZKAI_D64_GATE_PROJECTION_OUTPUT_COMMITMENT, ZKAI_D64_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
    ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION, ZKAI_D64_VALUE_PROJECTION_OUTPUT_COMMITMENT,
};

pub const ZKAI_D64_ACTIVATION_SWIGLU_INPUT_SCHEMA: &str =
    "zkai-d64-activation-swiglu-air-proof-input-v1";
pub const ZKAI_D64_ACTIVATION_SWIGLU_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D64_ACTIVATION_SWIGLU_AIR_PROOF";
pub const ZKAI_D64_ACTIVATION_SWIGLU_PROOF_VERSION: &str =
    "stwo-d64-activation-swiglu-air-proof-v1";
pub const ZKAI_D64_ACTIVATION_SWIGLU_STATEMENT_VERSION: &str =
    "zkai-d64-activation-swiglu-statement-v1";
pub const ZKAI_D64_ACTIVATION_SWIGLU_SEMANTIC_SCOPE: &str =
    "d64_activation_swiglu_rows_bound_to_gate_value_projection_receipt";
pub const ZKAI_D64_ACTIVATION_SWIGLU_DECISION: &str = "GO_D64_ACTIVATION_SWIGLU_AIR_PROOF";
pub const ZKAI_D64_ACTIVATION_SWIGLU_NEXT_BACKEND_STEP: &str =
    "encode down-projection rows that consume hidden_activation_commitment and produce residual_delta_commitment";
pub const ZKAI_D64_ACTIVATION_SWIGLU_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D64_ACTIVATION_SWIGLU_MAX_PROOF_BYTES: usize = 4_194_304;
pub const ZKAI_D64_SCALE_Q8: i64 = 256;
pub const ZKAI_D64_ACTIVATION_CLAMP_Q8: i64 = 1024;
pub const ZKAI_D64_ACTIVATION_OUTPUT_COMMITMENT: &str =
    "blake2b-256:0affe836f18831511792d49333e153038a5a15c4de501f11535060c458395464";
pub const ZKAI_D64_HIDDEN_ACTIVATION_COMMITMENT: &str =
    "blake2b-256:18482fa6e000d8fb0e0d7b39db46355eeec556622ca69478d1a039438495b047";
pub const ZKAI_D64_ACTIVATION_SWIGLU_ROW_COMMITMENT: &str =
    "blake2b-256:2a2bde136784be11b6bfcadfa09b1c952580c97d967b1a8ebeac2f9d69d9bd2e";

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const D64_ACTIVATION_SWIGLU_LOG_SIZE: u32 = 8;
const ZKAI_D64_ACTIVATION_SWIGLU_ROW_COUNT: usize = ZKAI_D64_FF_DIM;
const ZKAI_D64_ACTIVATION_SWIGLU_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D64_ACTIVATION_SWIGLU_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const ACTIVATION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-activation-output:v1";
const HIDDEN_ACTIVATION_DOMAIN: &str = "ptvm:zkai:d64-hidden-activation:v1";
const ACTIVATION_SWIGLU_ROW_DOMAIN: &str = "ptvm:zkai:d64-activation-swiglu-rows:v1";
const GATE_PROJECTION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-gate-projection-output:v1";
const VALUE_PROJECTION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-value-projection-output:v1";
const GATE_VALUE_PROJECTION_OUTPUT_DOMAIN: &str = "ptvm:zkai:d64-gate-value-projection-output:v1";
const ACTIVATION_LOOKUP_DOMAIN: &str = "ptvm:zkai:d64-bounded-silu-lut:v1";

const COLUMN_IDS: [&str; 9] = [
    "zkai/d64/activation-swiglu/row-index",
    "zkai/d64/activation-swiglu/gate-q8",
    "zkai/d64/activation-swiglu/clamped-gate-q8",
    "zkai/d64/activation-swiglu/activation-table-index",
    "zkai/d64/activation-swiglu/activation-q8",
    "zkai/d64/activation-swiglu/value-q8",
    "zkai/d64/activation-swiglu/product-q16",
    "zkai/d64/activation-swiglu/hidden-q8",
    "zkai/d64/activation-swiglu/remainder-q16",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not full d64 block proof",
    "not down projection proof",
    "not residual proof",
    "not binding the full d64 output_activation_commitment",
    "not a private activation-lookup opening proof",
    "activation lookup and SwiGLU rows are verifier-recomputed from checked public rows before proof verification",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "gate/value projection output commitment recomputation before proof verification",
    "activation table commitment checked before proof verification",
    "activation lookup rows recomputed before proof verification",
    "SwiGLU product, floor quotient, and remainder recomputed before proof verification",
    "hidden activation commitment recomputation before proof verification",
    "AIR relation for every checked activation/SwiGLU row",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

#[derive(Debug, Clone)]
struct D64ActivationSwiGluEval {
    log_size: u32,
}

impl FrameworkEval for D64ActivationSwiGluEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let row_index = eval.next_trace_mask();
        let gate_q8 = eval.next_trace_mask();
        let clamped_gate_q8 = eval.next_trace_mask();
        let activation_table_index = eval.next_trace_mask();
        let activation_q8 = eval.next_trace_mask();
        let value_q8 = eval.next_trace_mask();
        let product_q16 = eval.next_trace_mask();
        let hidden_q8 = eval.next_trace_mask();
        let remainder_q16 = eval.next_trace_mask();

        for (column_id, trace_value) in COLUMN_IDS.iter().zip([
            row_index,
            gate_q8,
            clamped_gate_q8,
            activation_table_index,
            activation_q8.clone(),
            value_q8.clone(),
            product_q16.clone(),
            hidden_q8.clone(),
            remainder_q16.clone(),
        ]) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        eval.add_constraint(activation_q8 * value_q8 - product_q16.clone());
        let q8_scale = E::F::from(BaseField::from(ZKAI_D64_SCALE_Q8 as u32));
        eval.add_constraint(product_q16 - hidden_q8 * q8_scale - remainder_q16);
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D64ActivationSwiGluRow {
    pub row_index: usize,
    pub gate_q8: i64,
    pub clamped_gate_q8: i64,
    pub activation_table_index: i64,
    pub activation_q8: i64,
    pub value_q8: i64,
    pub product_q16: i64,
    pub hidden_q8: i64,
    pub remainder_q16: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD64ActivationSwiGluProofInput {
    pub schema: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub ff_dim: usize,
    pub row_count: usize,
    pub activation_lookup_rows: usize,
    pub swiglu_mix_rows: usize,
    pub scale_q8: i64,
    pub activation_clamp_q8: i64,
    pub source_gate_value_projection_proof_version: String,
    pub source_gate_projection_output_commitment: String,
    pub source_value_projection_output_commitment: String,
    pub source_gate_value_projection_output_commitment: String,
    pub activation_lookup_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub activation_output_commitment: String,
    pub hidden_activation_commitment: String,
    pub activation_swiglu_row_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub gate_projection_q8: Vec<i64>,
    pub value_projection_q8: Vec<i64>,
    pub activated_gate_q8: Vec<i64>,
    pub hidden_q8: Vec<i64>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64ActivationSwiGluEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub source_gate_value_projection_proof_version: String,
    pub input: ZkAiD64ActivationSwiGluProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct D64ActivationSwiGluProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d64_activation_swiglu_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD64ActivationSwiGluProofInput> {
    if raw_json.len() > ZKAI_D64_ACTIVATION_SWIGLU_MAX_JSON_BYTES {
        return Err(activation_swiglu_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D64_ACTIVATION_SWIGLU_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD64ActivationSwiGluProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_activation_swiglu_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d64_activation_swiglu_envelope(
    input: &ZkAiD64ActivationSwiGluProofInput,
) -> Result<ZkAiD64ActivationSwiGluEnvelope> {
    validate_activation_swiglu_input(input)?;
    Ok(ZkAiD64ActivationSwiGluEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D64_ACTIVATION_SWIGLU_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D64_ACTIVATION_SWIGLU_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D64_ACTIVATION_SWIGLU_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D64_ACTIVATION_SWIGLU_DECISION.to_string(),
        source_gate_value_projection_proof_version: ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION
            .to_string(),
        input: input.clone(),
        proof: prove_activation_swiglu_rows(input)?,
    })
}

pub fn verify_zkai_d64_activation_swiglu_envelope(
    envelope: &ZkAiD64ActivationSwiGluEnvelope,
) -> Result<bool> {
    validate_activation_swiglu_envelope(envelope)?;
    verify_activation_swiglu_rows(&envelope.input, &envelope.proof)
}

fn validate_activation_swiglu_envelope(envelope: &ZkAiD64ActivationSwiGluEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(activation_swiglu_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D64_ACTIVATION_SWIGLU_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D64_ACTIVATION_SWIGLU_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D64_ACTIVATION_SWIGLU_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D64_ACTIVATION_SWIGLU_DECISION,
        "decision",
    )?;
    expect_eq(
        &envelope.source_gate_value_projection_proof_version,
        ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION,
        "source gate/value proof version",
    )?;
    if envelope.proof.is_empty() {
        return Err(activation_swiglu_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D64_ACTIVATION_SWIGLU_MAX_PROOF_BYTES {
        return Err(activation_swiglu_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D64_ACTIVATION_SWIGLU_MAX_PROOF_BYTES
        )));
    }
    validate_activation_swiglu_input(&envelope.input)
}

fn validate_activation_swiglu_input(input: &ZkAiD64ActivationSwiGluProofInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D64_ACTIVATION_SWIGLU_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D64_ACTIVATION_SWIGLU_INPUT_DECISION,
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
    expect_usize(
        input.row_count,
        ZKAI_D64_ACTIVATION_SWIGLU_ROW_COUNT,
        "row count",
    )?;
    expect_usize(
        input.activation_lookup_rows,
        ZKAI_D64_ACTIVATION_LOOKUP_ROWS,
        "activation lookup rows",
    )?;
    expect_usize(
        input.swiglu_mix_rows,
        ZKAI_D64_SWIGLU_MIX_ROWS,
        "SwiGLU mix rows",
    )?;
    expect_i64(input.scale_q8, ZKAI_D64_SCALE_Q8, "q8 scale")?;
    expect_i64(
        input.activation_clamp_q8,
        ZKAI_D64_ACTIVATION_CLAMP_Q8,
        "activation clamp q8",
    )?;
    expect_eq(
        &input.source_gate_value_projection_proof_version,
        ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION,
        "source gate/value proof version",
    )?;
    expect_eq(
        &input.source_gate_projection_output_commitment,
        ZKAI_D64_GATE_PROJECTION_OUTPUT_COMMITMENT,
        "source gate projection output commitment",
    )?;
    expect_eq(
        &input.source_value_projection_output_commitment,
        ZKAI_D64_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "source value projection output commitment",
    )?;
    expect_eq(
        &input.source_gate_value_projection_output_commitment,
        ZKAI_D64_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "source gate/value projection output commitment",
    )?;
    expect_eq(
        &input.activation_lookup_commitment,
        ZKAI_D64_ACTIVATION_LOOKUP_COMMITMENT,
        "activation lookup commitment",
    )?;
    expect_eq(
        &activation_lookup_commitment()?,
        &input.activation_lookup_commitment,
        "activation lookup recomputed commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        ZKAI_D64_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "proof-native parameter commitment",
    )?;
    expect_eq(
        &input.activation_output_commitment,
        ZKAI_D64_ACTIVATION_OUTPUT_COMMITMENT,
        "activation output commitment",
    )?;
    if input.hidden_activation_commitment == ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT {
        return Err(activation_swiglu_error(
            "hidden activation commitment must not relabel as full output activation commitment",
        ));
    }
    expect_eq(
        &input.hidden_activation_commitment,
        ZKAI_D64_HIDDEN_ACTIVATION_COMMITMENT,
        "hidden activation commitment",
    )?;
    expect_eq(
        &input.activation_swiglu_row_commitment,
        ZKAI_D64_ACTIVATION_SWIGLU_ROW_COMMITMENT,
        "activation/SwiGLU row commitment",
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
        ZKAI_D64_ACTIVATION_SWIGLU_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    if input.gate_projection_q8.len() != ZKAI_D64_FF_DIM {
        return Err(activation_swiglu_error(
            "gate projection output vector length mismatch",
        ));
    }
    if input.value_projection_q8.len() != ZKAI_D64_FF_DIM {
        return Err(activation_swiglu_error(
            "value projection output vector length mismatch",
        ));
    }
    if input.activated_gate_q8.len() != ZKAI_D64_FF_DIM {
        return Err(activation_swiglu_error(
            "activation output vector length mismatch",
        ));
    }
    if input.hidden_q8.len() != ZKAI_D64_FF_DIM {
        return Err(activation_swiglu_error(
            "hidden activation output vector length mismatch",
        ));
    }
    for (label, values) in [
        ("gate projection q8", &input.gate_projection_q8),
        ("value projection q8", &input.value_projection_q8),
        ("activation q8", &input.activated_gate_q8),
        ("hidden activation q8", &input.hidden_q8),
    ] {
        for (index, value) in values.iter().enumerate() {
            expect_signed_m31(*value, &format!("{label} {index}"))?;
        }
    }
    expect_eq(
        &sequence_commitment(
            &input.gate_projection_q8,
            GATE_PROJECTION_OUTPUT_DOMAIN,
            ZKAI_D64_FF_DIM,
        ),
        &input.source_gate_projection_output_commitment,
        "source gate projection recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &input.value_projection_q8,
            VALUE_PROJECTION_OUTPUT_DOMAIN,
            ZKAI_D64_FF_DIM,
        ),
        &input.source_value_projection_output_commitment,
        "source value projection recomputed commitment",
    )?;
    expect_eq(
        &gate_value_output_commitment(&input.gate_projection_q8, &input.value_projection_q8),
        &input.source_gate_value_projection_output_commitment,
        "source gate/value projection recomputed commitment",
    )?;
    let rows = build_rows(&input.gate_projection_q8, &input.value_projection_q8)?;
    let activated: Vec<i64> = rows.iter().map(|row| row.activation_q8).collect();
    let hidden: Vec<i64> = rows.iter().map(|row| row.hidden_q8).collect();
    if activated != input.activated_gate_q8 {
        return Err(activation_swiglu_error("activation output drift"));
    }
    if hidden != input.hidden_q8 {
        return Err(activation_swiglu_error("hidden activation output drift"));
    }
    for (expected_row_index, row) in rows.iter().enumerate() {
        validate_activation_swiglu_row(row, expected_row_index)?;
    }
    expect_eq(
        &sequence_commitment(
            &input.activated_gate_q8,
            ACTIVATION_OUTPUT_DOMAIN,
            ZKAI_D64_FF_DIM,
        ),
        &input.activation_output_commitment,
        "activation output recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(&input.hidden_q8, HIDDEN_ACTIVATION_DOMAIN, ZKAI_D64_FF_DIM),
        &input.hidden_activation_commitment,
        "hidden activation recomputed commitment",
    )?;
    expect_eq(
        &rows_commitment(&rows),
        &input.activation_swiglu_row_commitment,
        "activation/SwiGLU row recomputed commitment",
    )?;
    Ok(())
}

fn validate_activation_swiglu_row(
    row: &D64ActivationSwiGluRow,
    expected_index: usize,
) -> Result<()> {
    expect_usize(row.row_index, expected_index, "row index")?;
    expect_signed_m31(row.gate_q8, "gate q8")?;
    expect_signed_m31(row.clamped_gate_q8, "clamped gate q8")?;
    expect_signed_m31(row.activation_table_index, "activation table index")?;
    expect_signed_m31(row.activation_q8, "activation q8")?;
    expect_signed_m31(row.value_q8, "value q8")?;
    expect_signed_m31(row.product_q16, "product q16")?;
    expect_signed_m31(row.hidden_q8, "hidden q8")?;
    expect_signed_m31(row.remainder_q16, "remainder q16")?;
    let clamped = row
        .gate_q8
        .clamp(-ZKAI_D64_ACTIVATION_CLAMP_Q8, ZKAI_D64_ACTIVATION_CLAMP_Q8);
    expect_i64(row.clamped_gate_q8, clamped, "activation clamp relation")?;
    expect_i64(
        row.activation_table_index,
        clamped + ZKAI_D64_ACTIVATION_CLAMP_Q8,
        "activation table index relation",
    )?;
    if !(0..=2 * ZKAI_D64_ACTIVATION_CLAMP_Q8).contains(&row.activation_table_index) {
        return Err(activation_swiglu_error(
            "activation table index range drift",
        ));
    }
    expect_i64(
        row.activation_q8,
        activation_lut_value(row.gate_q8)?,
        "activation lookup relation",
    )?;
    expect_i64(
        row.product_q16,
        checked_mul_i64(row.activation_q8, row.value_q8, "SwiGLU product")?,
        "SwiGLU product relation",
    )?;
    expect_i64(
        row.product_q16,
        checked_add_i64(
            checked_mul_i64(row.hidden_q8, ZKAI_D64_SCALE_Q8, "SwiGLU quotient product")?,
            row.remainder_q16,
            "SwiGLU quotient plus remainder",
        )?,
        "SwiGLU floor relation",
    )?;
    if !(0..ZKAI_D64_SCALE_Q8).contains(&row.remainder_q16) {
        return Err(activation_swiglu_error("SwiGLU remainder range drift"));
    }
    Ok(())
}

fn build_rows(gate: &[i64], value: &[i64]) -> Result<Vec<D64ActivationSwiGluRow>> {
    if gate.len() != ZKAI_D64_FF_DIM || value.len() != ZKAI_D64_FF_DIM {
        return Err(activation_swiglu_error("projection vector length mismatch"));
    }
    let mut rows = Vec::with_capacity(ZKAI_D64_ACTIVATION_SWIGLU_ROW_COUNT);
    for (row_index, (gate_q8, value_q8)) in gate.iter().zip(value.iter()).enumerate() {
        let clamped_gate_q8 =
            (*gate_q8).clamp(-ZKAI_D64_ACTIVATION_CLAMP_Q8, ZKAI_D64_ACTIVATION_CLAMP_Q8);
        let activation_q8 = activation_lut_value(*gate_q8)?;
        let product_q16 = checked_mul_i64(activation_q8, *value_q8, "SwiGLU product")?;
        let hidden_q8 = product_q16.div_euclid(ZKAI_D64_SCALE_Q8);
        let remainder_q16 = product_q16.rem_euclid(ZKAI_D64_SCALE_Q8);
        rows.push(D64ActivationSwiGluRow {
            row_index,
            gate_q8: *gate_q8,
            clamped_gate_q8,
            activation_table_index: clamped_gate_q8 + ZKAI_D64_ACTIVATION_CLAMP_Q8,
            activation_q8,
            value_q8: *value_q8,
            product_q16,
            hidden_q8,
            remainder_q16,
        });
    }
    Ok(rows)
}

fn activation_lut_value(gate_q8: i64) -> Result<i64> {
    let x_q8 = gate_q8.clamp(-ZKAI_D64_ACTIVATION_CLAMP_Q8, ZKAI_D64_ACTIVATION_CLAMP_Q8);
    let denominator = x_q8.abs() + ZKAI_D64_ACTIVATION_CLAMP_Q8;
    let numerator = checked_mul_i64(32768, x_q8, "activation sigmoid numerator")?;
    let mut sigmoid_q16 = 32768 + numerator.div_euclid(denominator);
    sigmoid_q16 = sigmoid_q16.clamp(0, 65536);
    let product = checked_mul_i64(x_q8, sigmoid_q16, "activation lookup product")?;
    Ok(product.div_euclid(65536))
}

fn activation_lookup_commitment() -> Result<String> {
    let mut table = Vec::with_capacity(ZKAI_D64_ACTIVATION_TABLE_ROWS);
    for x_q8 in -ZKAI_D64_ACTIVATION_CLAMP_Q8..=ZKAI_D64_ACTIVATION_CLAMP_Q8 {
        table.push(activation_lut_value(x_q8)?);
    }
    Ok(sequence_commitment(
        &table,
        ACTIVATION_LOOKUP_DOMAIN,
        ZKAI_D64_ACTIVATION_TABLE_ROWS,
    ))
}

fn prove_activation_swiglu_rows(input: &ZkAiD64ActivationSwiGluProofInput) -> Result<Vec<u8>> {
    let component = activation_swiglu_component();
    let config = activation_swiglu_pcs_config();
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
    tree_builder.extend_evals(activation_swiglu_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(activation_swiglu_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "d64 activation/SwiGLU AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D64ActivationSwiGluProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_activation_swiglu_rows(
    input: &ZkAiD64ActivationSwiGluProofInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D64ActivationSwiGluProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_activation_swiglu_pcs_config(stark_proof.config)?;
    let component = activation_swiglu_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D64_ACTIVATION_SWIGLU_EXPECTED_TRACE_COMMITMENTS {
        return Err(activation_swiglu_error(format!(
            "internal activation/SwiGLU component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D64_ACTIVATION_SWIGLU_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D64_ACTIVATION_SWIGLU_EXPECTED_PROOF_COMMITMENTS {
        return Err(activation_swiglu_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D64_ACTIVATION_SWIGLU_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = activation_swiglu_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(activation_swiglu_error(
            "preprocessed row commitment does not match checked activation/SwiGLU rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(activation_swiglu_error(
            "base row commitment does not match checked activation/SwiGLU rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| activation_swiglu_error(format!("STARK verification failed: {error}")))
}

fn validate_activation_swiglu_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(activation_swiglu_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(activation_swiglu_pcs_config())
}

fn activation_swiglu_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn activation_swiglu_commitment_roots(
    input: &ZkAiD64ActivationSwiGluProofInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = activation_swiglu_component();
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
    tree_builder.extend_evals(activation_swiglu_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(activation_swiglu_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn activation_swiglu_component() -> FrameworkComponent<D64ActivationSwiGluEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D64ActivationSwiGluEval {
            log_size: D64_ACTIVATION_SWIGLU_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn activation_swiglu_trace(
    input: &ZkAiD64ActivationSwiGluProofInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D64_ACTIVATION_SWIGLU_LOG_SIZE).circle_domain();
    let rows = build_rows(&input.gate_projection_q8, &input.value_projection_q8)
        .expect("validated activation/SwiGLU rows");
    let columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.row_index)).collect(),
        rows.iter().map(|row| field_i64(row.gate_q8)).collect(),
        rows.iter()
            .map(|row| field_i64(row.clamped_gate_q8))
            .collect(),
        rows.iter()
            .map(|row| field_i64(row.activation_table_index))
            .collect(),
        rows.iter()
            .map(|row| field_i64(row.activation_q8))
            .collect(),
        rows.iter().map(|row| field_i64(row.value_q8)).collect(),
        rows.iter().map(|row| field_i64(row.product_q16)).collect(),
        rows.iter().map(|row| field_i64(row.hidden_q8)).collect(),
        rows.iter()
            .map(|row| field_i64(row.remainder_q16))
            .collect(),
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

fn rows_commitment(rows: &[D64ActivationSwiGluRow]) -> String {
    let rows_json = canonical_row_material(rows);
    let rows_sha256 = sha256_hex(rows_json.as_bytes());
    let payload = format!(
        "{{\"encoding\":\"d64_activation_swiglu_rows_v1\",\"rows_sha256\":\"{}\",\"shape\":[{},9]}}",
        rows_sha256,
        rows.len()
    );
    blake2b_commitment_bytes(payload.as_bytes(), ACTIVATION_SWIGLU_ROW_DOMAIN)
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

fn canonical_row_material(rows: &[D64ActivationSwiGluRow]) -> String {
    let mut out = String::from("[");
    for (index, row) in rows.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        out.push('[');
        for (field_index, value) in [
            row.row_index as i64,
            row.gate_q8,
            row.clamped_gate_q8,
            row.activation_table_index,
            row.activation_q8,
            row.value_q8,
            row.product_q16,
            row.hidden_q8,
            row.remainder_q16,
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
        return Err(activation_swiglu_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(activation_swiglu_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(activation_swiglu_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(activation_swiglu_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
}

fn checked_mul_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_mul(rhs)
        .ok_or_else(|| activation_swiglu_error(format!("{label} overflow")))
}

fn checked_add_i64(lhs: i64, rhs: i64, label: &str) -> Result<i64> {
    lhs.checked_add(rhs)
        .ok_or_else(|| activation_swiglu_error(format!("{label} overflow")))
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
        return Err(activation_swiglu_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn activation_swiglu_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 activation/SwiGLU proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json"
    );

    fn input() -> ZkAiD64ActivationSwiGluProofInput {
        zkai_d64_activation_swiglu_input_from_json_str(INPUT_JSON).expect("activation/SwiGLU input")
    }

    #[test]
    fn activation_swiglu_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(input.gate_projection_q8.len(), ZKAI_D64_FF_DIM);
        let rows = build_rows(&input.gate_projection_q8, &input.value_projection_q8)
            .expect("derived rows");
        assert_eq!(rows.len(), ZKAI_D64_ACTIVATION_SWIGLU_ROW_COUNT);
        assert_eq!(rows[0].gate_q8, -328);
        assert_eq!(rows[0].activation_q8, -125);
        assert_eq!(rows[0].value_q8, 139);
        assert_eq!(rows[0].hidden_q8, -68);
        assert_eq!(rows[0].remainder_q16, 33);
        assert_eq!(
            input.source_gate_value_projection_output_commitment,
            ZKAI_D64_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT
        );
        assert_eq!(
            input.hidden_activation_commitment,
            ZKAI_D64_HIDDEN_ACTIVATION_COMMITMENT
        );
        assert_ne!(
            input.hidden_activation_commitment,
            ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT
        );
    }

    #[test]
    fn activation_lookup_commitment_matches_deterministic_table() {
        assert_eq!(
            activation_lookup_commitment().expect("activation lookup commitment"),
            ZKAI_D64_ACTIVATION_LOOKUP_COMMITMENT
        );
    }

    #[test]
    fn activation_swiglu_pcs_config_uses_shared_publication_v1_profile() {
        let actual = activation_swiglu_pcs_config();
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
    fn activation_swiglu_air_proof_round_trips() {
        let input = input();
        let envelope =
            prove_zkai_d64_activation_swiglu_envelope(&input).expect("activation/SwiGLU proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d64_activation_swiglu_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn activation_swiglu_rejects_hidden_relabeling_as_full_output() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["hidden_activation_commitment"] =
            Value::String(ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d64_activation_swiglu_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("must not relabel"));
    }

    #[test]
    fn activation_swiglu_rejects_gate_projection_vector_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["gate_projection_q8"][0] = Value::from(-2);
        let error = zkai_d64_activation_swiglu_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("source gate projection recomputed commitment"));
    }

    #[test]
    fn activation_swiglu_rejects_activation_output_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["activated_gate_q8"][0] = Value::from(0);
        let error = zkai_d64_activation_swiglu_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("activation output drift"));
    }

    #[test]
    fn activation_swiglu_rejects_hidden_output_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["hidden_q8"][0] = Value::from(0);
        let error = zkai_d64_activation_swiglu_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("hidden activation output drift"));
    }

    #[test]
    fn activation_swiglu_rejects_activation_lookup_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["activation_lookup_commitment"] =
            Value::String(format!("blake2b-256:{}", "55".repeat(32)));
        let error = zkai_d64_activation_swiglu_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("activation lookup commitment"));
    }

    #[test]
    fn activation_swiglu_rejects_row_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["activation_swiglu_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "77".repeat(32)));
        let error = zkai_d64_activation_swiglu_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("activation/SwiGLU row commitment"));
    }

    #[test]
    fn activation_swiglu_rejects_oversized_input_json() {
        let oversized = " ".repeat(ZKAI_D64_ACTIVATION_SWIGLU_MAX_JSON_BYTES + 1);
        let error = zkai_d64_activation_swiglu_input_from_json_str(&oversized).unwrap_err();
        assert!(error.to_string().contains("input JSON exceeds max size"));
    }

    #[test]
    fn activation_swiglu_rejects_oversized_proof_bytes() {
        let input = input();
        let envelope = ZkAiD64ActivationSwiGluEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D64_ACTIVATION_SWIGLU_PROOF_VERSION.to_string(),
            statement_version: ZKAI_D64_ACTIVATION_SWIGLU_STATEMENT_VERSION.to_string(),
            semantic_scope: ZKAI_D64_ACTIVATION_SWIGLU_SEMANTIC_SCOPE.to_string(),
            decision: ZKAI_D64_ACTIVATION_SWIGLU_DECISION.to_string(),
            source_gate_value_projection_proof_version:
                ZKAI_D64_GATE_VALUE_PROJECTION_PROOF_VERSION.to_string(),
            input,
            proof: vec![0u8; ZKAI_D64_ACTIVATION_SWIGLU_MAX_PROOF_BYTES + 1],
        };
        let error = verify_zkai_d64_activation_swiglu_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof bytes exceed bounded verifier limit"));
    }

    #[test]
    fn activation_swiglu_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_activation_swiglu_envelope(&input).expect("activation/SwiGLU proof");
        let last = envelope.proof.len() - 1;
        envelope.proof[last] ^= 0x01;
        assert!(verify_zkai_d64_activation_swiglu_envelope(&envelope).is_err());
    }

    #[test]
    fn activation_swiglu_rejects_commitment_vector_shape_drift() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_activation_swiglu_envelope(&input).expect("activation/SwiGLU proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof payload json");
        let error = verify_zkai_d64_activation_swiglu_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }
}
