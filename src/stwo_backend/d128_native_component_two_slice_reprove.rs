use ark_ff::Zero;
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use stwo::core::air::{Component, Components};
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
use stwo::prover::{prove, CommitmentSchemeProver, ComponentProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    EvalAtRow, FrameworkComponent, FrameworkEval, TraceLocationAllocator,
};

use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

use super::d128_native_rmsnorm_public_row_proof::{
    zkai_d128_rmsnorm_public_row_component_with_allocator,
    zkai_d128_rmsnorm_public_row_input_from_json_str,
    zkai_d128_rmsnorm_public_row_preprocessed_column_ids,
    zkai_d128_rmsnorm_public_row_remainder_bit_column_id,
    zkai_d128_rmsnorm_public_row_scalar_bit_column_id, zkai_d128_rmsnorm_public_row_trace,
    ZkAiD128RmsnormPublicRowProofInput, ZKAI_D128_RMSNORM_AVERAGE_SQUARE_FLOOR_COLUMN_ID,
    ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS, ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
    ZKAI_D128_RMSNORM_SQRT_HIGH_GAP_COLUMN_ID, ZKAI_D128_RMSNORM_SQRT_LOW_DELTA_COLUMN_ID,
};
use super::d128_native_rmsnorm_to_projection_bridge_proof::{
    zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator,
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str,
    zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids,
    zkai_d128_rmsnorm_to_projection_bridge_trace, ZkAiD128RmsnormToProjectionBridgeInput,
    ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT, ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
};
use super::d128_native_two_slice_outer_statement_proof::{
    ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_NATIVE_PARAMETER_COMMITMENT,
    ZKAI_D128_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_TWO_SLICE_ACCUMULATOR_COMMITMENT,
    ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION,
    ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_TARGET_ID,
    ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN, ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT,
};

pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_INPUT_SCHEMA: &str =
    "zkai-d128-component-native-two-slice-reprove-input-v1";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D128_COMPONENT_NATIVE_TWO_SLICE_REPROVE";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_PROOF_VERSION: &str =
    "stwo-d128-component-native-two-slice-reprove-v1";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_STATEMENT_VERSION: &str =
    "zkai-d128-component-native-two-slice-reprove-statement-v1";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_PROOF_VERSION: &str =
    "stwo-d128-component-native-two-slice-compact-preprocessed-reprove-v1";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_STATEMENT_VERSION: &str =
    "zkai-d128-component-native-two-slice-compact-preprocessed-reprove-statement-v1";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SEMANTIC_SCOPE: &str =
    "component_native_reprove_of_rmsnorm_public_rows_and_projection_bridge";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_SEMANTIC_SCOPE: &str =
    "component_native_reprove_of_public_rmsnorm_and_projection_bridge_using_compact_preprocessed_rows";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_DECISION: &str =
    "GO_COMPONENT_NATIVE_TWO_SLICE_REPROVE_PROOF_OBJECT";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_DECISION: &str =
    "GO_COMPONENT_NATIVE_TWO_SLICE_COMPACT_PREPROCESSED_PROOF_OBJECT";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_OPERATION: &str =
    "d128_component_native_two_slice_reprove";
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_WIDTH: usize = 128;
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SELECTED_ROWS: usize = 256;
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SLICE_COUNT: usize = 2;
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES: usize = 2_097_152;
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_PROOF_BYTES: usize = 1_048_576;
pub const ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES: usize = 3_145_728;

const EXPECTED_PROOF_COMMITMENTS: usize = 3;
const EXPECTED_TRACE_COMMITMENT_TREES: usize = 2;
const STATEMENT_DOMAIN: &str = "ptvm:zkai:d128-component-native-two-slice-statement:v1";
const PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:d128-component-native-two-slice-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:d128-component-native-two-slice-proof-native-parameter:v1";
const PROOF_NATIVE_PARAMETER_KIND: &str = "d128-component-native-two-slice-reprove-parameters-v1";

