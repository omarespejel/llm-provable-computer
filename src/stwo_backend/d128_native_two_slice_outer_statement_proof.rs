use ark_ff::Zero;
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
#[cfg(test)]
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
use stwo_constraint_framework::{
    EvalAtRow, FrameworkComponent, FrameworkEval, TraceLocationAllocator,
};

use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

use super::d128_native_rmsnorm_public_row_proof::{
    ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION, ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
};
use super::d128_native_rmsnorm_to_projection_bridge_proof::{
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
};

pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_INPUT_SCHEMA: &str =
    "zkai-native-d128-two-slice-outer-statement-air-proof-input-v1";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_INPUT_DECISION: &str =
    "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_INPUT";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_PROOF_VERSION: &str =
    "stwo-d128-two-slice-outer-statement-air-proof-v1";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_STATEMENT_VERSION: &str =
    "zkai-d128-two-slice-outer-statement-v1";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SEMANTIC_SCOPE: &str =
    "host_verified_two_slice_inner_stwo_results_bound_by_native_outer_statement_air";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_DECISION: &str =
    "NARROW_GO_HOST_VERIFIED_D128_TWO_SLICE_OUTER_STATEMENT_AIR_PROOF";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_OPERATION: &str =
    "d128_two_slice_outer_statement_binding";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_TARGET_ID: &str = "rmsnorm-swiglu-residual-d128-v1";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION: &str =
    "stwo-rmsnorm-swiglu-residual-d128-v1";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:d128-rmsnorm-swiglu-statement-target:v1";
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_WIDTH: usize = 128;
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SELECTED_ROWS: usize = 256;
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SLICE_COUNT: usize = 2;
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_PROOF_BYTES: usize = 1_048_576;
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_ENVELOPE_JSON_BYTES: usize = 2_097_152;
pub const ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_NEXT_BACKEND_STEP: &str =
    "replace host-verified slice-result binding with native Stwo verifier-execution constraints for the selected inner slice proofs";

pub const ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT: &str =
    "blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6";
pub const ZKAI_D128_TWO_SLICE_ACCUMULATOR_COMMITMENT: &str =
    "blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d";
pub const ZKAI_D128_TWO_SLICE_VERIFIER_HANDLE_COMMITMENT: &str =
    "blake2b-256:8dd18b7b5b8d0a5399535f0a02f9a1fe4128211bad8f3e69bb44c92cdf07a131";
pub const ZKAI_D128_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT: &str =
    "blake2b-256:2dfa2ceffd67f95059b3d6cd639a82577f2bbd7be43e99c25814feb703a8fd72";
pub const ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_NATIVE_PARAMETER_COMMITMENT: &str =
    "blake2b-256:8d8bded756f3290980eaab322ba986b02c5584bc8348c2ffcfa4e4860a80944c";
pub const ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_FILE_SHA256: &str =
    "d80f9f16e5f8aef3a8ec49271bb0616483cb6906731539aea2f73ba4678123ec";
pub const ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_PAYLOAD_SHA256: &str =
    "19688310ba6001e16b80c15532f74b59097222a1aa9be132ea66b11a116ded05";
pub const ZKAI_D128_RMSNORM_PROJECTION_BRIDGE_SOURCE_FILE_SHA256: &str =
    "11f93a3ecee19c40ff14d154e054dab56a1b9c1a2dbb1d609a918e201e6fd849";
pub const ZKAI_D128_RMSNORM_PROJECTION_BRIDGE_SOURCE_PAYLOAD_SHA256: &str =
    "e6e46f2e35df3177790c7dbdc5c519f4a7d62e8ed6cba0501ffac94db73975f3";

