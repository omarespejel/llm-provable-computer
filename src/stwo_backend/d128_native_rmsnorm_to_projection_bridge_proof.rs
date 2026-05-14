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
use stwo::prover::{prove, CommitmentSchemeProver, ComponentProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    EvalAtRow, FrameworkComponent, FrameworkEval, TraceLocationAllocator,
};

use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

use super::d128_native_rmsnorm_public_row_proof::ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION;

pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_SCHEMA: &str =
    "zkai-d128-rmsnorm-to-projection-bridge-air-proof-input-v1";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_DECISION: &str =
    "GO_INPUT_FOR_D128_RMSNORM_TO_PROJECTION_BRIDGE_AIR_PROOF";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION: &str =
    "stwo-d128-rmsnorm-to-projection-bridge-air-proof-v1";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_VERSION: &str =
    "zkai-d128-rmsnorm-to-projection-bridge-statement-v1";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_SEMANTIC_SCOPE: &str =
    "d128_rmsnorm_output_rows_domain_separated_as_projection_input_rows";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_DECISION: &str =
    "GO_D128_RMSNORM_TO_PROJECTION_INPUT_BRIDGE_AIR_PROOF";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_NEXT_BACKEND_STEP: &str =
    "encode d128 gate/value projection rows that consume projection_input_row_commitment and produce gate/value projection output commitments";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_PROOF_BYTES: usize = 1_048_576;
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_OPERATION: &str = "rmsnorm_to_projection_bridge";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_TARGET_ID: &str =
    "rmsnorm-swiglu-residual-d128-v1";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_REQUIRED_BACKEND_VERSION: &str =
    "stwo-rmsnorm-swiglu-residual-d128-v1";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH: usize = 128;
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT: &str =
    "blake2b-256:fe0a9e59560611ed5220fd25b082806977a66a7032f457fce2cd5c3a41856728";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT: &str =
    "blake2b-256:ca94d85cb0ed5e9001cd3def00817060745fa015bd8dda5f08732944f7418383";
pub const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT: &str =
    "blake2b-256:ff31d2b502dac1e7d9f9cca69c4bd31e93e068dab49884e61a300a99389d58c1";
pub const ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT: &str =
    "blake2b-256:d8b6f5e54e874e46624cb9c9987dbcc42db2aa9fc83d4d7230294fbbccb88b87";
pub const ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT: &str =
    "blake2b-256:84fd5765c9ed8d21ced01ace55c5f95b34f16d159864c1ec20d9a0cd4cd67b17";
pub const ZKAI_D128_BRIDGE_FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT: &str =
    "blake2b-256:7e6ae6d301fc60ac2232d807d155785eabe653cf4e91971adda470a04246a572";

const M31_MODULUS: i64 = (1i64 << 31) - 1;
const D128_BRIDGE_LOG_SIZE: u32 = 7;
const ZKAI_D128_BRIDGE_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D128_BRIDGE_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const TARGET_COMMITMENT: &str =
    "blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18";
const SOURCE_RMSNORM_STATEMENT_COMMITMENT: &str =
    "blake2b-256:de944915f2664ac7a893f4ba9a029323f7408eac58bf39170a0935d7832ccbd8";
const SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT: &str =
    "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72";
const PROOF_NATIVE_PARAMETER_KIND: &str =
    "d128-rmsnorm-to-projection-bridge-synthetic-parameters-v1";
const PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:d128-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str = "ptvm:zkai:d128-proof-native-parameter-commitment:v1";
const RMSNORM_OUTPUT_ROW_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d128-rmsnorm-output-row:v1";
const PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d128-projection-input-row:v1";

pub(crate) const ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS: [&str; 3] = [
    "zkai/d128/rmsnorm-to-projection/index",
    "zkai/d128/rmsnorm-to-projection/rmsnorm_normed_q8",
    "zkai/d128/rmsnorm-to-projection/projection_input_q8",
];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not full d128 block proof",
    "not gate, value, or down projection proof",
    "not activation, SwiGLU, or residual proof",
    "not binding the full d128 output_activation_commitment",
    "bridge proves only the domain-separated handoff from RMSNorm-local rows to projection-input rows",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "source d128 RMSNorm evidence validation before bridge construction",
    "source RMSNorm statement commitment binding before bridge verification",
    "source RMSNorm output row commitment recomputation before proof verification",
    "projection input row commitment recomputation before proof verification",
    "statement/public-instance/native-parameter commitments recomputed before proof verification",
    "AIR equality between RMSNorm-local rows and projection-input rows",
    "full output_activation_commitment relabeling rejection",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input",
    "cargo +nightly-2025-07-14 test d128_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone)]
struct D128RmsnormToProjectionBridgeEval {
    log_size: u32,
}