const EXPECTED_SELECTED_SLICE_IDS: [&str; 2] = ["rmsnorm_public_rows", "rmsnorm_projection_bridge"];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not stable upstream Stwo binary serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "nested RMSNorm public-row input validated before component reprove",
    "nested projection-bridge input validated before component reprove",
    "RMSNorm output row commitment must equal bridge source output commitment",
    "component preprocessed columns allocated once across both selected components",
    "base trace columns allocated once across both selected components",
    "single native Stwo proof shares commitment/opening plumbing across both components",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- prove docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_component_two_slice_reprove",
    "git diff --check",
    "just gate-fast",
    "just gate",
];
const EXPECTED_COMPACT_PREPROCESSED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- prove-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_component_two_slice_reprove",
    "git diff --check",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128ComponentTwoSliceReproveInput {
    pub schema: String,
    pub decision: String,
    pub operation: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub selected_slice_count: usize,
    pub selected_checked_rows: usize,
    pub selected_slice_ids: Vec<String>,
    pub two_slice_target_commitment: String,
    pub accumulator_commitment: String,
    pub rmsnorm_statement_commitment: String,
    pub rmsnorm_public_instance_commitment: String,
    pub rmsnorm_proof_native_parameter_commitment: String,
    pub projection_bridge_statement_commitment: String,
    pub projection_bridge_public_instance_commitment: String,
    pub projection_bridge_proof_native_parameter_commitment: String,
    pub rmsnorm_output_row_commitment: String,
    pub projection_input_row_commitment: String,
    pub statement_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub rmsnorm_input: ZkAiD128RmsnormPublicRowProofInput,
    pub projection_bridge_input: ZkAiD128RmsnormToProjectionBridgeInput,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128ComponentTwoSliceReproveEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD128ComponentTwoSliceReproveInput,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD128ComponentTwoSliceReproveInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct D128ComponentTwoSliceReproveProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[derive(Serialize)]
struct StatementPayload<'a> {
    accumulator_commitment: &'a str,
    operation: &'a str,
    projection_bridge_proof_native_parameter_commitment: &'a str,
    projection_bridge_public_instance_commitment: &'a str,
    projection_bridge_statement_commitment: &'a str,
    projection_input_row_commitment: &'a str,
    required_backend_version: &'a str,
    rmsnorm_output_row_commitment: &'a str,
    rmsnorm_proof_native_parameter_commitment: &'a str,
    rmsnorm_public_instance_commitment: &'a str,
    rmsnorm_statement_commitment: &'a str,
    selected_checked_rows: usize,
    selected_slice_ids: &'a [String],
    target_id: &'a str,
    two_slice_target_commitment: &'a str,
    verifier_domain: &'a str,
    width: usize,
}

#[derive(Serialize)]
struct PublicInstancePayload<'a> {
    operation: &'a str,
    selected_checked_rows: usize,
    statement_commitment: &'a str,
    two_slice_target_commitment: &'a str,
}

#[derive(Serialize)]
struct ProofNativeParameterPayload<'a> {
    kind: &'a str,
    statement_commitment: &'a str,
}

