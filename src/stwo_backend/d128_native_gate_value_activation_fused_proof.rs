use std::collections::BTreeSet;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use stwo::core::air::{Component, Components};
use stwo::core::channel::Blake2sM31Channel;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::poly::circle::PolyOps;
use stwo::prover::{prove, CommitmentSchemeProver, ComponentProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::TraceLocationAllocator;

use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

use super::d128_native_activation_swiglu_proof::{
    prove_zkai_d128_activation_swiglu_envelope,
    zkai_d128_activation_swiglu_component_with_allocator,
    zkai_d128_activation_swiglu_input_from_json_str,
    zkai_d128_activation_swiglu_preprocessed_column_ids, zkai_d128_activation_swiglu_trace,
    ZkAiD128ActivationSwiGluProofInput, ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
    ZKAI_D128_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT, ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT,
};
use super::d128_native_gate_value_projection_proof::{
    prove_zkai_d128_gate_value_projection_envelope,
    zkai_d128_gate_value_projection_component_with_allocator,
    zkai_d128_gate_value_projection_input_from_json_str,
    zkai_d128_gate_value_projection_preprocessed_column_ids, zkai_d128_gate_value_projection_rows,
    zkai_d128_gate_value_projection_trace, ZkAiD128GateValueProjectionProofInput,
    ZKAI_D128_GATE_PROJECTION_OUTPUT_COMMITMENT, ZKAI_D128_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
    ZKAI_D128_GATE_VALUE_PROJECTION_PROOF_VERSION,
    ZKAI_D128_GATE_VALUE_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_GATE_VALUE_PROJECTION_STATEMENT_COMMITMENT,
    ZKAI_D128_VALUE_PROJECTION_OUTPUT_COMMITMENT,
};
use super::{publication_v1_pcs_config, publication_v1_pcs_config_matches};

pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_INPUT_SCHEMA: &str =
    "zkai-d128-gate-value-activation-fused-air-proof-input-v1";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D128_GATE_VALUE_ACTIVATION_FUSED_AIR_PROOF";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_PROOF_VERSION: &str =
    "stwo-d128-gate-value-activation-fused-air-proof-v1";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_STATEMENT_VERSION: &str =
    "zkai-d128-gate-value-activation-fused-statement-v1";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_SEMANTIC_SCOPE: &str =
    "d128_gate_value_projection_and_activation_swiglu_rows_fused_in_one_native_stwo_proof";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_DECISION: &str =
    "GO_D128_GATE_VALUE_ACTIVATION_FUSED_AIR_PROOF";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_ROUTE_ID: &str =
    "native_stwo_d128_gate_value_projection_plus_activation_swiglu_fused";
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES: usize = 2_097_152;
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES: usize = 8_388_608;
pub const ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_PROOF_BYTES: usize = 67_108_864;

const WIDTH: usize = 128;
const FF_DIM: usize = 512;
const GATE_VALUE_ROWS: usize = 131_072;
const ACTIVATION_ROWS: usize = 512;
const EXPECTED_TRACE_COMMITMENT_TREES: usize = 2;
const EXPECTED_PROOF_COMMITMENTS: usize = 3;
const STATEMENT_DOMAIN: &str = "ptvm:zkai:d128-gate-value-activation-fused-statement:v1";
const PUBLIC_INSTANCE_DOMAIN: &str =
    "ptvm:zkai:d128-gate-value-activation-fused-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:d128-gate-value-activation-fused-proof-native-parameter:v1";
const PROOF_NATIVE_PARAMETER_KIND: &str =
    "d128-gate-value-activation-fused-proof-native-parameter-v1";
const EXPECTED_TARGET_ID: &str = "rmsnorm-swiglu-residual-d128-v1";
const EXPECTED_REQUIRED_BACKEND_VERSION: &str = "stwo-rmsnorm-swiglu-residual-d128-v1";
const EXPECTED_VERIFIER_DOMAIN: &str = "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1";

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- prove docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- build-input docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json",
    "python3 scripts/zkai_d128_gate_value_activation_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_gate_value_activation_fused_gate",
    "cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_activation_fused_proof --lib",
    "git diff --check",
    "just gate-fast",
    "just gate",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not a full d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not recursion or proof-carrying data",
    "not private parameter-opening proof",
    "not upstream Stwo proof serialization",
    "not timing evidence",
    "not full transformer inference",
    "not production-ready zkML",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "nested gate/value input validated before fused proof construction",
    "nested activation/SwiGLU input validated before fused proof construction",
    "activation source commitments must match the gate/value statement and public instance",
    "activation source gate/value vectors must match the gate/value projection output vectors",
    "component preprocessed columns allocated once across dense and activation components",
    "base trace columns allocated once across dense and activation components",
    "single native Stwo proof shares commitment/opening plumbing across both adjacent components",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128GateValueActivationFusedInput {
    pub schema: String,
    pub decision: String,
    pub route_id: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub ff_dim: usize,
    pub gate_value_row_count: usize,
    pub activation_row_count: usize,
    pub gate_value_proof_version: String,
    pub activation_swiglu_proof_version: String,
    pub gate_value_statement_commitment: String,
    pub gate_value_public_instance_commitment: String,
    pub activation_statement_commitment: String,
    pub activation_public_instance_commitment: String,
    pub gate_projection_output_commitment: String,
    pub value_projection_output_commitment: String,
    pub gate_value_projection_output_commitment: String,
    pub hidden_activation_commitment: String,
    pub statement_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub gate_value_input: ZkAiD128GateValueProjectionProofInput,
    pub activation_input: ZkAiD128ActivationSwiGluProofInput,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128GateValueActivationFusedEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD128GateValueActivationFusedInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct D128GateValueActivationFusedProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d128_gate_value_activation_fused_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128GateValueActivationFusedInput> {
    if raw_json.len() > ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES {
        return Err(fused_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD128GateValueActivationFusedInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_fused_input(&input)?;
    Ok(input)
}

pub fn zkai_d128_gate_value_activation_fused_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiD128GateValueActivationFusedEnvelope> {
    if raw_json.len() > ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES {
        return Err(fused_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiD128GateValueActivationFusedEnvelope = serde_json::from_slice(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_fused_envelope(&envelope)?;
    Ok(envelope)
}

pub fn build_zkai_d128_gate_value_activation_fused_input(
    gate_value_input: ZkAiD128GateValueProjectionProofInput,
    activation_input: ZkAiD128ActivationSwiGluProofInput,
) -> Result<ZkAiD128GateValueActivationFusedInput> {
    validate_nested_gate_value_input(&gate_value_input)?;
    validate_nested_activation_input(&activation_input)?;
    validate_handoff(&gate_value_input, &activation_input)?;
    let mut input = ZkAiD128GateValueActivationFusedInput {
        schema: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_INPUT_SCHEMA.to_string(),
        decision: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_INPUT_DECISION.to_string(),
        route_id: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_ROUTE_ID.to_string(),
        target_id: gate_value_input.target_id.clone(),
        required_backend_version: gate_value_input.required_backend_version.clone(),
        verifier_domain: gate_value_input.verifier_domain.clone(),
        width: WIDTH,
        ff_dim: FF_DIM,
        gate_value_row_count: GATE_VALUE_ROWS,
        activation_row_count: ACTIVATION_ROWS,
        gate_value_proof_version: ZKAI_D128_GATE_VALUE_PROJECTION_PROOF_VERSION.to_string(),
        activation_swiglu_proof_version: ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION.to_string(),
        gate_value_statement_commitment: gate_value_input.statement_commitment.clone(),
        gate_value_public_instance_commitment: gate_value_input.public_instance_commitment.clone(),
        activation_statement_commitment: activation_input.statement_commitment.clone(),
        activation_public_instance_commitment: activation_input.public_instance_commitment.clone(),
        gate_projection_output_commitment: gate_value_input
            .gate_projection_output_commitment
            .clone(),
        value_projection_output_commitment: gate_value_input
            .value_projection_output_commitment
            .clone(),
        gate_value_projection_output_commitment: gate_value_input
            .gate_value_projection_output_commitment
            .clone(),
        hidden_activation_commitment: activation_input.hidden_activation_commitment.clone(),
        statement_commitment: String::new(),
        public_instance_commitment: String::new(),
        proof_native_parameter_commitment: String::new(),
        gate_value_input,
        activation_input,
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
    validate_fused_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d128_gate_value_activation_fused_envelope(
    input: &ZkAiD128GateValueActivationFusedInput,
) -> Result<ZkAiD128GateValueActivationFusedEnvelope> {
    validate_fused_input(input)?;
    Ok(ZkAiD128GateValueActivationFusedEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_DECISION.to_string(),
        input: input.clone(),
        proof: prove_fused_components(input)?,
    })
}

pub fn verify_zkai_d128_gate_value_activation_fused_envelope(
    envelope: &ZkAiD128GateValueActivationFusedEnvelope,
) -> Result<bool> {
    validate_fused_envelope(envelope)?;
    verify_fused_components(&envelope.input, &envelope.proof)
}

pub fn prove_zkai_d128_activation_swiglu_separate_envelope_for_fused_baseline(
    input: &ZkAiD128ActivationSwiGluProofInput,
) -> Result<super::d128_native_activation_swiglu_proof::ZkAiD128ActivationSwiGluEnvelope> {
    prove_zkai_d128_activation_swiglu_envelope(input)
}

pub fn prove_zkai_d128_gate_value_separate_envelope_for_fused_baseline(
    input: &ZkAiD128GateValueProjectionProofInput,
) -> Result<super::d128_native_gate_value_projection_proof::ZkAiD128GateValueProjectionEnvelope> {
    prove_zkai_d128_gate_value_projection_envelope(input)
}

fn validate_fused_envelope(envelope: &ZkAiD128GateValueActivationFusedEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(fused_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(fused_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_PROOF_BYTES {
        return Err(fused_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_MAX_PROOF_BYTES
        )));
    }
    validate_fused_input(&envelope.input)
}

fn validate_fused_input(input: &ZkAiD128GateValueActivationFusedInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(
        &input.route_id,
        ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_ROUTE_ID,
        "route id",
    )?;
    expect_eq(&input.target_id, EXPECTED_TARGET_ID, "target id")?;
    expect_eq(
        &input.verifier_domain,
        EXPECTED_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_usize(input.width, WIDTH, "width")?;
    expect_usize(input.ff_dim, FF_DIM, "ff dim")?;
    expect_usize(
        input.gate_value_row_count,
        GATE_VALUE_ROWS,
        "gate/value row count",
    )?;
    expect_usize(
        input.activation_row_count,
        ACTIVATION_ROWS,
        "activation row count",
    )?;
    expect_eq(
        &input.required_backend_version,
        EXPECTED_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    expect_eq(
        &input.gate_value_proof_version,
        ZKAI_D128_GATE_VALUE_PROJECTION_PROOF_VERSION,
        "gate/value proof version",
    )?;
    expect_eq(
        &input.activation_swiglu_proof_version,
        ZKAI_D128_ACTIVATION_SWIGLU_PROOF_VERSION,
        "activation/SwiGLU proof version",
    )?;
    expect_eq(
        &input.gate_value_statement_commitment,
        ZKAI_D128_GATE_VALUE_PROJECTION_STATEMENT_COMMITMENT,
        "gate/value statement commitment",
    )?;
    expect_eq(
        &input.gate_value_public_instance_commitment,
        ZKAI_D128_GATE_VALUE_PROJECTION_PUBLIC_INSTANCE_COMMITMENT,
        "gate/value public instance commitment",
    )?;
    expect_eq(
        &input.activation_statement_commitment,
        ZKAI_D128_ACTIVATION_SWIGLU_STATEMENT_COMMITMENT,
        "activation statement commitment",
    )?;
    expect_eq(
        &input.activation_public_instance_commitment,
        ZKAI_D128_ACTIVATION_SWIGLU_PUBLIC_INSTANCE_COMMITMENT,
        "activation public instance commitment",
    )?;
    expect_eq(
        &input.gate_projection_output_commitment,
        ZKAI_D128_GATE_PROJECTION_OUTPUT_COMMITMENT,
        "gate projection output commitment",
    )?;
    expect_eq(
        &input.value_projection_output_commitment,
        ZKAI_D128_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "value projection output commitment",
    )?;
    expect_eq(
        &input.gate_value_projection_output_commitment,
        ZKAI_D128_GATE_VALUE_PROJECTION_OUTPUT_COMMITMENT,
        "gate/value projection output commitment",
    )?;
    expect_eq(
        &input.hidden_activation_commitment,
        ZKAI_D128_HIDDEN_ACTIVATION_COMMITMENT,
        "hidden activation commitment",
    )?;
    expect_vec_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non-claims")?;
    expect_vec_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_vec_eq(
        &input.validation_commands,
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
    )?;
    validate_nested_gate_value_input(&input.gate_value_input)?;
    validate_nested_activation_input(&input.activation_input)?;
    validate_handoff(&input.gate_value_input, &input.activation_input)?;
    expect_eq(
        &input.statement_commitment,
        &statement_commitment(input)?,
        "statement commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        &public_instance_commitment(&input.statement_commitment)?,
        "public instance commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        &proof_native_parameter_commitment(&input.statement_commitment)?,
        "proof-native parameter commitment",
    )
}

fn validate_nested_gate_value_input(input: &ZkAiD128GateValueProjectionProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_gate_value_projection_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_nested_activation_input(input: &ZkAiD128ActivationSwiGluProofInput) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    zkai_d128_activation_swiglu_input_from_json_str(&raw)?;
    Ok(())
}

fn validate_handoff(
    gate_value_input: &ZkAiD128GateValueProjectionProofInput,
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
) -> Result<()> {
    expect_eq(
        &activation_input.target_id,
        &gate_value_input.target_id,
        "activation target id matches gate/value target id",
    )?;
    expect_eq(
        &activation_input.required_backend_version,
        &gate_value_input.required_backend_version,
        "activation required backend version matches gate/value required backend version",
    )?;
    expect_eq(
        &activation_input.verifier_domain,
        &gate_value_input.verifier_domain,
        "activation verifier domain matches gate/value verifier domain",
    )?;
    expect_eq(
        &activation_input.source_gate_value_projection_statement_commitment,
        &gate_value_input.statement_commitment,
        "activation source gate/value statement commitment",
    )?;
    expect_eq(
        &activation_input.source_gate_value_projection_public_instance_commitment,
        &gate_value_input.public_instance_commitment,
        "activation source gate/value public instance commitment",
    )?;
    expect_eq(
        &activation_input.source_gate_projection_output_commitment,
        &gate_value_input.gate_projection_output_commitment,
        "activation source gate projection output commitment",
    )?;
    expect_eq(
        &activation_input.source_value_projection_output_commitment,
        &gate_value_input.value_projection_output_commitment,
        "activation source value projection output commitment",
    )?;
    expect_eq(
        &activation_input.source_gate_value_projection_output_commitment,
        &gate_value_input.gate_value_projection_output_commitment,
        "activation source gate/value projection output commitment",
    )?;
    if activation_input.gate_projection_q8 != gate_value_input.gate_projection_q8 {
        return Err(fused_error(
            "activation source gate vector does not match gate/value output vector",
        ));
    }
    if activation_input.value_projection_q8 != gate_value_input.value_projection_q8 {
        return Err(fused_error(
            "activation source value vector does not match gate/value output vector",
        ));
    }
    Ok(())
}

fn prove_fused_components(input: &ZkAiD128GateValueActivationFusedInput) -> Result<Vec<u8>> {
    let gate_rows = zkai_d128_gate_value_projection_rows(&input.gate_value_input)?;
    let preprocessed_ids = fused_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let config = publication_v1_pcs_config();
    let max_constraint_log_degree_bound = gate_value_component
        .max_constraint_log_degree_bound()
        .max(activation_component.max_constraint_log_degree_bound());
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

    let fused_trace = fused_trace(&gate_rows, &input.activation_input)?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(fused_trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(fused_trace);
    tree_builder.commit(channel);

    let components: [&dyn ComponentProver<SimdBackend>; 2] =
        [&gate_value_component, &activation_component];
    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&components, channel, commitment_scheme)
            .map_err(|error| {
                fused_error(format!(
                    "d128 gate/value plus activation fused AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128GateValueActivationFusedProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_fused_components(
    input: &ZkAiD128GateValueActivationFusedInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D128GateValueActivationFusedProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_fused_pcs_config(stark_proof.config)?;
    let preprocessed_ids = fused_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let components: Vec<&dyn Component> = vec![&gate_value_component, &activation_component];
    let sizes = Components {
        components: components.clone(),
        n_preprocessed_columns: preprocessed_ids.len(),
    }
    .column_log_sizes();
    if sizes.len() != EXPECTED_TRACE_COMMITMENT_TREES {
        return Err(fused_error(format!(
            "internal fused component tree count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENT_TREES
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(fused_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = fused_commitment_roots(input, config)?;
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(fused_error(
            "preprocessed commitment does not match checked fused component rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(fused_error(
            "base commitment does not match checked fused component rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&components, channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| fused_error(format!("fused STARK verification failed: {error}")))
}

fn fused_commitment_roots(
    input: &ZkAiD128GateValueActivationFusedInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let gate_rows = zkai_d128_gate_value_projection_rows(&input.gate_value_input)?;
    let preprocessed_ids = fused_preprocessed_column_ids()?;
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_ids);
    let gate_value_component =
        zkai_d128_gate_value_projection_component_with_allocator(&mut allocator);
    let activation_component = zkai_d128_activation_swiglu_component_with_allocator(&mut allocator);
    let max_constraint_log_degree_bound = gate_value_component
        .max_constraint_log_degree_bound()
        .max(activation_component.max_constraint_log_degree_bound());
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

    let trace = fused_trace(&gate_rows, &input.activation_input)?;
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(trace);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn fused_trace(
    gate_rows: &[super::d128_native_gate_value_projection_proof::D128GateValueProjectionMulRow],
    activation_input: &ZkAiD128ActivationSwiGluProofInput,
) -> Result<
    stwo::core::ColumnVec<
        stwo::prover::poly::circle::CircleEvaluation<
            SimdBackend,
            stwo::core::fields::m31::BaseField,
            stwo::prover::poly::BitReversedOrder,
        >,
    >,
> {
    let mut trace = zkai_d128_gate_value_projection_trace(gate_rows)?;
    trace.extend(zkai_d128_activation_swiglu_trace(activation_input)?);
    Ok(trace)
}

fn fused_preprocessed_column_ids() -> Result<Vec<PreProcessedColumnId>> {
    let mut ids = zkai_d128_gate_value_projection_preprocessed_column_ids();
    ids.extend(zkai_d128_activation_swiglu_preprocessed_column_ids());
    let mut seen = BTreeSet::new();
    for id in &ids {
        if !seen.insert(id.id.clone()) {
            return Err(fused_error(format!(
                "duplicate fused preprocessed column id: {}",
                id.id
            )));
        }
    }
    Ok(ids)
}

fn validate_fused_pcs_config(config: PcsConfig) -> Result<PcsConfig> {
    if !publication_v1_pcs_config_matches(&config) {
        return Err(fused_error("unexpected PCS config for fused proof"));
    }
    Ok(publication_v1_pcs_config())
}

fn statement_commitment(input: &ZkAiD128GateValueActivationFusedInput) -> Result<String> {
    let payload = serde_json::json!({
        "activation_public_instance_commitment": input.activation_public_instance_commitment,
        "activation_row_count": input.activation_row_count,
        "activation_statement_commitment": input.activation_statement_commitment,
        "activation_swiglu_proof_version": input.activation_swiglu_proof_version,
        "ff_dim": input.ff_dim,
        "gate_value_projection_output_commitment": input.gate_value_projection_output_commitment,
        "gate_value_proof_version": input.gate_value_proof_version,
        "gate_value_public_instance_commitment": input.gate_value_public_instance_commitment,
        "gate_value_row_count": input.gate_value_row_count,
        "gate_value_statement_commitment": input.gate_value_statement_commitment,
        "hidden_activation_commitment": input.hidden_activation_commitment,
        "operation": "gate_value_activation_fused",
        "required_backend_version": input.required_backend_version,
        "route_id": input.route_id,
        "target_id": input.target_id,
        "verifier_domain": input.verifier_domain,
        "width": input.width,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, STATEMENT_DOMAIN))
}

fn public_instance_commitment(statement: &str) -> Result<String> {
    let payload = serde_json::json!({
        "operation": "gate_value_activation_fused",
        "route_id": ZKAI_D128_GATE_VALUE_ACTIVATION_FUSED_ROUTE_ID,
        "statement_commitment": statement,
        "width": WIDTH,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(&bytes, PUBLIC_INSTANCE_DOMAIN))
}

fn proof_native_parameter_commitment(statement: &str) -> Result<String> {
    let payload = serde_json::json!({
        "kind": PROOF_NATIVE_PARAMETER_KIND,
        "pcs_profile": "publication_v1",
        "statement_commitment": statement,
    });
    let bytes =
        serde_json::to_vec(&payload).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(blake2b_commitment_bytes(
        &bytes,
        PROOF_NATIVE_PARAMETER_DOMAIN,
    ))
}

fn blake2b_commitment_bytes(bytes: &[u8], domain: &str) -> String {
    let mut hasher = Blake2bVar::new(32).expect("valid blake2b output size");
    hasher.update(domain.as_bytes());
    hasher.update(b"\0");
    hasher.update(bytes);
    let mut output = [0u8; 32];
    hasher
        .finalize_variable(&mut output)
        .expect("blake2b finalization should succeed");
    let hex = output
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    format!("blake2b-256:{hex}")
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(fused_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(fused_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_vec_eq(actual: &[String], expected: &[&str], label: &str) -> Result<()> {
    let expected_vec = expected
        .iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    if actual != expected_vec {
        return Err(fused_error(format!("{label} drift")));
    }
    Ok(())
}

fn fused_error(message: impl Into<String>) -> VmError {
    VmError::UnsupportedProof(format!(
        "d128 gate/value activation fused proof: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn input_fixture() -> ZkAiD128GateValueActivationFusedInput {
        let gate_raw = include_str!(
            "../../docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json"
        );
        let activation_raw = include_str!(
            "../../docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json"
        );
        let gate = zkai_d128_gate_value_projection_input_from_json_str(gate_raw)
            .expect("gate/value input");
        let activation = zkai_d128_activation_swiglu_input_from_json_str(activation_raw)
            .expect("activation input");
        build_zkai_d128_gate_value_activation_fused_input(gate, activation).expect("fused input")
    }

    #[test]
    fn fused_input_validates_handoff_and_commitments() {
        let input = input_fixture();
        assert_eq!(input.gate_value_row_count, GATE_VALUE_ROWS);
        assert_eq!(input.activation_row_count, ACTIVATION_ROWS);
        assert_eq!(
            input.gate_value_projection_output_commitment,
            input
                .activation_input
                .source_gate_value_projection_output_commitment
        );
        validate_fused_input(&input).expect("valid fused input");
    }

    #[test]
    fn fused_preprocessed_columns_are_unique() {
        let ids = fused_preprocessed_column_ids().expect("ids");
        let unique = ids.iter().map(|id| id.id.clone()).collect::<BTreeSet<_>>();
        assert_eq!(ids.len(), unique.len());
    }

    #[test]
    fn fused_air_proof_round_trips() {
        let input = input_fixture();
        let envelope = prove_zkai_d128_gate_value_activation_fused_envelope(&input)
            .expect("fused proof should prove");
        assert!(
            verify_zkai_d128_gate_value_activation_fused_envelope(&envelope)
                .expect("fused proof should verify")
        );
    }

    #[test]
    fn fused_rejects_activation_handoff_drift() {
        let input = input_fixture();
        let mut value = serde_json::to_value(&input).expect("input json");
        value["activation_input"]["source_gate_value_projection_output_commitment"] =
            Value::String(format!("blake2b-256:{}", "33".repeat(32)));
        let raw = serde_json::to_string(&value).expect("mutated input");
        let _error = zkai_d128_gate_value_activation_fused_input_from_json_str(&raw)
            .expect_err("handoff drift should reject");
    }

    #[test]
    fn fused_rejects_required_backend_version_drift() {
        let input = input_fixture();
        let mut value = serde_json::to_value(&input).expect("input json");
        value["required_backend_version"] = Value::String("wrong-backend".to_string());
        let raw = serde_json::to_string(&value).expect("mutated input");
        let error = zkai_d128_gate_value_activation_fused_input_from_json_str(&raw)
            .expect_err("backend version drift should reject");
        assert!(error.to_string().contains("required backend version"));
    }

    #[test]
    fn fused_rejects_target_id_drift() {
        let input = input_fixture();
        let mut value = serde_json::to_value(&input).expect("input json");
        value["target_id"] = Value::String("wrong-target".to_string());
        let raw = serde_json::to_string(&value).expect("mutated input");
        let error = zkai_d128_gate_value_activation_fused_input_from_json_str(&raw)
            .expect_err("target id drift should reject");
        assert!(error.to_string().contains("target id"));
    }

    #[test]
    fn fused_rejects_verifier_domain_drift() {
        let input = input_fixture();
        let mut value = serde_json::to_value(&input).expect("input json");
        value["verifier_domain"] = Value::String("wrong-domain".to_string());
        let raw = serde_json::to_string(&value).expect("mutated input");
        let error = zkai_d128_gate_value_activation_fused_input_from_json_str(&raw)
            .expect_err("verifier domain drift should reject");
        assert!(error.to_string().contains("verifier domain"));
    }

    #[test]
    fn fused_rejects_extra_commitment_vector_entry() {
        let input = input_fixture();
        let mut envelope = prove_zkai_d128_gate_value_activation_fused_envelope(&input)
            .expect("fused proof should prove");
        let mut payload: Value =
            serde_json::from_slice(&envelope.proof).expect("fused proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        commitments.push(commitments[0].clone());
        envelope.proof = serde_json::to_vec(&payload).expect("mutated proof");
        let error = verify_zkai_d128_gate_value_activation_fused_envelope(&envelope)
            .expect_err("extra commitment should reject");
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn fused_rejects_tampered_base_commitment() {
        let input = input_fixture();
        let mut envelope = prove_zkai_d128_gate_value_activation_fused_envelope(&input)
            .expect("fused proof should prove");
        let mut payload: Value =
            serde_json::from_slice(&envelope.proof).expect("fused proof payload");
        payload["stark_proof"]["commitments"][1] =
            Value::Array((0..32).map(|_| Value::from(0)).collect());
        envelope.proof = serde_json::to_vec(&payload).expect("mutated proof");
        let error = verify_zkai_d128_gate_value_activation_fused_envelope(&envelope)
            .expect_err("tampered base commitment should reject");
        assert!(error
            .to_string()
            .contains("base commitment does not match checked fused component rows"));
    }
}