const D128_OUTER_LOG_SIZE: u32 = 1;
const DIGEST_LIMBS: usize = 16;
const DIGEST_COLUMN_GROUPS: [&str; 10] = [
    "two_slice_target_commitment",
    "accumulator_commitment",
    "verifier_handle_commitment",
    "slice_statement_commitment",
    "slice_public_instance_commitment",
    "slice_proof_native_parameter_commitment",
    "source_file_sha256",
    "source_payload_sha256",
    "proof_backend_version_label",
    "verifier_domain_label",
];
const ZKAI_D128_TWO_SLICE_OUTER_EXPECTED_TRACE_COMMITMENTS: usize = 2;
const ZKAI_D128_TWO_SLICE_OUTER_EXPECTED_PROOF_COMMITMENTS: usize = 3;
const PROOF_NATIVE_PARAMETER_KIND: &str = "d128-two-slice-outer-statement-parameters-v1";
const PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:d128-two-slice-outer-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:d128-two-slice-outer-proof-native-parameter:v1";
const LABEL_COMMITMENT_DOMAIN: &str = "ptvm:zkai:d128-two-slice-outer-label:v1";

const EXPECTED_SELECTED_SLICE_IDS: [&str; 2] = ["rmsnorm_public_rows", "rmsnorm_projection_bridge"];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not native verifier execution of the selected inner Stwo proofs",
    "not recursion or proof-carrying data",
    "not a native d128 transformer-block proof",
    "not a NANOZK proof-size win",
    "not a matched external zkML benchmark",
    "not full transformer inference",
    "not production-ready zkML",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "selected slice order checked before proof verification",
    "selected row count checked before proof verification",
    "two-slice target commitment bound into every outer statement row",
    "accumulator commitment bound into every outer statement row",
    "verifier-handle commitment bound into every outer statement row",
    "selected slice statement commitments bound as digest limbs",
    "selected source evidence hashes bound as digest limbs",
    "proof backend version labels bound as digest limbs",
    "verifier-domain label bound as digest limbs",
    "fixed PCS verifier profile before commitment-root recomputation",
    "bounded proof bytes before JSON deserialization",
    "commitment-vector length check before commitment indexing",
];

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "python3 scripts/zkai_native_d128_two_slice_outer_statement_input.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv",
    "cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- prove docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- verify docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 test d128_native_two_slice_outer_statement_proof --lib --features stwo-backend",
    "python3 scripts/zkai_native_d128_two_slice_outer_statement_gate.py --write-json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv",
    "git diff --check",
    "just gate-fast",
];

#[derive(Debug, Clone)]
struct D128TwoSliceOuterStatementEval {
    log_size: u32,
}

impl FrameworkEval for D128TwoSliceOuterStatementEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let index = eval.next_trace_mask();
        let slice_tag = eval.next_trace_mask();
        let row_count = eval.next_trace_mask();
        let verified = eval.next_trace_mask();
        let one = E::F::from(BaseField::from(1u32));
        eval.add_constraint(index.clone() * (index.clone() - one.clone()));
        eval.add_constraint(slice_tag - index - one.clone());
        eval.add_constraint(row_count - E::F::from(BaseField::from(128u32)));
        eval.add_constraint(verified - one);

        // Digest limbs are verifier-bound by the checked base-trace root.
        // The AIR still registers them as trace columns so the proof object
        // commits to the exact row surface that the host verifier recomputes.
        for _group in DIGEST_COLUMN_GROUPS {
            for _limb_index in 0..DIGEST_LIMBS {
                let _ = eval.next_trace_mask();
            }
        }
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct D128TwoSliceOuterStatementRow {
    pub index: usize,
    pub slice_id: String,
    pub slice_tag: u32,
    pub row_count: usize,
    pub verified: bool,
    pub proof_backend_version: String,
    pub verifier_domain: String,
    pub required_backend_version: String,
    pub statement_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub source_file_sha256: String,
    pub source_payload_sha256: String,
}

#[derive(Serialize)]
struct RowStatementPayload<'a> {
    index: usize,
    proof_backend_version: &'a str,
    proof_native_parameter_commitment: &'a str,
    public_instance_commitment: &'a str,
    required_backend_version: &'a str,
    row_count: usize,
    slice_id: &'a str,
    slice_tag: u32,
    source_file_sha256: &'a str,
    source_payload_sha256: &'a str,
    statement_commitment: &'a str,
    verified: bool,
    verifier_domain: &'a str,
}