pub fn zkai_d128_component_two_slice_reprove_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128ComponentTwoSliceReproveInput> {
    if raw_json.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES {
        return Err(reprove_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD128ComponentTwoSliceReproveInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_reprove_input(&input)?;
    Ok(input)
}

pub fn zkai_d128_component_two_slice_reprove_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiD128ComponentTwoSliceReproveEnvelope> {
    if raw_json.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES {
        return Err(reprove_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiD128ComponentTwoSliceReproveEnvelope = serde_json::from_slice(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_reprove_envelope(&envelope)?;
    Ok(envelope)
}

pub fn zkai_d128_component_two_slice_compact_preprocessed_reprove_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope> {
    if raw_json.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES {
        return Err(reprove_error(format!(
            "compact preprocessed envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope =
        serde_json::from_slice(raw_json)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_compact_preprocessed_reprove_envelope(&envelope)?;
    Ok(envelope)
}

pub fn build_zkai_d128_component_two_slice_reprove_input(
    rmsnorm_input: ZkAiD128RmsnormPublicRowProofInput,
    projection_bridge_input: ZkAiD128RmsnormToProjectionBridgeInput,
) -> Result<ZkAiD128ComponentTwoSliceReproveInput> {
    validate_nested_rmsnorm_input(&rmsnorm_input)?;
    validate_nested_bridge_input(&projection_bridge_input)?;
    let selected_slice_ids = EXPECTED_SELECTED_SLICE_IDS
        .iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    let mut input = ZkAiD128ComponentTwoSliceReproveInput {
        schema: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_INPUT_SCHEMA.to_string(),
        decision: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_INPUT_DECISION.to_string(),
        operation: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_OPERATION.to_string(),
        target_id: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_TARGET_ID.to_string(),
        required_backend_version: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION
            .to_string(),
        verifier_domain: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN.to_string(),
        width: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_WIDTH,
        selected_slice_count: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SLICE_COUNT,
        selected_checked_rows: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SELECTED_ROWS,
        selected_slice_ids,
        two_slice_target_commitment: ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT.to_string(),
        accumulator_commitment: ZKAI_D128_TWO_SLICE_ACCUMULATOR_COMMITMENT.to_string(),
        rmsnorm_statement_commitment: ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT.to_string(),
        rmsnorm_public_instance_commitment: ZKAI_D128_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT
            .to_string(),
        rmsnorm_proof_native_parameter_commitment:
            ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_NATIVE_PARAMETER_COMMITMENT.to_string(),
        projection_bridge_statement_commitment:
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT.to_string(),
        projection_bridge_public_instance_commitment:
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT.to_string(),
        projection_bridge_proof_native_parameter_commitment:
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT.to_string(),
        rmsnorm_output_row_commitment: ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT.to_string(),
        projection_input_row_commitment: ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT.to_string(),
        statement_commitment: String::new(),
        public_instance_commitment: String::new(),
        proof_native_parameter_commitment: String::new(),
        rmsnorm_input,
        projection_bridge_input,
        non_claims: EXPECTED_NON_CLAIMS
            .iter()
            .map(|value| value.to_string())
            .collect(),
        proof_verifier_hardening: EXPECTED_PROOF_VERIFIER_HARDENING
            .iter()
            .map(|value| value.to_string())
            .collect(),
        validation_commands: EXPECTED_VALIDATION_COMMANDS
            .iter()
            .map(|value| value.to_string())
            .collect(),
    };
    input.statement_commitment = statement_commitment(&input)?;
    input.public_instance_commitment = public_instance_commitment(&input.statement_commitment)?;
    input.proof_native_parameter_commitment =
        proof_native_parameter_commitment(&input.statement_commitment)?;
    validate_reprove_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d128_component_two_slice_reprove_envelope(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
) -> Result<ZkAiD128ComponentTwoSliceReproveEnvelope> {
    validate_reprove_input(input)?;
    Ok(ZkAiD128ComponentTwoSliceReproveEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_DECISION.to_string(),
        input: input.clone(),
        proof: prove_reprove_components(input)?,
    })
}

pub fn verify_zkai_d128_component_two_slice_reprove_envelope(
    envelope: &ZkAiD128ComponentTwoSliceReproveEnvelope,
) -> Result<bool> {
    validate_reprove_envelope(envelope)?;
    verify_reprove_components(&envelope.input, &envelope.proof)
}

pub fn prove_zkai_d128_component_two_slice_compact_preprocessed_reprove_envelope(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
) -> Result<ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope> {
    validate_reprove_input(input)?;
    let mut compact_input = input.clone();
    compact_input.validation_commands = EXPECTED_COMPACT_PREPROCESSED_VALIDATION_COMMANDS
        .iter()
        .map(|value| value.to_string())
        .collect();
    validate_compact_preprocessed_reprove_input(&compact_input)?;
    Ok(
        ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_PROOF_VERSION
                .to_string(),
            statement_version: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_STATEMENT_VERSION
                .to_string(),
            semantic_scope: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_SEMANTIC_SCOPE
                .to_string(),
            decision: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_DECISION.to_string(),
            input: compact_input.clone(),
            proof: prove_compact_preprocessed_reprove_components(&compact_input)?,
        },
    )
}

pub fn verify_zkai_d128_component_two_slice_compact_preprocessed_reprove_envelope(
    envelope: &ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope,
) -> Result<bool> {
    validate_compact_preprocessed_reprove_envelope(envelope)?;
    verify_compact_preprocessed_reprove_components(&envelope.input, &envelope.proof)
}

fn validate_reprove_envelope(envelope: &ZkAiD128ComponentTwoSliceReproveEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(reprove_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(reprove_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_PROOF_BYTES {
        return Err(reprove_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_PROOF_BYTES
        )));
    }
    validate_reprove_input(&envelope.input)
}

fn validate_compact_preprocessed_reprove_envelope(
    envelope: &ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope,
) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(reprove_error(
            "compact preprocessed proof backend is not Stwo",
        ));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_PROOF_VERSION,
        "compact preprocessed proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_STATEMENT_VERSION,
        "compact preprocessed statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_SEMANTIC_SCOPE,
        "compact preprocessed semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_DECISION,
        "compact preprocessed decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(reprove_error(
            "compact preprocessed proof bytes must not be empty",
        ));
    }
    if envelope.proof.len() > ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_PROOF_BYTES {
        return Err(reprove_error(format!(
            "compact preprocessed proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_MAX_PROOF_BYTES
        )));
    }
    validate_compact_preprocessed_reprove_input(&envelope.input)
}

fn validate_reprove_input(input: &ZkAiD128ComponentTwoSliceReproveInput) -> Result<()> {
    validate_reprove_input_with_validation_commands(input, EXPECTED_VALIDATION_COMMANDS)
}

fn validate_compact_preprocessed_reprove_input(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
) -> Result<()> {
    validate_reprove_input_with_validation_commands(
        input,
        EXPECTED_COMPACT_PREPROCESSED_VALIDATION_COMMANDS,
    )
}

fn validate_reprove_input_with_validation_commands(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
    expected_validation_commands: &[&str],
) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(
        &input.operation,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_OPERATION,
        "operation",
    )?;
    expect_eq(
        &input.target_id,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_TARGET_ID,
        "target id",
    )?;
    expect_eq(
        &input.required_backend_version,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_usize(
        input.width,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_WIDTH,
        "width",
    )?;
    expect_usize(
        input.selected_slice_count,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SLICE_COUNT,
        "selected slice count",
    )?;
    expect_usize(
        input.selected_checked_rows,
        ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SELECTED_ROWS,
        "selected checked rows",
    )?;
    let expected_ids = EXPECTED_SELECTED_SLICE_IDS
        .iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    if input.selected_slice_ids != expected_ids {
        return Err(reprove_error("selected slice id order drift"));
    }
    expect_eq(
        &input.two_slice_target_commitment,
        ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT,
        "two-slice target commitment",
    )?;
    expect_eq(
        &input.accumulator_commitment,
        ZKAI_D128_TWO_SLICE_ACCUMULATOR_COMMITMENT,
        "accumulator commitment",
    )?;
    expect_eq(
        &input.rmsnorm_statement_commitment,
        ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
        "RMSNorm statement commitment",
    )?;
    expect_eq(
        &input.rmsnorm_public_instance_commitment,
        ZKAI_D128_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT,
        "RMSNorm public-instance commitment",
    )?;
    expect_eq(
        &input.rmsnorm_proof_native_parameter_commitment,
        ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "RMSNorm proof-native parameter commitment",
    )?;
    expect_eq(
        &input.projection_bridge_statement_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
        "projection-bridge statement commitment",
    )?;
    expect_eq(
        &input.projection_bridge_public_instance_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
        "projection-bridge public-instance commitment",
    )?;
    expect_eq(
        &input.projection_bridge_proof_native_parameter_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "projection-bridge proof-native parameter commitment",
    )?;
    expect_eq(
        &input.rmsnorm_output_row_commitment,
        ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT,
        "RMSNorm output row commitment",
    )?;
    expect_eq(
        &input.projection_input_row_commitment,
        ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT,
        "projection input row commitment",
    )?;
    validate_nested_rmsnorm_input(&input.rmsnorm_input)?;
    validate_nested_bridge_input(&input.projection_bridge_input)?;
    expect_eq(
        &input.rmsnorm_input.rmsnorm_output_row_commitment,
        &input
            .projection_bridge_input
            .source_rmsnorm_output_row_commitment,
        "RMSNorm output row handoff commitment",
    )?;
    expect_eq(
        &input.rmsnorm_output_row_commitment,
        &input.rmsnorm_input.rmsnorm_output_row_commitment,
        "RMSNorm output row input commitment",
    )?;
    expect_eq(
        &input.projection_input_row_commitment,
        &input
            .projection_bridge_input
            .projection_input_row_commitment,
        "projection input row input commitment",
    )?;
    expect_str_list_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non claims")?;
    expect_str_list_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_str_list_eq(
        &input.validation_commands,
        expected_validation_commands,
        "validation commands",
    )?;
    let statement = statement_commitment(input)?;
    expect_eq(
        &input.statement_commitment,
        &statement,
        "statement commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        &public_instance_commitment(&statement)?,
        "public instance commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        &proof_native_parameter_commitment(&statement)?,
        "proof-native parameter commitment",
    )?;
    Ok(())
}

fn validate_nested_rmsnorm_input(input: &ZkAiD128RmsnormPublicRowProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_rmsnorm_public_row_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_bridge_input(input: &ZkAiD128RmsnormToProjectionBridgeInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(&raw)?;
    Ok(())
}

fn prove_reprove_components(input: &ZkAiD128ComponentTwoSliceReproveInput) -> Result<Vec<u8>> {
    let preprocessed_ids = component_preprocessed_column_ids();
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let config = reprove_pcs_config();
    let max_constraint_log_degree_bound = rmsnorm_component
        .max_constraint_log_degree_bound()
        .max(bridge_component.max_constraint_log_degree_bound());
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(component_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(component_trace(input));
    tree_builder.commit(channel);

    let components: [&dyn ComponentProver<SimdBackend>; 2] =
        [&rmsnorm_component, &bridge_component];
    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&components, channel, commitment_scheme)
            .map_err(|error| {
                reprove_error(format!(
                    "d128 component-native two-slice reprove AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128ComponentTwoSliceReproveProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_reprove_components(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D128ComponentTwoSliceReproveProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_reprove_pcs_config(stark_proof.config)?;
    let preprocessed_ids = component_preprocessed_column_ids();
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let components: Vec<&dyn Component> = vec![&rmsnorm_component, &bridge_component];
    let sizes = Components {
        components: components.clone(),
        n_preprocessed_columns: preprocessed_ids.len(),
    }
    .column_log_sizes();
    if sizes.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(reprove_error(format!(
            "internal component tree count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(reprove_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = reprove_commitment_roots(input, config)?;
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(reprove_error(
            "preprocessed commitment does not match checked component rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(reprove_error(
            "base commitment does not match checked component rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&components, channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| reprove_error(format!("STARK verification failed: {error}")))
}

fn prove_compact_preprocessed_reprove_components(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
) -> Result<Vec<u8>> {
    let preprocessed_ids = component_preprocessed_column_ids();
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = compact_preprocessed_rmsnorm_component_with_allocator(&mut allocator);
    let bridge_component = compact_preprocessed_bridge_component_with_allocator(&mut allocator);
    let config = reprove_pcs_config();
    let max_constraint_log_degree_bound = rmsnorm_component
        .max_constraint_log_degree_bound()
        .max(bridge_component.max_constraint_log_degree_bound());
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let compact_component_trace = component_trace(input);
    if compact_component_trace.len() != preprocessed_ids.len() {
        return Err(reprove_error(format!(
            "compact preprocessed component trace column count drift: got {}, expected {}",
            compact_component_trace.len(),
            preprocessed_ids.len()
        )));
    }
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(compact_component_trace);
    tree_builder.commit(channel);

    let compact_anchor_trace = compact_preprocessed_anchor_trace(input);
    if compact_anchor_trace.len() != EXPECTED_SELECTED_SLICE_IDS.len() {
        return Err(reprove_error(format!(
            "compact anchor trace column count drift: got {}, expected {}",
            compact_anchor_trace.len(),
            EXPECTED_SELECTED_SLICE_IDS.len()
        )));
    }
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(compact_anchor_trace);
    tree_builder.commit(channel);

    let components: [&dyn ComponentProver<SimdBackend>; 2] =
        [&rmsnorm_component, &bridge_component];
    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&components, channel, commitment_scheme)
            .map_err(|error| {
                reprove_error(format!(
                    "d128 compact preprocessed component reprove AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128ComponentTwoSliceReproveProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_compact_preprocessed_reprove_components(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D128ComponentTwoSliceReproveProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_reprove_pcs_config(stark_proof.config)?;
    let preprocessed_ids = component_preprocessed_column_ids();
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = compact_preprocessed_rmsnorm_component_with_allocator(&mut allocator);
    let bridge_component = compact_preprocessed_bridge_component_with_allocator(&mut allocator);
    let components: Vec<&dyn Component> = vec![&rmsnorm_component, &bridge_component];
    let sizes = Components {
        components: components.clone(),
        n_preprocessed_columns: preprocessed_ids.len(),
    }
    .column_log_sizes();
    if sizes.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(reprove_error(format!(
            "internal compact preprocessed component tree count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(reprove_error(format!(
            "compact preprocessed proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = compact_preprocessed_reprove_commitment_roots(input, config)?;
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(reprove_error(
            "compact preprocessed commitment does not match checked component rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(reprove_error(
            "compact anchor commitment does not match checked component rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&components, channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            reprove_error(format!(
                "compact preprocessed STARK verification failed: {error}"
            ))
        })
}

fn reprove_commitment_roots(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let preprocessed_ids = component_preprocessed_column_ids();
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = zkai_d128_rmsnorm_public_row_component_with_allocator(&mut allocator);
    let bridge_component =
        zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(&mut allocator);
    let max_constraint_log_degree_bound = rmsnorm_component
        .max_constraint_log_degree_bound()
        .max(bridge_component.max_constraint_log_degree_bound());
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(component_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(component_trace(input));
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn compact_preprocessed_reprove_commitment_roots(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let preprocessed_ids = component_preprocessed_column_ids();
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let rmsnorm_component = compact_preprocessed_rmsnorm_component_with_allocator(&mut allocator);
    let bridge_component = compact_preprocessed_bridge_component_with_allocator(&mut allocator);
    let max_constraint_log_degree_bound = rmsnorm_component
        .max_constraint_log_degree_bound()
        .max(bridge_component.max_constraint_log_degree_bound());
    let twiddles = SimdBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<SimdBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let compact_component_trace = component_trace(input);
    if compact_component_trace.len() != preprocessed_ids.len() {
        return Err(reprove_error(format!(
            "compact preprocessed component trace column count drift: got {}, expected {}",
            compact_component_trace.len(),
            preprocessed_ids.len()
        )));
    }
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(compact_component_trace);
    tree_builder.commit(channel);

    let compact_anchor_trace = compact_preprocessed_anchor_trace(input);
    if compact_anchor_trace.len() != EXPECTED_SELECTED_SLICE_IDS.len() {
        return Err(reprove_error(format!(
            "compact anchor trace column count drift: got {}, expected {}",
            compact_anchor_trace.len(),
            EXPECTED_SELECTED_SLICE_IDS.len()
        )));
    }
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(compact_anchor_trace);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn validate_reprove_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(reprove_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(reprove_pcs_config())
}

fn reprove_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn component_preprocessed_column_ids() -> Vec<PreProcessedColumnId> {
    let mut ids = zkai_d128_rmsnorm_public_row_preprocessed_column_ids();
    ids.extend(zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids());
    ids
}

fn component_trace(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, stwo::core::fields::m31::BaseField, BitReversedOrder>>
{
    let mut trace = zkai_d128_rmsnorm_public_row_trace(&input.rmsnorm_input);
    trace.extend(zkai_d128_rmsnorm_to_projection_bridge_trace(
        &input.projection_bridge_input,
    ));
    trace
}

const COMPACT_LOG_SIZE: u32 = 7;
const COMPACT_Q8_SCALE: i64 = 256;
const COMPACT_Q8_REMAINDER_BITS: usize = 8;
const COMPACT_RMSNORM_NORM_REMAINDER_GAP_BITS: usize = 31;
const COMPACT_RMSNORM_SCALAR_RANGE_BITS: usize = 17;

#[derive(Debug, Clone)]
struct CompactPreprocessedRmsnormEval {
    log_size: u32,
}

impl FrameworkEval for CompactPreprocessedRmsnormEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let anchor_index = eval.next_trace_mask();
        let index = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[0],
        ));
        eval.add_constraint(anchor_index - index);

        let input_q8 = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[1],
        ));
        let rms_scale_q8 = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[2],
        ));
        let input_square = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[3],
        ));
        let scaled_floor = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[4],
        ));
        let scale_remainder = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[5],
        ));
        let normed_q8 = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[6],
        ));
        let norm_remainder = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[7],
        ));
        let rms_q8 = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_PUBLIC_ROW_COLUMN_IDS[8],
        ));
        let average_square_floor = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_AVERAGE_SQUARE_FLOOR_COLUMN_ID,
        ));
        let sqrt_low_delta = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_SQRT_LOW_DELTA_COLUMN_ID,
        ));
        let sqrt_high_gap = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_SQRT_HIGH_GAP_COLUMN_ID,
        ));

        let one = E::F::from(BaseField::from(1u32));
        let mut low_delta_bits = E::F::from(BaseField::from(0u32));
        for bit_index in 0..COMPACT_RMSNORM_SCALAR_RANGE_BITS {
            let bit = eval.get_preprocessed_column(compact_preprocessed_column_id(
                &zkai_d128_rmsnorm_public_row_scalar_bit_column_id("low", bit_index),
            ));
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            low_delta_bits = low_delta_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut high_gap_bits = E::F::from(BaseField::from(0u32));
        for bit_index in 0..COMPACT_RMSNORM_SCALAR_RANGE_BITS {
            let bit = eval.get_preprocessed_column(compact_preprocessed_column_id(
                &zkai_d128_rmsnorm_public_row_scalar_bit_column_id("high", bit_index),
            ));
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            high_gap_bits = high_gap_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut scale_remainder_bits = E::F::from(BaseField::from(0u32));
        for bit_index in 0..COMPACT_Q8_REMAINDER_BITS {
            let bit = eval.get_preprocessed_column(compact_preprocessed_column_id(
                &zkai_d128_rmsnorm_public_row_remainder_bit_column_id("scale", bit_index),
            ));
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            scale_remainder_bits =
                scale_remainder_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut norm_remainder_gap_bits = E::F::from(BaseField::from(0u32));
        for bit_index in 0..COMPACT_RMSNORM_NORM_REMAINDER_GAP_BITS {
            let bit = eval.get_preprocessed_column(compact_preprocessed_column_id(
                &zkai_d128_rmsnorm_public_row_remainder_bit_column_id("norm_gap", bit_index),
            ));
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            let bit_weight = 1u32
                .checked_shl(bit_index as u32)
                .expect("compact norm remainder gap bit weight");
            norm_remainder_gap_bits =
                norm_remainder_gap_bits + bit * E::F::from(BaseField::from(bit_weight));
        }

        let q8_scale = E::F::from(BaseField::from(COMPACT_Q8_SCALE as u32));
        eval.add_constraint(input_q8.clone() * input_q8.clone() - input_square);
        eval.add_constraint(
            input_q8 * rms_scale_q8
                - scaled_floor.clone() * q8_scale.clone()
                - scale_remainder.clone(),
        );
        eval.add_constraint(scale_remainder - scale_remainder_bits);
        eval.add_constraint(
            scaled_floor * q8_scale - normed_q8 * rms_q8.clone() - norm_remainder.clone(),
        );
        eval.add_constraint(
            norm_remainder + norm_remainder_gap_bits + one.clone() - rms_q8.clone(),
        );
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

#[derive(Debug, Clone)]
struct CompactPreprocessedBridgeEval {
    log_size: u32,
}

impl FrameworkEval for CompactPreprocessedBridgeEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let anchor_index = eval.next_trace_mask();
        let index = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS[0],
        ));
        eval.add_constraint(anchor_index - index);
        let rmsnorm_normed_q8 = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS[1],
        ));
        let projection_input_q8 = eval.get_preprocessed_column(compact_preprocessed_column_id(
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS[2],
        ));
        eval.add_constraint(projection_input_q8 - rmsnorm_normed_q8);
        eval
    }
}

