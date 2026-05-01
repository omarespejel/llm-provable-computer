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
    ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT, ZKAI_D64_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D64_REQUIRED_BACKEND_VERSION, ZKAI_D64_STATEMENT_COMMITMENT, ZKAI_D64_TARGET_ID,
    ZKAI_D64_VERIFIER_DOMAIN, ZKAI_D64_WIDTH,
};
use super::d64_native_rmsnorm_public_row_proof::ZKAI_D64_RMSNORM_PUBLIC_ROW_PROOF_VERSION;

pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_SCHEMA: &str =
    "zkai-d64-rmsnorm-to-projection-bridge-air-proof-input-v1";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D64_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION: &str =
    "stwo-d64-rmsnorm-to-projection-bridge-air-proof-v1";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_VERSION: &str =
    "zkai-d64-rmsnorm-to-projection-bridge-statement-v1";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_SEMANTIC_SCOPE: &str =
    "d64_rmsnorm_output_rows_domain_separated_as_projection_input_rows";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_DECISION: &str =
    "GO_D64_RMSNORM_TO_PROJECTION_INPUT_BRIDGE_AIR_PROOF";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_NEXT_BACKEND_STEP: &str =
    "encode gate/value projection rows that consume projection_input_row_commitment and produce gate_value_projection_output_commitment";
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_MAX_PROOF_BYTES: usize = 1_048_576;
pub const ZKAI_D64_RMSNORM_OUTPUT_ROW_COMMITMENT: &str =
    "blake2b-256:c9ab975e440661ce7796f33b75008d20e7eb26a4c41956d2f723093e4ac373a7";
pub const ZKAI_D64_PROJECTION_INPUT_ROW_COMMITMENT: &str =
    "blake2b-256:3a84feca5eab58736fdf01369fc64d3afc45c97ecdc629e64f0bb2eb2f8de094";

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const D64_BRIDGE_LOG_SIZE: u32 = 6;
const ZKAI_D64_BRIDGE_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D64_BRIDGE_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const RMSNORM_OUTPUT_ROW_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d64-rmsnorm-output-row:v1";
const PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d64-projection-input-row:v1";