#[derive(Serialize)]
struct StatementPayload<'a> {
    accumulator_commitment: &'a str,
    accumulator_verifier_handle_commitment: &'a str,
    operation: &'a str,
    required_backend_version: &'a str,
    rows: Vec<RowStatementPayload<'a>>,
    selected_checked_rows: usize,
    selected_slice_count: usize,
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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128TwoSliceOuterStatementInput {
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
    pub accumulator_verifier_handle_commitment: String,
    pub statement_commitment: String,
    pub public_instance_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub rows: Vec<D128TwoSliceOuterStatementRow>,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiD128TwoSliceOuterStatementEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiD128TwoSliceOuterStatementInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct D128TwoSliceOuterStatementProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_d128_two_slice_outer_statement_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiD128TwoSliceOuterStatementInput> {
    if raw_json.len() > ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_JSON_BYTES {
        return Err(outer_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_JSON_BYTES
        )));
    }
    let input: ZkAiD128TwoSliceOuterStatementInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_outer_input(&input)?;
    Ok(input)
}

pub fn zkai_d128_two_slice_outer_statement_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiD128TwoSliceOuterStatementEnvelope> {
    if raw_json.len() > ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_ENVELOPE_JSON_BYTES {
        return Err(outer_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiD128TwoSliceOuterStatementEnvelope = serde_json::from_slice(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_outer_envelope(&envelope)?;
    Ok(envelope)
}

pub fn prove_zkai_d128_two_slice_outer_statement_envelope(
    input: &ZkAiD128TwoSliceOuterStatementInput,
) -> Result<ZkAiD128TwoSliceOuterStatementEnvelope> {
    validate_outer_input(input)?;
    Ok(ZkAiD128TwoSliceOuterStatementEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_PROOF_VERSION.to_string(),
        statement_version: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_DECISION.to_string(),
        input: input.clone(),
        proof: prove_outer_statement_rows(input)?,
    })
}

pub fn verify_zkai_d128_two_slice_outer_statement_envelope(
    envelope: &ZkAiD128TwoSliceOuterStatementEnvelope,
) -> Result<bool> {
    validate_outer_envelope(envelope)?;
    verify_outer_statement_rows(&envelope.input, &envelope.proof)
}

fn validate_outer_envelope(envelope: &ZkAiD128TwoSliceOuterStatementEnvelope) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(outer_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_PROOF_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(outer_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_PROOF_BYTES {
        return Err(outer_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_MAX_PROOF_BYTES
        )));
    }
    validate_outer_input(&envelope.input)
}

fn validate_outer_input(input: &ZkAiD128TwoSliceOuterStatementInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_INPUT_DECISION,
        "input decision",
    )?;
    expect_eq(
        &input.operation,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_OPERATION,
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
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_WIDTH,
        "width",
    )?;
    expect_usize(
        input.selected_slice_count,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SLICE_COUNT,
        "selected slice count",
    )?;
    expect_usize(
        input.selected_checked_rows,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SELECTED_ROWS,
        "selected checked rows",
    )?;
    let expected_ids = EXPECTED_SELECTED_SLICE_IDS
        .iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    if input.selected_slice_ids != expected_ids {
        return Err(outer_error(format!(
            "selected slice ids mismatch: got {:?}, expected {:?}",
            input.selected_slice_ids, expected_ids
        )));
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
        &input.accumulator_verifier_handle_commitment,
        ZKAI_D128_TWO_SLICE_VERIFIER_HANDLE_COMMITMENT,
        "accumulator verifier handle commitment",
    )?;
    expect_str_list_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non claims")?;
    expect_str_list_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_eq(
        &input.next_backend_step,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    expect_str_list_eq(
        &input.validation_commands,
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
    )?;
    if input.rows.len() != ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SLICE_COUNT {
        return Err(outer_error(format!(
            "outer row vector length mismatch: got {}, expected {}",
            input.rows.len(),
            ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SLICE_COUNT
        )));
    }
    for (expected_index, row) in input.rows.iter().enumerate() {
        validate_outer_row(row, expected_index)?;
    }
    let statement = statement_commitment(input);
    expect_eq(
        &input.statement_commitment,
        &statement,
        "statement commitment",
    )?;
    expect_eq(
        &input.public_instance_commitment,
        &public_instance_commitment(&statement),
        "public instance commitment",
    )?;
    expect_eq(
        &input.proof_native_parameter_commitment,
        &proof_native_parameter_commitment(&statement),
        "proof-native parameter commitment",
    )?;
    Ok(())
}

fn validate_outer_row(row: &D128TwoSliceOuterStatementRow, expected_index: usize) -> Result<()> {
    expect_usize(row.index, expected_index, "outer row index")?;
    expect_eq(
        &row.verifier_domain,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN,
        "row verifier domain",
    )?;
    expect_eq(
        &row.required_backend_version,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION,
        "row required backend version",
    )?;
    expect_usize(
        row.row_count,
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_WIDTH,
        "row count",
    )?;
    if !row.verified {
        return Err(outer_error("row verified flag is false"));
    }
    match expected_index {
        0 => validate_expected_row(
            row,
            "rmsnorm_public_rows",
            1,
            ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION,
            ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT,
            ZKAI_D128_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT,
            ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_NATIVE_PARAMETER_COMMITMENT,
            ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_FILE_SHA256,
            ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_PAYLOAD_SHA256,
        ),
        1 => validate_expected_row(
            row,
            "rmsnorm_projection_bridge",
            2,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT,
            ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT,
            ZKAI_D128_RMSNORM_PROJECTION_BRIDGE_SOURCE_FILE_SHA256,
            ZKAI_D128_RMSNORM_PROJECTION_BRIDGE_SOURCE_PAYLOAD_SHA256,
        ),
        _ => Err(outer_error("unexpected outer row index")),
    }
}

fn validate_expected_row(
    row: &D128TwoSliceOuterStatementRow,
    slice_id: &str,
    slice_tag: u32,
    proof_backend_version: &str,
    statement_commitment: &str,
    public_instance_commitment: &str,
    proof_native_parameter_commitment: &str,
    source_file_sha256: &str,
    source_payload_sha256: &str,
) -> Result<()> {
    expect_eq(&row.slice_id, slice_id, "slice id")?;
    if row.slice_tag != slice_tag {
        return Err(outer_error(format!(
            "slice tag mismatch: got {}, expected {}",
            row.slice_tag, slice_tag
        )));
    }
    expect_eq(
        &row.proof_backend_version,
        proof_backend_version,
        "proof backend version",
    )?;
    expect_eq(
        &row.statement_commitment,
        statement_commitment,
        "slice statement commitment",
    )?;
    expect_eq(
        &row.public_instance_commitment,
        public_instance_commitment,
        "slice public instance commitment",
    )?;
    expect_eq(
        &row.proof_native_parameter_commitment,
        proof_native_parameter_commitment,
        "slice proof-native parameter commitment",
    )?;
    expect_sha256(
        &row.source_file_sha256,
        source_file_sha256,
        "source file sha256",
    )?;
    expect_sha256(
        &row.source_payload_sha256,
        source_payload_sha256,
        "source payload sha256",
    )
}

fn prove_outer_statement_rows(input: &ZkAiD128TwoSliceOuterStatementInput) -> Result<Vec<u8>> {
    let component = outer_component();
    let config = outer_pcs_config();
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

    let tree_builder = commitment_scheme.tree_builder();
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(outer_statement_trace(input)?);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                outer_error(format!(
                    "d128 two-slice outer statement AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&D128TwoSliceOuterStatementProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_outer_statement_rows(
    input: &ZkAiD128TwoSliceOuterStatementInput,
    proof: &[u8],
) -> Result<bool> {
    let payload: D128TwoSliceOuterStatementProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_outer_pcs_config(stark_proof.config)?;
    let component = outer_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != ZKAI_D128_TWO_SLICE_OUTER_EXPECTED_TRACE_COMMITMENTS {
        return Err(outer_error(format!(
            "internal outer component commitment count drift: got {}, expected {}",
            sizes.len(),
            ZKAI_D128_TWO_SLICE_OUTER_EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != ZKAI_D128_TWO_SLICE_OUTER_EXPECTED_PROOF_COMMITMENTS {
        return Err(outer_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            ZKAI_D128_TWO_SLICE_OUTER_EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = outer_commitment_roots(input, config)?;
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(outer_error(
            "preprocessed commitment does not match empty outer-statement preprocessed trace",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(outer_error(
            "base row commitment does not match checked outer rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| outer_error(format!("STARK verification failed: {error}")))
}

fn validate_outer_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(outer_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(outer_pcs_config())
}

fn outer_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn outer_commitment_roots(
    input: &ZkAiD128TwoSliceOuterStatementInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let component = outer_component();
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

    let tree_builder = commitment_scheme.tree_builder();
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(outer_statement_trace(input)?);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn outer_component() -> FrameworkComponent<D128TwoSliceOuterStatementEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        D128TwoSliceOuterStatementEval {
            log_size: D128_OUTER_LOG_SIZE,
        },
        SecureField::zero(),
    )
}

fn outer_statement_trace(
    input: &ZkAiD128TwoSliceOuterStatementInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let domain = CanonicCoset::new(D128_OUTER_LOG_SIZE).circle_domain();
    let mut columns: Vec<Vec<BaseField>> = Vec::new();
    columns.push(
        input
            .rows
            .iter()
            .map(|row| field_usize(row.index))
            .collect(),
    );
    columns.push(
        input
            .rows
            .iter()
            .map(|row| BaseField::from(row.slice_tag))
            .collect(),
    );
    columns.push(
        input
            .rows
            .iter()
            .map(|row| field_usize(row.row_count))
            .collect(),
    );
    columns.push(
        input
            .rows
            .iter()
            .map(|row| BaseField::from(u32::from(row.verified)))
            .collect(),
    );
    for row_digest_group in digest_group_columns(input)? {
        columns.extend(row_digest_group);
    }
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

fn digest_group_columns(
    input: &ZkAiD128TwoSliceOuterStatementInput,
) -> Result<Vec<Vec<Vec<BaseField>>>> {
    DIGEST_COLUMN_GROUPS
        .iter()
        .map(|group| {
            (0..DIGEST_LIMBS)
                .map(|limb_index| {
                    let column = input
                        .rows
                        .iter()
                        .map(|row| {
                            row_digest_limbs(input, row, group)
                                .map(|limbs| BaseField::from(limbs[limb_index] as u32))
                        })
                        .collect::<Result<Vec<_>>>()?;
                    Ok(column)
                })
                .collect::<Result<Vec<_>>>()
        })
        .collect()
}

fn row_digest_limbs(
    input: &ZkAiD128TwoSliceOuterStatementInput,
    row: &D128TwoSliceOuterStatementRow,
    group: &str,
) -> Result<Vec<u16>> {
    match group {
        "two_slice_target_commitment" => digest_limbs(&input.two_slice_target_commitment),
        "accumulator_commitment" => digest_limbs(&input.accumulator_commitment),
        "verifier_handle_commitment" => digest_limbs(&input.accumulator_verifier_handle_commitment),
        "slice_statement_commitment" => digest_limbs(&row.statement_commitment),
        "slice_public_instance_commitment" => digest_limbs(&row.public_instance_commitment),
        "slice_proof_native_parameter_commitment" => {
            digest_limbs(&row.proof_native_parameter_commitment)
        }
        "source_file_sha256" => digest_limbs(&row.source_file_sha256),
        "source_payload_sha256" => digest_limbs(&row.source_payload_sha256),
        "proof_backend_version_label" => label_limbs(&row.proof_backend_version),
        "verifier_domain_label" => label_limbs(&row.verifier_domain),
        _ => unreachable!("unknown digest group"),
    }
}

fn field_usize(value: usize) -> BaseField {
    let value = u32::try_from(value).expect("outer statement field value exceeds u32 range");
    BaseField::from(value)
}

fn digest_limbs(value: &str) -> Result<Vec<u16>> {
    let hex = value.strip_prefix("blake2b-256:").unwrap_or(value);
    if hex.len() != 64 {
        return Err(outer_error(format!(
            "digest limb input must be 32 bytes, got {} hex chars",
            hex.len()
        )));
    }
    if !hex.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(outer_error("digest limb input contains non-hex bytes"));
    }
    (0..DIGEST_LIMBS)
        .map(|index| {
            u16::from_str_radix(&hex[index * 4..index * 4 + 4], 16)
                .map_err(|error| outer_error(format!("digest limb parse failed: {error}")))
        })
        .collect()
}

fn label_limbs(value: &str) -> Result<Vec<u16>> {
    digest_limbs(&blake2b_commitment_bytes(
        value.as_bytes(),
        LABEL_COMMITMENT_DOMAIN,
    ))
}

fn statement_commitment(input: &ZkAiD128TwoSliceOuterStatementInput) -> String {
    let payload = StatementPayload {
        accumulator_commitment: &input.accumulator_commitment,
        accumulator_verifier_handle_commitment: &input.accumulator_verifier_handle_commitment,
        operation: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_OPERATION,
        required_backend_version: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION,
        rows: input.rows.iter().map(row_statement_payload).collect(),
        selected_checked_rows: input.selected_checked_rows,
        selected_slice_count: input.selected_slice_count,
        target_id: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_TARGET_ID,
        two_slice_target_commitment: &input.two_slice_target_commitment,
        verifier_domain: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN,
        width: input.width,
    };
    let payload = serde_json::to_string(&payload).expect("statement payload serialization");
    blake2b_commitment_bytes(
        payload.as_bytes(),
        ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN,
    )
}

fn row_statement_payload(row: &D128TwoSliceOuterStatementRow) -> RowStatementPayload<'_> {
    RowStatementPayload {
        index: row.index,
        proof_backend_version: &row.proof_backend_version,
        proof_native_parameter_commitment: &row.proof_native_parameter_commitment,
        public_instance_commitment: &row.public_instance_commitment,
        required_backend_version: &row.required_backend_version,
        row_count: row.row_count,
        slice_id: &row.slice_id,
        slice_tag: row.slice_tag,
        source_file_sha256: &row.source_file_sha256,
        source_payload_sha256: &row.source_payload_sha256,
        statement_commitment: &row.statement_commitment,
        verified: row.verified,
        verifier_domain: &row.verifier_domain,
    }
}

fn public_instance_commitment(statement_commitment: &str) -> String {
    let payload = PublicInstancePayload {
        operation: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_OPERATION,
        selected_checked_rows: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SELECTED_ROWS,
        statement_commitment,
        two_slice_target_commitment: ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT,
    };
    let payload = serde_json::to_string(&payload).expect("public instance payload serialization");
    blake2b_commitment_bytes(payload.as_bytes(), PUBLIC_INSTANCE_DOMAIN)
}

fn proof_native_parameter_commitment(statement_commitment: &str) -> String {
    let payload = ProofNativeParameterPayload {
        kind: PROOF_NATIVE_PARAMETER_KIND,
        statement_commitment,
    };
    let payload =
        serde_json::to_string(&payload).expect("proof-native parameter payload serialization");
    blake2b_commitment_bytes(payload.as_bytes(), PROOF_NATIVE_PARAMETER_DOMAIN)
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(outer_error(format!(
            "{label} mismatch: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(outer_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_sha256(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual.len() != 64 || !actual.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(outer_error(format!("{label} is not a sha256 hex digest")));
    }
    expect_eq(actual, expected, label)
}

fn expect_str_list_eq(actual: &[String], expected: &[&str], label: &str) -> Result<()> {
    let actual_vec = actual.iter().map(String::as_str).collect::<Vec<_>>();
    if actual_vec.as_slice() != expected {
        return Err(outer_error(format!(
            "{label} mismatch: got {actual_vec:?}, expected {expected:?}"
        )));
    }
    Ok(())
}

#[cfg(test)]
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

fn outer_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "d128 two-slice outer statement proof rejected: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn input() -> ZkAiD128TwoSliceOuterStatementInput {
        let rows = vec![
            D128TwoSliceOuterStatementRow {
                index: 0,
                slice_id: "rmsnorm_public_rows".to_string(),
                slice_tag: 1,
                row_count: 128,
                verified: true,
                proof_backend_version: ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_VERSION.to_string(),
                verifier_domain: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN.to_string(),
                required_backend_version:
                    ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION.to_string(),
                statement_commitment: ZKAI_D128_RMSNORM_PUBLIC_ROW_STATEMENT_COMMITMENT.to_string(),
                public_instance_commitment: ZKAI_D128_RMSNORM_PUBLIC_ROW_PUBLIC_INSTANCE_COMMITMENT
                    .to_string(),
                proof_native_parameter_commitment:
                    ZKAI_D128_RMSNORM_PUBLIC_ROW_PROOF_NATIVE_PARAMETER_COMMITMENT.to_string(),
                source_file_sha256: ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_FILE_SHA256.to_string(),
                source_payload_sha256: ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_PAYLOAD_SHA256
                    .to_string(),
            },
            D128TwoSliceOuterStatementRow {
                index: 1,
                slice_id: "rmsnorm_projection_bridge".to_string(),
                slice_tag: 2,
                row_count: 128,
                verified: true,
                proof_backend_version: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_VERSION
                    .to_string(),
                verifier_domain: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN.to_string(),
                required_backend_version:
                    ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION.to_string(),
                statement_commitment: ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_STATEMENT_COMMITMENT
                    .to_string(),
                public_instance_commitment:
                    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PUBLIC_INSTANCE_COMMITMENT.to_string(),
                proof_native_parameter_commitment:
                    ZKAI_D128_RMSNORM_TO_PROJECTION_BRIDGE_PROOF_NATIVE_PARAMETER_COMMITMENT
                        .to_string(),
                source_file_sha256: ZKAI_D128_RMSNORM_PROJECTION_BRIDGE_SOURCE_FILE_SHA256
                    .to_string(),
                source_payload_sha256: ZKAI_D128_RMSNORM_PROJECTION_BRIDGE_SOURCE_PAYLOAD_SHA256
                    .to_string(),
            },
        ];
        let mut input = ZkAiD128TwoSliceOuterStatementInput {
            schema: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_INPUT_SCHEMA.to_string(),
            decision: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_INPUT_DECISION.to_string(),
            operation: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_OPERATION.to_string(),
            target_id: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_TARGET_ID.to_string(),
            required_backend_version: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_REQUIRED_BACKEND_VERSION
                .to_string(),
            verifier_domain: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_VERIFIER_DOMAIN.to_string(),
            width: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_WIDTH,
            selected_slice_count: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SLICE_COUNT,
            selected_checked_rows: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_SELECTED_ROWS,
            selected_slice_ids: EXPECTED_SELECTED_SLICE_IDS
                .iter()
                .map(|value| value.to_string())
                .collect(),
            two_slice_target_commitment: ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT.to_string(),
            accumulator_commitment: ZKAI_D128_TWO_SLICE_ACCUMULATOR_COMMITMENT.to_string(),
            accumulator_verifier_handle_commitment: ZKAI_D128_TWO_SLICE_VERIFIER_HANDLE_COMMITMENT
                .to_string(),
            statement_commitment: String::new(),
            public_instance_commitment: String::new(),
            proof_native_parameter_commitment: String::new(),
            rows,
            non_claims: EXPECTED_NON_CLAIMS
                .iter()
                .map(|value| value.to_string())
                .collect(),
            proof_verifier_hardening: EXPECTED_PROOF_VERIFIER_HARDENING
                .iter()
                .map(|value| value.to_string())
                .collect(),
            next_backend_step: ZKAI_D128_TWO_SLICE_OUTER_STATEMENT_NEXT_BACKEND_STEP.to_string(),
            validation_commands: EXPECTED_VALIDATION_COMMANDS
                .iter()
                .map(|value| value.to_string())
                .collect(),
        };
        input.statement_commitment = statement_commitment(&input);
        input.public_instance_commitment = public_instance_commitment(&input.statement_commitment);
        input.proof_native_parameter_commitment =
            proof_native_parameter_commitment(&input.statement_commitment);
        input
    }

    #[test]
    fn outer_statement_input_validates_bindings() {
        let input = input();
        validate_outer_input(&input).expect("valid input");
        assert_eq!(input.rows.len(), 2);
        assert_eq!(input.selected_checked_rows, 256);
        assert_eq!(
            input.two_slice_target_commitment,
            ZKAI_D128_TWO_SLICE_TARGET_COMMITMENT
        );
        assert!(input.non_claims.contains(
            &"not native verifier execution of the selected inner Stwo proofs".to_string()
        ));
    }

    #[test]
    fn outer_statement_air_proof_round_trips() {
        let input = input();
        let envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        assert!(!envelope.proof.is_empty());
        assert!(verify_zkai_d128_two_slice_outer_statement_envelope(&envelope).expect("verify"));
    }

    #[test]
    fn outer_statement_rejects_slice_order_drift() {
        let mut input = input();
        input.rows.swap(0, 1);
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("outer row index"));
    }

    #[test]
    fn outer_statement_rejects_false_verified_flag() {
        let mut input = input();
        input.rows[0].verified = false;
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("verified flag"));
    }

    #[test]
    fn outer_statement_rejects_statement_commitment_drift() {
        let mut input = input();
        input.rows[0].statement_commitment = format!("blake2b-256:{}", "aa".repeat(32));
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("slice statement commitment"));
    }

    #[test]
    fn outer_statement_rejects_source_hash_drift() {
        let mut input = input();
        input.rows[1].source_payload_sha256 = "bb".repeat(32);
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("source payload sha256"));
    }

    #[test]
    fn outer_statement_rejects_non_claim_order_drift() {
        let mut input = input();
        input.non_claims.swap(0, 1);
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("non claims"));
    }

    #[test]
    fn outer_statement_rejects_hardening_order_drift() {
        let mut input = input();
        input.proof_verifier_hardening.swap(0, 1);
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("proof verifier hardening"));
    }

    #[test]
    fn outer_statement_rejects_validation_command_order_drift() {
        let mut input = input();
        input.validation_commands.swap(0, 1);
        let error = validate_outer_input(&input).unwrap_err();
        assert!(error.to_string().contains("validation commands"));
    }

    #[test]
    fn outer_statement_rejects_tampered_row_after_proving() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        envelope.input.rows[0].source_file_sha256 =
            ZKAI_D128_RMSNORM_PUBLIC_ROW_SOURCE_FILE_SHA256.replace('d', "e");
        assert!(verify_zkai_d128_two_slice_outer_statement_envelope(&envelope).is_err());
    }

    #[test]
    fn outer_statement_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_d128_two_slice_outer_statement_envelope(&envelope).is_err());
    }

    #[test]
    fn outer_statement_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        commitments.push(commitments[0].clone());
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d128_two_slice_outer_statement_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn outer_statement_rejects_unknown_proof_payload_fields() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        payload["unexpected"] = Value::Bool(true);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        assert!(verify_zkai_d128_two_slice_outer_statement_envelope(&envelope).is_err());
    }

    #[test]
    fn outer_statement_rejects_unknown_envelope_fields() {
        let input = input();
        let envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        let mut value = serde_json::to_value(&envelope).expect("envelope json");
        value["unexpected"] = Value::Bool(true);
        let bytes = serde_json::to_vec(&value).expect("envelope bytes");
        assert!(zkai_d128_two_slice_outer_statement_envelope_from_json_slice(&bytes).is_err());
    }

    #[test]
    fn outer_statement_rejects_pcs_config_drift() {
        let input = input();
        let mut envelope =
            prove_zkai_d128_two_slice_outer_statement_envelope(&input).expect("outer proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error = verify_zkai_d128_two_slice_outer_statement_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }

    #[test]
    fn outer_statement_uses_empty_preprocessed_and_bound_base_trace_roots() {
        let input = input();
        let component = outer_component();
        let sizes = component.trace_log_degree_bounds();
        assert_eq!(sizes.len(), 2);
        assert!(sizes[0].is_empty());
        assert!(!sizes[1].is_empty());
        let roots = outer_commitment_roots(&input, outer_pcs_config()).expect("roots");
        assert_eq!(roots.len(), 2);
        assert_ne!(roots[0], roots[1]);
    }

    #[test]
    fn outer_statement_statement_commitment_is_stable_for_artifacts() {
        let input = input();
        assert_eq!(input.statement_commitment, statement_commitment(&input));
        assert_eq!(
            input.public_instance_commitment,
            public_instance_commitment(&input.statement_commitment)
        );
        assert_eq!(
            input.proof_native_parameter_commitment,
            proof_native_parameter_commitment(&input.statement_commitment)
        );
        assert_eq!(sha256_hex(input.statement_commitment.as_bytes()).len(), 64);
    }
}