fn compact_preprocessed_rmsnorm_component_with_allocator(
    allocator: &mut TraceLocationAllocator,
) -> impl ComponentProver<SimdBackend> {
    FrameworkComponent::new(
        allocator,
        CompactPreprocessedRmsnormEval {
            log_size: COMPACT_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn compact_preprocessed_bridge_component_with_allocator(
    allocator: &mut TraceLocationAllocator,
) -> impl ComponentProver<SimdBackend> {
    FrameworkComponent::new(
        allocator,
        CompactPreprocessedBridgeEval {
            log_size: COMPACT_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn compact_preprocessed_anchor_trace(
    input: &ZkAiD128ComponentTwoSliceReproveInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(COMPACT_LOG_SIZE).circle_domain();
    let columns: Vec<Vec<BaseField>> = vec![
        input
            .rmsnorm_input
            .rows
            .iter()
            .map(|row| compact_field_usize(row.index))
            .collect(),
        input
            .projection_bridge_input
            .rows
            .iter()
            .map(|row| compact_field_usize(row.index))
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

fn compact_preprocessed_column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

fn compact_field_usize(value: usize) -> BaseField {
    BaseField::from(value as u32)
}

fn statement_commitment(input: &ZkAiD128ComponentTwoSliceReproveInput) -> Result<String> {
    let payload = StatementPayload {
        accumulator_commitment: &input.accumulator_commitment,
        operation: &input.operation,
        projection_bridge_proof_native_parameter_commitment: &input
            .projection_bridge_proof_native_parameter_commitment,
        projection_bridge_public_instance_commitment: &input
            .projection_bridge_public_instance_commitment,
        projection_bridge_statement_commitment: &input.projection_bridge_statement_commitment,
        projection_input_row_commitment: &input.projection_input_row_commitment,
        required_backend_version: &input.required_backend_version,
        rmsnorm_output_row_commitment: &input.rmsnorm_output_row_commitment,
        rmsnorm_proof_native_parameter_commitment: &input.rmsnorm_proof_native_parameter_commitment,
        rmsnorm_public_instance_commitment: &input.rmsnorm_public_instance_commitment,
        rmsnorm_statement_commitment: &input.rmsnorm_statement_commitment,
        selected_checked_rows: input.selected_checked_rows,
        selected_slice_ids: &input.selected_slice_ids,
        target_id: &input.target_id,
        two_slice_target_commitment: &input.two_slice_target_commitment,
        verifier_domain: &input.verifier_domain,
        width: input.width,
    };
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, STATEMENT_DOMAIN))
}

fn public_instance_commitment(statement: &str) -> Result<String> {
    let payload = PublicInstancePayload {
        operation: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_OPERATION,
        selected_checked_rows: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SELECTED_ROWS,
        statement_commitment: statement,
        two_slice_target_commitment: ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT,
    };
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, PUBLIC_INSTANCE_DOMAIN))
}

fn proof_native_parameter_commitment(statement: &str) -> Result<String> {
    let payload = ProofNativeParameterPayload {
        kind: PROOF_NATIVE_PARAMETER_KIND,
        statement_commitment: statement,
    };
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(
        &bytes,
        PROOF_NATIVE_PARAMETER_DOMAIN,
    ))
}

fn blake2b_commitment_bytes(bytes: &[u8], domain: &str) -> String {
    let mut hasher = Blake2bVar::new(32).expect("valid BLAKE2b output size");
    hasher.update(domain.as_bytes());
    hasher.update(b"\0");
    hasher.update(bytes);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("BLAKE2b finalize");
    format!("blake2b-256:{}", hex_lower(&out))
}

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(reprove_error(format!(
            "{label} mismatch: got {actual:?}, expected {expected:?}"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(reprove_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_str_list_eq(actual: &[String], expected: &[&str], label: &str) -> Result<()> {
    let expected_vec = expected
        .iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    if actual != expected_vec {
        return Err(reprove_error(format!(
            "{label} drift: got {:?}, expected {:?}",
            actual, expected_vec
        )));
    }
    Ok(())
}

fn reprove_error(message: impl Into<String>) -> VmError {
    VmError::UnsupportedProof(format!(
        "d128 component-native two-slice reprove: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_input() -> ZkAiD128ComponentTwoSliceReproveInput {
        zkai_d128_component_two_slice_reprove_input_from_json_str(include_str!(
            "../../docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json"
        ))
        .expect("checked component-native input fixture should parse")
    }

    #[test]
    fn component_preprocessed_columns_are_unique() {
        let ids = component_preprocessed_column_ids();
        let mut labels = ids.iter().map(|id| id.id.clone()).collect::<Vec<_>>();
        labels.sort();
        labels.dedup();
        assert_eq!(labels.len(), ids.len());
    }

    #[test]
    fn rejects_selected_slice_id_order_drift() {
        let mut input = fixture_input();
        input.selected_slice_ids.swap(0, 1);
        let error = validate_reprove_input(&input).expect_err("slice-id order drift should reject");
        assert!(error.to_string().contains("selected slice id order drift"));
    }

    #[test]
    fn rejects_empty_proof_envelope() {
        let input = fixture_input();
        let envelope = ZkAiD128ComponentTwoSliceReproveEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_PROOF_VERSION.to_string(),
            statement_version: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_STATEMENT_VERSION.to_string(),
            semantic_scope: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_SEMANTIC_SCOPE.to_string(),
            decision: ZKAI_D128_COMPONENT_TWO_SLICE_REPROVE_DECISION.to_string(),
            input,
            proof: Vec::new(),
        };
        let error =
            validate_reprove_envelope(&envelope).expect_err("empty proof bytes should reject");
        assert!(error.to_string().contains("proof bytes must not be empty"));
    }

    #[test]
    fn compact_anchor_trace_has_one_column_per_selected_component() {
        let input = fixture_input();
        let trace = compact_preprocessed_anchor_trace(&input);
        assert_eq!(trace.len(), EXPECTED_SELECTED_SLICE_IDS.len());
    }

    #[test]
    fn compact_preprocessed_trace_column_count_matches_preprocessed_columns() {
        let input = fixture_input();
        assert_eq!(
            component_trace(&input).len(),
            component_preprocessed_column_ids().len()
        );
    }

    #[test]
    fn rejects_empty_compact_preprocessed_proof_envelope() {
        let input = fixture_input();
        let envelope = ZkAiD128ComponentTwoSliceCompactPreprocessedReproveEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_PROOF_VERSION
                .to_string(),
            statement_version: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_STATEMENT_VERSION
                .to_string(),
            semantic_scope: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_SEMANTIC_SCOPE
                .to_string(),
            decision: ZKAI_D128_COMPONENT_TWO_SLICE_COMPACT_PREPROCESSED_DECISION.to_string(),
            input,
            proof: Vec::new(),
        };
        let error = validate_compact_preprocessed_reprove_envelope(&envelope)
            .expect_err("empty compact proof bytes should reject");
        assert!(error
            .to_string()
            .contains("compact preprocessed proof bytes must not be empty"));
    }

    #[test]
    fn compact_preprocessed_rejects_tampered_anchor_commitment() {
        let input = fixture_input();
        let mut envelope =
            prove_zkai_d128_component_two_slice_compact_preprocessed_reprove_envelope(&input)
                .expect("compact proof should prove");
        let expected_compact_commands = EXPECTED_COMPACT_PREPROCESSED_VALIDATION_COMMANDS
            .iter()
            .map(|value| value.to_string())
            .collect::<Vec<_>>();
        assert_eq!(
            envelope.input.validation_commands,
            expected_compact_commands
        );
        assert!(
            verify_zkai_d128_component_two_slice_compact_preprocessed_reprove_envelope(&envelope)
                .expect("compact proof should verify")
        );

        let mut payload: serde_json::Value =
            serde_json::from_slice(&envelope.proof).expect("compact proof payload should parse");
        let first_commitment = payload["stark_proof"]["commitments"][0].clone();
        payload["stark_proof"]["commitments"][1] = first_commitment;
        envelope.proof = serde_json::to_vec(&payload).expect("compact proof payload should encode");

        let error =
            verify_zkai_d128_component_two_slice_compact_preprocessed_reprove_envelope(&envelope)
                .expect_err("tampered compact anchor commitment should reject");
        assert!(error
            .to_string()
            .contains("compact anchor commitment does not match checked component rows"));
    }
}