impl FrameworkEval for D128RmsnormToProjectionBridgeEval {
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

        for (column_id, trace_value) in ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS
            .iter()
            .zip([
                index,
                rmsnorm_normed_q8.clone(),
                projection_input_q8.clone(),
            ])
        {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }
        eval.add_constraint(projection_input_q8 - rmsnorm_normed_q8);
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D128RmsnormToProjectionBridgeRow {
    pub index: usize,
    pub rmsnorm_normed_q8: i64,
    pub projection_input_q8: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128RmsnormToProjectionBridgeInput {
    pub schema: String,
    pub decision: String,
    pub operation: String,
    pub target_id: String,
    pub required_backend_version: String,
    pub verifier_domain: String,
    pub width: usize,
    pub row_count: usize,
    pub source_rmsnorm_public_row_proof_version: String,
    pub source_rmsnorm_statement_commitment: String,
    pub source_rmsnorm_public_instance_commitment: String,
    pub source_rmsnorm_output_row_domain: String,
    pub projection_input_row_domain: String,
    pub source_rmsnorm_output_row_commitment: String,
    pub projection_input_row_commitment: String,
    pub forbidden_output_activation_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub statement_commitment: String,
    pub rows: Vec<D128RmsnormToProjectionBridgeRow>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZkAiD128RmsnormToProjectionBridgeEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD128RmsnormToProjectionBridgeInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct D128RmsnormToProjectionBridgeProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128RmsnormToProjectionBridgeInput> {
    if raw_json.len() > ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES {
        return Err(bridge_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD128RmsnormToProjectionBridgeInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_bridge_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(
    input: &ZkAiD128RmsnormToProjectionBridgeInput,
) -> Result<ZkAiD128RmsnormToProjectionBridgeEnvelope> {
    validate_bridge_input(input)?;
    Ok(ZkAiD128RmsnormToProjectionBridgeEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_DECISION.to_string(),
        input: input.clone(),
        proof: prove_bridge_rows(input)?,
    })
}

pub fn verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(
    envelope: &ZkAiD128RmsnormToProjectionBridgeEnvelope,
) -> Result<bool> {
    validate_bridge_envelope(envelope)?;
    verify_bridge_rows(&envelope.input, &envelope.proof)
}

fn validate_bridge_envelope(envelope: &ZkAiD128RmsnormToProjectionBridgeEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(bridge_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(bridge_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_PROOF_BYTES {
        return Err(bridge_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_MAX_PROOF_BYTES
        )));
    }
    validate_bridge_input(&envelope.input)
}

fn validate_bridge_input(input: &ZkAiD128RmsnormToProjectionBridgeInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(
        &input.operation,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_OPERATION,
        "operation",
    )?;
    expect_eq(
        &input.target_id,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_TARGET_ID,
        "target id",
    )?;
    expect_eq(
        &input.required_backend_version,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_usize(
        input.width,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH,
        "width",
    )?;
    expect_usize(
        input.row_count,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH,
        "row count",
    )?;
    expect_eq(
        &input.source_rmsnorm_public_row_proof_version,
        ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        "source RMSNorm public-row proof version",
    )?;
    expect_eq(
        &input.source_rmsnorm_statement_commitment,
        SOURCE_RMSNORM_STATEMENT_COMMITMENT,
        "source RMSNorm statement commitment",
    )?;
    expect_eq(
        &input.source_rmsnorm_public_instance_commitment,
        SOURCE_RMSNORM_PUBLIC_INSTANCE_COMMITMENT,
        "source RMSNorm public-instance commitment",
    )?;
    expect_eq(
        &input.source_rmsnorm_output_row_domain,
        RMSNORM_OUTPUT_ROW_COMMITMENT_DOMAIN,
        "source RMSNorm output row domain",
    )?;
    expect_eq(
        &input.projection_input_row_domain,
        PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN,
        "projection input row domain",
    )?;
    expect_eq(
        &input.source_rmsnorm_output_row_commitment,
        ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT,
        "source RMSNorm output row commitment",
    )?;
    expect_eq(
        &input.forbidden_output_activation_commitment,
        ZKAI_D128_BRIDGE_FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT,
        "forbidden output activation commitment",
    )?;
    if input.projection_input_row_commitment == input.forbidden_output_activation_commitment {
        return Err(bridge_error(
            "projection input row commitment must not relabel as full output activation commitment",
        ));
    }
    expect_eq(
        &input.projection_input_row_commitment,
        ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT,
        "projection input row commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
        "public instance commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT,
        "proof-native parameter commitment",
    )?;
    expect_eq(
        &input.statement_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
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
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    expect_str_set_eq(
        input.validation_commands.iter().map(String::as_str),
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
    )?;
    if input.rows.len() != ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH {
        return Err(bridge_error(format!(
            "row vector length mismatch: got {}, expected {}",
            input.rows.len(),
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH
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
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH,
        ),
        &input.source_rmsnorm_output_row_commitment,
        "source RMSNorm output row recomputed commitment",
    )?;
    expect_eq(
        &sequence_commitment(
            &projection_values,
            PROJECTION_INPUT_ROW_COMMITMENT_DOMAIN,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH,
        ),
        &input.projection_input_row_commitment,
        "projection input row recomputed commitment",
    )?;
    let statement = statement_commitment(input);
    expect_eq(
        &input.statement_commitment,
        &statement,
        "statement commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        &public_instance_commitment(&statement, input.width),
        "public instance recomputed commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        &proof_native_parameter_commitment(&statement),
        "proof-native parameter recomputed commitment",
    )?;
    Ok(())
}

fn validate_bridge_row(
    row: &D128RmsnormToProjectionBridgeRow,
    expected_index: usize,
) -> Result<()> {
    expect_usize(row.index, expected_index, "row index")?;
    expect_signed_m31(row.rmsnorm_normed_q8, "rmsnorm normed q8")?;
    expect_signed_m31(row.projection_input_q8, "projection input q8")?;
    expect_i64(
        row.projection_input_q8,
        row.rmsnorm_normed_q8,
        "RMSNorm-to-projection bridge equality",
    )
}

fn prove_bridge_rows(input: &ZkAiD128RmsnormToProjectionBridgeInput) -> Result<Vec<u8>> {
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
                    "d128 RMSNorm-to-projection bridge AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128RmsnormToProjectionBridgeProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_bridge_rows(
    input: &ZkAiD128RmsnormToProjectionBridgeInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D128RmsnormToProjectionBridgeProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_bridge_pcs_config(stark_proof.config)?;
    let component = bridge_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D128_BRIDGE_EXPECTED_TRACE_COMMITMENTS {
        return Err(bridge_error(format!(
            "internal bridge component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D128_BRIDGE_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D128_BRIDGE_EXPECTED_PROOF_COMMITMENTS {
        return Err(bridge_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D128_BRIDGE_EXPECTED_PROOF_COMMITMENTS
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
    input: &ZkAiD128RmsnormToProjectionBridgeInput,
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

fn bridge_component() -> FrameworkComponent<D128RmsnormToProjectionBridgeEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        D128RmsnormToProjectionBridgeEval {
            log_size: D128_BRIDGE_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

pub(crate) fn zkai_d128_rmsnorm_to_projection_bridge_component_with_allocator(
    allocator: &mut TraceLocationAllocator,
) -> impl ComponentProver<SimdBackend> {
    FrameworkComponent::new(
        allocator,
        D128RmsnormToProjectionBridgeEval {
            log_size: D128_BRIDGE_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

pub(crate) fn zkai_d128_rmsnorm_to_projection_bridge_preprocessed_column_ids(
) -> Vec<PreProcessedColumnId> {
    preprocessed_column_ids()
}

pub(crate) fn zkai_d128_rmsnorm_to_projection_bridge_trace(
    input: &ZkAiD128RmsnormToProjectionBridgeInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    bridge_trace(input)
}

fn bridge_trace(
    input: &ZkAiD128RmsnormToProjectionBridgeInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(D128_BRIDGE_LOG_SIZE).circle_domain();
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
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_COLUMN_IDS
        .into_iter()
        .map(preprocessed_column_id)
        .collect()
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

fn statement_commitment(input: &ZkAiD128RmsnormToProjectionBridgeInput) -> String {
    let payload = format!(
        "{{\"forbidden_output_activation_commitment\":\"{}\",\"operation\":\"{}\",\"projection_input_row_commitment\":\"{}\",\"projection_input_row_domain\":\"{}\",\"required_backend_version\":\"{}\",\"row_count\":{},\"source_rmsnorm_output_row_commitment\":\"{}\",\"source_rmsnorm_output_row_domain\":\"{}\",\"source_rmsnorm_public_instance_commitment\":\"{}\",\"source_rmsnorm_public_row_proof_version\":\"{}\",\"source_rmsnorm_statement_commitment\":\"{}\",\"target_commitment\":\"{}\",\"target_id\":\"{}\",\"verifier_domain\":\"{}\",\"width\":{}}}",
        input.forbidden_output_activation_commitment,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_OPERATION,
        input.projection_input_row_commitment,
        input.projection_input_row_domain,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_REQUIRED_BACKEND_VERSION,
        input.row_count,
        input.source_rmsnorm_output_row_commitment,
        input.source_rmsnorm_output_row_domain,
        input.source_rmsnorm_public_instance_commitment,
        ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
        input.source_rmsnorm_statement_commitment,
        TARGET_COMMITMENT,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_TARGET_ID,
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_VERIFIER_DOMAIN,
        input.width
    );
    blake2b_commitment_bytes(
        payload.as_bytes(),
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_VERIFIER_DOMAIN,
    )
}

fn public_instance_commitment(statement_commitment: &str, width: usize) -> String {
    let payload = format!(
        "{{\"operation\":\"{}\",\"target_commitment\":\"{}\",\"width\":{}}}",
        ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_OPERATION, statement_commitment, width
    );
    blake2b_commitment_bytes(payload.as_bytes(), PUBLIC_INSTANCE_DOMAIN)
}

fn proof_native_parameter_commitment(statement_commitment: &str) -> String {
    let payload = format!(
        "{{\"kind\":\"{}\",\"target_commitment\":\"{}\"}}",
        PROOF_NATIVE_PARAMETER_KIND, statement_commitment
    );
    blake2b_commitment_bytes(payload.as_bytes(), PROOF_NATIVE_PARAMETER_DOMAIN)
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
        "d128 RMSNorm-to-projection bridge proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json"
    );

    fn input() -> ZkAiD128RmsnormToProjectionBridgeInput {
        zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(INPUT_JSON)
            .expect("bridge input")
    }

    #[test]
    fn bridge_input_validates_checked_commitments_and_rows() {
        let input = input();
        assert_eq!(
            input.rows.len(),
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_WIDTH
        );
        assert_eq!(
            input.source_rmsnorm_output_row_commitment,
            ZKAI_D128_RMSNORM_OUTPUT_ROW_COMMITMENT
        );
        assert_eq!(
            input.projection_input_row_commitment,
            ZKAI_D128_PROJECTION_INPUT_ROW_COMMITMENT
        );
        assert_ne!(
            input.projection_input_row_commitment,
            ZKAI_D128_BRIDGE_FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT
        );
        assert_eq!(
            input.statement_commitment,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT
        );
        assert_eq!(
            input.public_instance_commitment,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT
        );
        assert_eq!(
            input.proof_native_parameter_commitment,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT
        );
        assert_eq!(input.rows[0].rmsnorm_normed_q8, -387);
        assert_eq!(input.rows[0].projection_input_q8, -387);
    }

    #[test]
    fn bridge_air_proof_round_trips() {
        let input = input();
        let envelope =
            prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope).expect("verify"));
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
            Value::String(ZKAI_D128_BRIDGE_FORBIDDEN_OUTPUT_ACTIVATION_COMMITMENT.to_string());
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
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
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
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
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("projection input row commitment"));
    }

    #[test]
    fn bridge_rejects_source_statement_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["source_rmsnorm_statement_commitment"] =
            Value::String(format!("blake2b-256:{}", "99".repeat(32)));
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("source RMSNorm statement commitment"));
    }

    #[test]
    fn bridge_rejects_statement_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["statement_commitment"] = Value::String(format!("blake2b-256:{}", "aa".repeat(32)));
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("statement commitment"));
    }

    #[test]
    fn bridge_rejects_public_instance_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["public_instance_commitment"] =
            Value::String(format!("blake2b-256:{}", "bb".repeat(32)));
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("public instance commitment"));
    }

    #[test]
    fn bridge_rejects_proof_native_parameter_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["proof_native_parameter_commitment"] =
            Value::String(format!("blake2b-256:{}", "cc".repeat(32)));
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("proof-native parameter commitment"));
    }

    #[test]
    fn bridge_rejects_row_equality_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["rows"][0]["projection_input_q8"] = Value::from(47);
        let error = zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("RMSNorm-to-projection bridge equality"));
    }

    #[test]
    fn bridge_rejects_unknown_input_fields() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["unexpected"] = Value::Bool(true);
        assert!(zkai_d128_rmsnorm_to_projection_bridge_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .is_err());
    }

    #[test]
    fn bridge_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        envelope.input.rows[0].rmsnorm_normed_q8 += 1;
        let error = verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("d128 RMSNorm-to-projection bridge proof rejected"));
    }

    #[test]
    fn bridge_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope).is_err());
    }

    #[test]
    fn bridge_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        let extra_commitment = commitments[0].clone();
        commitments.push(extra_commitment);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn bridge_rejects_unknown_proof_payload_fields() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        payload["unexpected"] = Value::Bool(true);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        assert!(verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope).is_err());
    }

    #[test]
    fn bridge_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_rmsnorm_to_projection_bridge_envelope(&input).expect("bridge proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d128_rmsnorm_to_projection_bridge_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }
}