const COLUMN_IDS: [&str; 3] = [
    "zkai/d64/rmsnorm-to-projection/index",
    "zkai/d64/rmsnorm-to-projection/rmsnorm_normed_q8",
    "zkai/d64/rmsnorm-to-projection/projection_input_q8",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not full d64 block proof",
    "not gate, value, or down projection proof",
    "not activation, SwiGLU, or residual proof",
    "not binding the full d64 output_activation_commitment",
    "bridge proves only the domain-separated handoff from RMSNorm-local rows to projection-input rows",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "source RMSNorm output row commitment recomputation before proof verification",
    "projection input row commitment recomputation before proof verification",
    "AIR equality between RMSNorm-local rows and projection-input rows",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

#[derive(Debug, Clone)]
struct D64RmsnormToProjectionBridgeEval {
    log_size: u32,
}

impl FrameworkEval for D64RmsnormToProjectionBridgeEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let index = eval.next_trace_mask();
        let rmsnorm_normed_q8 = eval.next_trace_mask();
        let projection_input_q8 = eval.next_trace_mask();

        for (column_id, trace_value) in COLUMN_IDS.iter().zip([
            index,
            rmsnorm_normed_q8.clone(),
            projection_input_q8.clone(),
        ]) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        eval.add_constraint(projection_input_q8 - rmsnorm_normed_q8);
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D64RmsnormToProjectionBridgeRow {
    pub index: usize,
    pub rmsnorm_normed_q8: i64,
    pub projection_input_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD64RmsnormToProjectionBridgeInput {
    pub schema: String,
    pub decision: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub row_count: usize,
    pub source_rmsnorm_public_row_proof_version: String,
    pub source_rmsnorm_output_row_commitment: String,
    pub projection_input_row_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub rows: Vec<D64RmsnormToProjectionBridgeRow>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD64RmsnormToProjectionBridgeEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD64RmsnormToProjectionBridgeInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
struct D64RmsnormToProjectionBridgeProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d64_rmsnorm_to_projection_bridge_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD64RmsnormToProjectionBridgeInput> {
    if raw_json.len() > ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES {
        return Err(bridge_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD64RmsnormToProjectionBridgeInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_bridge_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d64_rmsnorm_to_projection_bridge_envelope(
    input: &ZkAiD64RmsnormToProjectionBridgeInput,
) -> Result<ZkAiD64RmsnormToProjectionBridgeEnvelope> {
    validate_bridge_input(input)?;
    Ok(ZkAiD64RmsnormToProjectionBridgeEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_DECISION.to_string(),
        input: input.clone(),
        proof: prove_bridge_rows(input)?,
    })
}

pub fn verify_zkai_d64_rmsnorm_to_projection_bridge_envelope(
    envelope: &ZkAiD64RmsnormToProjectionBridgeEnvelope,
) -> Result<bool> {
    validate_bridge_envelope(envelope)?;
    verify_bridge_rows(&envelope.input, &envelope.proof)
}

fn validate_bridge_envelope(envelope: &ZkAiD64RmsnormToProjectionBridgeEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(bridge_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(bridge_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_MAX_PROOF_BYTES {
        return Err(bridge_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_MAX_PROOF_BYTES
        )));
    }
    validate_bridge_input(&envelope.input)
}

fn validate_bridge_input(input: &ZkAiD64RmsnormToProjectionBridgeInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_DECISION,
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
    expect_eq(
        &input.source_rmsnorm_public_row_proof_version,
        ZKAI_D64_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source RMSNorm public-row proof version",
    )?;
    expect_eq(
        &input.source_rmsnorm_output_row_commitment,
        ZKAI_D64_RMSNORM_OUTPUT_ROW_COMMITMENT,
        "source RMSNorm output row commitment",
    )?;
    if input.projection_input_row_commitment == ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT {
        return Err(bridge_error(
            "projection input row commitment must not relabel as full output activation commitment",
        ));
    }
    expect_eq(
        &input.projection_input_row_commitment,
        ZKAI_D64_PROJECTION_INPUT_ROW_COMMITMENT,
        "projection input row commitment",
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
        ZKAI_D64_RMSNORM_TO_PROJECTION_BRIDGE_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    if input.rows.len() != ZKAI_D64_WIDTH {
        return Err(bridge_error(format!(
            "row vector length mismatch: got {}, expected {}",
            input.rows.len(),
            ZKAI_D64_WIDTH
        )));
    }
    let mut rmsnorm_values = Vec::with_capacity(input.rows.len());
    let mut projection_values = Vec::with_capacity(input.rows.len());
    for (expected_index, row) in input.rows.iter().enumerate() {
        validate_bridge_row(row, expected_index)?;
        rmsnorm_values.push(row.rmsnorm_normed_q8);
        projection_values.push(row.projection_input_q8);
    }
    expect_eq(
        &sequence_commitment(
            &rmsnorm_values,
            RMSNORM_OUTPUT_ROW_COMMITMENT_DOMAIN,
            ZKAI_D64_WIDTH,
        ),
        &input.source_rmsnorm_output_row_commitment,
        "source RMSNorm output row recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &projection_values,
            PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN,
            ZKAI_D64_WIDTH,
        ),
        &input.projection_input_row_commitment,
        "projection input row recomputed commitment",
    )?;
    Ok(())
}

fn validate_bridge_row(row: &D64RmsnormToProjectionBridgeRow, expected_index: usize) -> Result<()> {
    expect_usize(row.index, expected_index, "row index")?;
    expect_signed_m31(row.rmsnorm_normed_q8, "rmsnorm normed q8")?;
    expect_signed_m31(row.projection_input_q8, "projection input q8")?;
    expect_i64(
        row.projection_input_q8,
        row.rmsnorm_normed_q8,
        "RMSNorm-to-projection bridge equality",
    )
}

fn prove_bridge_rows(input: &ZkAiD64RmsnormToProjectionBridgeInput) -> Result<Vec<u8>> {
    let component = bridge_component();
    let config = bridge_pcs_config();
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
    tree_builder.extend_evals(bridge_trace(input));
    tree_builder.commit(channel);

    // This mirrors the public-row proof shape: the framework component exposes
    // two trace-tree slots, and both deterministic roots are recomputed before
    // verification so a stale or substituted row surface still fails closed.
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bridge_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "d64 RMSNorm-to-projection bridge AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D64RmsnormToProjectionBridgeProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_bridge_rows(input: &ZkAiD64RmsnormToProjectionBridgeInput, proof: &[u8]) -> Result<bool> {
    let payload: D64RmsnormToProjectionBridgeProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_bridge_pcs_config(stark_proof.config)?;
    let component = bridge_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D64_BRIDGE_EXPECTED_TRACE_COMMITMENTS {
        return Err(bridge_error(format!(
            "internal bridge component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D64_BRIDGE_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D64_BRIDGE_EXPECTED_PROOF_COMMITMENTS {
        return Err(bridge_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D64_BRIDGE_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = bridge_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(bridge_error(
            "preprocessed row commitment does not match checked bridge rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(bridge_error(
            "base row commitment does not match checked bridge rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| bridge_error(format!("STARK verification failed: {error}")))
}

fn validate_bridge_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(bridge_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(bridge_pcs_config())
}

fn bridge_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn bridge_commitment_roots(
    input: &ZkAiD64RmsnormToProjectionBridgeInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = bridge_component();
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
    tree_builder.extend_evals(bridge_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bridge_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn bridge_component() -> FrameworkComponent<D64RmsnormToProjectionBridgeEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D64RmsnormToProjectionBridgeEval {
            log_size: D64_BRIDGE_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn bridge_trace(
    input: &ZkAiD64RmsnormToProjectionBridgeInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D64_BRIDGE_LOG_SIZE).circle_domain();
    let rows = &input.rows;
    let columns: Vec<Vec<BaseField>> = vec![
        rows.iter().map(|row| field_usize(row.index)).collect(),
        rows.iter()
            .map(|row| field_i64(row.rmsnorm_normed_q8))
            .collect(),
        rows.iter()
            .map(|row| field_i64(row.projection_input_q8))
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
    BaseField::from(value as u32)
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
        return Err(bridge_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(bridge_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(bridge_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_signed_m31(value: i64, label: &str) -> Result<()> {
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(bridge_error(format!(
            "{label} is outside signed M31 verifier bound: {value}"
        )));
    }
    Ok(())
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
        return Err(bridge_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected_vec:?}"
        )));
    }
    Ok(())
}

fn bridge_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d64 RMSNorm-to-projection bridge proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json"
    );

    fn input() -> ZkAiD64RmsnormToProjectionBridgeInput {
        zkai_d64_rmsnorm_to_projection_bridge_input_from_json_str(INPUT_JSON).expect("bridge input")
    }

    #[test]
    fn bridge_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(input.rows.len(), ZKAI_D64_WIDTH);
        assert_eq!(
            input.source_rmsnorm_output_row_commitment,
            ZKAI_D64_RMSNORM_OUTPUT_ROW_COMMITMENT
        );
        assert_eq!(
            input.projection_input_row_commitment,
            ZKAI_D64_PROJECTION_INPUT_ROW_COMMITMENT
        );
        assert_ne!(
            input.projection_input_row_commitment,
            ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT
        );
        assert_eq!(input.rows[0].rmsnorm_normed_q8, 46);
        assert_eq!(input.rows[0].projection_input_q8, 46);
    }

    #[test]
    fn bridge_air_proof_round_trips() {
        let input = input();
        let envelope =
            prove_zkai_d64_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d64_rmsnorm_to_projection_bridge_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn bridge_pcs_config_uses_shared_publication_v1_profile() {
        let actual = bridge_pcs_config();
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
    fn bridge_rejects_projection_input_relabeling_as_full_output() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["projection_input_row_commitment"] =
            Value::String(ZKAI_D64_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d64_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("must not relabel"));
    }

    #[test]
    fn bridge_rejects_source_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["source_rmsnorm_output_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "77".repeat(32)));
        let error = zkai_d64_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("source RMSNorm output row commitment"));
    }

    #[test]
    fn bridge_rejects_projection_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["projection_input_row_commitment"] =
            Value::String(format!("blake2b-256:{}", "88".repeat(32)));
        let error = zkai_d64_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("projection input row commitment"));
    }

    #[test]
    fn bridge_rejects_row_equality_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][0]["projection_input_q8"] = Value::from(47);
        let error = zkai_d64_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("RMSNorm-to-projection bridge equality"));
    }

    #[test]
    fn bridge_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        envelope.input.rows[0].rmsnorm_normed_q8 += 1;
        let error = verify_zkai_d64_rmsnorm_to_projection_bridge_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("d64 RMSNorm-to-projection bridge proof rejected"));
    }

    #[test]
    fn bridge_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d64_rmsnorm_to_projection_bridge_envelope(&envelope).is_err());
    }

    #[test]
    fn bridge_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_rmsnorm_to_projection_bridge_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn bridge_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope =
            prove_zkai_d64_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d64_rmsnorm_to_projection_bridge_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }
}
